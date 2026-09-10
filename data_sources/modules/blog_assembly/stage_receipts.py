"""Stage Receipts responsibilities."""
# ruff: noqa: F403, F405

from .common import *  # noqa: F403


def _validate_receipt_sequence(
    receipts: list[Mapping[str, Any]],
    *,
    expected_run_id: str,
    assembly_date: date,
    optimizer_outputs: list[dict[str, str]],
    artifacts: Mapping[str, Any],
    execution_evidence: Mapping[str, Mapping[str, str]],
    prior_preflight_readiness_path: str | Path | None,
    workspace_root: Path,
) -> tuple[bool, bool, list[Mapping[str, str]]]:
    try:
        from ..blog_assembly_stage_receipt import check_receipt_chain
    except ImportError:  # pragma: no cover - supports direct script execution.
        from blog_assembly_stage_receipt import check_receipt_chain
    stages = tuple(str(receipt.get("stage") or "") for receipt in receipts)
    optimized_tail = stages == (
        "post_optimization_scrub", "post_optimization_context_binding"
    )
    optimized = "optimization" in stages
    if optimized_tail and not prior_preflight_readiness_path:
        raise ValueError("optimized-tail workflow requires prior preflight readiness evidence")
    if not optimized_tail and optimized != bool(prior_preflight_readiness_path):
        raise ValueError(
            "prior preflight readiness evidence must be present if and only if the optimization stage is present"
        )
    resolvable = _resolvable_receipt_evidence_hashes(
        receipts, artifacts=artifacts, execution_evidence=execution_evidence,
        workspace_root=workspace_root,
    )
    if not optimized_tail:
        findings = check_receipt_chain(
            receipts, expected_run_id=expected_run_id, assembly_date=assembly_date,
            now=datetime.now(timezone.utc), resolvable_evidence_hashes=resolvable,
        )
        if findings:
            rules = ", ".join(sorted({str(row.get("rule_id")) for row in findings}))
            raise ValueError(f"stage receipt chain is invalid: {rules}")
    expected = stages if optimized_tail else (
        OPTIMIZED_PROVISIONAL_STAGES if optimized
        else _legacy_value("NORMAL_PROVISIONAL_STAGES", NORMAL_PROVISIONAL_STAGES)
    )
    if stages != expected:
        raise ValueError("provisional stage receipt sequence must be exactly: " + " -> ".join(expected))
    if not optimized_tail and optimized != bool(optimizer_outputs):
        raise ValueError(
            "optimizer output evidence must be present if and only if the optimization stage is present"
        )
    expected_rows = [
        execution_evidence[f"agent_output.{agent_id}"]
        for agent_id in blog_assembly_capabilities.expected_agent_ids(receipts)
    ] if optimized else []
    if not optimized_tail and optimizer_outputs != expected_rows:
        raise ValueError(
            "optimizer outputs must exactly match the ordered, distinct agent output artifacts in execution evidence"
        )
    return optimized_tail, optimized, expected_rows


def _validate_draft_receipt(
    receipt: Mapping[str, Any] | None,
    artifacts: Mapping[str, Any],
) -> None:
    if receipt is None:
        return
    inputs = _required_mapping(receipt.get("input_artifact_hashes"), "draft.input_artifact_hashes")
    if inputs.get("editorial_plan") != artifacts["editorial_plan"]["sha256"]:
        raise ValueError("draft stage receipt must bind the editorial plan input")
    evidence = _required_mapping(receipt.get("evidence_hashes"), "draft.evidence_hashes")
    if evidence.get("serp_evidence") != artifacts["serp_evidence"]["sha256"]:
        raise ValueError("draft stage receipt must bind verified SERP evidence")
    if evidence.get("keyword_decision") != artifacts["keyword_decision"]["sha256"]:
        raise ValueError("draft stage receipt must bind Semrush keyword decision evidence")


def _validate_scrub_receipts(by_stage: Mapping[str, Mapping[str, Any]]) -> None:
    for stage_name in ("scrub", "post_optimization_scrub"):
        receipt = by_stage.get(stage_name)
        if receipt is None:
            continue
        evidence = _required_mapping(receipt.get("evidence_hashes"), f"{stage_name}.evidence_hashes")
        try:
            validate_sha256(
                evidence.get("scrub_statistics"),
                field=f"{stage_name}.evidence_hashes.scrub_statistics",
            )
        except ValueError as error:
            raise ValueError(f"{stage_name} stage receipt must bind scrub statistics") from error


def _validate_context_receipts(
    by_stage: Mapping[str, Mapping[str, Any]],
    *,
    artifacts: Mapping[str, Any],
    prior_readiness: Mapping[str, Any] | None,
    connector_required: bool,
    connector_reason: str | None,
) -> None:
    for stage_name in ("context_binding", "post_optimization_context_binding"):
        receipt = by_stage.get(stage_name)
        if receipt is None:
            continue
        outputs = _required_mapping(receipt.get("output_artifact_hashes"), f"{stage_name}.output_artifact_hashes")
        expected_sidecar = artifacts["validation_sidecar"]["sha256"]
        if stage_name == "context_binding" and prior_readiness is not None:
            prior_inputs = _required_mapping(prior_readiness.get("input_hashes"), "prior_preflight_readiness.input_hashes")
            expected_sidecar = _required_mapping(
                prior_inputs.get("validation_sidecar"),
                "prior_preflight_readiness.input_hashes.validation_sidecar",
            ).get("sha256")
        if outputs.get("validation_sidecar") != expected_sidecar:
            raise ValueError(f"{stage_name} stage receipt must bind the validation sidecar output")
        evidence = _required_mapping(receipt.get("evidence_hashes"), f"{stage_name}.evidence_hashes")
        try:
            validate_sha256(evidence.get("context_binding"), field=f"{stage_name}.evidence_hashes.context_binding")
        except ValueError as error:
            raise ValueError(f"{stage_name} stage receipt must bind generated Context Binding evidence") from error
        _validate_context_receipt_inputs(
            receipt, evidence, stage_name=stage_name, artifacts=artifacts,
            connector_required=connector_required, connector_reason=connector_reason,
        )


def _validate_context_receipt_inputs(
    receipt: Mapping[str, Any],
    evidence: Mapping[str, Any],
    *,
    stage_name: str,
    artifacts: Mapping[str, Any],
    connector_required: bool,
    connector_reason: str | None,
) -> None:
    if not connector_required:
        expected = normalized_text_sha256(connector_reason, field="connector_binding.reason")
        if evidence.get("not_applicable_reason") != expected:
            raise ValueError(f"{stage_name} stage receipt must bind the BOM connector not-applicable reason")
        return
    inputs = _required_mapping(receipt.get("input_artifact_hashes"), f"{stage_name}.input_artifact_hashes")
    for label in ("context_request", "context_pack", "context_receipt"):
        row = _required_mapping(artifacts.get(label), f"artifacts.{label}")
        if inputs.get(label) != row.get("sha256"):
            raise ValueError(f"{stage_name} stage receipt must bind {label} input")


def _validate_optimization_receipt(
    receipt: Mapping[str, Any] | None,
    *,
    receipts: list[Mapping[str, Any]],
    execution_evidence: Mapping[str, Mapping[str, str]],
    expected_optimizer_rows: Sequence[Mapping[str, str]],
) -> None:
    if receipt is None:
        return
    evidence = _required_mapping(receipt.get("evidence_hashes"), "optimization.evidence_hashes")
    try:
        expected = blog_assembly_capabilities.receipt_definition_hashes(
            receipts, stage="optimization", execution_evidence=execution_evidence
        )
    except blog_assembly_capabilities.CapabilityRegistryError as error:
        raise ValueError(f"optimization execution evidence is invalid: {error}") from error
    for label, digest in expected.items():
        if evidence.get(label) != digest:
            raise ValueError(
                "optimization stage receipt must bind optimize command, agent definitions, and final agent outputs: " + label
            )
    expected_hashes = {str(row["sha256"]) for row in expected_optimizer_rows}
    if not expected_hashes.issubset(set(evidence.values())):
        raise ValueError("optimization stage receipt must bind every optimizer output artifact")


def _validate_provisional_stage_receipts(
    receipts: list[Mapping[str, Any]],
    *,
    expected_run_id: str,
    assembly_date: date,
    article_sha256: str,
    optimizer_outputs: list[dict[str, str]],
    artifacts: Mapping[str, Any],
    execution_evidence: Mapping[str, Mapping[str, str]],
    connector_required: bool,
    connector_reason: str | None,
    prior_preflight_readiness_path: str | Path | None,
    visible_faq: bool,
    workspace_root: Path,
) -> None:
    optimized_tail, optimized, expected_optimizer_rows = _validate_receipt_sequence(
        receipts,
        expected_run_id=expected_run_id,
        assembly_date=assembly_date,
        optimizer_outputs=optimizer_outputs,
        artifacts=artifacts,
        execution_evidence=execution_evidence,
        prior_preflight_readiness_path=prior_preflight_readiness_path,
        workspace_root=workspace_root,
    )
    outputs = receipts[-1].get("output_artifact_hashes")
    if not isinstance(outputs, Mapping) or outputs.get("article") != article_sha256:
        raise ValueError("last provisional stage receipt must bind the final article hash")
    by_stage = {str(receipt.get("stage") or ""): receipt for receipt in receipts}
    prior_readiness = (
        _validate_prior_preflight_readiness(
            prior_preflight_readiness_path,
            receipt=by_stage["preflight_readiness"],
            visible_faq=visible_faq,
            connector_required=connector_required,
            workspace_root=workspace_root,
        )
        if optimized and not optimized_tail
        else None
    )
    _validate_draft_receipt(by_stage.get("draft"), artifacts)
    _validate_scrub_receipts(by_stage)
    _validate_context_receipts(
        by_stage,
        artifacts=artifacts,
        prior_readiness=prior_readiness,
        connector_required=connector_required,
        connector_reason=connector_reason,
    )
    _validate_optimization_receipt(
        by_stage.get("optimization"),
        receipts=receipts,
        execution_evidence=execution_evidence,
        expected_optimizer_rows=expected_optimizer_rows,
    )

def _validate_prior_preflight_readiness(
    path: str | Path | None,
    *,
    receipt: Mapping[str, Any],
    visible_faq: bool,
    connector_required: bool,
    workspace_root: Path,
) -> Mapping[str, Any]:
    if path is None:
        raise ValueError("optimized workflow requires prior preflight readiness evidence")
    readiness = _read_json_object(path, "prior_preflight_readiness")
    inputs = _required_mapping(
        readiness.get("input_hashes"),
        "prior_preflight_readiness.input_hashes",
    )
    prior_bom_row = _required_mapping(
        inputs.get("assembly_bom"),
        "prior_preflight_readiness.input_hashes.assembly_bom",
    )
    try:
        prior_bom_path = verify_artifact(
            prior_bom_row,
            workspace_root=workspace_root,
            field="prior_preflight_readiness.input_hashes.assembly_bom",
        )
    except ValueError as error:
        raise ValueError("prior preflight BOM artifact is invalid") from error
    prior_bom = _read_json_object(prior_bom_path, "prior_preflight_bom")
    if (
        not _is_supported_bom_schema(prior_bom.get("schema"))
        or prior_bom.get("lifecycle_state") != "provisional"
    ):
        raise ValueError("prior preflight must bind a provisional blog assembly BOM")
    prior_schema = _required_mapping(
        prior_bom.get("schema_policy"),
        "prior_preflight_bom.schema_policy",
    )
    prior_connector = _required_mapping(
        prior_bom.get("connector_binding"),
        "prior_preflight_bom.connector_binding",
    )
    expected_inventory = expected_blog_gate_inventory(
        visible_faq=prior_schema.get("visible_faq") is True,
        connector_required=prior_connector.get("status") == "required",
    )
    if (
        readiness.get("schema") != READINESS_SCHEMA
        or readiness.get("tool")
        != {"name": "publish_readiness", "version": "1.0.0"}
        or readiness.get("phase") != "preflight"
        or readiness.get("passed") is not True
        or readiness.get("artifact_kind") != "blog"
        or readiness.get("verification_scope") != "source_artifact"
        or readiness.get("input_seal") != {"status": "verified"}
        or readiness.get("gate_inventory") != expected_inventory
    ):
        raise ValueError("prior preflight readiness result is not a passed tool result")
    gates = readiness.get("gates")
    if not isinstance(gates, list) or [
        row.get("name") if isinstance(row, Mapping) else None for row in gates
    ] != expected_inventory or any(
        not isinstance(row, Mapping)
        or row.get("passed") is not True
        or row.get("errors") != 0
        or row.get("blockers") not in ([], ())
        for row in gates
    ):
        raise ValueError("prior preflight readiness gate results are invalid")
    score = readiness.get("score")
    aeo_geo = readiness.get("aeo_geo")
    if (
        readiness.get("score_threshold") != 85
        or not _is_number(score)
        or score < 85
        or not isinstance(aeo_geo, Mapping)
        or aeo_geo.get("threshold") != 90
        or aeo_geo.get("passed") is not True
        or not _is_number(aeo_geo.get("score"))
        or aeo_geo["score"] < 90
    ):
        raise ValueError("prior preflight readiness scores are below the hard thresholds")
    prior_artifacts = _required_mapping(
        prior_bom.get("artifacts"),
        "prior_preflight_bom.artifacts",
    )
    expected_inputs = artifact_inventory_snapshots(prior_artifacts)
    actual_prior_inputs = {
        str(label): dict(row)
        for label, row in inputs.items()
        if label != "assembly_bom" and isinstance(row, Mapping)
    }
    if actual_prior_inputs != expected_inputs:
        raise ValueError("prior preflight inputs do not match its bound provisional BOM")
    input_hashes = {
        str(label): str(row.get("sha256"))
        for label, row in inputs.items()
        if isinstance(row, Mapping) and isinstance(row.get("sha256"), str)
    }
    if len(input_hashes) != len(inputs):
        raise ValueError("prior preflight readiness input hashes are invalid")
    outputs = _required_mapping(
        receipt.get("output_artifact_hashes"),
        "preflight_readiness.output_artifact_hashes",
    )
    article_input = _required_mapping(
        inputs.get("article"),
        "prior_preflight_readiness.input_hashes.article",
    )
    if (
        receipt.get("input_artifact_hashes") != input_hashes
        or outputs.get("readiness_output") != file_sha256(path)
        or outputs.get("article") != article_input.get("sha256")
        or receipt.get("run_id") != readiness.get("run_id")
        or receipt.get("started_at") != readiness.get("started_at")
        or receipt.get("completed_at") != readiness.get("completed_at")
    ):
        raise ValueError("preflight readiness stage receipt does not bind its prior result")
    return readiness


__all__ = ['_validate_prior_preflight_readiness', '_validate_provisional_stage_receipts']
