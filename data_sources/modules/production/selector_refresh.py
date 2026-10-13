"""Refresh customer-proof selector evidence by re-running the selector that wrote it.

The release needs same-day selector evidence (the rater rejects an older connector reference
date and a moved usage ledger). This re-runs the selector recorded in the evidence, with the
topic, title, objective, roles, overrides, limit, and artifact paths recorded there, and writes
the result to the same path. Connector evidence re-runs the vault-bound selector; nonconnector
evidence re-runs the nonvault selector, which needs no vault.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from datetime import date
from pathlib import Path
from typing import Any

from data_sources.modules.customer_proof.connector_evidence import CONNECTOR_EVIDENCE_SCHEMA
from data_sources.modules.customer_proof.connector_inputs import _selector_input_snapshot
from data_sources.modules.customer_proof.nonconnector_contracts import SCHEMA as NONVAULT_EVIDENCE_SCHEMA
from data_sources.modules.customer_proof.nonconnector_persistence import write_nonvault_selector_evidence
from data_sources.modules.customer_proof.selection import build_customer_proof_slate
from data_sources.modules.customer_proof.slate import _write_selector_evidence
from data_sources.modules.production.layout import Layout

_TEXT_INPUTS = ("topic", "title", "objective", "article_slug")


def _evidence_file(layout: Layout, bom: Mapping[str, Any]) -> Path:
    binding = (bom.get("customer_proof") or {}).get("evidence")
    if isinstance(binding, Mapping) and isinstance(binding.get("path"), str):
        return layout.root / binding["path"]
    for path in (layout.customer_proof_evidence, layout.nonvault_customer_proof_evidence):
        if path.is_file():
            return path
    raise ValueError("no customer-proof selector evidence to refresh")


def _artifact(payload: Mapping[str, Any], name: str, root: Path) -> Path | None:
    record = (payload.get("artifacts") or {}).get(name)
    if not isinstance(record, Mapping) or not isinstance(record.get("path"), str):
        return None
    path = Path(record["path"])
    return path if path.is_absolute() else root / path


def _required_artifact(payload: Mapping[str, Any], name: str, root: Path) -> Path:
    path = _artifact(payload, name, root)
    if path is None:
        raise ValueError(f"selector evidence does not record its {name} artifact")
    return path


def _common_inputs(payload: Mapping[str, Any]) -> dict[str, Any]:
    """The selector inputs every evidence schema records, checked for shape."""
    inputs = payload.get("inputs")
    if not isinstance(inputs, Mapping):
        raise ValueError("selector evidence does not record its inputs")
    missing = [key for key in (*_TEXT_INPUTS, "roles", "limit") if key not in inputs]
    if missing:
        raise ValueError(f"selector evidence inputs are missing: {', '.join(missing)}")
    return {
        **{key: str(inputs[key]) for key in _TEXT_INPUTS},
        "roles": list(inputs["roles"]),
        "require_eeat_story": inputs.get("require_eeat_story") is True,
        "limit": int(inputs["limit"]),
        "selected_overrides": dict(inputs.get("selected_overrides") or {}),
        "rejected_overrides": {role: dict(rows) for role, rows in (inputs.get("rejected_overrides") or {}).items()},
    }


def _refresh_nonvault(path: Path, payload: Mapping[str, Any], root: Path, today: date) -> None:
    inputs = _common_inputs(payload)
    write_nonvault_selector_evidence(
        path,
        brand=str((payload.get("inputs") or {}).get("brand") or ""),
        reference_date=today,
        index_path=_required_artifact(payload, "index", root),
        ledger_path=_required_artifact(payload, "ledger", root),
        **inputs,
    )


def _refresh_connector(path: Path, payload: Mapping[str, Any], root: Path, today: date) -> None:
    """Run the connector selector exactly as its CLI does with --slate --evidence-output."""
    inputs = _common_inputs(payload)
    allow_no_proof = (payload.get("inputs") or {}).get("allow_no_proof") is True
    paths = {name: _required_artifact(payload, name, root) for name in ("ledger", "context_pack", "context_receipt")}
    claim_lookup = _artifact(payload, "claim_lookup", root)
    with _selector_input_snapshot(
        ledger_path=paths["ledger"],
        context_pack=paths["context_pack"],
        context_receipt=paths["context_receipt"],
        claim_lookup_evidence=claim_lookup,
    ) as snapshot:
        role_evidence: list[dict[str, Any]] = []
        build_customer_proof_slate(
            inputs["topic"],
            ledger_path=paths["ledger"],
            context_pack=paths["context_pack"],
            context_receipt=paths["context_receipt"],
            allow_no_proof=allow_no_proof,
            reference_date=today,
            claim_lookup_evidence=snapshot.claim_lookup,
            _role_evidence=role_evidence,
            _input_snapshot=snapshot,
            **{key: value for key, value in inputs.items() if key != "topic"},
        )
        _write_selector_evidence(
            path,
            allow_no_proof=allow_no_proof,
            reference_date=today,
            role_evidence=role_evidence,
            input_snapshot=snapshot,
            **inputs,
        )


def refresh_selector_evidence(layout: Layout, bom: Mapping[str, Any]) -> Path:
    """Re-run the selector recorded in the BOM's bound evidence, dated today; return the evidence path."""
    path = _evidence_file(layout, bom)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise ValueError(f"customer-proof selector evidence {path} is unreadable: {error}") from error
    schema = payload.get("schema") if isinstance(payload, Mapping) else None
    refresh = {NONVAULT_EVIDENCE_SCHEMA: _refresh_nonvault, CONNECTOR_EVIDENCE_SCHEMA: _refresh_connector}.get(schema)
    if refresh is None:
        raise ValueError(f"customer-proof selector evidence {path.name} has an unknown schema: {schema!r}")
    refresh(path, payload, layout.root, date.today())
    return path


__all__ = ["refresh_selector_evidence"]
