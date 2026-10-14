"""Truth checks: block any fact, number, quote, or FAQ question that is not in the production BOM.

The BOM facts were verified on their live pages and the BOM proof items are approved claims, so
they are the only admitted sources. Everything here runs against a finished article. Network
work is two batch operations on one transport: ``verify_quotes`` once for every linked fact, and
the URL validator once for every article link.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from data_sources.modules.ai_copy_lint.core import lint_content
from data_sources.modules.faq_structure import detect_faq_structure
from data_sources.modules.production.facts import verify_quotes
from data_sources.modules.production.page_capture import PageCapture, load_capture
from data_sources.modules.production.truth_cites import (
    citation_findings,
    customer_story_findings,
    linked_urls,
    paragraph_number_findings,
)
from data_sources.modules.production.truth_faq import answer_ranges, faq_findings, section_ranges
from data_sources.modules.production.truth_index import BomIndex, canonical
from data_sources.modules.production.truth_numbers import ListicleScope, number_gate
from data_sources.modules.production.truth_quotes import quoted_passage_findings
from data_sources.modules.production.truth_text import (
    Finding,
    body_lines,
    h3_count,
    heading_lines,
    link_anchors,
    meta_lines,
    paragraph_units,
    public_copy_lines,
)
from data_sources.modules.proof_link_policy import analyze_proof_links
from data_sources.modules.public_http.markdown_urls import extract_urls
from data_sources.modules.url_validator import UrlValidator, validate_content_urls

_LEAKAGE_RULE = "editorial_process_leakage"


def _capture_bindings(
    facts: Sequence[Mapping[str, Any]], root: Path | None
) -> tuple[dict[str, PageCapture], dict[str, Finding]]:
    """Re-hash each fact's bound Chrome capture; return the intact ones by url and a block for each broken one."""
    captures: dict[str, PageCapture] = {}
    broken: dict[str, Finding] = {}
    for fact in facts:
        binding = fact.get("capture")
        if root is None or not isinstance(binding, Mapping):
            continue
        try:
            capture = load_capture(str(binding.get("path")), root)
            if capture.receipt_sha256 != binding.get("sha256") or capture.url != fact["url"]:
                raise ValueError("the receipt differs from the capture bound in the BOM")
        except ValueError as error:
            broken[str(fact["id"])] = Finding(
                "fact_quote", "block",
                f"fact {fact['id']} Chrome capture {binding.get('path')} can no longer be trusted: {error}", None,
            )
            continue
        captures[str(fact["url"])] = capture
    return captures, broken


def _fact_finding(fact: Mapping[str, Any], check: Any) -> Finding | None:
    """The finding for one fact's check: nothing when verified live, a warning when only unreachable."""
    if check.status == "verified":
        return None
    if check.status == "verified_capture":
        return Finding(
            "fact_quote", "warn",
            f"fact {fact['id']} source {fact['url']} blocked the live check; its quote was verified from "
            f"the Chrome capture taken at {fact['capture']['captured_at']} ({fact['capture']['path']})", None,
        )
    if check.status == "unreachable":
        verified = fact.get("verified_at")
        when = f"its quote was last verified at {verified}" if verified else "verification date unknown"
        return Finding(
            "fact_quote", "warn",
            f"fact {fact['id']} source {fact['url']} was unreachable ({check.detail}); {when}", None,
        )
    return Finding(
        "fact_quote", "block",
        f"fact {fact['id']} source {fact['url']} no longer supports its verified quote "
        f"({check.status}: {check.detail})", None,
    )


def _fact_findings(
    facts: Sequence[Mapping[str, Any]], transport: Any, root: Path | None = None
) -> tuple[list[Finding], frozenset[str]]:
    """Verify every linked fact in one batch; return findings and the unreachable source URLs.

    A fact whose page blocks the live check passes on its bound Chrome capture, with a warning, only
    while the capture still hashes as recorded; an edited capture blocks instead.
    """
    pairs = [(str(fact["url"]), str(fact["quote"])) for fact in facts]
    if not pairs:
        return [], frozenset()
    captures, broken = _capture_bindings(facts, root)
    results = verify_quotes(pairs, transport=transport, captures=captures)
    findings: list[Finding] = []
    unreachable: set[str] = set()
    for fact, pair in zip(facts, pairs):
        check = results[pair]
        if check.status == "unreachable" and str(fact["id"]) in broken:
            findings.append(broken[str(fact["id"])])
            continue
        if check.status in ("unreachable", "verified_capture"):
            unreachable.add(canonical(pair[0]))
        finding = _fact_finding(fact, check)
        if finding is not None:
            findings.append(finding)
    return findings, frozenset(unreachable)


def _link_findings(article: str, index: BomIndex, transport: Any, soft: frozenset[str]) -> list[Finding]:
    """Validate links once. A fact page that was merely unreachable is a warning, not a block."""
    summary = validate_content_urls(article, validator=UrlValidator(transport=transport))
    blocked = {id(result) for result in summary.blockers}
    findings = []
    for result in summary.blockers:
        severity = "warn" if canonical(result.url) in soft else "block"
        findings.append(Finding(
            "link_resolution", severity, f"link does not resolve: {result.url} ({result.reason})", result.line))
    findings += [
        Finding("link_off_bom", "warn", f"link is not a BOM link, fact, or proof URL: {result.url}", result.line)
        for result in summary.results
        if id(result) not in blocked and canonical(result.url) not in index.known_urls
    ]
    return findings


def _lint_findings(article: str) -> list[Finding]:
    return [
        Finding(
            "lint", "block" if item["rule_id"] == _LEAKAGE_RULE else "warn",
            f"{item['rule_id']}: {item['message']}", item.get("line"),
        )
        for item in lint_content(article)
    ]


def check_truth(
    article: str, bom: Mapping[str, Any], *, transport: Any, workspace_root: Path | None = None
) -> list[Finding]:
    """Check a finished article against its production BOM and return every finding.

    ``workspace_root`` lets a fact page that blocks bots be checked against its bound Chrome capture.
    """
    index = BomIndex.build(bom)
    report = analyze_proof_links(article, "", brand=bom["identity"]["brand"])
    raw = body_lines(article)
    links = extract_urls("\n".join(raw))  # comments, code, and frontmatter are blanked: hidden links do not count
    structure = detect_faq_structure(article)
    meta = meta_lines(article)
    scope = ListicleScope(
        h3_count(raw, section_ranges(raw)), frozenset({n for n, _ in meta} | heading_lines(raw)), link_anchors(raw)
    )
    findings = citation_findings(report.requirements, report.links, links, index)
    findings += customer_story_findings(links, index)
    linked_facts, _ = index.rows_for(linked_urls(links, 1, len(raw) + 1))
    fact_findings, unreachable = _fact_findings(linked_facts, transport, workspace_root)
    findings += fact_findings
    units = paragraph_units(article, answer_ranges(structure))
    findings += paragraph_number_findings(units, links, index, meta, scope)
    lines = public_copy_lines(article)
    findings += number_gate(lines, index.all_numbers(), scope)
    findings += quoted_passage_findings(lines, index.quote_sources(), index.customers)
    findings += faq_findings(structure, raw, lines, index)
    findings += _link_findings(article, index, transport, unreachable)
    return findings + _lint_findings(article)


__all__ = ["Finding", "check_truth"]
