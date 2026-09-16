"""Terminal compatibility entry point for governed blog releases."""

from __future__ import annotations

from pathlib import Path
from typing import Sequence

try:
    from .artifact_runtime.release_invocation import (
        ReleaseInvocationError,
        ReleaseResult,
    )
    from . import blog_release_impl
    from .release_workflow import error_reporting, precheck as release_precheck
except ImportError:  # pragma: no cover - supports direct script execution.
    from artifact_runtime.release_invocation import (
        ReleaseInvocationError,
        ReleaseResult,
    )
    import blog_release_impl
    from release_workflow import error_reporting
    import release_workflow.precheck as release_precheck

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
