"""Batch verification of research-fact quotes against live source pages."""

from __future__ import annotations

import re
from dataclasses import dataclass
from collections.abc import Mapping
from typing import Any, Dict, Sequence, Tuple

import requests

from data_sources.modules.production.page_capture import PageCapture
from data_sources.modules.source_support.retrieval import fetch_source_text_many
from data_sources.modules.source_support.text_matching import _normalize_text

_GONE_STATUSES = frozenset({404, 410})
# A Chrome capture may stand in only when the page refused or could not answer an automated client.
_CAPTURE_STATUSES = frozenset({403, 429, 503})
_CAPTURE_ERRORS = (requests.Timeout, requests.ConnectionError, TimeoutError, ConnectionError)
_THOUSANDS_COMMA = re.compile(r"(?<=\d),(?=\d{3}(?!\d))")
_DECIMAL_POINT = re.compile(r"(?<=\d)\.(?=\d)")


@dataclass(frozen=True)
class FactCheck:
    url: str
    status: str  # "verified" | "verified_capture" | "quote_missing" | "gone" | "unreachable"
    detail: str


def verify_quotes(
    pairs: Sequence[Tuple[str, str]],
    *,
    transport: Any,
    captures: Mapping[str, PageCapture] | None = None,
) -> Dict[Tuple[str, str], FactCheck]:
    """Check each (url, quote) pair against its live page with one batch fetch.

    A Chrome capture for the exact URL answers only when the live fetch was blocked (HTTP 403, 429, or
    503, or a timeout or connection error); it never overrides a gone, reachable, or quote-missing
    page, nor a 401, 451, other 4xx, or 500/502 answer.
    """
    pairs = list(pairs)
    outcomes = _fetch_outcomes([url for url, _quote in pairs], transport=transport)
    checks = {(url, quote): _check(url, quote, outcomes[url]) for url, quote in pairs}
    for (url, quote), check in checks.items():
        capture = (captures or {}).get(url)
        if capture is not None and check.status == "unreachable" and _is_blocked(outcomes[url]):
            checks[(url, quote)] = _check_capture(url, quote, capture)
    return checks


def _is_blocked(outcome: Any) -> bool:
    if isinstance(outcome, requests.HTTPError):
        return getattr(outcome.response, "status_code", None) in _CAPTURE_STATUSES
    return isinstance(outcome, _CAPTURE_ERRORS)


def _check_capture(url: str, quote: str, capture: PageCapture) -> FactCheck:
    match = _match_quote(url, quote, capture.text)
    where = f"Chrome capture {capture.path}"
    if match.status == "verified":
        return FactCheck(url, "verified_capture", f"quote found in {where} (captured {capture.captured_at})")
    return FactCheck(url, "quote_missing", f"quote not found in {where} (captured {capture.captured_at})")


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
    needle = _normalize_text(_keep_numbers_whole(quote))
    if not needle:
        return FactCheck(url, "quote_missing", "quote has no verifiable text")
    if f" {needle} " in f" {_normalize_text(_keep_numbers_whole(page_text))} ":
        return FactCheck(url, "verified", "quote found on page")
    return FactCheck(url, "quote_missing", "quote not found on page")


def _keep_numbers_whole(text: str) -> str:
    """Join digit groups so "1,500" and "12.5" stay single tokens for boundary matching."""
    text = _THOUSANDS_COMMA.sub("", text)
    return _DECIMAL_POINT.sub("p", text)


__all__ = ["FactCheck", "verify_quotes"]
