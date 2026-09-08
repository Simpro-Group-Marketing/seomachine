"""
Source Support Guard

Strict source-support validation for high-risk public claims. General claims
use an exact Claim/Claim type/Evidence relation mapping plus a hash-bound
``simpro-source-classification/v1`` registry export. Local PDF extractions and
unreachable-HTML fallbacks are accepted only with a hash-bound
``simpro-source-capture-receipt/v1`` tool receipt; an authored text file alone
is never proof.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import socket
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Dict, List, Optional, Sequence
from urllib.parse import urlsplit

import requests
from bs4 import BeautifulSoup

try:
    from diskcache import Cache
except ImportError:  # pragma: no cover - dependency is declared, fallback is defensive.
    Cache = None

try:
    from .blog_assembly_contract import (
        atomic_write_json,
        canonical_snapshot_artifact,
        load_json_object_snapshot,
        resolve_artifact,
    )
    from .execution_attestation import attest_mapping, verify_mapping_attestation
    from .guard_common import Finding, should_fail, summarize_findings
    from .public_url_safety import request_public_url
    from .proof_sidecar import compose_with_sidecar, load_sidecar_content
    from .numeric_claim_source_guard import (
        MARKDOWN_LINK_RE,
        _blank_fenced_code,
        _claim_text_for_detection,
        _extract_numeric_tokens,
        _is_candidate_claim,
        _iter_paragraphs,
        _normalize_numeric_token,
        _strip_frontmatter_preserve_lines,
    )
except ImportError:  # pragma: no cover - supports direct script execution.
    from blog_assembly_contract import (
        atomic_write_json,
        canonical_snapshot_artifact,
        load_json_object_snapshot,
        resolve_artifact,
    )
    from execution_attestation import attest_mapping, verify_mapping_attestation
    from guard_common import Finding, should_fail, summarize_findings
    from public_url_safety import request_public_url
    from proof_sidecar import compose_with_sidecar, load_sidecar_content
    from numeric_claim_source_guard import (
        MARKDOWN_LINK_RE,
        _blank_fenced_code,
        _claim_text_for_detection,
        _extract_numeric_tokens,
        _is_candidate_claim,
        _iter_paragraphs,
        _normalize_numeric_token,
        _strip_frontmatter_preserve_lines,
    )


Fetcher = Callable[[str], str]


DEFAULT_TIMEOUT_SECONDS = 12
DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/125.0 Safari/537.36 SEO-Machine-Source-Support/1.0"
)
SOURCE_TEXT_CACHE_SECONDS = 60 * 60 * 24
PDF_EXTENSION_RE = re.compile(r"\.pdf(?:$|[?#])", re.IGNORECASE)
LOCAL_ARTIFACT_EXTENSION_RE = re.compile(r"\.(?:md|txt|csv|tsv|json)$", re.IGNORECASE)
JSON_ARTIFACT_EXTENSION_RE = re.compile(r"\.json$", re.IGNORECASE)
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
RFC3339_UTC_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?Z$"
)
SOURCE_CAPTURE_SCHEMA = "simpro-source-capture-receipt/v1"
SOURCE_CLASSIFICATION_SCHEMA = "simpro-source-classification/v1"
SOURCE_CAPTURE_EMITTER = "source_support_capture"
SOURCE_CLASSIFICATION_EMITTER = "source_registry_export"
SOURCE_CAPTURE_EMITTER_VERSION = "1.0.0"
SOURCE_CLASSIFICATION_EMITTER_VERSION = "1.0.0"
SOURCE_CAPTURE_ATTESTATION_PURPOSE = SOURCE_CAPTURE_SCHEMA
SOURCE_CLASSIFICATION_ATTESTATION_PURPOSE = SOURCE_CLASSIFICATION_SCHEMA
SOURCE_DECISIONS_SCHEMA = "simpro-source-classification-decisions/v1"
SOURCE_DECISIONS_PATH = "context/source-classification-decisions.json"
SOURCE_DECISION_FIELDS = frozenset({
    "decision_id", "status", "source_url", "hostname", "source_class",
    "publisher_relationship",
})
PUBLISHER_RELATIONSHIPS = frozenset(
    {"independent", "owned", "competitor", "customer", "review_platform"}
)
PROOF_ROW_RE = re.compile(
    r"^\s*(?:[-*+]\s+)?(?P<body>(?:Claim|Approved metric|Approved quote)\s*:.*)$",
    re.IGNORECASE,
)
SECTION_RE = re.compile(r"^\s*(?:#{1,4}\s+)?(?P<section>[A-Za-z][A-Za-z /-]+):?\s*$")
EXACT_QUOTE_RE = re.compile(
    r"(?:\"[^\"]{20,}\"|\u201c[^\u201d]{20,}\u201d)"
)
QUOTE_ATTRIBUTION_SIGNAL_RE = re.compile(
    r"\b(?:said|says|according to|quote|quoted|testimonial|reviewer|reviewed|"
    r"customer review|case study|customer story)\b",
    re.IGNORECASE,
)
REVIEW_AUTHORITY_SIGNAL_RE = re.compile(
    r"\b(?:reviewer|named reviewer|star rating|stars?|rating|badge|badges|"
    r"ranked|ranking|category leader|category-leading|top rated|highest rated|"
    r"award|awarded)\b",
    re.IGNORECASE,
)

OUTCOME_SIGNAL_RE = re.compile(
    r"\b(?:achieved|increased|improved|reduced|saved|generated|lifted|grew|"
    r"doubled|tripled|processed?|centralized|transformed|can process|"
    r"profit|profits|margin|margins|revenue|resources|efficiency|"
    r"productivity|business)\b",
    re.IGNORECASE,
)

INSUFFICIENT_SOURCE_RE = re.compile(
    r"\b(?:context/|@context|source map|proof pack|industry standard|"
    r"FDD conventions|no anchor)\b",
    re.IGNORECASE,
)
SOURCE_CLASSES = frozenset(
    {
        "neutral",
        "primary_authority",
        "independent_research",
        "non_competing_expert",
        "owned_product",
        "customer_proof",
        "review_platform",
        "competitor",
    }
)
GENERAL_CLAIM_TYPES = frozenset(
    {
        "absolute",
        "causal",
        "commercial",
        "comparative",
        "definitional",
        "factual",
        "guarantee",
        "process",
        "recommendation",
    }
)
GENERAL_CLAIM_PATTERNS = (
    (
        "guarantee",
        re.compile(
            r"\b(?:guarantees?|ensures?|eliminates?)\b|"
            r"\b(?:zero[- ]risk|fail[- ]proof|error[- ]proof|cannot fail)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "absolute",
        re.compile(
            r"\b(?:always|never)\b(?=[^.!?]{0,100}\b(?:is|are|has|have|"
            r"stores?|records?|tracks?|offers?|provides?|includes?|supports?|"
            r"loses?|prevents?|works?|delivers?|produces?))",
            re.IGNORECASE,
        ),
    ),
    (
        "commercial",
        re.compile(
            r"\b(?:pricing|price|costs?|subscription|plan|package|premium|trial|"
            r"add[- ]on|upgrade|license|licence)\b[^.!?]{0,90}\b"
            r"(?:is|are|costs?|includes?|included|requires?|available|free|paid)\b|"
            r"\b(?:is|are)\s+included\s+in\s+(?:the\s+)?(?:paid|premium|"
            r"enterprise|standard|basic)?\s*(?:plan|package|subscription)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "comparative",
        re.compile(
            r"\b(?:better|worse|more|less|faster|slower|higher|lower)\b[^.!?]{0,80}\bthan\b|"
            r"\bcompared (?:with|to)\b|\bversus\b|\boutperform(?:s|ed|ing)?\b|"
            r"\bUnlike\s+(?!(?:the\s+)?(?:previous|next)\s+(?:section|paragraph|example)\b)"
            r"[^,]{1,100},\s+(?!this\s+(?:section|article|guide)\b)|"
            r",\s+whereas\s+",
            re.IGNORECASE,
        ),
    ),
    (
        "causal",
        re.compile(
            r"\b(?:causes?|leads? to|results? in|because of|therefore|drives?|"
            r"contributes? to|improves?|reduces?|increases?|decreases?|prevents?|"
            r"enables?|boosts?|cuts?|streamlines?)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "definitional",
        re.compile(
            r"\b(?:is defined as|refers to|means|describes)\b|"
            r"\b(?:is|are)\s+(?:a|an|the)\s+(?:type|process|practice|method|"
            r"system|software|approach|term|measure|metric|workflow|prioritized list)\b|"
            r"\b(?:is|are)\s+(?:a|an)\s+document\s+(?:that|which|used to)\b|"
            r"^(?!\s*(?:This|That|It)\b)[^.!?]{1,80}\s+(?:is|are)\s+when\s+"
            r"(?:a|an|the|you|teams?|workers?|businesses?)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "process",
        re.compile(
            r"\b(?:requires?|involves?|consists of|begins? with|starts? with|"
            r"works? by|follows? a sequence|steps? (?:include|are))\b|"
            r"^\s*First\s+[^.!?;]{3,100},\s+then\s+[^.!?;]{3,100},\s+"
            r"(?:and\s+)?finally\s+|"
            r"\b(?:process|workflow)\s+moves?\s+from\s+[^.!?]{1,80}\s+to\s+"
            r"[^.!?]{1,80}\s+to\s+[^.!?]{1,80}",
            re.IGNORECASE,
        ),
    ),
    (
        "factual",
        re.compile(
            r"^(?:The|A|An|This|That|These|Those|[A-Z][A-Za-z0-9&.+-]+)\s+"
            r"(?:[A-Za-z0-9&.+-]+\s+){0,5}"
            r"(?:stores?|records?|tracks?|offers?|provides?|includes?|supports?|"
            r"connects?|sends?|displays?|manages?|contains?)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "recommendation",
        re.compile(
            r"\b(?:should|must|need to|ought to|avoid|choose|recommend(?:ed|s)?|"
            r"best practice|is advisable to|is essential to|is important to)\b|"
            r"^\s*(?:Review|Verify|Confirm|Check)\s+[^.!?]{1,100}\s+"
            r"(?:before|prior to)\s+|"
            r"^\s*Do\s+not\s+[^.!?]{1,100}\s+(?:until|before)\s+",
            re.IGNORECASE,
        ),
    ),
)
GENERAL_SOURCE_CLASSES = frozenset(
    {"primary_authority", "independent_research", "non_competing_expert"}
)
OWNED_PRODUCT_GENERAL_CLAIM_TYPES = frozenset({"definitional", "process"})
SOURCE_CLASS_RELATIONSHIPS = {
    "neutral": frozenset({"independent"}),
    "primary_authority": frozenset({"independent"}),
    "independent_research": frozenset({"independent"}),
    "non_competing_expert": frozenset({"independent"}),
    "owned_product": frozenset({"owned"}),
    "customer_proof": frozenset({"customer"}),
    "review_platform": frozenset({"review_platform"}),
    "competitor": frozenset({"competitor"}),
}


@dataclass(frozen=True)
class ClaimCandidate:
    text: str
    line: int
    numeric_tokens: List[str]
    normalized_tokens: frozenset[str]
    customer_names: frozenset[str]
    has_case_study_link: bool
    requires_approved_quote: bool
    claim_type: str = ""

    @property
    def has_numeric_tokens(self) -> bool:
        return bool(self.numeric_tokens)

    @property
    def is_named_customer_claim(self) -> bool:
        return self.has_case_study_link or bool(self.customer_names)

    @property
    def is_named_customer_metric(self) -> bool:
        return self.is_named_customer_claim and self.has_numeric_tokens


@dataclass(frozen=True)
class ProofEntry:
    kind: str
    claim: str
    url: str
    evidence: str
    status: str
    line: int
    section: str
    customer: str = ""
    artifact: str = ""
    use: str = ""
    source_class: str = ""
    claim_type: str = ""
    evidence_relation: str = ""
    capture_receipt: str = ""
    capture_receipt_hash: str = ""
    classification_artifact: str = ""
    classification_hash: str = ""

    @property
    def is_approved(self) -> bool:
        return self.status.lower() == "approved"

    @property
    def is_public_url(self) -> bool:
        return self.url.startswith("http://") or self.url.startswith("https://")

    @property
    def is_pdf(self) -> bool:
        return bool(PDF_EXTENSION_RE.search(self.url))

    @property
    def normalized_numeric_tokens(self) -> frozenset[str]:
        tokens = _extract_numeric_tokens(_claim_text_for_detection(self.evidence))
        return frozenset(_normalize_numeric_token(token) for token in tokens)


class SourceSupportError(Exception):
    """Raised when source-support validation blocks publishing."""


def write_source_classification_artifact(
    path: str | Path,
    *,
    source_url: str,
    decision_id: str,
    decision_path: str | Path,
    workspace_root: str | Path | None = None,
) -> dict:
    """Emit classification derived from one approved repository decision row."""
    if workspace_root is None:
        raise ValueError("workspace_root is required for source classification")
    root = Path(workspace_root).resolve()
    normalized_url = _required_emitter_text(source_url, "source_url")
    hostname = (urlsplit(normalized_url).hostname or "").lower()
    if not hostname:
        raise ValueError("source_url must contain a hostname")
    normalized_decision_id = _required_emitter_text(decision_id, "decision_id")
    snapshot = load_json_object_snapshot(
        decision_path,
        field="source classification decision registry",
    )
    _require_registry_matches_committed_head(snapshot, workspace_root=root)
    registry = snapshot.payload
    if set(registry) != {"schema", "revision", "decisions"}:
        raise ValueError("source classification decision registry shape is invalid")
    if registry.get("schema") != SOURCE_DECISIONS_SCHEMA:
        raise ValueError("source classification decision registry schema is invalid")
    revision = _required_emitter_text(registry.get("revision"), "decision revision")
    decisions = registry.get("decisions")
    if not isinstance(decisions, list):
        raise ValueError("source classification decisions must be a list")
    matches = [
        row for row in decisions
        if isinstance(row, dict) and row.get("decision_id") == normalized_decision_id
    ]
    if len(matches) != 1 or set(matches[0]) != SOURCE_DECISION_FIELDS:
        raise ValueError("source classification decision must resolve exactly once")
    decision = matches[0]
    if decision.get("status") != "approved":
        raise ValueError("source classification decision is not approved")
    if decision.get("source_url") != normalized_url:
        raise ValueError("source classification decision URL does not match")
    if decision.get("hostname") != hostname:
        raise ValueError("source classification decision hostname does not match")
    source_class = decision.get("source_class")
    publisher_relationship = decision.get("publisher_relationship")
    if source_class not in SOURCE_CLASSES:
        raise ValueError("approved decision source_class is invalid")
    if publisher_relationship not in SOURCE_CLASS_RELATIONSHIPS[source_class]:
        raise ValueError("approved decision publisher relationship is invalid")
    decision_binding = canonical_snapshot_artifact(snapshot, workspace_root=root)
    if decision_binding["path"] != SOURCE_DECISIONS_PATH:
        raise ValueError(
            f"source classification decisions must use {SOURCE_DECISIONS_PATH}"
        )
    payload = {
        "schema": SOURCE_CLASSIFICATION_SCHEMA,
        "source_url": normalized_url,
        "source_class": source_class,
        "classified_at": _utc_timestamp_now(),
        "publisher": {
            "hostname": hostname,
            "relationship": publisher_relationship,
        },
        "registry": {
            "authority_mode": "repository_decision",
            "record_id": normalized_decision_id,
            "revision": revision,
            "decision_path": decision_binding["path"],
            "decision_sha256": decision_binding["sha256"],
        },
        "emitter": {
            "name": SOURCE_CLASSIFICATION_EMITTER,
            "version": SOURCE_CLASSIFICATION_EMITTER_VERSION,
        },
    }
    attested = attest_mapping(
        payload,
        purpose=SOURCE_CLASSIFICATION_ATTESTATION_PURPOSE,
        workspace_root=workspace_root,
    )
    if not _is_strict_classification_payload(attested):
        raise ValueError("generated source classification does not satisfy the v1 contract")
    atomic_write_json(path, attested)
    return attested


def write_source_capture_receipt(
    path: str | Path,
    *,
    source_url: str,
    source_content_path: str | Path,
    artifact_path: str | Path,
    artifact_reference: str,
    method: str,
    workspace_root: str | Path | None = None,
) -> dict:
    """Atomically emit one workspace-attested source capture receipt."""
    normalized_url = _required_emitter_text(source_url, "source_url")
    if not (urlsplit(normalized_url).hostname or ""):
        raise ValueError("source_url must contain a hostname")
    if method not in {"html_visible_text", "pdf_text"}:
        raise ValueError("method must be html_visible_text or pdf_text")

    captured_source = Path(source_content_path)
    extracted_artifact = Path(artifact_path)
    if not captured_source.is_file():
        raise ValueError("source_content_path must identify an existing file")
    if not extracted_artifact.is_file():
        raise ValueError("artifact_path must identify an existing file")

    source_content_hash = _sha256_file(captured_source)
    artifact_hash = _sha256_file(extracted_artifact)
    payload = {
        "schema": SOURCE_CAPTURE_SCHEMA,
        "source_url": normalized_url,
        "retrieved_at": _utc_timestamp_now(),
        "source_content_sha256": source_content_hash,
        "artifact": {
            "path": _required_emitter_text(
                artifact_reference,
                "artifact_reference",
            ),
            "sha256": artifact_hash,
        },
        "extraction": {
            "method": method,
            "tool_name": SOURCE_CAPTURE_EMITTER,
            "tool_version": SOURCE_CAPTURE_EMITTER_VERSION,
            "input_sha256": source_content_hash,
            "output_sha256": artifact_hash,
        },
        "emitter": {
            "name": SOURCE_CAPTURE_EMITTER,
            "version": SOURCE_CAPTURE_EMITTER_VERSION,
        },
    }
    attested = attest_mapping(
        payload,
        purpose=SOURCE_CAPTURE_ATTESTATION_PURPOSE,
        workspace_root=workspace_root,
    )
    if not _is_strict_capture_payload(attested):
        raise ValueError("generated source capture receipt does not satisfy the v1 contract")
    atomic_write_json(path, attested)
    return attested


def check_content(
    content: str,
    base_path: str | Path | None = None,
    fetcher: Optional[Fetcher] = None,
    proof_content: Optional[str] = None,
) -> List[Finding]:
    """Return source-support findings for high-risk article claims."""
    base = Path(base_path) if base_path is not None else Path.cwd()
    proof_source = compose_with_sidecar(content, proof_content)
    proof_entries = _extract_proof_entries(proof_source)
    known_customer_names = _known_customer_names(proof_entries)
    candidates = _extract_claim_candidates(content, known_customer_names)

    findings: List[Finding] = []
    for candidate in candidates:
        matching_proofs = _matching_proofs(candidate, proof_entries)
        if candidate.requires_approved_quote:
            approved_quote_proofs = [
                proof
                for proof in matching_proofs
                if proof.kind == "approved_quote" and proof.section == "customer proof pack"
            ]
            if approved_quote_proofs:
                proof_finding = _validate_proof_entry(
                    approved_quote_proofs[0],
                    candidate,
                    base_path=base,
                    fetcher=fetcher,
                )
                if proof_finding:
                    findings.append(proof_finding)
                continue

            findings.append(_finding(
                "quote_requires_approved_quote",
                candidate,
                "Exact quote or testimonial language requires an approved Customer Proof Pack quote row.",
                (
                    "Add an Approved quote row with Customer/brand, URL, Evidence, "
                    "Status: approved, and source-visible quote evidence."
                ),
            ))
            continue

        if candidate.is_named_customer_metric:
            approved_metric_proofs = [
                proof
                for proof in matching_proofs
                if proof.kind == "approved_metric" and proof.section == "customer proof pack"
            ]
            if approved_metric_proofs:
                proof_finding = _validate_proof_entry(
                    approved_metric_proofs[0],
                    candidate,
                    base_path=base,
                    fetcher=fetcher,
                )
                if proof_finding:
                    findings.append(proof_finding)
                continue

            proof_findings = [
                proof_finding
                for proof_finding in (
                    _validate_proof_entry(
                        proof,
                        candidate,
                        base_path=base,
                        fetcher=fetcher,
                    )
                    for proof in matching_proofs
                )
                if proof_finding is not None
            ]
            if proof_findings:
                findings.append(proof_findings[0])
                continue

            if matching_proofs:
                findings.append(_finding(
                    "named_customer_metric_requires_approved_metric",
                    candidate,
                    "Named customer metrics must be approved in Customer Proof Pack Approved metrics.",
                    (
                        "Move the customer metric into an Approved metric row with "
                        "Customer/brand, URL, Evidence, and Status: approved."
                    ),
                ))
                continue
            findings.append(_finding(
                "missing_strict_proof",
                candidate,
                "High-risk claims need an approved strict proof row with Claim, URL, Evidence, and Status: approved.",
                "Add a structured proof row with public URL, exact evidence snippet, and approved status.",
            ))
            continue

        if not matching_proofs:
            findings.append(_finding(
                "general_claim_source_missing"
                if candidate.claim_type in GENERAL_CLAIM_TYPES
                else "missing_strict_proof",
                candidate,
                "General factual claims require a claim-fit approved Source Map row."
                if candidate.claim_type in GENERAL_CLAIM_TYPES
                else "High-risk claims need an approved strict proof row with Claim, URL, Evidence, and Status: approved.",
                "Add Claim type, Source class, public URL, exact evidence, and approved status."
                if candidate.claim_type in GENERAL_CLAIM_TYPES
                else "Add a structured proof row with public URL, exact evidence snippet, and approved status.",
            ))
            continue

        proof_findings = [
            _validate_proof_entry(
                proof,
                candidate,
                base_path=base,
                fetcher=fetcher,
            )
            for proof in matching_proofs
        ]
        if any(finding is None for finding in proof_findings):
            continue
        findings.append(next(finding for finding in proof_findings if finding is not None))

    return sorted(findings, key=lambda finding: (finding["line"], finding["column"], finding["rule_id"]))


def check_file(
    path: str | Path,
    fail_on: str = "error",
    fetcher: Optional[Fetcher] = None,
    proof_sidecar: Optional[str] = None,
) -> List[Finding]:
    """Check a Markdown file for strict source-support findings."""
    if fail_on not in {"error", "warning", "none"}:
        raise ValueError("fail_on must be one of: error, warning, none")

    file_path = Path(path)
    proof_content = load_sidecar_content(file_path, proof_sidecar)
    return check_content(
        file_path.read_text(encoding="utf-8"),
        base_path=file_path.parent,
        fetcher=fetcher,
        proof_content=proof_content,
    )


def require_source_support(
    path: str | Path,
    context: str = "publish",
    fetcher: Optional[Fetcher] = None,
    proof_sidecar: Optional[str] = None,
) -> List[Finding]:
    """Raise ValueError if strict source support fails for a file."""
    findings = check_file(
        path,
        fail_on="error",
        fetcher=fetcher,
        proof_sidecar=proof_sidecar,
    )
    if should_fail(findings, fail_on="error"):
        raise ValueError(
            f"Source support validation failed before {context}:\n"
            f"{format_findings(findings)}"
        )
    return findings


def format_findings(findings: Sequence[Finding]) -> str:
    """Format findings for preflight error output."""
    lines = [
        "=== Source Support Validation Report ===",
        f"Errors: {summarize_findings(findings)['error']}",
        f"Warnings: {summarize_findings(findings)['warning']}",
    ]
    if findings:
        lines.append("")
        lines.append("Blockers:")
        for finding in findings:
            lines.append(
                f"  - line {finding['line']}: {finding['rule_id']} - {finding['message']}"
            )
    return "\n".join(lines)


def fetch_source_text(url: str, *, resolver=socket.getaddrinfo) -> str:
    """Fetch and normalize visible source text from an HTML URL."""
    cache = _cache()
    cache_key = _cache_key(url)
    if cache is not None and cache_key in cache:
        return str(cache[cache_key])

    response = request_public_url(
        requests.Session(),
        "GET",
        url,
        headers={"User-Agent": DEFAULT_USER_AGENT},
        timeout=DEFAULT_TIMEOUT_SECONDS,
        resolver=resolver,
    )
    response.raise_for_status()
    text = _extract_visible_text(response.text)
    if cache is not None:
        cache.set(cache_key, text, expire=60 * 60 * 24)
    return text


def _extract_proof_entries(content: str) -> List[ProofEntry]:
    entries: List[ProofEntry] = []
    section = ""

    for line_number, line in enumerate(content.splitlines(), start=1):
        stripped = line.strip()
        section_match = SECTION_RE.match(stripped)
        if section_match and not stripped.startswith("-"):
            section = _normalize_section(section_match.group("section"))

        row_match = PROOF_ROW_RE.match(stripped)
        if not row_match:
            continue

        fields = _parse_proof_fields(row_match.group("body"))
        if "approved metric" in fields:
            kind = "approved_metric"
        elif "approved quote" in fields:
            kind = "approved_quote"
        else:
            kind = "claim"
        claim = fields.get("approved metric") or fields.get("approved quote") or fields.get("claim", "")
        url = fields.get("url", "")
        evidence = fields.get("evidence", "")
        status = fields.get("status", "")
        if not claim or not evidence:
            continue

        entries.append(
            ProofEntry(
                kind=kind,
                claim=claim,
                url=url,
                evidence=evidence,
                status=status,
                line=line_number,
                section=section,
                customer=fields.get("customer/brand", "") or fields.get("customer", ""),
                artifact=(
                    fields.get("artifact", "")
                    or fields.get("proof artifact", "")
                    or fields.get("local proof artifact", "")
                ),
                use=fields.get("use", ""),
                source_class=fields.get("source class", ""),
                claim_type=fields.get("claim type", ""),
                evidence_relation=fields.get("evidence relation", ""),
                capture_receipt=fields.get("capture receipt", ""),
                capture_receipt_hash=fields.get("capture receipt hash", ""),
                classification_artifact=fields.get("classification artifact", ""),
                classification_hash=fields.get("classification hash", ""),
            )
        )

    return entries


def _parse_proof_fields(row_body: str) -> Dict[str, str]:
    fields: Dict[str, str] = {}
    for segment in row_body.split("|"):
        if ":" not in segment:
            continue
        key, value = segment.split(":", 1)
        fields[_normalize_key(key)] = _clean_field_value(value)
    return fields


def _extract_claim_candidates(
    content: str,
    known_customer_names: Sequence[str],
) -> List[ClaimCandidate]:
    body = _strip_frontmatter_preserve_lines(content)
    body = _blank_fenced_code(body)
    candidates: List[ClaimCandidate] = []

    for paragraph in _iter_paragraphs(body):
        numeric_tokens = []
        if _is_candidate_claim(paragraph.text):
            numeric_tokens = _extract_numeric_tokens(_claim_text_for_detection(paragraph.text))

        names = _customer_names_in_text(paragraph.text, known_customer_names)
        has_case_study_link = _has_case_study_link(paragraph.text)
        text_for_detection = _claim_text_for_detection(paragraph.text)
        is_quote_claim = _is_exact_quote_claim(paragraph.text, names, has_case_study_link)
        is_review_authority_claim = _is_review_authority_claim(text_for_detection)
        is_named_outcome = (
            (has_case_study_link or bool(names))
            and bool(OUTCOME_SIGNAL_RE.search(text_for_detection))
        )
        is_special_claim = bool(
            numeric_tokens or is_named_outcome or is_quote_claim or is_review_authority_claim
        )
        if not is_special_claim:
            general_candidates = []
            for sentence in _split_claim_sentences(paragraph.text):
                if _is_general_claim_exempt(sentence):
                    continue
                claim_type = _general_claim_type(_claim_text_for_detection(sentence))
                if claim_type:
                    general_candidates.append(
                        ClaimCandidate(
                            text=sentence,
                            line=paragraph.line,
                            numeric_tokens=[],
                            normalized_tokens=frozenset(),
                            customer_names=frozenset(),
                            has_case_study_link=False,
                            requires_approved_quote=False,
                            claim_type=claim_type,
                        )
                    )
            if general_candidates:
                candidates.extend(general_candidates)
            continue

        candidates.append(
            ClaimCandidate(
                text=paragraph.text.strip(),
                line=paragraph.line,
                numeric_tokens=numeric_tokens,
                normalized_tokens=frozenset(_normalize_numeric_token(token) for token in numeric_tokens),
                customer_names=frozenset(names),
                has_case_study_link=has_case_study_link,
                requires_approved_quote=is_quote_claim,
                claim_type="",
            )
        )

    return candidates


def _split_claim_sentences(text: str) -> List[str]:
    return [
        sentence.strip()
        for sentence in re.split(r"(?<=[.!?])\s+(?=[A-Z0-9\[])", text.strip())
        if sentence.strip()
    ]


def _matching_proofs(
    candidate: ClaimCandidate,
    proof_entries: Sequence[ProofEntry],
) -> List[ProofEntry]:
    matches = []
    for proof in proof_entries:
        if not proof.is_approved:
            continue
        if candidate.has_numeric_tokens:
            if not candidate.normalized_tokens.issubset(proof.normalized_numeric_tokens):
                continue
            if not _text_overlaps(candidate.text, proof):
                continue
        if candidate.is_named_customer_claim and not _proof_matches_customer(candidate, proof):
            continue
        if not candidate.has_numeric_tokens and not _text_overlaps(candidate.text, proof):
            continue
        matches.append(proof)
    return matches


def _validate_proof_entry(
    proof: ProofEntry,
    candidate: ClaimCandidate,
    base_path: Path,
    fetcher: Optional[Fetcher],
) -> Optional[Finding]:
    if candidate.claim_type in GENERAL_CLAIM_TYPES:
        if proof.source_class not in SOURCE_CLASSES:
            return _finding(
                "source_class_invalid",
                candidate,
                "General claim proof must use one exact supported Source class.",
                "Use primary_authority, independent_research, non_competing_expert, or another contract class that fits the claim.",
                proof,
            )
        if proof.claim_type != candidate.claim_type:
            return _finding(
                "source_claim_type_mismatch",
                candidate,
                "Source Map Claim type does not fit the public claim.",
                f"Set Claim type to {candidate.claim_type} or use a different supporting row.",
                proof,
            )
        contract_finding = _validate_general_claim_contract(proof, candidate)
        if contract_finding:
            return contract_finding
        classification_finding = _validate_source_classification(
            proof,
            candidate,
            base_path,
        )
        if classification_finding:
            return classification_finding
        allowed = set(GENERAL_SOURCE_CLASSES)
        if candidate.claim_type == "comparative":
            allowed.add("competitor")
        if (
            candidate.claim_type in OWNED_PRODUCT_GENERAL_CLAIM_TYPES
            and re.search(r"\bSimpro\b", candidate.text, re.IGNORECASE)
        ):
            allowed.add("owned_product")
        if proof.source_class not in allowed:
            return _finding(
                "source_class_claim_fit_invalid",
                candidate,
                "The selected Source class cannot support this general claim type.",
                "Use an authority, independent research, or non-competing expert source with visible claim-fit evidence.",
                proof,
            )
    if not proof.url or INSUFFICIENT_SOURCE_RE.search(proof.url):
        return _finding(
            "missing_strict_proof",
            candidate,
            "Strict proof must use a public URL, not an internal context path or placeholder.",
            "Use the public source URL that visibly supports the claim.",
            proof,
        )
    if not proof.is_public_url:
        return _finding(
            "source_url_not_public",
            candidate,
            "Strict proof must use a public HTTP or HTTPS URL.",
            "Replace the source with its canonical public HTTP or HTTPS URL.",
            proof,
        )

    if proof.is_pdf:
        if not proof.artifact:
            return _finding(
                "unsupported_pdf_source",
                candidate,
                "PDF sources require a local text proof artifact in v1.",
                "Add Artifact: path/to/proof.md with the extracted evidence snippet, or use an HTML source.",
                proof,
            )
        source_text = _read_artifact_text(proof, base_path)
        if source_text is None:
            return _finding(
                "proof_artifact_missing",
                candidate,
                "The local proof artifact for this PDF source does not exist or is unsupported.",
                "Create the referenced .md/.txt/.csv/.tsv/.json proof artifact or remove the claim.",
                proof,
            )
        capture_finding = _validate_capture_receipt(
            proof,
            candidate,
            base_path,
            expected_method="pdf_text",
        )
        if capture_finding:
            return capture_finding
    else:
        try:
            source_text = fetcher(proof.url) if fetcher is not None else fetch_source_text(proof.url)
        except Exception as exc:  # fail closed on fetch errors
            if proof.artifact:
                source_text = _read_artifact_text(proof, base_path)
                if source_text is not None:
                    capture_finding = _validate_capture_receipt(
                        proof,
                        candidate,
                        base_path,
                        expected_method="html_visible_text",
                    )
                    if capture_finding:
                        return capture_finding
                    evidence_finding = _validate_source_text_contains_evidence(
                        source_text,
                        proof,
                        candidate,
                    )
                    if evidence_finding:
                        return evidence_finding
                    return None
                return _finding(
                    "proof_artifact_missing",
                    candidate,
                    "The local proof artifact for this source does not exist or is unsupported.",
                    "Create the referenced .md/.txt/.csv/.tsv/.json proof artifact or remove the claim.",
                    proof,
                )
            return _finding(
                "source_fetch_failed",
                candidate,
                f"Could not fetch cited source text: {exc}",
                "Fix the source URL, add a local proof artifact for non-HTML evidence, or remove the claim.",
                proof,
            )

    evidence_finding = _validate_source_text_contains_evidence(source_text, proof, candidate)
    if evidence_finding:
        return evidence_finding

    if candidate.claim_type in GENERAL_CLAIM_TYPES:
        fit_finding = _validate_evidence_claim_fit(proof, candidate)
        if fit_finding:
            return fit_finding

    if candidate.has_numeric_tokens and not candidate.normalized_tokens.issubset(proof.normalized_numeric_tokens):
        return _finding(
            "evidence_missing_numeric_token",
            candidate,
            "The proof evidence does not contain the numeric token used in the claim.",
            "Use evidence that contains the same number, or remove the unsupported number from the claim.",
            proof,
        )

    return None


def _validate_general_claim_contract(
    proof: ProofEntry,
    candidate: ClaimCandidate,
) -> Optional[Finding]:
    article_claim = _normalize_text(_claim_text_for_detection(candidate.text))
    mapped_claim = _normalize_text(proof.claim)
    if article_claim != mapped_claim:
        return _finding(
            "source_claim_binding_mismatch",
            candidate,
            "The Source Map Claim must exactly bind the public general claim.",
            "Copy the complete public claim into Claim or use a separate row for each claim.",
            proof,
        )
    if proof.evidence_relation != "directly_supports":
        return _finding(
            "source_evidence_relation_invalid",
            candidate,
            "General claim proof must declare Evidence relation: directly_supports.",
            "Use directly_supports only when the source-visible evidence entails the mapped claim.",
            proof,
        )
    return None


def _validate_source_classification(
    proof: ProofEntry,
    candidate: ClaimCandidate,
    base_path: Path,
) -> Optional[Finding]:
    if not proof.classification_artifact or not proof.classification_hash:
        return _finding(
            "source_classification_artifact_missing",
            candidate,
            "General claim Source class must be bound to a registry-emitted classification artifact.",
            "Add Classification artifact and Classification hash from a source_registry_export record.",
            proof,
        )
    classification_path = _resolve_local_artifact(
        proof.classification_artifact,
        base_path,
        JSON_ARTIFACT_EXTENSION_RE,
    )
    if classification_path is None:
        return _finding(
            "source_classification_artifact_missing",
            candidate,
            "The declared source-classification artifact is missing or is not JSON.",
            "Use an existing registry-emitted JSON classification artifact.",
            proof,
        )
    if not SHA256_RE.fullmatch(proof.classification_hash):
        return _finding(
            "source_classification_hash_invalid",
            candidate,
            "Classification hash must be a 64-character lowercase SHA-256.",
            "Record the exact SHA-256 of the classification artifact.",
            proof,
        )
    try:
        classification_snapshot = load_json_object_snapshot(
            classification_path,
            field="source classification artifact",
        )
    except ValueError:
        classification_snapshot = None
    if (
        classification_snapshot is None
        or classification_snapshot.sha256 != proof.classification_hash
    ):
        return _finding(
            "source_classification_hash_mismatch",
            candidate,
            "The source-classification artifact hash does not match the Source Map binding.",
            "Regenerate the classification binding from the unchanged registry artifact.",
            proof,
        )
    payload = classification_snapshot.payload
    if not isinstance(payload, dict):
        return _finding(
            "source_classification_artifact_invalid",
            candidate,
            "The source-classification artifact does not satisfy simpro-source-classification/v1.",
            "Regenerate it with source_registry_export; do not hand-label the source class.",
            proof,
        )
    if not verify_mapping_attestation(
        payload,
        purpose=SOURCE_CLASSIFICATION_ATTESTATION_PURPOSE,
        workspace_root=_attestation_workspace_root(base_path),
    ):
        return _finding(
            "source_classification_execution_attestation_invalid",
            candidate,
            "The source-classification artifact lacks a valid workspace execution attestation.",
            "Regenerate it with write_source_classification_artifact in this workspace.",
            proof,
        )
    if not _is_strict_classification_payload(payload):
        return _finding(
            "source_classification_artifact_invalid",
            candidate,
            "The source-classification artifact does not satisfy simpro-source-classification/v1.",
            "Regenerate it with source_registry_export; do not hand-label the source class.",
            proof,
        )
    if payload["source_url"] != proof.url or payload["source_class"] != proof.source_class:
        return _finding(
            "source_classification_mismatch",
            candidate,
            "The declared Source class or URL does not match the registry classification artifact.",
            "Use the registry-declared class for this exact URL.",
            proof,
        )
    hostname = (urlsplit(proof.url).hostname or "").lower()
    publisher = payload["publisher"]
    if publisher["hostname"].lower() != hostname:
        return _finding(
            "source_classification_hostname_mismatch",
            candidate,
            "The registry classification hostname does not match the cited URL.",
            "Regenerate classification metadata for the exact cited URL.",
            proof,
        )
    relationship = publisher["relationship"]
    if relationship not in SOURCE_CLASS_RELATIONSHIPS[proof.source_class]:
        return _finding(
            "source_classification_relationship_mismatch",
            candidate,
            "The publisher relationship cannot support the declared Source class.",
            "Use the registry-declared ownership or competitor relationship.",
            proof,
        )
    if (hostname == "simprogroup.com" or hostname.endswith(".simprogroup.com")) and proof.source_class != "owned_product":
        return _finding(
            "source_classification_owned_domain_mismatch",
            candidate,
            "A Simpro-owned hostname cannot be classified as an independent or competitor source.",
            "Use Source class: owned_product for Simpro-owned product facts.",
            proof,
        )
    decision_finding = _validate_classification_decision(
        payload,
        classification_path=classification_path,
        base_path=base_path,
    )
    if decision_finding is not None:
        return _finding(
            decision_finding,
            candidate,
            "The source classification no longer matches its approved repository decision.",
            "Regenerate classification from the current approved decision registry.",
            proof,
        )
    return None


def validate_source_classification_binding(
    *,
    source_url: str,
    source_class: str,
    classification_artifact: str,
    classification_hash: str,
    base_path: str | Path,
) -> str | None:
    """Return the strict classification rule ID for another proof guard.

    This reuses the same repository-decision, Git HEAD, hash, and local
    execution-attestation checks as Source Map validation without trusting a
    second sidecar classification surface.
    """
    candidate = ClaimCandidate(
        text="classification binding",
        line=1,
        numeric_tokens=[],
        normalized_tokens=frozenset(),
        customer_names=frozenset(),
        has_case_study_link=False,
        requires_approved_quote=False,
        claim_type="factual",
    )
    proof = ProofEntry(
        kind="claim",
        claim="classification binding",
        url=source_url,
        evidence="classification binding",
        status="approved",
        line=1,
        section="faq proof map",
        source_class=source_class,
        claim_type="factual",
        evidence_relation="directly_supports",
        classification_artifact=classification_artifact,
        classification_hash=classification_hash,
    )
    finding = _validate_source_classification(proof, candidate, Path(base_path))
    return str(finding["rule_id"]) if finding is not None else None


def _validate_classification_decision(
    payload: dict,
    *,
    classification_path: Path,
    base_path: Path,
) -> str | None:
    registry = payload.get("registry")
    if not isinstance(registry, dict) or registry.get("authority_mode") != "repository_decision":
        return "source_classification_authority_unsupported"
    workspace_root = _attestation_workspace_root(base_path)
    try:
        decision_path = resolve_artifact(
            registry.get("decision_path"),
            workspace_root=workspace_root,
        )
        snapshot = load_json_object_snapshot(
            decision_path,
            field="source classification decision registry",
        )
    except ValueError:
        return "source_classification_decision_missing"
    if snapshot.sha256 != registry.get("decision_sha256"):
        return "source_classification_decision_tampered"
    if registry.get("decision_path") != SOURCE_DECISIONS_PATH:
        return "source_classification_authority_unsupported"
    try:
        _require_registry_matches_committed_head(
            snapshot,
            workspace_root=workspace_root,
        )
    except ValueError:
        return "source_classification_decision_tampered"
    decision_registry = snapshot.payload
    if (
        set(decision_registry) != {"schema", "revision", "decisions"}
        or decision_registry.get("schema") != SOURCE_DECISIONS_SCHEMA
        or decision_registry.get("revision") != registry.get("revision")
        or not isinstance(decision_registry.get("decisions"), list)
    ):
        return "source_classification_decision_revision_mismatch"
    matches = [
        row for row in decision_registry["decisions"]
        if isinstance(row, dict) and row.get("decision_id") == registry.get("record_id")
    ]
    if len(matches) != 1 or set(matches[0]) != SOURCE_DECISION_FIELDS:
        return "source_classification_decision_missing"
    decision = matches[0]
    expected = {
        "status": "approved",
        "source_url": payload.get("source_url"),
        "hostname": payload.get("publisher", {}).get("hostname"),
        "source_class": payload.get("source_class"),
        "publisher_relationship": payload.get("publisher", {}).get("relationship"),
    }
    if any(decision.get(key) != value for key, value in expected.items()):
        return "source_classification_decision_mismatch"
    return None


def _require_registry_matches_committed_head(
    snapshot: object,
    *,
    workspace_root: str | Path,
) -> None:
    """Require canonical registry bytes to equal the Git-tracked HEAD blob."""
    root = Path(workspace_root).resolve()
    path = getattr(snapshot, "path", None)
    data = getattr(snapshot, "data", None)
    if not isinstance(path, Path) or not isinstance(data, bytes):
        raise ValueError("source decision registry snapshot is invalid")
    expected_path = (root / SOURCE_DECISIONS_PATH).resolve()
    if path != expected_path:
        raise ValueError(
            f"source classification decisions must use {SOURCE_DECISIONS_PATH}"
        )
    try:
        top = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "--show-toplevel"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            timeout=10,
        )
        blob = subprocess.run(
            ["git", "-C", str(root), "show", f"HEAD:{SOURCE_DECISIONS_PATH}"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError) as error:
        raise ValueError(
            "source classification registry must match its committed HEAD blob"
        ) from error
    try:
        top_path = Path(top.stdout.decode("utf-8").strip()).resolve()
    except (UnicodeDecodeError, OSError):
        top_path = Path()
    if top.returncode != 0 or top_path != root or blob.returncode != 0 or blob.stdout != data:
        raise ValueError(
            "source classification registry must match its committed HEAD blob"
        )


def _validate_capture_receipt(
    proof: ProofEntry,
    candidate: ClaimCandidate,
    base_path: Path,
    *,
    expected_method: str,
) -> Optional[Finding]:
    if not proof.capture_receipt or not proof.capture_receipt_hash:
        return _finding(
            "source_capture_receipt_missing",
            candidate,
            "A local fallback is not evidence unless a tool-emitted capture receipt binds it to the cited source.",
            "Capture or extract the source with source_support_capture and bind its receipt and SHA-256.",
            proof,
        )
    receipt_path = _resolve_local_artifact(
        proof.capture_receipt,
        base_path,
        JSON_ARTIFACT_EXTENSION_RE,
    )
    if receipt_path is None:
        return _finding(
            "source_capture_receipt_missing",
            candidate,
            "The declared source-capture receipt is missing or is not JSON.",
            "Use the JSON receipt emitted for this exact captured source.",
            proof,
        )
    if not SHA256_RE.fullmatch(proof.capture_receipt_hash):
        return _finding(
            "source_capture_receipt_hash_invalid",
            candidate,
            "Capture receipt hash must be a 64-character lowercase SHA-256.",
            "Record the exact SHA-256 of the capture receipt.",
            proof,
        )
    if _sha256_file(receipt_path) != proof.capture_receipt_hash:
        return _finding(
            "source_capture_receipt_hash_mismatch",
            candidate,
            "The capture receipt hash does not match its Source Map binding.",
            "Regenerate the receipt binding from the unchanged capture output.",
            proof,
        )
    payload = _read_json_object(receipt_path)
    if payload is None:
        return _finding(
            "source_capture_receipt_invalid",
            candidate,
            "The capture receipt does not satisfy simpro-source-capture-receipt/v1.",
            "Regenerate the capture and receipt with source_support_capture.",
            proof,
        )
    if not verify_mapping_attestation(
        payload,
        purpose=SOURCE_CAPTURE_ATTESTATION_PURPOSE,
        workspace_root=_attestation_workspace_root(base_path),
    ):
        return _finding(
            "source_capture_execution_attestation_invalid",
            candidate,
            "The source-capture receipt lacks a valid workspace execution attestation.",
            "Regenerate it with write_source_capture_receipt in this workspace.",
            proof,
        )
    artifact_path = _resolve_local_artifact(
        proof.artifact,
        base_path,
        LOCAL_ARTIFACT_EXTENSION_RE,
    )
    if artifact_path is None or not _is_strict_capture_payload(payload):
        return _finding(
            "source_capture_receipt_invalid",
            candidate,
            "The capture receipt does not satisfy simpro-source-capture-receipt/v1.",
            "Regenerate the capture and receipt with source_support_capture.",
            proof,
        )
    artifact = payload["artifact"]
    extraction = payload["extraction"]
    if payload["source_url"] != proof.url or artifact["path"] != proof.artifact:
        return _finding(
            "source_capture_binding_mismatch",
            candidate,
            "The capture receipt does not bind the cited URL and declared local artifact.",
            "Use the receipt emitted for this exact URL and artifact path.",
            proof,
        )
    artifact_hash = _sha256_file(artifact_path)
    if artifact_hash != artifact["sha256"] or artifact_hash != extraction["output_sha256"]:
        return _finding(
            "source_capture_artifact_hash_mismatch",
            candidate,
            "The local source artifact changed after capture or extraction.",
            "Recapture the source and regenerate the receipt before using the evidence.",
            proof,
        )
    if extraction["input_sha256"] != payload["source_content_sha256"]:
        return _finding(
            "source_capture_input_hash_mismatch",
            candidate,
            "The extraction input hash does not match the captured source-content hash.",
            "Regenerate the tool-emitted capture receipt.",
            proof,
        )
    if extraction["method"] != expected_method:
        return _finding(
            "source_capture_method_mismatch",
            candidate,
            "The capture extraction method does not fit the cited source type.",
            f"Use extraction method {expected_method} for this source.",
            proof,
        )
    return None


def _general_claim_type(text: str) -> str:
    for claim_type, pattern in GENERAL_CLAIM_PATTERNS:
        if pattern.search(text):
            return claim_type
    return ""


OPINION_SIGNAL_RE = re.compile(
    r"^\s*(?:In my (?:view|opinion)|I (?:think|believe|prefer)|"
    r"From my perspective|We (?:think|believe|prefer))\b",
    re.IGNORECASE,
)
IMPERATIVE_INSTRUCTION_RE = re.compile(
    r"^\s*(?:Review|Verify|Confirm|Check|Choose|Avoid|Use|Open|Create|Add|"
    r"Remove|Compare|Document|Record|Keep|Do not|Don't)\b",
    re.IGNORECASE,
)
SCENARIO_SIGNAL_RE = re.compile(
    r"^\s*(?:Imagine|Suppose|For example,?\s+suppose|Consider a scenario where)\b",
    re.IGNORECASE,
)


def _is_general_claim_exempt(sentence: str) -> bool:
    """Apply only language-observable exemptions, never writer-provided labels."""
    text = _claim_text_for_detection(sentence).strip()
    if OPINION_SIGNAL_RE.search(text):
        return True
    if IMPERATIVE_INSTRUCTION_RE.search(text):
        return True
    if SCENARIO_SIGNAL_RE.search(text):
        return not (
            OUTCOME_SIGNAL_RE.search(text)
            or any(
                claim_type in {"absolute", "causal", "comparative", "guarantee"}
                and pattern.search(text)
                for claim_type, pattern in GENERAL_CLAIM_PATTERNS
            )
        )
    return False


def _validate_source_text_contains_evidence(
    source_text: str,
    proof: ProofEntry,
    candidate: ClaimCandidate,
) -> Optional[Finding]:
    if not _contains_evidence(source_text, proof.evidence):
        return _finding(
            "source_evidence_not_found",
            candidate,
            "Proof evidence was not found in the cited source.",
            "Replace the claim with source-visible wording, update Evidence to an exact visible snippet, or remove the claim.",
            proof,
        )
    return None


def _validate_evidence_claim_fit(
    proof: ProofEntry,
    candidate: ClaimCandidate,
) -> Optional[Finding]:
    if _evidence_contradicts_claim(proof.claim, proof.evidence):
        return _finding(
            "source_evidence_contradicts_claim",
            candidate,
            "The mapped source evidence contradicts the public claim.",
            "Remove or rewrite the claim so it follows the source-visible evidence.",
            proof,
        )
    claim_words = _significant_words(proof.claim)
    evidence_words = _significant_words(proof.evidence)
    minimum_overlap = max(3, math.ceil(len(claim_words) * 0.5))
    if len(claim_words.intersection(evidence_words)) < minimum_overlap:
        return _finding(
            "source_evidence_claim_fit_insufficient",
            candidate,
            "The evidence snippet does not directly support enough of the mapped claim.",
            "Use source-visible evidence that directly entails the complete claim, not a topical fragment.",
            proof,
        )
    return None


def _evidence_contradicts_claim(claim: str, evidence: str) -> bool:
    claim_text = _normalize_text(claim)
    evidence_text = _normalize_text(evidence)
    negations = (" no ", " not ", " never ", " cannot ", " without ", " fails to ")
    padded_claim = f" {claim_text} "
    padded_evidence = f" {evidence_text} "
    claim_negated = any(token in padded_claim for token in negations)
    evidence_negated = any(token in padded_evidence for token in negations)
    if claim_negated != evidence_negated:
        return True
    opposites = (
        ("increase", "decrease"),
        ("improve", "worsen"),
        ("reduce", "increase"),
        ("higher", "lower"),
        ("more", "less"),
        ("faster", "slower"),
        ("better", "worse"),
        ("enable", "prevent"),
    )
    claim_words = set(claim_text.split())
    evidence_words = set(evidence_text.split())
    for left, right in opposites:
        claim_has_left = any(word.startswith(left) for word in claim_words)
        claim_has_right = any(word.startswith(right) for word in claim_words)
        evidence_has_left = any(word.startswith(left) for word in evidence_words)
        evidence_has_right = any(word.startswith(right) for word in evidence_words)
        if (claim_has_left and evidence_has_right) or (claim_has_right and evidence_has_left):
            return True
    return False


def _read_artifact_text(proof: ProofEntry, base_path: Path) -> Optional[str]:
    resolved = _resolve_local_artifact(
        proof.artifact,
        base_path,
        LOCAL_ARTIFACT_EXTENSION_RE,
    )
    if resolved is None:
        return None
    return resolved.read_text(encoding="utf-8")


def _resolve_local_artifact(
    reference: str,
    base_path: Path,
    extension_pattern: re.Pattern[str],
) -> Optional[Path]:
    if not reference or not extension_pattern.search(Path(reference).name):
        return None
    artifact_path = Path(reference)
    candidates = [artifact_path] if artifact_path.is_absolute() else [
        base_path / artifact_path,
        base_path.parent / artifact_path,
        Path.cwd() / artifact_path,
    ]
    for candidate in candidates:
        resolved = candidate.resolve()
        if resolved.exists() and resolved.is_file():
            return resolved
    return None


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _read_json_object(path: Path) -> Optional[dict]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def _is_strict_classification_payload(payload: dict) -> bool:
    if set(payload) != {
        "schema",
        "source_url",
        "source_class",
        "classified_at",
        "publisher",
        "registry",
        "emitter",
        "execution_attestation",
    }:
        return False
    if payload.get("schema") != SOURCE_CLASSIFICATION_SCHEMA:
        return False
    if payload.get("source_class") not in SOURCE_CLASSES:
        return False
    if not _is_nonempty_string(payload.get("source_url")):
        return False
    if not _is_valid_utc_timestamp(payload.get("classified_at")):
        return False
    publisher = payload.get("publisher")
    registry = payload.get("registry")
    emitter = payload.get("emitter")
    if not isinstance(publisher, dict) or set(publisher) != {"hostname", "relationship"}:
        return False
    if not _is_nonempty_string(publisher.get("hostname")):
        return False
    if publisher.get("relationship") not in PUBLISHER_RELATIONSHIPS:
        return False
    if not isinstance(registry, dict) or set(registry) != {
        "authority_mode", "record_id", "revision", "decision_path", "decision_sha256"
    }:
        return False
    if registry.get("authority_mode") != "repository_decision":
        return False
    if not all(_is_nonempty_string(registry.get(key)) for key in (
        "record_id", "revision", "decision_path",
    )):
        return False
    if not _is_sha256(registry.get("decision_sha256")):
        return False
    if not isinstance(emitter, dict) or set(emitter) != {"name", "version"}:
        return False
    return (
        emitter.get("name") == SOURCE_CLASSIFICATION_EMITTER
        and _is_nonempty_string(emitter.get("version"))
    )


def _is_strict_capture_payload(payload: dict) -> bool:
    if set(payload) != {
        "schema",
        "source_url",
        "retrieved_at",
        "source_content_sha256",
        "artifact",
        "extraction",
        "emitter",
        "execution_attestation",
    }:
        return False
    if payload.get("schema") != SOURCE_CAPTURE_SCHEMA:
        return False
    if not _is_nonempty_string(payload.get("source_url")):
        return False
    if not _is_valid_utc_timestamp(payload.get("retrieved_at")):
        return False
    if not _is_sha256(payload.get("source_content_sha256")):
        return False
    artifact = payload.get("artifact")
    extraction = payload.get("extraction")
    emitter = payload.get("emitter")
    if not isinstance(artifact, dict) or set(artifact) != {"path", "sha256"}:
        return False
    if not _is_nonempty_string(artifact.get("path")) or not _is_sha256(artifact.get("sha256")):
        return False
    if not isinstance(extraction, dict) or set(extraction) != {
        "method",
        "tool_name",
        "tool_version",
        "input_sha256",
        "output_sha256",
    }:
        return False
    if extraction.get("method") not in {"html_visible_text", "pdf_text"}:
        return False
    if extraction.get("tool_name") != SOURCE_CAPTURE_EMITTER:
        return False
    if not _is_nonempty_string(extraction.get("tool_version")):
        return False
    if not _is_sha256(extraction.get("input_sha256")) or not _is_sha256(extraction.get("output_sha256")):
        return False
    if not isinstance(emitter, dict) or set(emitter) != {"name", "version"}:
        return False
    return (
        emitter.get("name") == SOURCE_CAPTURE_EMITTER
        and _is_nonempty_string(emitter.get("version"))
    )


def _is_valid_utc_timestamp(value: object) -> bool:
    if not isinstance(value, str) or not RFC3339_UTC_RE.fullmatch(value):
        return False
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError:
        return False
    return parsed.tzinfo == timezone.utc and parsed <= datetime.now(timezone.utc)


def _is_nonempty_string(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _is_sha256(value: object) -> bool:
    return isinstance(value, str) and bool(SHA256_RE.fullmatch(value))


def _required_emitter_text(value: object, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a non-empty string")
    return value.strip()


def _utc_timestamp_now() -> str:
    return (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def _attestation_workspace_root(base_path: Path) -> Path:
    resolved = base_path.resolve()
    for candidate in (resolved, *resolved.parents):
        if (candidate / ".git").exists():
            return candidate
    return resolved


def _finding(
    rule_id: str,
    candidate: ClaimCandidate,
    message: str,
    suggestion: str,
    proof: Optional[ProofEntry] = None,
    severity: str = "error",
    match: Optional[str] = None,
) -> Finding:
    finding: Finding = {
        "rule_id": rule_id,
        "severity": severity,
        "line": candidate.line,
        "column": 1,
        "match": candidate.text if match is None else match,
        "message": message,
        "suggestion": suggestion,
    }
    if candidate.numeric_tokens:
        finding["numeric_tokens"] = candidate.numeric_tokens
    if proof is not None:
        finding["proof_line"] = proof.line
        finding["proof_url"] = proof.url
        finding["evidence"] = proof.evidence
    return finding


def _known_customer_names(proof_entries: Sequence[ProofEntry]) -> List[str]:
    names = set()
    for proof in proof_entries:
        for value in (proof.customer, proof.claim):
            for name in re.findall(r"\b[A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z&]+){1,4}\b", value):
                if not _is_generic_name(name):
                    names.add(name.strip())
    return sorted(names, key=len, reverse=True)


def _customer_names_in_text(text: str, known_customer_names: Sequence[str]) -> List[str]:
    normalized = _normalize_text(text)
    matches = []
    for name in known_customer_names:
        if _normalize_text(name) in normalized:
            matches.append(name)
    return matches


def _has_case_study_link(text: str) -> bool:
    return any("/case-studies/" in match.group(2) for match in MARKDOWN_LINK_RE.finditer(text))


def _is_exact_quote_claim(
    text: str,
    customer_names: Sequence[str],
    has_case_study_link: bool,
) -> bool:
    if not EXACT_QUOTE_RE.search(text):
        return False
    detection_text = _claim_text_for_detection(text)
    return (
        has_case_study_link
        or bool(customer_names)
        or bool(QUOTE_ATTRIBUTION_SIGNAL_RE.search(detection_text))
    )


def _is_review_authority_claim(text: str) -> bool:
    normalized = _normalize_text(text)
    negated_patterns = (
        "without naming a reviewer",
        "without using ratings",
        "without star ratings",
        "no reviewer",
        "no ratings",
        "not use ratings",
        "do not use ratings",
    )
    if any(pattern in normalized for pattern in negated_patterns):
        return False
    return bool(REVIEW_AUTHORITY_SIGNAL_RE.search(text))


def _proof_matches_customer(candidate: ClaimCandidate, proof: ProofEntry) -> bool:
    candidate_names = set(candidate.customer_names)
    if proof.customer:
        proof_names = {proof.customer}
    else:
        proof_names = set(_known_customer_names([proof]))
    if candidate_names and any(
        _normalize_text(proof_name) in _normalize_text(candidate_name)
        or _normalize_text(candidate_name) in _normalize_text(proof_name)
        for candidate_name in candidate_names
        for proof_name in proof_names
    ):
        return True
    return bool(candidate.has_case_study_link and "/case-studies/" in proof.url)


def _text_overlaps(text: str, proof: ProofEntry) -> bool:
    text_words = _significant_words(text)
    proof_words = _significant_words(f"{proof.claim} {proof.evidence}")
    return len(text_words.intersection(proof_words)) >= 2


def _contains_evidence(source_text: str, evidence: str) -> bool:
    return _normalize_text(evidence) in _normalize_text(source_text)


def _extract_visible_text(html: str) -> str:
    soup = BeautifulSoup(html, "lxml")
    for tag in soup(["script", "style", "noscript", "svg"]):
        tag.decompose()
    return soup.get_text(" ", strip=True)


def _cache():
    cache_dir = Path(".cache") / "source_support_guard"
    if Cache is not None:
        try:
            return Cache(str(cache_dir))
        except Exception:
            pass
    return _FileCache(cache_dir)


def _cache_key(url: str) -> str:
    return hashlib.sha256(url.encode("utf-8")).hexdigest()


class _FileCache:
    """Tiny text cache used when diskcache is not installed."""

    def __init__(self, cache_dir: Path, expire_seconds: int = SOURCE_TEXT_CACHE_SECONDS):
        self.cache_dir = cache_dir
        self.expire_seconds = expire_seconds

    def __contains__(self, key: str) -> bool:
        path = self._path(key)
        if not path.exists():
            return False
        if time.time() - path.stat().st_mtime > self.expire_seconds:
            try:
                path.unlink()
            except OSError:
                pass
            return False
        return True

    def __getitem__(self, key: str) -> str:
        return self._path(key).read_text(encoding="utf-8")

    def set(self, key: str, value: str, expire: Optional[int] = None) -> None:
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._path(key).write_text(value, encoding="utf-8")

    def _path(self, key: str) -> Path:
        return self.cache_dir / f"{key}.txt"


def _normalize_key(key: str) -> str:
    return re.sub(r"\s+", " ", key.strip().lower()).strip()


def _clean_field_value(value: str) -> str:
    return value.strip().strip('"').strip("'")


def _normalize_section(section: str) -> str:
    normalized = _normalize_key(section)
    if "customer proof pack" in normalized:
        return "customer proof pack"
    if "source map" in normalized:
        return "source map"
    if "faq proof" in normalized:
        return "faq proof"
    return normalized


def _normalize_text(text: str) -> str:
    text = text.replace("\u2018", "'").replace("\u2019", "'")
    text = text.replace("\u201c", '"').replace("\u201d", '"')
    text = text.replace("\u2013", "-").replace("\u2014", "-")
    text = re.sub(r"[^a-z0-9%$]+", " ", text.lower())
    return re.sub(r"\s+", " ", text).strip()


def _significant_words(text: str) -> set[str]:
    stopwords = {
        "the", "and", "with", "that", "this", "from", "into", "using",
        "used", "can", "for", "its", "their", "same", "amount", "business",
        "resources", "mechanical", "beacon", "shaffer", "simpro",
    }
    return {
        word
        for word in re.findall(r"[a-z0-9%$]+", _normalize_text(text))
        if len(word) > 2 and word not in stopwords
    }


def _is_generic_name(name: str) -> bool:
    normalized = _normalize_text(name)
    generic = {
        "source map",
        "customer proof pack",
        "approved metric",
        "proof url",
        "status approved",
        "hvac operators",
        "specialty trade",
    }
    return normalized in generic


def _main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Check source evidence supports high-risk claims.")
    parser.add_argument("path", help="Markdown file to check")
    parser.add_argument(
        "--fail-on",
        choices=["error", "warning", "none"],
        default="error",
        help="Finding severity that should produce a nonzero exit code.",
    )
    parser.add_argument(
        "--proof-sidecar",
        help="Optional validation sidecar containing Source Map or Proof Pack rows.",
    )
    args = parser.parse_args(argv)

    findings = check_file(args.path, fail_on=args.fail_on, proof_sidecar=args.proof_sidecar)
    payload = {
        "path": args.path,
        "fail_on": args.fail_on,
        "summary": summarize_findings(findings),
        "findings": findings,
    }
    print(json.dumps(payload, indent=2))
    return 1 if should_fail(findings, fail_on=args.fail_on) else 0


if __name__ == "__main__":
    sys.exit(_main())
