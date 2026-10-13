"""Coverage checks: the finished article delivers what the production BOM marked must or should.

A ``must`` item that the article leaves out blocks; a ``should`` item warns. Coverage checks
presence only. Whether a number, quote, or FAQ question is allowed is the truth layer's job.
No network is used.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from typing import Any

from data_sources.modules.production.coverage_base import items, missing
from data_sources.modules.production.coverage_proof import proof_findings
from data_sources.modules.production.coverage_view import (
    ArticleView,
    anchor_key,
    contains_phrase,
    content_tokens,
)
from data_sources.modules.production.serp_coverage import normalize_heading
from data_sources.modules.production.truth_index import canonical, question_key
from data_sources.modules.production.truth_text import Finding


def _section_present(heading: str, present: Sequence[str]) -> bool:
    wanted, tokens = normalize_heading(heading), content_tokens(heading)
    return any(
        normalize_heading(found) == wanted or (bool(tokens) and tokens <= content_tokens(found)) for found in present
    )


def _section_findings(view: ArticleView, bom: Mapping[str, Any]) -> list[Finding]:
    present = view.section_headings()
    return [
        missing(
            section, "coverage_section",
            f"BOM section is missing from the article (add an H2 or H3): {section.get('heading')!r}",
        )
        for section in items(bom, "sections")
        if not _section_present(str(section.get("heading", "")), present)
    ]


def _fact_findings(view: ArticleView, bom: Mapping[str, Any]) -> list[Finding]:
    linked = view.linked
    return [
        missing(
            fact, "coverage_fact",
            f"BOM fact {fact.get('id')} is not cited: link {fact.get('url')} where the article uses it",
        )
        for fact in items(bom, "facts")
        if canonical(str(fact.get("url", ""))) not in linked
    ]


def _paa_findings(view: ArticleView, bom: Mapping[str, Any]) -> list[Finding]:
    paa = bom.get("paa")
    asked = paa.get("questions") if isinstance(paa, Mapping) else None
    return [
        missing(
            item, "coverage_paa", f"BOM PAA question is missing from the FAQ: {item.get('question')!r}"
        )
        for item in asked or []
        if isinstance(item, Mapping) and question_key(str(item.get("question", ""))) not in view.faq_keys
    ]


def _pillar_finding(view: ArticleView, link: Mapping[str, Any]) -> Finding | None:
    url, anchor = canonical(str(link.get("url", ""))), str(link.get("anchor", ""))
    found = [body for body in view.links if canonical(body.url) == url]
    if not found:
        return Finding("coverage_pillar", "block", f"commercial pillar link missing: {link.get('url')}", None)
    if any(anchor_key(body.anchor) == anchor_key(anchor) for body in found):
        return None
    anchors = ", ".join(repr(body.anchor) for body in found)
    return Finding(
        "coverage_pillar", "block",
        f"commercial pillar anchor differs for {link.get('url')}: planned {anchor!r}, article uses {anchors}",
        found[0].line,
    )


def _link_findings(view: ArticleView, bom: Mapping[str, Any]) -> list[Finding]:
    findings: list[Finding] = []
    for link in items(bom, "links"):
        if link.get("kind") == "commercial_pillar":
            finding = _pillar_finding(view, link)
        elif canonical(str(link.get("url", ""))) in view.linked:
            continue
        else:
            finding = missing(link, "coverage_link", f"BOM link is missing from the article: {link.get('url')}")
        if finding:
            findings.append(finding)
    return findings


def _keyword_findings(view: ArticleView, bom: Mapping[str, Any]) -> list[Finding]:
    keyword = bom.get("keyword")
    primary = str(keyword.get("primary") or "").strip() if isinstance(keyword, Mapping) else ""
    if not primary:
        return []
    places: list[tuple[str, bool]] = [
        ("title", contains_phrase(view.title, primary)),
        ("H1", any(contains_phrase(text, primary) for text in view.h1_headings())),
        ("first 100 words", contains_phrase(view.lead_text(), primary)),
    ]
    return [
        Finding("coverage_keyword", "block", f"primary keyword {primary!r} is missing from the {place}", None)
        for place, found in places
        if not found
    ]


_CHECKS: tuple[Callable[[ArticleView, Mapping[str, Any]], list[Finding]], ...] = (
    _section_findings, _fact_findings, proof_findings, _paa_findings, _link_findings, _keyword_findings,
)


def check_coverage(article: str, bom: Mapping[str, Any]) -> list[Finding]:
    """Check a finished article against the must and should items of its production BOM."""
    view = ArticleView.build(article)
    return [finding for check in _CHECKS for finding in check(view, bom)]


__all__ = ["Finding", "check_coverage"]
