"""Path helpers for governed release workflows."""

from __future__ import annotations

from pathlib import Path

try:
    from ..artifact_runtime.release_invocation import ReleaseInvocationError
except ImportError:  # pragma: no cover - supports direct script execution.
    from artifact_runtime.release_invocation import ReleaseInvocationError


def planned_output_dir(path: str | Path, *, workspace_root: Path) -> Path:
    if not isinstance(path, (str, Path)) or not str(path).strip():
        raise ReleaseInvocationError("output_dir is required")
    candidate = Path(path)
    if not candidate.is_absolute():
        candidate = workspace_root / candidate
    resolved = candidate.resolve(strict=False)
    try:
        resolved.relative_to(workspace_root)
    except ValueError as error:
        raise ReleaseInvocationError("output_dir must stay inside the workspace") from error
    if resolved.exists():
        raise ReleaseInvocationError("output_dir must not already exist")
    return resolved


def new_output_dir(path: str | Path, *, workspace_root: Path) -> Path:
    resolved = planned_output_dir(path, workspace_root=workspace_root)
    resolved.mkdir(parents=True)
    return resolved


def blog_release_paths(output_dir: Path) -> dict[str, Path]:
    return {
        "pre_bom_report": output_dir / "pre-bom-report.json",
        "provisional_bom": output_dir / "provisional-bom.json",
        "preflight_readiness": output_dir / "preflight-readiness.json",
        "preflight_readiness_stage_receipt": output_dir
        / "preflight-readiness-stage-receipt.json",
        "optimization_state": output_dir / "optimization-state.json",
        "optimization_recovery": output_dir / "optimization-recovery.json",
        "optimization_stage_receipt": output_dir / "optimization-stage-receipt.json",
        "final_bom": output_dir / "final-bom.json",
        "release_manifest": output_dir / "release-manifest.json",
        "final_readiness": output_dir / "final-readiness.json",
        "final_readiness_stage_receipt": output_dir / "final-readiness-stage-receipt.json",
        "release_telemetry": output_dir / "release-telemetry.json",
    }


def workspace_path(path: str | Path, *, workspace_root: Path) -> str:
    resolved = Path(path).resolve(strict=False)
    try:
        return resolved.relative_to(workspace_root).as_posix()
    except ValueError:
        return resolved.as_posix()


__all__ = ["blog_release_paths", "new_output_dir", "planned_output_dir", "workspace_path"]
