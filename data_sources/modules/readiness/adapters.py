"""Publish-readiness adapters responsibilities."""
# ruff: noqa: F403, F405

from .common import *  # noqa: F403


def _reject_telemetry_output_collision(args: argparse.Namespace) -> None:
    root = Path(args.workspace_root).resolve()
    destination = _resolve_workspace_input(
        args.telemetry_output,
        workspace_root=root,
        field="telemetry output",
    )
    candidates = {
        "file": args.file_path,
        "proof_sidecar": args.proof_sidecar,
        "context_request": args.context_request,
        "context_pack": args.context_pack,
        "context_receipt": args.context_receipt,
        "assembly_bom": args.assembly_bom,
        "readiness_output": args.output,
        "stage_receipt_output": args.stage_receipt_output,
    }
    destination_key = os.path.normcase(str(destination))
    for label, value in candidates.items():
        if value is None:
            continue
        candidate = _resolve_workspace_input(value, workspace_root=root, field=label)
        if os.path.normcase(str(candidate)) == destination_key:
            raise ValueError(f"telemetry output cannot overwrite {label}")

def _gate_from_findings(
    name: str,
    label: str,
    findings: List[Dict[str, Any]],
) -> GateResult:
    summary = summarize_findings(findings)
    passed = not should_fail(findings, fail_on="error")
    return {
        "name": name,
        "label": label,
        "passed": passed,
        "errors": summary["error"],
        "warnings": summary["warning"],
        "findings": findings,
        "blockers": _finding_lines(findings) if not passed else [],
    }

def _timed_call(
    telemetry: ReadinessTelemetry | None,
    stage_name: str,
    operation: Any,
    *args: Any,
    **kwargs: Any,
) -> Any:
    if telemetry is None:
        return operation(*args, **kwargs)
    with telemetry.stage(stage_name):
        return operation(*args, **kwargs)

def _blocked_readiness_result(
    *,
    phase: str,
    article_path: Path,
    proof_sidecar_path: str | None,
    context_request_path: str | None,
    context_pack_path: str | None,
    context_receipt_path: str | None,
    assembly_bom_path: str | None,
    artifact_kind: str | None,
    gates: list[GateResult],
    score_threshold: int,
    gate: GateResult,
) -> ReadinessResult:
    return {
        "schema": READINESS_RESULT_SCHEMA,
        "phase": phase,
        "verification_scope": "source_artifact",
        "file": str(article_path),
        "proof_sidecar": proof_sidecar_path,
        "context_request": context_request_path,
        "context_pack": context_pack_path,
        "context_receipt": context_receipt_path,
        "assembly_bom": assembly_bom_path,
        "passed": False,
        "artifact_kind": artifact_kind,
        "gates": gates,
        "score": None,
        "score_threshold": score_threshold,
        "aeo_geo": {"score": None, "threshold": 90, "passed": False},
        "priority_fixes": [
            {
                "dimension": str(gate.get("name") or ""),
                "issue": blocker,
            }
            for blocker in gate.get("blockers", [])
        ],
    }

def _gate_from_url_summary(summary: UrlValidationSummary) -> GateResult:
    blockers = summary.blockers
    return {
        "name": "url_validator",
        "label": "URL Validator",
        "passed": summary.passed,
        "errors": len(blockers),
        "warnings": 0,
        "findings": [
            {
                "rule_id": "url_unresolved",
                "severity": "error",
                "line": result.line,
                "url": result.url,
                "status": result.status,
                "status_code": result.status_code,
                "reason": result.reason,
                "anchor": result.anchor,
            }
            for result in blockers
        ],
        "blockers": [
            _url_blocker_line(result)
            for result in blockers[:3]
        ],
    }

def _gate_from_score(score_result: Dict[str, Any]) -> GateResult:
    passed = bool(score_result.get("passed", False))
    priority_fixes = score_result.get("priority_fixes", [])
    return {
        "name": score_result.get("gate_name", "content_scorer"),
        "label": score_result.get("gate_label", "Content Scorer"),
        "passed": passed,
        "errors": 0 if passed else 1,
        "warnings": len(priority_fixes) if passed else 0,
        "findings": [],
        "blockers": _priority_fix_lines(priority_fixes) if not passed else [],
    }

def _score_content(
    article_path: Path,
    proof_sidecar: Optional[str],
    *,
    artifact_kind: str = "blog",
    assembly_bom: Optional[str] = None,
    runtime_policy: Mapping[str, Any] | None = None,
    workspace_root: str | Path,
    readiness_gate_context: object = None,
) -> Dict[str, Any]:
    content = article_path.read_text(encoding="utf-8")
    if artifact_kind == "landing_page":
        artifact = read_publishable_markdown(article_path)
        page_type = artifact.scalar("page_type").casefold()
        conversion_goal = artifact.scalar("conversion_goal").casefold()
        if page_type not in {"seo", "ppc"} or conversion_goal not in {
            "trial",
            "demo",
            "lead",
        }:
            return {
                "passed": False,
                "content_quality_score": None,
                "threshold": 75,
                "aeo_geo": {
                    "score": None,
                    "threshold": None,
                    "passed": True,
                    "not_applicable": True,
                },
                "priority_fixes": [
                    {
                        "dimension": "landing_page_metadata",
                        "issue": "Landing pages require page_type seo|ppc and conversion_goal trial|demo|lead.",
                    }
                ],
                "gate_name": "landing_page_scorer",
                "gate_label": "Landing Page Scorer",
            }
        result = LandingPageScorer(page_type, conversion_goal).score(
            content,
            meta_title=artifact.scalar("meta_title", "title"),
            meta_description=artifact.scalar("meta_description"),
            primary_keyword=artifact.scalar("primary_keyword", "target_keyword"),
        )
        issues = [
            {"dimension": "landing_page", "issue": str(issue)}
            for issue in result.get("critical_issues", [])
        ]
        if not issues and not result.get("publishing_ready"):
            issues = [
                {"dimension": "landing_page", "issue": str(issue)}
                for issue in result.get("suggestions", [])[:5]
            ]
        return {
            "passed": bool(result.get("publishing_ready")),
            "content_quality_score": result.get("overall_score"),
            "threshold": 75,
            "aeo_geo": {
                "score": None,
                "threshold": None,
                "passed": True,
                "not_applicable": True,
            },
            "priority_fixes": issues,
            "gate_name": "landing_page_scorer",
            "gate_label": "Landing Page Scorer",
            "landing_page": result,
        }
    scorer = ContentScorer()
    policy = dict(runtime_policy or {})
    if assembly_bom and not policy:
        policy = _bom_runtime_policy(
            assembly_bom,
            workspace_root=workspace_root,
        )
    raw_metadata = policy.get("scoring_metadata")
    metadata = dict(raw_metadata) if isinstance(raw_metadata, Mapping) else {}
    metadata["faq_policy_status"] = str(policy.get("faq_policy_status") or "")
    raw_paa = policy.get("paa_kwargs")
    paa = dict(raw_paa) if isinstance(raw_paa, Mapping) else {}
    return scorer.score(
        content,
        metadata=metadata,
        validate_urls=False,
        validate_source_support=False,
        source_path=str(article_path),
        proof_sidecar=proof_sidecar,
        finalized_bom=(
            policy.get("assembly_bom")
            if isinstance(policy.get("assembly_bom"), Mapping)
            else None
        ),
        assembly_date=str(policy.get("assembly_date") or "") or None,
        paa_workflow_mode=str(paa.get("workflow_mode") or "") or None,
        paa_content_brief=str(paa.get("content_brief") or "") or None,
        paa_answersocrates_blocker=(
            str(paa.get("answersocrates_blocker") or "") or None
        ),
        paa_expected_query=str(paa.get("expected_query") or "") or None,
        paa_expected_collection_date=(
            str(paa.get("expected_collection_date") or "") or None
        ),
        paa_expected_run_id=str(paa.get("expected_run_id") or "") or None,
        paa_artifact=str(paa.get("paa_artifact") or "") or None,
        readiness_gate_context=readiness_gate_context,
    )

def _content_score(score_result: Dict[str, Any]) -> Any:
    return score_result.get("content_quality_score", score_result.get("composite_score"))


def _content_scorecard_gate(
    score_result: Mapping[str, Any],
    source: Mapping[str, Any],
    artifact_kind: str,
) -> Dict[str, Any]:
    threshold = source.get("threshold", score_result.get("threshold"))
    if not _is_number(threshold):
        threshold = 75 if artifact_kind == "landing_page" else 85
    score = source.get("score", _content_score(dict(score_result)))
    passed = bool(source.get(
        "passed", _is_number(score) and float(score) >= float(threshold)
    ))
    return {"score": score, "threshold": threshold, "passed": passed}


def _seo_scorecard_gate(
    source: Mapping[str, Any],
    *,
    applicable: bool,
) -> Dict[str, Any]:
    if not applicable:
        return {
            "score": None, "threshold": None, "passed": True,
            "critical_issue_count": 0, "not_applicable": True,
        }
    threshold = _legacy_value("SEO_PUBLISHING_THRESHOLD", SEO_PUBLISHING_THRESHOLD)
    target = _legacy_value("SEO_TARGET_SCORE", SEO_TARGET_SCORE)
    issues = source.get("critical_issues", [])
    critical_issues = issues if isinstance(issues, list) else []
    score = source.get("score")
    passed = (
        _is_number(score)
        and float(score) >= float(threshold)
        and not critical_issues
    )
    target_met = _is_number(score) and float(score) >= float(target)
    status = "failed_floor" if not passed else "met" if target_met else "below_target"
    gate = {
        "score": score,
        "threshold": threshold,
        "passed": passed,
        "critical_issue_count": len(critical_issues),
        "target": target,
        "target_met": bool(target_met),
        "target_status": status,
    }
    if critical_issues:
        gate["critical_issues"] = critical_issues
    return gate


def _aeo_scorecard_gate(
    source: Mapping[str, Any],
    *,
    artifact_kind: str,
) -> Dict[str, Any]:
    not_applicable = artifact_kind != "blog" and source.get("not_applicable") is True
    threshold = source.get("threshold", 90)
    score = source.get("score")
    passed = bool(source.get(
        "passed",
        True if not_applicable else _is_number(score) and float(score) >= float(threshold),
    ))
    gate = {"score": score, "threshold": threshold, "passed": passed}
    if source.get("not_applicable") is True:
        gate["not_applicable"] = True
    return gate


def _scorecard_from_scorer_result(
    score_result: Mapping[str, Any],
    *,
    artifact_kind: str,
) -> Dict[str, Any]:
    """Return independent publish score gates from a scorer result."""
    gates = score_result.get("quality_gates")
    quality_gates = gates if isinstance(gates, Mapping) else {}
    content_source = quality_gates.get("content_quality")
    if not isinstance(content_source, Mapping):
        content_source = {}
    seo_source = quality_gates.get("seo_quality")
    if not isinstance(seo_source, Mapping):
        seo_source = {}
    aeo_source = quality_gates.get("aeo_geo")
    if not isinstance(aeo_source, Mapping):
        aeo_source = score_result.get("aeo_geo")
    if not isinstance(aeo_source, Mapping):
        aeo_source = {}

    seo_not_applicable = artifact_kind != "blog" and not seo_source
    content_gate = _content_scorecard_gate(score_result, content_source, artifact_kind)
    seo_gate = _seo_scorecard_gate(seo_source, applicable=not seo_not_applicable)
    aeo_gate = _aeo_scorecard_gate(aeo_source, artifact_kind=artifact_kind)
    return {
        "passed": bool(
            content_gate["passed"]
            and seo_gate["passed"]
            and aeo_gate["passed"]
        ),
        "content_quality": content_gate,
        "seo_quality": seo_gate,
        "aeo_geo": aeo_gate,
    }

def _score_report_line(
    label: str,
    score: Any,
    threshold: Any,
    passed: bool,
) -> str:
    if score is None:
        return f"{label}: n/a"
    status = "PASS" if passed else "FAIL"
    return f"{label}: {score}/100 (threshold: {threshold}, {status})"

def _seo_score_report_line(
    label: str,
    score: Any,
    threshold: Any,
    target: Any,
    passed: bool,
    *,
    target_met: Any,
    target_status: Any,
) -> str:
    if score is None:
        return f"{label}: n/a"
    if not passed:
        status = "FAIL"
    elif target_met is True or target_status == "met":
        status = "PASS, TARGET MET"
    else:
        status = "PASS, BELOW TARGET"
    return (
        f"{label}: {score}/100 "
        f"(release floor: {threshold}, target: {target}, {status})"
    )

def _finding_lines(findings: List[Dict[str, Any]]) -> List[str]:
    blockers = [
        finding
        for finding in findings
        if finding.get("severity") == "error"
    ]
    if not blockers:
        blockers = findings
    lines = []
    for finding in blockers[:3]:
        line = finding.get("line", "?")
        rule = finding.get("rule_id", "finding")
        message = finding.get("message", "")
        lines.append(f"line {line}: {rule} - {message}".rstrip(" -"))
    return lines

def _url_blocker_line(result: Any) -> str:
    location = f"line {result.line}: " if result.line else ""
    anchor = f" [{result.anchor}]" if result.anchor else ""
    code = f"HTTP {result.status_code}" if result.status_code is not None else result.reason
    line = f"{location}{result.url}{anchor} ({result.status}: {code})"
    if result.status == "manual_review":
        line += (
            " Replace this source with an equivalent resolved public source "
            "or remove the supported claim. Do not remove the citation without "
            "replacing it with a resolved source supporting the same claim."
        )
    return line

def _priority_fix_lines(priority_fixes: List[Dict[str, Any]]) -> List[str]:
    lines = []
    for fix in priority_fixes[:3]:
        dimension = fix.get("dimension", "unknown")
        issue = fix.get("issue", "Unknown issue")
        lines.append(f"{dimension}: {issue}")
    return lines


__all__ = ['_blocked_readiness_result', '_content_score', '_finding_lines', '_gate_from_findings', '_gate_from_score', '_gate_from_url_summary', '_priority_fix_lines', '_reject_telemetry_output_collision', '_score_content', '_score_report_line', '_scorecard_from_scorer_result', '_seo_score_report_line', '_timed_call', '_url_blocker_line']
