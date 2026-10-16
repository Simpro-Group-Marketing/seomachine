"""Publish-readiness workspace bindings responsibilities."""
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Mapping

from .common import (
    ReadinessInputs,
    ReadinessTelemetry,
    canonical_artifact,
    load_json_object_snapshot,
)
from .artifact_views import thaw_value
from .input_spec import ReadinessInputSpec


def _same_path(left: str | Path, right: str | Path) -> bool:
    return os.path.normcase(str(Path(left).resolve())) == os.path.normcase(
        str(Path(right).resolve())
    )

def _readiness_run_id(assembly_bom: str | None, article_hash: str) -> str:
    if assembly_bom:
        try:
            bom = load_json_object_snapshot(
                assembly_bom, field="assembly BOM"
            ).payload
        except ValueError:
            bom = None
        workflow = bom.get("workflow") if isinstance(bom, Mapping) else None
        receipts = workflow.get("stage_receipts") if isinstance(workflow, Mapping) else None
        if isinstance(receipts, list) and receipts and isinstance(receipts[0], Mapping):
            run_id = receipts[0].get("run_id")
            if isinstance(run_id, str) and run_id.strip():
                return run_id.strip()
    return f"readiness-{article_hash[:16]}"

def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

def _resolve_workspace_input(
    value: str | Path,
    *,
    workspace_root: str | Path,
    field: str,
) -> Path:
    """Resolve one caller path without allowing a BOM to widen the trust root."""
    root = Path(workspace_root).resolve()
    raw = Path(value)
    candidate = raw.resolve() if raw.is_absolute() else (root / raw).resolve()
    try:
        common = Path(os.path.commonpath((str(root), str(candidate))))
    except ValueError as error:
        raise ValueError(f"{field} must remain inside workspace_root") from error
    if os.path.normcase(str(common)) != os.path.normcase(str(root)):
        raise ValueError(f"{field} must remain inside workspace_root")
    return candidate

def _resolve_optional_workspace_input(
    value: str | Path | None,
    *,
    workspace_root: str | Path,
    field: str,
) -> Path | None:
    if value is None:
        return None
    return _resolve_workspace_input(value, workspace_root=workspace_root, field=field)

def _readiness_input_hashes(
    inputs: Dict[str, str | Path | None],
    *,
    workspace_root: str | Path,
) -> Dict[str, Dict[str, str]]:
    snapshots: Dict[str, Dict[str, str]] = {}
    for label, value in inputs.items():
        if value is None:
            continue
        path = _resolve_workspace_input(
            value,
            workspace_root=workspace_root,
            field=f"readiness input {label}",
        )
        if path.is_file():
            snapshots[label] = canonical_artifact(
                path,
                workspace_root=workspace_root,
            )
    return snapshots

def _capture_readiness_inputs(
    *,
    article: str | Path,
    validation_sidecar: str | Path | None,
    context_request: str | Path | None,
    context_pack: str | Path | None,
    context_receipt: str | Path | None,
    assembly_bom: str | Path | None,
    workspace_root: str | Path,
    telemetry: ReadinessTelemetry | None = None,
) -> ReadinessInputs:
    spec = ReadinessInputSpec.for_readiness(
        {
            "article": article,
            "validation_sidecar": validation_sidecar,
            "context_request": context_request,
            "context_pack": context_pack,
            "context_receipt": context_receipt,
            "assembly_bom": assembly_bom,
        },
        workspace_root=workspace_root,
    )
    return ReadinessInputs.capture(spec, workspace_root=workspace_root, telemetry=telemetry)

def _captured_proof_content(
    inputs: ReadinessInputs | None,
    *,
    proof_sidecar_path: str | None,
) -> str | None:
    if proof_sidecar_path is None:
        return None
    if inputs is not None and inputs.optional_snapshot("validation_sidecar") is not None:
        return inputs.text("validation_sidecar")
    return Path(proof_sidecar_path).read_text(encoding="utf-8")


def _captured_json(
    inputs: ReadinessInputs,
    label: str,
) -> Mapping[str, Any] | None:
    if inputs.optional_snapshot(label) is None:
        return None
    value = thaw_value(inputs.json_object(label))
    return value if isinstance(value, Mapping) else None


def _captured_context_payloads(inputs: ReadinessInputs) -> dict[str, Any]:
    values: dict[str, Any] = {}
    for short_label, label in (
        ("request", "context_request"),
        ("pack", "context_pack"),
        ("receipt", "context_receipt"),
    ):
        snapshot = inputs.optional_snapshot(label)
        values[short_label] = _captured_json(inputs, label)
        values[f"{short_label}_path"] = snapshot.path if snapshot is not None else None
        values[f"{short_label}_sha256"] = snapshot.sha256 if snapshot is not None else None
    return values

__all__ = ['_capture_readiness_inputs', '_captured_context_payloads', '_captured_json', '_captured_proof_content', '_readiness_input_hashes', '_readiness_run_id', '_resolve_optional_workspace_input', '_resolve_workspace_input', '_same_path', '_utc_now']
