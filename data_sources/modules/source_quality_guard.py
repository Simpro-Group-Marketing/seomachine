"""Claim-level source quality and lifecycle refresh guard."""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Optional, Sequence
from urllib.parse import urlparse

try:
    from .artifact_detection import extract_frontmatter, strip_frontmatter
    from .blog_strategy_contract import BlogStrategyContract, validate_contract
    from .guard_common import Finding, make_finding, should_fail, summarize_findings
    from .proof_sidecar import load_sidecar_content
except ImportError:  # pragma: no cover - direct script execution.
    from artifact_detection import extract_frontmatter, strip_frontmatter
    from blog_strategy_contract import BlogStrategyContract, validate_contract
    from guard_common import Finding, make_finding, should_fail, summarize_findings
    from proof_sidecar import load_sidecar_content


SOURCE_MAP_HEADING_RE = re.compile(r"^\s*(?:#{1,6}\s+)?Source Map:?\s*$", re.IGNORECASE)
ANY_HEADING_RE = re.compile(r"^\s*#{1,6}\s+")
HEADING_RE = re.compile(r"^\s*#{1,6}\s+(?P<title>.*?)\s*$")
SIDECAR_SECTION_HEADING_RE = re.compile(
    r"^\s*(?:#{1,6}\s+)?(?:"
    r"Editorial Validation Appendix|PAA/FAQ Provenance|Metric Proof Pack|Source Map|Customer Proof Pack|"
    r"E-E-A-T Proof Map|FAQ Proof Map|FAQ Proof|Structured data plan|Early Artifact Plan|"
    r"Concrete Answer Check|Vault Brand Language Alignment|Source Routing Decision|"
    r"Search Intent and Format Decision|Commercial Pillar and Anchor Decision|Lifecycle Refresh Record|"
    r"Author Verification|Reviewer Verification|Fred Voccola Authority Selection|"
    r"Named Feature Status and Commercial Treatment|Context Binding|Context Claim Use Map|"
    r"Discovery Trace|Selected Resource Inventory|Context Recovery Report|Approved Claim Evidence|"
    r"Constraints and Unresolved Gaps|Retrieved Guidance"
    r"):?\s*$",
    re.IGNORECASE,
)
FENCE_RE = re.compile(r"^\s*(```|~~~)")
ROW_RE = re.compile(r"^\s*[-*+]\s+(?P<body>Claim\s*:.*)$", re.IGNORECASE)
FAQ_MAP_HEADING_RE = re.compile(r"^\s*(?:#{1,6}\s+)?FAQ Proof Map:?\s*$", re.IGNORECASE)
URL_FIELD_RE = re.compile(r"(?:^|\|)\s*URL\s*:\s*(?P<url>https?://[^|\s]+)", re.IGNORECASE)
ISO_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
DATED_EVIDENCE_RE = re.compile(r"\b\d{4}-\d{2}-\d{2}\b")
PLACEHOLDER_RE = re.compile(r"\b(?:tbd|todo|placeholder|fill[ -]?in|unknown)\b", re.IGNORECASE)
PERFORMANCE_CLAIM_RE = re.compile(
    r"\b(?:improv(?:e|ed|ement)|increase[sd]?|decrease[sd]?|lift(?:ed)?|grew|growth|gain(?:ed)?|outperform(?:ed)?|"
    r"(?:traffic|clicks?|sessions?|impressions?|rankings?|positions?).{0,50}?\b(?:up|down|rose|jump(?:ed)?|grew|fell|dropped|increased|decreased|improved))\b",
    re.IGNORECASE,
)
URL_RE = re.compile(r"https?://\S+", re.IGNORECASE)
H1_RE = re.compile(r"^\s{0,3}#(?!#)\s+(?P<title>.+?)\s*#*\s*$", re.MULTILINE)
HIGH_VOLATILITY_TOPIC_RE = re.compile(r"\b(?:pricing|price|prices|cost|costs|regulation|standard|comparison|compare|vs|statistics?|stats?|product status)\b", re.IGNORECASE)

REQUIRED_FIELDS = (
    "claim",
    "claim type",
    "url",
    "evidence",
    "source class",
    "original-source status",
    "source date",
    "checked date",
    "claim fit",
    "freshness decision",
    "freshness reason",
    "status",
    "intended use",
)
ALLOWED_CLAIM_TYPES = {
    "statistic",
    "regulation",
    "standard",
    "factual",
    "definition",
    "historical",
    "recommendation",
    "comparison",
    "faq",
    "customer_proof",
    "customer_metric",
    "quote",
    "review",
    "simpro_metric",
    "product_claim",
    "feature_claim",
    "product_status",
    "pricing",
}
ALLOWED_SOURCE_CLASSES = {
    "official",
    "regulator",
    "standards_body",
    "government",
    "academic",
    "trade_association",
    "neutral",
    "non_competing_expert",
    "competitor_owned",
    "simpro_owned",
    "customer",
    "review_site",
    "original_research",
    "secondary",
}
ALLOWED_ORIGINAL_STATUSES = {"original", "secondary", "not_applicable"}
ALLOWED_FRESHNESS_DECISIONS = {"current", "historical_scoped", "refresh_required"}
OFFICIAL_CLASSES = {"official", "regulator", "standards_body", "government"}
STRICTER_PROOF_TYPES = {
    "customer_proof",
    "customer_metric",
    "quote",
    "review",
    "simpro_metric",
    "product_claim",
    "feature_claim",
    "product_status",
}
STRICTER_PROOF_SECTIONS = {
    "customer_proof": (("Customer Proof Pack",),),
    "customer_metric": (("Customer Proof Pack",),),
    "quote": (("Customer Proof Pack",),),
    "review": (("Customer Proof Pack", "Review Story Selection", "Review Site Theme Selection"),),
    "simpro_metric": (("Metric Proof Pack",),),
    "product_claim": (("Vault Context Read Path",), ("Vault Brand Language Alignment",)),
    "product_status": (("Vault Context Read Path",), ("Vault Brand Language Alignment",)),
    "feature_claim": (
        ("Vault Context Read Path",),
        ("Vault Brand Language Alignment",),
        ("Named Feature/Add-On Link Check", "Named Feature Status and Commercial Treatment"),
    ),
}
HIGH_VOLATILITY_TYPES = {
    "statistic",
    "regulation",
    "standard",
    "comparison",
    "product_status",
    "pricing",
}


@dataclass(frozen=True)
class SourceMapRow:
    line: int
    fields: dict[str, str]

    @property
    def claim(self) -> str:
        return self.fields.get("claim", "")

    @property
    def url(self) -> str:
        return self.fields.get("url", "")

    @property
    def claim_type(self) -> str:
        return self.fields.get("claim type", "").casefold()


def check_source_map(proof_content: str, *, today: date) -> list[Finding]:
    """Validate every Source Map row in validation-sidecar content."""
    rows = _extract_source_rows(proof_content)
    findings: list[Finding] = []
    faq_urls = _faq_proof_urls(proof_content)
    seen_exact: dict[tuple[tuple[str, str], ...], int] = {}
    seen_claim_url: dict[tuple[str, str], tuple[int, tuple[tuple[str, str], ...]]] = {}

    for row in rows:
        fields = row.fields
        for field in REQUIRED_FIELDS:
            value = fields.get(field, "").strip()
            if not value:
                findings.append(_finding("source_quality_required_field_missing", row.line, f"Source Map row is missing required field: {field}."))
            elif PLACEHOLDER_RE.search(value):
                findings.append(_finding("source_quality_placeholder", row.line, f"Source Map field contains placeholder content: {field}."))

        claim_type = row.claim_type
        source_class = fields.get("source class", "").casefold()
        original_status = fields.get("original-source status", "").casefold()
        freshness_decision = fields.get("freshness decision", "").casefold()
        claim_fit = fields.get("claim fit", "").casefold()
        status = fields.get("status", "").casefold()

        if claim_type and claim_type not in ALLOWED_CLAIM_TYPES:
            findings.append(_finding("source_quality_claim_type_invalid", row.line, f"Unsupported Source Map claim type: {claim_type}."))
        if source_class and source_class not in ALLOWED_SOURCE_CLASSES:
            findings.append(_finding("source_quality_source_class_invalid", row.line, f"Unsupported Source Map source class: {source_class}."))
        if original_status and original_status not in ALLOWED_ORIGINAL_STATUSES:
            findings.append(_finding("source_quality_original_status_invalid", row.line, f"Unsupported original-source status: {original_status}."))
        if freshness_decision and freshness_decision not in ALLOWED_FRESHNESS_DECISIONS:
            findings.append(_finding("source_quality_freshness_decision_invalid", row.line, f"Unsupported freshness decision: {freshness_decision}."))
        if freshness_decision == "refresh_required":
            findings.append(_finding("source_quality_refresh_required", row.line, "Evidence marked refresh_required cannot approve a public claim."))
        if claim_fit and claim_fit != "direct":
            findings.append(_finding("source_quality_claim_fit_not_direct", row.line, "Public Source Map claims require Claim fit: direct."))
        if status and status != "approved":
            findings.append(_finding("source_quality_status_not_approved", row.line, "Public Source Map rows require Status: approved."))

        parsed_url = urlparse(row.url)
        if row.url and (parsed_url.scheme != "https" or not parsed_url.netloc):
            findings.append(_finding("source_quality_url_invalid", row.line, "Source Map URL must be an absolute HTTPS public URL."))

        findings.extend(_date_findings(row, today=today))
        if claim_type == "statistic" and original_status != "original":
            findings.append(_finding("source_quality_statistic_not_original", row.line, "Statistics require an original source."))
        if original_status == "original" and source_class == "secondary":
            findings.append(
                _finding(
                    "source_quality_original_status_conflict",
                    row.line,
                    "A secondary source class cannot be declared as the original source.",
                )
            )
        if claim_type in {"regulation", "standard"} and source_class not in OFFICIAL_CLASSES:
            findings.append(_finding("source_quality_official_source_required", row.line, "Regulations and standards require an official source."))
        if source_class == "competitor_owned" and claim_type in {"recommendation", "comparison", "faq"}:
            findings.append(_finding("source_quality_competitor_neutral_proof", row.line, "Competitor-owned evidence cannot support a neutral verdict, recommendation, comparison, or FAQ."))
        source_date = fields.get("source date", "").casefold()
        if source_date in {"undated", "historical"} and freshness_decision != "historical_scoped":
            findings.append(_finding("source_quality_undated_unscoped", row.line, "Undated or historical evidence requires Freshness decision: historical_scoped."))
        if claim_type in STRICTER_PROOF_TYPES and not _has_stricter_proof_route(
            proof_content,
            claim_type,
        ):
            findings.append(_finding("source_quality_stricter_proof_required", row.line, "This claim type must use its controlling customer, metric, vault-receipt, review, or named-feature proof gate; Source Map cannot approve it."))
        if claim_type == "faq" and row.url not in faq_urls:
            findings.append(_finding("source_quality_faq_proof_map_required", row.line, "FAQ Source Map evidence requires a matching exact FAQ Proof Map URL."))
        freshness_reason = fields.get("freshness reason", "").strip().casefold()
        if freshness_decision in {"historical_scoped", "refresh_required"} and freshness_reason in {
            "",
            "none",
            "n/a",
            "na",
            "not_applicable",
            "not applicable",
        }:
            findings.append(_finding("source_quality_freshness_reason_missing", row.line, "Historical or refresh-required evidence needs a substantive freshness reason."))

        exact_key = tuple(sorted((key, value.casefold()) for key, value in fields.items()))
        claim_url_key = (_normalize(row.claim), row.url.casefold())
        if exact_key in seen_exact:
            findings.append(_finding("source_quality_row_duplicate", row.line, f"Source Map row duplicates line {seen_exact[exact_key]}."))
        else:
            seen_exact[exact_key] = row.line
        if claim_url_key in seen_claim_url and seen_claim_url[claim_url_key][1] != exact_key:
            findings.append(_finding("source_quality_row_conflict", row.line, f"Source Map row conflicts with line {seen_claim_url[claim_url_key][0]}."))
        else:
            seen_claim_url[claim_url_key] = (row.line, exact_key)

    return _sort_findings(findings)


def check_content(content: str, *, proof_content: str, today: date) -> list[Finding]:
    """Validate Source Map quality plus the versioned lifecycle record."""
    findings = check_source_map(proof_content, today=today)
    if not _requires_lifecycle_contract(content, proof_content):
        return _sort_findings(findings)
    if not _extract_source_rows(proof_content):
        findings.append(
            _finding(
                "source_quality_source_map_missing",
                1,
                "Lifecycle-required Simpro blog sidecars require at least one executable Source Map claim row.",
            )
        )
    contract, contract_findings = validate_contract(proof_content)
    if contract_findings or contract is None:
        return _sort_findings(findings + contract_findings)
    findings.extend(_lifecycle_findings(content, proof_content, contract, today=today))
    return _sort_findings(findings)


def check_file(
    path: str | Path,
    *,
    fail_on: str = "error",
    proof_sidecar: str | Path | None = None,
) -> list[Finding]:
    """Validate a public article and its explicit lifecycle/source sidecar."""
    if fail_on not in {"error", "warning", "none"}:
        raise ValueError("fail_on must be one of: error, warning, none")
    article_path = Path(path)
    proof_content = load_sidecar_content(article_path, str(proof_sidecar) if proof_sidecar else None)
    return check_content(
        article_path.read_text(encoding="utf-8"),
        proof_content=proof_content,
        today=date.today(),
    )


def _lifecycle_findings(
    content: str,
    proof_content: str,
    contract: BlogStrategyContract,
    *,
    today: date,
) -> list[Finding]:
    findings: list[Finding] = []
    lifecycle = contract.lifecycle
    frontmatter = extract_frontmatter(content)
    article_updated = (
        frontmatter.get("last_updated")
        or frontmatter.get("last_update")
        or ""
    ).strip()
    try:
        last_updated = date.fromisoformat(lifecycle.last_updated_date)
        next_review = date.fromisoformat(lifecycle.next_review_date)
    except ValueError:
        return [_finding("lifecycle_date_invalid", 1, "Lifecycle dates must use YYYY-MM-DD.")]

    if article_updated and article_updated != lifecycle.last_updated_date:
        findings.append(_finding("lifecycle_article_date_mismatch", 1, "Lifecycle Last-updated date does not match article frontmatter."))
    if next_review <= last_updated:
        findings.append(_finding("lifecycle_next_review_not_after_update", 1, "Next review date must be after Last-updated date."))
    if next_review < today:
        findings.append(_finding("lifecycle_next_review_overdue", 1, "Next review date is already overdue."))

    source_rows = _extract_source_rows(proof_content)
    high_volatility = any(row.claim_type in HIGH_VOLATILITY_TYPES for row in source_rows) or _is_high_volatility_topic(content, contract)
    if high_volatility and lifecycle.volatility != "high":
        findings.append(_finding("lifecycle_high_volatility_required", 1, "Pricing, regulation, product-status, comparison, standards, and statistics-led articles require high volatility."))
    allowed_days = 90 if high_volatility or lifecycle.volatility == "high" else 180
    if (next_review - last_updated).days > allowed_days:
        findings.append(_finding("lifecycle_review_cadence_exceeded", 1, f"Next review exceeds the {allowed_days}-day lifecycle cadence."))

    lane_values = {
        "GSC lane": lifecycle.gsc_lane,
        "GA4 lane": lifecycle.ga4_lane,
        "Semrush lane": lifecycle.semrush_lane,
        "AI-citation lane": lifecycle.ai_citation_lane,
    }
    for lane_name, value in lane_values.items():
        if PERFORMANCE_CLAIM_RE.search(value) and not (
            DATED_EVIDENCE_RE.search(value) and URL_RE.search(value)
        ):
            findings.append(_finding("lifecycle_performance_claim_unproved", 1, f"{lane_name} claims performance change without dated source evidence."))
        if ":" not in value:
            findings.append(_finding("lifecycle_lane_reason_missing", 1, f"{lane_name} requires status: reason."))
            if _normalize(value) in {"0", "zero"}:
                findings.append(_finding("lifecycle_lane_status_invalid", 1, f"{lane_name} cannot use zero as a data-availability status."))
            continue
        status, reason = (part.strip() for part in value.split(":", 1))
        if status.casefold() not in {"available", "unavailable", "not_applicable"}:
            findings.append(_finding("lifecycle_lane_status_invalid", 1, f"{lane_name} has unsupported availability status: {status}."))
        if not reason:
            findings.append(_finding("lifecycle_lane_reason_missing", 1, f"{lane_name} requires a non-empty reason."))
        if status.casefold() == "unavailable" and re.search(r"\b(?:0|zero)\b", reason, re.IGNORECASE):
            findings.append(_finding("lifecycle_unavailable_as_zero", 1, f"{lane_name} converts unavailable data into zero."))
    if PERFORMANCE_CLAIM_RE.search(lifecycle.decision) and not (
        DATED_EVIDENCE_RE.search(lifecycle.decision) and URL_RE.search(lifecycle.decision)
    ):
        findings.append(_finding("lifecycle_performance_claim_unproved", 1, "Lifecycle decision claims performance change without dated source evidence."))
    return findings


def _extract_source_rows(content: str) -> list[SourceMapRow]:
    lines = _executable_lines(content)
    rows: list[SourceMapRow] = []
    in_source_map = False
    table_headers: Optional[list[str]] = None
    for line_number, line in lines:
        stripped = line.strip()
        if SOURCE_MAP_HEADING_RE.match(stripped):
            in_source_map = True
            table_headers = None
            continue
        if in_source_map and (
            ANY_HEADING_RE.match(stripped)
            or SIDECAR_SECTION_HEADING_RE.match(stripped)
        ):
            in_source_map = False
            table_headers = None
        if not in_source_map:
            continue
        match = ROW_RE.match(line)
        if match:
            fields: dict[str, str] = {}
            for segment in match.group("body").split("|"):
                if ":" not in segment:
                    continue
                key, value = segment.split(":", 1)
                fields[_normalize_field(key)] = value.strip().strip('"').strip("'")
            rows.append(SourceMapRow(line=line_number, fields=fields))
            continue

        table_cells = _table_cells(line)
        if table_cells is None:
            continue
        if table_headers is None:
            normalized_headers = [_normalize_field(cell) for cell in table_cells]
            if "claim" in normalized_headers:
                table_headers = normalized_headers
            continue
        if all(re.fullmatch(r":?-{3,}:?", cell.strip()) for cell in table_cells):
            continue
        if not any(cell.strip() for cell in table_cells):
            continue
        fields = {
            header: table_cells[index].strip().strip('"').strip("'")
            if index < len(table_cells)
            else ""
            for index, header in enumerate(table_headers)
        }
        rows.append(SourceMapRow(line=line_number, fields=fields))
    return rows


def _table_cells(line: str) -> Optional[list[str]]:
    stripped = line.strip()
    if not stripped.startswith("|") or not stripped.endswith("|"):
        return None
    return [cell.strip() for cell in stripped[1:-1].split("|")]


def _has_stricter_proof_route(content: str, claim_type: str) -> bool:
    required_groups = STRICTER_PROOF_SECTIONS.get(claim_type, ())
    for alternatives in required_groups:
        if not any(_has_heading(content, heading) for heading in alternatives):
            return False
    return bool(required_groups)


def _has_heading(content: str, heading: str) -> bool:
    pattern = re.compile(
        rf"^\s*(?:#{{1,6}}\s+)?{re.escape(heading)}:?\s*$",
        re.IGNORECASE,
    )
    return any(pattern.match(line.strip()) for _, line in _executable_lines(content))


def _faq_proof_urls(content: str) -> set[str]:
    lines = _executable_lines(content)
    urls: set[str] = set()
    in_map = False
    for _, line in lines:
        stripped = line.strip()
        if FAQ_MAP_HEADING_RE.match(stripped):
            in_map = True
            continue
        if in_map and (
            ANY_HEADING_RE.match(stripped)
            or SIDECAR_SECTION_HEADING_RE.match(stripped)
        ):
            in_map = False
        if not in_map:
            continue
        match = URL_FIELD_RE.search(line)
        if match:
            urls.add(match.group("url").rstrip(".,;"))
    return urls


def _date_findings(row: SourceMapRow, *, today: date) -> list[Finding]:
    findings: list[Finding] = []
    source_date = row.fields.get("source date", "")
    checked_date = row.fields.get("checked date", "")
    if source_date.casefold() not in {"undated", "historical"}:
        try:
            parsed_source = date.fromisoformat(source_date)
            if parsed_source > today:
                findings.append(_finding("source_quality_source_date_future", row.line, "Source date cannot be in the future."))
        except ValueError:
            findings.append(_finding("source_quality_source_date_invalid", row.line, "Source date must use YYYY-MM-DD, undated, or historical."))
    try:
        parsed_checked = date.fromisoformat(checked_date)
        if parsed_checked > today:
            findings.append(_finding("source_quality_checked_date_future", row.line, "Checked date cannot be in the future."))
    except ValueError:
        findings.append(_finding("source_quality_checked_date_invalid", row.line, "Checked date must use YYYY-MM-DD."))
    return findings


def _normalize_field(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip().replace("**", "").casefold())


def _normalize(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.casefold()).strip()


def _requires_lifecycle_contract(content: str, proof_content: str) -> bool:
    brand = extract_frontmatter(content).get("brand", "").strip()
    if brand.casefold() == "simpro":
        return True
    if "simprogroup.com" in content.casefold():
        return True
    headings = {
        "search intent and format decision",
        "commercial pillar and anchor decision",
        "lifecycle refresh record",
    }
    return any(
        HEADING_RE.match(line) and HEADING_RE.match(line).group("title").strip().rstrip(":").casefold() in headings
        for _, line in _executable_lines(proof_content)
    )


def _is_high_volatility_topic(content: str, contract: BlogStrategyContract) -> bool:
    frontmatter = extract_frontmatter(content)
    body, _ = strip_frontmatter(content)
    h1_match = H1_RE.search(body)
    text = " ".join(
        value
        for value in (
            frontmatter.get("title", ""),
            frontmatter.get("primary_keyword", ""),
            frontmatter.get("target_keyword", ""),
            h1_match.group("title") if h1_match else "",
            contract.commercial_pillar.article_title,
            contract.commercial_pillar.article_primary_keyword,
        )
        if value
    )
    return bool(HIGH_VOLATILITY_TOPIC_RE.search(text))


def _executable_lines(content: str) -> list[tuple[int, str]]:
    lines: list[tuple[int, str]] = []
    in_fence = False
    in_comment = False
    for line_number, line in enumerate(content.splitlines(), start=1):
        if FENCE_RE.match(line):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        visible, in_comment = _strip_comments(line, in_comment=in_comment)
        if visible or not line.strip():
            lines.append((line_number, visible))
    return lines


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


def _finding(rule_id: str, line: int, message: str) -> Finding:
    return make_finding(
        rule_id,
        "error",
        line,
        message=message,
        suggestion="Correct the Source Map or lifecycle record with direct, current, claim-fit evidence; do not bypass stricter proof gates.",
    )


def _sort_findings(findings: list[Finding]) -> list[Finding]:
    return sorted(findings, key=lambda finding: (int(finding["line"]), str(finding["rule_id"])))


def _main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Validate Source Map quality and lifecycle scheduling.")
    parser.add_argument("path")
    parser.add_argument("--proof-sidecar", required=True)
    parser.add_argument("--fail-on", choices=["error", "warning", "none"], default="error")
    args = parser.parse_args(argv)
    findings = check_file(args.path, proof_sidecar=args.proof_sidecar, fail_on=args.fail_on)
    payload = {"path": args.path, "summary": summarize_findings(findings), "findings": findings}
    print(json.dumps(payload, indent=2))
    return 1 if should_fail(findings, fail_on=args.fail_on) else 0


if __name__ == "__main__":
    sys.exit(_main())
