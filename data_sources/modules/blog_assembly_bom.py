"""Compatibility API and CLI for deterministic blog assembly BOMs."""
# ruff: noqa: F401

try:
    from .blog_assembly.cli import _reject_bom_output_collision, main
    from .blog_assembly.common import (
        ARCHIVED_BOM_SCHEMAS,
        BOM_SCHEMA,
        BOM_SCHEMA_V1,
        BOM_SCHEMA_V2,
        BOM_SCHEMA_V3,
        CONNECTOR_CUSTOMER_PROOF_SCHEMA,
        EDITORIAL_PLAN_SCHEMA,
        LIFECYCLE_STATES,
        NONVAULT_CUSTOMER_PROOF_SCHEMA,
        NON_CONNECTOR_REASON,
        PACK_SCHEMA,
        PLACEHOLDER_VALUES,
        READINESS_SCHEMA,
        RECEIPT_SCHEMA,
        WORKFLOW_MODES,
        load_json_object_snapshot,
    )
    from .blog_assembly.construction import build_blog_assembly_bom_from_files
    from .blog_assembly.contracts import (
        _has_video_embed,
        _is_number,
        _is_supported_bom_schema,
        _iso_date,
        _label_paths,
        _machine_review_bindings,
        _nonempty,
        _optional_json_schema,
        _read_json_object,
        _required_article_scalar,
        _required_enum,
        _required_mapping,
        _required_string,
        _string_list,
        _validate_input_path,
        _validate_path_sequence,
        _visible_faq_questions,
    )
    from .blog_assembly.derivation import (
        _execution_evidence_from_prior_preflight,
        _hindsight_strategy_block,
        _hindsight_strategy_policy,
        _normalize_hindsight_block_text,
        _optional_artifact,
    )
    from .blog_assembly.dependencies import BomValidationDependencies
    from .blog_assembly.finalization import (
        build_blog_assembly_bom,
        finalize_blog_assembly_bom,
        validate_preflight_stage_receipt_binding,
        write_blog_assembly_bom,
    )
    from .blog_assembly.policy import (
        _author_policy,
        _connector_binding,
        _derive_paa_policy,
        _editorial_plan_summary,
        _identity_from_article,
        _schema_policy,
        _validate_article_identity,
        _validate_editorial_plan,
    )
    from .blog_assembly.preflight import (
        _resolvable_receipt_evidence_hashes,
        _validate_passed_preflight,
        _verify_bom_artifacts_unchanged,
    )
    from .blog_assembly.stage_receipts import (
        _validate_prior_preflight_payloads,
        _validate_prior_preflight_readiness,
        _validate_provisional_stage_receipts,
    )
except ImportError:  # pragma: no cover - direct script compatibility.
    from blog_assembly.cli import _reject_bom_output_collision, main
    from blog_assembly.common import (
        ARCHIVED_BOM_SCHEMAS,
        BOM_SCHEMA,
        BOM_SCHEMA_V1,
        BOM_SCHEMA_V2,
        BOM_SCHEMA_V3,
        CONNECTOR_CUSTOMER_PROOF_SCHEMA,
        EDITORIAL_PLAN_SCHEMA,
        LIFECYCLE_STATES,
        NONVAULT_CUSTOMER_PROOF_SCHEMA,
        NON_CONNECTOR_REASON,
        PACK_SCHEMA,
        PLACEHOLDER_VALUES,
        READINESS_SCHEMA,
        RECEIPT_SCHEMA,
        WORKFLOW_MODES,
        load_json_object_snapshot,
    )
    from blog_assembly.construction import build_blog_assembly_bom_from_files
    from blog_assembly.contracts import (
        _has_video_embed,
        _is_number,
        _is_supported_bom_schema,
        _iso_date,
        _label_paths,
        _machine_review_bindings,
        _nonempty,
        _optional_json_schema,
        _read_json_object,
        _required_article_scalar,
        _required_enum,
        _required_mapping,
        _required_string,
        _string_list,
        _validate_input_path,
        _validate_path_sequence,
        _visible_faq_questions,
    )
    from blog_assembly.derivation import (
        _execution_evidence_from_prior_preflight,
        _hindsight_strategy_block,
        _hindsight_strategy_policy,
        _normalize_hindsight_block_text,
        _optional_artifact,
    )
    from blog_assembly.dependencies import BomValidationDependencies
    from blog_assembly.finalization import (
        build_blog_assembly_bom,
        finalize_blog_assembly_bom,
        validate_preflight_stage_receipt_binding,
        write_blog_assembly_bom,
    )
    from blog_assembly.policy import (
        _author_policy,
        _connector_binding,
        _derive_paa_policy,
        _editorial_plan_summary,
        _identity_from_article,
        _schema_policy,
        _validate_article_identity,
        _validate_editorial_plan,
    )
    from blog_assembly.preflight import (
        _resolvable_receipt_evidence_hashes,
        _validate_passed_preflight,
        _verify_bom_artifacts_unchanged,
    )
    from blog_assembly.stage_receipts import (
        _validate_prior_preflight_payloads,
        _validate_prior_preflight_readiness,
        _validate_provisional_stage_receipts,
    )


__all__ = [
    "ARCHIVED_BOM_SCHEMAS",
    "BOM_SCHEMA",
    "BOM_SCHEMA_V1",
    "BOM_SCHEMA_V2",
    "BOM_SCHEMA_V3",
    "BomValidationDependencies",
    "CONNECTOR_CUSTOMER_PROOF_SCHEMA",
    "EDITORIAL_PLAN_SCHEMA",
    "LIFECYCLE_STATES",
    "NONVAULT_CUSTOMER_PROOF_SCHEMA",
    "NON_CONNECTOR_REASON",
    "PACK_SCHEMA",
    "PLACEHOLDER_VALUES",
    "READINESS_SCHEMA",
    "RECEIPT_SCHEMA",
    "WORKFLOW_MODES",
    "build_blog_assembly_bom",
    "build_blog_assembly_bom_from_files",
    "finalize_blog_assembly_bom",
    "load_json_object_snapshot",
    "main",
    "validate_preflight_stage_receipt_binding",
    "write_blog_assembly_bom",
]


if __name__ == "__main__":
    raise SystemExit(main())
