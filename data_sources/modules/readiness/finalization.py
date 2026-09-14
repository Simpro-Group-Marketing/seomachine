"""Trusted delta that binds one authenticated preflight to final inputs."""

from __future__ import annotations

import copy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Mapping

from .inputs import ReadinessInputs
from .session import ValidationSession
from .telemetry import ReadinessTelemetry


def reseal_readiness_inputs(
    inputs: ReadinessInputs | None,
    *,
    capture_error: ValueError | None = None,
) -> tuple[dict[str, dict[str, str]], list[dict[str, Any]]]:
    """Reseal one captured inventory and return a gate-ready failure finding."""
    hashes = inputs.hash_inventory() if inputs is not None else {}
    try:
        if capture_error is not None:
            raise capture_error
        if inputs is None:
            raise ValueError("readiness input snapshot is unavailable")
        inputs.reseal()
        return inputs.hash_inventory(), []
    except ValueError as error:
        return hashes, [{
            "rule_id": "readiness_inputs_changed_during_run",
            "severity": "error",
            "line": 1,
            "column": 1,
            "message": str(error),
            "suggestion": (
                "Resume at the mutation receipt, then rerun scrub, Context Binding, "
                "BOM build, and readiness."
            ),
        }]


def finalize_blocked_result(
    result: Mapping[str, Any],
    *,
    inputs: ReadinessInputs | None,
    capture_error: ValueError | None = None,
) -> dict[str, Any]:
    """Attach the mandatory final input seal to any post-capture blocked exit."""
    hashes, findings = reseal_readiness_inputs(inputs, capture_error=capture_error)
    seal_gate = _input_seal_gate(findings)
    finalized = copy.deepcopy(dict(result))
    gates = list(finalized.get("gates") or [])
    if not any(
        isinstance(gate, Mapping) and gate.get("name") == "input_seal"
        for gate in gates
    ):
        gates.append(seal_gate)
    finalized["gates"] = gates
    finalized["gate_inventory"] = [
        str(gate.get("name") or "")
        for gate in gates
        if isinstance(gate, Mapping)
    ]
    finalized["input_hashes"] = hashes
    finalized["input_seal"] = {"status": "failed" if findings else "verified"}
    if findings:
        finalized["passed"] = False
        fixes = list(finalized.get("priority_fixes") or [])
        fixes.append({"dimension": "input_seal", "issue": findings[0]["message"]})
        finalized["priority_fixes"] = fixes
    return finalized


def _input_seal_gate(findings: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "name": "input_seal",
        "label": "Input Seal",
        "passed": not findings,
        "errors": len(findings),
        "warnings": 0,
        "findings": findings,
        "blockers": [
            f"line 1: {finding['rule_id']} - {finding['message']}"
            for finding in findings[:3]
        ],
    }


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
    started_at = _utc_now()
    session = _capture_final_session(
        preflight_result,
        final_bom_path=final_bom_path,
        workspace_root=workspace_root,
        telemetry=telemetry,
    )
    with session:
        inputs = session.inputs
        _validate_preflight_input_hashes(inputs, preflight_result)
        final_bom = (
            inputs.json_object("assembly_bom")
            if final_bom_path is not None
            else None
        )
        if final_bom is not None and final_bom.get("lifecycle_state") != "final":
            raise ValueError("final readiness attestation requires a final assembly BOM")
        if artifact_kind == "landing_page" and final_bom is not None:
            raise ValueError("landing-page final readiness does not use a blog assembly BOM")

        inputs.reseal()
        input_hashes = inputs.hash_inventory()
        final_result = copy.deepcopy(dict(preflight_result))
        final_result.update({
            "phase": "final",
            "assembly_bom": str(final_bom_path) if final_bom_path is not None else None,
            "input_hashes": input_hashes,
            "input_seal": {"status": "verified"},
            "run_id": run_id or _bom_run_id(final_bom) or readiness_run_id(
                None, input_hashes["article"]["sha256"]
            ),
            "started_at": started_at,
            "completed_at": _utc_now(),
        })
        if final_bom is not None:
            final_result["final_bom_sha256"] = inputs.snapshot(
                "assembly_bom"
            ).sha256
        else:
            final_result.pop("final_bom_sha256", None)
        executed = executed_result_factory(final_result, workspace_root=workspace_root)
        validate_result(executed, workspace_root=workspace_root)
        return executed


def _capture_final_session(
    preflight_result: Mapping[str, Any],
    *,
    final_bom_path: Path | None,
    workspace_root: Path,
    telemetry: ReadinessTelemetry | None,
) -> ValidationSession:
    paths = _preflight_input_paths(preflight_result)
    paths.update({
        "article": preflight_result["file"],
        "validation_sidecar": _optional_path(preflight_result, "proof_sidecar"),
        "context_request": _optional_path(preflight_result, "context_request"),
        "context_pack": _optional_path(preflight_result, "context_pack"),
        "context_receipt": _optional_path(preflight_result, "context_receipt"),
        "assembly_bom": final_bom_path,
    })
    return ValidationSession.capture(
        paths,
        workspace_root=workspace_root,
        telemetry=telemetry,
    )


def _preflight_input_paths(
    preflight_result: Mapping[str, Any],
) -> dict[str, str]:
    inventory = preflight_result.get("input_hashes")
    if not isinstance(inventory, Mapping):
        return {}
    return {
        label: str(row["path"])
        for label, row in inventory.items()
        if isinstance(label, str)
        and isinstance(row, Mapping)
        and isinstance(row.get("path"), str)
    }


def _validate_preflight_input_hashes(
    inputs: ReadinessInputs,
    preflight_result: Mapping[str, Any],
) -> None:
    expected = preflight_result.get("input_hashes")
    if not isinstance(expected, Mapping):
        return
    current = inputs.hash_inventory()
    for label, row in expected.items():
        if label == "assembly_bom" or not isinstance(row, Mapping):
            continue
        captured = current.get(str(label))
        if captured != {"path": row.get("path"), "sha256": row.get("sha256")}:
            raise ValueError(
                f"final readiness input differs from authenticated preflight: {label}"
            )


def _bom_run_id(bom: Mapping[str, Any] | None) -> str | None:
    workflow = bom.get("workflow") if isinstance(bom, Mapping) else None
    receipts = workflow.get("stage_receipts") if isinstance(workflow, Mapping) else None
    first = receipts[0] if isinstance(receipts, (list, tuple)) and receipts else None
    value = first.get("run_id") if isinstance(first, Mapping) else None
    return value.strip() if isinstance(value, str) and value.strip() else None


def _optional_path(result: Mapping[str, Any], key: str) -> str | None:
    value = result.get(key)
    return value if isinstance(value, str) else None


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


__all__ = [
    "build_final_attestation",
    "finalize_blocked_result",
    "reseal_readiness_inputs",
]
