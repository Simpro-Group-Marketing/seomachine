"""Strict constants for blog assembly BOM validation."""

from __future__ import annotations

import re
from typing import Any

from ..blog_assembly_bom import BOM_SCHEMA_V3

NORMAL_PROVISIONAL_STAGES = ("draft", "scrub", "context_binding")
NONVAULT_CUSTOMER_PROOF_SCHEMA = (
    "simpro-nonvault-customer-proof-selector-evidence/v1"
)
NORMAL_FINAL_STAGES = NORMAL_PROVISIONAL_STAGES + ("preflight_readiness",)
OPTIMIZED_PROVISIONAL_STAGES = NORMAL_FINAL_STAGES + (
    "optimization",
    "post_optimization_scrub",
    "post_optimization_context_binding",
)
OPTIMIZED_FINAL_STAGES = OPTIMIZED_PROVISIONAL_STAGES + (
    "final_preflight_readiness",
)
OPTIMIZED_TAIL_PROVISIONAL_STAGES = (
    "post_optimization_scrub",
    "post_optimization_context_binding",
)
OPTIMIZED_TAIL_FINAL_STAGES = OPTIMIZED_TAIL_PROVISIONAL_STAGES + (
    "final_preflight_readiness",
)
FORBIDDEN_TOPOLOGY_PATTERNS = (
    "/".join(("obsidian", "simpro brand context", "")),
    "".join(("wi", "ki", "/")),
    "_".join(("authority", "root")),
    "_".join(("simpro", "vault", "root")),
)
PATH_SHAPED_RE = re.compile(
    r"(?:^[A-Za-z]:[/\\]|^[/\\]{2}|^/|(?:^|[/\\])\.\.(?:[/\\]|$)|\$\{|%[A-Za-z_][A-Za-z0-9_]*%)"
)
REQUIRED_ARTIFACT_FIELDS = (
    "article",
    "validation_sidecar",
    "editorial_plan",
    "keyword_decision",
    "serp_evidence",
    "paa_artifact",
    "content_brief",
    "user_paa_csv",
    "answersocrates_blocker",
    "context_request",
    "context_pack",
    "context_receipt",
    "customer_proof_selector_evidence",
    "fred_authority_evidence",
    "hindsight_strategy_evidence",
    "execution_evidence",
    "optimizer_outputs",
    "stage_receipts",
    "stage_evidence",
    "prior_preflight_readiness",
    "preflight_readiness",
)
V1_V2_REQUIRED_ARTIFACT_FIELDS = tuple(
    field for field in REQUIRED_ARTIFACT_FIELDS
    if field != "hindsight_strategy_evidence"
)
REQUIRED_TOP_LEVEL_FIELDS = frozenset(
    {
        "schema",
        "lifecycle_state",
        "workflow_mode",
        "assembly_date",
        "identity",
        "artifacts",
        "connector_binding",
        "author_policy",
        "schema_policy",
        "industry_cluster_link_policy",
        "eeat_strength_policy",
        "faq_policy",
        "paa_policy",
        "editorial_plan_summary",
        "workflow",
        "preflight",
    }
)
V2_REQUIRED_TOP_LEVEL_FIELDS = REQUIRED_TOP_LEVEL_FIELDS | frozenset(
    {"machine_reviews"}
)
V3_REQUIRED_TOP_LEVEL_FIELDS = V2_REQUIRED_TOP_LEVEL_FIELDS | frozenset(
    {"hindsight_strategy_policy"}
)
POST_PUBLISH_MEASUREMENT_RECEIPT_SCHEMA = (
    "simpro-post-publish-measurement-receipt/v1"
)


def required_artifact_fields(schema: Any) -> tuple[str, ...]:
    """Return the strict inventory contract for one BOM schema."""
    if schema == BOM_SCHEMA_V3:
        return REQUIRED_ARTIFACT_FIELDS
    return V1_V2_REQUIRED_ARTIFACT_FIELDS


__all__ = [
    "FORBIDDEN_TOPOLOGY_PATTERNS",
    "NONVAULT_CUSTOMER_PROOF_SCHEMA",
    "NORMAL_FINAL_STAGES",
    "NORMAL_PROVISIONAL_STAGES",
    "OPTIMIZED_FINAL_STAGES",
    "OPTIMIZED_PROVISIONAL_STAGES",
    "OPTIMIZED_TAIL_FINAL_STAGES",
    "OPTIMIZED_TAIL_PROVISIONAL_STAGES",
    "PATH_SHAPED_RE",
    "POST_PUBLISH_MEASUREMENT_RECEIPT_SCHEMA",
    "REQUIRED_ARTIFACT_FIELDS",
    "REQUIRED_TOP_LEVEL_FIELDS",
    "V1_V2_REQUIRED_ARTIFACT_FIELDS",
    "V2_REQUIRED_TOP_LEVEL_FIELDS",
    "V3_REQUIRED_TOP_LEVEL_FIELDS",
    "required_artifact_fields",
]
