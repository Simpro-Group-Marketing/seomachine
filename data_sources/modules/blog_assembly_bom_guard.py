"""Compatibility facade for strict blog assembly BOM validation."""
# ruff: noqa: F401

from __future__ import annotations

import sys
from pathlib import Path

if __package__ in {None, ""}:  # pragma: no cover - direct script compatibility.
    repository_root = Path(__file__).resolve().parents[2]
    if str(repository_root) not in sys.path:
        sys.path.insert(0, str(repository_root))
    import blog_assembly_stage_receipt
else:  # pragma: no cover - exercised by normal package imports.
    from data_sources.modules import blog_assembly_stage_receipt

from data_sources.modules import (  # noqa: E402
    blog_assembly_capabilities,
    blog_assembly_contract,
    blog_identity_guard,
    context_binding_guard,
    eeat_strength_guard,
    editorial_plan_guard,
    industry_cluster_link_policy,
    machine_review,
    paa_provenance_guard,
    semrush_keyword_decision_guard,
)
from data_sources.modules import blog_bom_validation as _impl  # noqa: E402
from data_sources.modules.blog_assembly_bom import (  # noqa: E402
    ARCHIVED_BOM_SCHEMAS,
    BOM_SCHEMA,
    BOM_SCHEMA_V1,
    BOM_SCHEMA_V2,
    BOM_SCHEMA_V3,
    EDITORIAL_PLAN_SCHEMA,
    LIFECYCLE_STATES,
    WORKFLOW_MODES,
)

BomValidationDependencies = _impl.BomValidationDependencies
FORBIDDEN_TOPOLOGY_PATTERNS = _impl.FORBIDDEN_TOPOLOGY_PATTERNS
NONVAULT_CUSTOMER_PROOF_SCHEMA = _impl.NONVAULT_CUSTOMER_PROOF_SCHEMA
NORMAL_FINAL_STAGES = _impl.NORMAL_FINAL_STAGES
NORMAL_PROVISIONAL_STAGES = _impl.NORMAL_PROVISIONAL_STAGES
OPTIMIZED_FINAL_STAGES = _impl.OPTIMIZED_FINAL_STAGES
OPTIMIZED_PROVISIONAL_STAGES = _impl.OPTIMIZED_PROVISIONAL_STAGES
OPTIMIZED_TAIL_FINAL_STAGES = _impl.OPTIMIZED_TAIL_FINAL_STAGES
OPTIMIZED_TAIL_PROVISIONAL_STAGES = _impl.OPTIMIZED_TAIL_PROVISIONAL_STAGES
PATH_SHAPED_RE = _impl.PATH_SHAPED_RE
POST_PUBLISH_MEASUREMENT_RECEIPT_SCHEMA = (
    _impl.POST_PUBLISH_MEASUREMENT_RECEIPT_SCHEMA
)
REQUIRED_ARTIFACT_FIELDS = _impl.REQUIRED_ARTIFACT_FIELDS
REQUIRED_TOP_LEVEL_FIELDS = _impl.REQUIRED_TOP_LEVEL_FIELDS
V1_V2_REQUIRED_ARTIFACT_FIELDS = _impl.V1_V2_REQUIRED_ARTIFACT_FIELDS
V2_REQUIRED_TOP_LEVEL_FIELDS = _impl.V2_REQUIRED_TOP_LEVEL_FIELDS
V3_REQUIRED_TOP_LEVEL_FIELDS = _impl.V3_REQUIRED_TOP_LEVEL_FIELDS

_artifact_json_schema = _impl._artifact_json_schema
_bom_serp_expected_run_id = _impl._bom_serp_expected_run_id
_bom_workflow_run_id = _impl._bom_workflow_run_id
_check_artifact_inventory = _impl._check_artifact_inventory
_check_author = _impl._check_author
_check_connector = _impl._check_connector
_check_editorial_plan = _impl._check_editorial_plan
_check_hindsight_strategy_policy = _impl._check_hindsight_strategy_policy
_check_identity = _impl._check_identity
_check_machine_reviews = _impl._check_machine_reviews
_check_paa_policy = _impl._check_paa_policy
_check_post_publish_measurement_receipt_exclusion = (
    _impl._check_post_publish_measurement_receipt_exclusion
)
_check_preflight = _impl._check_preflight
_check_research_provenance = _impl._check_research_provenance
_check_schema_and_faq = _impl._check_schema_and_faq
_check_supplied_path = _impl._check_supplied_path
_check_topology = _impl._check_topology
_check_workflow = _impl._check_workflow
_finding = _impl._finding
_is_artifact_snapshot_label = _impl._is_artifact_snapshot_label
_is_declared_artifact_path = _impl._is_declared_artifact_path
_is_number = _impl._is_number
_is_workspace_file = _impl._is_workspace_file
_load_bound_editorial_plan = _impl._load_bound_editorial_plan
_load_bound_json_object = _impl._load_bound_json_object
_parse_date = _impl._parse_date
_required_artifact_fields = _impl._required_artifact_fields
_sorted = _impl._sorted
_verified_optional_artifact_path = _impl._verified_optional_artifact_path
_verify_row = _impl._verify_row

check_archived_final_bom = _impl.check_archived_final_bom
check_bom = _impl.check_bom
check_bom_file = _impl.check_bom_file
missing_bom_finding = _impl.missing_bom_finding

__all__ = [
    "BomValidationDependencies",
    "check_archived_final_bom",
    "check_bom",
    "check_bom_file",
    "missing_bom_finding",
]
