"""Draft closeout report assembled from proof-aware blog diagnostics."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any, Mapping

try:
    from .ai_copy_linter import (
        lint_file,
        should_fail as lint_should_fail,
        summarize_findings as lint_summarize_findings,
    )
    from .blog_assembly_contract import atomic_write_json
    from .blog_draft_closeout_support import (
        artifact_row,
        collect_blockers,
        collect_warnings,
        failed_tool_check,
        finding_blockers,
        url_result_row,
        validate_closeout_output_path,
    )
    from .content_scrubber import scrub_file
    from .content_scoring.scorer import ContentScorer
    from .source_classification_preflight import build_preflight_report
    from .source_support.common import (
        should_fail as source_support_should_fail,
        summarize_findings as source_support_summarize_findings,
    )
    from .source_support.orchestration import check_file as source_support_check_file
    from .url_validator import validate_file_urls
except ImportError:  # pragma: no cover - supports direct script execution.
    from ai_copy_linter import (
        lint_file,
        should_fail as lint_should_fail,
        summarize_findings as lint_summarize_findings,
    )
    from blog_assembly_contract import atomic_write_json
    from blog_draft_closeout_support import (
        artifact_row,
        collect_blockers,
        collect_warnings,
        failed_tool_check,
        finding_blockers,
        url_result_row,
        validate_closeout_output_path,
    )
    from content_scrubber import scrub_file
    from content_scoring.scorer import ContentScorer
    from source_classification_preflight import build_preflight_report
    from source_support.common import (
        should_fail as source_support_should_fail,
        summarize_findings as source_support_summarize_findings,
    )
    from source_support.orchestration import check_file as source_support_check_file
    from url_validator import validate_file_urls


REPORT_SCHEMA = "simpro-blog-draft-closeout/v1"
CHECK_NAMES = (
    "scrub",
    "ai_lint",
    "source_classification",
    "source_support",
    "paa",
    "url_validation",
    "scoring",
)
def build_report(
    article_path: str | Path,
    *,
    proof_sidecar: str | Path,
    workspace_root: str | Path = ".",
    source_inventory: str | Path | None = None,
    classification_directory: str | Path | None = None,
    source_decision_path: str | Path | None = None,
    fail_on: str = "error",
    paa_workflow_mode: str | None = None,
    paa_content_brief: str | None = None,
    paa_answersocrates_blocker: str | None = None,
    paa_expected_query: str | None = None,
    paa_expected_collection_date: str | None = None,
    paa_expected_run_id: str | None = None,
    paa_artifact: str | None = None,
    assembly_date: str | None = None,
) -> dict[str, Any]:
    """Run closeout diagnostics and return the v1 machine report."""
    if fail_on not in {"error", "warning", "none"}:
        raise ValueError("fail_on must be one of: error, warning, none")
    root = Path(workspace_root).resolve()
    article = Path(article_path).resolve()
    sidecar = Path(proof_sidecar).resolve()
    article_text = article.read_text(encoding="utf-8")
    paa_args = {
        "paa_workflow_mode": paa_workflow_mode,
        "paa_content_brief": paa_content_brief,
        "paa_answersocrates_blocker": paa_answersocrates_blocker,
        "paa_expected_query": paa_expected_query,
        "paa_expected_collection_date": paa_expected_collection_date,
        "paa_expected_run_id": paa_expected_run_id,
        "paa_artifact": paa_artifact,
    }

    checks: dict[str, dict[str, Any]] = {}
    checks["scrub"] = _scrub_check(article)
    checks["ai_lint"] = _ai_lint_check(article, fail_on=fail_on)
    checks["source_classification"] = _source_classification_check(
        source_inventory,
        classification_directory=classification_directory,
        source_decision_path=source_decision_path,
        workspace_root=root,
    )
    checks["source_support"] = _source_support_check(article, proof_sidecar=sidecar, fail_on=fail_on)
    checks["url_validation"] = _url_validation_check(article)
    scorecard = _score_article(
        article_text,
        article=article,
        sidecar=sidecar,
        paa_args=paa_args,
        assembly_date=assembly_date,
    )
    checks["scoring"] = _scoring_check(scorecard)
    checks["paa"] = _paa_check(scorecard, paa_args)

    blockers = collect_blockers(checks, CHECK_NAMES)
    warnings = collect_warnings(checks, CHECK_NAMES)
    return {
        "schema": REPORT_SCHEMA,
        "article": artifact_row(article, root=root),
        "sidecar": artifact_row(sidecar, root=root),
        "release_artifacts_created": False,
        "checks": {name: checks[name] for name in CHECK_NAMES},
        "scorecard": scorecard,
        "passed": not blockers and bool(scorecard.get("passed", False)),
        "blockers": blockers,
        "warnings": warnings,
    }


def _scrub_check(article: Path) -> dict[str, Any]:
    try:
        result = scrub_file(str(article))
    except Exception as error:  # noqa: BLE001 - report all closeout tool failures.
        return failed_tool_check("scrub_failed", error)
    check = {
        "status": "failed" if result.get("would_change") else "passed",
        "passed": not bool(result.get("would_change")),
        "file": result.get("file"),
        "would_change": bool(result.get("would_change")),
        "statistics": result.get("statistics", {}),
        "blockers": [],
    }
    if result.get("would_change"):
        check["blockers"].append(
            {
                "rule_id": "scrub_changes_required",
                "message": "Scrub diagnostics found required article cleanup.",
            }
        )
    return check


def _ai_lint_check(article: Path, *, fail_on: str) -> dict[str, Any]:
    try:
        findings = lint_file(str(article), profile="simpro-web", fail_on=fail_on)
        summary = lint_summarize_findings(findings)
        failed = lint_should_fail(findings, fail_on=fail_on)
    except Exception as error:  # noqa: BLE001
        return failed_tool_check("ai_lint_failed", error)
    return {
        "status": "failed" if failed else "passed",
        "passed": not failed,
        "profile": "simpro-web",
        "fail_on": fail_on,
        "summary": summary,
        "findings": findings,
        "blockers": finding_blockers("ai_lint", findings, failed=failed),
    }


def _source_classification_check(
    source_inventory: str | Path | None,
    *,
    classification_directory: str | Path | None,
    source_decision_path: str | Path | None,
    workspace_root: Path,
) -> dict[str, Any]:
    if source_inventory is None:
        return {
            "status": "not_applicable",
            "passed": True,
            "reason": (
                "No source inventory was supplied; source classification is optional "
                "for this closeout run."
            ),
            "blockers": [],
        }
    directory = classification_directory or workspace_root / "research" / "source-classifications"
    try:
        report = build_preflight_report(
            source_inventory,
            classification_directory=directory,
            decision_path=source_decision_path,
            workspace_root=workspace_root,
        )
    except Exception as error:  # noqa: BLE001
        return failed_tool_check("source_classification_preflight_failed", error)
    blockers = list(report.get("blockers", []))
    return {
        "status": "passed" if report.get("ready_for_drafting") else "failed",
        "passed": bool(report.get("ready_for_drafting")),
        "report": report,
        "blockers": blockers,
    }


def _source_support_check(
    article: Path,
    *,
    proof_sidecar: Path,
    fail_on: str,
) -> dict[str, Any]:
    try:
        findings = source_support_check_file(
            article,
            fail_on=fail_on,
            proof_sidecar=str(proof_sidecar),
        )
        summary = source_support_summarize_findings(findings)
        failed = source_support_should_fail(findings, fail_on=fail_on)
    except Exception as error:  # noqa: BLE001
        return failed_tool_check("source_support_failed", error)
    return {
        "status": "failed" if failed else "passed",
        "passed": not failed,
        "fail_on": fail_on,
        "summary": summary,
        "findings": findings,
        "blockers": finding_blockers("source_support", findings, failed=failed),
    }


def _url_validation_check(article: Path) -> dict[str, Any]:
    try:
        summary = validate_file_urls(article)
    except Exception as error:  # noqa: BLE001
        return failed_tool_check("url_validation_failed", error)
    blockers = [
        {
            "rule_id": "url_validation_failed",
            "url": result.url,
            "status": result.status,
            "status_code": result.status_code,
            "line": result.line,
            "anchor": result.anchor,
            "message": result.reason,
        }
        for result in summary.blockers
    ]
    return {
        "status": "passed" if summary.passed else "failed",
        "passed": bool(summary.passed),
        "total": summary.total,
        "resolved": summary.resolved_count,
        "unresolved": summary.unresolved_count,
        "manual_review": summary.manual_review_count,
        "results": [url_result_row(result) for result in summary.results],
        "blockers": blockers,
    }


def _score_article(
    article_text: str,
    *,
    article: Path,
    sidecar: Path,
    paa_args: Mapping[str, str | None],
    assembly_date: str | None,
) -> dict[str, Any]:
    try:
        return ContentScorer().score(
            article_text,
            validate_urls=False,
            validate_source_support=False,
            source_path=str(article),
            proof_sidecar=str(sidecar),
            paa_workflow_mode=paa_args.get("paa_workflow_mode"),
            paa_content_brief=paa_args.get("paa_content_brief"),
            paa_answersocrates_blocker=paa_args.get("paa_answersocrates_blocker"),
            paa_expected_query=paa_args.get("paa_expected_query"),
            paa_expected_collection_date=paa_args.get("paa_expected_collection_date"),
            paa_expected_run_id=paa_args.get("paa_expected_run_id"),
            paa_artifact=paa_args.get("paa_artifact"),
            assembly_date=assembly_date,
        )
    except Exception as error:  # noqa: BLE001
        return {
            "passed": False,
            "error": {
                "rule_id": "content_scoring_failed",
                "message": str(error),
            },
        }


def _scoring_check(scorecard: Mapping[str, Any]) -> dict[str, Any]:
    passed = bool(scorecard.get("passed", False))
    blockers = []
    if not passed:
        message = "Content scoring did not pass all closeout gates."
        if isinstance(scorecard.get("error"), Mapping):
            message = str(scorecard["error"].get("message") or message)
        blockers.append(
            {
                "rule_id": "content_scoring_failed",
                "message": message,
            }
        )
    return {
        "status": "passed" if passed else "failed",
        "passed": passed,
        "composite_score": scorecard.get("composite_score"),
        "threshold": scorecard.get("threshold"),
        "quality_gates": scorecard.get("quality_gates", {}),
        "priority_fixes": scorecard.get("priority_fixes", []),
        "blockers": blockers,
    }


def _paa_check(
    scorecard: Mapping[str, Any],
    paa_args: Mapping[str, str | None],
) -> dict[str, Any]:
    paa_inputs = {key: value for key, value in paa_args.items() if value}
    paa_check = (
        scorecard.get("aeo_geo", {})
        .get("checks", {})
        .get("paa_provenance")
    )
    if isinstance(paa_check, Mapping):
        passed = bool(paa_check.get("passed", False))
        return {
            "status": str(paa_check.get("status") or ("passed" if passed else "failed")),
            "passed": passed,
            "inputs": paa_inputs,
            "source": "scorecard.aeo_geo.checks.paa_provenance",
            "check": dict(paa_check),
            "blockers": [] if passed else [_paa_blocker(paa_check)],
        }
    if not paa_inputs:
        return {
            "status": "not_applicable",
            "passed": True,
            "inputs": {},
            "reason": "No PAA closeout arguments were supplied and no scorer PAA check was available.",
            "blockers": [],
        }
    return {
        "status": "failed",
        "passed": False,
        "inputs": paa_inputs,
        "blockers": [
            {
                "rule_id": "paa_check_unavailable",
                "message": "PAA inputs were supplied but the scorer did not return a PAA check.",
            }
        ],
    }


def _paa_blocker(paa_check: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "rule_id": "paa_provenance_failed",
        "message": str(paa_check.get("issue") or "PAA provenance did not pass."),
        "fix": str(paa_check.get("fix") or ""),
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="blog_draft_closeout",
        description="Write a draft closeout report without creating release artifacts.",
    )
    parser.add_argument("article_path")
    parser.add_argument("--proof-sidecar", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--workspace-root", default=".")
    parser.add_argument("--source-inventory")
    parser.add_argument("--classification-directory")
    parser.add_argument("--source-decision-path")
    parser.add_argument("--fail-on", choices=("error", "warning", "none"), default="error")
    parser.add_argument("--paa-workflow-mode")
    parser.add_argument("--paa-content-brief")
    parser.add_argument("--paa-answersocrates-blocker")
    parser.add_argument("--paa-expected-query")
    parser.add_argument("--paa-expected-collection-date")
    parser.add_argument("--paa-expected-run-id")
    parser.add_argument("--paa-artifact")
    parser.add_argument("--assembly-date")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)
    try:
        output = validate_closeout_output_path(
            args.output,
            article_path=args.article_path,
            proof_sidecar=args.proof_sidecar,
            workspace_root=args.workspace_root,
        )
    except ValueError as error:
        parser.error(str(error))
    report = build_report(
        args.article_path,
        proof_sidecar=args.proof_sidecar,
        workspace_root=args.workspace_root,
        source_inventory=args.source_inventory,
        classification_directory=args.classification_directory,
        source_decision_path=args.source_decision_path,
        fail_on=args.fail_on,
        paa_workflow_mode=args.paa_workflow_mode,
        paa_content_brief=args.paa_content_brief,
        paa_answersocrates_blocker=args.paa_answersocrates_blocker,
        paa_expected_query=args.paa_expected_query,
        paa_expected_collection_date=args.paa_expected_collection_date,
        paa_expected_run_id=args.paa_expected_run_id,
        paa_artifact=args.paa_artifact,
        assembly_date=args.assembly_date,
    )
    atomic_write_json(output, report)
    return 0 if report["passed"] else 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
