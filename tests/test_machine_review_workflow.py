from __future__ import annotations

import json
from pathlib import Path

import data_sources.modules.machine_review_workflow as workflow
from data_sources.modules.machine_review import AGENT_ROSTER, check_machine_review_file
from data_sources.modules.machine_review_workflow import (
    AGENT_RESPONSE_SCHEMA,
    COLLECTION_REPORT_SCHEMA,
    build_agent_response,
    main,
    write_agent_response,
)


RUN_METADATA = {
    "run_id": "run-123",
    "workflow_stage": "rewrite",
    "phase": "article",
    "command": "/rewrite",
    "repository_commit": "abc123",
}


def _inputs(tmp_path: Path) -> tuple[Path, Path, Path]:
    plan = tmp_path / "research" / "plan.json"
    article = tmp_path / "rewrites" / "article.md"
    sidecar = tmp_path / "research" / "validation-article.md"
    plan.parent.mkdir(parents=True)
    article.parent.mkdir(parents=True)
    plan.write_text('{"schema":"simpro-blog-editorial-plan/v2"}\n', encoding="utf-8")
    article.write_text("---\nartifact_type: blog\n---\n# Article\n", encoding="utf-8")
    sidecar.write_text("## Source Map\n- Status: approved\n", encoding="utf-8")
    return plan, article, sidecar


def _response_files(
    tmp_path: Path,
    plan: Path,
    article: Path,
    sidecar: Path,
) -> list[Path]:
    paths: list[Path] = []
    for index, agent in enumerate(AGENT_ROSTER):
        path = tmp_path / "responses" / f"response-{index}.json"
        response = build_agent_response(
            **RUN_METADATA,
            editorial_plan_path=plan,
            article_path=article,
            proof_sidecar_path=sidecar,
            agent=agent,
            status="completed",
            findings=[],
        )
        assert response["schema"] == AGENT_RESPONSE_SCHEMA
        write_agent_response(path, response)
        paths.append(path)
    return paths


def _cli_args(
    plan: Path,
    article: Path,
    sidecar: Path,
    output: Path,
    report: Path,
    responses: list[Path],
) -> list[str]:
    return [
        "--run-id",
        RUN_METADATA["run_id"],
        "--workflow-stage",
        RUN_METADATA["workflow_stage"],
        "--phase",
        RUN_METADATA["phase"],
        "--command",
        RUN_METADATA["command"],
        "--repository-commit",
        RUN_METADATA["repository_commit"],
        "--editorial-plan",
        str(plan),
        "--article",
        str(article),
        "--proof-sidecar",
        str(sidecar),
        "--created-at",
        "2026-09-16T12:00:00Z",
        "--output",
        str(output),
        "--report",
        str(report),
        *[str(path) for path in responses],
    ]


def test_six_hash_bound_agent_responses_produce_existing_review_artifact(tmp_path: Path):
    plan, article, sidecar = _inputs(tmp_path)
    responses = _response_files(tmp_path, plan, article, sidecar)
    output = tmp_path / "research" / "machine-review-article.json"
    report = tmp_path / "research" / "machine-review-collection.json"

    exit_code = main(_cli_args(plan, article, sidecar, output, report, responses))

    assert exit_code == 0
    assert check_machine_review_file(
        output,
        editorial_plan_path=plan,
        article_path=article,
        proof_sidecar_path=sidecar,
        expected_run_id=RUN_METADATA["run_id"],
        expected_phase=RUN_METADATA["phase"],
    ) == []
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert [response["agent"] for response in payload["agent_responses"]] == list(AGENT_ROSTER)
    assert json.loads(report.read_text(encoding="utf-8"))["status"] == "review_collected"


def test_missing_role_is_draft_ready_not_release_ready_without_synthetic_response(tmp_path: Path):
    plan, article, sidecar = _inputs(tmp_path)
    responses = _response_files(tmp_path, plan, article, sidecar)[:-1]
    output = tmp_path / "research" / "machine-review-article.json"
    report = tmp_path / "research" / "machine-review-collection.json"

    exit_code = main(_cli_args(plan, article, sidecar, output, report, responses))

    assert exit_code != 0
    assert not output.exists()
    payload = json.loads(report.read_text(encoding="utf-8"))
    assert payload["schema"] == COLLECTION_REPORT_SCHEMA
    assert payload["status"] == "draft_ready_not_release_ready"
    assert "machine_review_response_missing_role" in {
        issue["code"] for issue in payload["issues"]
    }
    assert payload["collected_agents"] == list(AGENT_ROSTER[:-1])


def test_missing_role_removes_pre_existing_successful_review(tmp_path: Path):
    plan, article, sidecar = _inputs(tmp_path)
    responses = _response_files(tmp_path, plan, article, sidecar)
    output = tmp_path / "research" / "machine-review-article.json"
    report = tmp_path / "research" / "machine-review-collection.json"
    args = _cli_args(plan, article, sidecar, output, report, responses)
    assert main(args) == 0
    assert check_machine_review_file(
        output,
        editorial_plan_path=plan,
        article_path=article,
        proof_sidecar_path=sidecar,
        expected_run_id=RUN_METADATA["run_id"],
        expected_phase=RUN_METADATA["phase"],
    ) == []

    exit_code = main(_cli_args(plan, article, sidecar, output, report, responses[:-1]))

    assert exit_code != 0
    assert not output.exists()
    payload = json.loads(report.read_text(encoding="utf-8"))
    assert payload["status"] == "draft_ready_not_release_ready"
    assert payload["review_path"] is None
    assert payload["review_sha256"] is None


def test_duplicate_role_is_draft_ready_not_release_ready(tmp_path: Path):
    plan, article, sidecar = _inputs(tmp_path)
    responses = _response_files(tmp_path, plan, article, sidecar)
    duplicate = json.loads(responses[-1].read_text(encoding="utf-8"))
    duplicate["agent"] = AGENT_ROSTER[0]
    write_agent_response(responses[-1], duplicate)
    output = tmp_path / "research" / "machine-review-article.json"
    report = tmp_path / "research" / "machine-review-collection.json"

    exit_code = main(_cli_args(plan, article, sidecar, output, report, responses))

    assert exit_code != 0
    assert not output.exists()
    payload = json.loads(report.read_text(encoding="utf-8"))
    assert payload["status"] == "draft_ready_not_release_ready"
    codes = {issue["code"] for issue in payload["issues"]}
    assert "machine_review_response_duplicate_role" in codes
    assert "machine_review_response_missing_role" in codes


def test_stale_and_wrong_run_responses_fail_without_completed_substitutes(tmp_path: Path):
    plan, article, sidecar = _inputs(tmp_path)
    responses = _response_files(tmp_path, plan, article, sidecar)
    stale = json.loads(responses[0].read_text(encoding="utf-8"))
    stale["run_id"] = "wrong-run"
    stale["article_sha256"] = "0" * 64
    write_agent_response(responses[0], stale)
    output = tmp_path / "research" / "machine-review-article.json"
    report = tmp_path / "research" / "machine-review-collection.json"

    exit_code = main(_cli_args(plan, article, sidecar, output, report, responses))

    assert exit_code != 0
    assert not output.exists()
    payload = json.loads(report.read_text(encoding="utf-8"))
    assert payload["status"] == "draft_ready_not_release_ready"
    codes = {issue["code"] for issue in payload["issues"]}
    assert "machine_review_response_run_id_mismatch" in codes
    assert "machine_review_response_article_sha256_mismatch" in codes
    assert len(payload["collected_agents"]) == len(AGENT_ROSTER) - 1


def test_input_mutation_before_final_build_fails_closed(
    tmp_path: Path,
    monkeypatch,
):
    plan, article, sidecar = _inputs(tmp_path)
    responses = _response_files(tmp_path, plan, article, sidecar)
    output = tmp_path / "research" / "machine-review-article.json"
    report = tmp_path / "research" / "machine-review-collection.json"
    original_build = workflow.build_machine_review

    def mutate_article_then_build(**kwargs):
        article.write_text("# Changed after response validation\n", encoding="utf-8")
        return original_build(**kwargs)

    monkeypatch.setattr(workflow, "build_machine_review", mutate_article_then_build)

    exit_code = main(_cli_args(plan, article, sidecar, output, report, responses))

    assert exit_code != 0
    assert not output.exists()
    payload = json.loads(report.read_text(encoding="utf-8"))
    assert payload["status"] == "draft_ready_not_release_ready"
    assert "machine_review_input_changed_during_collection" in {
        issue["code"] for issue in payload["issues"]
    }


def test_blocked_response_fails_closed(tmp_path: Path):
    plan, article, sidecar = _inputs(tmp_path)
    responses = _response_files(tmp_path, plan, article, sidecar)
    blocked = json.loads(responses[0].read_text(encoding="utf-8"))
    blocked["status"] = "blocked"
    blocked["findings"] = [
        {
            "id": "proof-001",
            "priority": "high",
            "category": "proof",
            "location": "Article",
            "evidence_anchor": "Missing proof",
            "recommendation": "Add approved proof.",
            "proof_risk": "high",
            "protected_span": False,
        }
    ]
    write_agent_response(responses[0], blocked)
    output = tmp_path / "research" / "machine-review-article.json"
    report = tmp_path / "research" / "machine-review-collection.json"

    exit_code = main(_cli_args(plan, article, sidecar, output, report, responses))

    assert exit_code != 0
    assert not output.exists()
    codes = {
        issue["code"]
        for issue in json.loads(report.read_text(encoding="utf-8"))["issues"]
    }
    assert "machine_review_unresolved_status" in codes


def test_invalid_response_artifact_hash_fails_closed(tmp_path: Path):
    plan, article, sidecar = _inputs(tmp_path)
    responses = _response_files(tmp_path, plan, article, sidecar)
    invalid = json.loads(responses[0].read_text(encoding="utf-8"))
    invalid["artifact_hash"] = "0" * 64
    responses[0].write_text(json.dumps(invalid), encoding="utf-8")
    output = tmp_path / "research" / "machine-review-article.json"
    report = tmp_path / "research" / "machine-review-collection.json"

    exit_code = main(_cli_args(plan, article, sidecar, output, report, responses))

    assert exit_code != 0
    assert not output.exists()
    codes = {
        issue["code"]
        for issue in json.loads(report.read_text(encoding="utf-8"))["issues"]
    }
    assert "machine_review_response_artifact_hash_invalid" in codes
