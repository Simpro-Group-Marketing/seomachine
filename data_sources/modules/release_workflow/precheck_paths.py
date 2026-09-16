"""Path safety checks for blog release precheck reports."""

from __future__ import annotations

from pathlib import Path
from typing import Mapping, Sequence

try:
    from ..artifact_runtime.release_invocation import ReleaseInvocationError
    from .paths import planned_output_dir
except ImportError:  # pragma: no cover - supports direct script execution.
    from artifact_runtime.release_invocation import ReleaseInvocationError
    from release_workflow.paths import planned_output_dir


def resolve_precheck_output(value: str | Path | None, *, workspace_root: Path) -> Path | None:
    if value is None:
        return None
    if not isinstance(value, (str, Path)) or not str(value).strip():
        raise ReleaseInvocationError("precheck_output path is required")
    resolved = _resolve_workspace_path(value, workspace_root=workspace_root)
    if resolved.exists() and resolved.is_dir():
        raise ReleaseInvocationError("precheck_output must be a file path")
    return resolved


def validate_precheck_output_target(
    report_path: Path | None,
    *,
    output_dir: str | Path,
    workspace_root: Path,
    required_files: Mapping[str, str | Path],
    optional_files: Mapping[str, str | Path | None],
    stage_receipts: Sequence[str | Path],
    optimizer_outputs: Sequence[str | Path],
    prior_preflight_readiness: str | Path | None,
    agent_output_paths: Mapping[str, str | Path],
) -> Path:
    planned_dir = planned_output_dir(output_dir, workspace_root=workspace_root)
    if report_path is None:
        return planned_dir
    if _is_within(report_path, planned_dir):
        raise ReleaseInvocationError("precheck_output must not be inside output_dir")
    collisions = _input_collisions(
        report_path,
        output_dir=planned_dir,
        workspace_root=workspace_root,
        required_files=required_files,
        optional_files=optional_files,
        stage_receipts=stage_receipts,
        optimizer_outputs=optimizer_outputs,
        prior_preflight_readiness=prior_preflight_readiness,
        agent_output_paths=agent_output_paths,
    )
    if collisions:
        names = ", ".join(collisions)
        raise ReleaseInvocationError(
            f"precheck_output must not overwrite release input or output paths: {names}"
        )
    return planned_dir


def safe_output_dir(value: str | Path | None, *, workspace_root: Path) -> Path:
    if value is None:
        return workspace_root
    try:
        return planned_output_dir(value, workspace_root=workspace_root)
    except ReleaseInvocationError:
        return _resolve_workspace_path(value, workspace_root=workspace_root)


def _input_collisions(
    report_path: Path,
    *,
    output_dir: Path,
    workspace_root: Path,
    required_files: Mapping[str, str | Path],
    optional_files: Mapping[str, str | Path | None],
    stage_receipts: Sequence[str | Path],
    optimizer_outputs: Sequence[str | Path],
    prior_preflight_readiness: str | Path | None,
    agent_output_paths: Mapping[str, str | Path],
) -> list[str]:
    candidates: list[tuple[str, str | Path | None]] = [("output_dir", output_dir)]
    candidates.extend(required_files.items())
    candidates.extend(optional_files.items())
    candidates.extend(
        (f"stage_receipts[{index}]", path)
        for index, path in enumerate(stage_receipts)
    )
    candidates.extend(
        (f"optimizer_outputs[{index}]", path)
        for index, path in enumerate(optimizer_outputs)
    )
    candidates.append(("prior_preflight_readiness", prior_preflight_readiness))
    candidates.extend(
        (f"agent_output[{agent_id}]", path)
        for agent_id, path in agent_output_paths.items()
    )
    collisions: list[str] = []
    for label, value in candidates:
        if value is not None and report_path == _resolve_workspace_path(
            value,
            workspace_root=workspace_root,
        ):
            collisions.append(label)
    return collisions


def _resolve_workspace_path(value: str | Path, *, workspace_root: Path) -> Path:
    candidate = Path(value)
    if not candidate.is_absolute():
        candidate = workspace_root / candidate
    resolved = candidate.resolve(strict=False)
    try:
        resolved.relative_to(workspace_root)
    except ValueError as error:
        raise ReleaseInvocationError("precheck_output must stay inside the workspace") from error
    return resolved


def _is_within(candidate: Path, parent: Path) -> bool:
    try:
        candidate.relative_to(parent)
    except ValueError:
        return False
    return True


__all__ = [
    "resolve_precheck_output",
    "safe_output_dir",
    "validate_precheck_output_target",
]
