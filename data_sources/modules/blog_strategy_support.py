"""Markdown and evidence helpers for the commercial blog strategy guard."""

from __future__ import annotations

import html
import json
import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

try:
    from .artifact_detection import extract_frontmatter, strip_frontmatter
    from .blog_strategy_contract import BlogStrategyContract
    from .commercial_pillar_index import CommercialPillarRecord
    from .guard_common import Finding, make_finding
except ImportError:  # pragma: no cover - direct script execution.
    from artifact_detection import extract_frontmatter, strip_frontmatter
    from blog_strategy_contract import BlogStrategyContract
    from commercial_pillar_index import CommercialPillarRecord
    from guard_common import Finding, make_finding


MARKDOWN_LINK_RE = re.compile(
    r"(?<!!)\[(?P<anchor>[^\]]+)\]\((?P<href>[^)\s]+)(?:\s+['\"][^)]*['\"])?\)"
)
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
        if raw_line.startswith(("    ", "\t")) and not re.match(
            r"^\s{4}[-*+]\s+", raw_line
        ):
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
    return any(
        name.casefold() in combined
        for name in (
            "Search Intent and Format Decision",
            "Commercial Pillar and Anchor Decision",
        )
    )


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
        return [
            _finding(
                "blog_strategy_context_request_invalid",
                1,
                f"Unable to read context request: {exc}",
            )
        ]
    scope = payload.get("scope", {}) if isinstance(payload, dict) else {}
    if not isinstance(scope, dict):
        return [
            _finding(
                "blog_strategy_context_request_invalid",
                1,
                "Context request scope must be an object.",
            )
        ]
    findings: list[Finding] = []
    request_brand = str(scope.get("brand", "")).strip()
    request_market = str(scope.get("region", scope.get("market", ""))).strip().upper()
    if request_brand and request_brand.casefold() != brand.casefold():
        findings.append(
            _finding(
                "blog_strategy_context_brand_mismatch",
                1,
                "Context request brand does not match article Brand.",
            )
        )
    if request_market and request_market != market:
        findings.append(
            _finding(
                "blog_strategy_context_market_mismatch",
                1,
                "Context request region does not match article Market.",
            )
        )
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
    return "no specific" in text and any(
        phrase in text
        for phrase in ("fit", "destination", "industry page", "solution page", "feature page")
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
            usable = candidate.is_file() and bool(
                candidate.read_text(encoding="utf-8-sig").strip()
            )
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


def _report_metadata(
    record: CommercialPillarRecord,
    *,
    today: date,
) -> dict[str, object]:
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
        suggestion=(
            "Regenerate the commercial pillar decision from verified evidence and "
            "correct the visible article link."
        ),
        **extra,
    )


def _sort_findings(findings: list[Finding]) -> list[Finding]:
    return sorted(
        findings,
        key=lambda finding: (int(finding["line"]), str(finding["rule_id"])),
    )
