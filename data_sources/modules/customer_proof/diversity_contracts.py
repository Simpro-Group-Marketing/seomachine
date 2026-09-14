"""Customer-proof diversity policy constants."""

from __future__ import annotations

import re
from pathlib import Path

DEFAULT_LEDGER_PATH = Path("context/customer-proof-usage-ledger.json")

DEFAULT_INDEX_PATH = Path("context/customer-proof-index.json")

CASE_STUDY_URL_RE = re.compile(
    r"https?://[^\s),|]+(?:/case-studies/[^\s),|]+|/resources/case-study-[^\s),|]+)",
    re.IGNORECASE,
)

ANY_CUSTOMER_PROOF_URL_RE = re.compile(
    r"https?://[^\s),|]+(?:/case-studies/|/resources/case-study-|/reviews(?:/|$)|/customers?/|/customer-(?:story|stories|success|case-study|testimonials?)(?:/|$)|/testimonials?/)[^\s),|]*",
    re.IGNORECASE,
)

CUSTOMER_PROOF_HEADING_RE = re.compile(
    r"^\s*(?:#{1,6}\s+)?Customer Proof Pack:?\s*$",
    re.IGNORECASE,
)

SELECTION_DECISION_HEADING_RE = re.compile(
    r"^\s*(?:#{1,6}\s+)?Customer Proof Selection Decision:?\s*$",
    re.IGNORECASE,
)

CUSTOMER_PROOF_SLATE_HEADING_RE = re.compile(
    r"^\s*(?:#{1,6}\s+)?Customer Proof Slate:?\s*$",
    re.IGNORECASE,
)

SELECTED_CUSTOMER_PROOF_MINING_HEADING_RE = re.compile(
    r"^\s*(?:#{1,6}\s+)?Selected Customer Proof Mining:?\s*$",
    re.IGNORECASE,
)

NEXT_PROOF_HEADING_RE = re.compile(
    r"^\s*(?:#{1,6}\s+)?(?:PAA/FAQ Provenance|Metric Proof Pack|Source Map|"
    r"Customer Proof Slate|Selected Customer Proof Mining|Customer Proof Selection Decision|"
    r"E-E-A-T Proof Map|FAQ Proof Map|Review Story Selection|Review Site Theme Selection|"
    r"Structured data plan|Fred Voccola Authority Selection)\s*$",
    re.IGNORECASE,
)

NEXT_DECISION_HEADING_RE = re.compile(
    r"^\s*(?:#{1,6}\s+)?(?:PAA/FAQ Provenance|Metric Proof Pack|Source Map|"
    r"Customer Proof Slate|Selected Customer Proof Mining|Customer Proof Pack|E-E-A-T Proof Map|"
    r"FAQ Proof Map|Review Story Selection|Review Site Theme Selection|Structured data plan|Fred Voccola Authority Selection)\s*$",
    re.IGNORECASE,
)

NEXT_SLATE_HEADING_RE = re.compile(
    r"^\s*(?:#{1,6}\s+)?(?:PAA/FAQ Provenance|Metric Proof Pack|Source Map|"
    r"Selected Customer Proof Mining|Customer Proof Pack|Customer Proof Selection Decision|"
    r"E-E-A-T Proof Map|FAQ Proof Map|Review Story Selection|Review Site Theme Selection|"
    r"Structured data plan|Fred Voccola Authority Selection)\s*$",
    re.IGNORECASE,
)

NEXT_MINING_HEADING_RE = re.compile(
    r"^\s*(?:#{1,6}\s+)?(?:PAA/FAQ Provenance|Metric Proof Pack|Source Map|"
    r"Customer Proof Slate|Customer Proof Pack|Customer Proof Selection Decision|"
    r"E-E-A-T Proof Map|FAQ Proof Map|Review Story Selection|Review Site Theme Selection|"
    r"Structured data plan|Fred Voccola Authority Selection)\s*$",
    re.IGNORECASE,
)

REVIEW_PROOF_HEADING_RE = re.compile(
    r"^\s*(?:#{1,6}\s+)?(?:Review Story Selection|Review Site Theme Selection):?\s*$",
    re.IGNORECASE,
)

BULLET_FIELD_RE = re.compile(r"^\s*[-*+]\s*(?P<key>[^:]+):\s*(?P<value>.*?)\s*$")

EXACT_QUOTE_RE = re.compile(r"(?:\"[^\"]{20,}\"|\u201c[^\u201d]{20,}\u201d)")

QUOTE_CONTEXT_RE = re.compile(
    r"\b(?:said|says|reviewer|testimonial|customer review|case study|quoted|according to)\b",
    re.IGNORECASE,
)

NON_CASE_STUDY_KEYS = {
    "quote matrix candidates",
    "reference candidates",
    "references candidates",
    "customer story candidates",
    "customer stories candidates",
    "review-site experience evidence",
    "review site experience evidence",
}

BLOCKED_OR_EMPTY_RE = re.compile(
    r"^(?:none|none used|none collected|not collected|not checked|not reviewed|"
    r"not searched|n/a|na|no)$",
    re.IGNORECASE,
)

NONE_RESULT_RE = re.compile(
    r"^(?:none|none found|none used|none collected|not found|not usable|no usable|"
    r"n/a|na|no)$",
    re.IGNORECASE,
)

REQUIRED_SLATE_ROLES = ("metric", "quote", "theme")

EMPTY_SELECTION_VALUES = {"", "none", "none used", "n/a", "na", "no", "not selected"}
