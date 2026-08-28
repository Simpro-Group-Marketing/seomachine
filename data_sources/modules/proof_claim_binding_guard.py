"""Require receipt-approved connector claims for proof-sensitive public passages.

Legacy validation-sidecar evidence can corroborate a claim, but it cannot grant
public-use approval. This module detects the public passage that creates each
proof obligation and verifies an exact binding to typed claim evidence in the
validated context pack and receipt.
"""

from __future__ import annotations

import hashlib
import html
import re
import unicodedata
from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from bs4 import BeautifulSoup

try:
    from .guard_common import Finding, make_finding
    from .numeric_claim_source_guard import (
        _blank_fenced_code,
        _claim_text_for_detection,
        _extract_numeric_tokens,
        _is_candidate_claim,
        _iter_paragraphs,
        _strip_frontmatter_preserve_lines,
    )
except ImportError:  # pragma: no cover - supports direct script execution.
    from guard_common import Finding, make_finding
    from numeric_claim_source_guard import (
        _blank_fenced_code,
        _claim_text_for_detection,
        _extract_numeric_tokens,
        _is_candidate_claim,
        _iter_paragraphs,
        _strip_frontmatter_preserve_lines,
    )


EXACT_QUOTE_RE = re.compile(r'["\u201c](?P<quote>[^"\u201d]{20,})["\u201d]')

CONNECTOR_PROOF_CONTEXT_RE = re.compile(
    r"\b(?:Simpro|Fred(?:\s+Voccola)?|customers?|case stud(?:y|ies)|"
    r"Capterra|G2|GetApp|Software Advice|Trustpilot|reviewers?|reviews)\b|"
    r"https?://[^\s)]+simprogroup\.com/(?:customers?|case-stud(?:y|ies))/",
    re.IGNORECASE,
)
REVIEW_THEME_RE = re.compile(
    r"\b(?:Capterra|G2|GetApp|Software Advice|Trustpilot|reviewers?|reviews)\b"
    r".{0,120}\b(?:describe|described|report|reported|say|says|said|praise|"
    r"praised|mention|mentioned|highlight|highlighted|cite|cited|note|noted)\b"
    r"|\b(?:describe|described|report|reported|say|says|said|praise|praised|"
    r"mention|mentioned|highlight|highlighted|cite|cited|note|noted)\b"
    r".{0,120}\b(?:Capterra|G2|GetApp|Software Advice|Trustpilot|reviewers?|reviews)\b",
    re.IGNORECASE,
)
CUSTOMER_PROOF_RE = re.compile(
    r"(?:https?://[^\s)]+/(?:customers?|case-stud(?:y|ies))/|\bcase stud(?:y|ies)\b)"
    r".{0,180}\b(?:achiev|improv|increas|reduc|sav|grow|grew|deliver|report|show|"
    r"transform|streamlin|automat)",
    re.IGNORECASE,
)
COMMERCIAL_CLAIM_RE = re.compile(
    r"\bSimpro\b.{0,120}\b(?:helps?|can|enables?|allows?|delivers?|improves?|"
    r"increases?|reduces?|saves?|boosts?|streamlines?|automates?|optimizes?)\b"
    r".{0,160}\b(?:administrative(?: work)?|costs?|efficien|profit|productiv|"
    r"revenue|time|workflow|operations?|scheduling|dispatch|invoic|cash flow|growth)\b",
    re.IGNORECASE,
)

PROOF_USE_MODES = {
    "metric": frozenset({"public_metric"}),
    "exact_quote": frozenset({"exact_quote"}),
    "review_theme": frozenset({"public_paraphrase"}),
    "customer_proof": frozenset({"paraphrase", "public_claim", "public_paraphrase"}),
    "commercial_claim": frozenset({"paraphrase", "public_claim", "public_paraphrase"}),
}


@dataclass(frozen=True)
class ProofObligation:
    """A proof-sensitive public passage and the claim modes that may authorize it."""

    kind: str
    passage: str
    line: int
    compatible_use_modes: frozenset[str]


@dataclass(frozen=True)
class ClaimBinding:
    """A structurally valid pack, receipt, and claim-map join."""

    claim_id: str
    use_mode: str
    public_url: str
    public_text: str


def validate_proof_claim_bindings(
    article_content: str,
    evidence_rows: Any,
    decisions: Any,
    claim_map: Any,
) -> list[Finding]:
    """Return blockers for public proof passages without typed receipt bindings."""
    obligations = find_proof_obligations(article_content)
    if not obligations:
        return []
    bindings = _valid_claim_bindings(
        article_content,
        evidence_rows,
        decisions,
        claim_map,
    )
    findings: list[Finding] = []
    for obligation in obligations:
        if any(_binding_satisfies(binding, obligation) for binding in bindings):
            continue
        findings.append(
            make_finding(
                "context_proof_claim_unbound",
                "error",
                obligation.line,
                message=(
                    f"Public {obligation.kind.replace('_', ' ')} passage is not bound to "
                    "a compatible receipt-approved connector claim."
                ),
                suggestion=(
                    "Retrieve an approved claim for this exact passage and use mode, then "
                    "regenerate the Context Claim Use Map; sidecar approval text alone is "
                    "not authorization."
                ),
                proof_kind=obligation.kind,
                required_use_modes=sorted(obligation.compatible_use_modes),
                match=obligation.passage,
            )
        )
    return findings


def find_proof_obligations(article_content: str) -> list[ProofObligation]:
    """Detect one highest-specificity proof obligation per public paragraph."""
    body = _strip_frontmatter_preserve_lines(article_content)
    body = _blank_fenced_code(body)
    body = re.sub(r"<!--.*?-->", " ", body, flags=re.DOTALL)
    obligations: list[ProofObligation] = []
    for paragraph in _iter_paragraphs(body):
        raw = paragraph.text.strip()
        if not raw:
            continue
        visible = _visible_markdown_text(raw)
        if not visible:
            continue
        quote = _exact_quote(visible)
        connector_sensitive = _is_connector_sensitive_proof_context(visible)
        if quote and connector_sensitive:
            obligations.append(_obligation("exact_quote", quote, paragraph.line))
            continue
        if _is_candidate_claim(raw) and _extract_numeric_tokens(
            _claim_text_for_detection(raw)
        ) and connector_sensitive:
            obligations.append(_obligation("metric", visible, paragraph.line))
            continue
        if REVIEW_THEME_RE.search(visible):
            obligations.append(_obligation("review_theme", visible, paragraph.line))
            continue
        if CUSTOMER_PROOF_RE.search(raw):
            obligations.append(_obligation("customer_proof", visible, paragraph.line))
            continue
        if COMMERCIAL_CLAIM_RE.search(visible):
            obligations.append(_obligation("commercial_claim", visible, paragraph.line))
    return obligations


def _is_connector_sensitive_proof_context(text: str) -> bool:
    """Return true when a public passage needs connector-backed proof approval."""
    return bool(CONNECTOR_PROOF_CONTEXT_RE.search(text))


def _obligation(kind: str, passage: str, line: int) -> ProofObligation:
    return ProofObligation(
        kind=kind,
        passage=_normalize_text(passage),
        line=line,
        compatible_use_modes=PROOF_USE_MODES[kind],
    )


def _exact_quote(text: str) -> str:
    match = EXACT_QUOTE_RE.search(text)
    return _normalize_text(match.group("quote")) if match else ""


def _valid_claim_bindings(
    article_content: str,
    evidence_rows: Any,
    decisions: Any,
    claim_map: Any,
) -> list[ClaimBinding]:
    if not isinstance(evidence_rows, list) or not isinstance(decisions, list):
        return []
    if not isinstance(claim_map, list):
        return []
    evidence_by_id = _rows_by_claim_id(evidence_rows)
    decisions_by_id = _rows_by_claim_id(decisions)
    normalized_article = _normalize_visible_body(article_content)
    bindings: list[ClaimBinding] = []
    for row in claim_map:
        if not isinstance(row, Mapping):
            continue
        claim_id = str(row.get("claim_id") or "").strip()
        evidence_matches = evidence_by_id.get(claim_id, [])
        decision_matches = decisions_by_id.get(claim_id, [])
        if len(evidence_matches) != 1 or len(decision_matches) != 1:
            continue
        evidence = evidence_matches[0]
        decision = decision_matches[0]
        if decision.get("approved") is not True:
            continue
        use_mode = str(row.get("use_mode") or "").strip()
        if not use_mode or use_mode != str(evidence.get("use_mode") or "").strip():
            continue
        decision_mode = str(
            decision.get("requested_use_mode") or decision.get("use_mode") or ""
        ).strip()
        if use_mode != decision_mode:
            continue
        public_url = str(row.get("public_url") or "").strip()
        if not public_url.startswith(("http://", "https://")):
            continue
        if public_url != str(evidence.get("public_url") or "").strip():
            continue
        public_text = row.get("public_text")
        if not isinstance(public_text, str) or not public_text.strip():
            continue
        normalized_text = _normalize_text(public_text)
        expected_hash = hashlib.sha256(normalized_text.encode("utf-8")).hexdigest()
        if row.get("public_text_sha256") != expected_hash:
            continue
        if normalized_article.count(normalized_text) != 1:
            continue
        bindings.append(
            ClaimBinding(
                claim_id=claim_id,
                use_mode=use_mode,
                public_url=public_url,
                public_text=normalized_text,
            )
        )
    return bindings


def _rows_by_claim_id(rows: Sequence[Any]) -> dict[str, list[Mapping[str, Any]]]:
    indexed: dict[str, list[Mapping[str, Any]]] = {}
    for row in rows:
        if not isinstance(row, Mapping):
            continue
        claim_id = str(row.get("claim_id") or "").strip()
        if claim_id:
            indexed.setdefault(claim_id, []).append(row)
    return indexed


def _binding_satisfies(binding: ClaimBinding, obligation: ProofObligation) -> bool:
    return (
        binding.use_mode in obligation.compatible_use_modes
        and binding.public_text == obligation.passage
    )


def _normalize_visible_body(content: str) -> str:
    body = _strip_frontmatter_preserve_lines(content)
    body = _blank_fenced_code(body)
    body = re.sub(r"<!--.*?-->", " ", body, flags=re.DOTALL)
    return _normalize_text(_visible_markdown_text(body))


def _visible_markdown_text(value: str) -> str:
    text = re.sub(r"!\[[^\]]*\]\([^)]*\)", " ", value)
    text = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", text)
    if "<" in text and ">" in text:
        soup = BeautifulSoup(text, "html.parser")
        for tag in soup(["script", "style", "template", "noscript", "head", "title", "meta"]):
            tag.decompose()
        for tag in soup.find_all(True):
            if tag.attrs is None:
                continue
            hidden = "hidden" in tag.attrs
            aria_hidden = str(tag.attrs.get("aria-hidden", "")).strip().casefold() == "true"
            if hidden or aria_hidden:
                tag.decompose()
        text = soup.get_text(" ")
    text = re.sub(r"<[^>]+>", " ", text)
    text = html.unescape(text)
    text = re.sub(r"(?<!\\)[*_~`]", "", text)
    return _normalize_text(text)


def _normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", unicodedata.normalize("NFKC", value).strip())
