"""Compatibility API and CLI for deterministic blog assembly BOMs."""
# ruff: noqa: F403, F405

try:
    from .blog_assembly.common import *  # noqa: F403
    from .blog_assembly.construction import *  # noqa: F403
    from .blog_assembly.finalization import *  # noqa: F403
    from .blog_assembly.cli import *  # noqa: F403
    from .blog_assembly.policy import *  # noqa: F403
    from .blog_assembly.stage_receipts import *  # noqa: F403
    from .blog_assembly.preflight import *  # noqa: F403
    from .blog_assembly.derivation import *  # noqa: F403
    from .blog_assembly.contracts import *  # noqa: F403
except ImportError:  # pragma: no cover - direct script compatibility.
    from blog_assembly.common import *  # noqa: F403
    from blog_assembly.construction import *  # noqa: F403
    from blog_assembly.finalization import *  # noqa: F403
    from blog_assembly.cli import *  # noqa: F403
    from blog_assembly.policy import *  # noqa: F403
    from blog_assembly.stage_receipts import *  # noqa: F403
    from blog_assembly.preflight import *  # noqa: F403
    from blog_assembly.derivation import *  # noqa: F403
    from blog_assembly.contracts import *  # noqa: F403


load_json_object_snapshot = _DEFAULT_LOAD_JSON_OBJECT_SNAPSHOT


if __name__ == "__main__":
    raise SystemExit(main())
