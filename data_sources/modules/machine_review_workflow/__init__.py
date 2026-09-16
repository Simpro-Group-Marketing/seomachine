"""Collect hash-bound agent responses into an existing machine-review artifact."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Mapping, Sequence

from ..blog_assembly_contract import (
    atomic_write_json,
    canonical_json_sha256,
    file_sha256,
    validate_sha256,
)
from ..machine_review import (
    AGENT_RESPONSE_FIELDS,
    AGENT_ROSTER,
    PHASES,
    build_machine_review,
    check_machine_review,
    write_machine_review,
)
from .validation import check_review_response


AGENT_RESPONSE_SCHEMA = "simpro-machine-review-agent-response/v1"
COLLECTION_REPORT_SCHEMA = "simpro-machine-review-collection-report/v1"
NOT_RELEASE_READY = "draft_ready_not_release_ready"
RESPONSE_BINDING_FIELDS = (
    "run_id",
    "workflow_stage",
    "phase",
    "command",
    "repository_commit",
    "editorial_plan_sha256",
    "article_sha256",
    "proof_sidecar_sha256",
)
RESPONSE_FIELDS = frozenset(
    {
        "schema",
        *RESPONSE_BINDING_FIELDS,
        *AGENT_RESPONSE_FIELDS,
        "artifact_hash",
    }
)


def build_agent_response(
    *,
    run_id: str,
    workflow_stage: str,
    phase: str,
    command: str,
    repository_commit: str,
    editorial_plan_path: str | Path,
    article_path: str | Path,
    proof_sidecar_path: str | Path,
    agent: str,
    status: str,
    findings: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Build one canonical agent response bound to the reviewed input bytes."""
    payload: dict[str, Any] = {
        "schema": AGENT_RESPONSE_SCHEMA,
        "run_id": _required_string(run_id, "run_id"),
        "workflow_stage": _required_string(workflow_stage, "workflow_stage"),
        "phase": _required_phase(phase),
        "command": _required_string(command, "command"),
        "repository_commit": _required_string(repository_commit, "repository_commit"),
        "editorial_plan_sha256": file_sha256(editorial_plan_path),
        "article_sha256": file_sha256(article_path),
        "proof_sidecar_sha256": file_sha256(proof_sidecar_path),
        "agent": agent,
        "status": status,
        "findings": [dict(finding) for finding in findings],
    }
    payload["artifact_hash"] = canonical_json_sha256(payload)
    issues = check_agent_response(payload, expected_bindings=payload)
    if issues:
        raise ValueError(_issues_message(issues))
    return payload


def write_agent_response(path: str | Path, response: Mapping[str, Any]) -> None:
    """Persist an agent response and refresh its canonical artifact hash."""
    payload = dict(response)
    payload.pop("artifact_hash", None)
    payload["artifact_hash"] = canonical_json_sha256(payload)
    atomic_write_json(path, payload)


def check_agent_response(
    payload: Mapping[str, Any],
    *,
    expected_bindings: Mapping[str, str],
) -> list[dict[str, str]]:
    """Return deterministic issues for one response artifact."""
    issues: list[dict[str, str]] = []
    missing = RESPONSE_FIELDS - set(payload)
    unknown = set(payload) - RESPONSE_FIELDS
    if missing:
        issues.append(_issue("machine_review_response_missing_fields", ", ".join(sorted(missing))))
    if unknown:
        issues.append(_issue("machine_review_response_unknown_fields", ", ".join(sorted(unknown))))
    if payload.get("schema") != AGENT_RESPONSE_SCHEMA:
        issues.append(
            _issue(
                "machine_review_response_schema_invalid",
                f"Response must use {AGENT_RESPONSE_SCHEMA}.",
            )
        )
    for field in RESPONSE_BINDING_FIELDS[:5]:
        if not isinstance(payload.get(field), str) or not str(payload.get(field)).strip():
            issues.append(_issue(f"machine_review_response_{field}_invalid", f"{field} must be a non-empty string."))
    for field in RESPONSE_BINDING_FIELDS[5:]:
        try:
            validate_sha256(payload.get(field), field=field)
        except ValueError:
            issues.append(_issue(f"machine_review_response_{field}_invalid", f"{field} must be a lowercase SHA-256 digest."))
    for field in RESPONSE_BINDING_FIELDS:
        if payload.get(field) != expected_bindings.get(field):
            issues.append(
                _issue(
                    f"machine_review_response_{field}_mismatch",
                    f"Response {field} does not match the current collection input.",
                )
            )
    response = {field: payload.get(field) for field in AGENT_RESPONSE_FIELDS}
    issues.extend(check_review_response(response))
    stored_hash = payload.get("artifact_hash")
    unsigned = dict(payload)
    unsigned.pop("artifact_hash", None)
    if not isinstance(stored_hash, str) or stored_hash != canonical_json_sha256(unsigned):
        issues.append(
            _issue(
                "machine_review_response_artifact_hash_invalid",
                "Response artifact_hash does not match its canonical payload.",
            )
        )
    return _sorted_issues(issues)


def collect_machine_review(
    *,
    response_paths: Sequence[str | Path],
    output_path: str | Path,
    report_path: str | Path,
    run_id: str,
    workflow_stage: str,
    phase: str,
    command: str,
    repository_commit: str,
    editorial_plan_path: str | Path,
    article_path: str | Path,
    proof_sidecar_path: str | Path,
    created_at: str,
) -> int:
    """Collect six valid responses, or write a fail-closed collection report."""
    Path(output_path).unlink(missing_ok=True)
    expected = _current_bindings(
        run_id=run_id,
        workflow_stage=workflow_stage,
        phase=phase,
        command=command,
        repository_commit=repository_commit,
        editorial_plan_path=editorial_plan_path,
        article_path=article_path,
        proof_sidecar_path=proof_sidecar_path,
    )
    valid_by_agent: dict[str, Mapping[str, Any]] = {}
    issues: list[dict[str, str]] = []
    for path_value in response_paths:
        path = Path(path_value)
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as error:
            issues.append(_issue("machine_review_response_unreadable", f"{path}: {error}", path))
            continue
        if not isinstance(payload, Mapping):
            issues.append(_issue("machine_review_response_root_invalid", "Response must be a JSON object.", path))
            continue
        response_issues = check_agent_response(payload, expected_bindings=expected)
        if response_issues:
            issues.extend(_with_path(response_issues, path))
            continue
        agent = str(payload["agent"])
        if agent in valid_by_agent:
            issues.append(_issue("machine_review_response_duplicate_role", f"Duplicate response for {agent}.", path))
            continue
        valid_by_agent[agent] = payload
    missing = [agent for agent in AGENT_ROSTER if agent not in valid_by_agent]
    if missing:
        issues.append(
            _issue(
                "machine_review_response_missing_role",
                "Missing valid responses for: " + ", ".join(missing),
            )
        )
    if issues:
        _write_collection_report(
            report_path,
            status=NOT_RELEASE_READY,
            expected=expected,
            collected_agents=valid_by_agent,
            issues=issues,
            output_path=None,
        )
        return 1
    responses = [
        {field: valid_by_agent[agent][field] for field in AGENT_RESPONSE_FIELDS}
        for agent in AGENT_ROSTER
    ]
    review = build_machine_review(
        run_id=run_id,
        workflow_stage=workflow_stage,
        phase=phase,
        command=command,
        repository_commit=repository_commit,
        editorial_plan_path=editorial_plan_path,
        article_path=article_path,
        proof_sidecar_path=proof_sidecar_path,
        responses=responses,
        created_at=created_at,
    )
    final_issues = [
        _issue(str(finding["rule_id"]), str(finding["message"]))
        for finding in check_machine_review(review)
    ]
    changed_hashes = [
        field
        for field in RESPONSE_BINDING_FIELDS[5:]
        if review.get(field) != expected[field]
    ]
    if changed_hashes:
        final_issues.append(
            _issue(
                "machine_review_input_changed_during_collection",
                "Final review hashes differ from the validated response bindings: "
                + ", ".join(changed_hashes),
            )
        )
    if final_issues:
        _write_collection_report(
            report_path,
            status=NOT_RELEASE_READY,
            expected=expected,
            collected_agents=valid_by_agent,
            issues=final_issues,
            output_path=None,
        )
        return 1
    write_machine_review(output_path, review)
    _write_collection_report(
        report_path,
        status="review_collected",
        expected=expected,
        collected_agents=valid_by_agent,
        issues=[],
        output_path=Path(output_path),
    )
    return 0


def _current_bindings(
    *,
    run_id: str,
    workflow_stage: str,
    phase: str,
    command: str,
    repository_commit: str,
    editorial_plan_path: str | Path,
    article_path: str | Path,
    proof_sidecar_path: str | Path,
) -> dict[str, str]:
    return {
        "run_id": _required_string(run_id, "run_id"),
        "workflow_stage": _required_string(workflow_stage, "workflow_stage"),
        "phase": _required_phase(phase),
        "command": _required_string(command, "command"),
        "repository_commit": _required_string(repository_commit, "repository_commit"),
        "editorial_plan_sha256": file_sha256(editorial_plan_path),
        "article_sha256": file_sha256(article_path),
        "proof_sidecar_sha256": file_sha256(proof_sidecar_path),
    }


def _write_collection_report(
    path: str | Path,
    *,
    status: str,
    expected: Mapping[str, str],
    collected_agents: Mapping[str, Mapping[str, Any]],
    issues: Sequence[Mapping[str, str]],
    output_path: Path | None,
) -> None:
    payload: dict[str, Any] = {
        "schema": COLLECTION_REPORT_SCHEMA,
        "status": status,
        **expected,
        "collected_agents": [agent for agent in AGENT_ROSTER if agent in collected_agents],
        "issues": _sorted_issues(issues),
        "review_path": str(output_path) if output_path is not None else None,
        "review_sha256": file_sha256(output_path) if output_path is not None else None,
    }
    payload["artifact_hash"] = canonical_json_sha256(payload)
    atomic_write_json(path, payload)


def _issue(code: str, message: str, path: Path | None = None) -> dict[str, str]:
    issue = {"code": code, "message": message}
    if path is not None:
        issue["path"] = str(path)
    return issue


def _with_path(issues: Sequence[Mapping[str, str]], path: Path) -> list[dict[str, str]]:
    return [{**dict(issue), "path": str(path)} for issue in issues]


def _sorted_issues(issues: Sequence[Mapping[str, str]]) -> list[dict[str, str]]:
    return sorted(
        (dict(issue) for issue in issues),
        key=lambda issue: (issue.get("code", ""), issue.get("path", ""), issue.get("message", "")),
    )


def _issues_message(issues: Sequence[Mapping[str, str]]) -> str:
    return "; ".join(f"{issue['code']}: {issue['message']}" for issue in issues)


def _required_string(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a non-empty string")
    return value.strip()


def _required_phase(value: Any) -> str:
    if value not in PHASES:
        raise ValueError("phase must be plan or article")
    return str(value)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Collect six hash-bound machine-review agent responses.",
    )
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--workflow-stage", required=True)
    parser.add_argument("--phase", choices=sorted(PHASES), required=True)
    parser.add_argument("--command", required=True)
    parser.add_argument("--repository-commit", required=True)
    parser.add_argument("--editorial-plan", required=True)
    parser.add_argument("--article", required=True)
    parser.add_argument("--proof-sidecar", required=True)
    parser.add_argument("--created-at", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--report", required=True)
    parser.add_argument("responses", nargs="*")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    return collect_machine_review(
        response_paths=args.responses,
        output_path=args.output,
        report_path=args.report,
        run_id=args.run_id,
        workflow_stage=args.workflow_stage,
        phase=args.phase,
        command=args.command,
        repository_commit=args.repository_commit,
        editorial_plan_path=args.editorial_plan,
        article_path=args.article,
        proof_sidecar_path=args.proof_sidecar,
        created_at=args.created_at,
    )


__all__ = [
    "AGENT_RESPONSE_SCHEMA",
    "COLLECTION_REPORT_SCHEMA",
    "NOT_RELEASE_READY",
    "build_agent_response",
    "check_agent_response",
    "collect_machine_review",
    "main",
    "write_agent_response",
]


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main(sys.argv[1:]))
