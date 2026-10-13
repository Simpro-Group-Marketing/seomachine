"""Batch verification of research-fact quotes against live source pages."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Sequence, Tuple

import requests

from data_sources.modules.source_support.retrieval import fetch_source_text_many
from data_sources.modules.source_support.text_matching import _normalize_text

_GONE_STATUSES = frozenset({404, 410})


@dataclass(frozen=True)
class FactCheck:
    url: str
    status: str  # "verified" | "quote_missing" | "gone" | "unreachable"
    detail: str


def verify_quotes(
    pairs: Sequence[Tuple[str, str]],
    *,
    transport: Any,
) -> Dict[Tuple[str, str], FactCheck]:
    """Check each (url, quote) pair against its live page with one batch fetch."""
    pairs = list(pairs)
    outcomes = _fetch_outcomes([url for url, _quote in pairs], transport=transport)
    return {(url, quote): _check(url, quote, outcomes[url]) for url, quote in pairs}


def _fetch_outcomes(urls: Sequence[str], *, transport: Any) -> Dict[str, Any]:
    """Fetch in one batch; if the batch raised for a non-HTTP reason, retry each failing URL alone."""
    outcomes = fetch_source_text_many(urls, transport=transport)
    unique = list(dict.fromkeys(urls))
    if len(unique) > 1:
        for url in unique:
            if _is_isolated_failure(outcomes[url]):
                outcomes[url] = fetch_source_text_many([url], transport=transport)[url]
    return outcomes


def _is_isolated_failure(outcome: Any) -> bool:
    return isinstance(outcome, Exception) and not isinstance(outcome, requests.HTTPError)


def _check(url: str, quote: str, outcome: Any) -> FactCheck:
    if isinstance(outcome, requests.HTTPError):
        status = getattr(outcome.response, "status_code", None)
        if status in _GONE_STATUSES:
            return FactCheck(url, "gone", f"HTTP {status}")
        return FactCheck(url, "unreachable", f"HTTP {status}")
    if isinstance(outcome, Exception):
        return FactCheck(url, "unreachable", f"{type(outcome).__name__}: {outcome}")
    return _match_quote(url, quote, outcome)


def _match_quote(url: str, quote: str, page_text: str) -> FactCheck:
    needle = _normalize_text(quote)
    if not needle:
        return FactCheck(url, "quote_missing", "quote has no verifiable text")
    if f" {needle} " in f" {_normalize_text(page_text)} ":
        return FactCheck(url, "verified", "quote found on page")
    return FactCheck(url, "quote_missing", "quote not found on page")


__all__ = ["FactCheck", "verify_quotes"]
