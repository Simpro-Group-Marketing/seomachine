"""Terminal compatibility entry point for governed blog releases."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Sequence

try:
    from .artifact_runtime.release_invocation import (
        ReleaseInvocationError,
        ReleaseResult,
    )
    from . import blog_release_impl
    from .release_workflow import (
        error_reporting,
        precheck as release_precheck,
        precheck_paths,
    )
except ImportError:  # pragma: no cover - supports direct script execution.
    from artifact_runtime.release_invocation import (
        ReleaseInvocationError,
        ReleaseResult,
    )
    import blog_release_impl
    from release_workflow import error_reporting
    import release_workflow.precheck as release_precheck
    import release_workflow.precheck_paths as precheck_paths

ReleasePolicyError = blog_release_impl.ReleasePolicyError
_run_blog_release = blog_release_impl._run_blog_release
blog_assembly_bom = blog_release_impl.blog_assembly_bom
blog_creation_preflight = blog_release_impl.blog_creation_preflight
publish_readiness = blog_release_impl.publish_readiness
release_authorization = blog_release_impl.release_authorization


def run_blog_release(**kwargs: object) -> ReleaseResult:
    """Compatibility facade over the unified artifact release workflow."""
    try:
        from .artifact_release import run_artifact_release
    except ImportError:  # pragma: no cover - supports direct script execution.
        from artifact_release import run_artifact_release
    try:
        result = run_artifact_release(artifact_kind="blog", **kwargs)
    except Exception as error:
        _report_requested_precheck_exception(error, kwargs)
        error_reporting.report_exception(
            error,
            run_id=kwargs.get("run_id"),
            workspace_root=kwargs.get("workspace_root") or Path.cwd(),
            phase="invocation" if isinstance(error, ReleaseInvocationError) else "exception",
            module="blog_release",
            artifact="blog",
            output_dir=kwargs.get("output_dir"),
        )
        raise
    if result.exit_code != 0:
        error_reporting.report_nonzero_result(
            result,
            run_id=kwargs.get("run_id"),
            workspace_root=kwargs.get("workspace_root") or Path.cwd(),
            module="blog_release",
            artifact="blog",
        )
    return result


def _report_requested_precheck_exception(
    error: BaseException,
    kwargs: dict[str, object],
) -> None:
    if not (kwargs.get("precheck_output") or kwargs.get("precheck_only")):
        return
    if isinstance(error, ReleaseInvocationError) and str(error).startswith("precheck_output"):
        return
    if _requested_precheck_path_is_unsafe(kwargs):
        return
    if _requested_precheck_is_current_failure(
        kwargs.get("precheck_output"),
        workspace_root=kwargs.get("workspace_root") or Path.cwd(),
    ):
        return
    try:
        release_precheck.write_exception_report(
            error,
            run_id=kwargs.get("run_id"),
            workspace_root=kwargs.get("workspace_root") or Path.cwd(),
            output_dir=kwargs.get("output_dir"),
            precheck_output=kwargs.get("precheck_output"),
            phase="invocation" if isinstance(error, ReleaseInvocationError) else "exception",
        )
    except Exception:
        return


def _requested_precheck_path_is_unsafe(kwargs: dict[str, object]) -> bool:
    root = Path(kwargs.get("workspace_root") or Path.cwd()).resolve(strict=False)
    output_dir = kwargs.get("output_dir")
    if output_dir is None:
        return False
    try:
        report_path = precheck_paths.resolve_precheck_output(
            kwargs.get("precheck_output"),
            workspace_root=root,
        )
        precheck_paths.validate_precheck_output_target(
            report_path,
            output_dir=output_dir,
            workspace_root=root,
            required_files=_required_collision_paths(kwargs),
            optional_files=_optional_collision_paths(kwargs),
            stage_receipts=tuple(kwargs.get("stage_receipts") or ()),
            optimizer_outputs=tuple(kwargs.get("optimizer_outputs") or ()),
            prior_preflight_readiness=kwargs.get("prior_preflight_readiness"),
            agent_output_paths=dict(kwargs.get("agent_output_paths") or {}),
        )
    except ReleaseInvocationError as error:
        return str(error).startswith("precheck_output")
    return False


def _required_collision_paths(kwargs: dict[str, object]) -> dict[str, str | Path]:
    names = (
        "article",
        "proof_sidecar",
        "editorial_plan",
        "plan_review",
        "article_review",
        "keyword_decision",
        "scrub_receipt",
        "serp_evidence",
        "plan_fulfillment",
        "commercial_pillar_index",
    )
    return {
        name: value
        for name in names
        if isinstance((value := kwargs.get(name)), (str, Path))
    }


def _optional_collision_paths(kwargs: dict[str, object]) -> dict[str, str | Path | None]:
    names = (
        "context_request",
        "context_pack",
        "context_receipt",
        "customer_proof_evidence",
        "fred_authority_evidence",
        "paa_artifact",
        "content_brief",
        "user_paa_csv",
        "answersocrates_blocker",
    )
    return {
        name: value if isinstance(value, (str, Path)) else None
        for name in names
        for value in (kwargs.get(name),)
    }


def _requested_precheck_is_current_failure(
    value: object,
    *,
    workspace_root: object,
) -> bool:
    if not isinstance(value, (str, Path)) or not str(value).strip():
        return False
    path = Path(value)
    if not path.is_absolute():
        path = Path(workspace_root) / path
    if not path.is_file():
        return False
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return False
    return isinstance(payload, dict) and payload.get("passed") is False


def main(argv: Sequence[str] | None = None) -> int:
    try:
        from .readiness.release_cli import run_release_cli
    except ImportError:  # pragma: no cover - supports direct script execution.
        from readiness.release_cli import run_release_cli
    return run_release_cli(
        argv,
        runner=run_blog_release,
        invocation_error=ReleaseInvocationError,
    )


__all__ = [
    "ReleaseInvocationError",
    "ReleasePolicyError",
    "ReleaseResult",
    "_run_blog_release",
    "blog_assembly_bom",
    "blog_creation_preflight",
    "run_blog_release",
    "main",
    "publish_readiness",
    "release_authorization",
]


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
