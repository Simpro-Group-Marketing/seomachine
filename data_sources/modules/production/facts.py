"""Batch verification of research-fact quotes against live source pages."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Sequence, Tuple

import requests

from data_sources.modules.source_support.retrieval import fetch_source_text_many
from data_sources.modules.source_support.text_matching import _contains_evidence

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
    texts = fetch_source_text_many([url for url, _quote in pairs], transport=transport)
    return {(url, quote): _check(url, quote, texts[url]) for url, quote in pairs}


def _check(url: str, quote: str, outcome: Any) -> FactCheck:
    if isinstance(outcome, requests.HTTPError):
        status = getattr(outcome.response, "status_code", None)
        if status in _GONE_STATUSES:
            return FactCheck(url, "gone", f"HTTP {status}")
        return FactCheck(url, "unreachable", f"HTTP {status}")
    if isinstance(outcome, Exception):
        return FactCheck(url, "unreachable", f"{type(outcome).__name__}: {outcome}")
    if _contains_evidence(outcome, quote):
        return FactCheck(url, "verified", "quote found on page")
    return FactCheck(url, "quote_missing", "quote not found on page")


__all__ = ["FactCheck", "verify_quotes"]
