"""Landing-page article gates, scoring, and final input sealing."""
from pathlib import Path
from typing import Any, List

from .adapters import (
    _content_score,
    _gate_from_findings,
    _gate_from_score,
    _gate_from_url_summary,
    _score_content,
    _scorecard_from_scorer_result,
    _timed_call,
)
from .common import (
    ARTICLE_GATES,
    ContentGateInputs,
    GateResult,
    ReadinessResult,
    ReadinessTelemetry,
    UrlValidator,
    ValidationSession,
    ai_copy_linter,
    chrome_review_evidence,
    context_binding_guard,
    public_artifact_guard,
    public_research_link_guard,
    run_content_gate,
)
from .workspace_bindings import _captured_proof_content, _readiness_run_id
from .gate_policy import skip_article_gate as _skip_article_gate
try:
    from ..url_validator import validate_content_urls
except ImportError:  # pragma: no cover - direct script compatibility.
    from url_validator import validate_content_urls

from .finalization import _utc_now, reseal_readiness_inputs
from .snapshot_gates import source_registry_state


def _run_remaining_gates(
    *,
    run_started_at: str,
    article_path: Path,
    article: Any,
    article_content: str,
    proof_sidecar_path: str | None,
    context_request_path: str | None,
    context_pack_path: str | None,
    context_receipt_path: str | None,
    vault_root: str | Path | None,
    ai_profile: str,
    phase: str,
    workspace_root: str | Path,
    artifact_kind: str,
    gates: List[GateResult],
    session: ValidationSession,
    input_capture_error: ValueError | None,
    telemetry: ReadinessTelemetry | None,
    run_id: str | None,
) -> ReadinessResult:
    sealed_inputs = session.inputs
    gates.append(
        _gate_from_findings(
            "public_artifact",
            "Public Artifact",
            _timed_call(
                telemetry,
                "gate.public_artifact",
                public_artifact_guard.check_content,
                article_content,
            ),
        )
    )

    ai_findings = _timed_call(
        telemetry,
        "gate.ai_copy_linter",
        ai_copy_linter.lint_content,
        article_content,
        profile=ai_profile,
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
        validate_content_urls,
        article_content,
        validator=UrlValidator(transport=session.transport()),
    )
    url_summary = chrome_review_evidence.apply_chrome_review_evidence_fallbacks(
        url_summary,
        proof_sidecar=proof_sidecar_path,
        workspace_root=workspace_root,
    )
    gates.append(_gate_from_url_summary(url_summary))

    proof_sidecar_content = _captured_proof_content(
        sealed_inputs,
        proof_sidecar_path=proof_sidecar_path,
    )
    gates.append(
        _gate_from_findings(
            "public_research_links",
            "Public Research Links",
            _timed_call(
                telemetry,
                "gate.public_research_links",
                public_research_link_guard.check_content,
                article_content,
                proof_content=proof_sidecar_content,
                url_summary=url_summary,
            ),
        )
    )

    simpro_context_required = context_binding_guard.requires_context(article_content)
    content_gate_inputs = ContentGateInputs(
        article_content=article_content,
        proof_content=proof_sidecar_content,
        article_path=article_path,
        proof_sidecar_path=proof_sidecar_path,
        context_pack_path=context_pack_path,
        context_receipt_path=context_receipt_path,
        vault_root=vault_root,
        captured=sealed_inputs,
        validated_claim_set=(
            session.validated_claim_set() if simpro_context_required else None
        ),
        transport=session.transport(),
        normalize_source=session.normalized_source,
        registry_state=source_registry_state(session, sealed_inputs),
    )
    for name, label, guard_module in ARTICLE_GATES:
        if _skip_article_gate(name, simpro_context_required=simpro_context_required):
            continue
        findings = _timed_call(
            telemetry, f"gate.{name}", run_content_gate, name, guard_module, content_gate_inputs
        )
        session.record_findings(name, findings)
        gates.append(_gate_from_findings(name, label, findings))

    scorer_result = _timed_call(
        telemetry,
        "gate.content_scorer",
        _score_content,
        article_path,
        article_content=article_content,
        article=article,
    )
    gates.append(_gate_from_score(scorer_result))

    current_input_hashes, seal_findings = reseal_readiness_inputs(
        sealed_inputs,
        capture_error=input_capture_error,
    )

    scorecard = _scorecard_from_scorer_result(scorer_result)
    passed = all(gate["passed"] for gate in gates) and bool(scorecard["passed"])
    return {
        "schema": "simpro-publish-readiness-result/v1",
        "tool": {"name": "publish_readiness", "version": "1.0.0"},
        "phase": phase,
        "verification_scope": "source_artifact",
        "file": str(article_path),
        "proof_sidecar": proof_sidecar_path,
        "context_request": context_request_path,
        "context_pack": context_pack_path,
        "context_receipt": context_receipt_path,
        "passed": passed,
        "artifact_kind": artifact_kind,
        "gates": gates,
        "score": _content_score(scorer_result),
        "score_threshold": scorer_result["threshold"],
        "aeo_geo": scorer_result.get("aeo_geo", {}),
        "scorecard": scorecard,
        "priority_fixes": scorer_result.get("priority_fixes", []),
        "gate_inventory": [gate["name"] for gate in gates],
        "input_hashes": current_input_hashes,
        "input_seal": {
            "status": "verified" if not seal_findings else "failed",
        },
        "run_id": run_id or _readiness_run_id(article.sha256),
        "started_at": run_started_at,
        "completed_at": _utc_now(),
    }


__all__ = ["_run_remaining_gates"]
