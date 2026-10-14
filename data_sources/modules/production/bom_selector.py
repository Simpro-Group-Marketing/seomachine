"""Bind the customer-proof selector evidence: every BOM proof item must be a selected candidate."""

from __future__ import annotations

import copy
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from data_sources.modules.customer_proof.connector_evidence import CONNECTOR_EVIDENCE_SCHEMA
from data_sources.modules.customer_proof.nonconnector_contracts import SCHEMA as NONVAULT_EVIDENCE_SCHEMA
from data_sources.modules.customer_proof.nonconnector_evidence import verify_nonconnector_selector_evidence
from data_sources.modules.production.bom_artifacts import read_bound
from data_sources.modules.production.layout import Layout


def evidence_path(layout: Layout, nonconnector: bool) -> Path:
    """Return the selector evidence file the selectors write for this article."""
    return layout.nonvault_customer_proof_evidence if nonconnector else layout.customer_proof_evidence


def _role_errors(roles: Any, label: str) -> list[str]:
    if not isinstance(roles, list) or not roles:
        return [f"{label} roles must be a non-empty list"]
    return [
        f"{label} roles[{index}] needs text role and selected_id"
        for index, row in enumerate(roles)
        if not (isinstance(row, Mapping) and isinstance(row.get("role"), str) and isinstance(row.get("selected_id"), str))
    ]


def _role_record(row: Mapping[str, Any], inputs: Mapping[str, Any]) -> dict[str, Any]:
    """Copy one role's selection exactly as the selector recorded it."""
    rejected = row.get("rejected_overrides")
    if rejected is None:
        all_rejected = inputs.get("rejected_overrides")
        rejected = all_rejected.get(row["role"], {}) if isinstance(all_rejected, Mapping) else {}
    return {
        "role": row["role"],
        "selected_id": row["selected_id"],
        "candidate_ids": copy.deepcopy(row.get("candidate_ids") or []),
        "selected_candidate": copy.deepcopy(row.get("selected_candidate")),
        "no_fit_reason": str(row.get("no_fit_reason") or ""),
        "rejected_overrides": copy.deepcopy(rejected),
    }


def _unselected_errors(proof: Sequence[Mapping[str, Any]], roles: Sequence[Mapping[str, Any]]) -> list[str]:
    selected = {row["selected_id"] for row in roles if row["selected_id"].casefold() != "none"}
    return [
        f"proof {item['id']} claim_id {item['claim_id']} is not a selected candidate in the customer-proof selector evidence"
        for item in proof
        if item["claim_id"] not in selected
    ]


def bind_selector_evidence(
    layout: Layout, proof: Sequence[Mapping[str, Any]], nonconnector: bool
) -> dict[str, Any]:
    """Bind the selector evidence and require every proof item to be one of its selections."""
    path = evidence_path(layout, nonconnector)
    label = f"customer-proof selector evidence {path.name}"
    payload, binding = read_bound(layout, path, label)
    expected = NONVAULT_EVIDENCE_SCHEMA if nonconnector else CONNECTOR_EVIDENCE_SCHEMA
    if payload.get("schema") != expected:
        raise ValueError(f"{label} selector evidence schema must be {expected}, found: {payload.get('schema')!r}")
    errors = _role_errors(payload.get("roles"), label)
    if errors:
        raise ValueError("\n".join(errors))
    if nonconnector and verify_nonconnector_selector_evidence(payload) is None:
        raise ValueError(
            f"{label} failed verification: the nonvault selector does not reproduce it from its bound index and "
            "ledger (a publish moves the usage ledger); re-run the nonvault customer proof selector, then rebuild"
        )
    roles = payload["roles"]
    errors = _unselected_errors(proof, roles)
    if errors:
        raise ValueError("\n".join(errors))
    inputs = payload.get("inputs") if isinstance(payload.get("inputs"), Mapping) else {}
    return {
        "evidence": binding,
        "schema": expected,
        "selection_outcome": str(payload.get("selection_outcome") or ""),
        "roles": [_role_record(row, inputs) for row in roles],
    }
