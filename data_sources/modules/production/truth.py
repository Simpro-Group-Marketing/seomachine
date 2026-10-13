"""Truth checks: block any fact, number, quote, or FAQ question that is not in the production BOM.

The BOM facts were verified on their live pages and the BOM proof items are approved claims, so
they are the only admitted sources. Everything here runs against a finished article. Network
work is two batch operations on one transport: ``verify_quotes`` once for every cited fact, and
the URL validator once for every article link.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from data_sources.modules.ai_copy_lint.core import lint_content
from data_sources.modules.faq_structure import detect_faq_structure
from data_sources.modules.production.bom_text import supported_numbers
from data_sources.modules.production.facts import verify_quotes
from data_sources.modules.production.truth_numbers import missing_claim_numbers, number_gate
from data_sources.modules.production.truth_quotes import quoted_passage_findings
from data_sources.modules.production.truth_text import Finding, public_copy_lines
from data_sources.modules.proof_link_policy import (
    CitationRequirement,
    analyze_proof_links,
    canonicalize_link_identity,
)
from data_sources.modules.url_validator import UrlValidator, validate_content_urls

_CITING_MODES = frozenset({"inline_required", "section_source_allowed"})
_LEAKAGE_RULE = "editorial_process_leakage"
_TRAILING_PUNCTUATION = " \t?!.:;,…"


def _canonical(url: str) -> str:
    return canonicalize_link_identity(url) or url.strip()


def _question_key(question: str) -> str:
    return " ".join(question.casefold().split()).rstrip(_TRAILING_PUNCTUATION)


def _items(bom: Mapping[str, Any], key: str) -> list[Mapping[str, Any]]:
    value = bom.get(key)
    return [item for item in value if isinstance(item, Mapping)] if isinstance(value, list) else []


@dataclass(frozen=True)
class _Index:
    """The BOM reduced to the lookups the checks need."""

    facts: tuple[Mapping[str, Any], ...]
    proof: tuple[Mapping[str, Any], ...]
    facts_by_url: Mapping[str, tuple[Mapping[str, Any], ...]]
    proof_by_url: Mapping[str, tuple[Mapping[str, Any], ...]]
    known_urls: frozenset[str]
    questions: frozenset[str]
    year: str

    @classmethod
    def build(cls, bom: Mapping[str, Any]) -> "_Index":
        facts, proof = _items(bom, "facts"), _items(bom, "proof")
        facts_by_url = _group_by_url(facts)
        proof_by_url = _group_by_url(proof)
        link_urls = {_canonical(link["url"]) for link in _items(bom, "links") if link.get("url")}
        cta = bom["identity"].get("cta")
        cta_urls = {_canonical(cta["url"])} if isinstance(cta, Mapping) and cta.get("url") else set()
        paa = bom.get("paa")
        asked = paa.get("questions") if isinstance(paa, Mapping) else None
        questions = {
            _question_key(item["question"]) for item in asked or [] if isinstance(item, Mapping) and item.get("question")
        }
        return cls(
            tuple(facts), tuple(proof), facts_by_url, proof_by_url,
            frozenset(link_urls | cta_urls | set(facts_by_url) | set(proof_by_url)),
            frozenset(questions), str(bom["identity"].get("date", ""))[:4],
        )

    def quote_sources(self) -> list[str]:
        sources = [str(fact["quote"]) for fact in self.facts]
        for item in self.proof:
            sources.append(str(item.get("text") or ""))
            sources += [
                str(quote.get("quote") if isinstance(quote, Mapping) else quote)
                for quote in item.get("approved_quotes") or []
            ]
        return [source for source in sources if source.strip()]


def _group_by_url(items: Sequence[Mapping[str, Any]]) -> dict[str, tuple[Mapping[str, Any], ...]]:
    grouped: dict[str, list[Mapping[str, Any]]] = {}
    for item in items:
        if item.get("url"):
            grouped.setdefault(_canonical(item["url"]), []).append(item)
    return {url: tuple(rows) for url, rows in grouped.items()}


def _bom_sources(requirement: CitationRequirement, index: _Index) -> frozenset[str]:
    cited = {_canonical(url) for url in requirement.visible_urls}
    return frozenset(cited & (set(index.facts_by_url) | set(index.proof_by_url)))


def _citation_findings(
    requirements: Sequence[CitationRequirement], index: _Index
) -> tuple[list[Finding], list[tuple[CitationRequirement, frozenset[str]]]]:
    findings: list[Finding] = []
    cited: list[tuple[CitationRequirement, frozenset[str]]] = []
    for requirement in requirements:
        sources = _bom_sources(requirement, index)
        if sources:
            cited.append((requirement, sources))
            continue
        findings.append(Finding(
            "citation_source", "block",
            "claim cites a source outside the production BOM (no cited URL is a BOM fact or proof URL): "
            f"{requirement.claim}",
            requirement.line,
        ))
    return findings, cited


def _rows_for(lookup: Mapping[str, tuple[Mapping[str, Any], ...]], urls: frozenset[str]) -> list[Mapping[str, Any]]:
    rows: list[Mapping[str, Any]] = []
    for url in sorted(urls):
        rows += [row for row in lookup.get(url, ()) if row not in rows]
    return rows


def _fact_findings(facts: Sequence[Mapping[str, Any]], transport: Any) -> list[Finding]:
    pairs = [(str(fact["url"]), str(fact["quote"])) for fact in facts]
    if not pairs:
        return []
    results = verify_quotes(pairs, transport=transport)
    findings = []
    for fact, pair in zip(facts, pairs):
        status = results[pair].status
        if status == "verified":
            continue
        detail = results[pair].detail
        if status == "unreachable":
            findings.append(Finding(
                "fact_quote", "warn",
                f"fact {fact['id']} source {pair[0]} was unreachable ({detail}); "
                f"its quote was last verified at {fact.get('verified_at')}",
                None,
            ))
        else:
            findings.append(Finding(
                "fact_quote", "block",
                f"fact {fact['id']} source {pair[0]} no longer supports its verified quote ({status}: {detail})",
                None,
            ))
    return findings


def _claim_number_findings(
    cited: Sequence[tuple[CitationRequirement, frozenset[str]]], index: _Index
) -> list[Finding]:
    findings = []
    for requirement, sources in cited:
        facts = _rows_for(index.facts_by_url, sources)
        proof = _rows_for(index.proof_by_url, sources)
        missing = missing_claim_numbers(requirement.claim, supported_numbers(facts, proof, ""))
        if missing:
            findings.append(Finding(
                "claim_numbers", "block",
                f"claim numbers missing from the cited BOM sources: {', '.join(missing)}; claim: {requirement.claim}",
                requirement.line,
            ))
    return findings


def _faq_findings(article: str, index: _Index) -> list[Finding]:
    return [
        Finding("faq_question", "block", f"FAQ question is not a BOM PAA question: {entry.question}", entry.line)
        for entry in detect_faq_structure(article).entries
        if _question_key(entry.question) not in index.questions
    ]


def _link_findings(article: str, index: _Index, transport: Any) -> list[Finding]:
    summary = validate_content_urls(article, validator=UrlValidator(transport=transport))
    blocked = {id(result) for result in summary.blockers}
    findings = [
        Finding("link_resolution", "block", f"link does not resolve: {result.url} ({result.reason})", result.line)
        for result in summary.blockers
    ]
    findings += [
        Finding("link_off_bom", "warn", f"link is not a BOM link, fact, or proof URL: {result.url}", result.line)
        for result in summary.results
        if id(result) not in blocked and _canonical(result.url) not in index.known_urls
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


def check_truth(article: str, bom: Mapping[str, Any], *, transport: Any) -> list[Finding]:
    """Check a finished article against its production BOM and return every finding."""
    index = _Index.build(bom)
    report = analyze_proof_links(article, "", brand=bom["identity"]["brand"])
    requirements = [item for item in report.requirements if item.mode in _CITING_MODES]
    findings, cited = _citation_findings(requirements, index)
    cited_urls = frozenset().union(*(sources for _, sources in cited))
    findings += _fact_findings(_rows_for(index.facts_by_url, cited_urls), transport)
    findings += _claim_number_findings(cited, index)
    lines = public_copy_lines(article)
    findings += number_gate(lines, supported_numbers(index.facts, index.proof, index.year))
    findings += quoted_passage_findings(lines, index.quote_sources())
    findings += _faq_findings(article, index)
    findings += _link_findings(article, index, transport)
    return findings + _lint_findings(article)


__all__ = ["Finding", "check_truth"]
