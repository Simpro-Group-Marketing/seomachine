"""Publish readiness implementation behind the stable compatibility facade.

Runs the existing blog proof and quality gates in one deterministic order so
agents do not have to copy the full command stack by hand.
"""
# ruff: noqa: F401

from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence

try:
    from .. import (
        ai_copy_linter,
        answer_withholding_guard,
        blog_identity_guard,
        blog_strategy_plan_guard,
        chrome_review_evidence,
        context_binding_guard,
        competitive_shortlist_guard,
        early_artifact_guard,
        eeat_strength_guard,
        faq_answer_quality_guard,
        fred_authority_guard,
        hindsight_boundary_guard,
        faq_proof_guard,
        industry_cluster_link_policy,
        metric_proof_pack_guard,
        named_feature_status_guard,
        numeric_claim_source_guard,
        public_research_link_guard,
        public_artifact_guard,
        review_story_identity_guard,
        semrush_keyword_decision_guard,
        schema_handoff_guard,
        source_quality_plan_guard,
        source_support_guard,
        vault_brand_language_guard,
    )
    from ..blog_assembly_contract import (
        artifact_inventory_snapshots,
        atomic_write_json,
        canonical_artifact,
        canonical_article_run_id,
        canonical_json_bytes,
        expected_blog_gate_inventory,
        file_sha256,
        is_json_number,
        load_json_object_snapshot,
        order_blog_gate_results,
        resolve_artifact,
        validate_sha256,
    )
    from ..blog_assembly_stage_receipt import (
        build_stage_receipt,
        check_receipt_chain,
        write_stage_receipt,
    )
    from ..publishable_markdown import (
        FrontmatterError,
        parse_publishable_markdown,
        read_publishable_markdown,
        split_frontmatter,
    )
    from ..readiness_gate_context import _issue_readiness_gate_context
    from .inputs import ReadinessInputs
    from .contracts import (
        GATE_RESULT_FIELDS,
        FINAL_READINESS_RESULT_SCHEMA,
        FINAL_RELEASE_FIELDS,
        PASSED_RESULT_FIELDS,
        READINESS_RESULT_SCHEMA,
        READINESS_TOOL,
        ExecutedReadinessResult,
        GateResult,
        ReadinessResult,
        sign_readiness_execution,
    )
    from .gates import CONTENT_GATE_NAMES, ContentGateInputs, run_content_gate
    from .session import ValidationSession
    from .orchestrator import run_in_session
    from .persistence import persist_new_result_pair, persist_result_pair
    from .telemetry import ReadinessTelemetry
    from .scoring_contracts import compatibility_symbols
    from ..simpro_vault_client import SimproVaultClient
    from ..vault_claim_receipts import (
        ValidatedClaimSet,
        VaultClaimReceiptError,
        load_validated_claim_set,
    )
    from ..guard_common import should_fail, summarize_findings
    from ..url_validator import UrlValidationSummary, UrlValidator, validate_file_urls
    import data_sources.modules.customer_proof.diversity as customer_proof_diversity_guard
    import data_sources.modules.editorial_plan.orchestration as editorial_plan_guard
    import data_sources.modules.paa_provenance.evaluation as paa_provenance_guard
except ImportError:  # pragma: no cover - supports direct script execution.
    import ai_copy_linter
    import answer_withholding_guard
    import blog_identity_guard
    import blog_strategy_plan_guard
    import chrome_review_evidence
    import context_binding_guard
    import competitive_shortlist_guard
    import early_artifact_guard
    import eeat_strength_guard
    import faq_answer_quality_guard
    import fred_authority_guard
    import hindsight_boundary_guard
    import faq_proof_guard
    import industry_cluster_link_policy
    import metric_proof_pack_guard
    import named_feature_status_guard
    import numeric_claim_source_guard
    import public_research_link_guard
    import public_artifact_guard
    import review_story_identity_guard
    import semrush_keyword_decision_guard
    import schema_handoff_guard
    import source_quality_plan_guard
    import source_support_guard
    import vault_brand_language_guard
    from blog_assembly_contract import (
        artifact_inventory_snapshots,
        atomic_write_json,
        canonical_artifact,
        canonical_article_run_id,
        canonical_json_bytes,
        expected_blog_gate_inventory,
        file_sha256,
        is_json_number,
        load_json_object_snapshot,
        order_blog_gate_results,
        resolve_artifact,
        validate_sha256,
    )
    from blog_assembly_stage_receipt import (
        build_stage_receipt,
        check_receipt_chain,
        write_stage_receipt,
    )
    from publishable_markdown import (
        FrontmatterError,
        parse_publishable_markdown,
        read_publishable_markdown,
        split_frontmatter,
    )
    from readiness_gate_context import _issue_readiness_gate_context
    from readiness.inputs import ReadinessInputs
    from readiness.contracts import (
        GATE_RESULT_FIELDS,
        FINAL_READINESS_RESULT_SCHEMA,
        FINAL_RELEASE_FIELDS,
        PASSED_RESULT_FIELDS,
        READINESS_RESULT_SCHEMA,
        READINESS_TOOL,
        ExecutedReadinessResult,
        GateResult,
        ReadinessResult,
        sign_readiness_execution,
    )
    from readiness.gates import CONTENT_GATE_NAMES, ContentGateInputs, run_content_gate
    from readiness.session import ValidationSession
    from readiness.orchestrator import run_in_session
    from readiness.persistence import persist_new_result_pair, persist_result_pair
    from readiness.telemetry import ReadinessTelemetry
    from readiness.scoring_contracts import compatibility_symbols
    from simpro_vault_client import SimproVaultClient
    from vault_claim_receipts import (
        ValidatedClaimSet,
        VaultClaimReceiptError,
        load_validated_claim_set,
    )
    from guard_common import should_fail, summarize_findings
    from url_validator import UrlValidationSummary, UrlValidator, validate_file_urls
    import customer_proof.diversity as customer_proof_diversity_guard
    import editorial_plan.orchestration as editorial_plan_guard
    import paa_provenance.evaluation as paa_provenance_guard


_ExecutedReadinessResult = ExecutedReadinessResult
_sign_readiness_execution = sign_readiness_execution
ContentScorer, LandingPageScorer, SEO_PUBLISHING_THRESHOLD, SEO_TARGET_SCORE = (
    compatibility_symbols()
)

NO_FIT_CUSTOMER_PROOF_OUTCOME = "no_fit_customer_proof"
CUSTOMER_PROOF_NO_FIT_MARKERS = (
    "case study",
    "customer story",
    "customer proof",
    "testimonial",
    "review story",
    "review-derived",
    "reviewer",
    "capterra",
    "g2.com",
    "software advice",
    "/case-studies/",
    "quote matrix",
)
CUSTOMER_PROOF_EXACT_QUOTE_RE = re.compile(
    r"(?:\"[^\"]{20,}\"|\u201c[^\u201d]{20,}\u201d)"
)
CUSTOMER_PROOF_QUOTE_CONTEXT_RE = re.compile(
    r"\b(?:customer|review|testimonial|said|says|reviewer|quoted)\b",
    re.IGNORECASE,
)
ARTICLE_GATES = (
    (
        "industry_cluster_link_policy",
        "Industry Cluster Link Policy",
        industry_cluster_link_policy,
    ),
    (
        "metric_proof_pack",
        "Metric Proof Pack",
        metric_proof_pack_guard,
    ),
    (
        "numeric_claim_source",
        "Numeric Claim Source",
        numeric_claim_source_guard,
    ),
    (
        "faq_answer_quality",
        "FAQ Answer Quality",
        faq_answer_quality_guard,
    ),
    (
        "faq_proof",
        "FAQ Proof",
        faq_proof_guard,
    ),
    (
        "paa_provenance",
        "PAA Provenance",
        paa_provenance_guard,
    ),
    (
        "editorial_plan",
        "Editorial Plan",
        editorial_plan_guard,
    ),
    (
        "semrush_keyword_decision",
        "Semrush Keyword Decision",
        semrush_keyword_decision_guard,
    ),
    (
        "blog_strategy",
        "Blog Strategy",
        blog_strategy_plan_guard,
    ),
    (
        "competitive_shortlist",
        "Competitive Shortlist",
        competitive_shortlist_guard,
    ),
    (
        "hindsight_boundary",
        "Hindsight Boundary",
        hindsight_boundary_guard,
    ),
    (
        "source_support",
        "Source Support",
        source_support_guard,
    ),
    (
        "source_quality",
        "Source Quality and Lifecycle",
        source_quality_plan_guard,
    ),
    (
        "customer_proof_diversity",
        "Customer Proof Diversity",
        customer_proof_diversity_guard,
    ),
    (
        "review_story_identity",
        "Review Story Identity",
        review_story_identity_guard,
    ),
    (
        "eeat_strength",
        "E-E-A-T Strength",
        eeat_strength_guard,
    ),
    (
        "early_artifact",
        "Early Artifact",
        early_artifact_guard,
    ),
    (
        "answer_withholding",
        "Answer Withholding",
        answer_withholding_guard,
    ),
    (
        "schema_handoff",
        "Schema Handoff",
        schema_handoff_guard,
    ),
    (
        "vault_brand_language",
        "Vault Brand Language",
        vault_brand_language_guard,
    ),
    (
        "named_feature_status",
        "Named Feature Status",
        named_feature_status_guard,
    ),
    (
        "fred_authority",
        "Fred Voccola Authority",
        fred_authority_guard,
    ),
)

SIMPRO_CONTEXT_GATE_NAMES = frozenset({
    "vault_brand_language",
    "named_feature_status",
})

from .gate_registry import assert_gate_executor_invariant

assert_gate_executor_invariant(
    (name for name, _, _ in ARTICLE_GATES),
    CONTENT_GATE_NAMES,
)
