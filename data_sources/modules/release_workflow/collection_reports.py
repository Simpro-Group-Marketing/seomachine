"""Machine-review collection-report validation for release-chain decisions."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from .. import machine_review, machine_review_workflow
from ..blog_assembly.common import (
    canonical_json_sha256,
    file_sha256,
    load_json_object_snapshot,
)


REVIEW_COLLECTED = "review_collected"
COLLECTION_REPORT_FIELDS = frozenset({
    "schema", "status", "run_id", "workflow_stage", "phase", "command",
    "repository_commit", "editorial_plan_sha256", "article_sha256",
    "proof_sidecar_sha256", "collected_agents", "issues", "review_path",
    "review_sha256", "artifact_hash",
})


def check_collection_report(
    report_path: str | Path,
    *,
    review_path: str | Path,
    editorial_plan_path: str | Path,
    article_path: str | Path,
    proof_sidecar_path: str | Path,
    expected_run_id: str,
    expected_phase: str,
) -> list[str]:
    try:
        report = load_json_object_snapshot(
            report_path,
            field="machine review collection report",
        ).payload
    except (OSError, TypeError, ValueError):
        return ["machine_review_collection_report_unreadable"]
    if report.get("status") != REVIEW_COLLECTED:
        return ["machine_review_collection_incomplete"]
    try:
        expected = _collection_expected_values(
            review_path=review_path,
            editorial_plan_path=editorial_plan_path,
            article_path=article_path,
            proof_sidecar_path=proof_sidecar_path,
            expected_run_id=expected_run_id,
            expected_phase=expected_phase,
        )
    except (OSError, TypeError, ValueError):
        return ["machine_review_collection_report_binding_unavailable"]
    issues = [
        *_collection_shape_issues(report),
        *_collection_binding_issues(report, expected_bindings=expected["bindings"]),
        *_collection_contract_issues(report),
        *_collection_review_issues(report, expected=expected),
    ]
    return sorted(set(issues))


def _collection_shape_issues(report: Mapping[str, Any]) -> list[str]:
    issues: list[str] = []
    if set(report) != COLLECTION_REPORT_FIELDS:
        issues.append("machine_review_collection_report_shape_invalid")
    unsigned = dict(report)
    stored_hash = unsigned.pop("artifact_hash", None)
    if stored_hash != canonical_json_sha256(unsigned):
        issues.append("machine_review_collection_report_hash_invalid")
    return issues


def _collection_expected_values(
    *,
    review_path: str | Path,
    editorial_plan_path: str | Path,
    article_path: str | Path,
    proof_sidecar_path: str | Path,
    expected_run_id: str,
    expected_phase: str,
) -> dict[str, Any]:
    expected_review = Path(review_path).resolve()
    return {
        "bindings": {
            "run_id": expected_run_id,
            "phase": expected_phase,
            "editorial_plan_sha256": file_sha256(editorial_plan_path),
            "article_sha256": file_sha256(article_path),
            "proof_sidecar_sha256": file_sha256(proof_sidecar_path),
        },
        "review_path": expected_review,
        "review_sha256": file_sha256(expected_review),
    }


def _collection_binding_issues(
    report: Mapping[str, Any],
    *,
    expected_bindings: Mapping[str, str],
) -> list[str]:
    if any(report.get(field) != value for field, value in expected_bindings.items()):
        return ["machine_review_collection_report_binding_mismatch"]
    return []


def _collection_contract_issues(report: Mapping[str, Any]) -> list[str]:
    issues: list[str] = []
    if (
        report.get("schema") != machine_review_workflow.COLLECTION_REPORT_SCHEMA
        or report.get("collected_agents") != list(machine_review.AGENT_ROSTER)
        or report.get("issues") != []
    ):
        issues.append("machine_review_collection_report_contract_invalid")
    for field in ("workflow_stage", "command", "repository_commit"):
        if not isinstance(report.get(field), str) or not report[field].strip():
            issues.append("machine_review_collection_report_contract_invalid")
            break
    return issues


def _collection_review_issues(
    report: Mapping[str, Any],
    *,
    expected: Mapping[str, Any],
) -> list[str]:
    reported_review = report.get("review_path")
    try:
        reported_review_matches = (
            isinstance(reported_review, str)
            and Path(reported_review).resolve() == expected["review_path"]
        )
    except (OSError, ValueError):
        reported_review_matches = False
    if (
        not reported_review_matches
        or report.get("review_sha256") != expected["review_sha256"]
    ):
        return ["machine_review_collection_report_review_mismatch"]
    return []


__all__ = ["check_collection_report"]
