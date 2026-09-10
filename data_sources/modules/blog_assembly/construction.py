"""Construction responsibilities."""
# ruff: noqa: F403, F405

from .common import *  # noqa: F403
from .construction_support import (
    derive_and_validate_paa,
    normalize_construction_inputs,
    resolve_construction_execution_evidence,
    validate_connector_construction,
    validate_connector_sidecar_bindings,
    validate_plan_inputs,
)


def build_blog_assembly_bom_from_files(
    *,
    article_path: str | Path,
    validation_sidecar_path: str | Path,
    editorial_plan_path: str | Path,
    keyword_decision_path: str | Path,
    serp_evidence_path: str | Path,
    stage_receipt_paths: Sequence[str | Path],
    workflow_mode: str,
    assembly_date: str,
    plan_review_path: str | Path | None = None,
    article_review_path: str | Path | None = None,
    expected_review_run_id: str | None = None,
    paa_artifact_path: str | Path | None = None,
    content_brief_path: str | Path | None = None,
    user_paa_csv_path: str | Path | None = None,
    answersocrates_blocker_path: str | Path | None = None,
    context_request_path: str | Path | None = None,
    context_pack_path: str | Path | None = None,
    context_receipt_path: str | Path | None = None,
    customer_proof_selector_evidence_path: str | Path | None = None,
    fred_authority_evidence_path: str | Path | None = None,
    hindsight_strategy_evidence_path: str | Path | None = None,
    agent_output_paths: Mapping[str, str | Path] | None = None,
    optimizer_output_paths: Sequence[str | Path] | None = None,
    prior_preflight_readiness_path: str | Path | None = None,
    workspace_root: str | Path | None = None,
    context_client: Any = None,
    vault_root: str | Path | None = None,
) -> dict[str, Any]:
    """Build a deterministic provisional BOM from exact current files."""
    stage_receipt_paths, optimizer_output_paths, normalized_agent_output_paths, root = (
        normalize_construction_inputs(
            required_paths={
                "article_path": article_path,
                "validation_sidecar_path": validation_sidecar_path,
                "editorial_plan_path": editorial_plan_path,
                "keyword_decision_path": keyword_decision_path,
                "serp_evidence_path": serp_evidence_path,
            },
            optional_paths={
                "plan_review_path": plan_review_path,
                "article_review_path": article_review_path,
                "paa_artifact_path": paa_artifact_path,
                "content_brief_path": content_brief_path,
                "user_paa_csv_path": user_paa_csv_path,
                "answersocrates_blocker_path": answersocrates_blocker_path,
                "context_request_path": context_request_path,
                "context_pack_path": context_pack_path,
                "context_receipt_path": context_receipt_path,
                "customer_proof_selector_evidence_path": customer_proof_selector_evidence_path,
                "fred_authority_evidence_path": fred_authority_evidence_path,
                "hindsight_strategy_evidence_path": hindsight_strategy_evidence_path,
                "prior_preflight_readiness_path": prior_preflight_readiness_path,
            },
            stage_receipt_paths=stage_receipt_paths,
            optimizer_output_paths=optimizer_output_paths,
            agent_output_paths=agent_output_paths,
            workspace_root=workspace_root,
            vault_root=vault_root,
        )
    )
    mode = _required_enum(workflow_mode, "workflow_mode", WORKFLOW_MODES)
    assembled = _iso_date(assembly_date, "assembly_date")
    article = read_publishable_markdown(article_path)
    _validate_article_identity(article, assembled)
    canonical_run_id = canonical_article_run_id(
        article_path,
        workspace_root=root,
        assembly_date=assembled,
    )
    workflow_run_id = expected_review_run_id or canonical_run_id
    plan_snapshot = load_json_object_snapshot(
        editorial_plan_path,
        field="editorial_plan",
    )
    plan = plan_snapshot.payload
    stage_receipt_snapshots = [
        load_json_object_snapshot(path, field=f"stage_receipt[{index}]")
        for index, path in enumerate(stage_receipt_paths)
    ]
    stage_receipts = [snapshot.payload for snapshot in stage_receipt_snapshots]
    if plan_review_path is None or article_review_path is None:
        raise ValueError(
            "New BOM assembly requires both plan_review_path and article_review_path; "
            "BOM v1 is read-only archived evidence."
        )
    execution_evidence = resolve_construction_execution_evidence(
        stage_receipts,
        prior_preflight_readiness_path=prior_preflight_readiness_path,
        agent_output_paths=normalized_agent_output_paths,
        workspace_root=root,
    )
    validate_plan_inputs(
        editorial_plan_path=editorial_plan_path,
        article_path=article_path,
        serp_evidence_path=serp_evidence_path,
        keyword_decision_path=keyword_decision_path,
        assembly_date=assembled,
        run_id=workflow_run_id,
    )
    machine_reviews = _machine_review_bindings(
        plan_review_path=plan_review_path,
        article_review_path=article_review_path,
        editorial_plan_path=editorial_plan_path,
        article_path=article_path,
        proof_sidecar_path=validation_sidecar_path,
        workspace_root=root,
        expected_run_id=expected_review_run_id,
    )

    connector_required, context_result, connector_reason = validate_connector_construction(
        article,
        validation_sidecar_path=validation_sidecar_path,
        context_request_path=context_request_path,
        context_pack_path=context_pack_path,
        context_receipt_path=context_receipt_path,
        customer_proof_selector_evidence_path=customer_proof_selector_evidence_path,
        fred_authority_evidence_path=fred_authority_evidence_path,
        plan=plan,
        vault_root=vault_root,
        context_client=context_client,
    )

    paa_policy = derive_and_validate_paa(
        article,
        plan,
        workflow_mode=mode,
        assembly_date=assembled,
        run_id=workflow_run_id,
        validation_sidecar_path=validation_sidecar_path,
        paa_artifact_path=paa_artifact_path,
        content_brief_path=content_brief_path,
        user_paa_csv_path=user_paa_csv_path,
        answersocrates_blocker_path=answersocrates_blocker_path,
    )
    artifacts = {
        "article": canonical_artifact_identity(
            article.path,
            sha256=article.sha256,
            workspace_root=root,
        ),
        "validation_sidecar": canonical_artifact(
            validation_sidecar_path,
            workspace_root=root,
        ),
        "editorial_plan": canonical_artifact(editorial_plan_path, workspace_root=root),
        "keyword_decision": canonical_artifact(keyword_decision_path, workspace_root=root),
        "serp_evidence": canonical_artifact(serp_evidence_path, workspace_root=root),
        "paa_artifact": _optional_artifact(paa_artifact_path, root),
        "content_brief": _optional_artifact(content_brief_path, root),
        "user_paa_csv": _optional_artifact(user_paa_csv_path, root),
        "answersocrates_blocker": _optional_artifact(
            answersocrates_blocker_path,
            root,
        ),
        "context_request": _optional_artifact(context_request_path, root),
        "context_pack": _optional_artifact(context_pack_path, root),
        "context_receipt": _optional_artifact(context_receipt_path, root),
        "customer_proof_selector_evidence": _optional_artifact(
            customer_proof_selector_evidence_path,
            root,
        ),
        "fred_authority_evidence": _optional_artifact(
            fred_authority_evidence_path,
            root,
        ),
        "hindsight_strategy_evidence": _optional_artifact(
            hindsight_strategy_evidence_path,
            root,
        ),
        "execution_evidence": execution_evidence,
        "optimizer_outputs": [
            canonical_artifact(path, workspace_root=root)
            for path in (optimizer_output_paths or [])
        ],
        "stage_receipts": [
            canonical_snapshot_artifact(snapshot, workspace_root=root)
            for snapshot in stage_receipt_snapshots
        ],
        "stage_evidence": [
            canonical_artifact(stage_evidence_path(path), workspace_root=root)
            for path in stage_receipt_paths
            if stage_evidence_path(path).is_file()
        ],
        "prior_preflight_readiness": _optional_artifact(
            prior_preflight_readiness_path,
            root,
        ),
        "preflight_readiness": None,
    }
    validate_connector_sidecar_bindings(
        connector_required=connector_required,
        validation_sidecar_path=validation_sidecar_path,
        artifacts=artifacts,
        workspace_root=root,
    )
    if not stage_receipts:
        raise ValueError("stage_receipt_paths must contain real tool-emitted receipts")
    _validate_provisional_stage_receipts(
        stage_receipts,
        expected_run_id=workflow_run_id,
        assembly_date=assembled,
        article_sha256=artifacts["article"]["sha256"],
        optimizer_outputs=artifacts["optimizer_outputs"],
        artifacts=artifacts,
        execution_evidence=execution_evidence,
        connector_required=connector_required,
        connector_reason=connector_reason,
        prior_preflight_readiness_path=prior_preflight_readiness_path,
        visible_faq=bool(_visible_faq_questions(article.raw)),
        workspace_root=root,
    )
    eeat_strength_policy = eeat_strength_guard.summarize_policy(
        article.raw,
        proof_sidecar=validation_sidecar_path,
        editorial_plan=plan,
        customer_proof_selector_evidence=customer_proof_selector_evidence_path,
        fred_authority_evidence=fred_authority_evidence_path,
    )
    selector_row = artifacts.get("customer_proof_selector_evidence")
    fred_row = artifacts.get("fred_authority_evidence")
    eeat_strength_policy["customer_proof_selector_evidence"] = (
        str(selector_row.get("path"))
        if isinstance(selector_row, Mapping)
        else ""
    )
    eeat_strength_policy["fred_authority_evidence"] = (
        str(fred_row.get("path"))
        if isinstance(fred_row, Mapping)
        else ""
    )

    bom = {
        "schema": BOM_SCHEMA,
        "lifecycle_state": "provisional",
        "workflow_mode": mode,
        "assembly_date": assembled.isoformat(),
        "identity": _identity_from_article(article),
        "artifacts": artifacts,
        "connector_binding": _connector_binding(
            context_result,
            not_applicable_reason=connector_reason,
        ),
        "author_policy": _author_policy(article),
        "schema_policy": _schema_policy(article),
        "industry_cluster_link_policy": industry_cluster_link_policy.summarize_policy(
            article.raw,
            plan=plan,
            context_resource_ids=(
                context_result.resource_ids
                if context_result is not None
                else ()
            ),
        ),
        "eeat_strength_policy": eeat_strength_policy,
        "hindsight_strategy_policy": _hindsight_strategy_policy(
            validation_sidecar_path=validation_sidecar_path,
            hindsight_strategy_evidence_path=hindsight_strategy_evidence_path,
        ),
        "faq_policy": _required_mapping(plan.get("faq_policy"), "editorial_plan.faq_policy"),
        "paa_policy": paa_policy,
        "editorial_plan_summary": _editorial_plan_summary(plan),
        "workflow": {
            "stage_receipts": stage_receipts,
        },
        "machine_reviews": machine_reviews,
        "preflight": None,
    }
    _verify_bom_artifacts_unchanged(bom, root)
    return bom


__all__ = ['build_blog_assembly_bom_from_files']
