"""Focused validation phases for provisional BOM construction."""
# ruff: noqa: F403, F405

from .common import *  # noqa: F403


def normalize_construction_inputs(
    *,
    required_paths: Mapping[str, str | Path],
    optional_paths: Mapping[str, str | Path | None],
    stage_receipt_paths: Sequence[str | Path],
    optimizer_output_paths: Sequence[str | Path] | None,
    agent_output_paths: Mapping[str, str | Path] | None,
    workspace_root: str | Path | None,
    vault_root: str | Path | None,
) -> tuple[list[str | Path], list[str | Path], dict[str, str | Path], Path]:
    for field, value in required_paths.items():
        _validate_input_path(value, field=field)
    for field, value in optional_paths.items():
        if value is not None:
            _validate_input_path(value, field=field)
    receipts = _validate_path_sequence(stage_receipt_paths, field="stage_receipt_paths")
    optimizer = _validate_path_sequence(
        optimizer_output_paths or (), field="optimizer_output_paths"
    )
    agents = agent_output_paths or {}
    if not isinstance(agents, Mapping):
        raise ValueError("agent_output_paths must be an ID-to-path object")
    normalized_agents: dict[str, str | Path] = {}
    for agent_id, output_path in agents.items():
        if not isinstance(agent_id, str) or not agent_id.strip():
            raise ValueError("agent_output_paths IDs must be non-empty strings")
        _validate_input_path(output_path, field=f"agent_output_paths.{agent_id}")
        normalized_agents[agent_id] = output_path
    if workspace_root is not None:
        _validate_input_path(workspace_root, field="workspace_root")
    if vault_root is not None:
        _validate_input_path(vault_root, field="vault_root")
    return receipts, optimizer, normalized_agents, Path(workspace_root or Path.cwd()).resolve()


def resolve_construction_execution_evidence(
    stage_receipts: Sequence[Mapping[str, Any]],
    *,
    prior_preflight_readiness_path: str | Path | None,
    agent_output_paths: Mapping[str, str | Path],
    workspace_root: Path,
) -> Mapping[str, Mapping[str, str]]:
    stages = tuple(str(receipt.get("stage") or "") for receipt in stage_receipts)
    optimized_tail = stages == (
        "post_optimization_scrub", "post_optimization_context_binding"
    )
    try:
        if optimized_tail:
            return _execution_evidence_from_prior_preflight(
                prior_preflight_readiness_path, workspace_root=workspace_root
            )
        return blog_assembly_capabilities.resolve_execution_evidence(
            stage_receipts,
            agent_output_paths=agent_output_paths,
            workspace_root=workspace_root,
        )
    except blog_assembly_capabilities.CapabilityRegistryError as error:
        raise ValueError(f"repository execution provenance is invalid: {error}") from error


def validate_plan_inputs(
    *,
    editorial_plan_path: str | Path,
    article_path: str | Path,
    serp_evidence_path: str | Path,
    keyword_decision_path: str | Path,
    assembly_date: date,
    run_id: str,
) -> None:
    plan_findings = editorial_plan_guard.check_file(
        editorial_plan_path,
        article_path=article_path,
        serp_evidence_path=serp_evidence_path,
        assembly_date=assembly_date.isoformat(),
        expected_run_id=run_id,
    )
    if plan_findings:
        rules = ", ".join(sorted({str(row.get("rule_id") or "") for row in plan_findings}))
        raise ValueError(f"editorial plan is invalid: {rules}")
    keyword_findings = semrush_keyword_decision_guard.check_file(
        keyword_decision_path,
        article_path=article_path,
        editorial_plan_path=editorial_plan_path,
        assembly_date=assembly_date.isoformat(),
    )
    if keyword_findings:
        rules = ", ".join(sorted({str(row.get("rule_id") or "") for row in keyword_findings}))
        raise ValueError(f"Semrush keyword decision is invalid: {rules}")


def _validate_nonconnector_evidence(
    *,
    fred_authority_evidence_path: str | Path | None,
    customer_proof_selector_evidence_path: str | Path | None,
) -> None:
    if fred_authority_evidence_path:
        raise ValueError("non-connector blog cannot include Fred authority evidence")
    if not customer_proof_selector_evidence_path:
        return
    try:
        schema = _optional_json_schema(customer_proof_selector_evidence_path)
    except ValueError:
        schema = ""
    if schema != NONVAULT_CUSTOMER_PROOF_SCHEMA:
        raise ValueError(
            "non-connector blog cannot include vault-dependent customer proof evidence; approved proof must use simpro-nonvault-customer-proof-selector-evidence/v1"
        )


def validate_connector_construction(
    article: Any,
    *,
    validation_sidecar_path: str | Path,
    context_request_path: str | Path | None,
    context_pack_path: str | Path | None,
    context_receipt_path: str | Path | None,
    customer_proof_selector_evidence_path: str | Path | None,
    fred_authority_evidence_path: str | Path | None,
    plan: Mapping[str, Any],
    vault_root: str | Path | None,
    context_client: Any,
) -> tuple[bool, Any, str | None]:
    required = context_binding_guard.requires_context(article.raw)
    context_paths = (context_request_path, context_pack_path, context_receipt_path)
    if required and not all(context_paths):
        raise ValueError(
            "connector-bound blog requires context_request_path, context_pack_path, and context_receipt_path"
        )
    if not required and any(context_paths):
        raise ValueError("non-connector blog cannot include a partial or caller-forced connector binding")
    if not required:
        _validate_nonconnector_evidence(
            fred_authority_evidence_path=fred_authority_evidence_path,
            customer_proof_selector_evidence_path=customer_proof_selector_evidence_path,
        )
        return False, None, NON_CONNECTOR_REASON
    result = context_binding_guard.validate_context_artifacts(
        article.path,
        proof_sidecar=validation_sidecar_path,
        context_request=context_request_path,
        context_pack=context_pack_path,
        context_receipt=context_receipt_path,
        editorial_plan=plan,
        vault_root=vault_root,
        client=context_client,
    )
    if not result.passed:
        rules = ", ".join(str(row.get("rule_id")) for row in result.findings)
        raise ValueError(f"context binding is invalid: {rules}")
    validate_sha256(result.pack_canonical_sha256, field="context.context_pack_hash")
    validate_sha256(result.receipt_canonical_sha256, field="context.receipt_hash")
    if not customer_proof_selector_evidence_path:
        raise ValueError("connector-bound blog requires customer proof selector evidence")
    if not fred_authority_evidence_path:
        raise ValueError("connector-bound blog requires Fred authority selection evidence")
    return True, result, None


def derive_and_validate_paa(
    article: Any,
    plan: Mapping[str, Any],
    *,
    workflow_mode: str,
    assembly_date: date,
    run_id: str,
    validation_sidecar_path: str | Path,
    paa_artifact_path: str | Path | None,
    content_brief_path: str | Path | None,
    user_paa_csv_path: str | Path | None,
    answersocrates_blocker_path: str | Path | None,
) -> Mapping[str, Any]:
    policy = _derive_paa_policy(
        plan,
        workflow_mode=workflow_mode,
        paa_artifact_path=paa_artifact_path,
        content_brief_path=content_brief_path,
        user_paa_csv_path=user_paa_csv_path,
        answersocrates_blocker_path=answersocrates_blocker_path,
    )
    if policy["selected_questions"] != _visible_faq_questions(article.raw):
        raise ValueError("paa_policy.selected_questions must exactly match visible FAQ headings in order")
    bound = {
        "brief_paa": content_brief_path,
        "user_csv": user_paa_csv_path,
    }.get(policy["source_kind"], paa_artifact_path)
    findings = paa_provenance_guard.check_file(
        str(article.path),
        proof_sidecar=str(validation_sidecar_path),
        workflow_mode=workflow_mode,
        content_brief=str(content_brief_path) if content_brief_path else None,
        answersocrates_blocker=str(answersocrates_blocker_path) if answersocrates_blocker_path else None,
        expected_query=str(policy["query"]),
        expected_collection_date=assembly_date.isoformat(),
        expected_run_id=run_id,
        paa_artifact=str(bound) if bound else None,
    )
    if findings:
        rules = ", ".join(sorted({str(row.get("rule_id")) for row in findings}))
        raise ValueError(f"PAA provenance is invalid: {rules}")
    return policy


def validate_connector_sidecar_bindings(
    *,
    connector_required: bool,
    validation_sidecar_path: str | Path,
    artifacts: Mapping[str, Any],
    workspace_root: Path,
) -> None:
    if not connector_required:
        return
    try:
        content = Path(validation_sidecar_path).read_text(encoding="utf-8")
    except (OSError, UnicodeError) as error:
        raise ValueError(f"validation sidecar is unreadable: {error}") from error
    errors = sidecar_evidence_binding_errors(
        content, artifacts, workspace_root=workspace_root, required=True
    )
    if errors:
        raise ValueError(
            "sidecar evidence bindings are invalid: " + ", ".join(code for code, _ in errors)
        )


__all__ = [
    "derive_and_validate_paa",
    "normalize_construction_inputs",
    "resolve_construction_execution_evidence",
    "validate_connector_construction",
    "validate_connector_sidecar_bindings",
    "validate_plan_inputs",
]
