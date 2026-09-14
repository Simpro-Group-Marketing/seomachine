"""Shared connector-bound customer-proof contracts."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Mapping

DEFAULT_INDEX_PATH = Path("context/customer-proof-index.json")

DEFAULT_LEDGER_PATH = Path("context/customer-proof-usage-ledger.json")

FindingDict = Dict[str, Any]

SLATE_ROLES = {"experience_story", "metric", "quote", "theme"}

CUSTOMER_PROOF_USE_MODES = {"public_metric", "exact_quote", "public_paraphrase"}

NO_FIT_CUSTOMER_PROOF_OUTCOME = "no_fit_customer_proof"

CUSTOMER_PROOF_CANDIDATES_AVAILABLE_OUTCOME = "customer_proof_candidates_available"

NO_FIT_CUSTOMER_PROOF_REASON = (
    "No customer proof selected because the selector evaluated the current "
    "connector-bound proof inventory and found no article-relevant approved "
    "customer proof for this role; public copy must omit customer proof, named "
    "customer claims, review stories, exact quotes, testimonials, and customer "
    "metrics for the unsupported role."
)

NO_BOUND_CUSTOMER_PROOF_MESSAGE = (
    "no approved claims bound to the customer proof inventory"
)

class CustomerProofDataError(RuntimeError):
    """Raised when receipt-backed customer proof cannot be verified."""

@dataclass(frozen=True)
class _ApprovedClaimBinding:
    claim: Any
    binding_source: str

@dataclass(frozen=True)
class _ArtifactSnapshot:
    label: str
    path: Path
    content: bytes
    sha256: str
    json_object: FindingDict | None = None

    def evidence_record(self) -> FindingDict:
        return {"path": str(self.path), "sha256": self.sha256}

@dataclass(frozen=True)
class _SelectorInputSnapshot:
    artifacts: Mapping[str, _ArtifactSnapshot]
    index: FindingDict
    ledger: FindingDict
    context_pack_path: Path
    context_receipt_path: Path
    receipt_claims: Any

SOURCE_TYPE_WEIGHT = {
    "quote_matrix": 18,
    "reference": 17,
    "customer_story": 16,
    "review_site": 12,
    "case_study": 10,
}

SOURCE_INTENT_BONUS = 18

RECENT_USE_SCORE_PENALTY = 20

HISTORICAL_USE_SCORE_PENALTY = 2

SOURCE_INTENT_PATTERNS = {
    "review_site": (
        "review",
        "reviews",
        "reviewer",
        "review story",
        "review site",
        "g2",
        "capterra",
        "google review",
        "software advice",
        "softwareadvice",
    ),
    "quote_matrix": ("quote matrix",),
    "reference": ("reference", "references"),
    "customer_story": ("customer story", "customer stories"),
    "case_study": ("case study", "case studies"),
}

APPROVAL_WEIGHT = {
    "approved": 24,
    "ready": 18,
    "candidate": 8,
    "blocked": -8,
    "rejected": -20,
}

STOPWORDS = {
    "about",
    "after",
    "and",
    "are",
    "best",
    "business",
    "businesses",
    "for",
    "from",
    "guide",
    "into",
    "job",
    "jobs",
    "software",
    "that",
    "the",
    "this",
    "with",
    "your",
}
