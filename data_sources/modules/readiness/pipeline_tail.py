"""Article gates, scoring, and final input sealing."""
# ruff: noqa: F403, F405

from .common import *  # noqa: F403


def _missing_gate_finding(rule_id: str, message: str, suggestion: str) -> List[Dict[str, Any]]:
    return [{
        "rule_id": rule_id,
        "severity": "error",
        "line": 1,
        "column": 1,
        "message": message,
        "suggestion": suggestion,
    }]


def _skip_article_gate(
    name: str,
    *,
    visible_faq: bool,
    simpro_context_required: bool,
) -> bool:
    faq_skipped = name in {"faq_answer_quality", "faq_proof"} and not visible_faq
    context_skipped = name in SIMPRO_CONTEXT_GATE_NAMES and not simpro_context_required
    fred_skipped = name == "fred_authority" and not simpro_context_required
    return faq_skipped or context_skipped or fred_skipped


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
    telemetry: ReadinessTelemetry | None,
) -> List[Dict[str, Any]]:
    editorial_path = runtime_policy.get("editorial_plan")
    if not editorial_path:
        return _missing_gate_finding(
            "editorial_plan_missing",
            "Blog readiness requires a bound editorial plan.",
            "Regenerate the provisional BOM with --editorial-plan.",
        )
    return _timed_call(
        telemetry,
        "gate.editorial_plan",
        guard_module.check_file,
        editorial_path,
        article_path=article_path,
        serp_evidence_path=runtime_policy.get("serp_evidence"),
        assembly_date=runtime_policy.get("assembly_date"),
        expected_run_id=runtime_policy.get("run_id"),
    )


def _run_keyword_gate(
    guard_module: Any,
    *,
    article_path: Path,
    runtime_policy: Mapping[str, Any],
    telemetry: ReadinessTelemetry | None,
) -> List[Dict[str, Any]]:
    keyword_path = runtime_policy.get("keyword_decision")
    editorial_path = runtime_policy.get("editorial_plan")
    if not keyword_path or not editorial_path:
        return _missing_gate_finding(
            "semrush_keyword_decision_missing",
            "Blog readiness requires a bound Semrush keyword decision.",
            "Regenerate the provisional BOM with --keyword-decision.",
        )
    return _timed_call(
        telemetry,
        "gate.semrush_keyword_decision",
        guard_module.check_file,
        keyword_path,
        article_path=article_path,
        editorial_plan_path=editorial_path,
        assembly_date=runtime_policy.get("assembly_date"),
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
            telemetry=telemetry,
        )
    if name == "semrush_keyword_decision":
        return _run_keyword_gate(
            guard_module,
            article_path=article_path,
            runtime_policy=runtime_policy,
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
    try:
        if input_capture_error is not None:
            raise input_capture_error
        if sealed_inputs is None:
            raise ValueError("readiness input snapshot is unavailable")
        sealed_inputs.reseal()
        current_hashes = sealed_inputs.hash_inventory()
        changed = artifact_kind == "blog" and current_hashes != sealed_input_hashes
        if not changed:
            return current_hashes, []
        message = "One or more bound artifacts changed during readiness."
    except ValueError as error:
        current_hashes = sealed_input_hashes or {}
        message = str(error)
    return current_hashes, _missing_gate_finding(
        "readiness_inputs_changed_during_run",
        message,
        "Resume at the mutation receipt, then rerun scrub, Context Binding, BOM build, and readiness.",
    )


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
            transport=session.transport() if session is not None else None,
        )
        if sealed_inputs is not None
        else None
    )
    prevalidated_gate_findings: Dict[
        str,
        tuple[Mapping[str, Any], ...],
    ] = {}
    for name, label, guard_module in ARTICLE_GATES:
        if _skip_article_gate(
            name,
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
                ),
            ]
        prevalidated_gate_findings[name] = _record_gate_findings(session, name, findings)
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
