"""Stable terminal facade for publish-readiness APIs and CLI."""
# ruff: noqa: F401

from __future__ import annotations

import sys
from pathlib import Path

if not __package__:  # pragma: no cover - direct script bootstrap.
    repository_root = str(Path(__file__).resolve().parents[2])
    if repository_root not in sys.path:
        sys.path.insert(0, repository_root)
    __package__ = "data_sources.modules"

from . import blog_assembly_bom_guard, context_binding_guard
from .readiness.adapters import _score_content, _scorecard_from_scorer_result
from .readiness.api import (
    _run_publish_readiness_session as _run_publish_readiness,
    build_final_readiness_attestation,
    run_publish_readiness,
)
from .readiness.common import (
    ContentScorer,
    LandingPageScorer,
    ReadinessTelemetry,
    SimproVaultClient,
    _ExecutedReadinessResult,
    load_validated_claim_set,
    read_publishable_markdown,
    validate_file_urls,
)
from .readiness.dependencies import ReadinessDependencies
from .readiness.persistence_api import (
    readiness_stage_receipt_path,
    write_readiness_result,
)
from .readiness.reporting import format_text_report, main
from .readiness.result_validation import (
    _validate_actual_readiness_execution,
    validate_passed_readiness_result,
)
from .readiness.runtime_policy import (
    _bom_runtime_policy,
    _no_fit_customer_proof_findings,
)
from .blog_assembly_stage_receipt import build_stage_receipt, write_stage_receipt

__all__ = [
    "ContentScorer",
    "LandingPageScorer",
    "ReadinessDependencies",
    "ReadinessTelemetry",
    "SimproVaultClient",
    "_ExecutedReadinessResult",
    "_bom_runtime_policy",
    "_no_fit_customer_proof_findings",
    "_run_publish_readiness",
    "_score_content",
    "_scorecard_from_scorer_result",
    "_validate_actual_readiness_execution",
    "blog_assembly_bom_guard",
    "build_final_readiness_attestation",
    "build_stage_receipt",
    "context_binding_guard",
    "format_text_report",
    "load_validated_claim_set",
    "main",
    "read_publishable_markdown",
    "readiness_stage_receipt_path",
    "run_publish_readiness",
    "validate_file_urls",
    "validate_passed_readiness_result",
    "write_readiness_result",
    "write_stage_receipt",
]


if __name__ == "__main__":
    raise SystemExit(main())
