"""Compatibility facade for connector-bound customer-proof selection."""

from __future__ import annotations

import sys
from pathlib import Path

if not __package__:  # pragma: no cover - supports direct script execution.
    repository_root = str(Path(__file__).resolve().parents[2])
    if repository_root not in sys.path:
        sys.path.insert(0, repository_root)
    __package__ = "data_sources.modules"

from .customer_proof.connector_inputs import _validate_evidence_output_paths
from .customer_proof.contracts import (
    APPROVAL_WEIGHT,
    CUSTOMER_PROOF_CANDIDATES_AVAILABLE_OUTCOME,
    CUSTOMER_PROOF_USE_MODES,
    DEFAULT_INDEX_PATH,
    DEFAULT_LEDGER_PATH,
    HISTORICAL_USE_SCORE_PENALTY,
    NO_BOUND_CUSTOMER_PROOF_MESSAGE,
    NO_FIT_CUSTOMER_PROOF_OUTCOME,
    NO_FIT_CUSTOMER_PROOF_REASON,
    RECENT_USE_SCORE_PENALTY,
    SLATE_ROLES,
    SOURCE_INTENT_BONUS,
    SOURCE_INTENT_PATTERNS,
    SOURCE_TYPE_WEIGHT,
    STOPWORDS,
    CustomerProofDataError,
)
from .customer_proof.selection import (
    build_customer_proof_slate,
    select_customer_proofs,
)
from .customer_proof.selector_cli import _main

__all__ = [
    "APPROVAL_WEIGHT",
    "CUSTOMER_PROOF_CANDIDATES_AVAILABLE_OUTCOME",
    "CUSTOMER_PROOF_USE_MODES",
    "CustomerProofDataError",
    "DEFAULT_INDEX_PATH",
    "DEFAULT_LEDGER_PATH",
    "HISTORICAL_USE_SCORE_PENALTY",
    "NO_BOUND_CUSTOMER_PROOF_MESSAGE",
    "NO_FIT_CUSTOMER_PROOF_OUTCOME",
    "NO_FIT_CUSTOMER_PROOF_REASON",
    "RECENT_USE_SCORE_PENALTY",
    "SLATE_ROLES",
    "SOURCE_INTENT_BONUS",
    "SOURCE_INTENT_PATTERNS",
    "SOURCE_TYPE_WEIGHT",
    "STOPWORDS",
    "_main",
    "_validate_evidence_output_paths",
    "build_customer_proof_slate",
    "select_customer_proofs",
]

if __name__ == "__main__":
    raise SystemExit(_main())
