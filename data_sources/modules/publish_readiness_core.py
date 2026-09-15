"""Historical compatibility facade for publish readiness internals.

Implementation code lives under :mod:`data_sources.modules.readiness`. This
module remains a terminal compatibility leaf for older tests and callers that
patched the former monolithic module.
"""
# ruff: noqa: F401

from __future__ import annotations

from .blog_bom_validation import api as blog_assembly_bom_guard
from .publishable_markdown import read_publishable_markdown
from .readiness.adapters import (
    _blocked_readiness_result,
    _content_score,
    _gate_from_findings,
    _gate_from_score,
    _gate_from_url_summary,
    _score_content,
    _scorecard_from_scorer_result,
    _timed_call,
)
from .readiness.api import build_final_readiness_attestation, run_publish_readiness
from .readiness.common import (
    ContentScorer,
    FrontmatterError,
    GateResult,
    LandingPageScorer,
    ReadinessResult,
    ReadinessTelemetry,
    SimproVaultClient,
    ValidationSession,
    blog_identity_guard,
    build_stage_receipt,
    context_binding_guard,
    load_validated_claim_set,
    parse_publishable_markdown,
    validate_file_urls,
    write_stage_receipt,
)
from .readiness.finalization import _utc_now, finalize_blocked_result
from .readiness.gate_policy import artifact_kind_rule_id as _artifact_kind_rule_id
from .readiness.persistence_api import (
    readiness_stage_receipt_path,
    write_readiness_result,
)
from .readiness.reporting import format_text_report, main
from .readiness.result_validation import (
    _validate_actual_readiness_execution,
    validate_passed_readiness_result,
)
from .readiness.runner import (
    _blocked_for_gate,
    _failure_gate,
    _read_article_snapshot,
    _resolve_artifact_kind_value,
    _run_context_gate,
    _run_publish_readiness,
    _sealed_blocked_result,
    _validate_bom_and_capture_hashes,
)
from .readiness.runtime_policy import (
    _bom_runtime_policy,
    _no_fit_customer_proof_findings,
)
from .readiness.workspace_bindings import (
    _captured_context_payloads,
    _captured_json,
    _captured_proof_content,
)

__all__ = [
    "ContentScorer",
    "FrontmatterError",
    "GateResult",
    "LandingPageScorer",
    "ReadinessResult",
    "ReadinessTelemetry",
    "SimproVaultClient",
    "ValidationSession",
    "_artifact_kind_rule_id",
    "_blocked_for_gate",
    "_blocked_readiness_result",
    "_bom_runtime_policy",
    "_captured_context_payloads",
    "_captured_json",
    "_captured_proof_content",
    "_content_score",
    "_failure_gate",
    "_gate_from_findings",
    "_gate_from_score",
    "_gate_from_url_summary",
    "_no_fit_customer_proof_findings",
    "_read_article_snapshot",
    "_resolve_artifact_kind_value",
    "_run_publish_readiness",
    "_run_context_gate",
    "_score_content",
    "_scorecard_from_scorer_result",
    "_sealed_blocked_result",
    "_timed_call",
    "_utc_now",
    "_validate_actual_readiness_execution",
    "_validate_bom_and_capture_hashes",
    "blog_assembly_bom_guard",
    "blog_identity_guard",
    "build_final_readiness_attestation",
    "build_stage_receipt",
    "context_binding_guard",
    "finalize_blocked_result",
    "format_text_report",
    "load_validated_claim_set",
    "main",
    "parse_publishable_markdown",
    "read_publishable_markdown",
    "readiness_stage_receipt_path",
    "run_publish_readiness",
    "validate_file_urls",
    "validate_passed_readiness_result",
    "write_readiness_result",
    "write_stage_receipt",
]
