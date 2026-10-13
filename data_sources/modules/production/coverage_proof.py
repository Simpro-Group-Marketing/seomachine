"""Proof coverage: a BOM proof item is used when its URL is linked, and its quote or number is present."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from data_sources.modules.production.coverage_base import items, missing
from data_sources.modules.production.coverage_view import ArticleView
from data_sources.modules.production.numbers import extract_numbers
from data_sources.modules.production.truth_index import canonical
from data_sources.modules.production.truth_quotes import normalize_passage
from data_sources.modules.production.truth_text import Finding


def _quote_texts(item: Mapping[str, Any]) -> list[str]:
    """The approved quotes, or the proof text for a connector exact_quote item with none."""
    approved = [
        str(quote.get("quote") if isinstance(quote, Mapping) else quote)
        for quote in item.get("approved_quotes") or []
    ]
    return [text for text in approved or [str(item.get("text") or "")] if text.strip()]


def _quote_present(view: ArticleView, item: Mapping[str, Any]) -> bool:
    prose = view.prose()
    return any(normalize_passage(text) in prose for text in _quote_texts(item))


def _metric_present(view: ArticleView, item: Mapping[str, Any], url: str) -> bool:
    wanted = extract_numbers(str(item.get("text") or ""))
    if not wanted:
        return True
    return any(wanted & extract_numbers(paragraph) for paragraph in view.paragraphs_linking(url))


def _gap(view: ArticleView, item: Mapping[str, Any]) -> str:
    """Return what is missing for ``item``, or an empty string when the article uses it."""
    url = canonical(str(item.get("url", "")))
    if url not in view.linked:
        return f"link {item.get('url')} where the article uses it"
    kind = item.get("kind")
    if kind == "quote" and not _quote_present(view, item):
        return "quote it verbatim from its approved quote text"
    if kind == "metric" and not _metric_present(view, item, url):
        return f"state a number from its proof text in the paragraph that links {item.get('url')}"
    return ""


def proof_findings(view: ArticleView, bom: Mapping[str, Any]) -> list[Finding]:
    findings = []
    for item in items(bom, "proof"):
        gap = _gap(view, item)
        if gap:
            findings.append(missing(item, "coverage_proof", f"BOM proof {item.get('id')} is not used: {gap}"))
    return findings
