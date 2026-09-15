"""Focused blog assembly BOM validation routines."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Mapping

from .. import (
    eeat_strength_guard,
    industry_cluster_link_policy,
    semrush_keyword_decision_guard,
)
import data_sources.modules.blog_bom_validation.session_validation as blog_assembly_bom_session
import data_sources.modules.blog_bom_validation.snapshot_adapters as blog_assembly_bom_snapshot
from ..blog_assembly.common import BOM_SCHEMA_V4, EDITORIAL_PLAN_SCHEMA
from ..blog_assembly.policy import _editorial_plan_summary
from ..blog_assembly_contract import (
    canonical_article_run_id,
    load_json_object_snapshot,
    resolve_artifact,
    validate_sha256,
    verify_artifact,
)
from ..editorial_plan.orchestration import _check_loaded_plan
from ..guard_common import Finding
from ..paa_provenance.evaluation import check_content as check_paa_provenance_content
from ..paa_provenance.results import check_file as check_paa_provenance_file
from .common import _finding, _parse_date
from .contracts import (
    OPTIMIZED_TAIL_FINAL_STAGES,
    OPTIMIZED_TAIL_PROVISIONAL_STAGES,
)
from .dependencies import BomValidationDependencies
from .fulfillment import check_editorial_fulfillment


LEGACY_EDITORIAL_PLAN_SCHEMA = "simpro-blog-editorial-plan/v1"

def _load_bound_editorial_plan(
    artifacts: Mapping[str, Any],
    root: Path,
) -> Mapping[str, Any] | None:
    row = artifacts.get("editorial_plan")
    if not isinstance(row, Mapping) or not isinstance(row.get("path"), str):
        return None
    try:
        path = verify_artifact(
            row,
            workspace_root=root,
            field="artifacts.editorial_plan",
        )
        plan = json.loads(path.read_text(encoding="utf-8"))
    except (ValueError, OSError, UnicodeError, json.JSONDecodeError):
        return None
    if not isinstance(plan, Mapping) or plan.get("schema") not in {
        LEGACY_EDITORIAL_PLAN_SCHEMA,
        EDITORIAL_PLAN_SCHEMA,
    }:
        return None
    return plan


def _load_bound_json_object(
    row: Any,
    *,
    workspace_root: Path,
    field: str,
) -> tuple[Path, dict[str, Any]]:
    """Hash and parse one bound JSON object from the same immutable bytes."""
    if not isinstance(row, Mapping):
        raise ValueError(f"{field} must be a path/hash object")
    expected = validate_sha256(row.get("sha256"), field=f"{field}.sha256")
    path = resolve_artifact(row.get("path"), workspace_root=workspace_root)
    snapshot = load_json_object_snapshot(path, field=field)
    if snapshot.sha256 != expected:
        raise ValueError(f"{field}.sha256 does not match current file contents")
    return path, snapshot.payload


def _check_editorial_plan(
    bom: Mapping[str, Any],
    artifacts: Mapping[str, Any],
    root: Path,
    article_path: str | Path,
) -> list[Finding]:
    row = artifacts.get("editorial_plan")
    if not isinstance(row, Mapping) or not isinstance(row.get("path"), str):
        return []
    try:
        path, plan = _load_bound_json_object(
            row,
            workspace_root=root,
            field="artifacts.editorial_plan",
        )
    except ValueError as error:
        return [_finding("bom_editorial_plan_invalid", f"Editorial plan is invalid: {error}")]
    expected_plan_schema = (
        EDITORIAL_PLAN_SCHEMA
        if bom.get("schema") == BOM_SCHEMA_V4
        else LEGACY_EDITORIAL_PLAN_SCHEMA
    )
    if not isinstance(plan, Mapping) or plan.get("schema") != expected_plan_schema:
        return [_finding("bom_editorial_plan_schema_invalid", f"Editorial plan must use {expected_plan_schema}.")]
    article_row = artifacts.get("article")
    serp_row = artifacts.get("serp_evidence")
    keyword_row = artifacts.get("keyword_decision")
    try:
        article_path = verify_artifact(
            article_row, workspace_root=root, field="artifacts.article",
        )
        serp_path = verify_artifact(
            serp_row, workspace_root=root, field="artifacts.serp_evidence",
        )
        keyword_path = verify_artifact(
            keyword_row, workspace_root=root, field="artifacts.keyword_decision",
        )
    except ValueError:
        return []
    assembled = _parse_date(bom.get("assembly_date"))
    if assembled is None:
        return [_finding("bom_assembly_date_invalid", "BOM assembly date is invalid.")]
    canonical_run_id = canonical_article_run_id(
        article_path,
        workspace_root=root,
        assembly_date=assembled,
    )
    workflow_run_id = _bom_serp_expected_run_id(
        bom, artifacts, root,
    ) or canonical_run_id
    plan_findings = _check_loaded_plan(
        plan,
        article_path=article_path,
        serp_evidence_path=serp_path,
        assembly_date=(
            str(bom.get("assembly_date"))
            if isinstance(bom.get("assembly_date"), str)
            else None
        ),
        expected_run_id=workflow_run_id,
        workspace_root=root,
    )
    plan_findings.extend(
        semrush_keyword_decision_guard.check_file(
            keyword_path,
            article_path=article_path,
            editorial_plan_path=path,
            assembly_date=(
                str(bom.get("assembly_date"))
                if isinstance(bom.get("assembly_date"), str)
                else None
            ),
        )
    )
    if plan_findings:
        return [
            _finding(
                f"bom_{finding.get('rule_id')}",
                str(finding.get("message") or "Editorial plan is invalid."),
            )
            for finding in plan_findings
        ]
    return _check_editorial_policy_bindings(
        bom,
        artifacts,
        root,
        article_path,
        plan,
        assembled,
        workflow_run_id,
    )


def _check_editorial_policy_bindings(
    bom: Mapping[str, Any],
    artifacts: Mapping[str, Any],
    root: Path,
    article_path: Path,
    plan: Mapping[str, Any],
    assembled: Any,
    workflow_run_id: str,
) -> list[Finding]:
    try:
        expected = _editorial_plan_summary(plan)
    except (KeyError, TypeError) as error:
        return [_finding("bom_editorial_plan_incomplete", f"Editorial plan is incomplete: {error}")]
    findings: list[Finding] = []
    if bom.get("editorial_plan_summary") != expected:
        findings.append(_finding("bom_editorial_plan_summary_mismatch", "BOM editorial plan summary does not match the bound plan."))
    try:
        article_content = article_path.read_bytes().decode("utf-8")
    except (OSError, UnicodeError) as error:
        return [_finding("bom_article_unreadable", f"Article cannot be read for industry cluster policy: {error}")]
    findings.extend(check_editorial_fulfillment(
        bom,
        artifacts,
        root,
        plan=plan,
        article_content=article_content,
    ))
    connector = bom.get("connector_binding")
    context = connector.get("context") if isinstance(connector, Mapping) else None
    resource_ids = (
        context.get("selected_resource_ids")
        if isinstance(context, Mapping)
        else []
    )
    expected_industry_policy = industry_cluster_link_policy.summarize_policy(
        article_content,
        plan=plan,
        context_resource_ids=(
            resource_ids
            if isinstance(resource_ids, list)
            else []
        ),
    )
    if bom.get("industry_cluster_link_policy") != expected_industry_policy:
        findings.append(
            _finding(
                "bom_industry_cluster_link_policy_mismatch",
                "BOM industry_cluster_link_policy does not match the current article, editorial plan, and context binding.",
            )
        )
    expected_eeat_strength_policy = _legacy_eeat_policy(
        article_content, artifacts, root, plan,
    )
    if bom.get("eeat_strength_policy") != expected_eeat_strength_policy:
        findings.append(
            _finding(
                "bom_eeat_strength_policy_mismatch",
                "BOM eeat_strength_policy does not match the current article, editorial plan, sidecar, and proof evidence.",
            )
        )
    if bom.get("faq_policy") != plan.get("faq_policy"):
        findings.append(
            _finding(
                "bom_faq_policy_mismatch",
                "BOM faq_policy must exactly match the bound editorial plan.",
            )
        )
    findings.extend(
        _legacy_paa_findings(
            bom, artifacts, root, article_path, assembled, workflow_run_id,
        )
    )
    ownership = plan.get("query_ownership")
    if isinstance(ownership, Mapping) and ownership.get("decision") == "blocked":
        findings.append(_finding("bom_query_ownership_blocked", "Blocked query ownership prevents readiness."))
    return findings


def _legacy_eeat_policy(
    article_content: str,
    artifacts: Mapping[str, Any],
    root: Path,
    plan: Mapping[str, Any],
) -> dict[str, Any]:
    expected = eeat_strength_guard.summarize_policy(
        article_content,
        proof_sidecar=_verified_optional_artifact_path(
            artifacts, "validation_sidecar", root,
        ),
        editorial_plan=plan,
        customer_proof_selector_evidence=_verified_optional_artifact_path(
            artifacts, "customer_proof_selector_evidence", root,
        ),
        fred_authority_evidence=_verified_optional_artifact_path(
            artifacts, "fred_authority_evidence", root,
        ),
    )
    for field in (
        "customer_proof_selector_evidence",
        "fred_authority_evidence",
    ):
        row = artifacts.get(field)
        expected[field] = str(row.get("path")) if isinstance(row, Mapping) else ""
    return expected


def _legacy_paa_findings(
    bom: Mapping[str, Any],
    artifacts: Mapping[str, Any],
    root: Path,
    article_path: Path,
    assembled: Any,
    workflow_run_id: str,
) -> list[Finding]:
    policy = bom.get("paa_policy")
    if not isinstance(policy, Mapping):
        return []
    artifact_label = {
        "answersocrates": "paa_artifact",
        "brief_paa": "content_brief",
        "user_csv": "user_paa_csv",
    }.get(str(policy.get("source_kind") or ""))
    result = check_paa_provenance_file(
        str(article_path),
        proof_sidecar=_bound_path(artifacts, "validation_sidecar", root),
        workflow_mode=str(bom.get("workflow_mode") or ""),
        content_brief=_bound_path(artifacts, "content_brief", root),
        answersocrates_blocker=_bound_path(
            artifacts, "answersocrates_blocker", root,
        ),
        expected_query=str(policy.get("query") or ""),
        expected_collection_date=assembled.isoformat(),
        expected_run_id=workflow_run_id,
        paa_artifact=(
            _bound_path(artifacts, artifact_label, root)
            if artifact_label else None
        ),
    )
    return [
        _finding(
            f"bom_{finding.get('rule_id')}",
            str(finding.get("message") or "PAA provenance is invalid."),
        )
        for finding in result
    ]


def _bound_path(
    artifacts: Mapping[str, Any],
    label: str,
    root: Path,
) -> str | None:
    artifact = artifacts.get(label)
    if not isinstance(artifact, Mapping):
        return None
    try:
        return str(
            verify_artifact(
                artifact,
                workspace_root=root,
                field=f"artifacts.{label}",
            )
        )
    except ValueError:
        return None


def _check_research_provenance(
    bom: Mapping[str, Any],
    artifacts: Mapping[str, Any],
    root: Path,
    article_path: str | Path,
    *,
    captured: Any = None,
    dependencies: BomValidationDependencies | None = None,
) -> list[Finding]:
    dependencies = dependencies or BomValidationDependencies()
    return blog_assembly_bom_session.check_editorial_plan_dispatch(
        _session_dependencies(
            dependencies,
            editorial_plan_schema=(
                EDITORIAL_PLAN_SCHEMA
                if bom.get("schema") == BOM_SCHEMA_V4
                else LEGACY_EDITORIAL_PLAN_SCHEMA
            ),
        ),
        _check_editorial_plan,
        bom,
        artifacts,
        root,
        article_path,
        captured,
    )


def _session_dependencies(
    dependencies: BomValidationDependencies,
    *,
    editorial_plan_schema: str = EDITORIAL_PLAN_SCHEMA,
) -> BomValidationDependencies:
    return dependencies.bind(
        EDITORIAL_PLAN_SCHEMA=editorial_plan_schema,
        _bom_serp_expected_run_id=_bom_serp_expected_run_id,
        _editorial_plan_summary=_editorial_plan_summary,
        _finding=_finding,
        _parse_date=_parse_date,
        canonical_article_run_id=canonical_article_run_id,
        editorial_plan_guard=SimpleNamespace(_check_loaded_plan=_check_loaded_plan),
        eeat_strength_guard=eeat_strength_guard,
        industry_cluster_link_policy=industry_cluster_link_policy,
        paa_provenance_guard=SimpleNamespace(
            check_content=check_paa_provenance_content,
        ),
        semrush_keyword_decision_guard=semrush_keyword_decision_guard,
    )


def _verified_optional_artifact_path(
    artifacts: Mapping[str, Any],
    field: str,
    root: Path,
) -> Path | None:
    row = artifacts.get(field)
    if not isinstance(row, Mapping):
        return None
    try:
        return verify_artifact(
            row,
            workspace_root=root,
            field=f"artifacts.{field}",
        )
    except ValueError:
        return None


def _bom_workflow_run_id(bom: Mapping[str, Any]) -> str | None:
    workflow = bom.get("workflow")
    receipts = (
        workflow.get("stage_receipts")
        if isinstance(workflow, Mapping)
        else None
    )
    if not isinstance(receipts, list) or not receipts:
        return None
    run_ids = {
        str(receipt.get("run_id") or "").strip()
        for receipt in receipts
        if isinstance(receipt, Mapping)
    }
    run_ids.discard("")
    if len(run_ids) != 1:
        return None
    return next(iter(run_ids))


def _bom_serp_expected_run_id(
    bom: Mapping[str, Any],
    artifacts: Mapping[str, Any],
    root: Path,
    *,
    captured: Any = None,
) -> str | None:
    workflow = bom.get("workflow")
    receipts = (
        workflow.get("stage_receipts")
        if isinstance(workflow, Mapping)
        else None
    )
    stages = tuple(
        str(receipt.get("stage") or "")
        for receipt in receipts
        if isinstance(receipt, Mapping)
    ) if isinstance(receipts, list) else ()
    optimized_tail = stages in {
        OPTIMIZED_TAIL_PROVISIONAL_STAGES,
        OPTIMIZED_TAIL_FINAL_STAGES,
    }
    if optimized_tail:
        prior_row = artifacts.get("prior_preflight_readiness")
        if isinstance(prior_row, Mapping):
            try:
                prior = blog_assembly_bom_snapshot.json_artifact(
                    captured,
                    prior_row,
                    field="artifacts.prior_preflight_readiness",
                    root=root,
                    legacy_loader=load_json_object_snapshot,
                    legacy_verify=verify_artifact,
                )
            except ValueError:
                prior = None
            if isinstance(prior, Mapping):
                run_id = str(prior.get("run_id") or "").strip()
                if run_id:
                    return run_id
    return _bom_workflow_run_id(bom)
