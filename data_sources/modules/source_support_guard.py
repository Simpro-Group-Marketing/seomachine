"""Compatibility API and CLI for source-support validation."""
# ruff: noqa: F403, F405

try:
    from .source_support.common import *  # noqa: F403
    from .source_support.persistence import *  # noqa: F403
    from .source_support.orchestration import *  # noqa: F403
    from .source_support.proof_parsing import *  # noqa: F403
    from .source_support.evidence_validation import *  # noqa: F403
    from .source_support.classification import *  # noqa: F403
    from .source_support.capture_receipts import *  # noqa: F403
    from .source_support.claim_matching import *  # noqa: F403
    from .source_support.artifacts import *  # noqa: F403
    from .source_support.findings import *  # noqa: F403
    from .source_support.text_matching import *  # noqa: F403
    from .source_support.cli import *  # noqa: F403
except ImportError:  # pragma: no cover - direct script compatibility.
    from source_support.common import *  # noqa: F403
    from source_support.persistence import *  # noqa: F403
    from source_support.orchestration import *  # noqa: F403
    from source_support.proof_parsing import *  # noqa: F403
    from source_support.evidence_validation import *  # noqa: F403
    from source_support.classification import *  # noqa: F403
    from source_support.capture_receipts import *  # noqa: F403
    from source_support.claim_matching import *  # noqa: F403
    from source_support.artifacts import *  # noqa: F403
    from source_support.findings import *  # noqa: F403
    from source_support.text_matching import *  # noqa: F403
    from source_support.cli import *  # noqa: F403


if __name__ == "__main__":
    raise SystemExit(_main())
