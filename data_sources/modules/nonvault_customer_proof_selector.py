"""Compatibility facade for nonconnector customer-proof selection."""

from __future__ import annotations

import sys
from pathlib import Path

if not __package__:  # pragma: no cover - supports direct script execution.
    repository_root = str(Path(__file__).resolve().parents[2])
    if repository_root not in sys.path:
        sys.path.insert(0, repository_root)
    __package__ = "data_sources.modules"

from .customer_proof.nonconnector_cli import (
    _main,
    _parse_rejected,
    _parse_roles,
    _parse_selected,
)
from .customer_proof.nonconnector_contracts import (
    SCHEMA,
    STOPWORDS,
    SUPPORTED_BRAND_HOSTS,
    SUPPORTED_REVIEW_PAGES,
    SUPPORTED_ROLES,
    SUPPORTED_SOURCE_TYPES,
    NonVaultProofDataError,
)
from .customer_proof.nonconnector_eligibility import (
    _brand_key,
    _canonical_brand,
    _eligible_source,
    _experience_binding,
    _recent_uses,
    _relevance_score,
    _source_weight,
    _supports_role,
    _tokens,
    _values,
)
from .customer_proof.nonconnector_inputs import _file_sha256, _read_json
from .customer_proof.nonconnector_persistence import (
    build_nonvault_customer_proof_slate,
    write_nonvault_selector_evidence,
)
from .customer_proof.nonconnector_selection import select_nonvault_customer_proofs

__all__ = [
    "SCHEMA",
    "STOPWORDS",
    "SUPPORTED_BRAND_HOSTS",
    "SUPPORTED_REVIEW_PAGES",
    "SUPPORTED_ROLES",
    "SUPPORTED_SOURCE_TYPES",
    "NonVaultProofDataError",
    "_brand_key",
    "_canonical_brand",
    "_eligible_source",
    "_experience_binding",
    "_file_sha256",
    "_main",
    "_parse_rejected",
    "_parse_roles",
    "_parse_selected",
    "_read_json",
    "_recent_uses",
    "_relevance_score",
    "_source_weight",
    "_supports_role",
    "_tokens",
    "_values",
    "build_nonvault_customer_proof_slate",
    "select_nonvault_customer_proofs",
    "write_nonvault_selector_evidence",
]

if __name__ == "__main__":
    raise SystemExit(_main())
