"""Compatibility facade and serial gate runner for publish readiness."""
# ruff: noqa: F403, F405

try:
    from .readiness.common import *  # noqa: F403
    from .readiness.api import *  # noqa: F403
    from .readiness.persistence_api import *  # noqa: F403
    from .readiness.result_validation import *  # noqa: F403
    from .readiness.workspace_bindings import *  # noqa: F403
    from .readiness.runtime_policy import *  # noqa: F403
    from .readiness.reporting import *  # noqa: F403
    from .readiness.adapters import *  # noqa: F403
    from .readiness.pipeline_tail import _run_remaining_gates
except ImportError:  # pragma: no cover - direct script compatibility.
    from readiness.common import *  # noqa: F403
    from readiness.api import *  # noqa: F403
    from readiness.persistence_api import *  # noqa: F403
    from readiness.result_validation import *  # noqa: F403
    from readiness.workspace_bindings import *  # noqa: F403
    from readiness.runtime_policy import *  # noqa: F403
    from readiness.reporting import *  # noqa: F403
    from readiness.adapters import *  # noqa: F403
    from readiness.pipeline_tail import _run_remaining_gates

ContentScorer = _DIRECT_DEFAULTS["ContentScorer"]
LandingPageScorer = _DIRECT_DEFAULTS["LandingPageScorer"]
ReadinessTelemetry = _DIRECT_DEFAULTS["ReadinessTelemetry"]
SimproVaultClient = _DIRECT_DEFAULTS["SimproVaultClient"]
build_stage_receipt = _DIRECT_DEFAULTS["build_stage_receipt"]
load_validated_claim_set = _DIRECT_DEFAULTS["load_validated_claim_set"]
read_publishable_markdown = _DIRECT_DEFAULTS["read_publishable_markdown"]
validate_file_urls = _DIRECT_DEFAULTS["validate_file_urls"]
write_stage_receipt = _DIRECT_DEFAULTS["write_stage_receipt"]


def _read_article_snapshot(
    article_path: Path,
    session: ValidationSession | None,
) -> tuple[Any | None, FrontmatterError | None]:
    try:
        snapshot = session.inputs.snapshot("article") if session is not None else None
        article = (
            parse_publishable_markdown(
                article_path,
                session.inputs.text("article"),
                sha256=snapshot.sha256,
            )
            if session is not None and snapshot is not None
            else read_publishable_markdown(article_path)
        )
        return article, None
    except FrontmatterError as error:
        return None, error


def _resolve_artifact_kind_value(
    article_content: str,
    article_path: Path,
    requested: str | None,
) -> tuple[str | None, ValueError | None]:
    try:
        detected = context_binding_guard.require_artifact_kind(
            article_content,
            article_path=article_path,
        )
        if requested not in {None, "blog", "landing_page"}:
            raise ValueError("artifact_kind must be blog or landing_page")
        if requested == "blog" and detected != "blog":
            raise ValueError("artifact_kind does not match the article")
        return requested or detected, None
    except ValueError as error:
        return None, error


def _artifact_kind_rule_id(message: str) -> str:
    normalized = message.casefold()
    if "unsupported" in normalized:
        return "artifact_kind_unsupported"
    if "conflict" in normalized:
        return "artifact_kind_conflict"
    return "artifact_kind_missing"


def _failure_gate(
    name: str,
    label: str,
    *,
    rule_id: str,
    message: str,
    suggestion: str,
) -> GateResult:
    return _gate_from_findings(name, label, [{
        "rule_id": rule_id,
        "severity": "error",
        "line": 1,
        "column": 1,
        "message": message,
        "suggestion": suggestion,
    }])


def _blocked_for_gate(
    gate: GateResult,
    *,
    phase: str,
    article_path: Path,
    paths: Mapping[str, str | None],
    artifact_kind: str | None,
    gates: List[GateResult],
    score_threshold: int,
) -> ReadinessResult:
    return _blocked_readiness_result(
        phase=phase,
        article_path=article_path,
        proof_sidecar_path=paths["proof_sidecar"],
        context_request_path=paths["context_request"],
        context_pack_path=paths["context_pack"],
        context_receipt_path=paths["context_receipt"],
        assembly_bom_path=paths["assembly_bom"],
        artifact_kind=artifact_kind,
        gates=gates,
        score_threshold=score_threshold,
        gate=gate,
    )


def _run_context_gate(
    *,
    article_path: Path,
    article_content: str,
    paths: Mapping[str, str | None],
    runtime_policy: Mapping[str, Any],
    vault_root: str | Path | None,
    session: ValidationSession | None,
    telemetry: ReadinessTelemetry | None,
) -> tuple[Any, GateResult]:
    connector_required = context_binding_guard.requires_context(article_content) or any(
        paths[name] is not None
        for name in ("context_request", "context_pack", "context_receipt")
    )
    client = session.connector() if session is not None and connector_required else None
    if client is not None and session is not None and session.telemetry is not None:
        session.telemetry.increment("connector_operations")
    result = _timed_call(
        telemetry,
        "gate.context_binding",
        context_binding_guard.validate_context_artifacts,
        str(article_path),
        fail_on="error",
        proof_sidecar=paths["proof_sidecar"],
        context_request=paths["context_request"],
        context_pack=paths["context_pack"],
        context_receipt=paths["context_receipt"],
        editorial_plan=runtime_policy.get("editorial_plan"),
        vault_root=vault_root,
        client=client,
    )
    if session is not None:
        session.set_context_result(result)
        session.record_findings("context_binding", result.findings)
    return result, _gate_from_findings(
        "context_binding", "Context Binding", list(result.findings)
    )


def _validate_bom_and_capture_hashes(
    *,
    article_path: Path,
    artifact_kind: str,
    paths: Mapping[str, str | None],
    phase: str,
    readiness_root: Path,
    context_result: Any,
    vault_root: str | Path | None,
    session: ValidationSession | None,
    input_capture_error: ValueError | None,
    telemetry: ReadinessTelemetry | None,
    gates: List[GateResult],
    score_threshold: int,
) -> tuple[ReadinessResult | None, Dict[str, Dict[str, str]] | None]:
    bom_path = paths["assembly_bom"]
    if artifact_kind == "blog" and bom_path is None:
        gate = _gate_from_findings(
            "blog_assembly_bom",
            "Blog Assembly BOM",
            [blog_assembly_bom_guard.missing_bom_finding()],
        )
        gates.append(gate)
        return _blocked_for_gate(
            gate,
            phase=phase,
            article_path=article_path,
            paths=paths,
            artifact_kind=artifact_kind,
            gates=gates,
            score_threshold=score_threshold,
        ), None
    if bom_path is None:
        return None, None
    gate = _gate_from_findings(
        "blog_assembly_bom",
        "Blog Assembly BOM",
        _timed_call(
            telemetry,
            "gate.blog_assembly_bom",
            blog_assembly_bom_guard.check_bom_file,
            bom_path,
            article_path=article_path,
            validation_sidecar_path=paths["proof_sidecar"] or "",
            context_request_path=paths["context_request"],
            context_pack_path=paths["context_pack"],
            context_receipt_path=paths["context_receipt"],
            workspace_root=readiness_root,
            expected_lifecycle_state="provisional" if phase == "preflight" else "final",
            require_current_schema=True,
            context_result=context_result,
            vault_root=vault_root,
        ),
    )
    gates.append(gate)
    if not gate["passed"]:
        return _blocked_for_gate(
            gate,
            phase=phase,
            article_path=article_path,
            paths=paths,
            artifact_kind=artifact_kind,
            gates=gates,
            score_threshold=score_threshold,
        ), None
    try:
        if input_capture_error is not None:
            raise input_capture_error
        if session is None:
            raise ValueError("readiness input snapshot is unavailable")
        return None, session.inputs.hash_inventory()
    except ValueError as error:
        seal_gate = _failure_gate(
            "input_seal",
            "Input Seal",
            rule_id="readiness_input_snapshot_invalid",
            message=str(error),
            suggestion="Regenerate the BOM from unchanged current artifacts.",
        )
        gates.append(seal_gate)
        return _blocked_for_gate(
            seal_gate,
            phase=phase,
            article_path=article_path,
            paths=paths,
            artifact_kind=artifact_kind,
            gates=gates,
            score_threshold=score_threshold,
        ), None


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
    paths = {
        "proof_sidecar": str(proof_sidecar) if proof_sidecar is not None else None,
        "context_request": str(context_request) if context_request is not None else None,
        "context_pack": str(context_pack) if context_pack is not None else None,
        "context_receipt": str(context_receipt) if context_receipt is not None else None,
        "assembly_bom": str(assembly_bom) if assembly_bom is not None else None,
    }
    readiness_root = Path(workspace_root).resolve()
    article, article_error = _read_article_snapshot(article_path, session)
    if article_error is not None:
        gate = _failure_gate(
            "frontmatter_metadata",
            "Frontmatter Metadata",
            rule_id="frontmatter_invalid",
            message=str(article_error),
            suggestion="Repair the YAML frontmatter before publishing.",
        )
        return _blocked_for_gate(
            gate,
            phase=phase,
            article_path=article_path,
            paths=paths,
            artifact_kind=None,
            gates=[gate],
            score_threshold=85,
        )
    assert article is not None
    article_content = article.raw
    resolved_kind, kind_error = _resolve_artifact_kind_value(
        article_content, article_path, artifact_kind
    )
    if kind_error is not None:
        message = str(kind_error)
        gate = _failure_gate(
            "artifact_identity",
            "Artifact Identity",
            rule_id=_artifact_kind_rule_id(message),
            message=message,
            suggestion="Declare one supported artifact_type in frontmatter.",
        )
        return _blocked_for_gate(
            gate,
            phase=phase,
            article_path=article_path,
            paths=paths,
            artifact_kind=None,
            gates=[gate],
            score_threshold=85,
        )
    assert resolved_kind is not None
    artifact_kind = resolved_kind
    proof_sidecar_path = paths["proof_sidecar"]
    context_request_path = paths["context_request"]
    context_pack_path = paths["context_pack"]
    context_receipt_path = paths["context_receipt"]
    assembly_bom_path = paths["assembly_bom"]
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
        return _blocked_for_gate(
            identity_gate,
            phase=phase,
            article_path=article_path,
            paths=paths,
            artifact_kind=artifact_kind,
            gates=gates,
            score_threshold=score_threshold,
        )

    context_result, context_gate = _run_context_gate(
        article_path=article_path,
        article_content=article_content,
        paths=paths,
        runtime_policy=runtime_policy,
        vault_root=vault_root,
        session=session,
        telemetry=telemetry,
    )
    gates.append(context_gate)
    if not context_gate["passed"]:
        return _blocked_for_gate(
            context_gate,
            phase=phase,
            article_path=article_path,
            paths=paths,
            artifact_kind=artifact_kind,
            gates=gates,
            score_threshold=score_threshold,
        )

    sealed_inputs = session.inputs if session is not None else None
    blocked, sealed_input_hashes = _validate_bom_and_capture_hashes(
        article_path=article_path,
        artifact_kind=artifact_kind,
        paths=paths,
        phase=phase,
        readiness_root=readiness_root,
        context_result=context_result,
        vault_root=vault_root,
        session=session,
        input_capture_error=input_capture_error,
        telemetry=telemetry,
        gates=gates,
        score_threshold=score_threshold,
    )
    if blocked is not None:
        return blocked

    return _run_remaining_gates(
        run_started_at=run_started_at,
        article_path=article_path,
        article=article,
        article_content=article_content,
        proof_sidecar_path=proof_sidecar_path,
        context_request_path=context_request_path,
        context_pack_path=context_pack_path,
        context_receipt_path=context_receipt_path,
        assembly_bom_path=assembly_bom_path,
        vault_root=vault_root,
        ai_profile=ai_profile,
        phase=phase,
        workspace_root=workspace_root,
        readiness_root=readiness_root,
        artifact_kind=artifact_kind,
        score_threshold=score_threshold,
        gates=gates,
        runtime_policy=runtime_policy,
        session=session,
        sealed_inputs=sealed_inputs,
        sealed_input_hashes=sealed_input_hashes,
        input_capture_error=input_capture_error,
        telemetry=telemetry,
    )


if __name__ == "__main__":
    raise SystemExit(main())
