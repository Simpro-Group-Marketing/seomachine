"""Lifecycle policy evaluation for source-quality governance."""

from __future__ import annotations

import re
from datetime import date
from typing import Any, Callable

try:
    from .artifact_detection import extract_frontmatter, strip_frontmatter
    from .blog_strategy_contract import BlogStrategyContract
    from .guard_common import Finding
except ImportError:  # pragma: no cover - direct script execution.
    from artifact_detection import extract_frontmatter, strip_frontmatter
    from blog_strategy_contract import BlogStrategyContract
    from guard_common import Finding


DATED_EVIDENCE_RE = re.compile(r"\b\d{4}-\d{2}-\d{2}\b")
PERFORMANCE_CLAIM_RE = re.compile(
    r"\b(?:improv(?:e|ed|ement)|increase[sd]?|decrease[sd]?|lift(?:ed)?|"
    r"grew|growth|gain(?:ed)?|outperform(?:ed)?|(?:traffic|clicks?|sessions?|"
    r"impressions?|rankings?|positions?).{0,50}?\b(?:up|down|rose|jump(?:ed)?|"
    r"grew|fell|dropped|increased|decreased|improved))\b",
    re.IGNORECASE,
)
URL_RE = re.compile(r"https?://\S+", re.IGNORECASE)
H1_RE = re.compile(r"^\s{0,3}#(?!#)\s+(?P<title>.+?)\s*#*\s*$", re.MULTILINE)
HIGH_VOLATILITY_TOPIC_RE = re.compile(
    r"\b(?:pricing|price|prices|cost|costs|regulation|standard|comparison|"
    r"compare|vs|statistics?|stats?|product status)\b",
    re.IGNORECASE,
)


def findings(
    content: str,
    proof_content: str,
    contract: BlogStrategyContract,
    *,
    today: date,
    source_rows: Callable[[str], list[Any]],
    finding: Callable[[str, int, str], Finding],
    normalize: Callable[[str], str],
    high_volatility_types: set[str],
) -> list[Finding]:
    """Evaluate lifecycle dates, volatility, evidence lanes, and cadence."""
    results: list[Finding] = []
    lifecycle = contract.lifecycle
    frontmatter = extract_frontmatter(content)
    article_updated = (
        frontmatter.get("last_updated") or frontmatter.get("last_update") or ""
    ).strip()
    try:
        last_updated = date.fromisoformat(lifecycle.last_updated_date)
        next_review = date.fromisoformat(lifecycle.next_review_date)
    except ValueError:
        return [finding("lifecycle_date_invalid", 1, "Lifecycle dates must use YYYY-MM-DD.")]
    rows = source_rows(proof_content)
    high_volatility = any(
        row.claim_type in high_volatility_types for row in rows
    ) or is_high_volatility_topic(content, contract)
    results.extend(
        _schedule_findings(
            article_updated=article_updated,
            lifecycle=lifecycle,
            last_updated=last_updated,
            next_review=next_review,
            today=today,
            high_volatility=high_volatility,
            finding=finding,
        )
    )
    results.extend(_lane_findings(lifecycle, finding=finding, normalize=normalize))
    if PERFORMANCE_CLAIM_RE.search(lifecycle.decision) and not (
        DATED_EVIDENCE_RE.search(lifecycle.decision)
        and URL_RE.search(lifecycle.decision)
    ):
        results.append(
            finding(
                "lifecycle_performance_claim_unproved",
                1,
                "Lifecycle decision claims performance change without dated source evidence.",
            )
        )
    return results


def _schedule_findings(
    *,
    article_updated: str,
    lifecycle: Any,
    last_updated: date,
    next_review: date,
    today: date,
    high_volatility: bool,
    finding: Callable[[str, int, str], Finding],
) -> list[Finding]:
    results: list[Finding] = []
    if article_updated and article_updated != lifecycle.last_updated_date:
        results.append(finding("lifecycle_article_date_mismatch", 1, "Lifecycle Last-updated date does not match article frontmatter."))
    if next_review <= last_updated:
        results.append(finding("lifecycle_next_review_not_after_update", 1, "Next review date must be after Last-updated date."))
    if next_review < today:
        results.append(finding("lifecycle_next_review_overdue", 1, "Next review date is already overdue."))
    if high_volatility and lifecycle.volatility != "high":
        results.append(finding("lifecycle_high_volatility_required", 1, "Pricing, regulation, product-status, comparison, standards, and statistics-led articles require high volatility."))
    allowed_days = 90 if high_volatility or lifecycle.volatility == "high" else 180
    if (next_review - last_updated).days > allowed_days:
        results.append(finding("lifecycle_review_cadence_exceeded", 1, f"Next review exceeds the {allowed_days}-day lifecycle cadence."))
    return results


def _lane_findings(
    lifecycle: Any,
    *,
    finding: Callable[[str, int, str], Finding],
    normalize: Callable[[str], str],
) -> list[Finding]:
    lane_values = {
        "GSC lane": lifecycle.gsc_lane,
        "GA4 lane": lifecycle.ga4_lane,
        "Semrush lane": lifecycle.semrush_lane,
        "AI-citation lane": lifecycle.ai_citation_lane,
    }
    results: list[Finding] = []
    for lane_name, value in lane_values.items():
        results.extend(_single_lane_findings(lane_name, value, finding, normalize))
    return results


def _single_lane_findings(
    lane_name: str,
    value: str,
    finding: Callable[[str, int, str], Finding],
    normalize: Callable[[str], str],
) -> list[Finding]:
    results: list[Finding] = []
    if PERFORMANCE_CLAIM_RE.search(value) and not (DATED_EVIDENCE_RE.search(value) and URL_RE.search(value)):
        results.append(finding("lifecycle_performance_claim_unproved", 1, f"{lane_name} claims performance change without dated source evidence."))
    if ":" not in value:
        results.append(finding("lifecycle_lane_reason_missing", 1, f"{lane_name} requires status: reason."))
        if normalize(value) in {"0", "zero"}:
            results.append(finding("lifecycle_lane_status_invalid", 1, f"{lane_name} cannot use zero as a data-availability status."))
        return results
    status, reason = (part.strip() for part in value.split(":", 1))
    if status.casefold() not in {"available", "unavailable", "not_applicable"}:
        results.append(finding("lifecycle_lane_status_invalid", 1, f"{lane_name} has unsupported availability status: {status}."))
    if not reason:
        results.append(finding("lifecycle_lane_reason_missing", 1, f"{lane_name} requires a non-empty reason."))
    if status.casefold() == "unavailable" and re.search(r"\b(?:0|zero)\b", reason, re.IGNORECASE):
        results.append(finding("lifecycle_unavailable_as_zero", 1, f"{lane_name} converts unavailable data into zero."))
    return results


def requires_contract(content: str, proof_content: str) -> bool:
    brand = extract_frontmatter(content).get("brand", "").strip()
    if brand.casefold() == "simpro" or "simprogroup.com" in content.casefold():
        return True
    headings = {
        "search intent and format decision",
        "commercial pillar and anchor decision",
        "lifecycle refresh record",
    }
    heading_re = re.compile(r"^\s*#{1,6}\s+(?P<title>.*?)\s*$")
    return any(
        match
        and match.group("title").strip().rstrip(":").casefold() in headings
        for line in proof_content.splitlines()
        if (match := heading_re.match(line))
    )


def is_high_volatility_topic(
    content: str,
    contract: BlogStrategyContract,
) -> bool:
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
