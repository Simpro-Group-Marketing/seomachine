"""Preflight session adapters owned by blog assembly BOM validation."""

from __future__ import annotations

from typing import Any, Mapping


def load_receipts(
    guard: Any,
    captured: Any,
    rows: list[Any],
    root: Any,
) -> tuple[list[Mapping[str, Any]], list[dict[str, Any]]]:
    """Load receipt rows as detached JSON values from the session store."""
    loaded: list[Mapping[str, Any]] = []
    findings: list[dict[str, Any]] = []
    for index, row in enumerate(rows):
        if not isinstance(row, Mapping) or not isinstance(row.get("path"), str):
            continue
        try:
            receipt = (
                captured.json_row_copy(
                    row, field=f"artifacts.stage_receipts[{index}]",
                )
                if captured is not None
                else guard["blog_assembly_bom_snapshot"].json_artifact(
                    None,
                    row,
                    field=f"artifacts.stage_receipts[{index}]",
                    root=root,
                    legacy_loader=guard["load_json_object_snapshot"],
                    legacy_verify=guard["verify_artifact"],
                )
            )
        except ValueError:
            continue
        if not isinstance(receipt, Mapping):
            findings.append(guard["_finding"](
                "bom_stage_receipt_invalid",
                f"Stage receipt {index} must be an object.",
            ))
            continue
        loaded.append(receipt)
    return loaded, findings


def validate_prior_preflight(
    guard: Any,
    captured: Any,
    prior_row: Any,
    prior_receipt: Mapping[str, Any],
    bom: Mapping[str, Any],
) -> Mapping[str, Any]:
    """Validate optimized-workflow preflight evidence from captured payloads."""
    snapshot = captured.snapshot_row(
        prior_row, field="artifacts.prior_preflight_readiness",
    )
    readiness = captured.json_row_copy(
        prior_row, field="artifacts.prior_preflight_readiness",
    )
    inputs = readiness.get("input_hashes")
    prior_bom_row = (
        inputs.get("assembly_bom") if isinstance(inputs, Mapping) else None
    )
    prior_bom = captured.json_row_copy(
        prior_bom_row,
        field="prior_preflight_readiness.input_hashes.assembly_bom",
    )
    schema = bom.get("schema_policy")
    connector = bom.get("connector_binding")
    return guard["_validate_prior_preflight_payloads"](
        readiness,
        prior_bom,
        readiness_sha256=snapshot.sha256,
        receipt=prior_receipt,
        visible_faq=(
            isinstance(schema, Mapping) and schema.get("visible_faq") is True
        ),
        connector_required=(
            isinstance(connector, Mapping) and connector.get("status") == "required"
        ),
    )


def load_preflight(
    captured: Any,
    row: Any,
) -> tuple[Any, dict[str, Any], str]:
    """Return the captured preflight path, payload, and digest."""
    snapshot = captured.snapshot_row(row, field="artifacts.preflight_readiness")
    return (
        snapshot.path,
        captured.json_row_copy(row, field="artifacts.preflight_readiness"),
        snapshot.sha256,
    )


def load_preflight_dispatch(
    guard: Any,
    captured: Any,
    row: Any,
    root: Any,
) -> tuple[Any, Mapping[str, Any], str | None, Mapping[str, Any] | None]:
    """Load preflight through one store-aware compatibility dispatch."""
    if captured is not None:
        path, payload, digest = load_preflight(captured, row)
        return path, payload, digest, payload
    path, payload = guard["_load_bound_json_object"](
        row,
        workspace_root=root,
        field="artifacts.preflight_readiness",
    )
    return path, payload, None, None


def load_historical_bom(captured: Any, row: Any) -> dict[str, Any]:
    """Return the provisional BOM captured through preflight input hashes."""
    return captured.json_row_copy(
        row, field="preflight.input_hashes.assembly_bom",
    )


def load_historical_bom_dispatch(
    guard: Any,
    captured: Any,
    row: Any,
    root: Any,
) -> Mapping[str, Any]:
    """Load the historical BOM from captured or compatibility storage."""
    if captured is not None:
        return load_historical_bom(captured, row)
    _, payload = guard["_load_bound_json_object"](
        row,
        workspace_root=root,
        field="preflight.input_hashes.assembly_bom",
    )
    return payload


__all__ = [
    "load_historical_bom",
    "load_historical_bom_dispatch",
    "load_preflight",
    "load_preflight_dispatch",
    "load_receipts",
    "validate_prior_preflight",
]
