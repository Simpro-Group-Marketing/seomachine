"""Compatibility facade for focused editorial-plan validation."""

from __future__ import annotations

import sys
from pathlib import Path

if not __package__:  # pragma: no cover - top-level/direct-script compatibility.
    repository_root = str(Path(__file__).resolve().parents[2])
    if repository_root not in sys.path:
        sys.path.insert(0, repository_root)
    __package__ = "data_sources.modules"

from .editorial_plan.contracts import (
    AUDIENCE_LANGUAGE_RESEARCH_FIELDS,
    BRAND_INTERNAL_DOMAINS,
    CTA_TYPES,
    EDITORIAL_PLAN_SCHEMA,
    ENGAGEMENT_FIELDS,
    ENTITY_MAP_FIELDS,
    FAQ_POLICY_FIELDS,
    FAQ_SECTION_TYPE,
    FUNNEL_STAGES,
    INTERNAL_LINK_FIELDS,
    KEYWORD_DECISION_FIELDS,
    KEYWORD_DECISION_SCHEMA,
    LINK_POLICY_OVERRIDE_FIELDS,
    META_FIELDS,
    ORIGINAL_CONTRIBUTION_FIELDS,
    OWNED_INTERNAL_DOMAINS,
    PAA_POLICY_FIELDS,
    QUERY_OWNERSHIP_FIELDS,
    READER_CONTRACT_FIELDS,
    RFC3339_UTC_RE,
    REWRITE_DECISIONS_FIELDS,
    SECTION_FIELDS,
    SECTION_TYPES,
    SERP_APPROVED_COLLECTORS,
    SERP_EVIDENCE_ATTESTATION_PURPOSE,
    SERP_EVIDENCE_FIELDS,
    SERP_EVIDENCE_SCHEMA,
    SERP_OBSERVATION_FIELDS,
    SERP_RAW_CAPTURE_ATTESTATION_PURPOSE,
    SERP_RAW_CAPTURE_FIELDS,
    SERP_RAW_CAPTURE_SCHEMA,
    SERP_RESULT_FIELDS,
    SERP_STRATEGY_FIELDS,
    TOP_LEVEL_FIELDS,
)
from .editorial_plan.dependencies import (
    EditorialPlanDependencies,
    default_editorial_plan_dependencies,
)
from .editorial_plan.link_policy import internal_link_guidelines_from_plan
from .editorial_plan.orchestration import _check_loaded_plan, check_file
from .editorial_plan.plan_validation import check_plan
from .editorial_plan.serp_capture import (
    build_serp_evidence,
    load_json_text,
    load_normalized_serp_raw_capture,
)
from .editorial_plan.serp_validation import (
    _check_serp_evidence_payload,
    check_serp_evidence_file,
)


__all__ = [
    "AUDIENCE_LANGUAGE_RESEARCH_FIELDS",
    "BRAND_INTERNAL_DOMAINS",
    "CTA_TYPES",
    "EDITORIAL_PLAN_SCHEMA",
    "ENGAGEMENT_FIELDS",
    "ENTITY_MAP_FIELDS",
    "EditorialPlanDependencies",
    "FAQ_POLICY_FIELDS",
    "FAQ_SECTION_TYPE",
    "FUNNEL_STAGES",
    "INTERNAL_LINK_FIELDS",
    "KEYWORD_DECISION_FIELDS",
    "KEYWORD_DECISION_SCHEMA",
    "LINK_POLICY_OVERRIDE_FIELDS",
    "META_FIELDS",
    "ORIGINAL_CONTRIBUTION_FIELDS",
    "OWNED_INTERNAL_DOMAINS",
    "PAA_POLICY_FIELDS",
    "QUERY_OWNERSHIP_FIELDS",
    "READER_CONTRACT_FIELDS",
    "RFC3339_UTC_RE",
    "REWRITE_DECISIONS_FIELDS",
    "SECTION_FIELDS",
    "SECTION_TYPES",
    "SERP_APPROVED_COLLECTORS",
    "SERP_EVIDENCE_ATTESTATION_PURPOSE",
    "SERP_EVIDENCE_FIELDS",
    "SERP_EVIDENCE_SCHEMA",
    "SERP_OBSERVATION_FIELDS",
    "SERP_RAW_CAPTURE_ATTESTATION_PURPOSE",
    "SERP_RAW_CAPTURE_FIELDS",
    "SERP_RAW_CAPTURE_SCHEMA",
    "SERP_RESULT_FIELDS",
    "SERP_STRATEGY_FIELDS",
    "TOP_LEVEL_FIELDS",
    "_check_loaded_plan",
    "_check_serp_evidence_payload",
    "build_serp_evidence",
    "check_file",
    "check_plan",
    "check_serp_evidence_file",
    "default_editorial_plan_dependencies",
    "internal_link_guidelines_from_plan",
    "load_json_text",
    "load_normalized_serp_raw_capture",
]
