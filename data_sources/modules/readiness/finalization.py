"""Trusted delta that binds one authenticated preflight to a final BOM."""

from __future__ import annotations

import copy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Mapping

from ..blog_assembly_contract import load_json_object_snapshot
from .inputs import ReadinessInputs
from .telemetry import ReadinessTelemetry


def build_final_attestation(
    preflight_result: Mapping[str, Any],
    *,
    final_bom_path: Path,
    workspace_root: Path,
    validate_execution: Callable[..., None],
    validate_result: Callable[..., None],
    executed_result_factory: Callable[..., Mapping[str, Any]],
    readiness_run_id: Callable[[str | None, str], str],
    telemetry: ReadinessTelemetry | None = None,
) -> Mapping[str, Any]:
    """Reuse authenticated gates, then perform one complete final input reseal."""
    validate_execution(preflight_result, workspace_root=workspace_root)
    validate_result(preflight_result, workspace_root=workspace_root)
    if preflight_result.get("phase") != "preflight":
        raise ValueError("final readiness attestation requires a passed preflight result")

    final_bom = load_json_object_snapshot(final_bom_path, field="final BOM")
    if final_bom.payload.get("lifecycle_state") != "final":
        raise ValueError("final readiness attestation requires a final assembly BOM")

    started_at = _utc_now()
    inputs = _capture_final_inputs(
        preflight_result,
        final_bom_path=final_bom_path,
        workspace_root=workspace_root,
        telemetry=telemetry,
    )
    inputs.reseal()
    input_hashes = inputs.hash_inventory()
    final_result = copy.deepcopy(dict(preflight_result))
    final_result.update(
        {
            "phase": "final",
            "assembly_bom": str(final_bom_path),
            "input_hashes": input_hashes,
            "input_seal": {"status": "verified"},
            "final_bom_sha256": final_bom.sha256,
            "run_id": readiness_run_id(
                str(final_bom_path),
                input_hashes["article"]["sha256"],
            ),
            "started_at": started_at,
            "completed_at": _utc_now(),
        }
    )
    executed = executed_result_factory(final_result, workspace_root=workspace_root)
    validate_result(executed, workspace_root=workspace_root)
    return executed


def _capture_final_inputs(
    preflight_result: Mapping[str, Any],
    *,
    final_bom_path: Path,
    workspace_root: Path,
    telemetry: ReadinessTelemetry | None,
) -> ReadinessInputs:
    return ReadinessInputs.capture(
        {
            "article": preflight_result["file"],
            "validation_sidecar": _optional_path(preflight_result, "proof_sidecar"),
            "context_request": _optional_path(preflight_result, "context_request"),
            "context_pack": _optional_path(preflight_result, "context_pack"),
            "context_receipt": _optional_path(preflight_result, "context_receipt"),
            "assembly_bom": final_bom_path,
        },
        workspace_root=workspace_root,
        telemetry=telemetry,
    )


def _optional_path(result: Mapping[str, Any], key: str) -> str | None:
    value = result.get(key)
    return value if isinstance(value, str) else None


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
