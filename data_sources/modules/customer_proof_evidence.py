"""Compatibility facade for customer-proof selector evidence validation."""

from __future__ import annotations

import sys
from pathlib import Path

if not __package__:  # pragma: no cover - supports top-level imports.
    repository_root = str(Path(__file__).resolve().parents[2])
    if repository_root not in sys.path:
        sys.path.insert(0, repository_root)
    __package__ = "data_sources.modules"

from .customer_proof.evidence import (
    MAX_SELECTOR_EVIDENCE_BYTES,
    _experience_candidate_binding,
    _file_sha256,
    _nonvault_experience_candidate_binding,
    _selector_evidence_path,
    _verify_nonvault_selector_evidence,
    verify_selector_evidence_roles,
)

__all__ = [
    "MAX_SELECTOR_EVIDENCE_BYTES",
    "_experience_candidate_binding",
    "_file_sha256",
    "_nonvault_experience_candidate_binding",
    "_selector_evidence_path",
    "_verify_nonvault_selector_evidence",
    "verify_selector_evidence_roles",
]
