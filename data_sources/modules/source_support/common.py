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
import sys
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
    from ..public_http import PublicHttpTransport
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
    from public_http import PublicHttpTransport
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
            r"contributes? to|helps?|improves?|reduces?|increases?|decreases?|prevents?|"
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




_PROXY_NAMES = ['_attestation_workspace_root', '_blank_reader_supplied_worksheet_tables', '_candidate_is_proof_not_required', '_clean_field_value', '_contains_evidence', '_customer_names_in_text', '_evidence_contradicts_claim', '_extract_claim_candidates', '_extract_proof_entries', '_extract_visible_text', '_finding', '_general_claim_type', '_has_case_study_link', '_is_exact_quote_claim', '_is_general_claim_exempt', '_is_generic_name', '_is_nonempty_string', '_is_review_authority_claim', '_is_sha256', '_is_strict_capture_payload', '_is_strict_classification_payload', '_is_valid_utc_timestamp', '_known_customer_names', '_main', '_matching_proofs', '_normalize_key', '_normalize_section', '_normalize_text', '_parse_proof_fields', '_policy_aligned_candidates', '_proof_matches_customer', '_read_artifact_text', '_read_json_object', '_require_registry_matches_committed_head', '_required_emitter_text', '_requirement_has_candidate', '_resolve_local_artifact', '_sha256_file', '_significant_words', '_split_claim_sentences', '_text_overlaps', '_utc_timestamp_now', '_validate_capture_receipt', '_validate_classification_decision', '_validate_evidence_claim_fit', '_validate_general_claim_contract', '_validate_numeric_proof_cluster', '_validate_proof_entry', '_validate_source_classification', '_validate_source_text_contains_evidence', 'check_content', 'check_file', 'fetch_source_text', 'format_findings', 'require_source_support', 'validate_source_classification_binding', 'write_source_capture_receipt', 'write_source_classification_artifact']

def _proxy(name: str):
    def call(*args, **kwargs):
        module = sys.modules.get("data_sources.modules.source_support_guard")
        module = module or sys.modules.get("source_support_guard") or sys.modules.get("__main__")
        target = getattr(module, name, None)
        if target is None or target is call:
            raise RuntimeError(f"source-support dependency is unavailable: {name}")
        return target(*args, **kwargs)
    return call

for _proxy_name in _PROXY_NAMES:
    globals()[_proxy_name] = _proxy(_proxy_name)

__all__ = [name for name in globals() if not name.startswith("__")]
