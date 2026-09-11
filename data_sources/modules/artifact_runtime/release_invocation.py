"""Validation contract for an atomic blog-release invocation."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path

from .release_inputs import validate_release_text_inputs


class ReleaseInvocationError(ValueError):
    """Raised when release arguments are incomplete, unsafe, or unreadable."""


def validate_release_invocation(
    *,
    required_files: Mapping[str, str | Path],
    optional_files: Mapping[str, str | Path | None],
    stage_receipts: Sequence[str | Path],
    optimizer_outputs: Sequence[str | Path],
    prior_preflight_readiness: str | Path | None,
    agent_output_paths: Mapping[str, str | Path],
    run_id: str,
    workflow_mode: str,
    workspace_root: Path,
) -> bool:
    """Validate every release argument before any output directory is created."""
    _validate_required_files(required_files, stage_receipts)
    _validate_optional_files(optional_files)
    _validate_optimization_files(
        optimizer_outputs,
        prior_preflight_readiness=prior_preflight_readiness,
    )
    _validate_agent_outputs(agent_output_paths)
    try:
        validate_release_text_inputs(required_files, workspace_root=workspace_root)
    except ValueError as error:
        raise ReleaseInvocationError(str(error)) from error
    if not isinstance(run_id, str) or not run_id.strip():
        raise ReleaseInvocationError("run_id is required")
    if workflow_mode not in {"new", "rewrite"}:
        raise ReleaseInvocationError("workflow_mode must be new or rewrite")
    return bool(optimizer_outputs)


def _require_file(path: str | Path, label: str) -> None:
    if not isinstance(path, (str, Path)) or not str(path).strip():
        raise ReleaseInvocationError(f"{label} path is required")
    if not Path(path).is_file():
        raise ReleaseInvocationError(f"{label} is unreadable: {path}")


def _validate_required_files(
    required_files: Mapping[str, str | Path],
    stage_receipts: Sequence[str | Path],
) -> None:
    for label, value in required_files.items():
        _require_file(value, label)
    if not stage_receipts:
        raise ReleaseInvocationError("at least one stage receipt is required")
    for index, receipt in enumerate(stage_receipts):
        _require_file(receipt, f"stage_receipts[{index}]")


def _validate_optional_files(
    optional_files: Mapping[str, str | Path | None],
) -> None:
    for label, value in optional_files.items():
        if value is not None:
            _require_file(value, label)


def _validate_optimization_files(
    optimizer_outputs: Sequence[str | Path],
    *,
    prior_preflight_readiness: str | Path | None,
) -> None:
    if bool(optimizer_outputs) != (prior_preflight_readiness is not None):
        raise ReleaseInvocationError(
            "optimized release requires both --optimizer-output and "
            "--prior-preflight-readiness"
        )
    for index, optimizer_output in enumerate(optimizer_outputs):
        _require_file(optimizer_output, f"optimizer_outputs[{index}]")
    if prior_preflight_readiness is not None:
        _require_file(prior_preflight_readiness, "prior_preflight_readiness")


def _validate_agent_outputs(agent_output_paths: Mapping[str, str | Path]) -> None:
    for agent_id, agent_output in agent_output_paths.items():
        if not isinstance(agent_id, str) or not agent_id.strip():
            raise ReleaseInvocationError("agent_output IDs must be non-empty strings")
        _require_file(agent_output, f"agent_output[{agent_id}]")
