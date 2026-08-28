from __future__ import annotations

import hashlib
import json
from pathlib import Path

from data_sources.modules.blog_assembly_contract import canonical_json_sha256
from data_sources.modules.machine_review import (
    AGENT_ROSTER,
    BLOCKER_SCHEMA,
    build_machine_review,
    build_machine_review_blocker,
    check_machine_review_file,
    machine_repair_decision,
    write_machine_review,
    write_machine_review_blocker,
)


def _inputs(tmp_path: Path) -> tuple[Path, Path, Path]:
    plan = tmp_path / "research" / "plan.json"
    sidecar = tmp_path / "research" / "validation-article.md"
    article = tmp_path / "rewrites" / "article.md"
    plan.parent.mkdir(parents=True, exist_ok=True); article.parent.mkdir(parents=True, exist_ok=True)
    plan.write_text('{"schema":"simpro-blog-editorial-plan/v1"}\n', encoding="utf-8")
    sidecar.write_text("## Source Map\n- Status: approved\n", encoding="utf-8")
    article.write_text("---\nartifact_type: blog\n---\n# Article\n", encoding="utf-8")
    return plan, article, sidecar


def _responses(status: str = "completed") -> list[dict[str, object]]:
    finding = {"id": "review-001", "priority": "high", "category": "proof", "location": "Plan", "evidence_anchor": "Missing source row", "recommendation": "Bind the missing source.", "proof_risk": "high", "protected_span": False}
    return [{"agent": agent, "status": status, "findings": [] if status == "completed" else [finding]} for agent in AGENT_ROSTER]


def _review(tmp_path: Path, status: str = "completed") -> tuple[Path, Path, Path, Path]:
    plan, article, sidecar = _inputs(tmp_path); output = tmp_path / "research" / "review.json"
    write_machine_review(output, build_machine_review(run_id="run-123", workflow_stage="rewrite", phase="article", command="/rewrite", repository_commit="abc123", editorial_plan_path=plan, article_path=article, proof_sidecar_path=sidecar, responses=_responses(status), created_at="2026-08-26T12:00:00Z"))
    return plan, article, sidecar, output


def test_machine_review_accepts_exact_roster_hashes_and_blocks_mutation(tmp_path: Path):
    plan, article, sidecar, output = _review(tmp_path)
    assert check_machine_review_file(output, editorial_plan_path=plan, article_path=article, proof_sidecar_path=sidecar, expected_run_id="run-123", expected_phase="article") == []
    loaded = json.loads(output.read_text(encoding="utf-8")); unsigned = dict(loaded); unsigned.pop("artifact_hash")
    assert loaded["artifact_hash"] == canonical_json_sha256(unsigned)
    assert loaded["proof_sidecar_sha256"] == hashlib.sha256(sidecar.read_bytes()).hexdigest()
    article.write_text("# Changed\n", encoding="utf-8")
    assert "machine_review_article_hash_mismatch" in {f["rule_id"] for f in check_machine_review_file(output, editorial_plan_path=plan, article_path=article, proof_sidecar_path=sidecar, expected_run_id="run-123", expected_phase="article")}


def test_machine_review_rejects_a_stale_proof_sidecar(tmp_path: Path):
    plan, article, sidecar, output = _review(tmp_path)

    sidecar.write_text("## Source Map\n- Status: changed after review\n", encoding="utf-8")

    rules = {
        finding["rule_id"]
        for finding in check_machine_review_file(
            output,
            editorial_plan_path=plan,
            article_path=article,
            proof_sidecar_path=sidecar,
            expected_run_id="run-123",
            expected_phase="article",
        )
    }
    assert "machine_review_proof_sidecar_hash_mismatch" in rules


def test_machine_review_rejects_missing_duplicate_blocked_and_verdict_fields(tmp_path: Path):
    plan, article, sidecar = _inputs(tmp_path)
    payload = build_machine_review(run_id="run-123", workflow_stage="rewrite", phase="plan", command="/rewrite", repository_commit="abc123", editorial_plan_path=plan, article_path=article, proof_sidecar_path=sidecar, responses=[*_responses()[:-1], _responses("blocked")[0]], created_at="2026-08-26T12:00:00Z")
    payload["agent_responses"].append(payload["agent_responses"][0]); payload["release_verdict"] = "ready"
    output = tmp_path / "review.json"; output.write_text(json.dumps(payload), encoding="utf-8")
    rules = {f["rule_id"] for f in check_machine_review_file(output, editorial_plan_path=plan, article_path=article, proof_sidecar_path=sidecar, expected_run_id="run-123", expected_phase="plan")}
    assert {"machine_review_duplicate_agent", "machine_review_missing_agent", "machine_review_unresolved_status", "machine_review_release_verdict_prohibited"} <= rules


def test_completed_agent_cannot_hide_unresolved_findings(tmp_path: Path):
    plan, article, sidecar = _inputs(tmp_path)
    responses = _responses()
    responses[0]["findings"] = [
        {
            "id": "proof-001",
            "priority": "critical",
            "category": "proof",
            "location": "Renewal paragraph",
            "evidence_anchor": "Unsupported deadline",
            "recommendation": "Add the approved authority link.",
            "proof_risk": "high",
            "protected_span": True,
        }
    ]
    output = tmp_path / "review-with-hidden-finding.json"
    write_machine_review(
        output,
        build_machine_review(
            run_id="run-123",
            workflow_stage="rewrite",
            phase="article",
            command="/rewrite",
            repository_commit="abc123",
            editorial_plan_path=plan,
            article_path=article,
            proof_sidecar_path=sidecar,
            responses=responses,
            created_at="2026-08-26T12:00:00Z",
        ),
    )

    rules = {
        finding["rule_id"]
        for finding in check_machine_review_file(
            output,
            editorial_plan_path=plan,
            article_path=article,
            proof_sidecar_path=sidecar,
            expected_run_id="run-123",
            expected_phase="article",
        )
    }

    assert "machine_review_completed_with_findings" in rules


def test_machine_review_two_cycles_end_in_research_blocker_without_human_handoff(tmp_path: Path):
    plan, article, _ = _inputs(tmp_path)
    findings = [{"rule_id": "machine_review_unresolved_status", "severity": "error", "message": "Editor requested changes.", "suggestion": "Resolve and rerun."}]
    assert machine_repair_decision(findings, completed_cycles=0)["action"] == "repair_and_rerun"
    assert machine_repair_decision(findings, completed_cycles=1)["action"] == "repair_and_rerun"
    assert machine_repair_decision(findings, completed_cycles=2)["action"] == "write_research_blocker"
    output = tmp_path / "research" / "machine-review-blocker.json"
    write_machine_review_blocker(output, build_machine_review_blocker(run_id="run-123", workflow_stage="rewrite", phase="article", command="/rewrite", repository_commit="abc123", editorial_plan_path=plan, article_path=article, completed_cycles=2, findings=findings, created_at="2026-08-26T12:00:00Z"))
    loaded = json.loads(output.read_text(encoding="utf-8"))
    assert loaded["schema"] == BLOCKER_SCHEMA
    assert loaded["next_action"] == "leave_article_in_place_and_return_nonzero"
    assert loaded["requires_human_review"] is False
    assert loaded["review_required_path"] is None
