"""Refresh customer-proof selector evidence by re-running the selector that wrote it.

The release needs same-day selector evidence (the rater rejects an older connector reference
date and a moved usage ledger). This re-runs the selector recorded in the evidence, with the
topic, title, objective, roles, overrides, limit, and artifact paths recorded there, and writes
the result to the same path. The caller decides connector or nonconnector from the spec (as the
BOM build does): a connector article re-runs the vault-bound selector, a nonconnector article the
nonvault selector, which needs no vault. Evidence whose path or schema belongs to the other branch
is refused before any selector runs.

The BOM's current selections are pinned: each role's selected id in the BOM is passed to the
selector as its override, so a moved usage ledger re-checks freshness and eligibility without
re-choosing. A pinned id the selector no longer offers (the claim lost approval or eligibility)
raises ``PinnedSelectionRejected``; the release treats that as a refused BOM, not an outage.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from datetime import date
from pathlib import Path
from typing import Any

from data_sources.modules.customer_proof.connector_evidence import CONNECTOR_EVIDENCE_SCHEMA
from data_sources.modules.customer_proof.connector_inputs import _selector_input_snapshot
from data_sources.modules.customer_proof.contracts import CustomerProofDataError
from data_sources.modules.customer_proof.nonconnector_contracts import SCHEMA as NONVAULT_EVIDENCE_SCHEMA
from data_sources.modules.customer_proof.nonconnector_contracts import NonVaultProofDataError
from data_sources.modules.customer_proof.nonconnector_persistence import write_nonvault_selector_evidence
from data_sources.modules.customer_proof.selection import build_customer_proof_slate
from data_sources.modules.customer_proof.slate import _write_selector_evidence
from data_sources.modules.production.bom_selector import evidence_path
from data_sources.modules.production.layout import Layout

_TEXT_INPUTS = ("topic", "title", "objective", "article_slug")
# Both selectors word an override outside the verified slate this way.
_REJECTED_OVERRIDE = "Selected customer proof ID is not in the verified"


class PinnedSelectionRejected(ValueError):
    """The selector no longer offers a proof the BOM selected: it lost approval or eligibility."""


def pinned_selections(bom: Mapping[str, Any]) -> dict[str, str]:
    """The BOM's selected id per role; a role the BOM left at "none" binds no proof and stays unpinned."""
    binding = bom.get("customer_proof")
    roles = binding.get("roles") if isinstance(binding, Mapping) else None
    rows = [row for row in roles if isinstance(row, Mapping)] if isinstance(roles, list) else []
    return {
        row["role"]: row["selected_id"]
        for row in rows
        if isinstance(row.get("role"), str) and isinstance(row.get("selected_id"), str)
        and row["selected_id"].strip().casefold() not in ("", "none")
    }


def _branch(nonconnector: bool) -> str:
    return "nonconnector" if nonconnector else "connector"


def _evidence_file(layout: Layout, nonconnector: bool, bom: Mapping[str, Any]) -> Path:
    """The branch's evidence file; a BOM bound to another file is refused."""
    expected = evidence_path(layout, nonconnector)
    binding = (bom.get("customer_proof") or {}).get("evidence")
    if isinstance(binding, Mapping) and isinstance(binding.get("path"), str):
        bound = (layout.root / binding["path"]).resolve()
        if bound != expected.resolve():
            raise ValueError(
                f"the BOM binds selector evidence {binding['path']}, but this {_branch(nonconnector)} "
                f"article's selector evidence is {expected.relative_to(layout.root).as_posix()}"
            )
    return expected


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


def _common_inputs(payload: Mapping[str, Any], pins: Mapping[str, str]) -> dict[str, Any]:
    """The selector inputs every evidence schema records, checked for shape, with the BOM pins applied."""
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
        "selected_overrides": {**dict(inputs.get("selected_overrides") or {}), **pins},
        "rejected_overrides": {role: dict(rows) for role, rows in (inputs.get("rejected_overrides") or {}).items()},
    }


def _refresh_nonvault(
    path: Path, payload: Mapping[str, Any], root: Path, today: date, pins: Mapping[str, str]
) -> None:
    inputs = _common_inputs(payload, pins)
    write_nonvault_selector_evidence(
        path,
        brand=str((payload.get("inputs") or {}).get("brand") or ""),
        reference_date=today,
        index_path=_required_artifact(payload, "index", root),
        ledger_path=_required_artifact(payload, "ledger", root),
        **inputs,
    )


def _refresh_connector(
    path: Path, payload: Mapping[str, Any], root: Path, today: date, pins: Mapping[str, str]
) -> None:
    """Run the connector selector exactly as its CLI does with --slate --evidence-output."""
    inputs = _common_inputs(payload, pins)
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


def refresh_selector_evidence(layout: Layout, nonconnector: bool, bom: Mapping[str, Any]) -> Path:
    """Re-run this branch's selector with the inputs recorded in its evidence, dated today, pinned to the BOM."""
    path = _evidence_file(layout, nonconnector, bom)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise ValueError(f"customer-proof selector evidence {path} is unreadable: {error}") from error
    schema = payload.get("schema") if isinstance(payload, Mapping) else None
    expected = NONVAULT_EVIDENCE_SCHEMA if nonconnector else CONNECTOR_EVIDENCE_SCHEMA
    if schema != expected:
        raise ValueError(
            f"customer-proof selector evidence {path.name} has schema {schema!r}; "
            f"a {_branch(nonconnector)} article needs {expected}"
        )
    refresh = _refresh_nonvault if nonconnector else _refresh_connector
    try:
        refresh(path, payload, layout.root, date.today(), pinned_selections(bom))
    except (CustomerProofDataError, NonVaultProofDataError) as error:
        if str(error).startswith(_REJECTED_OVERRIDE):
            raise PinnedSelectionRejected(f"the BOM's proof selection is no longer offered: {error}") from error
        raise
    return path


__all__ = ["PinnedSelectionRejected", "pinned_selections", "refresh_selector_evidence"]
