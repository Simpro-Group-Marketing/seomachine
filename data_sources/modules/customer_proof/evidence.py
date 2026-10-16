"""Dispatch hash-bound evidence to connector-specific validators."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .connector_evidence import (
    CONNECTOR_EVIDENCE_SCHEMA,
    verify_connector_selector_evidence,
)
from .evidence_common import (
    MAX_SELECTOR_EVIDENCE_BYTES,
    file_sha256,
    load_selector_evidence,
)
from .nonconnector_contracts import SCHEMA as NONVAULT_SELECTOR_EVIDENCE_SCHEMA
from .nonconnector_evidence import (
    verify_nonconnector_selector_evidence,
)


def verify_selector_evidence_roles(
    proof_sidecar_content: str,
    proof_sidecar_path: str | None,
) -> dict[str, dict[str, Any]] | None:
    evidence = load_selector_evidence(proof_sidecar_content, proof_sidecar_path)
    if evidence is None:
        return None
    schema = evidence.get("schema")
    if schema == NONVAULT_SELECTOR_EVIDENCE_SCHEMA:
        return verify_nonconnector_selector_evidence(evidence)
    if schema == CONNECTOR_EVIDENCE_SCHEMA:
        return verify_connector_selector_evidence(evidence)
    return None


def _file_sha256(path: Path) -> str:
    return file_sha256(path)


__all__ = [
    "MAX_SELECTOR_EVIDENCE_BYTES",
    "_file_sha256",
    "verify_selector_evidence_roles",
]
