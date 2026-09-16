"""Validation for the review payload nested in an agent response artifact."""

from __future__ import annotations

from typing import Any, Mapping

from ..machine_review import (
    AGENT_RESPONSE_FIELDS,
    AGENT_ROSTER,
    FINDING_FIELDS,
    PROHIBITED_VERDICT_FIELDS,
    STATUSES,
)


def check_review_response(response: Mapping[str, Any]) -> list[dict[str, str]]:
    """Validate the established agent, status, and findings response shape."""
    issues: list[dict[str, str]] = []
    if PROHIBITED_VERDICT_FIELDS.intersection(response):
        issues.append(
            _issue(
                "machine_review_release_verdict_prohibited",
                "Machine review agent responses must not include release verdicts.",
            )
        )
    if set(response) != AGENT_RESPONSE_FIELDS:
        issues.append(
            _issue(
                "machine_review_agent_response_shape_invalid",
                "Machine review agent response has an invalid shape.",
            )
        )
    agent = response.get("agent")
    if not isinstance(agent, str) or agent not in AGENT_ROSTER:
        issues.append(
            _issue(
                "machine_review_agent_invalid",
                "Machine review agent response uses an unknown agent.",
            )
        )
        return issues
    status = response.get("status")
    if status not in STATUSES:
        issues.append(
            _issue(
                "machine_review_status_invalid",
                f"Machine review status for {agent} is invalid.",
            )
        )
    elif status != "completed":
        issues.append(
            _issue(
                "machine_review_unresolved_status",
                f"Machine review for {agent} is {status}.",
            )
        )
    response_findings = response.get("findings")
    if status == "completed" and isinstance(response_findings, list) and response_findings:
        issues.append(
            _issue(
                "machine_review_completed_with_findings",
                f"Machine review for {agent} is completed but still contains findings.",
            )
        )
    issues.extend(_check_findings(response_findings, agent=agent))
    return issues


def _check_findings(value: Any, *, agent: str) -> list[dict[str, str]]:
    if not isinstance(value, list):
        return [
            _issue(
                "machine_review_findings_invalid",
                f"Machine review findings for {agent} must be a list.",
            )
        ]
    issues: list[dict[str, str]] = []
    seen_ids: set[str] = set()
    for index, finding in enumerate(value):
        finding_issues, finding_id = _check_finding(
            finding,
            index=index,
            agent=agent,
            seen_ids=seen_ids,
        )
        issues.extend(finding_issues)
        if finding_id is not None:
            seen_ids.add(finding_id)
    return issues


def _check_finding(
    finding: Any,
    *,
    index: int,
    agent: str,
    seen_ids: set[str],
) -> tuple[list[dict[str, str]], str | None]:
    if not isinstance(finding, Mapping):
        return [
            _issue(
                "machine_review_finding_invalid",
                f"Machine review finding {index} for {agent} must be an object.",
            )
        ], None
    finding_id = finding.get("id")
    issues = [
        *_finding_shape_issues(finding, index=index, agent=agent),
        *_finding_id_issues(finding_id, index=index, agent=agent, seen_ids=seen_ids),
        *_finding_field_issues(finding, finding_id=finding_id or index),
    ]
    return issues, str(finding_id) if isinstance(finding_id, str) else None


def _finding_shape_issues(
    finding: Mapping[str, Any],
    *,
    index: int,
    agent: str,
) -> list[dict[str, str]]:
    if set(finding) == FINDING_FIELDS:
        return []
    return [
        _issue(
            "machine_review_finding_shape_invalid",
            f"Machine review finding {index} for {agent} has an invalid shape.",
        )
    ]


def _finding_id_issues(
    finding_id: Any,
    *,
    index: int,
    agent: str,
    seen_ids: set[str],
) -> list[dict[str, str]]:
    if not isinstance(finding_id, str) or not finding_id.strip():
        return [
            _issue(
                "machine_review_finding_id_invalid",
                f"Machine review finding {index} for {agent} needs a stable ID.",
            )
        ]
    if finding_id in seen_ids:
        return [
            _issue(
                "machine_review_finding_id_duplicate",
                f"Machine review finding ID {finding_id} is duplicated for {agent}.",
            )
        ]
    return []


def _finding_field_issues(
    finding: Mapping[str, Any],
    *,
    finding_id: object,
) -> list[dict[str, str]]:
    issues: list[dict[str, str]] = []
    if finding.get("priority") not in {"low", "medium", "high", "critical"}:
        issues.append(
            _issue(
                "machine_review_finding_priority_invalid",
                f"Machine review finding {finding_id} has an invalid priority.",
            )
        )
    for field in ("category", "location", "evidence_anchor", "recommendation", "proof_risk"):
        if not isinstance(finding.get(field), str) or not str(finding.get(field)).strip():
            issues.append(
                _issue(
                    "machine_review_finding_field_invalid",
                    f"Machine review finding {finding_id} {field} must be a non-empty string.",
                )
            )
    if not isinstance(finding.get("protected_span"), bool):
        issues.append(
            _issue(
                "machine_review_finding_protected_span_invalid",
                f"Machine review finding {finding_id} protected_span must be a boolean.",
            )
        )
    return issues


def _issue(code: str, message: str) -> dict[str, str]:
    return {"code": code, "message": message}


__all__ = ["check_review_response"]
