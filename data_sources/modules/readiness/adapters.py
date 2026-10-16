"""Publish-readiness adapters responsibilities."""
from pathlib import Path
from typing import Any, Dict, List, Mapping

from .common import (
    GateResult,
    LANDING_PAGE_SCORE_THRESHOLD,
    LandingPageScorer,
    READINESS_RESULT_SCHEMA,
    ReadinessResult,
    ReadinessTelemetry,
    UrlValidationSummary,
    is_json_number as _is_number,
    read_publishable_markdown,
    should_fail,
    summarize_findings,
)


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
    *,
    article_content: str | None = None,
    article: Any | None = None,
) -> Dict[str, Any]:
    content = article_content if article_content is not None else article_path.read_text(
        encoding="utf-8"
    )
    artifact = article or read_publishable_markdown(article_path)
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
            "threshold": LANDING_PAGE_SCORE_THRESHOLD,
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
        "threshold": LANDING_PAGE_SCORE_THRESHOLD,
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

def _content_score(score_result: Dict[str, Any]) -> Any:
    return score_result.get("content_quality_score", score_result.get("composite_score"))


def _content_scorecard_gate(score_result: Mapping[str, Any]) -> Dict[str, Any]:
    threshold = score_result.get("threshold")
    if not _is_number(threshold):
        threshold = LANDING_PAGE_SCORE_THRESHOLD
    score = _content_score(dict(score_result))
    passed = bool(_is_number(score) and float(score) >= float(threshold))
    return {"score": score, "threshold": threshold, "passed": passed}


def _aeo_scorecard_gate(source: Mapping[str, Any]) -> Dict[str, Any]:
    not_applicable = source.get("not_applicable") is True
    threshold = source.get("threshold", 90)
    score = source.get("score")
    passed = bool(source.get(
        "passed",
        True if not_applicable else _is_number(score) and float(score) >= float(threshold),
    ))
    gate = {"score": score, "threshold": threshold, "passed": passed}
    if not_applicable:
        gate["not_applicable"] = True
    return gate


def _scorecard_from_scorer_result(score_result: Mapping[str, Any]) -> Dict[str, Any]:
    """Return the landing-page score gates; SEO is not scored for landing pages."""
    aeo_source = score_result.get("aeo_geo")
    content_gate = _content_scorecard_gate(score_result)
    aeo_gate = _aeo_scorecard_gate(aeo_source if isinstance(aeo_source, Mapping) else {})
    return {
        "passed": bool(content_gate["passed"] and aeo_gate["passed"]),
        "content_quality": content_gate,
        "seo_quality": {
            "score": None, "threshold": None, "passed": True,
            "critical_issue_count": 0, "not_applicable": True,
        },
        "aeo_geo": aeo_gate,
    }

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


__all__ = ['_blocked_readiness_result', '_content_score', '_finding_lines', '_gate_from_findings', '_gate_from_score', '_gate_from_url_summary', '_priority_fix_lines', '_score_content', '_scorecard_from_scorer_result', '_timed_call', '_url_blocker_line']
