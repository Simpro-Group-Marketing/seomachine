"""Trusted delta that binds one authenticated preflight to final inputs."""

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
    final_bom_path: Path | None,
    workspace_root: Path,
    validate_execution: Callable[..., None],
    validate_result: Callable[..., None],
    executed_result_factory: Callable[..., Mapping[str, Any]],
    readiness_run_id: Callable[[str | None, str], str],
    run_id: str | None = None,
    telemetry: ReadinessTelemetry | None = None,
) -> Mapping[str, Any]:
    """Reuse authenticated gates, then perform one complete final input reseal."""
    validate_execution(preflight_result, workspace_root=workspace_root)
    validate_result(preflight_result, workspace_root=workspace_root)
    if preflight_result.get("phase") != "preflight":
        raise ValueError("final readiness attestation requires a passed preflight result")

    artifact_kind = preflight_result.get("artifact_kind")
    if artifact_kind == "blog" and final_bom_path is None:
        raise ValueError("final blog readiness attestation requires a final assembly BOM")
    final_bom = (
        load_json_object_snapshot(final_bom_path, field="final BOM")
        if final_bom_path is not None
        else None
    )
    if final_bom is not None and final_bom.payload.get("lifecycle_state") != "final":
        raise ValueError("final readiness attestation requires a final assembly BOM")
    if artifact_kind == "landing_page" and final_bom is not None:
        raise ValueError("landing-page final readiness does not use a blog assembly BOM")

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
    final_result.update({
        "phase": "final",
        "assembly_bom": str(final_bom_path) if final_bom_path is not None else None,
        "input_hashes": input_hashes,
        "input_seal": {"status": "verified"},
        "run_id": run_id or readiness_run_id(
            str(final_bom_path) if final_bom_path is not None else None,
            input_hashes["article"]["sha256"],
        ),
        "started_at": started_at,
        "completed_at": _utc_now(),
    })
    if final_bom is not None:
        final_result["final_bom_sha256"] = final_bom.sha256
    else:
        final_result.pop("final_bom_sha256", None)
    executed = executed_result_factory(final_result, workspace_root=workspace_root)
    validate_result(executed, workspace_root=workspace_root)
    return executed


def _capture_final_inputs(
    preflight_result: Mapping[str, Any],
    *,
    final_bom_path: Path | None,
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
