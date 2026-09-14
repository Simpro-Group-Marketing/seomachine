"""Session-backed checks owned by blog assembly BOM validation."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from . import snapshot_adapters as blog_assembly_bom_snapshot


def check_editorial_plan_dispatch(
    guard: Any,
    legacy: Any,
    bom: Mapping[str, Any],
    artifacts: Mapping[str, Any],
    root: Path,
    article_path: str | Path,
    captured: Any,
) -> list[dict[str, Any]]:
    """Select the authoritative or compatibility editorial validator."""
    if captured is not None:
        return check_editorial_plan(guard, bom, artifacts, root, captured)
    return legacy(bom, artifacts, root, article_path)


def check_editorial_plan(
    guard: Any,
    bom: Mapping[str, Any],
    artifacts: Mapping[str, Any],
    root: Path,
    captured: Any,
) -> list[dict[str, Any]]:
    """Validate editorial, keyword, policy, and PAA state from snapshots."""
    row = artifacts.get("editorial_plan")
    if not isinstance(row, Mapping) or not isinstance(row.get("path"), str):
        return []
    try:
        plan_snapshot = captured.snapshot_row(
            row, field="artifacts.editorial_plan",
        )
        plan = captured.json_row_copy(row, field="artifacts.editorial_plan")
        article_path = captured.snapshot_row(
            artifacts.get("article"), field="artifacts.article",
        ).path
        serp_path = captured.snapshot_row(
            artifacts.get("serp_evidence"), field="artifacts.serp_evidence",
        ).path
        keyword_path = captured.snapshot_row(
            artifacts.get("keyword_decision"), field="artifacts.keyword_decision",
        ).path
    except ValueError as error:
        return [guard["_finding"](
            "bom_editorial_plan_invalid", f"Editorial plan is invalid: {error}",
        )]
    if plan.get("schema") != guard["EDITORIAL_PLAN_SCHEMA"]:
        return [guard["_finding"](
            "bom_editorial_plan_schema_invalid",
            f"Editorial plan must use {guard['EDITORIAL_PLAN_SCHEMA']}.",
        )]
    assembled = guard["_parse_date"](bom.get("assembly_date"))
    if assembled is None:
        return [guard["_finding"](
            "bom_assembly_date_invalid", "BOM assembly date is invalid.",
        )]
    article_content = captured.text("article")
    run_id = (
        guard["_bom_serp_expected_run_id"](
            bom, artifacts, root, captured=captured,
        )
        or guard["canonical_article_run_id"](
            article_path, workspace_root=root, assembly_date=assembled,
        )
    )
    plan_findings = _plan_findings(
        guard,
        bom=bom,
        plan=plan,
        plan_path=plan_snapshot.path,
        article_path=article_path,
        article_content=article_content,
        serp_path=serp_path,
        keyword_path=keyword_path,
        run_id=run_id,
        root=root,
        captured=captured,
    )
    if plan_findings:
        return _wrap(guard, plan_findings, "Editorial plan is invalid.")
    return _policy_findings(
        guard,
        bom=bom,
        artifacts=artifacts,
        plan=plan,
        article_path=article_path,
        article_content=article_content,
        assembled=assembled,
        run_id=run_id,
        root=root,
        captured=captured,
    )


def _plan_findings(
    guard: Any,
    *,
    bom: Mapping[str, Any],
    plan: Mapping[str, Any],
    plan_path: Path,
    article_path: Path,
    article_content: str,
    serp_path: Path,
    keyword_path: Path,
    run_id: str,
    root: Path,
    captured: Any,
) -> list[dict[str, Any]]:
    raw = (
        blog_assembly_bom_snapshot.json_snapshot(captured, "serp_raw_capture")
        if captured.optional_snapshot("serp_raw_capture") is not None else None
    )
    brief = captured.optional_snapshot("content_brief")
    findings = guard["editorial_plan_guard"]._check_loaded_plan(
        plan,
        plan_path=plan_path,
        article_path=article_path,
        serp_evidence_path=serp_path,
        assembly_date=str(bom.get("assembly_date") or ""),
        expected_run_id=run_id,
        article_content=article_content,
        serp_evidence_payload=captured.json_row_copy(
            artifacts_row(captured, "serp_evidence"),
            field="artifacts.serp_evidence",
        ),
        raw_capture_snapshot=raw,
        brief_content=(
            blog_assembly_bom_snapshot.optional_text(captured, "content_brief")
            if brief is not None else None
        ),
        brief_sha256=brief.sha256 if brief is not None else None,
        workspace_root=root,
    )
    findings.extend(guard["semrush_keyword_decision_guard"].check_decision(
        captured.json_row_copy(
            artifacts_row(captured, "keyword_decision"),
            field="artifacts.keyword_decision",
        ),
        article_path=article_path,
        article_content=article_content,
        editorial_plan_path=plan_path,
        editorial_plan=plan,
        assembly_date=str(bom.get("assembly_date") or ""),
    ))
    return findings


def artifacts_row(captured: Any, label: str) -> dict[str, str]:
    snapshot = captured.snapshot(label)
    return {"path": snapshot.relative_path, "sha256": snapshot.sha256}


def _policy_findings(
    guard: Any,
    *,
    bom: Mapping[str, Any],
    artifacts: Mapping[str, Any],
    plan: Mapping[str, Any],
    article_path: Path,
    article_content: str,
    assembled: Any,
    run_id: str,
    root: Path,
    captured: Any,
) -> list[dict[str, Any]]:
    try:
        expected = guard["_editorial_plan_summary"](plan)
    except (KeyError, TypeError) as error:
        return [guard["_finding"](
            "bom_editorial_plan_incomplete", f"Editorial plan is incomplete: {error}",
        )]
    findings: list[dict[str, Any]] = []
    if bom.get("editorial_plan_summary") != expected:
        findings.append(guard["_finding"](
            "bom_editorial_plan_summary_mismatch",
            "BOM editorial plan summary does not match the bound plan.",
        ))
    connector = bom.get("connector_binding")
    context = connector.get("context") if isinstance(connector, Mapping) else None
    resource_ids = (
        context.get("selected_resource_ids") if isinstance(context, Mapping) else []
    )
    expected_industry = guard["industry_cluster_link_policy"].summarize_policy(
        article_content,
        plan=plan,
        context_resource_ids=resource_ids if isinstance(resource_ids, list) else [],
    )
    if bom.get("industry_cluster_link_policy") != expected_industry:
        findings.append(guard["_finding"](
            "bom_industry_cluster_link_policy_mismatch",
            "BOM industry_cluster_link_policy does not match the current article, editorial plan, and context binding.",
        ))
    expected_eeat = _eeat_policy(
        guard, article_content, plan, captured,
    )
    selector = artifacts.get("customer_proof_selector_evidence")
    fred = artifacts.get("fred_authority_evidence")
    expected_eeat["customer_proof_selector_evidence"] = (
        str(selector.get("path")) if isinstance(selector, Mapping) else ""
    )
    expected_eeat["fred_authority_evidence"] = (
        str(fred.get("path")) if isinstance(fred, Mapping) else ""
    )
    if bom.get("eeat_strength_policy") != expected_eeat:
        findings.append(guard["_finding"](
            "bom_eeat_strength_policy_mismatch",
            "BOM eeat_strength_policy does not match the current article, editorial plan, sidecar, and proof evidence.",
        ))
    if bom.get("faq_policy") != plan.get("faq_policy"):
        findings.append(guard["_finding"](
            "bom_faq_policy_mismatch",
            "BOM faq_policy must exactly match the bound editorial plan.",
        ))
    findings.extend(_paa_findings(
        guard,
        bom=bom,
        artifacts=artifacts,
        article_path=article_path,
        article_content=article_content,
        assembled=assembled,
        run_id=run_id,
        captured=captured,
    ))
    ownership = plan.get("query_ownership")
    if isinstance(ownership, Mapping) and ownership.get("decision") == "blocked":
        findings.append(guard["_finding"](
            "bom_query_ownership_blocked", "Blocked query ownership prevents readiness.",
        ))
    return findings


def _eeat_policy(
    guard: Any,
    article_content: str,
    plan: Mapping[str, Any],
    captured: Any,
) -> dict[str, Any]:
    customer = captured.optional_snapshot("customer_proof_selector_evidence")
    fred = captured.optional_snapshot("fred_authority_evidence")
    module = guard["eeat_strength_guard"]
    proof = captured.text("validation_sidecar")
    customer_payload = (
        captured.json_row_copy(
            artifacts_row(captured, "customer_proof_selector_evidence"),
            field="customer_proof_selector_evidence",
        ) if customer is not None else None
    )
    fred_content = (
        blog_assembly_bom_snapshot.optional_text(
            captured, "fred_authority_evidence",
        ) if fred is not None else ""
    )
    context = module._evaluate(
        article_content,
        proof_content=proof,
        editorial_plan=plan,
        customer_proof_evidence=customer_payload,
        fred_authority_content=fred_content,
    )
    findings = module.check_content(
        article_content,
        proof_content=proof,
        editorial_plan=plan,
        customer_proof_evidence=customer_payload,
        fred_authority_content=fred_content,
    )
    status = "not_applicable"
    if context["applicability"] == "required":
        status = (
            "failed" if any(str(row.get("severity")) == "error" for row in findings)
            else "warning" if any(
                str(row.get("severity")) == "warning" for row in findings
            ) else "passed"
        )
    return {
        "applicability": context["applicability"],
        "intent": context["intent"],
        "intent_reasons": context["intent_reasons"],
        "positive_signals": context["positive_signals"],
        "decision": context["decision"],
        "sidecar_status": context["sidecar_status"],
        "status": status,
        "findings": [str(row.get("rule_id") or "") for row in findings],
        "customer_proof_selector_evidence": str(customer_payload or ""),
        "fred_authority_evidence": str(fred_content or ""),
    }


def _paa_findings(
    guard: Any,
    *,
    bom: Mapping[str, Any],
    artifacts: Mapping[str, Any],
    article_path: Path,
    article_content: str,
    assembled: Any,
    run_id: str,
    captured: Any,
) -> list[dict[str, Any]]:
    policy = bom.get("paa_policy")
    if not isinstance(policy, Mapping):
        return []
    label = {
        "answersocrates": "paa_artifact",
        "brief_paa": "content_brief",
        "user_csv": "user_paa_csv",
    }.get(str(policy.get("source_kind") or ""))

    def path(name: str | None) -> str | None:
        snapshot = captured.optional_snapshot(name) if name is not None else None
        return str(snapshot.path) if snapshot is not None else None

    raw = (
        blog_assembly_bom_snapshot.json_snapshot(captured, "paa_raw_capture")
        if captured.optional_snapshot("paa_raw_capture") is not None else None
    )
    findings = guard["paa_provenance_guard"].check_content(
        article_content,
        source_path=str(article_path),
        proof_content=captured.text("validation_sidecar"),
        workflow_mode=str(bom.get("workflow_mode") or ""),
        content_brief=path("content_brief"),
        answersocrates_blocker=path("answersocrates_blocker"),
        expected_query=str(policy.get("query") or ""),
        expected_collection_date=assembled.isoformat(),
        expected_run_id=run_id,
        paa_artifact=path(label),
        content_brief_content=blog_assembly_bom_snapshot.optional_text(
            captured, "content_brief",
        ),
        answersocrates_blocker_content=blog_assembly_bom_snapshot.optional_text(
            captured, "answersocrates_blocker",
        ),
        paa_artifact_content=blog_assembly_bom_snapshot.optional_text(
            captured, label,
        ),
        raw_capture_snapshot=raw,
    )
    return _wrap(guard, findings, "PAA provenance is invalid.")


def _wrap(
    guard: Any,
    findings: list[Mapping[str, Any]],
    fallback: str,
) -> list[dict[str, Any]]:
    return [
        guard["_finding"](
            f"bom_{finding.get('rule_id')}",
            str(finding.get("message") or fallback),
        )
        for finding in findings
    ]


__all__ = ["check_editorial_plan", "check_editorial_plan_dispatch"]
