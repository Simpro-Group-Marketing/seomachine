"""Captured customer-proof index and ledger helpers for readiness."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Mapping


def load_index_for_comparison(
    path: str | Path,
    payload: Mapping[str, Any] | None = None,
) -> dict[str, object]:
    """Validate a captured index or use the legacy path adapter."""
    index_path = Path(path)
    if payload is None and not index_path.exists():
        return _index_error(
            "customer_proof_index_missing",
            f"Customer proof index is required to compare overused proof sources, but it was not found: {index_path}",
            "Pass --proof-index context/customer-proof-index.json or create the proof index before running publish readiness.",
        )
    try:
        value = dict(payload) if payload is not None else json.loads(
            index_path.read_text(encoding="utf-8")
        )
    except json.JSONDecodeError as error:
        return _index_error(
            "customer_proof_index_invalid",
            f"Customer proof index is not valid JSON: {index_path}: {error}",
            "Fix customer-proof-index.json so overused proof can be compared against approved alternatives.",
        )
    if not isinstance(value, dict) or not isinstance(value.get("proof", []), list):
        return _index_error(
            "customer_proof_index_invalid",
            f"Customer proof index must be an object with a proof list: {index_path}",
            "Fix customer-proof-index.json so overused proof can be compared against approved alternatives.",
        )
    return {"error": False, "index": value}


def selector_inputs(
    index: Mapping[str, Any],
    ledger: Mapping[str, Any],
    validated_claim_set: object | None,
) -> object | None:
    """Build the selector's immutable input view without reopening artifacts."""
    if validated_claim_set is None:
        return None
    return SimpleNamespace(
        index=dict(index),
        ledger=dict(ledger),
        receipt_claims=validated_claim_set,
    )


def _index_error(rule_id: str, message: str, suggestion: str) -> dict[str, object]:
    return {
        "error": True,
        "rule_id": rule_id,
        "message": message,
        "suggestion": suggestion,
        "index": {},
    }


__all__ = ["load_index_for_comparison", "selector_inputs"]
