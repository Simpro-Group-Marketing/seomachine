"""Article gates, scoring, and final input sealing."""
from pathlib import Path
from typing import Any, Dict, List, Mapping, Sequence

from .adapters import (
    _blocked_readiness_result,
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
    CONTENT_GATE_NAMES,
    ContentGateInputs,
    GateResult,
    ReadinessInputs,
    ReadinessResult,
    ReadinessTelemetry,
    UrlValidator,
    ValidationSession,
    _issue_readiness_gate_context,
    ai_copy_linter,
    chrome_review_evidence,
    context_binding_guard,
    file_sha256,
    order_blog_gate_results,
    public_artifact_guard,
    public_research_link_guard,
    run_content_gate,
)
from .runtime_policy import _no_fit_customer_proof_findings
from .workspace_bindings import _captured_proof_content, _readiness_run_id
from .gate_policy import (
    missing_gate_finding as _missing_gate_finding,
    skip_article_gate as _skip_article_gate,
)
try:
    from ..url_validator import validate_content_urls
except ImportError:  # pragma: no cover - direct script compatibility.
    from url_validator import validate_content_urls

from .finalization import _utc_now, finalize_blocked_result, reseal_readiness_inputs
from .snapshot_gates import (
    run_editorial_plan_gate,
    run_keyword_gate,
    source_registry_state,
)


def _guard_kwargs(
    name: str,
    *,
    proof_sidecar_path: str | None,
    context_pack_path: str | None,
    context_receipt_path: str | None,
    vault_root: str | Path | None,
    validated_claim_set: Any,
    runtime_policy: Mapping[str, Any],
) -> Dict[str, Any]:
    kwargs: Dict[str, Any] = {
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
        kwargs.update({
            "context_pack": context_pack_path,
            "context_receipt": context_receipt_path,
        })
    if name in {"named_feature_status", "competitive_shortlist", "fred_authority"}:
        kwargs["vault_root"] = vault_root
        kwargs["validated_claim_set"] = validated_claim_set
    if name == "eeat_strength":
        kwargs.update({
            "editorial_plan": runtime_policy.get("editorial_plan"),
            "customer_proof_selector_evidence": runtime_policy.get(
                "customer_proof_selector_evidence"
            ),
            "fred_authority_evidence": runtime_policy.get("fred_authority_evidence"),
        })
    if name == "industry_cluster_link_policy":
        kwargs["editorial_plan"] = runtime_policy.get("editorial_plan")
    if name == "paa_provenance":
        kwargs.update(runtime_policy["paa_kwargs"])
    return kwargs


def _run_editorial_plan_gate(
    guard_module: Any,
    *,
    article_path: Path,
    runtime_policy: Mapping[str, Any],
    content_gate_inputs: ContentGateInputs | None,
    telemetry: ReadinessTelemetry | None,
) -> List[Dict[str, Any]]:
    return run_editorial_plan_gate(
        guard_module,
        article_path=article_path,
        runtime_policy=runtime_policy,
        content_gate_inputs=content_gate_inputs,
        telemetry=telemetry,
        timed_call=_timed_call,
        missing_finding=_missing_gate_finding,
    )


def _run_keyword_gate(
    guard_module: Any,
    *,
    article_path: Path,
    runtime_policy: Mapping[str, Any],
    content_gate_inputs: ContentGateInputs | None,
    telemetry: ReadinessTelemetry | None,
) -> List[Dict[str, Any]]:
    return run_keyword_gate(
        guard_module,
        article_path=article_path,
        runtime_policy=runtime_policy,
        content_gate_inputs=content_gate_inputs,
        telemetry=telemetry,
        timed_call=_timed_call,
        missing_finding=_missing_gate_finding,
    )


def _execute_article_gate(
    name: str,
    guard_module: Any,
    *,
    article_path: Path,
    content_gate_inputs: ContentGateInputs | None,
    runtime_policy: Mapping[str, Any],
    guard_kwargs: Mapping[str, Any],
    telemetry: ReadinessTelemetry | None,
) -> List[Dict[str, Any]]:
    if name in CONTENT_GATE_NAMES and content_gate_inputs is not None:
        return _timed_call(
            telemetry, f"gate.{name}", run_content_gate, name, guard_module, content_gate_inputs
        )
    if name == "editorial_plan":
        return _run_editorial_plan_gate(
            guard_module,
            article_path=article_path,
            runtime_policy=runtime_policy,
            content_gate_inputs=content_gate_inputs,
            telemetry=telemetry,
        )
    if name == "semrush_keyword_decision":
        return _run_keyword_gate(
            guard_module,
            article_path=article_path,
            runtime_policy=runtime_policy,
            content_gate_inputs=content_gate_inputs,
            telemetry=telemetry,
        )
    return _timed_call(
        telemetry,
        f"gate.{name}",
        guard_module.check_file,
        str(article_path),
        **guard_kwargs,
    )


def _record_gate_findings(
    session: ValidationSession | None,
    name: str,
    findings: Sequence[Mapping[str, Any]],
) -> tuple[Mapping[str, Any], ...]:
    if session is None:
        return tuple(dict(finding) for finding in findings)
    session.record_findings(name, findings)
    return tuple(session.findings(name) or [])


def _reseal_inputs(
    *,
    artifact_kind: str,
    sealed_inputs: ReadinessInputs | None,
    sealed_input_hashes: Dict[str, Dict[str, str]] | None,
    input_capture_error: ValueError | None,
) -> tuple[Dict[str, Dict[str, str]], List[Dict[str, Any]]]:
    current_hashes, findings = reseal_readiness_inputs(
        sealed_inputs,
        capture_error=input_capture_error,
    )
    if not findings and artifact_kind == "blog" and current_hashes != sealed_input_hashes:
        return current_hashes, _missing_gate_finding(
            "readiness_inputs_changed_during_run",
            "One or more bound artifacts changed during readiness.",
            "Resume at the mutation receipt, then rerun scrub, Context Binding, BOM build, and readiness.",
        )
    return current_hashes, findings


def _order_final_gates(
    gates: List[GateResult],
    *,
    artifact_kind: str,
    seal_findings: Sequence[Mapping[str, Any]],
    runtime_policy: Mapping[str, Any],
    simpro_context_required: bool,
) -> List[GateResult]:
    if artifact_kind != "blog":
        return gates
    gates.append(_gate_from_findings("input_seal", "Input Seal", seal_findings))
    try:
        return [
            dict(row)
            for row in order_blog_gate_results(
                gates,
                visible_faq=bool(runtime_policy["visible_faq"]),
                connector_required=simpro_context_required,
                current_strategy=bool(runtime_policy.get("current_strategy")),
            )
        ]
    except ValueError:
        gates.append(_gate_from_findings(
            "readiness_contract",
            "Readiness Contract",
            _missing_gate_finding(
                "readiness_gate_inventory_invalid",
                "Readiness gate order drifted from the closed blog contract.",
                "Restore the expected conditional gate inventory before sealing.",
            ),
        ))
        return gates


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
    assembly_bom_path: str | None,
    vault_root: str | Path | None,
    ai_profile: str,
    phase: str,
    workspace_root: str | Path,
    readiness_root: Path,
    artifact_kind: str,
    score_threshold: int,
    gates: List[GateResult],
    runtime_policy: Mapping[str, Any],
    session: ValidationSession | None,
    sealed_inputs: ReadinessInputs | None,
    sealed_input_hashes: Dict[str, Dict[str, str]] | None,
    input_capture_error: ValueError | None,
    telemetry: ReadinessTelemetry | None,
    run_id: str | None,
) -> ReadinessResult:
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
        validator=UrlValidator(transport=session.transport()) if session is not None else None,
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
                public_research_link_guard.check_content,
                article_content,
                proof_content=_captured_proof_content(
                    sealed_inputs,
                    proof_sidecar_path=proof_sidecar_path,
                ),
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
            transport=session.transport() if session is not None else None,
            normalize_source=(
                session.normalized_source if session is not None else None
            ),
            registry_state=source_registry_state(session, sealed_inputs),
            url_summary=url_summary,
        )
        if sealed_inputs is not None
        else None
    )
    prevalidated_gate_findings: Dict[
        str,
        tuple[Mapping[str, Any], ...],
    ] = {}
    for name, label, guard_module in ARTICLE_GATES:
        if name in {"blog_strategy", "schema_handoff"} and not runtime_policy.get(
            "current_strategy"
        ):
            continue
        if _skip_article_gate(
            name,
            artifact_kind=artifact_kind,
            visible_faq=bool(runtime_policy["visible_faq"]),
            simpro_context_required=simpro_context_required,
        ):
            continue
        findings = _execute_article_gate(
            name,
            guard_module,
            article_path=article_path,
            content_gate_inputs=content_gate_inputs,
            runtime_policy=runtime_policy,
            guard_kwargs=_guard_kwargs(
                name,
                proof_sidecar_path=proof_sidecar_path,
                context_pack_path=context_pack_path,
                context_receipt_path=context_receipt_path,
                vault_root=vault_root,
                validated_claim_set=validated_claim_set,
                runtime_policy=runtime_policy,
            ),
            telemetry=telemetry,
        )
        if name == "customer_proof_diversity":
            findings = [
                *findings,
                *_no_fit_customer_proof_findings(
                    article_content,
                    runtime_policy=runtime_policy,
                    inputs=sealed_inputs,
                ),
            ]
        prevalidated_gate_findings[name] = _record_gate_findings(session, name, findings)
        gate = _gate_from_findings(name, label, findings)
        gates.append(gate)
        if name == "semrush_keyword_decision" and not gate["passed"]:
            blocked = _blocked_readiness_result(
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
            return finalize_blocked_result(
                blocked,
                inputs=sealed_inputs,
                capture_error=input_capture_error,
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
        article_content=article_content,
        article=article,
        proof_content=proof_sidecar_content,
        artifact_kind=artifact_kind or "blog",
        assembly_bom=assembly_bom_path,
        runtime_policy=runtime_policy,
        workspace_root=readiness_root,
        readiness_gate_context=readiness_gate_context,
    )
    gates.append(_gate_from_score(scorer_result))

    current_input_hashes, seal_findings = _reseal_inputs(
        artifact_kind=artifact_kind,
        sealed_inputs=sealed_inputs,
        sealed_input_hashes=sealed_input_hashes,
        input_capture_error=input_capture_error,
    )
    gates = _order_final_gates(
        gates,
        artifact_kind=artifact_kind,
        seal_findings=seal_findings,
        runtime_policy=runtime_policy,
        simpro_context_required=simpro_context_required,
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
        "run_id": run_id or _readiness_run_id(assembly_bom_path, article.sha256),
        "started_at": run_started_at,
        "completed_at": _utc_now(),
    }
    if phase == "final" and assembly_bom_path:
        result["final_bom_sha256"] = file_sha256(assembly_bom_path)
    return result


__all__ = ["_run_remaining_gates"]
