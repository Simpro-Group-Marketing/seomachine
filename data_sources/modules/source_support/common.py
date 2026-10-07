"""
Source Support Guard

Strict source-support validation for high-risk public claims. General claims
use an exact Claim/Claim type/Evidence relation mapping plus a hash-bound
``simpro-source-classification/v1`` registry export. Local PDF extractions and
unreachable-HTML fallbacks are accepted only with a hash-bound
``simpro-source-capture-receipt/v1`` tool receipt; an authored text file alone
is never proof.
"""
# ruff: noqa: F401

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import socket
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Dict, List, Optional, Sequence
from urllib.parse import urlsplit

from bs4 import BeautifulSoup

try:
    from ..blog_assembly_contract import (
        atomic_write_json,
        canonical_snapshot_artifact,
        load_json_object_snapshot,
        resolve_artifact,
    )
    from ..execution_attestation import attest_mapping, verify_mapping_attestation
    from ..guard_common import Finding, should_fail, summarize_findings
    from ..image_placeholder import is_production_image_placeholder_line
    from ..public_http import (
        PublicHttpTransport,
        SOURCE_VISIBLE_TEXT_POLICY,
        canonical_request_identity,
    )
    from ..claim_patterns import GENERAL_CLAIM_PATTERNS
    from ..proof_sidecar import compose_with_sidecar, load_sidecar_content
    from ..proof_link_policy import (
        CitationRequirement,
        ProofLinkReport,
        analyze_proof_links,
    )
    from ..numeric_claim_source_guard import (
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
    from image_placeholder import is_production_image_placeholder_line
    from public_http import (
        PublicHttpTransport,
        SOURCE_VISIBLE_TEXT_POLICY,
        canonical_request_identity,
    )
    from claim_patterns import GENERAL_CLAIM_PATTERNS
    from proof_sidecar import compose_with_sidecar, load_sidecar_content
    from proof_link_policy import (
        CitationRequirement,
        ProofLinkReport,
        analyze_proof_links,
    )
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
PDF_EXTENSION_RE = re.compile(r"\.pdf(?:$|[?#])", re.IGNORECASE)
LOCAL_ARTIFACT_EXTENSION_RE = re.compile(r"\.(?:md|txt|csv|tsv|json)$", re.IGNORECASE)
JSON_ARTIFACT_EXTENSION_RE = re.compile(r"\.json$", re.IGNORECASE)
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
RFC3339_UTC_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?Z$"
)
SOURCE_CAPTURE_SCHEMA = "simpro-source-capture-receipt/v1"
SOURCE_CLASSIFICATION_SCHEMA = "simpro-source-classification/v1"
SOURCE_DECISIONS_SCHEMA = "simpro-source-classification-decisions/v1"
SOURCE_DECISIONS_PATH = "context/source-classification-decisions.json"
SOURCE_DECISION_FIELDS = frozenset({
    "decision_id",
    "status",
    "source_url",
    "hostname",
    "source_class",
    "publisher_relationship",
})
SOURCE_CAPTURE_EMITTER = "source_support_capture"
SOURCE_CLASSIFICATION_EMITTER = "source_registry_export"
SOURCE_CAPTURE_EMITTER_VERSION = "1.0.0"
SOURCE_CLASSIFICATION_EMITTER_VERSION = "1.0.0"
SOURCE_CAPTURE_ATTESTATION_PURPOSE = SOURCE_CAPTURE_SCHEMA
SOURCE_CLASSIFICATION_ATTESTATION_PURPOSE = SOURCE_CLASSIFICATION_SCHEMA
MARKDOWN_IMAGE_LINE_RE = re.compile(r"^\s*!\[[^\]\r\n]*\]\([^)]+?\)\s*$")
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
SELF_NAVIGATION_RE = re.compile(
    r"^(?:This|The)\s+(?:article|example|guide|section)\s+(?:can\s+)?helps?\s+"
    r"(?:readers?|you)\s+(?:find|locate|navigate|understand|use)\b",
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


__all__ = ["ClaimCandidate", "Fetcher", "ProofEntry", "SourceSupportError"]
