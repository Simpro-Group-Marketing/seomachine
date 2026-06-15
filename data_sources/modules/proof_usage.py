"""
Shared customer proof usage counting.

The selector and diversity guard both need the same reuse semantics:
count unique article slugs for overuse thresholds, keep raw occurrence counts
for diagnostics, and allow editorial overuse baselines to preserve known
historical overuse after stale artifact rows are cleaned up.
"""

from __future__ import annotations

import re
from datetime import date, datetime
from typing import Any, Dict, Iterable, Optional


FindingDict = Dict[str, Any]


def count_customer_proof_usage(
    ledger: FindingDict,
    *,
    proof_id: str = "",
    source_url: str = "",
    customer: str = "",
    reference_date: Optional[date] = None,
) -> FindingDict:
    """Return effective and raw reuse counts for one proof source."""
    reference = reference_date or date.today()
    normalized_proof_id = str(proof_id or _proof_id_from_url(source_url)).strip()
    normalized_url = str(source_url or "").strip()
    normalized_customer = _normalize_text(str(customer or ""))

    total_occurrences = 0
    recent_occurrences = 0
    unique_articles: set[str] = set()
    recent_articles: set[str] = set()

    for usage in ledger.get("uses", []) or []:
        if not isinstance(usage, dict):
            continue
        if not _matches_usage(
            usage,
            proof_id=normalized_proof_id,
            source_url=normalized_url,
            customer=normalized_customer,
        ):
            continue
        total_occurrences += 1
        article_slug = str(usage.get("article_slug", "")).strip() or str(usage.get("artifact_path", "")).strip()
        if article_slug:
            unique_articles.add(article_slug)
        used_on = _parse_date(str(usage.get("date_used", "")))
        if used_on is None:
            continue
        age = (reference - used_on).days
        if 0 <= age <= 90:
            recent_occurrences += 1
            if article_slug:
                recent_articles.add(article_slug)

    counted_total = len(unique_articles) or total_occurrences
    counted_recent = len(recent_articles) or recent_occurrences
    baseline = _matching_baseline(
        ledger.get("overuse_baselines", []),
        proof_id=normalized_proof_id,
        source_url=normalized_url,
        customer=normalized_customer,
    )
    baseline_recent = _safe_int(baseline.get("recent_uses_90d", 0)) if baseline else 0
    baseline_total = _safe_int(baseline.get("total_uses", baseline_recent)) if baseline else 0
    effective_total = max(counted_total, baseline_total)
    effective_recent = max(counted_recent, baseline_recent)

    return {
        "total_uses": effective_total,
        "recent_uses_90d": effective_recent,
        "total_occurrences": total_occurrences,
        "recent_occurrences_90d": recent_occurrences,
        "baseline_total_uses": baseline_total,
        "baseline_recent_uses_90d": baseline_recent,
        "overused": effective_recent >= 3,
    }


def proof_id_from_url(url: str) -> str:
    """Return the conventional proof ID for a public proof URL."""
    return _proof_id_from_url(url)


def usage_matches_candidate(candidate: FindingDict, usage: FindingDict) -> bool:
    """Return True when a ledger row points at the candidate proof."""
    return _matches_usage(
        usage,
        proof_id=str(candidate.get("proof_id", "")).strip(),
        source_url=str(candidate.get("public_url", "")).strip(),
        customer=_normalize_text(str(candidate.get("customer", ""))),
    )


def _matching_baseline(
    baselines: Any,
    *,
    proof_id: str,
    source_url: str,
    customer: str,
) -> FindingDict:
    for baseline in _iter_baselines(baselines):
        if not isinstance(baseline, dict):
            continue
        if _matches_usage(
            baseline,
            proof_id=proof_id,
            source_url=source_url,
            customer=customer,
            url_keys=("source_url", "public_url", "url"),
        ):
            return baseline
    return {}


def _iter_baselines(baselines: Any) -> Iterable[FindingDict]:
    if isinstance(baselines, dict):
        for key, value in baselines.items():
            if isinstance(value, dict):
                merged = dict(value)
                merged.setdefault("proof_id", key)
                yield merged
        return
    if isinstance(baselines, list):
        for baseline in baselines:
            if isinstance(baseline, dict):
                yield baseline


def _matches_usage(
    usage: FindingDict,
    *,
    proof_id: str,
    source_url: str,
    customer: str,
    url_keys: tuple[str, ...] = ("source_url", "public_url", "url"),
) -> bool:
    usage_proof_id = str(usage.get("proof_id", "")).strip()
    if proof_id and usage_proof_id == proof_id:
        return True
    usage_urls = {str(usage.get(key, "")).strip() for key in url_keys}
    if source_url and source_url in usage_urls:
        return True
    if source_url:
        source_slug = _proof_id_from_url(source_url)
        if source_slug and usage_proof_id == source_slug:
            return True
    usage_customer = _normalize_text(str(usage.get("customer", "")))
    return bool(customer and usage_customer and customer == usage_customer)


def _proof_id_from_url(url: str) -> str:
    if not url:
        return ""
    slug = url.rstrip("/").rsplit("/", 1)[-1]
    if "/case-studies/" in url:
        return f"case-study-{slug}"
    return slug


def _parse_date(value: str) -> Optional[date]:
    if not value:
        return None
    try:
        return datetime.strptime(value[:10], "%Y-%m-%d").date()
    except ValueError:
        return None


def _normalize_text(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()


def _safe_int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0
