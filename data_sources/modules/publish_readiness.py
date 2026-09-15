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

from . import (
    ai_copy_linter,
    answer_withholding_guard,
    blog_assembly_bom_guard,
    competitive_shortlist_guard,
    context_binding_guard,
    customer_proof_diversity_guard,
    early_artifact_guard,
    editorial_plan_guard,
    eeat_strength_guard,
    faq_answer_quality_guard,
    faq_proof_guard,
    fred_authority_guard,
    hindsight_boundary_guard,
    industry_cluster_link_policy,
    metric_proof_pack_guard,
    named_feature_status_guard,
    numeric_claim_source_guard,
    paa_provenance_guard,
    public_artifact_guard,
    public_research_link_guard,
    review_story_identity_guard,
    semrush_keyword_decision_guard,
    source_quality_guard,
    source_support_guard,
    vault_brand_language_guard,
)
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
from .blog_bom_validation import api as blog_assembly_bom_guard
from .customer_proof import diversity as customer_proof_diversity_guard
from .editorial_plan import orchestration as editorial_plan_guard
from .paa_provenance import evaluation as paa_provenance_guard

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
    "ai_copy_linter",
    "answer_withholding_guard",
    "blog_assembly_bom_guard",
    "build_final_readiness_attestation",
    "build_stage_receipt",
    "competitive_shortlist_guard",
    "context_binding_guard",
    "customer_proof_diversity_guard",
    "early_artifact_guard",
    "editorial_plan_guard",
    "eeat_strength_guard",
    "faq_answer_quality_guard",
    "faq_proof_guard",
    "format_text_report",
    "fred_authority_guard",
    "hindsight_boundary_guard",
    "industry_cluster_link_policy",
    "load_validated_claim_set",
    "main",
    "metric_proof_pack_guard",
    "named_feature_status_guard",
    "numeric_claim_source_guard",
    "paa_provenance_guard",
    "public_artifact_guard",
    "public_research_link_guard",
    "read_publishable_markdown",
    "readiness_stage_receipt_path",
    "review_story_identity_guard",
    "run_publish_readiness",
    "semrush_keyword_decision_guard",
    "source_quality_guard",
    "source_support_guard",
    "validate_file_urls",
    "validate_passed_readiness_result",
    "vault_brand_language_guard",
    "write_readiness_result",
    "write_stage_receipt",
]


if __name__ == "__main__":
    raise SystemExit(main())
