"""Build and finalize strict, evidence-backed blog assembly BOM artifacts."""
# ruff: noqa: F401

from __future__ import annotations

import argparse
import copy
import json
import os
import re
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

try:
    from .. import (
        blog_assembly_capabilities,
        blog_identity_guard,
        context_binding_guard,
        eeat_strength_guard,
        editorial_plan_guard,
        industry_cluster_link_policy,
        machine_review,
        paa_provenance_guard,
        semrush_keyword_decision_guard,
    )
    from ..blog_assembly_contract import (
        artifact_inventory_snapshots,
        atomic_write_json,
        canonical_artifact,
        canonical_artifact_identity,
        canonical_article_run_id,
        canonical_snapshot_artifact,
        canonical_json_sha256,
        expected_blog_gate_inventory,
        file_sha256,
        is_json_number,
        load_json_object_snapshot,
        NORMAL_PROVISIONAL_STAGES,
        normalized_text_sha256,
        OPTIMIZED_PROVISIONAL_STAGES,
        resolve_artifact,
        sidecar_evidence_binding_errors,
        validate_current_assembly_date,
        validate_sha256,
        verify_artifact,
    )
    from ..faq_structure import detect_faq_structure
    from ..blog_assembly_stage_receipt import stage_evidence_path
    from ..named_person import is_named_person
    from ..publishable_markdown import PublishableMarkdown, read_publishable_markdown
    from ..schema_item_list import inspect_item_list_schema
    from ..video_embed import inspect_video_embeds
except ImportError:  # pragma: no cover - supports direct script execution.
    import blog_assembly_capabilities
    import blog_identity_guard
    import context_binding_guard
    import eeat_strength_guard
    import editorial_plan_guard
    import industry_cluster_link_policy
    import machine_review
    import paa_provenance_guard
    import semrush_keyword_decision_guard
    from blog_assembly_contract import (
        artifact_inventory_snapshots,
        atomic_write_json,
        canonical_artifact,
        canonical_artifact_identity,
        canonical_article_run_id,
        canonical_snapshot_artifact,
        canonical_json_sha256,
        expected_blog_gate_inventory,
        file_sha256,
        is_json_number,
        load_json_object_snapshot,
        NORMAL_PROVISIONAL_STAGES,
        normalized_text_sha256,
        OPTIMIZED_PROVISIONAL_STAGES,
        resolve_artifact,
        sidecar_evidence_binding_errors,
        validate_current_assembly_date,
        validate_sha256,
        verify_artifact,
    )
    from faq_structure import detect_faq_structure
    from blog_assembly_stage_receipt import stage_evidence_path
    from named_person import is_named_person
    from publishable_markdown import PublishableMarkdown, read_publishable_markdown
    from schema_item_list import inspect_item_list_schema
    from video_embed import inspect_video_embeds


BOM_SCHEMA_V1 = "simpro-blog-assembly-bom/v1"
BOM_SCHEMA_V2 = "simpro-blog-assembly-bom/v2"
BOM_SCHEMA_V3 = "simpro-blog-assembly-bom/v3"
BOM_SCHEMA = BOM_SCHEMA_V3
ARCHIVED_BOM_SCHEMAS = frozenset({BOM_SCHEMA_V1, BOM_SCHEMA_V2, BOM_SCHEMA_V3})
EDITORIAL_PLAN_SCHEMA = "simpro-blog-editorial-plan/v1"
CONNECTOR_CUSTOMER_PROOF_SCHEMA = "simpro-customer-proof-selector-evidence/v1"
NONVAULT_CUSTOMER_PROOF_SCHEMA = (
    "simpro-nonvault-customer-proof-selector-evidence/v1"
)
READINESS_SCHEMA = "simpro-publish-readiness-result/v1"
PACK_SCHEMA = "simpro-product-context-pack/v2"
RECEIPT_SCHEMA = "simpro-context-receipt/v1"
WORKFLOW_MODES = frozenset({"new", "rewrite"})
LIFECYCLE_STATES = frozenset({"provisional", "final"})
PLACEHOLDER_VALUES = blog_identity_guard.PLACEHOLDER_VALUES
NON_CONNECTOR_REASON = (
    "Final article contains no Simpro brand, URL, or connector-sensitive language."
)
