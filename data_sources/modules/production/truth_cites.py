"""Citation grading and the paragraph-bound number rule.

A material number (percent, currency, multiplier, ratio, or 11 and up) must appear in a BOM
fact quote or BOM proof item whose URL is linked inside the same paragraph. Keyword-only
citation requirements from the proof-link policy are graded: only an unverified evidence
URL, or customer proof with no BOM proof link, blocks.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Sequence
from typing import Any
from urllib.parse import urlsplit

from data_sources.modules.production.truth_index import BomIndex, canonical
from data_sources.modules.production.truth_numbers import material_numbers
from data_sources.modules.production.truth_text import Finding, Unit
from data_sources.modules.proof_link_policy import CitationRequirement

CITING_MODES = frozenset({"inline_required", "section_source_allowed"})
_PROOF_OWNERS = frozenset({"customer_proof", "review_story"})
_OUTSIDE = "claim cites a source outside the production BOM"
_STORY_PATH = re.compile(r"/(?:case-stud|customers/|customer-stor|testimonial|success-stor)", re.IGNORECASE)
_REVIEW_HOST = re.compile(
    r"(?:^|\.)(?:g2\.com|(?:capterra|trustpilot|getapp|softwareadvice)\.[a-z.]+)$", re.IGNORECASE
)


def _is_customer_story(url: str) -> bool:
    parts = urlsplit(url)
    return _STORY_PATH.search(parts.path) is not None or _REVIEW_HOST.search(parts.hostname or "") is not None


def linked_urls(links: Iterable[Any], first: int, last: int) -> frozenset[str]:
    """Canonical URLs of the article's own links on lines ``first`` to ``last``."""
    return frozenset(canonical(link.url) for link in links if first <= link.line <= last)


def _requirement_finding(
    requirement: CitationRequirement, urls: frozenset[str], evidence: frozenset[str], index: BomIndex
) -> Finding | None:
    where = f"{requirement.claim}"
    if requirement.owner in _PROOF_OWNERS:
        if urls & frozenset(index.proof_by_url):
            return None
        return Finding("citation_source", "block",
                       f"{_OUTSIDE}: no BOM proof URL is linked for this customer or review claim: {where}",
                       requirement.line)
    outside = sorted(evidence - index.known_urls)
    if outside:
        return Finding("citation_source", "block", f"{_OUTSIDE}: {', '.join(outside)}: {where}", requirement.line)
    if urls & index.source_urls:
        return None
    return Finding("citation_source", "warn",
                   f"claim links no production BOM fact or proof source: {where}", requirement.line)


def citation_findings(
    requirements: Sequence[CitationRequirement], report_links: Iterable[Any], links: Sequence[Any], index: BomIndex
) -> list[Finding]:
    """Grade each citing requirement; return one finding per requirement that is not satisfied."""
    findings = []
    for requirement in requirements:
        if requirement.mode not in CITING_MODES:
            continue
        urls = linked_urls(links, requirement.line, requirement.end_line)
        evidence = frozenset(
            link.canonical_url for link in report_links
            if link.external and requirement.line <= link.line <= requirement.end_line
        )
        finding = _requirement_finding(requirement, urls, evidence, index)
        if finding:
            findings.append(finding)
    return findings


def _missing_message(missing: dict[str, str], index: BomIndex) -> str:
    parts = []
    for canonical_number, written in sorted(missing.items(), key=lambda item: float(item[0])):
        holder = index.holder_of(canonical_number)
        elsewhere = f"found in BOM {holder}, which is not linked in this paragraph" if holder else "in no BOM source"
        parts.append(f"{canonical_number} ({written.strip()}: {elsewhere})")
    return "numbers not supported by the BOM sources linked in this paragraph: " + "; ".join(parts)


def _heading_urls(units: Sequence[Unit], position: int, links: Sequence[Any]) -> frozenset[str]:
    """URLs linked in a heading plus those linked in the next content unit below it."""
    unit = units[position]
    urls = linked_urls(links, unit.line, unit.end_line)
    following = next((later for later in units[position + 1 :] if not later.heading), None)
    return urls | (linked_urls(links, following.line, following.end_line) if following else frozenset())


def _unsupported(
    lines: Sequence[str], urls: frozenset[str], index: BomIndex, listicle: int
) -> dict[str, str]:
    needed = material_numbers(lines, index.year, listicle)
    supplied = index.numbers_for(urls)
    return {number: written for number, written in needed.items() if number not in supplied}


def paragraph_number_findings(
    units: Sequence[Unit], links: Sequence[Any], index: BomIndex, meta: Sequence[tuple[int, str]] = (),
    listicle: int = 0,
) -> list[Finding]:
    """Block material numbers that no BOM source linked where the number sits supplies.

    Paragraphs, list items, table rows, and FAQ answers use their own links; a heading also
    uses the next content unit's links; the title and meta fields use any link in the body.
    """
    findings = []
    for position, unit in enumerate(units):
        urls = _heading_urls(units, position, links) if unit.heading else linked_urls(links, unit.line, unit.end_line)
        missing = _unsupported(unit.text, urls, index, listicle)
        if missing:
            findings.append(Finding("claim_numbers", "block", _missing_message(missing, index), unit.line))
    everywhere = linked_urls(links, 1, 10**9)
    for number, text in meta:
        missing = _unsupported([text], everywhere, index, listicle)
        if missing:
            findings.append(Finding("claim_numbers", "block", _missing_message(missing, index), number))
    return findings


def customer_story_findings(links: Sequence[Any], index: BomIndex) -> list[Finding]:
    """Block a customer-story or review-site link that is not a BOM proof or fact URL."""
    findings, seen = [], set()
    for link in links:
        url = canonical(link.url)
        if url in index.source_urls or (url, link.line) in seen or not _is_customer_story(url):
            continue
        seen.add((url, link.line))
        findings.append(Finding(
            "citation_source", "block",
            f"{_OUTSIDE}: customer story or review link is not a BOM proof or fact URL: {url}", link.line,
        ))
    return findings
