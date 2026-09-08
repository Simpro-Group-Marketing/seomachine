"""Fail-closed commercial pillar and article-link strategy guard."""

from __future__ import annotations

import argparse
import html
import json
import re
import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Optional, Sequence
from urllib.parse import urlsplit, urlunsplit

try:
    from .artifact_detection import extract_frontmatter, strip_frontmatter
    from .blog_strategy_contract import BlogStrategyContract, validate_contract
    from .commercial_pillar_index import (
        CommercialPillarIndex,
        CommercialPillarIndexError,
        CommercialPillarRecord,
        get_verified_destination,
        load_index,
        validate_index,
    )
    from .guard_common import Finding, make_finding, should_fail, summarize_findings
    from .proof_sidecar import load_sidecar_content
    from .url_validator import UrlValidationSummary
except ImportError:  # pragma: no cover - direct script execution.
    from artifact_detection import extract_frontmatter, strip_frontmatter
    from blog_strategy_contract import BlogStrategyContract, validate_contract
    from commercial_pillar_index import (
        CommercialPillarIndex,
        CommercialPillarIndexError,
        CommercialPillarRecord,
        get_verified_destination,
        load_index,
        validate_index,
    )
    from guard_common import Finding, make_finding, should_fail, summarize_findings
    from proof_sidecar import load_sidecar_content
    from url_validator import UrlValidationSummary


DEFAULT_INDEX_PATH = Path(__file__).resolve().parents[2] / "context" / "commercial-pillar-index.json"
MARKDOWN_LINK_RE = re.compile(r"(?<!!)\[(?P<anchor>[^\]]+)\]\((?P<href>[^)\s]+)(?:\s+['\"][^)]*['\"])?\)")
MARKDOWN_IMAGE_RE = re.compile(r"!\[[^\]]*\]\([^)]+\)")
INLINE_CODE_RE = re.compile(r"`[^`\n]*`")
H2_RE = re.compile(r"^\s{0,3}##(?!#)\s+(?P<title>.+?)\s*#*\s*$")
H1_RE = re.compile(r"^\s{0,3}#(?!#)\s+(?P<title>.+?)\s*#*\s*$", re.MULTILINE)
HTML_TAG_RE = re.compile(r"<[^>]+>")
MARKDOWN_DECORATION_RE = re.compile(r"[*_~]+")


@dataclass(frozen=True)
class VisibleLink:
    href: str
    anchor: str
    line: int
    h2: str
    paragraph: int
    line_text: str


def check_content(
    content: str,
    *,
    proof_content: str,
    index: CommercialPillarIndex,
    today: date,
    url_summary: UrlValidationSummary | None = None,
    context_request: str | Path | None = None,
    article_path: str | Path | None = None,
    artifact_root: str | Path | None = None,
    require_strategy: bool = False,
) -> list[Finding]:
    """Validate a parsed contract against the index and visible Markdown."""
    if not _requires_blog_strategy(content, proof_content, require_strategy=require_strategy):
        return []
    contract, contract_findings = validate_contract(proof_content)
    if contract_findings or contract is None:
        return contract_findings

    frontmatter = extract_frontmatter(content)
    brand = frontmatter.get("brand", "").strip()
    market = frontmatter.get("market", "").strip().upper()
    primary_keyword = (
        frontmatter.get("primary_keyword")
        or frontmatter.get("target_keyword")
        or ""
    ).strip()
    title = _article_title(content, frontmatter.get("title", ""))

    findings: list[Finding] = []
    if not brand:
        findings.append(_finding("blog_strategy_brand_missing", 1, "Simpro blog frontmatter requires Brand."))
    if not market:
        findings.append(_finding("blog_strategy_market_missing", 1, "Simpro blog frontmatter requires Market."))
    if not primary_keyword:
        findings.append(_finding("blog_strategy_primary_keyword_missing", 1, "Simpro blog frontmatter requires Primary Keyword."))

    index_findings = validate_index(index, today=today)
    if index_findings:
        return index_findings + findings

    decision = contract.commercial_pillar
    destination: Optional[CommercialPillarRecord] = None
    try:
        destination = get_verified_destination(
            index,
            destination_id=decision.destination_id,
            brand=brand,
            market=market,
        )
    except CommercialPillarIndexError as exc:
        matching = [record for record in index.records if record.destination_id == decision.destination_id]
        if matching:
            record = matching[0]
            destination = record
            if brand and record.brand.casefold() != brand.casefold():
                findings.append(_finding("blog_strategy_brand_mismatch", 1, str(exc), record=record))
            if market and record.market != market:
                findings.append(_finding("blog_strategy_market_mismatch", 1, str(exc), record=record))
            if record.status != "verified":
                findings.append(_finding("blog_strategy_destination_not_verified", 1, str(exc), record=record))
        else:
            findings.append(_finding("blog_strategy_destination_unknown", 1, str(exc)))

    if context_request:
        findings.extend(_context_request_findings(context_request, brand=brand, market=market))
    if destination is None:
        return _sort_findings(findings)

    metadata = _report_metadata(destination, today=today)
    if decision.commercial_pillar_url != destination.canonical_url:
        findings.append(
            _finding(
                "blog_strategy_pillar_url_mismatch",
                1,
                "Sidecar commercial pillar URL does not equal the indexed canonical URL.",
                record=destination,
                **metadata,
            )
        )
    if decision.status != "aligned":
        findings.append(_finding("blog_strategy_pillar_status_blocked", 1, "Commercial pillar decision is not aligned.", record=destination, **metadata))
    if contract.search_intent.status != "ready":
        findings.append(_finding("blog_strategy_search_status_blocked", 1, "Search intent and format decision is not ready.", record=destination, **metadata))
    if contract.lifecycle.status != "scheduled":
        findings.append(_finding("blog_strategy_lifecycle_status_blocked", 1, "Lifecycle refresh record is not scheduled.", record=destination, **metadata))
    if destination.pillar_type == "industries_hub" and not _has_industries_hub_exception_reason(decision):
        findings.append(
            _finding(
                "blog_strategy_industries_hub_reason_missing",
                1,
                "Industries hub commercial pillars require a documented no-specific-fit reason.",
                record=destination,
                **metadata,
            )
        )
    if artifact_root is not None:
        findings.extend(
            _research_artifact_findings(
                contract,
                artifact_root=artifact_root,
                record=destination,
                metadata=metadata,
            )
        )
    if title and _normalize_text(title) != _normalize_text(decision.article_title):
        findings.append(_finding("blog_strategy_article_title_mismatch", 1, "Article title does not match the commercial pillar decision.", record=destination, **metadata))
    if primary_keyword and _normalize_text(primary_keyword) != _normalize_text(decision.article_primary_keyword):
        findings.append(_finding("blog_strategy_article_keyword_mismatch", 1, "Article primary keyword does not match the commercial pillar decision.", record=destination, **metadata))

    normalized_article_keyword = _normalize_text(primary_keyword)
    normalized_destination_keyword = _normalize_text(destination.main_keyword)
    if normalized_article_keyword and normalized_article_keyword == normalized_destination_keyword:
        findings.append(_finding("blog_strategy_primary_keyword_collision", 1, "Article primary keyword exactly collides with the commercial destination's indexed main keyword.", record=destination, **metadata))
    elif (
        normalized_article_keyword
        and normalized_destination_keyword
        and (
            _contains_normalized_phrase(primary_keyword, destination.main_keyword)
            or _contains_normalized_phrase(destination.main_keyword, primary_keyword)
        )
        and not _overlap_difference_is_verified(
            contract,
            artifact_root=artifact_root,
            destination=destination,
        )
    ):
        findings.append(_finding("blog_strategy_keyword_overlap_unproved", 1, "Contained keywords require verified SERP evidence of different intent and different content type.", record=destination, **metadata))

    if article_path:
        parent = Path(article_path).parent.name.casefold()
        if decision.cannibalization_decision == "consolidate" or (
            parent == "drafts" and decision.cannibalization_decision == "update_existing"
        ):
            findings.append(_finding("blog_strategy_new_article_blocked", 1, f"Cannibalization decision {decision.cannibalization_decision} blocks a new article.", record=destination, **metadata))

    if not _contains_normalized_phrase(decision.planned_anchor_text, destination.main_keyword):
        findings.append(_finding("blog_strategy_planned_anchor_keyword_missing", 1, "Planned anchor text omits the destination's indexed main keyword.", record=destination, **metadata))

    links = _extract_visible_links(content)
    exact_links = [link for link in links if link.href == destination.canonical_url]
    noncanonical_variants = [
        link
        for link in links
        if _without_query_fragment(link.href) == destination.canonical_url
        and link.href != destination.canonical_url
    ]
    if noncanonical_variants:
        for link in noncanonical_variants:
            findings.append(_finding("blog_strategy_pillar_link_noncanonical", link.line, "Commercial pillar link contains tracking parameters or a fragment.", record=destination, link=link, **metadata))
    if not exact_links:
        findings.append(_finding("blog_strategy_pillar_link_missing", 1, "The exact indexed pillar URL is missing from visible article-body Markdown.", record=destination, **metadata))
    else:
        keyword_links = [
            link
            for link in exact_links
            if _contains_normalized_phrase(link.anchor, destination.main_keyword)
        ]
        if not keyword_links:
            findings.append(_finding("blog_strategy_anchor_keyword_missing", exact_links[0].line, "Visible pillar anchor omits the destination's indexed main keyword.", record=destination, link=exact_links[0], **metadata))
        normalized_planned_anchor = _normalize_text(decision.planned_anchor_text)
        planned_anchor_links = [
            link
            for link in keyword_links
            if _normalize_text(link.anchor) == normalized_planned_anchor
        ]
        if keyword_links and not planned_anchor_links:
            findings.append(_finding("blog_strategy_approved_anchor_missing", keyword_links[0].line, "No visible pillar link uses the approved planned anchor text.", record=destination, link=keyword_links[0], **metadata))
        planned_h2 = _normalize_text(decision.planned_h2_section)
        approved_links = [
            link
            for link in planned_anchor_links
            if _normalize_text(link.h2) == planned_h2
        ]
        if planned_anchor_links and not approved_links:
            findings.append(_finding("blog_strategy_planned_h2_mismatch", planned_anchor_links[0].line, "Approved pillar link is outside the planned H2 section.", record=destination, link=planned_anchor_links[0], **metadata))
        for approved_link in approved_links:
            paragraph_link_count = sum(
                1 for link in links if link.paragraph == approved_link.paragraph
            )
            if paragraph_link_count > 1:
                findings.append(_finding("blog_strategy_pillar_paragraph_link_count", approved_link.line, "The designated pillar paragraph contains more than one link.", record=destination, link=approved_link, **metadata))
                break

    if url_summary is not None:
        for result in url_summary.results:
            if result.url == destination.canonical_url and result.final_url and result.final_url != destination.canonical_url:
                findings.append(_finding("blog_strategy_pillar_redirect", result.line or 1, f"Commercial pillar redirects to {result.final_url}.", record=destination, **metadata))
                break

    return _sort_findings(findings)


def check_file(
    path: str | Path,
    *,
    proof_sidecar: str | Path | None,
    context_request: str | Path | None = None,
    context_pack: str | Path | None = None,
    context_receipt: str | Path | None = None,
    url_summary: UrlValidationSummary | None = None,
    require_strategy: bool = False,
) -> list[Finding]:
    """Validate the sidecar strategy contract and the final public Markdown."""
    del context_pack, context_receipt
    article_path = Path(path)
    proof_content = load_sidecar_content(article_path, proof_sidecar)
    try:
        index = load_index(DEFAULT_INDEX_PATH)
    except CommercialPillarIndexError as exc:
        return [_finding("blog_strategy_index_load_failed", 1, str(exc))]
    return check_content(
        article_path.read_text(encoding="utf-8"),
        proof_content=proof_content,
        index=index,
        today=date.today(),
        url_summary=url_summary,
        context_request=context_request,
        article_path=article_path,
        artifact_root=DEFAULT_INDEX_PATH.parent.parent,
        require_strategy=require_strategy,
    )


def _extract_visible_links(content: str) -> list[VisibleLink]:
    body, body_start_line = strip_frontmatter(content)
    links: list[VisibleLink] = []
    current_h2 = ""
    paragraph = 0
    in_fence = False
    in_comment = False
    for offset, raw_line in enumerate(body.splitlines()):
        line_number = body_start_line + offset
        stripped = raw_line.strip()
        if stripped.startswith("```") or stripped.startswith("~~~"):
            in_fence = not in_fence
            paragraph += 1
            continue
        if in_fence:
            continue
        if raw_line.startswith(("    ", "\t")) and not re.match(r"^\s{4}[-*+]\s+", raw_line):
            paragraph += 1
            continue
        visible_line, in_comment = _strip_comments(raw_line, in_comment=in_comment)
        if not visible_line.strip():
            paragraph += 1
            continue
        h2_match = H2_RE.match(visible_line)
        if h2_match:
            current_h2 = h2_match.group("title").strip()
            paragraph += 1
            continue
        prepared = INLINE_CODE_RE.sub("", visible_line)
        prepared = MARKDOWN_IMAGE_RE.sub("", prepared)
        for match in MARKDOWN_LINK_RE.finditer(prepared):
            links.append(
                VisibleLink(
                    href=html.unescape(match.group("href").strip()),
                    anchor=html.unescape(match.group("anchor").strip()),
                    line=line_number,
                    h2=current_h2,
                    paragraph=paragraph,
                    line_text=raw_line.strip(),
                )
            )
    return links


def _article_title(content: str, frontmatter_title: str) -> str:
    if frontmatter_title.strip():
        return frontmatter_title.strip()
    body, _ = strip_frontmatter(content)
    match = H1_RE.search(body)
    return match.group("title").strip() if match else ""


def _strip_comments(line: str, *, in_comment: bool) -> tuple[str, bool]:
    output = line
    if in_comment:
        if "-->" not in output:
            return "", True
        output = output.split("-->", 1)[1]
        in_comment = False
    while "<!--" in output:
        before, after = output.split("<!--", 1)
        if "-->" not in after:
            return before, True
        output = before + after.split("-->", 1)[1]
    return output, in_comment


def _normalize_text(value: str) -> str:
    normalized = html.unescape(value)
    normalized = HTML_TAG_RE.sub(" ", normalized)
    normalized = MARKDOWN_DECORATION_RE.sub("", normalized)
    normalized = re.sub(r"[^a-z0-9]+", " ", normalized.casefold())
    return re.sub(r"\s+", " ", normalized).strip()


def _contains_normalized_phrase(text: str, phrase: str) -> bool:
    normalized_text = _normalize_text(text)
    normalized_phrase = _normalize_text(phrase)
    if not normalized_text or not normalized_phrase:
        return False
    return f" {normalized_phrase} " in f" {normalized_text} "


def _without_query_fragment(value: str) -> str:
    parsed = urlsplit(value)
    return urlunsplit((parsed.scheme, parsed.netloc, parsed.path, "", ""))


def _overlap_difference_is_verified(
    contract: BlogStrategyContract,
    *,
    artifact_root: str | Path | None,
    destination: CommercialPillarRecord,
) -> bool:
    explanation = _normalize_text(
        contract.commercial_pillar.pillar_versus_blog_intent_difference
    )
    if not (
        "different intent" in explanation
        and "different content type" in explanation
        and contract.commercial_pillar.cannibalization_decision == "different_intent"
    ):
        return False
    if artifact_root is None:
        return False
    artifact_text = _research_artifact_text(
        contract.search_intent.serp_evidence_artifact,
        artifact_root=artifact_root,
    )
    normalized_artifact = _normalize_text(artifact_text)
    return (
        _contains_normalized_phrase(
            normalized_artifact,
            contract.commercial_pillar.article_primary_keyword,
        )
        and _contains_normalized_phrase(normalized_artifact, destination.main_keyword)
        and "different intent" in normalized_artifact
        and "different content type" in normalized_artifact
    )


def _requires_blog_strategy(
    content: str,
    proof_content: str,
    *,
    require_strategy: bool = False,
) -> bool:
    frontmatter = extract_frontmatter(content)
    brand = frontmatter.get("brand", "").strip()
    if brand.casefold() == "simpro":
        return True
    if require_strategy and not brand:
        return True
    combined = f"{content}\n{proof_content}".casefold()
    if "simprogroup.com" in combined:
        return True
    return any(name.casefold() in combined for name in ("Search Intent and Format Decision", "Commercial Pillar and Anchor Decision"))


def _context_request_findings(
    request_path: str | Path,
    *,
    brand: str,
    market: str,
) -> list[Finding]:
    path = Path(request_path)
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as exc:
        return [_finding("blog_strategy_context_request_invalid", 1, f"Unable to read context request: {exc}")]
    scope = payload.get("scope", {}) if isinstance(payload, dict) else {}
    if not isinstance(scope, dict):
        return [_finding("blog_strategy_context_request_invalid", 1, "Context request scope must be an object.")]
    findings: list[Finding] = []
    request_brand = str(scope.get("brand", "")).strip()
    request_market = str(scope.get("region", scope.get("market", ""))).strip().upper()
    if request_brand and request_brand.casefold() != brand.casefold():
        findings.append(_finding("blog_strategy_context_brand_mismatch", 1, "Context request brand does not match article Brand."))
    if request_market and request_market != market:
        findings.append(_finding("blog_strategy_context_market_mismatch", 1, "Context request region does not match article Market."))
    return findings


def _has_industries_hub_exception_reason(decision: object) -> bool:
    text = _normalize_text(
        " ".join(
            str(value)
            for value in (
                getattr(decision, "existing_overlapping_urls_checked", ""),
                getattr(decision, "pillar_versus_blog_intent_difference", ""),
            )
            if value
        )
    )
    return (
        "no specific" in text
        and (
            "fit" in text
            or "destination" in text
            or "industry page" in text
            or "solution page" in text
            or "feature page" in text
        )
    )


def _research_artifact_findings(
    contract: BlogStrategyContract,
    *,
    artifact_root: str | Path,
    record: CommercialPillarRecord,
    metadata: dict[str, object],
) -> list[Finding]:
    root = Path(artifact_root).resolve()
    artifacts = (
        (
            "serp",
            contract.search_intent.serp_evidence_artifact,
            "blog_strategy_serp_artifact_missing",
        ),
        (
            "related-query/PAA",
            contract.search_intent.related_query_paa_artifact,
            "blog_strategy_related_query_artifact_missing",
        ),
    )
    findings: list[Finding] = []
    for label, value, missing_rule in artifacts:
        candidate_value = Path(value)
        candidate = (
            candidate_value.resolve()
            if candidate_value.is_absolute()
            else (root / candidate_value).resolve()
        )
        try:
            candidate.relative_to(root)
        except ValueError:
            findings.append(
                _finding(
                    "blog_strategy_research_artifact_outside_root",
                    1,
                    f"The {label} evidence artifact resolves outside the repository.",
                    record=record,
                    **metadata,
                )
            )
            continue
        try:
            usable = candidate.is_file() and bool(candidate.read_text(encoding="utf-8-sig").strip())
        except (OSError, UnicodeError):
            usable = False
        if not usable:
            findings.append(
                _finding(
                    missing_rule,
                    1,
                    f"The {label} evidence artifact is missing or empty: {value}.",
                    record=record,
                    **metadata,
                )
            )
    return findings


def _research_artifact_text(value: str, *, artifact_root: str | Path) -> str:
    root = Path(artifact_root).resolve()
    candidate_value = Path(value)
    candidate = (
        candidate_value.resolve()
        if candidate_value.is_absolute()
        else (root / candidate_value).resolve()
    )
    try:
        candidate.relative_to(root)
    except ValueError:
        return ""
    try:
        return candidate.read_text(encoding="utf-8-sig") if candidate.is_file() else ""
    except (OSError, UnicodeError):
        return ""


def _report_metadata(record: CommercialPillarRecord, *, today: date) -> dict[str, object]:
    checked = date.fromisoformat(record.semrush_checked)
    return {
        "destination_id": record.destination_id,
        "pillar_type": record.pillar_type,
        "canonical_url": record.canonical_url,
        "indexed_main_keyword": record.main_keyword,
        "market": record.market,
        "semrush_database": record.semrush_database,
        "evidence_age_days": (today - checked).days,
    }


def _finding(
    rule_id: str,
    line: int,
    message: str,
    *,
    record: CommercialPillarRecord | None = None,
    link: VisibleLink | None = None,
    **extra: object,
) -> Finding:
    if record is not None:
        extra.update(
            {
                "destination_id": record.destination_id,
                "pillar_type": record.pillar_type,
                "canonical_url": record.canonical_url,
                "indexed_main_keyword": record.main_keyword,
                "market": record.market,
                "semrush_database": record.semrush_database,
            }
        )
    if link is not None:
        extra.update(
            {
                "matched_article_line": link.line_text,
                "visible_anchor": link.anchor,
            }
        )
    return make_finding(
        rule_id,
        "error",
        line,
        message=message,
        suggestion="Regenerate the commercial pillar decision from verified evidence and correct the visible article link.",
        **extra,
    )


def _sort_findings(findings: list[Finding]) -> list[Finding]:
    return sorted(findings, key=lambda finding: (int(finding["line"]), str(finding["rule_id"])))


def _main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Validate a blog strategy contract and commercial pillar link.")
    parser.add_argument("path")
    parser.add_argument("--proof-sidecar", required=True)
    parser.add_argument("--context-request")
    parser.add_argument("--fail-on", choices=["error", "warning", "none"], default="error")
    args = parser.parse_args(argv)
    findings = check_file(
        args.path,
        proof_sidecar=args.proof_sidecar,
        context_request=args.context_request,
        require_strategy=True,
    )
    payload = {"path": args.path, "summary": summarize_findings(findings), "findings": findings}
    print(json.dumps(payload, indent=2))
    return 1 if should_fail(findings, fail_on=args.fail_on) else 0


if __name__ == "__main__":
    sys.exit(_main())
