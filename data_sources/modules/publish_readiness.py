"""Stable explicit facade for publish-readiness APIs and CLI."""
# ruff: noqa: F401

from __future__ import annotations

import sys
from pathlib import Path

if not __package__:  # pragma: no cover - direct script bootstrap.
    repository_root = str(Path(__file__).resolve().parents[2])
    if repository_root not in sys.path:
        sys.path.insert(0, repository_root)
    __package__ = "data_sources.modules"

try:
    from .readiness.dependencies import ReadinessDependencies
    from .publish_readiness_core import (
        ContentScorer,
        LandingPageScorer,
        ReadinessTelemetry,
        SimproVaultClient,
        _bom_runtime_policy,
        _no_fit_customer_proof_findings,
        _run_publish_readiness,
        _score_content,
        _scorecard_from_scorer_result,
        _validate_actual_readiness_execution,
        build_final_readiness_attestation,
        build_stage_receipt,
        format_text_report,
        load_validated_claim_set,
        main,
        read_publishable_markdown,
        readiness_stage_receipt_path,
        run_publish_readiness,
        validate_file_urls,
        validate_passed_readiness_result,
        write_readiness_result,
        write_stage_receipt,
    )
    from .readiness.common import (
        ai_copy_linter,
        answer_withholding_guard,
        blog_assembly_bom_guard,
        competitive_shortlist_guard,
        context_binding_guard,
        customer_proof_diversity_guard,
        early_artifact_guard,
        eeat_strength_guard,
        editorial_plan_guard,
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
except ImportError:  # pragma: no cover - direct script compatibility.
    from readiness.dependencies import ReadinessDependencies
    from publish_readiness_core import (
        ContentScorer,
        LandingPageScorer,
        ReadinessTelemetry,
        SimproVaultClient,
        _bom_runtime_policy,
        _no_fit_customer_proof_findings,
        _run_publish_readiness,
        _score_content,
        _scorecard_from_scorer_result,
        _validate_actual_readiness_execution,
        build_final_readiness_attestation,
        build_stage_receipt,
        format_text_report,
        load_validated_claim_set,
        main,
        read_publishable_markdown,
        readiness_stage_receipt_path,
        run_publish_readiness,
        validate_file_urls,
        validate_passed_readiness_result,
        write_readiness_result,
        write_stage_receipt,
    )
    from readiness.common import (
        ai_copy_linter,
        answer_withholding_guard,
        blog_assembly_bom_guard,
        competitive_shortlist_guard,
        context_binding_guard,
        customer_proof_diversity_guard,
        early_artifact_guard,
        eeat_strength_guard,
        editorial_plan_guard,
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


__all__ = [
    "build_final_readiness_attestation",
    "format_text_report",
    "ReadinessDependencies",
    "main",
    "readiness_stage_receipt_path",
    "run_publish_readiness",
    "validate_passed_readiness_result",
    "write_readiness_result",
]


if __name__ == "__main__":
    raise SystemExit(main())
