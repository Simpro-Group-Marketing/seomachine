"""Release error artifact writer for governed blog workflows."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

try:
    from ..artifact_runtime.release_invocation import ReleaseResult
    from ..blog_assembly_contract import atomic_write_json
    from .paths import workspace_path
except ImportError:  # pragma: no cover - supports direct script execution.
    from artifact_runtime.release_invocation import ReleaseResult
    from blog_assembly_contract import atomic_write_json
    from release_workflow.paths import workspace_path

ERROR_SCHEMA = "simpro-blog-release-error/v1"
ERROR_DIR = Path("research") / "release-errors"


def report_nonzero_result(
    result: ReleaseResult,
    *,
    run_id: object,
    workspace_root: str | Path,
    module: str,
    artifact: str = "blog",
) -> Path:
    return write_release_error(
        run_id=run_id,
        workspace_root=workspace_root,
        failure_kind="nonzero_result",
        exception_type=None,
        message=result.message,
        phase=result.phase,
        module=module,
        artifact=artifact,
        next_command=_next_command_for_result(result.phase),
        paths=_paths_for_result(result, workspace_root=_coerce_workspace_root(workspace_root)),
    )


def report_exception(
    error: BaseException,
    *,
    run_id: object,
    workspace_root: str | Path,
    phase: str,
    module: str,
    artifact: str = "blog",
    output_dir: str | Path | None = None,
) -> Path:
    root = _coerce_workspace_root(workspace_root)
    paths: dict[str, str | None] = {}
    if output_dir is not None:
        paths["output_dir"] = workspace_path(_resolve_under_root(output_dir, root), workspace_root=root)
    return write_release_error(
        run_id=run_id,
        workspace_root=root,
        failure_kind="exception",
        exception_type=type(error).__name__,
        message=str(error),
        phase=phase,
        module=module,
        artifact=artifact,
        next_command=_next_command_for_exception(phase),
        paths=paths,
    )


def write_release_error(
    *,
    run_id: object,
    workspace_root: str | Path,
    failure_kind: str,
    exception_type: str | None,
    message: str,
    phase: str,
    module: str,
    artifact: str,
    next_command: str,
    paths: Mapping[str, str | None] | None = None,
) -> Path:
    root = _coerce_workspace_root(workspace_root)
    target = error_report_path(run_id, workspace_root=root)
    reuse_status = "overwritten" if target.exists() else "new"
    payload: dict[str, Any] = {
        "schema": ERROR_SCHEMA,
        "run_id": _run_id_value(run_id),
        "failure_kind": failure_kind,
        "exception_type": exception_type,
        "message": message,
        "phase": phase,
        "module": module,
        "artifact": artifact,
        "next_command": next_command,
        "reuse_status": reuse_status,
        "paths": dict(paths or {}),
    }
    safe_stem = _safe_run_id_stem(run_id)
    if safe_stem != _run_id_value(run_id):
        payload["raw_run_id"] = _run_id_value(run_id)
    atomic_write_json(target, payload)
    return target


def error_report_path(run_id: object, *, workspace_root: str | Path) -> Path:
    root = _coerce_workspace_root(workspace_root)
    return root / ERROR_DIR / f"{_safe_run_id_stem(run_id)}.json"


def _paths_for_result(
    result: ReleaseResult,
    *,
    workspace_root: Path,
) -> dict[str, str | None]:
    paths: dict[str, str | None] = {
        "output_dir": workspace_path(result.output_dir, workspace_root=workspace_root),
    }
    if result.recovery_artifact is not None:
        paths["recovery_artifact"] = workspace_path(
            result.recovery_artifact,
            workspace_root=workspace_root,
        )
    return paths


def _next_command_for_result(phase: str) -> str:
    return (
        f"Inspect the {phase} blocker artifacts, repair the blocker, "
        "then rerun the blog release command."
    )


def _next_command_for_exception(phase: str) -> str:
    if phase == "invocation":
        return "Fix the release invocation inputs, then rerun the blog release command."
    if phase == "cli":
        return "Fix the CLI release error, then rerun the blog release command."
    return "Inspect the release artifacts and telemetry, repair the error, then rerun the blog release command."


def _resolve_under_root(path: str | Path, root: Path) -> Path:
    candidate = Path(path)
    if not candidate.is_absolute():
        candidate = root / candidate
    return candidate.resolve(strict=False)


def _coerce_workspace_root(value: str | Path) -> Path:
    return Path(value).resolve(strict=False)


def _run_id_value(value: object) -> str:
    if isinstance(value, str) and value.strip():
        return value.strip()
    return "missing-run-id"


def _safe_run_id_stem(value: object) -> str:
    raw = _run_id_value(value)
    safe = "".join(character if character.isalnum() or character in "._-" else "_" for character in raw)
    return safe or "missing-run-id"


__all__ = [
    "ERROR_SCHEMA",
    "error_report_path",
    "report_exception",
    "report_nonzero_result",
    "write_release_error",
]
