"""Build and validate hash-bound machine editorial review artifacts."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Mapping, Sequence

try:
    from .blog_assembly_contract import atomic_write_json, canonical_json_sha256, file_sha256, validate_sha256
    from .guard_common import Finding, make_finding
except ImportError:  # pragma: no cover - supports direct script execution.
    from blog_assembly_contract import atomic_write_json, canonical_json_sha256, file_sha256, validate_sha256
    from guard_common import Finding, make_finding


SCHEMA = "simpro-blog-machine-review/v1"
BLOCKER_SCHEMA = "simpro-blog-machine-review-blocker/v1"
MAX_REPAIR_CYCLES = 2
AGENT_ROSTER = (
    "Content Analyzer",
    "Editor",
    "SEO Optimizer",
    "Meta Creator",
    "Internal Linker",
    "Keyword Mapper",
)
PHASES = frozenset({"plan", "article"})
STATUSES = frozenset({"completed", "changes_requested", "blocked"})
TOP_LEVEL_FIELDS = frozenset(
    {
        "schema",
        "run_id",
        "workflow_stage",
        "phase",
        "command",
        "repository_commit",
        "created_at",
        "editorial_plan_sha256",
        "article_sha256",
        "proof_sidecar_sha256",
        "agent_roster",
        "agent_responses",
        "artifact_hash",
    }
)
AGENT_RESPONSE_FIELDS = frozenset({"agent", "status", "findings"})
FINDING_FIELDS = frozenset(
    {
        "id",
        "priority",
        "category",
        "location",
        "evidence_anchor",
        "recommendation",
        "proof_risk",
        "protected_span",
    }
)
RFC3339_UTC_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z$"
)
PROHIBITED_VERDICT_FIELDS = {
    "release_verdict",
    "release_status",
    "publish_ready",
    "ready_for_publish",
}
PAIR_PROVENANCE_FIELDS = (
    "run_id",
    "workflow_stage",
    "command",
    "repository_commit",
)


def build_machine_review(
    *,
    run_id: str,
    workflow_stage: str,
    phase: str,
    command: str,
    repository_commit: str,
    editorial_plan_path: str | Path,
    article_path: str | Path,
    proof_sidecar_path: str | Path,
    responses: Sequence[Mapping[str, Any]],
    created_at: str,
) -> dict[str, Any]:
    """Return a deterministic review artifact for one frozen plan or article."""
    payload: dict[str, Any] = {
        "schema": SCHEMA,
        "run_id": _required_string(run_id, "run_id"),
        "workflow_stage": _required_string(workflow_stage, "workflow_stage"),
        "phase": _required_phase(phase),
        "command": _required_string(command, "command"),
        "repository_commit": _required_string(repository_commit, "repository_commit"),
        "created_at": _required_timestamp(created_at),
        "editorial_plan_sha256": file_sha256(editorial_plan_path),
        "article_sha256": file_sha256(article_path),
        "proof_sidecar_sha256": file_sha256(proof_sidecar_path),
        "agent_roster": list(AGENT_ROSTER),
        "agent_responses": [dict(response) for response in responses],
    }
    payload["artifact_hash"] = canonical_json_sha256(payload)
    return payload


def write_machine_review(path: str | Path, review: Mapping[str, Any]) -> None:
    """Persist a deterministic machine review JSON artifact."""
    payload = dict(review)
    payload.pop("artifact_hash", None)
    payload["artifact_hash"] = canonical_json_sha256(payload)
    atomic_write_json(path, payload)


def check_machine_review_file(
    path: str | Path,
    *,
    proof_sidecar_path: str | Path,
    editorial_plan_path: str | Path | None = None,
    article_path: str | Path | None = None,
    expected_run_id: str | None = None,
    expected_phase: str | None = None,
) -> list[Finding]:
    """Validate one review artifact and, when supplied, current input bytes."""
    try:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        return [
            _finding(
                "machine_review_unreadable",
                f"Machine review artifact is unreadable: {error}",
                "Regenerate the machine review from frozen current inputs.",
            )
        ]
    if not isinstance(payload, Mapping):
        return [
            _finding(
                "machine_review_root_invalid",
                "Machine review artifact must be a JSON object.",
                "Regenerate the machine review from frozen current inputs.",
            )
        ]
    findings = check_machine_review(payload)
    if expected_run_id is not None and payload.get("run_id") != expected_run_id:
        findings.append(
            _finding(
                "machine_review_run_id_mismatch",
                "Machine review run_id does not match the workflow run.",
                "Rerun every review agent against the current workflow run.",
            )
        )
    if expected_phase is not None and payload.get("phase") != expected_phase:
        findings.append(
            _finding(
                "machine_review_phase_mismatch",
                "Machine review phase does not match the expected review phase.",
                "Pass the correct plan-review or article-review artifact.",
            )
        )
    if editorial_plan_path is not None:
        findings.extend(
            _check_bound_file_hash(
                payload,
                "editorial_plan_sha256",
                editorial_plan_path,
                "machine_review_editorial_plan_hash_mismatch",
                "Machine review editorial-plan hash no longer matches the current file.",
            )
        )
    if article_path is not None:
        findings.extend(
            _check_bound_file_hash(
                payload,
                "article_sha256",
                article_path,
                "machine_review_article_hash_mismatch",
                "Machine review article hash no longer matches the current file.",
            )
        )
    findings.extend(
        _check_bound_file_hash(
            payload,
            "proof_sidecar_sha256",
            proof_sidecar_path,
            "machine_review_proof_sidecar_hash_mismatch",
            "Machine review proof-sidecar hash no longer matches the current file.",
        )
    )
    return _sorted(findings)


def check_machine_review_pair(
    plan_review_path: str | Path,
    article_review_path: str | Path,
    *,
    expected_run_id: str | None = None,
) -> list[Finding]:
    """Require plan and article reviews to share one workflow provenance identity."""
    payloads: dict[str, Mapping[str, Any]] = {}
    findings: list[Finding] = []
    for phase, path in (("plan", plan_review_path), ("article", article_review_path)):
        try:
            payload = json.loads(Path(path).read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as error:
            findings.append(
                _finding(
                    "machine_review_pair_unreadable",
                    f"Machine review {phase} artifact is unreadable: {error}",
                    "Regenerate both machine reviews from one workflow run.",
                )
            )
            continue
        if not isinstance(payload, Mapping):
            findings.append(
                _finding(
                    "machine_review_pair_root_invalid",
                    f"Machine review {phase} artifact must be a JSON object.",
                    "Regenerate both machine reviews from one workflow run.",
                )
            )
            continue
        payloads[phase] = payload
    if set(payloads) != {"plan", "article"}:
        return _sorted(findings)
    plan = payloads["plan"]
    article = payloads["article"]
    for field in PAIR_PROVENANCE_FIELDS:
        if plan.get(field) != article.get(field):
            findings.append(
                _finding(
                    f"machine_review_pair_{field}_mismatch",
                    f"Plan and article machine reviews have different {field} values.",
                    "Rerun both review phases within the same command and workflow run.",
                )
            )
    if expected_run_id is not None:
        for phase, payload in payloads.items():
            if payload.get("run_id") != expected_run_id:
                findings.append(
                    _finding(
                        "machine_review_release_run_id_mismatch",
                        f"Machine review {phase} run_id does not match the release run.",
                        "Rerun both review phases using the release run_id.",
                    )
                )
    return _sorted(findings)


def check_machine_review(payload: Mapping[str, Any]) -> list[Finding]:
    """Return blocking findings for one loaded machine-review artifact."""
    findings: list[Finding] = []
    unknown = set(payload) - TOP_LEVEL_FIELDS
    missing = TOP_LEVEL_FIELDS - set(payload)
    if missing:
        findings.append(
            _finding(
                "machine_review_shape_missing_fields",
                "Machine review is missing required fields: " + ", ".join(sorted(missing)),
                "Regenerate the machine review with the current schema.",
            )
        )
    if unknown:
        verdict_unknown = PROHIBITED_VERDICT_FIELDS.intersection(unknown)
        if verdict_unknown:
            findings.append(
                _finding(
                    "machine_review_release_verdict_prohibited",
                    "Machine review artifacts must not include a release verdict.",
                    "Remove release-verdict fields and let publish-readiness own release.",
                )
            )
        findings.append(
            _finding(
                "machine_review_shape_unknown_fields",
                "Machine review contains unsupported fields: " + ", ".join(sorted(unknown)),
                "Regenerate the machine review with the current schema.",
            )
        )
    if payload.get("schema") != SCHEMA:
        findings.append(
            _finding(
                "machine_review_schema_invalid",
                f"Machine review must use {SCHEMA}.",
                "Regenerate the machine review with the current schema.",
            )
        )
    for key in ("run_id", "workflow_stage", "command", "repository_commit"):
        if not isinstance(payload.get(key), str) or not str(payload.get(key)).strip():
            findings.append(
                _finding(
                    "machine_review_field_invalid",
                    f"Machine review {key} must be a non-empty string.",
                    "Regenerate the machine review from workflow metadata.",
                )
            )
    if payload.get("phase") not in PHASES:
        findings.append(
            _finding(
                "machine_review_phase_invalid",
                "Machine review phase must be plan or article.",
                "Regenerate the machine review for one supported phase.",
            )
        )
    if not isinstance(payload.get("created_at"), str) or RFC3339_UTC_RE.fullmatch(str(payload.get("created_at") or "")) is None:
        findings.append(
            _finding(
                "machine_review_created_at_invalid",
                "Machine review created_at must be an RFC 3339 UTC timestamp ending in Z.",
                "Regenerate the machine review with a current UTC timestamp.",
            )
        )
    for key in ("editorial_plan_sha256", "article_sha256", "proof_sidecar_sha256"):
        try:
            validate_sha256(payload.get(key), field=key)
        except ValueError:
            findings.append(
                _finding(
                    "machine_review_hash_invalid",
                    f"Machine review {key} must be a lowercase SHA-256 digest.",
                    "Regenerate the review from current input files.",
                )
            )
    if payload.get("agent_roster") != list(AGENT_ROSTER):
        findings.append(
            _finding(
                "machine_review_roster_invalid",
                "Machine review must use the fixed six-agent roster in order.",
                "Run Content Analyzer, Editor, SEO Optimizer, Meta Creator, Internal Linker, and Keyword Mapper.",
            )
        )
    findings.extend(_check_agent_responses(payload.get("agent_responses")))
    stored_hash = payload.get("artifact_hash")
    unsigned = dict(payload)
    unsigned.pop("artifact_hash", None)
    if not isinstance(stored_hash, str) or stored_hash != canonical_json_sha256(unsigned):
        findings.append(
            _finding(
                "machine_review_artifact_hash_invalid",
                "Machine review artifact_hash does not match the canonical review payload.",
                "Regenerate the immutable machine review artifact.",
            )
        )
    return _sorted(findings)


def machine_repair_decision(
    findings: Sequence[Mapping[str, Any]],
    *,
    completed_cycles: int,
) -> dict[str, Any]:
    """Return the next deterministic action for machine review repair loops."""
    if not isinstance(completed_cycles, int) or completed_cycles < 0:
        raise ValueError("completed_cycles must be a non-negative integer")
    unresolved = [dict(finding) for finding in findings]
    if not unresolved:
        return {
            "action": "continue_release",
            "exit_code": 0,
            "remaining_cycles": MAX_REPAIR_CYCLES - min(completed_cycles, MAX_REPAIR_CYCLES),
            "requires_human_review": False,
        }
    if completed_cycles < MAX_REPAIR_CYCLES:
        return {
            "action": "repair_and_rerun",
            "exit_code": 1,
            "remaining_cycles": MAX_REPAIR_CYCLES - completed_cycles,
            "requires_human_review": False,
        }
    return {
        "action": "write_research_blocker",
        "exit_code": 1,
        "remaining_cycles": 0,
        "requires_human_review": False,
    }


def build_machine_review_blocker(
    *,
    run_id: str,
    workflow_stage: str,
    phase: str,
    command: str,
    repository_commit: str,
    editorial_plan_path: str | Path,
    article_path: str | Path,
    completed_cycles: int,
    findings: Sequence[Mapping[str, Any]],
    created_at: str,
) -> dict[str, Any]:
    """Return a machine-readable research blocker for unresolved review findings."""
    decision = machine_repair_decision(findings, completed_cycles=completed_cycles)
    if decision["action"] != "write_research_blocker":
        raise ValueError("machine review blocker requires unresolved findings after two repair cycles")
    payload: dict[str, Any] = {
        "schema": BLOCKER_SCHEMA,
        "run_id": _required_string(run_id, "run_id"),
        "workflow_stage": _required_string(workflow_stage, "workflow_stage"),
        "phase": _required_phase(phase),
        "command": _required_string(command, "command"),
        "repository_commit": _required_string(repository_commit, "repository_commit"),
        "created_at": _required_timestamp(created_at),
        "editorial_plan_sha256": file_sha256(editorial_plan_path),
        "article_sha256": file_sha256(article_path),
        "status": "blocked",
        "repair_cycles_completed": completed_cycles,
        "next_action": "leave_article_in_place_and_return_nonzero",
        "requires_human_review": False,
        "review_required_path": None,
        "findings": [dict(finding) for finding in findings],
    }
    payload["artifact_hash"] = canonical_json_sha256(payload)
    return payload


def write_machine_review_blocker(path: str | Path, blocker: Mapping[str, Any]) -> None:
    """Persist a deterministic machine-review blocker artifact under research/."""
    payload = dict(blocker)
    payload.pop("artifact_hash", None)
    payload["artifact_hash"] = canonical_json_sha256(payload)
    atomic_write_json(path, payload)


def _check_agent_responses(value: Any) -> list[Finding]:
    findings: list[Finding] = []
    if not isinstance(value, list):
        return [
            _finding(
                "machine_review_agent_responses_invalid",
                "Machine review agent_responses must be a list.",
                "Collect exactly one structured response per review agent.",
            )
        ]
    seen: set[str] = set()
    for index, response in enumerate(value):
        if not isinstance(response, Mapping):
            findings.append(
                _finding(
                    "machine_review_agent_response_invalid",
                    f"Machine review agent response {index} must be an object.",
                    "Collect structured JSON from every review agent.",
                )
            )
            continue
        if PROHIBITED_VERDICT_FIELDS.intersection(response):
            findings.append(
                _finding(
                    "machine_review_release_verdict_prohibited",
                    "Machine review agent responses must not include release verdicts.",
                    "Remove release-verdict fields from reviewer output.",
                )
            )
        if set(response) != AGENT_RESPONSE_FIELDS:
            findings.append(
                _finding(
                    "machine_review_agent_response_shape_invalid",
                    f"Machine review agent response {index} has an invalid shape.",
                    "Use agent, status, and findings only.",
                )
            )
        agent = response.get("agent")
        if not isinstance(agent, str) or agent not in AGENT_ROSTER:
            findings.append(
                _finding(
                    "machine_review_agent_invalid",
                    f"Machine review agent response {index} uses an unknown agent.",
                    "Use the fixed six-agent roster names exactly.",
                )
            )
            continue
        if agent in seen:
            findings.append(
                _finding(
                    "machine_review_duplicate_agent",
                    f"Machine review contains duplicate response for {agent}.",
                    "Keep exactly one response per roster agent.",
                )
            )
        seen.add(agent)
        status = response.get("status")
        if status not in STATUSES:
            findings.append(
                _finding(
                    "machine_review_status_invalid",
                    f"Machine review status for {agent} is invalid.",
                    "Use completed, changes_requested, or blocked.",
                )
            )
        elif status != "completed":
            findings.append(
                _finding(
                    "machine_review_unresolved_status",
                    f"Machine review for {agent} is {status}.",
                    "Resolve requested changes or blockers and rerun machine review.",
                )
            )
        response_findings = response.get("findings")
        if status == "completed" and isinstance(response_findings, list) and response_findings:
            findings.append(
                _finding(
                    "machine_review_completed_with_findings",
                    f"Machine review for {agent} is completed but still contains findings.",
                    "Resolve every finding, then rerun the agent and return an empty findings list.",
                )
            )
        findings.extend(_check_findings(response_findings, agent=agent))
    missing = set(AGENT_ROSTER) - seen
    if missing:
        findings.append(
            _finding(
                "machine_review_missing_agent",
                "Machine review is missing agent responses: " + ", ".join(sorted(missing)),
                "Run every required machine reviewer against identical inputs.",
            )
        )
    return findings


def _check_findings(value: Any, *, agent: str) -> list[Finding]:
    findings: list[Finding] = []
    if not isinstance(value, list):
        return [
            _finding(
                "machine_review_findings_invalid",
                f"Machine review findings for {agent} must be a list.",
                "Return an empty findings list when no changes are requested.",
            )
        ]
    seen_ids: set[str] = set()
    for index, finding in enumerate(value):
        if not isinstance(finding, Mapping):
            findings.append(
                _finding(
                    "machine_review_finding_invalid",
                    f"Machine review finding {index} for {agent} must be an object.",
                    "Use the fixed finding shape.",
                )
            )
            continue
        if set(finding) != FINDING_FIELDS:
            findings.append(
                _finding(
                    "machine_review_finding_shape_invalid",
                    f"Machine review finding {index} for {agent} has an invalid shape.",
                    "Use id, priority, category, location, evidence_anchor, recommendation, proof_risk, and protected_span.",
                )
            )
        finding_id = finding.get("id")
        if not isinstance(finding_id, str) or not finding_id.strip():
            findings.append(
                _finding(
                    "machine_review_finding_id_invalid",
                    f"Machine review finding {index} for {agent} needs a stable ID.",
                    "Assign a stable finding ID.",
                )
            )
        elif finding_id in seen_ids:
            findings.append(
                _finding(
                    "machine_review_finding_id_duplicate",
                    f"Machine review finding ID {finding_id} is duplicated for {agent}.",
                    "Use unique stable finding IDs per agent response.",
                )
            )
        seen_ids.add(str(finding_id))
        if finding.get("priority") not in {"low", "medium", "high", "critical"}:
            findings.append(
                _finding(
                    "machine_review_finding_priority_invalid",
                    f"Machine review finding {finding_id or index} has an invalid priority.",
                    "Use low, medium, high, or critical.",
                )
            )
        for key in ("category", "location", "evidence_anchor", "recommendation", "proof_risk"):
            if not isinstance(finding.get(key), str) or not str(finding.get(key)).strip():
                findings.append(
                    _finding(
                        "machine_review_finding_field_invalid",
                        f"Machine review finding {finding_id or index} {key} must be a non-empty string.",
                        "Complete every required finding field.",
                    )
                )
        if not isinstance(finding.get("protected_span"), bool):
            findings.append(
                _finding(
                    "machine_review_finding_protected_span_invalid",
                    f"Machine review finding {finding_id or index} protected_span must be a boolean.",
                    "Mark whether the finding touches protected content.",
                )
            )
    return findings


def _check_bound_file_hash(
    payload: Mapping[str, Any],
    key: str,
    path: str | Path,
    rule_id: str,
    message: str,
) -> list[Finding]:
    try:
        current = file_sha256(path)
    except OSError as error:
        return [
            _finding(
                "machine_review_bound_file_unavailable",
                f"Machine review bound file is unavailable: {error}",
                "Restore the reviewed file or rerun machine review.",
            )
        ]
    if payload.get(key) == current:
        return []
    return [
        _finding(
            rule_id,
            message,
            "Rerun all six reviewers against the current bytes.",
        )
    ]


def _required_string(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a non-empty string")
    return value.strip()


def _required_phase(value: Any) -> str:
    if value not in PHASES:
        raise ValueError("phase must be plan or article")
    return str(value)


def _required_timestamp(value: Any) -> str:
    if not isinstance(value, str) or RFC3339_UTC_RE.fullmatch(value) is None:
        raise ValueError("created_at must be an RFC 3339 UTC timestamp ending in Z")
    return value


def _finding(rule_id: str, message: str, suggestion: str) -> Finding:
    return make_finding(
        rule_id,
        "error",
        1,
        message=message,
        suggestion=suggestion,
    )


def _sorted(findings: Sequence[Finding]) -> list[Finding]:
    return sorted(
        (dict(finding) for finding in findings),
        key=lambda finding: (
            str(finding.get("rule_id") or ""),
            str(finding.get("message") or ""),
        ),
    )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate a Simpro machine-review artifact.")
    parser.add_argument("path")
    parser.add_argument("--editorial-plan")
    parser.add_argument("--article")
    parser.add_argument("--proof-sidecar", required=True)
    parser.add_argument("--run-id")
    parser.add_argument("--phase", choices=sorted(PHASES))
    parser.add_argument("--json", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    findings = check_machine_review_file(
        args.path,
        proof_sidecar_path=args.proof_sidecar,
        editorial_plan_path=args.editorial_plan,
        article_path=args.article,
        expected_run_id=args.run_id,
        expected_phase=args.phase,
    )
    if args.json:
        print(json.dumps({"passed": not findings, "findings": findings}, indent=2))
    else:
        for finding in findings:
            print(f"{finding['rule_id']}: {finding['message']}")
    return 0 if not findings else 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main(sys.argv[1:]))
