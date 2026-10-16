"""Shared imports and gate tables for landing-page publish readiness.

The runner executes these proof and quality gates in one deterministic order so
agents do not have to copy the full command stack by hand.
"""
# ruff: noqa: F401

from __future__ import annotations

import argparse
import hashlib
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
        chrome_review_evidence,
        context_boundary_guard,
        context_binding_guard,
        competitive_shortlist_guard,
        early_artifact_guard,
        eeat_strength_guard,
        faq_answer_quality_guard,
        fred_authority_guard,
        hindsight_boundary_guard,
        faq_proof_guard,
        metric_proof_pack_guard,
        named_feature_status_guard,
        numeric_claim_source_guard,
        public_research_link_guard,
        public_artifact_guard,
        review_story_identity_guard,
        source_quality_guard,
        source_support_guard,
        vault_brand_language_guard,
    )
    from ..blog_assembly_contract import (
        atomic_write_json,
        is_json_number,
        load_json_object_snapshot,
        resolve_artifact,
    )
    from ..publishable_markdown import (
        FrontmatterError,
        parse_publishable_markdown,
        read_publishable_markdown,
        split_frontmatter,
    )
    from .inputs import ReadinessInputs
    from .contracts import (
        LANDING_AEO_NOT_APPLICABLE,
        LANDING_PAGE_SCORE_THRESHOLD,
        READINESS_RESULT_SCHEMA,
        ExecutedReadinessResult,
        GateResult,
        ReadinessResult,
    )
    from .gates import CONTENT_GATE_NAMES, ContentGateInputs, run_content_gate
    from .session import ValidationSession
    from .orchestrator import run_in_session
    from .telemetry import ReadinessTelemetry
    from .scoring_contracts import create_landing_page_scorer
    from ..vault_claim_receipts import (
        ValidatedClaimSet,
        VaultClaimReceiptError,
        load_validated_claim_set,
    )
    from ..guard_common import should_fail, summarize_findings
    from ..url_validator import UrlValidationSummary, UrlValidator
    import data_sources.modules.customer_proof.diversity as customer_proof_diversity_guard
except ImportError:  # pragma: no cover - supports direct script execution.
    import ai_copy_linter
    import answer_withholding_guard
    import blog_identity_guard
    import chrome_review_evidence
    import context_boundary_guard
    import context_binding_guard
    import competitive_shortlist_guard
    import early_artifact_guard
    import eeat_strength_guard
    import faq_answer_quality_guard
    import fred_authority_guard
    import hindsight_boundary_guard
    import faq_proof_guard
    import metric_proof_pack_guard
    import named_feature_status_guard
    import numeric_claim_source_guard
    import public_research_link_guard
    import public_artifact_guard
    import review_story_identity_guard
    import source_quality_guard
    import source_support_guard
    import vault_brand_language_guard
    from blog_assembly_contract import (
        atomic_write_json,
        is_json_number,
        load_json_object_snapshot,
        resolve_artifact,
    )
    from publishable_markdown import (
        FrontmatterError,
        parse_publishable_markdown,
        read_publishable_markdown,
        split_frontmatter,
    )
    from readiness.inputs import ReadinessInputs
    from readiness.contracts import (
        LANDING_AEO_NOT_APPLICABLE,
        LANDING_PAGE_SCORE_THRESHOLD,
        READINESS_RESULT_SCHEMA,
        ExecutedReadinessResult,
        GateResult,
        ReadinessResult,
    )
    from readiness.gates import CONTENT_GATE_NAMES, ContentGateInputs, run_content_gate
    from readiness.session import ValidationSession
    from readiness.orchestrator import run_in_session
    from readiness.telemetry import ReadinessTelemetry
    from readiness.scoring_contracts import create_landing_page_scorer
    from vault_claim_receipts import (
        ValidatedClaimSet,
        VaultClaimReceiptError,
        load_validated_claim_set,
    )
    from guard_common import should_fail, summarize_findings
    from url_validator import UrlValidationSummary, UrlValidator
    import customer_proof.diversity as customer_proof_diversity_guard


_ExecutedReadinessResult = ExecutedReadinessResult
LandingPageScorer = create_landing_page_scorer

ARTICLE_GATES = (
    (
        "context_boundary",
        "Context Boundary",
        context_boundary_guard,
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
        source_quality_guard,
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

from .gate_registry import assert_landing_gate_invariant

assert_landing_gate_invariant(
    (name for name, _, _ in ARTICLE_GATES),
    CONTENT_GATE_NAMES,
)
