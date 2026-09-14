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
except ImportError:  # pragma: no cover - supports direct script execution.
    from artifact_runtime.release_invocation import (
        ReleaseInvocationError,
        ReleaseResult,
    )
    import blog_release_impl

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
    return run_artifact_release(artifact_kind="blog", **kwargs)


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
