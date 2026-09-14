"""Compatibility API and CLI for source-support validation."""

try:
    from .source_support.classification import validate_source_classification_binding
    from .source_support.cli import _main
    from .source_support.common import (
        ClaimCandidate,
        ProofEntry,
        SourceSupportError,
        should_fail,
        summarize_findings,
    )
    from .source_support.orchestration import (
        check_content,
        check_file,
        format_findings,
        require_source_support,
    )
    from .source_support.retrieval import fetch_source_text, fetch_source_text_many
    from .source_support.persistence import (
        write_source_capture_receipt,
        write_source_classification_artifact,
    )
except ImportError:  # pragma: no cover - direct script compatibility.
    from source_support.classification import validate_source_classification_binding
    from source_support.cli import _main
    from source_support.common import (
        ClaimCandidate,
        ProofEntry,
        SourceSupportError,
        should_fail,
        summarize_findings,
    )
    from source_support.orchestration import (
        check_content,
        check_file,
        format_findings,
        require_source_support,
    )
    from source_support.retrieval import fetch_source_text, fetch_source_text_many
    from source_support.persistence import (
        write_source_capture_receipt,
        write_source_classification_artifact,
    )


__all__ = [
    "ClaimCandidate",
    "ProofEntry",
    "SourceSupportError",
    "check_content",
    "check_file",
    "fetch_source_text",
    "fetch_source_text_many",
    "format_findings",
    "require_source_support",
    "should_fail",
    "summarize_findings",
    "validate_source_classification_binding",
    "write_source_capture_receipt",
    "write_source_classification_artifact",
]


if __name__ == "__main__":
    raise SystemExit(_main())
