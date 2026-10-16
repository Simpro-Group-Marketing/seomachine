"""Serial gate runner for landing-page publish readiness."""

from pathlib import Path
from typing import Any, List, Mapping

from .adapters import (
    _blocked_readiness_result,
    _gate_from_findings,
    _timed_call,
)
from .common import (
    FrontmatterError,
    GateResult,
    LANDING_PAGE_SCORE_THRESHOLD,
    ReadinessResult,
    ReadinessTelemetry,
    ValidationSession,
    blog_identity_guard,
    context_binding_guard,
    parse_publishable_markdown,
)
from .finalization import _utc_now, finalize_blocked_result
from .gate_policy import RETIRED_BLOG_READINESS
from .gate_policy import artifact_kind_rule_id as _artifact_kind_rule_id
from .pipeline_tail import _run_remaining_gates
from .workspace_bindings import (
    _captured_context_payloads,
    _captured_proof_content,
)


def _read_article_snapshot(
    article_path: Path,
    session: ValidationSession,
) -> tuple[Any | None, FrontmatterError | None]:
    try:
        article = parse_publishable_markdown(
            article_path,
            session.inputs.text("article"),
            sha256=session.inputs.snapshot("article").sha256,
        )
        return article, None
    except ValueError as error:
        return None, error if isinstance(error, FrontmatterError) else FrontmatterError(str(error))


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
        if "blog" in (requested, detected):
            raise ValueError(RETIRED_BLOG_READINESS)
        return requested or detected, None
    except ValueError as error:
        return None, error


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
) -> ReadinessResult:
    return _blocked_readiness_result(
        phase=phase,
        article_path=article_path,
        proof_sidecar_path=paths["proof_sidecar"],
        context_request_path=paths["context_request"],
        context_pack_path=paths["context_pack"],
        context_receipt_path=paths["context_receipt"],
        artifact_kind=artifact_kind,
        gates=gates,
        score_threshold=LANDING_PAGE_SCORE_THRESHOLD,
        gate=gate,
    )


def _sealed_blocked_result(
    result: ReadinessResult,
    *,
    session: ValidationSession,
    input_capture_error: ValueError | None,
) -> ReadinessResult:
    return finalize_blocked_result(
        result,
        inputs=session.inputs,
        capture_error=input_capture_error,
    )


def _run_context_gate(
    *,
    article_path: Path,
    article_content: str,
    paths: Mapping[str, str | None],
    vault_root: str | Path | None,
    session: ValidationSession,
    telemetry: ReadinessTelemetry | None,
) -> GateResult:
    connector_required = context_binding_guard.requires_context(article_content) or any(
        paths[name] is not None
        for name in ("context_request", "context_pack", "context_receipt")
    )
    client = session.connector() if connector_required else None
    if client is not None and session.telemetry is not None:
        session.telemetry.increment("connector_operations")
    inputs = session.inputs
    result = _timed_call(
        telemetry,
        "gate.context_binding",
        context_binding_guard.validate_context_payloads,
        article_content=article_content,
        article_path=article_path,
        article_sha256=inputs.snapshot("article").sha256,
        proof_content=_captured_proof_content(
            inputs,
            proof_sidecar_path=paths["proof_sidecar"],
        ),
        **_captured_context_payloads(inputs),
        vault_root=vault_root,
        client=client,
    )
    session.set_context_result(result)
    session.record_findings("context_binding", result.findings)
    return _gate_from_findings("context_binding", "Context Binding", list(result.findings))


def _run_publish_readiness(
    file_path: str | Path,
    *,
    proof_sidecar: str | Path | None = None,
    context_request: str | Path | None = None,
    context_pack: str | Path | None = None,
    context_receipt: str | Path | None = None,
    vault_root: str | Path | None = None,
    ai_profile: str = "simpro-web",
    phase: str = "preflight",
    workspace_root: str | Path,
    artifact_kind: str | None = None,
    run_id: str | None = None,
    session: ValidationSession,
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
    }
    article, article_error = _read_article_snapshot(article_path, session)
    if article_error is not None:
        gate = _failure_gate(
            "frontmatter_metadata",
            "Frontmatter Metadata",
            rule_id="frontmatter_invalid",
            message=str(article_error),
            suggestion="Repair the YAML frontmatter before publishing.",
        )
        return _sealed_blocked_result(
            _blocked_for_gate(
                gate,
                phase=phase,
                article_path=article_path,
                paths=paths,
                artifact_kind=None,
                gates=[gate],
            ),
            session=session,
            input_capture_error=input_capture_error,
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
            suggestion=(
                "Release blogs with /publish-readiness."
                if message == RETIRED_BLOG_READINESS
                else "Declare one supported artifact_type in frontmatter."
            ),
        )
        return _sealed_blocked_result(
            _blocked_for_gate(
                gate,
                phase=phase,
                article_path=article_path,
                paths=paths,
                artifact_kind=None,
                gates=[gate],
            ),
            session=session,
            input_capture_error=input_capture_error,
        )
    assert resolved_kind is not None
    artifact_kind = resolved_kind
    proof_sidecar_path = paths["proof_sidecar"]
    context_request_path = paths["context_request"]
    context_pack_path = paths["context_pack"]
    context_receipt_path = paths["context_receipt"]
    gates: List[GateResult] = []
    identity_gate = _gate_from_findings(
        "artifact_identity",
        "Artifact Identity",
        _timed_call(
            telemetry,
            "gate.artifact_identity",
            blog_identity_guard.check_article,
            article_content,
        ),
    )
    gates.append(identity_gate)
    if not identity_gate["passed"]:
        return _sealed_blocked_result(
            _blocked_for_gate(
                identity_gate,
                phase=phase,
                article_path=article_path,
                paths=paths,
                artifact_kind=artifact_kind,
                gates=gates,
            ),
            session=session,
            input_capture_error=input_capture_error,
        )

    context_gate = _run_context_gate(
        article_path=article_path,
        article_content=article_content,
        paths=paths,
        vault_root=vault_root,
        session=session,
        telemetry=telemetry,
    )
    gates.append(context_gate)
    if not context_gate["passed"]:
        return _sealed_blocked_result(
            _blocked_for_gate(
                context_gate,
                phase=phase,
                article_path=article_path,
                paths=paths,
                artifact_kind=artifact_kind,
                gates=gates,
            ),
            session=session,
            input_capture_error=input_capture_error,
        )

    return _run_remaining_gates(
        run_started_at=run_started_at,
        article_path=article_path,
        article=article,
        article_content=article_content,
        proof_sidecar_path=proof_sidecar_path,
        context_request_path=context_request_path,
        context_pack_path=context_pack_path,
        context_receipt_path=context_receipt_path,
        vault_root=vault_root,
        ai_profile=ai_profile,
        phase=phase,
        workspace_root=workspace_root,
        artifact_kind=artifact_kind,
        gates=gates,
        session=session,
        input_capture_error=input_capture_error,
        telemetry=telemetry,
        run_id=run_id,
    )
