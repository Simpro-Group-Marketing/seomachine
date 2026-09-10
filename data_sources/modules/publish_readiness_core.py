"""Publish readiness implementation behind the stable compatibility facade.

Runs the existing blog proof and quality gates in one deterministic order so
agents do not have to copy the full command stack by hand.
"""

from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence

try:
    from . import (
        ai_copy_linter,
        answer_withholding_guard,
        blog_assembly_bom_guard,
        blog_identity_guard,
        chrome_review_evidence,
        context_binding_guard,
        competitive_shortlist_guard,
        customer_proof_diversity_guard,
        early_artifact_guard,
        eeat_strength_guard,
        editorial_plan_guard,
        faq_answer_quality_guard,
        fred_authority_guard,
        hindsight_boundary_guard,
        faq_proof_guard,
        industry_cluster_link_policy,
        metric_proof_pack_guard,
        named_feature_status_guard,
        numeric_claim_source_guard,
        paa_provenance_guard,
        public_research_link_guard,
        public_artifact_guard,
        review_story_identity_guard,
        semrush_keyword_decision_guard,
        source_quality_guard,
        source_support_guard,
        vault_brand_language_guard,
    )
    from .content_scorer import ContentScorer
    from .blog_assembly_contract import (
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
    from .blog_assembly_stage_receipt import (
        build_stage_receipt,
        check_receipt_chain,
        write_stage_receipt,
    )
    from .landing_page_scorer import LandingPageScorer
    from .publishable_markdown import (
        FrontmatterError,
        parse_publishable_markdown,
        read_publishable_markdown,
        split_frontmatter,
    )
    from .readiness_gate_context import _issue_readiness_gate_context
    from .readiness.inputs import ReadinessInputs
    from .readiness.contracts import (
        GATE_RESULT_FIELDS,
        PASSED_RESULT_FIELDS,
        READINESS_RESULT_SCHEMA,
        READINESS_TOOL,
        ExecutedReadinessResult,
        GateResult,
        ReadinessResult,
        sign_readiness_execution,
    )
    from .readiness.finalization import build_final_attestation
    from .readiness.gates import CONTENT_GATE_NAMES, ContentGateInputs, run_content_gate
    from .readiness.session import ValidationSession
    from .readiness.orchestrator import run_in_session
    from .readiness.persistence import persist_result_pair
    from .readiness.telemetry import ReadinessTelemetry
    from .simpro_vault_client import SimproVaultClient
    from .vault_claim_receipts import (
        ValidatedClaimSet,
        VaultClaimReceiptError,
        load_validated_claim_set,
    )
    from .seo_quality_rater import PUBLISHING_THRESHOLD as SEO_PUBLISHING_THRESHOLD
    from .seo_quality_rater import SEO_TARGET_SCORE
    from .guard_common import should_fail, summarize_findings
    from .url_validator import UrlValidationSummary, validate_file_urls
except ImportError:  # pragma: no cover - supports direct script execution.
    import ai_copy_linter
    import answer_withholding_guard
    import blog_assembly_bom_guard
    import blog_identity_guard
    import chrome_review_evidence
    import context_binding_guard
    import competitive_shortlist_guard
    import customer_proof_diversity_guard
    import early_artifact_guard
    import eeat_strength_guard
    import editorial_plan_guard
    import faq_answer_quality_guard
    import fred_authority_guard
    import hindsight_boundary_guard
    import faq_proof_guard
    import industry_cluster_link_policy
    import metric_proof_pack_guard
    import named_feature_status_guard
    import numeric_claim_source_guard
    import paa_provenance_guard
    import public_research_link_guard
    import public_artifact_guard
    import review_story_identity_guard
    import semrush_keyword_decision_guard
    import source_quality_guard
    import source_support_guard
    import vault_brand_language_guard
    from content_scorer import ContentScorer
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
    from landing_page_scorer import LandingPageScorer
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
        PASSED_RESULT_FIELDS,
        READINESS_RESULT_SCHEMA,
        READINESS_TOOL,
        ExecutedReadinessResult,
        GateResult,
        ReadinessResult,
        sign_readiness_execution,
    )
    from readiness.finalization import build_final_attestation
    from readiness.gates import CONTENT_GATE_NAMES, ContentGateInputs, run_content_gate
    from readiness.session import ValidationSession
    from readiness.orchestrator import run_in_session
    from readiness.persistence import persist_result_pair
    from readiness.telemetry import ReadinessTelemetry
    from simpro_vault_client import SimproVaultClient
    from vault_claim_receipts import (
        ValidatedClaimSet,
        VaultClaimReceiptError,
        load_validated_claim_set,
    )
    from seo_quality_rater import PUBLISHING_THRESHOLD as SEO_PUBLISHING_THRESHOLD
    from seo_quality_rater import SEO_TARGET_SCORE
    from guard_common import should_fail, summarize_findings
    from url_validator import UrlValidationSummary, validate_file_urls


_ExecutedReadinessResult = ExecutedReadinessResult
_sign_readiness_execution = sign_readiness_execution

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

BLOG_ONLY_GATES = {"source_quality", "blog_strategy", "schema_handoff"}


SIMPRO_CONTEXT_GATE_NAMES = frozenset({
    "vault_brand_language",
    "named_feature_status",
})


def run_publish_readiness(
    file_path: str | Path,
    *,
    proof_sidecar: str | Path | None = None,
    context_request: str | Path | None = None,
    context_pack: str | Path | None = None,
    context_receipt: str | Path | None = None,
    assembly_bom: str | Path | None = None,
    vault_root: str | Path | None = None,
    ai_profile: str = "simpro-web",
    phase: str = "preflight",
    workspace_root: str | Path | None = None,
    artifact_kind: str | None = None,
    telemetry: ReadinessTelemetry | None = None,
) -> ReadinessResult:
    """Run the complete gate stack inside one trusted workspace boundary."""
    if phase not in {"preflight", "final"}:
        raise ValueError("phase must be preflight or final")
    root = Path(workspace_root or Path.cwd()).resolve()
    article_path = _resolve_workspace_input(file_path, workspace_root=root, field="file")
    proof_path = _resolve_optional_workspace_input(
        proof_sidecar,
        workspace_root=root,
        field="proof_sidecar",
    )
    request_path = _resolve_optional_workspace_input(
        context_request,
        workspace_root=root,
        field="context_request",
    )
    pack_path = _resolve_optional_workspace_input(
        context_pack,
        workspace_root=root,
        field="context_pack",
    )
    receipt_path = _resolve_optional_workspace_input(
        context_receipt,
        workspace_root=root,
        field="context_receipt",
    )
    bom_path = _resolve_optional_workspace_input(
        assembly_bom,
        workspace_root=root,
        field="assembly_bom",
    )
    raw = _run_publish_readiness_session(
        article_path,
        proof_sidecar=proof_path,
        context_request=request_path,
        context_pack=pack_path,
        context_receipt=receipt_path,
        assembly_bom=bom_path,
        vault_root=vault_root,
        ai_profile=ai_profile,
        phase=phase,
        workspace_root=root,
        artifact_kind=artifact_kind,
        telemetry=telemetry,
    )
    return _ExecutedReadinessResult(raw, workspace_root=root)


def build_final_readiness_attestation(
    preflight_result: Mapping[str, Any],
    *,
    final_bom: str | Path,
    workspace_root: str | Path | None = None,
    telemetry: ReadinessTelemetry | None = None,
) -> ReadinessResult:
    """Bind an authenticated full preflight to one validated final BOM."""
    root = _result_workspace_root(preflight_result, workspace_root)
    final_bom_path = _resolve_workspace_input(
        final_bom,
        workspace_root=root,
        field="final_bom",
    )
    return build_final_attestation(
        preflight_result,
        final_bom_path=final_bom_path,
        workspace_root=root,
        validate_execution=_validate_actual_readiness_execution,
        validate_result=validate_passed_readiness_result,
        executed_result_factory=_ExecutedReadinessResult,
        readiness_run_id=_readiness_run_id,
        telemetry=telemetry,
    )


def _run_publish_readiness_session(
    file_path: str | Path,
    *,
    proof_sidecar: str | Path | None = None,
    context_request: str | Path | None = None,
    context_pack: str | Path | None = None,
    context_receipt: str | Path | None = None,
    assembly_bom: str | Path | None = None,
    vault_root: str | Path | None = None,
    ai_profile: str = "simpro-web",
    phase: str = "preflight",
    workspace_root: str | Path,
    artifact_kind: str | None = None,
    telemetry: ReadinessTelemetry | None = None,
) -> ReadinessResult:
    """Create one immutable input/session boundary around the gate stack."""
    runner_kwargs = {
        "file_path": file_path,
        "proof_sidecar": proof_sidecar,
        "context_request": context_request,
        "context_pack": context_pack,
        "context_receipt": context_receipt,
        "assembly_bom": assembly_bom,
        "vault_root": vault_root,
        "ai_profile": ai_profile,
        "phase": phase,
        "workspace_root": workspace_root,
        "artifact_kind": artifact_kind,
    }
    return run_in_session(
        input_paths={
            "article": file_path,
            "validation_sidecar": proof_sidecar,
            "context_request": context_request,
            "context_pack": context_pack,
            "context_receipt": context_receipt,
            "assembly_bom": assembly_bom,
        },
        workspace_root=workspace_root,
        runner=_run_publish_readiness,
        runner_kwargs=runner_kwargs,
        blocked_result=lambda error: _input_capture_blocked_result(
            error=error,
            file_path=file_path,
            proof_sidecar=proof_sidecar,
            context_request=context_request,
            context_pack=context_pack,
            context_receipt=context_receipt,
            assembly_bom=assembly_bom,
            phase=phase,
        ),
        connector_factory=lambda: SimproVaultClient(vault_root=vault_root),
        claim_loader=lambda client: _load_session_claims(
            context_pack,
            context_receipt,
            vault_root=vault_root,
            client=client,
        ),
        telemetry=telemetry,
    )


def _load_session_claims(
    context_pack: str | Path | None,
    context_receipt: str | Path | None,
    *,
    vault_root: str | Path | None,
    client: Any,
) -> ValidatedClaimSet:
    try:
        return load_validated_claim_set(
            context_pack,
            context_receipt,
            vault_root=vault_root,
            client=client,
        )
    except (VaultClaimReceiptError, OSError, ValueError, TypeError) as error:
        return ValidatedClaimSet(blocker=str(error))


def _input_capture_blocked_result(
    *,
    error: ValueError,
    file_path: str | Path,
    proof_sidecar: str | Path | None,
    context_request: str | Path | None,
    context_pack: str | Path | None,
    context_receipt: str | Path | None,
    assembly_bom: str | Path | None,
    phase: str,
) -> ReadinessResult:
    invalid_article_utf8 = str(error).startswith(
        "readiness input article must use valid UTF-8"
    )
    gate_name = "frontmatter_metadata" if invalid_article_utf8 else "input_seal"
    gate_title = "Frontmatter Metadata" if invalid_article_utf8 else "Input Seal"
    rule_id = "frontmatter_invalid" if invalid_article_utf8 else "readiness_input_snapshot_invalid"
    gate = _gate_from_findings(
        gate_name,
        gate_title,
        [{
            "rule_id": rule_id,
            "severity": "error",
            "line": 1,
            "column": 1,
            "message": str(error),
            "suggestion": "Provide unchanged, bounded inputs inside the trusted workspace.",
        }],
    )
    return {
        "schema": READINESS_RESULT_SCHEMA,
        "phase": phase,
        "verification_scope": "source_artifact",
        "file": str(file_path),
        "proof_sidecar": str(proof_sidecar) if proof_sidecar is not None else None,
        "context_request": str(context_request) if context_request is not None else None,
        "context_pack": str(context_pack) if context_pack is not None else None,
        "context_receipt": str(context_receipt) if context_receipt is not None else None,
        "assembly_bom": str(assembly_bom) if assembly_bom is not None else None,
        "passed": False,
        "artifact_kind": None,
        "gates": [gate],
        "score": None,
        "score_threshold": 85,
        "aeo_geo": {"score": None, "threshold": 90, "passed": False},
        "priority_fixes": [{"dimension": gate_name, "issue": str(error)}],
    }


def _run_publish_readiness(
    file_path: str | Path,
    *,
    proof_sidecar: str | Path | None = None,
    context_request: str | Path | None = None,
    context_pack: str | Path | None = None,
    context_receipt: str | Path | None = None,
    assembly_bom: str | Path | None = None,
    vault_root: str | Path | None = None,
    ai_profile: str = "simpro-web",
    phase: str = "preflight",
    workspace_root: str | Path,
    artifact_kind: str | None = None,
    session: ValidationSession | None,
    input_capture_error: ValueError | None,
    telemetry: ReadinessTelemetry | None,
) -> ReadinessResult:
    """Run the full publish-readiness stack and return structured results."""
    if phase not in {"preflight", "final"}:
        raise ValueError("phase must be preflight or final")
    run_started_at = _utc_now()
    article_path = Path(file_path)
    proof_sidecar_path = str(proof_sidecar) if proof_sidecar is not None else None
    context_request_path = str(context_request) if context_request is not None else None
    context_pack_path = str(context_pack) if context_pack is not None else None
    context_receipt_path = str(context_receipt) if context_receipt is not None else None
    assembly_bom_path = str(assembly_bom) if assembly_bom is not None else None
    readiness_root = Path(workspace_root).resolve()
    try:
        article_snapshot = session.inputs.snapshot("article") if session is not None else None
        article = (
            parse_publishable_markdown(
                article_path,
                session.inputs.text("article"),
                sha256=article_snapshot.sha256,
            )
            if session is not None and article_snapshot is not None
            else read_publishable_markdown(article_path)
        )
    except FrontmatterError as exc:
        gate = _gate_from_findings(
            "frontmatter_metadata",
            "Frontmatter Metadata",
            [{
                "rule_id": "frontmatter_invalid",
                "severity": "error",
                "line": 1,
                "column": 1,
                "message": str(exc),
                "suggestion": "Repair the YAML frontmatter before publishing.",
            }],
        )
        return {
            "schema": "simpro-publish-readiness-result/v1",
            "phase": phase,
            "verification_scope": "source_artifact",
            "file": str(article_path),
            "proof_sidecar": proof_sidecar_path,
            "context_request": context_request_path,
            "context_pack": context_pack_path,
            "context_receipt": context_receipt_path,
            "assembly_bom": assembly_bom_path,
            "passed": False,
            "artifact_kind": None,
            "gates": [gate],
            "score": None,
            "score_threshold": 85,
            "aeo_geo": {"score": None, "threshold": 90, "passed": False},
            "priority_fixes": [
                {"dimension": "frontmatter_metadata", "issue": str(exc)}
            ],
        }
    article_content = article.raw
    try:
        requested_artifact_kind = artifact_kind
        detected_artifact_kind = context_binding_guard.require_artifact_kind(
            article_content,
            article_path=article_path,
        )
        if requested_artifact_kind is not None:
            if requested_artifact_kind not in {"blog", "landing_page"}:
                raise ValueError("artifact_kind must be blog or landing_page")
            if (
                requested_artifact_kind == "blog"
                and detected_artifact_kind != "blog"
            ):
                raise ValueError("artifact_kind does not match the article")
            resolved_artifact_kind = requested_artifact_kind
        else:
            resolved_artifact_kind = detected_artifact_kind
    except ValueError as error:
        message = str(error)
        normalized = message.casefold()
        if "unsupported" in normalized:
            rule_id = "artifact_kind_unsupported"
        elif "conflict" in normalized:
            rule_id = "artifact_kind_conflict"
        else:
            rule_id = "artifact_kind_missing"
        identity_gate = _gate_from_findings(
            "artifact_identity",
            "Artifact Identity",
            [{
                "rule_id": rule_id,
                "severity": "error",
                "line": 1,
                "column": 1,
                "message": message,
                "suggestion": "Declare one supported artifact_type in frontmatter.",
            }],
        )
        return {
            "schema": "simpro-publish-readiness-result/v1",
            "phase": phase,
            "file": str(article_path),
            "proof_sidecar": proof_sidecar_path,
            "context_request": context_request_path,
            "context_pack": context_pack_path,
            "context_receipt": context_receipt_path,
            "assembly_bom": assembly_bom_path,
            "verification_scope": "source_artifact",
            "passed": False,
            "artifact_kind": None,
            "gates": [identity_gate],
            "score": None,
            "score_threshold": 85,
            "aeo_geo": {"score": None, "threshold": 90, "passed": False},
            "priority_fixes": [
                {"dimension": "artifact_identity", "issue": message}
            ],
        }
    artifact_kind = resolved_artifact_kind
    score_threshold = 75 if artifact_kind == "landing_page" else 85
    gates: List[GateResult] = []
    runtime_policy = _bom_runtime_policy(
        assembly_bom_path,
        workspace_root=readiness_root,
    )
    identity_gate = _gate_from_findings(
        "artifact_identity",
        "Artifact Identity",
        _timed_call(
            telemetry,
            "gate.artifact_identity",
            blog_identity_guard.check_article,
            article_content,
            assembly_date=runtime_policy.get("assembly_date") or None,
        ),
    )
    gates.append(identity_gate)
    if not identity_gate["passed"]:
        return {
            "schema": "simpro-publish-readiness-result/v1",
            "phase": phase,
            "file": str(article_path),
            "proof_sidecar": proof_sidecar_path,
            "context_request": context_request_path,
            "context_pack": context_pack_path,
            "context_receipt": context_receipt_path,
            "assembly_bom": assembly_bom_path,
            "verification_scope": "source_artifact",
            "passed": False,
            "artifact_kind": artifact_kind,
            "gates": gates,
            "score": None,
            "score_threshold": score_threshold,
            "aeo_geo": {"score": None, "threshold": 90, "passed": False},
            "priority_fixes": [
                {"dimension": "artifact_identity", "issue": blocker}
                for blocker in identity_gate.get("blockers", [])
            ],
        }

    connector_required = context_binding_guard.requires_context(article_content) or any(
        value is not None
        for value in (context_request_path, context_pack_path, context_receipt_path)
    )
    context_client = session.connector() if session is not None and connector_required else None
    if context_client is not None and session is not None and session.telemetry is not None:
        session.telemetry.increment("connector_operations")
    context_result = _timed_call(
        telemetry,
        "gate.context_binding",
        context_binding_guard.validate_context_artifacts,
        str(article_path),
        fail_on="error",
        proof_sidecar=proof_sidecar_path,
        context_request=context_request_path,
        context_pack=context_pack_path,
        context_receipt=context_receipt_path,
        editorial_plan=runtime_policy.get("editorial_plan"),
        vault_root=vault_root,
        client=context_client,
    )
    if session is not None:
        session.set_context_result(context_result)
    context_gate = _gate_from_findings(
        "context_binding",
        "Context Binding",
        list(context_result.findings),
    )
    if session is not None:
        session.record_findings("context_binding", context_result.findings)
    gates.append(context_gate)
    if not context_gate["passed"]:
        return {
            "schema": "simpro-publish-readiness-result/v1",
            "phase": phase,
            "verification_scope": "source_artifact",
            "file": str(article_path),
            "proof_sidecar": proof_sidecar_path,
            "context_request": context_request_path,
            "context_pack": context_pack_path,
            "context_receipt": context_receipt_path,
            "assembly_bom": assembly_bom_path,
            "passed": False,
            "artifact_kind": artifact_kind,
            "gates": gates,
            "score": None,
            "score_threshold": score_threshold,
            "aeo_geo": {"score": None, "threshold": 90, "passed": False},
            "priority_fixes": [
                {
                    "dimension": "context_binding",
                    "issue": blocker,
                }
                for blocker in context_gate.get("blockers", [])
            ],
        }

    bom_required = artifact_kind == "blog"
    sealed_inputs = session.inputs if session is not None else None
    sealed_input_hashes: Dict[str, Dict[str, str]] | None = None
    if bom_required and assembly_bom_path is None:
        bom_gate = _gate_from_findings(
            "blog_assembly_bom",
            "Blog Assembly BOM",
            [blog_assembly_bom_guard.missing_bom_finding()],
        )
        gates.append(bom_gate)
        return {
            "schema": "simpro-publish-readiness-result/v1",
            "phase": phase,
            "verification_scope": "source_artifact",
            "file": str(article_path),
            "proof_sidecar": proof_sidecar_path,
            "context_request": context_request_path,
            "context_pack": context_pack_path,
            "context_receipt": context_receipt_path,
            "assembly_bom": assembly_bom_path,
            "passed": False,
            "artifact_kind": artifact_kind,
            "gates": gates,
            "score": None,
            "score_threshold": score_threshold,
            "aeo_geo": {"score": None, "threshold": 90, "passed": False},
            "priority_fixes": [
                {
                    "dimension": "blog_assembly_bom",
                    "issue": blocker,
                }
                for blocker in bom_gate.get("blockers", [])
            ],
        }

    if assembly_bom_path is not None:
        bom_gate = _gate_from_findings(
            "blog_assembly_bom",
            "Blog Assembly BOM",
            _timed_call(
                telemetry,
                "gate.blog_assembly_bom",
                blog_assembly_bom_guard.check_bom_file,
                assembly_bom_path,
                article_path=article_path,
                validation_sidecar_path=proof_sidecar_path or "",
                context_request_path=context_request_path,
                context_pack_path=context_pack_path,
                context_receipt_path=context_receipt_path,
                workspace_root=readiness_root,
                expected_lifecycle_state=(
                    "provisional" if phase == "preflight" else "final"
                ),
                require_current_schema=True,
                context_result=context_result,
                vault_root=vault_root,
            ),
        )
        gates.append(bom_gate)
        if not bom_gate["passed"]:
            return {
                "schema": "simpro-publish-readiness-result/v1",
                "phase": phase,
                "verification_scope": "source_artifact",
                "file": str(article_path),
                "proof_sidecar": proof_sidecar_path,
                "context_request": context_request_path,
                "context_pack": context_pack_path,
                "context_receipt": context_receipt_path,
                "assembly_bom": assembly_bom_path,
                "passed": False,
                "artifact_kind": artifact_kind,
                "gates": gates,
                "score": None,
                "score_threshold": score_threshold,
                "aeo_geo": {"score": None, "threshold": 90, "passed": False},
                "priority_fixes": [
                    {
                        "dimension": "blog_assembly_bom",
                        "issue": blocker,
                    }
                    for blocker in bom_gate.get("blockers", [])
                ],
            }
        try:
            if input_capture_error is not None:
                raise input_capture_error
            if sealed_inputs is None:
                raise ValueError("readiness input snapshot is unavailable")
            sealed_input_hashes = sealed_inputs.hash_inventory()
        except ValueError as error:
            seal_gate = _gate_from_findings(
                "input_seal",
                "Input Seal",
                [{
                    "rule_id": "readiness_input_snapshot_invalid",
                    "severity": "error",
                    "line": 1,
                    "column": 1,
                    "message": str(error),
                    "suggestion": "Regenerate the BOM from unchanged current artifacts.",
                }],
            )
            gates.append(seal_gate)
            return {
                "schema": "simpro-publish-readiness-result/v1",
                "phase": phase,
                "verification_scope": "source_artifact",
                "file": str(article_path),
                "proof_sidecar": proof_sidecar_path,
                "context_request": context_request_path,
                "context_pack": context_pack_path,
                "context_receipt": context_receipt_path,
                "assembly_bom": assembly_bom_path,
                "passed": False,
                "artifact_kind": artifact_kind,
                "gates": gates,
                "score": None,
                "score_threshold": score_threshold,
                "aeo_geo": {"score": None, "threshold": 90, "passed": False},
                "priority_fixes": [{
                    "dimension": "input_seal",
                    "issue": str(error),
                }],
            }

    gates.append(
        _gate_from_findings(
            "public_artifact",
            "Public Artifact",
            _timed_call(
                telemetry,
                "gate.public_artifact",
                public_artifact_guard.check_file,
                str(article_path),
                fail_on="error",
            ),
        )
    )

    ai_findings = _timed_call(
        telemetry,
        "gate.ai_copy_linter",
        ai_copy_linter.lint_file,
        str(article_path),
        profile=ai_profile,
        fail_on="error",
    )
    gates.append(
        _gate_from_findings(
            "ai_copy_linter",
            "AI Copy Linter",
            ai_findings,
        )
    )

    url_summary = _timed_call(
        telemetry,
        "gate.url_validator",
        validate_file_urls,
        article_path,
    )
    url_summary = chrome_review_evidence.apply_chrome_review_evidence_fallbacks(
        url_summary,
        proof_sidecar=proof_sidecar_path,
        workspace_root=workspace_root,
    )
    gates.append(_gate_from_url_summary(url_summary))

    gates.append(
        _gate_from_findings(
            "public_research_links",
            "Public Research Links",
            _timed_call(
                telemetry,
                "gate.public_research_links",
                public_research_link_guard.check_file,
                str(article_path),
                fail_on="error",
                proof_sidecar=proof_sidecar_path,
                url_summary=url_summary,
            ),
        )
    )

    simpro_context_required = context_binding_guard.requires_context(article_content)
    validated_claim_set = (
        session.validated_claim_set()
        if session is not None and simpro_context_required
        else None
    )
    proof_sidecar_content = _captured_proof_content(
        sealed_inputs,
        proof_sidecar_path=proof_sidecar_path,
    )
    content_gate_inputs = (
        ContentGateInputs(
            article_content=article_content,
            proof_content=proof_sidecar_content,
            article_path=article_path,
            proof_sidecar_path=proof_sidecar_path,
            context_pack_path=context_pack_path,
            context_receipt_path=context_receipt_path,
            vault_root=vault_root,
            runtime_policy=runtime_policy,
            captured=sealed_inputs,
            validated_claim_set=validated_claim_set,
        )
        if sealed_inputs is not None
        else None
    )
    prevalidated_gate_findings: Dict[
        str,
        tuple[Mapping[str, Any], ...],
    ] = {}
    for name, label, guard_module in ARTICLE_GATES:
        if name in {"faq_answer_quality", "faq_proof"} and not runtime_policy["visible_faq"]:
            continue
        if name in SIMPRO_CONTEXT_GATE_NAMES and not simpro_context_required:
            continue
        if name == "fred_authority" and not simpro_context_required:
            continue
        guard_kwargs: Dict[str, Any] = {
            "fail_on": "error",
            "proof_sidecar": proof_sidecar_path,
        }
        if name in {
            "competitive_shortlist",
            "named_feature_status",
            "customer_proof_diversity",
            "fred_authority",
            "vault_brand_language",
        }:
            guard_kwargs.update(
                {
                    "context_pack": context_pack_path,
                    "context_receipt": context_receipt_path,
                }
            )
        if name == "named_feature_status":
            guard_kwargs["vault_root"] = vault_root
        if name == "competitive_shortlist":
            guard_kwargs["vault_root"] = vault_root
        if name == "fred_authority":
            guard_kwargs["vault_root"] = vault_root
        if name in {"competitive_shortlist", "named_feature_status", "fred_authority"}:
            guard_kwargs["validated_claim_set"] = validated_claim_set
        if name == "eeat_strength":
            guard_kwargs.update(
                {
                    "editorial_plan": runtime_policy.get("editorial_plan"),
                    "customer_proof_selector_evidence": runtime_policy.get(
                        "customer_proof_selector_evidence"
                    ),
                    "fred_authority_evidence": runtime_policy.get(
                        "fred_authority_evidence"
                    ),
                }
            )
        if name == "industry_cluster_link_policy":
            guard_kwargs["editorial_plan"] = runtime_policy.get("editorial_plan")
        if name == "paa_provenance":
            guard_kwargs.update(runtime_policy["paa_kwargs"])
        if name in CONTENT_GATE_NAMES and content_gate_inputs is not None:
            findings = _timed_call(
                telemetry,
                f"gate.{name}",
                run_content_gate,
                name,
                guard_module,
                content_gate_inputs,
            )
        elif name == "editorial_plan":
            editorial_path = runtime_policy.get("editorial_plan")
            findings = (
                _timed_call(
                    telemetry,
                    f"gate.{name}",
                    guard_module.check_file,
                    editorial_path,
                    article_path=article_path,
                    serp_evidence_path=runtime_policy.get("serp_evidence"),
                    assembly_date=runtime_policy.get("assembly_date"),
                    expected_run_id=runtime_policy.get("run_id"),
                )
                if editorial_path
                else [{
                    "rule_id": "editorial_plan_missing",
                    "severity": "error",
                    "line": 1,
                    "column": 1,
                    "message": "Blog readiness requires a bound editorial plan.",
                    "suggestion": "Regenerate the provisional BOM with --editorial-plan.",
                }]
            )
        elif name == "semrush_keyword_decision":
            keyword_decision_path = runtime_policy.get("keyword_decision")
            editorial_path = runtime_policy.get("editorial_plan")
            findings = (
                _timed_call(
                    telemetry,
                    f"gate.{name}",
                    guard_module.check_file,
                    keyword_decision_path,
                    article_path=article_path,
                    editorial_plan_path=editorial_path,
                    assembly_date=runtime_policy.get("assembly_date"),
                )
                if keyword_decision_path and editorial_path
                else [{
                    "rule_id": "semrush_keyword_decision_missing",
                    "severity": "error",
                    "line": 1,
                    "column": 1,
                    "message": "Blog readiness requires a bound Semrush keyword decision.",
                    "suggestion": "Regenerate the provisional BOM with --keyword-decision.",
                }]
            )
        else:
            findings = _timed_call(
                telemetry,
                f"gate.{name}",
                guard_module.check_file,
                str(article_path),
                **guard_kwargs,
            )
        if name == "customer_proof_diversity":
            findings = [
                *findings,
                *_no_fit_customer_proof_findings(
                    article_content,
                    runtime_policy=runtime_policy,
                ),
            ]
        if session is not None:
            session.record_findings(name, findings)
            cached_findings = session.findings(name) or []
        else:
            cached_findings = [dict(finding) for finding in findings]
        prevalidated_gate_findings[name] = tuple(cached_findings)
        gate = _gate_from_findings(name, label, findings)
        gates.append(gate)
        if name == "semrush_keyword_decision" and not gate["passed"]:
            return _blocked_readiness_result(
                phase=phase,
                article_path=article_path,
                proof_sidecar_path=proof_sidecar_path,
                context_request_path=context_request_path,
                context_pack_path=context_pack_path,
                context_receipt_path=context_receipt_path,
                assembly_bom_path=assembly_bom_path,
                artifact_kind=artifact_kind,
                gates=gates,
                score_threshold=score_threshold,
                gate=gate,
            )

    readiness_gate_context = _issue_readiness_gate_context(
        prevalidated_gate_findings,
        article_content=article_content,
        proof_sidecar_content=proof_sidecar_content,
        input_hashes=sealed_input_hashes or {},
        workspace_root=readiness_root,
    )

    scorer_result = _timed_call(
        telemetry,
        "gate.content_scorer",
        _score_content,
        article_path,
        proof_sidecar_path,
        artifact_kind=artifact_kind or "blog",
        assembly_bom=assembly_bom_path,
        runtime_policy=runtime_policy,
        workspace_root=readiness_root,
        readiness_gate_context=readiness_gate_context,
    )
    gates.append(_gate_from_score(scorer_result))

    current_input_hashes: Dict[str, Dict[str, str]]
    try:
        if input_capture_error is not None:
            raise input_capture_error
        if sealed_inputs is None:
            raise ValueError("readiness input snapshot is unavailable")
        sealed_inputs.reseal()
        current_input_hashes = sealed_inputs.hash_inventory()
        seal_findings = []
        if artifact_kind == "blog" and current_input_hashes != sealed_input_hashes:
            seal_findings = [{
                "rule_id": "readiness_inputs_changed_during_run",
                "severity": "error",
                "line": 1,
                "column": 1,
                "message": "One or more bound artifacts changed during readiness.",
                "suggestion": (
                    "Resume at the mutation receipt, then rerun scrub, Context Binding, "
                    "BOM build, and readiness."
                ),
            }]
    except ValueError as error:
        current_input_hashes = sealed_input_hashes or {}
        seal_findings = [{
            "rule_id": "readiness_inputs_changed_during_run",
            "severity": "error",
            "line": 1,
            "column": 1,
            "message": str(error),
            "suggestion": (
                "Resume at the mutation receipt, then rerun scrub, Context Binding, "
                "BOM build, and readiness."
            ),
        }]

    if artifact_kind == "blog":
        gates.append(
            _gate_from_findings(
                "input_seal",
                "Input Seal",
                seal_findings,
            )
        )
        try:
            gates = [
                dict(row)
                for row in order_blog_gate_results(
                    gates,
                    visible_faq=bool(runtime_policy["visible_faq"]),
                    connector_required=simpro_context_required,
                )
            ]
        except ValueError:
            gates.append(
                _gate_from_findings(
                    "readiness_contract",
                    "Readiness Contract",
                    [{
                        "rule_id": "readiness_gate_inventory_invalid",
                        "severity": "error",
                        "line": 1,
                        "column": 1,
                        "message": (
                            "Readiness gate order drifted from the closed blog contract."
                        ),
                        "suggestion": (
                            "Restore the expected conditional gate inventory before sealing."
                        ),
                    }],
                )
            )

    scorecard = _scorecard_from_scorer_result(
        scorer_result,
        artifact_kind=artifact_kind,
    )
    passed = all(gate["passed"] for gate in gates) and bool(scorecard["passed"])
    result = {
        "schema": "simpro-publish-readiness-result/v1",
        "tool": {"name": "publish_readiness", "version": "1.0.0"},
        "phase": phase,
        "verification_scope": "source_artifact",
        "file": str(article_path),
        "proof_sidecar": proof_sidecar_path,
        "context_request": context_request_path,
        "context_pack": context_pack_path,
        "context_receipt": context_receipt_path,
        "assembly_bom": assembly_bom_path,
        "passed": passed,
        "artifact_kind": artifact_kind,
        "gates": gates,
        "score": _content_score(scorer_result),
        "score_threshold": scorer_result.get("threshold", 85),
        "aeo_geo": scorer_result.get("aeo_geo", {}),
        "scorecard": scorecard,
        "priority_fixes": scorer_result.get("priority_fixes", []),
        "gate_inventory": [gate["name"] for gate in gates],
        "input_hashes": current_input_hashes,
        "input_seal": {
            "status": "verified" if not seal_findings else "failed",
        },
        "run_id": _readiness_run_id(assembly_bom_path, article.sha256),
        "started_at": run_started_at,
        "completed_at": _utc_now(),
    }
    if phase == "final" and assembly_bom_path:
        result["final_bom_sha256"] = file_sha256(assembly_bom_path)
    return result


def readiness_stage_receipt_path(output_path: str | Path) -> Path:
    """Return the deterministic detached receipt path for a readiness output."""
    output = Path(output_path)
    return output.with_name(f"{output.stem}-stage-receipt.json")


def write_readiness_result(
    output_path: str | Path,
    result: Mapping[str, Any],
    *,
    receipt_path: str | Path | None = None,
    workspace_root: str | Path | None = None,
) -> Path | None:
    """Write the result and, when passed, its non-circular stage receipt."""
    root = _result_workspace_root(result, workspace_root)
    output = _resolve_workspace_input(
        output_path,
        workspace_root=root,
        field="readiness output",
    )
    destination = (
        _resolve_workspace_input(
            receipt_path,
            workspace_root=root,
            field="readiness receipt",
        )
        if receipt_path is not None
        else readiness_stage_receipt_path(output)
    )
    _reject_output_input_collision(output, result, workspace_root=root)
    if result.get("passed") is not True:
        atomic_write_json(output, result)
        return None
    validate_passed_readiness_result(result, workspace_root=root)
    input_rows = result.get("input_hashes")
    input_hashes = {
        str(label): str(row.get("sha256"))
        for label, row in input_rows.items()
        if isinstance(row, Mapping) and isinstance(row.get("sha256"), str)
    }
    article_hash = input_hashes.get("article")
    if not article_hash:
        raise ValueError("passed readiness result requires the article input hash")
    bom_path = result.get("assembly_bom")
    previous_hash = ""
    optimized = False
    prior_receipts: list[Mapping[str, Any]] = []
    bom_assembly_date: str | None = None
    expected_chain_run_id: str | None = None
    if isinstance(bom_path, str) and bom_path:
        try:
            bom = load_json_object_snapshot(bom_path, field="assembly BOM").payload
        except ValueError as error:
            raise ValueError(f"readiness BOM is unavailable: {error}") from error
        workflow = bom.get("workflow") if isinstance(bom, Mapping) else None
        bom_assembly_date = (
            str(bom.get("assembly_date"))
            if isinstance(bom, Mapping) and isinstance(bom.get("assembly_date"), str)
            else None
        )
        if bom_assembly_date is None:
            raise ValueError("readiness BOM requires a canonical assembly_date")
        expected_chain_run_id = canonical_article_run_id(
            str(result.get("file") or ""),
            workspace_root=root,
            assembly_date=bom_assembly_date,
        )
        receipts = workflow.get("stage_receipts") if isinstance(workflow, Mapping) else None
        if isinstance(receipts, list) and receipts:
            if any(not isinstance(row, Mapping) for row in receipts):
                raise ValueError("readiness BOM contains an invalid stage receipt chain")
            prior_receipts = list(receipts)
            receipt_run_ids = {
                str(row.get("run_id") or "").strip()
                for row in prior_receipts
                if isinstance(row, Mapping)
            }
            receipt_run_ids.discard("")
            if len(receipt_run_ids) == 1:
                expected_chain_run_id = next(iter(receipt_run_ids))
            last = receipts[-1]
            if isinstance(last, Mapping):
                previous_hash = str(last.get("receipt_hash") or "")
            optimized = any(
                isinstance(row, Mapping)
                and row.get("stage")
                in {
                    "optimization",
                    "post_optimization_scrub",
                    "post_optimization_context_binding",
                }
                for row in receipts
            )
    if result.get("phase") == "final":
        stage = "final_readiness_attestation"
    elif optimized:
        stage = "final_preflight_readiness"
    else:
        stage = "preflight_readiness"
    if _same_path(destination, output):
        raise ValueError("readiness receipt cannot overwrite readiness output")
    _reject_output_input_collision(
        destination,
        result,
        output_label="readiness receipt",
        workspace_root=root,
    )
    output_digest = hashlib.sha256(canonical_json_bytes(result)).hexdigest()
    receipt = build_stage_receipt(
        run_id=str(result.get("run_id") or ""),
        stage=stage,
        tool_name="publish_readiness",
        tool_version="1.0.0",
        started_at=str(result.get("started_at") or ""),
        completed_at=str(result.get("completed_at") or ""),
        mutation=False,
        input_artifact_hashes=input_hashes,
        output_artifact_hashes={
            "article": article_hash,
            "readiness_output": output_digest,
        },
        evidence_hashes={
            label: digest
            for label, digest in input_hashes.items()
            if label not in {"article", "assembly_bom"}
        },
        previous_receipt_hash=previous_hash,
    )
    if prior_receipts:
        if expected_chain_run_id is None or bom_assembly_date is None:
            raise ValueError(
                "readiness stage receipt requires canonical workflow identity"
            )
        chain_findings = check_receipt_chain(
            [*prior_receipts, receipt],
            expected_run_id=expected_chain_run_id,
            assembly_date=bom_assembly_date,
        )
        if chain_findings:
            rules = ", ".join(
                sorted({str(finding["rule_id"]) for finding in chain_findings})
            )
            raise ValueError(f"readiness stage receipt chain is invalid: {rules}")
    _validate_actual_readiness_execution(result, workspace_root=root)
    return persist_result_pair(
        output,
        result,
        destination,
        receipt,
        receipt_writer=write_stage_receipt,
    )


def _validate_actual_readiness_execution(
    result: Mapping[str, Any],
    *,
    workspace_root: Path,
) -> None:
    if not isinstance(result, _ExecutedReadinessResult):
        raise ValueError(
            "passed readiness output requires an actual publish-readiness execution"
        )
    if os.path.normcase(str(result._workspace_root)) != os.path.normcase(
        str(workspace_root.resolve())
    ):
        raise ValueError("readiness execution workspace_root changed before persistence")
    expected = _sign_readiness_execution(result)
    if not hmac.compare_digest(result._execution_signature, expected):
        raise ValueError(
            "passed readiness output changed after its actual publish-readiness execution"
        )


def validate_passed_readiness_result(
    result: Mapping[str, Any],
    *,
    workspace_root: str | Path | None = None,
) -> None:
    """Reject caller-invented pass payloads that do not match the closed contract."""
    phase = result.get("phase")
    expected_fields = set(PASSED_RESULT_FIELDS)
    if phase == "final":
        expected_fields.add("final_bom_sha256")
    if set(result) != expected_fields:
        raise ValueError("passed readiness result must use the exact result field set")
    if result.get("schema") != READINESS_RESULT_SCHEMA:
        raise ValueError(f"passed readiness result must use {READINESS_RESULT_SCHEMA}")
    if result.get("tool") != READINESS_TOOL:
        raise ValueError("passed readiness result uses the wrong readiness tool identity")
    if phase not in {"preflight", "final"}:
        raise ValueError("passed readiness result phase must be preflight or final")
    if result.get("verification_scope") != "source_artifact":
        raise ValueError("passed readiness result must declare source_artifact verification")
    if result.get("passed") is not True:
        raise ValueError("passed readiness result must declare passed true")
    root = _result_workspace_root(result, workspace_root)

    file_value = result.get("file")
    if not isinstance(file_value, str):
        raise ValueError("passed readiness result file must identify the current article")
    file_path = _resolve_workspace_input(
        file_value,
        workspace_root=root,
        field="readiness article",
    )
    if not file_path.is_file():
        raise ValueError("passed readiness result file must identify the current article")
    try:
        article = read_publishable_markdown(file_path)
        actual_kind = context_binding_guard.require_artifact_kind(
            article.raw,
            article_path=file_path,
        )
    except (FrontmatterError, ValueError) as error:
        raise ValueError(f"passed readiness result article identity is invalid: {error}") from error
    artifact_kind = result.get("artifact_kind")
    if artifact_kind != actual_kind:
        raise ValueError("passed readiness artifact_kind does not match the article")

    gates = result.get("gates")
    inventory = result.get("gate_inventory")
    if not isinstance(gates, list) or not gates:
        raise ValueError("passed readiness result is missing the expected gate inventory")
    if not isinstance(inventory, list) or not inventory:
        raise ValueError("passed readiness result is missing the expected gate inventory")
    names: list[str] = []
    for index, gate in enumerate(gates):
        if not isinstance(gate, Mapping) or set(gate) != GATE_RESULT_FIELDS:
            raise ValueError(f"passed readiness gate {index} has an invalid shape")
        name = gate.get("name")
        label = gate.get("label")
        if not isinstance(name, str) or not name or not isinstance(label, str) or not label:
            raise ValueError(f"passed readiness gate {index} requires a name and label")
        if (
            gate.get("passed") is not True
            or gate.get("errors") != 0
            or not isinstance(gate.get("warnings"), int)
            or isinstance(gate.get("warnings"), bool)
            or gate.get("warnings", -1) < 0
            or not isinstance(gate.get("findings"), list)
            or gate.get("blockers") != []
        ):
            raise ValueError(f"passed readiness gate {name} is not a completed pass")
        names.append(name)
    if len(names) != len(set(names)) or inventory != names:
        raise ValueError("passed readiness result has an invalid gate inventory")

    bom_path = result.get("assembly_bom")
    if artifact_kind == "blog":
        if not isinstance(bom_path, str):
            raise ValueError("passed blog readiness requires the bound assembly BOM")
        resolved_bom = _resolve_workspace_input(
            bom_path,
            workspace_root=root,
            field="readiness assembly_bom",
        )
        if not resolved_bom.is_file():
            raise ValueError("passed blog readiness requires the bound assembly BOM")
        try:
            bom = load_json_object_snapshot(
                resolved_bom, field="assembly BOM"
            ).payload
        except ValueError as error:
            raise ValueError(f"passed readiness BOM is unavailable: {error}") from error
        if not isinstance(bom, Mapping):
            raise ValueError("passed readiness BOM must be an object")
        expected_lifecycle = "provisional" if phase == "preflight" else "final"
        if bom.get("lifecycle_state") != expected_lifecycle:
            raise ValueError(
                f"{phase} readiness requires a {expected_lifecycle} assembly BOM"
            )
        schema_policy = bom.get("schema_policy")
        connector_binding = bom.get("connector_binding")
        visible_faq = bool(
            isinstance(schema_policy, Mapping)
            and schema_policy.get("visible_faq") is True
        )
        connector_required = bool(
            context_binding_guard.requires_context(article.raw)
            or (
                isinstance(connector_binding, Mapping)
                and connector_binding.get("status") == "required"
            )
        )
        expected_inventory = expected_blog_gate_inventory(
            visible_faq=visible_faq,
            connector_required=connector_required,
        )
        if names != expected_inventory:
            raise ValueError("passed readiness result does not contain the expected gate inventory")

    score_value = result.get("score")
    score_threshold = result.get("score_threshold")
    expected_threshold = 75 if artifact_kind == "landing_page" else 85
    if (
        not _is_number(score_value)
        or score_threshold != expected_threshold
        or float(score_value) < expected_threshold
    ):
        raise ValueError("passed readiness result does not meet its content score threshold")
    aeo_geo = result.get("aeo_geo")
    if not isinstance(aeo_geo, Mapping):
        raise ValueError("passed readiness result requires an AEO/GEO result")
    if artifact_kind == "blog":
        if (
            not _is_number(aeo_geo.get("score"))
            or aeo_geo.get("threshold") != 90
            or aeo_geo.get("passed") is not True
            or float(aeo_geo["score"]) < 90
        ):
            raise ValueError("passed blog readiness does not meet the AEO/GEO threshold")
    elif aeo_geo.get("passed") is not True:
        raise ValueError("passed readiness result contains a failed AEO/GEO result")
    _validate_passed_scorecard(result, artifact_kind=artifact_kind)
    if not isinstance(result.get("priority_fixes"), list):
        raise ValueError("passed readiness priority_fixes must be a list")
    if not isinstance(result.get("run_id"), str) or not str(result["run_id"]).strip():
        raise ValueError("passed readiness result requires a run_id")

    _verify_result_inputs_unchanged(result, workspace_root=root)
    _verify_result_path_bindings(result, workspace_root=root)
    expected_inputs = _complete_readiness_input_hashes(
        article=str(result["file"]),
        validation_sidecar=(
            result.get("proof_sidecar")
            if isinstance(result.get("proof_sidecar"), str)
            else None
        ),
        context_request=(
            result.get("context_request")
            if isinstance(result.get("context_request"), str)
            else None
        ),
        context_pack=(
            result.get("context_pack")
            if isinstance(result.get("context_pack"), str)
            else None
        ),
        context_receipt=(
            result.get("context_receipt")
            if isinstance(result.get("context_receipt"), str)
            else None
        ),
        assembly_bom=(
            result.get("assembly_bom")
            if isinstance(result.get("assembly_bom"), str)
            else None
        ),
        workspace_root=root,
    )
    if result.get("input_hashes") != expected_inputs:
        raise ValueError(
            "passed readiness result must bind the complete exact readiness input inventory"
        )


def _validate_passed_scorecard(
    result: Mapping[str, Any],
    *,
    artifact_kind: str,
) -> None:
    scorecard = result.get("scorecard")
    if not isinstance(scorecard, Mapping):
        raise ValueError("passed readiness result requires a scorecard")
    expected_fields = {"passed", "content_quality", "seo_quality", "aeo_geo"}
    if set(scorecard) != expected_fields:
        raise ValueError("passed readiness scorecard has an invalid shape")
    if scorecard.get("passed") is not True:
        raise ValueError("passed readiness scorecard is not a completed pass")

    expected_content_threshold = 75 if artifact_kind == "landing_page" else 85
    content_gate = _validate_scorecard_gate(
        scorecard,
        "content_quality",
        "content quality",
        expected_threshold=expected_content_threshold,
        require_numeric_score=True,
    )
    if not _same_number(content_gate.get("score"), result.get("score")):
        raise ValueError("passed readiness scorecard content score does not match the result")
    if content_gate.get("threshold") != result.get("score_threshold"):
        raise ValueError("passed readiness scorecard content threshold does not match the result")

    seo_gate = _scorecard_gate(scorecard, "seo_quality")
    seo_not_applicable = seo_gate.get("not_applicable") is True
    if seo_not_applicable:
        if seo_gate.get("passed") is not True:
            raise ValueError("passed readiness scorecard SEO gate is not a pass")
    else:
        _validate_scorecard_gate(
            scorecard,
            "seo_quality",
            "SEO",
            expected_threshold=SEO_PUBLISHING_THRESHOLD,
            require_numeric_score=True,
        )
        has_target_fields = any(
            field in seo_gate
            for field in ("target", "target_met", "target_status")
        )
        if has_target_fields:
            if seo_gate.get("target") != SEO_TARGET_SCORE:
                raise ValueError("passed readiness scorecard SEO gate has an invalid target")
            target_met = seo_gate.get("target_met")
            target_status = seo_gate.get("target_status")
            if not isinstance(target_met, bool):
                raise ValueError("passed readiness scorecard SEO gate has an invalid target status")
            if target_status not in {"met", "below_target"}:
                raise ValueError("passed readiness scorecard SEO gate has an invalid target status")
    critical_issue_count = seo_gate.get("critical_issue_count")
    if (
        not isinstance(critical_issue_count, int)
        or isinstance(critical_issue_count, bool)
        or critical_issue_count != 0
    ):
        raise ValueError("passed readiness scorecard SEO gate has critical issues")
    critical_issues = seo_gate.get("critical_issues", [])
    if not isinstance(critical_issues, list) or critical_issues:
        raise ValueError("passed readiness scorecard SEO gate has critical issues")

    aeo_gate = _scorecard_gate(scorecard, "aeo_geo")
    aeo_not_applicable = aeo_gate.get("not_applicable") is True
    if aeo_not_applicable and artifact_kind != "blog":
        if aeo_gate.get("passed") is not True:
            raise ValueError("passed readiness scorecard AEO/GEO gate is not a pass")
    else:
        _validate_scorecard_gate(
            scorecard,
            "aeo_geo",
            "AEO/GEO",
            expected_threshold=90 if artifact_kind == "blog" else None,
            require_numeric_score=True,
        )
        aeo_geo = result.get("aeo_geo")
        if not isinstance(aeo_geo, Mapping):
            raise ValueError("passed readiness result requires an AEO/GEO result")
        if not _same_number(aeo_gate.get("score"), aeo_geo.get("score")):
            raise ValueError("passed readiness scorecard AEO/GEO score does not match the result")
        if aeo_gate.get("threshold") != aeo_geo.get("threshold"):
            raise ValueError("passed readiness scorecard AEO/GEO threshold does not match the result")
        if aeo_gate.get("passed") != aeo_geo.get("passed"):
            raise ValueError("passed readiness scorecard AEO/GEO status does not match the result")


def _validate_scorecard_gate(
    scorecard: Mapping[str, Any],
    gate_name: str,
    label: str,
    *,
    expected_threshold: int | None,
    require_numeric_score: bool,
) -> Mapping[str, Any]:
    gate = scorecard.get(gate_name)
    if not isinstance(gate, Mapping):
        raise ValueError(f"passed readiness scorecard is missing the {label} gate")
    score = gate.get("score")
    threshold = gate.get("threshold")
    if expected_threshold is not None and threshold != expected_threshold:
        raise ValueError(f"passed readiness scorecard {label} threshold is invalid")
    if require_numeric_score and (not _is_number(score) or not _is_number(threshold)):
        raise ValueError(f"passed readiness scorecard {label} gate is missing a numeric score")
    if gate.get("passed") is not True:
        raise ValueError(f"passed readiness scorecard {label} gate is not a pass")
    if _is_number(score) and _is_number(threshold) and float(score) < float(threshold):
        raise ValueError(f"passed readiness scorecard {label} gate is below threshold")
    return gate


def _scorecard_gate(scorecard: Any, gate_name: str) -> Mapping[str, Any]:
    if not isinstance(scorecard, Mapping):
        return {}
    gate = scorecard.get(gate_name)
    if not isinstance(gate, Mapping):
        return {}
    return gate


def _same_number(left: Any, right: Any) -> bool:
    return _is_number(left) and _is_number(right) and float(left) == float(right)

def _verify_result_path_bindings(
    result: Mapping[str, Any],
    *,
    workspace_root: str | Path,
) -> None:
    rows = result.get("input_hashes")
    if not isinstance(rows, Mapping):
        raise ValueError("passed readiness result requires input_hashes")
    root = Path(workspace_root).resolve()
    bindings = {
        "article": "file",
        "validation_sidecar": "proof_sidecar",
        "context_request": "context_request",
        "context_pack": "context_pack",
        "context_receipt": "context_receipt",
        "assembly_bom": "assembly_bom",
    }
    for label, field in bindings.items():
        declared = result.get(field)
        row = rows.get(label)
        if declared is None:
            if row is not None:
                raise ValueError(f"readiness input {label} is not bound to {field}")
            continue
        if not isinstance(declared, str) or not isinstance(row, Mapping):
            raise ValueError(f"readiness input {label} is missing its path binding")
        stored = row.get("path")
        if not isinstance(stored, str):
            raise ValueError(f"readiness input {label} has an invalid path binding")
        try:
            bound_path = _resolve_workspace_input(
                declared,
                workspace_root=root,
                field=field,
            )
            stored_path = resolve_artifact(stored, workspace_root=root)
        except ValueError as error:
            raise ValueError(f"readiness input {label} has an invalid path binding") from error
        if not _same_path(bound_path, stored_path):
            raise ValueError(f"readiness input {label} does not match its declared path")


def _is_number(value: Any) -> bool:
    return is_json_number(value)


def _same_path(left: str | Path, right: str | Path) -> bool:
    return os.path.normcase(str(Path(left).resolve())) == os.path.normcase(
        str(Path(right).resolve())
    )


def _readiness_run_id(assembly_bom: str | None, article_hash: str) -> str:
    if assembly_bom:
        try:
            bom = load_json_object_snapshot(
                assembly_bom, field="assembly BOM"
            ).payload
        except ValueError:
            bom = None
        workflow = bom.get("workflow") if isinstance(bom, Mapping) else None
        receipts = workflow.get("stage_receipts") if isinstance(workflow, Mapping) else None
        if isinstance(receipts, list) and receipts and isinstance(receipts[0], Mapping):
            run_id = receipts[0].get("run_id")
            if isinstance(run_id, str) and run_id.strip():
                return run_id.strip()
    return f"readiness-{article_hash[:16]}"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _resolve_workspace_input(
    value: str | Path,
    *,
    workspace_root: str | Path,
    field: str,
) -> Path:
    """Resolve one caller path without allowing a BOM to widen the trust root."""
    root = Path(workspace_root).resolve()
    raw = Path(value)
    candidate = raw.resolve() if raw.is_absolute() else (root / raw).resolve()
    try:
        common = Path(os.path.commonpath((str(root), str(candidate))))
    except ValueError as error:
        raise ValueError(f"{field} must remain inside workspace_root") from error
    if os.path.normcase(str(common)) != os.path.normcase(str(root)):
        raise ValueError(f"{field} must remain inside workspace_root")
    return candidate


def _resolve_optional_workspace_input(
    value: str | Path | None,
    *,
    workspace_root: str | Path,
    field: str,
) -> Path | None:
    if value is None:
        return None
    return _resolve_workspace_input(value, workspace_root=workspace_root, field=field)


def _result_workspace_root(
    result: Mapping[str, Any],
    workspace_root: str | Path | None,
) -> Path:
    if workspace_root is not None:
        root = Path(workspace_root).resolve()
    elif isinstance(result, _ExecutedReadinessResult):
        root = result._workspace_root
    else:
        root = Path.cwd().resolve()
    if (
        isinstance(result, _ExecutedReadinessResult)
        and os.path.normcase(str(root))
        != os.path.normcase(str(result._workspace_root))
    ):
        raise ValueError("readiness result workspace_root does not match its execution")
    return root


def _verify_result_inputs_unchanged(
    result: Mapping[str, Any],
    *,
    workspace_root: str | Path,
) -> None:
    """Reject persistence of a pass after any attested input changed."""
    if result.get("input_seal") != {"status": "verified"}:
        raise ValueError("passed readiness result requires a verified input seal")
    rows = result.get("input_hashes")
    if not isinstance(rows, Mapping) or not rows:
        raise ValueError("passed readiness result requires input_hashes")
    root = Path(workspace_root).resolve()
    for label, row in rows.items():
        if not isinstance(row, Mapping) or set(row) != {"path", "sha256"}:
            raise ValueError(f"readiness input {label} must contain only path and sha256")
        digest = validate_sha256(row.get("sha256"), field=f"input_hashes.{label}.sha256")
        stored = row.get("path")
        if not isinstance(stored, str) or not stored:
            raise ValueError(f"input_hashes.{label}.path must be a non-empty string")
        candidate = resolve_artifact(stored, workspace_root=root)
        if not candidate.is_file() or file_sha256(candidate) != digest:
            raise ValueError(f"readiness input {label} changed after gate execution")
    if result.get("phase") == "final":
        assembly_row = rows.get("assembly_bom")
        if (
            not isinstance(assembly_row, Mapping)
            or result.get("final_bom_sha256") != assembly_row.get("sha256")
        ):
            raise ValueError("final readiness must bind the exact final BOM hash")


def _reject_output_input_collision(
    output_path: str | Path,
    result: Mapping[str, Any],
    *,
    output_label: str = "readiness output",
    workspace_root: str | Path,
) -> None:
    root = Path(workspace_root).resolve()
    destination = os.path.normcase(str(Path(output_path).resolve()))
    direct_inputs = {
        "article": result.get("file"),
        "validation_sidecar": result.get("proof_sidecar"),
        "context_request": result.get("context_request"),
        "context_pack": result.get("context_pack"),
        "context_receipt": result.get("context_receipt"),
        "assembly_bom": result.get("assembly_bom"),
    }
    for label, value in direct_inputs.items():
        if isinstance(value, str) and value:
            resolved = _resolve_workspace_input(
                value,
                workspace_root=root,
                field=label,
            )
            if destination == os.path.normcase(str(resolved)):
                raise ValueError(f"{output_label} cannot overwrite input {label}")
    bom_value = result.get("assembly_bom")
    if isinstance(bom_value, str) and bom_value:
        try:
            bom = load_json_object_snapshot(
                bom_value, field="assembly BOM"
            ).payload
            artifacts = bom.get("artifacts") if isinstance(bom, Mapping) else None
            if not isinstance(artifacts, Mapping):
                raise ValueError("assembly BOM artifacts must be an object")
            nested_rows = artifact_inventory_snapshots(artifacts)
            nested_rows.update(_historical_preflight_input_snapshots(bom))
            for label, row in nested_rows.items():
                resolved = resolve_artifact(row["path"], workspace_root=root)
                if destination == os.path.normcase(str(resolved)):
                    raise ValueError(
                        f"{output_label} cannot overwrite input {label}"
                    )
        except ValueError as error:
            raise ValueError(
                f"{output_label} cannot safely inspect its bound assembly BOM: {error}"
            ) from error
    rows = result.get("input_hashes")
    if not isinstance(rows, Mapping):
        return
    for label, row in rows.items():
        if not isinstance(row, Mapping) or not isinstance(row.get("path"), str):
            continue
        stored = str(row["path"])
        try:
            resolved = resolve_artifact(stored, workspace_root=root)
        except ValueError:
            continue
        if destination == os.path.normcase(str(resolved)):
            raise ValueError(f"{output_label} cannot overwrite input {label}")


def _readiness_input_hashes(
    inputs: Dict[str, str | Path | None],
    *,
    workspace_root: str | Path,
) -> Dict[str, Dict[str, str]]:
    snapshots: Dict[str, Dict[str, str]] = {}
    for label, value in inputs.items():
        if value is None:
            continue
        path = _resolve_workspace_input(
            value,
            workspace_root=workspace_root,
            field=f"readiness input {label}",
        )
        if path.is_file():
            snapshots[label] = canonical_artifact(
                path,
                workspace_root=workspace_root,
            )
    return snapshots


def _complete_readiness_input_hashes(
    *,
    article: str | Path,
    validation_sidecar: str | Path | None,
    context_request: str | Path | None,
    context_pack: str | Path | None,
    context_receipt: str | Path | None,
    assembly_bom: str | Path | None,
    workspace_root: str | Path,
) -> Dict[str, Dict[str, str]]:
    return _capture_readiness_inputs(
        article=article,
        validation_sidecar=validation_sidecar,
        context_request=context_request,
        context_pack=context_pack,
        context_receipt=context_receipt,
        assembly_bom=assembly_bom,
        workspace_root=workspace_root,
    ).hash_inventory()


def _capture_readiness_inputs(
    *,
    article: str | Path,
    validation_sidecar: str | Path | None,
    context_request: str | Path | None,
    context_pack: str | Path | None,
    context_receipt: str | Path | None,
    assembly_bom: str | Path | None,
    workspace_root: str | Path,
    telemetry: ReadinessTelemetry | None = None,
) -> ReadinessInputs:
    return ReadinessInputs.capture(
        {
            "article": article,
            "validation_sidecar": validation_sidecar,
            "context_request": context_request,
            "context_pack": context_pack,
            "context_receipt": context_receipt,
            "assembly_bom": assembly_bom,
        },
        workspace_root=workspace_root,
        telemetry=telemetry,
    )


def _captured_proof_content(
    inputs: ReadinessInputs | None,
    *,
    proof_sidecar_path: str | None,
) -> str | None:
    if proof_sidecar_path is None:
        return None
    if inputs is not None and inputs.optional_snapshot("validation_sidecar") is not None:
        return inputs.text("validation_sidecar")
    return Path(proof_sidecar_path).read_text(encoding="utf-8")


def _optional_result_path(result: Mapping[str, Any], key: str) -> str | None:
    value = result.get(key)
    return value if isinstance(value, str) else None


def _historical_preflight_input_snapshots(
    bom: Mapping[str, Any],
) -> Dict[str, Dict[str, str]]:
    """Return the immutable inputs sealed by a final BOM's preflight run."""
    record = bom.get("preflight")
    if record is None:
        return {}
    if not isinstance(record, Mapping):
        raise ValueError("assembly BOM preflight record must be an object")
    inputs = record.get("input_hashes")
    if not isinstance(inputs, Mapping) or not inputs:
        raise ValueError("assembly BOM preflight input_hashes must be an object")
    snapshots: Dict[str, Dict[str, str]] = {}
    for label, row in sorted(inputs.items(), key=lambda item: str(item[0])):
        if not isinstance(label, str) or not label:
            raise ValueError("assembly BOM preflight input labels must be non-empty strings")
        if not isinstance(row, Mapping) or set(row) != {"path", "sha256"}:
            raise ValueError(
                f"assembly BOM preflight input {label} must contain path and sha256"
            )
        path = row.get("path")
        if not isinstance(path, str) or not path:
            raise ValueError(
                f"assembly BOM preflight input {label}.path must be a non-empty string"
            )
        digest = validate_sha256(
            row.get("sha256"),
            field=f"preflight.input_hashes.{label}.sha256",
        )
        snapshots[f"historical_preflight.{label}"] = {
            "path": path,
            "sha256": digest,
        }
    return snapshots


def _bom_runtime_policy(
    assembly_bom: str | None,
    *,
    workspace_root: str | Path,
) -> Dict[str, Any]:
    default = {
        "visible_faq": True,
        "editorial_plan": None,
        "keyword_decision": None,
        "serp_evidence": None,
        "assembly_date": None,
        "run_id": None,
        "assembly_bom": None,
        "customer_proof_selector_evidence": None,
        "fred_authority_evidence": None,
        "faq_policy_status": "",
        "scoring_metadata": {},
        "paa_kwargs": {},
    }
    if not assembly_bom:
        return default
    try:
        source = _resolve_workspace_input(
            assembly_bom,
            workspace_root=workspace_root,
            field="assembly_bom",
        )
    except ValueError:
        return default
    try:
        bom = load_json_object_snapshot(source, field="assembly BOM").payload
    except ValueError:
        return default
    if not isinstance(bom, Mapping):
        return default
    artifacts = bom.get("artifacts")
    paa_policy = bom.get("paa_policy")
    faq_policy = bom.get("faq_policy")
    schema_policy = bom.get("schema_policy")
    if (
        not isinstance(artifacts, Mapping)
        or not isinstance(paa_policy, Mapping)
        or not isinstance(faq_policy, Mapping)
    ):
        return default
    root = Path(workspace_root).resolve()

    def artifact_path(label: str) -> str | None:
        row = artifacts.get(label)
        if not isinstance(row, Mapping) or not isinstance(row.get("path"), str):
            return None
        try:
            return str(resolve_artifact(row["path"], workspace_root=root))
        except ValueError:
            return None

    source_kind = paa_policy.get("source_kind")
    if source_kind == "brief_paa":
        paa_artifact = artifact_path("content_brief")
    elif source_kind == "user_csv":
        paa_artifact = artifact_path("user_paa_csv")
    else:
        paa_artifact = artifact_path("paa_artifact")
    editorial_plan_path = artifact_path("editorial_plan")
    scoring_metadata: Dict[str, Any] = {}
    if editorial_plan_path:
        try:
            plan = load_json_object_snapshot(
                editorial_plan_path, field="editorial plan"
            ).payload
        except ValueError:
            plan = None
        meta = plan.get("meta") if isinstance(plan, Mapping) else None
        if isinstance(meta, Mapping):
            for key in (
                "meta_title",
                "meta_description",
                "primary_keyword",
                "secondary_keywords",
            ):
                scoring_metadata[key] = meta.get(key)
        if isinstance(plan, Mapping):
            scoring_metadata["seo_guidelines"] = (
                editorial_plan_guard.internal_link_guidelines_from_plan(plan)
            )
    return {
        "visible_faq": bool(
            isinstance(schema_policy, Mapping) and schema_policy.get("visible_faq") is True
        ),
        "editorial_plan": editorial_plan_path,
        "keyword_decision": artifact_path("keyword_decision"),
        "serp_evidence": artifact_path("serp_evidence"),
        "customer_proof_selector_evidence": artifact_path(
            "customer_proof_selector_evidence"
        ),
        "fred_authority_evidence": artifact_path("fred_authority_evidence"),
        "assembly_date": str(bom.get("assembly_date") or ""),
        "run_id": _canonical_bom_run_id(bom),
        "assembly_bom": bom,
        "faq_policy_status": str(faq_policy.get("status") or ""),
        "scoring_metadata": scoring_metadata,
        "paa_kwargs": {
            "workflow_mode": str(bom.get("workflow_mode") or ""),
            "paa_artifact": paa_artifact,
            "content_brief": artifact_path("content_brief"),
            "answersocrates_blocker": artifact_path("answersocrates_blocker"),
            "expected_query": str(paa_policy.get("query") or ""),
            "expected_collection_date": str(bom.get("assembly_date") or ""),
            "expected_run_id": _canonical_bom_run_id(bom),
        },
    }


def _no_fit_customer_proof_findings(
    article_content: str,
    *,
    runtime_policy: Mapping[str, Any],
) -> List[Dict[str, Any]]:
    evidence_path = runtime_policy.get("customer_proof_selector_evidence")
    if not isinstance(evidence_path, str) or not evidence_path:
        return []
    try:
        evidence = json.loads(Path(evidence_path).read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return []
    if not isinstance(evidence, Mapping):
        return []
    if evidence.get("selection_outcome") != NO_FIT_CUSTOMER_PROOF_OUTCOME:
        return []
    try:
        _, scan_content, body_start_line = split_frontmatter(article_content)
    except FrontmatterError:
        scan_content = article_content
        body_start_line = 1
    for line_number, line in enumerate(
        scan_content.splitlines(),
        start=body_start_line,
    ):
        lowered = line.lower()
        if not lowered.strip():
            continue
        has_customer_proof_marker = any(
            marker in lowered for marker in CUSTOMER_PROOF_NO_FIT_MARKERS
        )
        has_customer_metric_shape = (
            "%" in line
            and any(
                marker in lowered
                for marker in (
                    "customer",
                    "case study",
                    "review",
                    "testimonial",
                    "reduced",
                    "increased",
                    "saved",
                    "improved",
                )
            )
        )
        has_customer_quote_shape = (
            bool(CUSTOMER_PROOF_EXACT_QUOTE_RE.search(line))
            and bool(CUSTOMER_PROOF_QUOTE_CONTEXT_RE.search(lowered))
        )
        if (
            has_customer_proof_marker
            or has_customer_metric_shape
            or has_customer_quote_shape
        ):
            return [
                {
                    "rule_id": "customer_proof_no_fit_public_claim_present",
                    "severity": "error",
                    "line": line_number,
                    "column": 1,
                    "message": (
                        "The bound selector evidence selected no customer proof, "
                        "but the article contains customer proof-sensitive copy."
                    ),
                    "suggestion": (
                        "Remove the customer proof copy or rerun customer proof "
                        "selection and mining with approved bound evidence."
                    ),
                }
            ]
    return []


def _canonical_bom_run_id(bom: Mapping[str, Any]) -> str:
    workflow = bom.get("workflow")
    receipts = workflow.get("stage_receipts") if isinstance(workflow, Mapping) else None
    if isinstance(receipts, list) and receipts and isinstance(receipts[0], Mapping):
        run_id = receipts[0].get("run_id")
        if isinstance(run_id, str) and run_id.strip():
            return run_id.strip()
    return ""


def format_text_report(result: ReadinessResult) -> str:
    """Return a human-readable publish-readiness report."""
    lines = [
        "PUBLISH READINESS",
        "=" * 50,
        f"File: {result['file']}",
        f"Proof sidecar: {result.get('proof_sidecar') or 'auto/default'}",
        f"Context request: {result.get('context_request') or 'not required/provided'}",
        f"Context pack: {result.get('context_pack') or 'not required/provided'}",
        f"Context receipt: {result.get('context_receipt') or 'not required/provided'}",
        f"Assembly BOM: {result.get('assembly_bom') or 'not required/provided'}",
        f"Overall: {'PASS' if result['passed'] else 'FAIL'}",
        "",
        "Gates:",
    ]

    for gate in result["gates"]:
        status = "PASS" if gate["passed"] else "FAIL"
        lines.append(
            f"  {status:4} {gate['label']:<28} "
            f"errors={gate['errors']} warnings={gate['warnings']}"
        )
        for blocker in gate.get("blockers", [])[:3]:
            lines.append(f"       - {blocker}")

    scorecard = result.get("scorecard")
    content_gate = _scorecard_gate(scorecard, "content_quality")
    seo_gate = _scorecard_gate(scorecard, "seo_quality")
    aeo_gate = _scorecard_gate(scorecard, "aeo_geo")

    content_score = content_gate.get("score", result.get("score"))
    content_threshold = content_gate.get("threshold", result.get("score_threshold", 85))
    content_passed = bool(
        content_gate.get(
            "passed",
            content_score is not None and content_score >= content_threshold,
        )
    )
    seo_score = seo_gate.get("score")
    seo_threshold = seo_gate.get("threshold", 90)
    seo_target = seo_gate.get("target", SEO_TARGET_SCORE)
    seo_passed = bool(seo_gate.get("passed", False))
    seo_target_met = seo_gate.get("target_met")
    seo_target_status = seo_gate.get("target_status")
    seo_critical_issue_count = seo_gate.get("critical_issue_count")
    aeo_geo = result.get("aeo_geo", {})
    if not isinstance(aeo_geo, Mapping):
        aeo_geo = {}
    aeo_geo_score = aeo_gate.get("score", aeo_geo.get("score"))
    aeo_geo_threshold = aeo_gate.get("threshold", aeo_geo.get("threshold", 90))
    aeo_geo_passed = bool(aeo_gate.get("passed", aeo_geo.get("passed", False)))

    lines.extend(
        [
            "",
            _score_report_line(
                "Content score",
                content_score,
                content_threshold,
                content_passed,
            ),
            _seo_score_report_line(
                "SEO score",
                seo_score,
                seo_threshold,
                seo_target,
                seo_passed,
                target_met=seo_target_met,
                target_status=seo_target_status,
            ),
        ]
    )
    if isinstance(seo_critical_issue_count, int) and not isinstance(
        seo_critical_issue_count,
        bool,
    ) and seo_critical_issue_count > 0:
        lines.append(f"SEO critical issues: {seo_critical_issue_count}")
    lines.append(
        _score_report_line(
            "AEO/GEO score",
            aeo_geo_score,
            aeo_geo_threshold,
            aeo_geo_passed,
        )
    )
    priority_fixes = result.get("priority_fixes", [])
    if priority_fixes:
        lines.append("")
        lines.append("Priority fixes:")
        for index, fix in enumerate(priority_fixes[:5], start=1):
            issue = fix.get("issue", "Unknown issue")
            dimension = fix.get("dimension", "unknown")
            lines.append(f"  {index}. [{dimension}] {issue}")

    lines.append("=" * 50)
    return "\n".join(lines)


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Run the publish-readiness gate stack.")
    parser.add_argument("file_path", help="Path to the draft or rewrite markdown file.")
    parser.add_argument(
        "--proof-sidecar",
        help="Validation sidecar containing proof maps and proof packs.",
    )
    parser.add_argument(
        "--profile",
        default="simpro-web",
        help="AI copy linter profile. Defaults to simpro-web.",
    )
    parser.add_argument("--context-request", help="Current Simpro context request JSON.")
    parser.add_argument("--context-pack", help="Current Simpro v2 context pack JSON.")
    parser.add_argument("--context-receipt", help="Current Simpro context receipt JSON.")
    parser.add_argument("--assembly-bom", help="Current blog assembly BOM JSON.")
    parser.add_argument(
        "--phase",
        choices=("preflight", "final"),
        default="preflight",
        help="Validate a provisional BOM for preflight or a final BOM for attestation.",
    )
    parser.add_argument(
        "--output",
        help="Atomically persist the machine-readable readiness result JSON.",
    )
    parser.add_argument(
        "--stage-receipt-output",
        help="Optional receipt path; defaults beside --output for passed runs.",
    )
    parser.add_argument(
        "--telemetry-output",
        help="Optional content-free readiness telemetry JSON output.",
    )
    parser.add_argument("--vault-root", help="Configured Simpro vault root override.")
    parser.add_argument(
        "--workspace-root",
        default=str(Path.cwd()),
        help="Trusted repository root used to resolve and contain all readiness artifacts.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print machine-readable JSON instead of the text report.",
    )
    args = parser.parse_args(argv)
    if args.stage_receipt_output and not args.output:
        parser.error("--stage-receipt-output requires --output")
    if args.assembly_bom and not args.output:
        parser.error("--output is required when --assembly-bom is supplied")
    if args.phase == "preflight" and args.stage_receipt_output:
        parser.error(
            "preflight receipts use the deterministic --output companion path; "
            "--stage-receipt-output is allowed only for final attestation"
        )
    if args.telemetry_output:
        try:
            _reject_telemetry_output_collision(args)
        except ValueError as error:
            parser.error(str(error))

    telemetry: ReadinessTelemetry | None = None
    if args.telemetry_output:
        try:
            telemetry = ReadinessTelemetry(
                run_id=_readiness_run_id(
                    args.assembly_bom,
                    file_sha256(args.file_path),
                ),
                phase=args.phase,
            )
            telemetry.increment("full_readiness_executions")
        except (OSError, UnicodeError, ValueError) as error:
            parser.error(str(error))

    try:
        if telemetry is None:
            result = run_publish_readiness(
                args.file_path,
                proof_sidecar=args.proof_sidecar,
                context_request=args.context_request,
                context_pack=args.context_pack,
                context_receipt=args.context_receipt,
                assembly_bom=args.assembly_bom,
                vault_root=args.vault_root,
                ai_profile=args.profile,
                phase=args.phase,
                workspace_root=args.workspace_root,
            )
        else:
            with telemetry.stage("publish_readiness"):
                result = run_publish_readiness(
                    args.file_path,
                    proof_sidecar=args.proof_sidecar,
                    context_request=args.context_request,
                    context_pack=args.context_pack,
                    context_receipt=args.context_receipt,
                    assembly_bom=args.assembly_bom,
                    vault_root=args.vault_root,
                    ai_profile=args.profile,
                    phase=args.phase,
                    workspace_root=args.workspace_root,
                    telemetry=telemetry,
                )
        if telemetry is not None:
            telemetry.increment("gate_invocations", len(result.get("gates", [])))
        if args.output:
            write_readiness_result(
                args.output,
                result,
                receipt_path=args.stage_receipt_output,
                workspace_root=args.workspace_root,
            )
    except (OSError, UnicodeError, ValueError) as error:
        if telemetry is not None:
            telemetry.finish("operational_error")
            try:
                telemetry.write(
                    _resolve_workspace_input(
                        args.telemetry_output,
                        workspace_root=args.workspace_root,
                        field="telemetry output",
                    )
                )
            except (OSError, UnicodeError, ValueError) as telemetry_error:
                parser.error(f"{error}; telemetry write failed: {telemetry_error}")
        parser.error(str(error))
    if telemetry is not None:
        telemetry.finish("passed" if result.get("passed") is True else "blocked")
        try:
            telemetry.write(
                _resolve_workspace_input(
                    args.telemetry_output,
                    workspace_root=args.workspace_root,
                    field="telemetry output",
                )
            )
        except (OSError, UnicodeError, ValueError) as error:
            parser.error(str(error))
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(format_text_report(result))
    return 0 if result["passed"] else 1


def _reject_telemetry_output_collision(args: argparse.Namespace) -> None:
    root = Path(args.workspace_root).resolve()
    destination = _resolve_workspace_input(
        args.telemetry_output,
        workspace_root=root,
        field="telemetry output",
    )
    candidates = {
        "file": args.file_path,
        "proof_sidecar": args.proof_sidecar,
        "context_request": args.context_request,
        "context_pack": args.context_pack,
        "context_receipt": args.context_receipt,
        "assembly_bom": args.assembly_bom,
        "readiness_output": args.output,
        "stage_receipt_output": args.stage_receipt_output,
    }
    destination_key = os.path.normcase(str(destination))
    for label, value in candidates.items():
        if value is None:
            continue
        candidate = _resolve_workspace_input(value, workspace_root=root, field=label)
        if os.path.normcase(str(candidate)) == destination_key:
            raise ValueError(f"telemetry output cannot overwrite {label}")


def _gate_from_findings(
    name: str,
    label: str,
    findings: List[Dict[str, Any]],
) -> GateResult:
    summary = summarize_findings(findings)
    passed = not should_fail(findings, fail_on="error")
    return {
        "name": name,
        "label": label,
        "passed": passed,
        "errors": summary["error"],
        "warnings": summary["warning"],
        "findings": findings,
        "blockers": _finding_lines(findings) if not passed else [],
    }


def _timed_call(
    telemetry: ReadinessTelemetry | None,
    stage_name: str,
    operation: Any,
    *args: Any,
    **kwargs: Any,
) -> Any:
    if telemetry is None:
        return operation(*args, **kwargs)
    with telemetry.stage(stage_name):
        return operation(*args, **kwargs)


def _blocked_readiness_result(
    *,
    phase: str,
    article_path: Path,
    proof_sidecar_path: str | None,
    context_request_path: str | None,
    context_pack_path: str | None,
    context_receipt_path: str | None,
    assembly_bom_path: str | None,
    artifact_kind: str | None,
    gates: list[GateResult],
    score_threshold: int,
    gate: GateResult,
) -> ReadinessResult:
    return {
        "schema": READINESS_RESULT_SCHEMA,
        "phase": phase,
        "verification_scope": "source_artifact",
        "file": str(article_path),
        "proof_sidecar": proof_sidecar_path,
        "context_request": context_request_path,
        "context_pack": context_pack_path,
        "context_receipt": context_receipt_path,
        "assembly_bom": assembly_bom_path,
        "passed": False,
        "artifact_kind": artifact_kind,
        "gates": gates,
        "score": None,
        "score_threshold": score_threshold,
        "aeo_geo": {"score": None, "threshold": 90, "passed": False},
        "priority_fixes": [
            {
                "dimension": str(gate.get("name") or ""),
                "issue": blocker,
            }
            for blocker in gate.get("blockers", [])
        ],
    }


def _gate_from_url_summary(summary: UrlValidationSummary) -> GateResult:
    blockers = summary.blockers
    return {
        "name": "url_validator",
        "label": "URL Validator",
        "passed": summary.passed,
        "errors": len(blockers),
        "warnings": 0,
        "findings": [
            {
                "rule_id": "url_unresolved",
                "severity": "error",
                "line": result.line,
                "url": result.url,
                "status": result.status,
                "status_code": result.status_code,
                "reason": result.reason,
                "anchor": result.anchor,
            }
            for result in blockers
        ],
        "blockers": [
            _url_blocker_line(result)
            for result in blockers[:3]
        ],
    }


def _gate_from_score(score_result: Dict[str, Any]) -> GateResult:
    passed = bool(score_result.get("passed", False))
    priority_fixes = score_result.get("priority_fixes", [])
    return {
        "name": score_result.get("gate_name", "content_scorer"),
        "label": score_result.get("gate_label", "Content Scorer"),
        "passed": passed,
        "errors": 0 if passed else 1,
        "warnings": len(priority_fixes) if passed else 0,
        "findings": [],
        "blockers": _priority_fix_lines(priority_fixes) if not passed else [],
    }


def _score_content(
    article_path: Path,
    proof_sidecar: Optional[str],
    *,
    artifact_kind: str = "blog",
    assembly_bom: Optional[str] = None,
    runtime_policy: Mapping[str, Any] | None = None,
    workspace_root: str | Path,
    readiness_gate_context: object = None,
) -> Dict[str, Any]:
    content = article_path.read_text(encoding="utf-8")
    if artifact_kind == "landing_page":
        artifact = read_publishable_markdown(article_path)
        page_type = artifact.scalar("page_type").casefold()
        conversion_goal = artifact.scalar("conversion_goal").casefold()
        if page_type not in {"seo", "ppc"} or conversion_goal not in {
            "trial",
            "demo",
            "lead",
        }:
            return {
                "passed": False,
                "content_quality_score": None,
                "threshold": 75,
                "aeo_geo": {
                    "score": None,
                    "threshold": None,
                    "passed": True,
                    "not_applicable": True,
                },
                "priority_fixes": [
                    {
                        "dimension": "landing_page_metadata",
                        "issue": "Landing pages require page_type seo|ppc and conversion_goal trial|demo|lead.",
                    }
                ],
                "gate_name": "landing_page_scorer",
                "gate_label": "Landing Page Scorer",
            }
        result = LandingPageScorer(page_type, conversion_goal).score(
            content,
            meta_title=artifact.scalar("meta_title", "title"),
            meta_description=artifact.scalar("meta_description"),
            primary_keyword=artifact.scalar("primary_keyword", "target_keyword"),
        )
        issues = [
            {"dimension": "landing_page", "issue": str(issue)}
            for issue in result.get("critical_issues", [])
        ]
        if not issues and not result.get("publishing_ready"):
            issues = [
                {"dimension": "landing_page", "issue": str(issue)}
                for issue in result.get("suggestions", [])[:5]
            ]
        return {
            "passed": bool(result.get("publishing_ready")),
            "content_quality_score": result.get("overall_score"),
            "threshold": 75,
            "aeo_geo": {
                "score": None,
                "threshold": None,
                "passed": True,
                "not_applicable": True,
            },
            "priority_fixes": issues,
            "gate_name": "landing_page_scorer",
            "gate_label": "Landing Page Scorer",
            "landing_page": result,
        }
    scorer = ContentScorer()
    policy = dict(runtime_policy or {})
    if assembly_bom and not policy:
        policy = _bom_runtime_policy(
            assembly_bom,
            workspace_root=workspace_root,
        )
    raw_metadata = policy.get("scoring_metadata")
    metadata = dict(raw_metadata) if isinstance(raw_metadata, Mapping) else {}
    metadata["faq_policy_status"] = str(policy.get("faq_policy_status") or "")
    raw_paa = policy.get("paa_kwargs")
    paa = dict(raw_paa) if isinstance(raw_paa, Mapping) else {}
    return scorer.score(
        content,
        metadata=metadata,
        validate_urls=False,
        validate_source_support=False,
        source_path=str(article_path),
        proof_sidecar=proof_sidecar,
        finalized_bom=(
            policy.get("assembly_bom")
            if isinstance(policy.get("assembly_bom"), Mapping)
            else None
        ),
        assembly_date=str(policy.get("assembly_date") or "") or None,
        paa_workflow_mode=str(paa.get("workflow_mode") or "") or None,
        paa_content_brief=str(paa.get("content_brief") or "") or None,
        paa_answersocrates_blocker=(
            str(paa.get("answersocrates_blocker") or "") or None
        ),
        paa_expected_query=str(paa.get("expected_query") or "") or None,
        paa_expected_collection_date=(
            str(paa.get("expected_collection_date") or "") or None
        ),
        paa_expected_run_id=str(paa.get("expected_run_id") or "") or None,
        paa_artifact=str(paa.get("paa_artifact") or "") or None,
        readiness_gate_context=readiness_gate_context,
    )


def _content_score(score_result: Dict[str, Any]) -> Any:
    return score_result.get("content_quality_score", score_result.get("composite_score"))


def _scorecard_from_scorer_result(
    score_result: Mapping[str, Any],
    *,
    artifact_kind: str,
) -> Dict[str, Any]:
    """Return independent publish score gates from a scorer result."""
    gates = score_result.get("quality_gates")
    quality_gates = gates if isinstance(gates, Mapping) else {}
    content_source = quality_gates.get("content_quality")
    if not isinstance(content_source, Mapping):
        content_source = {}
    seo_source = quality_gates.get("seo_quality")
    if not isinstance(seo_source, Mapping):
        seo_source = {}
    aeo_source = quality_gates.get("aeo_geo")
    if not isinstance(aeo_source, Mapping):
        aeo_source = score_result.get("aeo_geo")
    if not isinstance(aeo_source, Mapping):
        aeo_source = {}

    content_threshold = content_source.get("threshold", score_result.get("threshold"))
    if not _is_number(content_threshold):
        content_threshold = 75 if artifact_kind == "landing_page" else 85
    content_score = content_source.get("score", _content_score(dict(score_result)))
    content_passed = bool(
        content_source.get(
            "passed",
            _is_number(content_score) and float(content_score) >= float(content_threshold),
        )
    )

    seo_not_applicable = artifact_kind != "blog" and not seo_source
    if seo_not_applicable:
        critical_issues: list[Any] = []
        seo_threshold = None
        seo_target = None
        seo_score = None
        seo_passed = True
        seo_target_met = False
        seo_target_status = None
    else:
        critical_issues = seo_source.get("critical_issues", [])
        if not isinstance(critical_issues, list):
            critical_issues = []
        seo_threshold = SEO_PUBLISHING_THRESHOLD
        seo_target = SEO_TARGET_SCORE
        seo_score = seo_source.get("score")
        seo_passed = (
            _is_number(seo_score)
            and float(seo_score) >= float(seo_threshold)
            and len(critical_issues) == 0
        )
        seo_target_met = _is_number(seo_score) and float(seo_score) >= float(seo_target)
        if not seo_passed:
            seo_target_status = "failed_floor"
        elif seo_target_met:
            seo_target_status = "met"
        else:
            seo_target_status = "below_target"

    aeo_not_applicable = artifact_kind != "blog" and aeo_source.get("not_applicable") is True
    aeo_threshold = aeo_source.get("threshold", 90)
    aeo_score = aeo_source.get("score")
    if aeo_not_applicable:
        aeo_passed = bool(aeo_source.get("passed", True))
    else:
        aeo_passed = bool(
            aeo_source.get(
                "passed",
                _is_number(aeo_score) and float(aeo_score) >= float(aeo_threshold),
            )
        )

    content_gate = {
        "score": content_score,
        "threshold": content_threshold,
        "passed": content_passed,
    }
    seo_gate = {
        "score": seo_score,
        "threshold": seo_threshold,
        "passed": seo_passed,
        "critical_issue_count": len(critical_issues),
    }
    if not seo_not_applicable:
        seo_gate.update(
            {
                "target": seo_target,
                "target_met": bool(seo_target_met),
                "target_status": seo_target_status,
            }
        )
    aeo_gate = {
        "score": aeo_score,
        "threshold": aeo_threshold,
        "passed": aeo_passed,
    }
    if seo_not_applicable:
        seo_gate["not_applicable"] = True
    if critical_issues:
        seo_gate["critical_issues"] = critical_issues
    if aeo_source.get("not_applicable") is True:
        aeo_gate["not_applicable"] = True
    return {
        "passed": bool(
            content_gate["passed"]
            and seo_gate["passed"]
            and aeo_gate["passed"]
        ),
        "content_quality": content_gate,
        "seo_quality": seo_gate,
        "aeo_geo": aeo_gate,
    }


def _score_report_line(
    label: str,
    score: Any,
    threshold: Any,
    passed: bool,
) -> str:
    if score is None:
        return f"{label}: n/a"
    status = "PASS" if passed else "FAIL"
    return f"{label}: {score}/100 (threshold: {threshold}, {status})"


def _seo_score_report_line(
    label: str,
    score: Any,
    threshold: Any,
    target: Any,
    passed: bool,
    *,
    target_met: Any,
    target_status: Any,
) -> str:
    if score is None:
        return f"{label}: n/a"
    if not passed:
        status = "FAIL"
    elif target_met is True or target_status == "met":
        status = "PASS, TARGET MET"
    else:
        status = "PASS, BELOW TARGET"
    return (
        f"{label}: {score}/100 "
        f"(release floor: {threshold}, target: {target}, {status})"
    )


def _finding_lines(findings: List[Dict[str, Any]]) -> List[str]:
    blockers = [
        finding
        for finding in findings
        if finding.get("severity") == "error"
    ]
    if not blockers:
        blockers = findings
    lines = []
    for finding in blockers[:3]:
        line = finding.get("line", "?")
        rule = finding.get("rule_id", "finding")
        message = finding.get("message", "")
        lines.append(f"line {line}: {rule} - {message}".rstrip(" -"))
    return lines


def _url_blocker_line(result: Any) -> str:
    location = f"line {result.line}: " if result.line else ""
    anchor = f" [{result.anchor}]" if result.anchor else ""
    code = f"HTTP {result.status_code}" if result.status_code is not None else result.reason
    line = f"{location}{result.url}{anchor} ({result.status}: {code})"
    if result.status == "manual_review":
        line += (
            " Replace this source with an equivalent resolved public source "
            "or remove the supported claim. Do not remove the citation without "
            "replacing it with a resolved source supporting the same claim."
        )
    return line


def _priority_fix_lines(priority_fixes: List[Dict[str, Any]]) -> List[str]:
    lines = []
    for fix in priority_fixes[:3]:
        dimension = fix.get("dimension", "unknown")
        issue = fix.get("issue", "Unknown issue")
        lines.append(f"{dimension}: {issue}")
    return lines


if __name__ == "__main__":
    sys.exit(main())
