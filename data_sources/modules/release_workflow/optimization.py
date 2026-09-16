"""Optimization recovery artifact helpers for blog release."""

from __future__ import annotations

import json
from pathlib import Path

try:
    from .. import blog_assembly_stage_receipt
    from ..blog_assembly_contract import atomic_write_json, validate_sha256
    from .paths import workspace_path
except ImportError:  # pragma: no cover - supports direct script execution.
    import blog_assembly_stage_receipt
    from blog_assembly_contract import atomic_write_json, validate_sha256
    from release_workflow.paths import workspace_path


class ReleasePolicyError(RuntimeError):
    pass


def begin_optimization_run(
    *,
    article: str | Path,
    run_id: str,
    paths: dict[str, Path],
    preflight: dict[str, object],
    preflight_receipt_path: Path | None,
    workspace_root: Path,
) -> Path:
    optimization_state: str | None = None
    optimization_stage_receipt: str | None = None
    preflight_stage_receipt: str | None = None
    native_edit_status = "not_started"
    recovery_steps = [
        "Run /optimize against the article using the initial readiness output.",
        "Write a simpro-optimizer-output/v2 artifact binding the current article, editorial plan, proof sidecar, scorecard, and prior-preflight readiness.",
        "Rerun /scrub and Context Binding after article or sidecar changes.",
    ]
    if preflight_receipt_path is not None:
        preflight_receipt = read_json_object(
            preflight_receipt_path,
            "preflight_readiness_stage_receipt",
        )
        try:
            previous_receipt_hash = validate_sha256(
                preflight_receipt.get("receipt_hash"),
                field="preflight_readiness_stage_receipt.receipt_hash",
            )
        except ValueError as error:
            raise ReleasePolicyError(
                "preflight readiness receipt is missing a valid receipt_hash; "
                "cannot begin /optimize recovery"
            ) from error

        blog_assembly_stage_receipt.begin_native_edit(
            article_path=article,
            state_path=paths["optimization_state"],
            run_id=run_id,
            stage="optimization",
            tool_name="optimize-command",
            tool_version="1",
            input_artifacts={
                "preflight_readiness": paths["preflight_readiness"],
                "preflight_readiness_receipt": preflight_receipt_path,
            },
            previous_receipt_hash=previous_receipt_hash,
        )
        native_edit_status = "started"
        preflight_stage_receipt = workspace_path(
            preflight_receipt_path,
            workspace_root=workspace_root,
        )
        optimization_state = workspace_path(
            paths["optimization_state"],
            workspace_root=workspace_root,
        )
        optimization_stage_receipt = workspace_path(
            paths["optimization_stage_receipt"],
            workspace_root=workspace_root,
        )
        recovery_steps.extend(
            [
                "Finish the optimization stage receipt if article bytes changed.",
                "Rerun the release wrapper with --optimizer-output and --prior-preflight-readiness.",
            ]
        )
    else:
        recovery_steps.extend(
            [
                "Resolve the preflight blocker, then rerun /scrub and Context Binding when needed.",
                "Rerun the release wrapper to produce the required passed initial scorecard before final release.",
            ]
        )
    recovery = {
        "schema": "simpro-blog-optimization-recovery/v1",
        "status": "started",
        "reason": "Optimizer evidence was not supplied to the release wrapper.",
        "preflight_passed": preflight.get("passed") is True,
        "native_edit_status": native_edit_status,
        "preflight_readiness": workspace_path(
            paths["preflight_readiness"],
            workspace_root=workspace_root,
        ),
        "preflight_readiness_stage_receipt": preflight_stage_receipt,
        "optimization_state": optimization_state,
        "optimization_stage_receipt": optimization_stage_receipt,
        "required_next_steps": recovery_steps,
    }
    atomic_write_json(paths["optimization_recovery"], recovery)
    return paths["optimization_recovery"]


def read_json_object(path: str | Path, label: str) -> dict[str, object]:
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise ReleasePolicyError(f"{label} is unreadable: {error}") from error
    if not isinstance(value, dict):
        raise ReleasePolicyError(f"{label} must be a JSON object")
    return value


__all__ = ["ReleasePolicyError", "begin_optimization_run", "read_json_object"]
