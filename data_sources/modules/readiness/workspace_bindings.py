"""Publish-readiness workspace bindings responsibilities."""
import os
from pathlib import Path
from typing import Any, Mapping

from .common import (
    ReadinessInputs,
)
from .artifact_views import thaw_value


def _readiness_run_id(article_hash: str) -> str:
    return f"readiness-{article_hash[:16]}"

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

__all__ = ['_captured_context_payloads', '_captured_json', '_captured_proof_content', '_readiness_run_id', '_resolve_optional_workspace_input', '_resolve_workspace_input']
