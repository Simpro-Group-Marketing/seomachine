"""Shared customer-proof diversity parsing and finding utilities."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Dict, Iterable, List

from ..guard_common import Finding
from ..proof_link_policy import analyze_proof_links, canonicalize_link_identity, is_generic_proof_anchor
from .diversity_contracts import ANY_CUSTOMER_PROOF_URL_RE, CASE_STUDY_URL_RE, EXACT_QUOTE_RE, QUOTE_CONTEXT_RE


def _customer_proof_link_findings(
    content: str,
    proof_source: str,
) -> List[Finding]:
    """Require one natural, canonical-matching link per customer-proof unit."""
    report = analyze_proof_links(content, proof_source)
    findings: List[Finding] = []
    emitted: set[tuple[str, int, int, tuple[str, ...]]] = set()

    for requirement in report.requirements:
        if (
            requirement.owner != "customer_proof"
            or requirement.mode != "inline_required"
            or not requirement.approved_urls
        ):
            continue

        unit_links = [
            link
            for link in report.links
            if requirement.line <= link.line <= requirement.end_line
            and canonicalize_link_identity(link.url) in requirement.approved_urls
        ]
        natural_links = [
            link
            for link in unit_links
            if not is_generic_proof_anchor(link.anchor)
        ]
        if natural_links:
            continue

        if unit_links:
            rule_id = "customer_proof_anchor_not_descriptive"
            message = (
                "Customer proof uses a bare URL or generic anchor instead of a "
                "descriptive contextual link."
            )
            suggestion = (
                "Link descriptive customer-story text to the approved proof URL in "
                "the same paragraph or table row as the claim."
            )
        else:
            rule_id = "customer_proof_visible_link_missing"
            message = (
                "Customer proof is mapped in the sidecar but has no canonical-matching "
                "public link in the same paragraph or table row."
            )
            suggestion = (
                "Add one natural contextual link to the approved customer proof URL "
                "in the same paragraph or table row as the claim."
            )

        finding_key = (
            rule_id,
            requirement.line,
            requirement.end_line,
            requirement.approved_urls,
        )
        if finding_key in emitted:
            continue
        emitted.add(finding_key)
        findings.append(
            _finding(
                rule_id,
                requirement.line,
                message,
                suggestion,
                match=requirement.claim,
            )
        )

    return findings


def _has_customer_quote_claim(content: str) -> bool:
    public_content = _blank_fenced_code(content)
    for paragraph in _paragraphs(public_content):
        if not EXACT_QUOTE_RE.search(paragraph):
            continue
        if QUOTE_CONTEXT_RE.search(paragraph) or ANY_CUSTOMER_PROOF_URL_RE.search(
            paragraph
        ):
            return True
    return False


def _first_quote_line(content: str) -> int:
    public_content = _blank_fenced_code(content)
    for line_number, line in enumerate(public_content.splitlines(), start=1):
        if EXACT_QUOTE_RE.search(line):
            return line_number
    return 1


def _case_study_urls(content: str) -> List[str]:
    return [
        match.group(0).rstrip(".,") for match in CASE_STUDY_URL_RE.finditer(content)
    ]


def _customer_proof_urls(content: str) -> List[str]:
    return [
        match.group(0).rstrip(".,")
        for match in ANY_CUSTOMER_PROOF_URL_RE.finditer(content)
    ]


def _load_ledger(path: str | Path) -> Dict[str, object]:
    ledger_path = Path(path)
    if not ledger_path.exists():
        return {"uses": []}
    return json.loads(ledger_path.read_text(encoding="utf-8"))


def _proof_id_from_url(url: str) -> str:
    slug = url.rstrip("/").rsplit("/", 1)[-1]
    if "/case-studies/" in url or "/resources/case-study-" in url:
        return f"case-study-{slug}"
    return slug


def _paragraphs(content: str) -> Iterable[str]:
    chunks = re.split(r"\n\s*\n", content)
    for chunk in chunks:
        stripped = chunk.strip()
        if stripped:
            yield stripped


def _blank_fenced_code(content: str) -> str:
    lines = content.splitlines()
    blanked: List[str] = []
    in_fence = False
    for line in lines:
        if line.strip().startswith("```"):
            in_fence = not in_fence
            blanked.append("")
            continue
        blanked.append("" if in_fence else line)
    return "\n".join(blanked)


def _normalize_key(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip().lower()).strip()


def _normalize_space(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip().lower()).strip()


def _normalize_text(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()


def _finding(
    rule_id: str,
    line: int,
    message: str,
    suggestion: str,
    *,
    severity: str = "error",
    match: str = "",
) -> Finding:
    finding: Finding = {
        "rule_id": rule_id,
        "severity": severity,
        "line": line,
        "column": 1,
        "message": message,
        "suggestion": suggestion,
    }
    if match:
        finding["match"] = match
    return finding


__all__ = [
    '_customer_proof_link_findings',
    '_has_customer_quote_claim',
    '_first_quote_line',
    '_case_study_urls',
    '_customer_proof_urls',
    '_load_ledger',
    '_proof_id_from_url',
    '_paragraphs',
    '_blank_fenced_code',
    '_normalize_key',
    '_normalize_space',
    '_normalize_text',
    '_finding'
]
