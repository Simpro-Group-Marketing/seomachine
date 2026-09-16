from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from data_sources.modules.blog_assembly.common import canonical_artifact
from data_sources.modules.machine_review import (
    AGENT_ROSTER,
    build_machine_review,
    write_machine_review,
)
from data_sources.modules.release_workflow.chain_decision import (
    DRAFT_READY_NOT_RELEASE_READY,
    NORMAL_CHAIN_REQUIRED,
    OPTIMIZED_TAIL_ALLOWED,
    decide_release_chain,
)


OPTIMIZED_TAIL_RECEIPTS = (
    {"stage": "post_optimization_scrub"},
    {"stage": "post_optimization_context_binding"},
)


def _write_text(path: Path, content: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def _write_json(path: Path, payload: object) -> Path:
    return _write_text(path, json.dumps(payload, indent=2) + "\n")


def _completed_responses() -> list[dict[str, Any]]:
    return [
        {"agent": agent, "status": "completed", "findings": []}
        for agent in AGENT_ROSTER
    ]


def _case_inputs(tmp_path: Path) -> dict[str, Any]:
    plan = _write_json(
        tmp_path / "research" / "plan.json",
        {"schema": "simpro-blog-editorial-plan/v2"},
    )
    article = _write_text(
        tmp_path / "rewrites" / "article.md",
        "---\nartifact_type: blog\n---\n# Current article\n",
    )
    sidecar = _write_text(
        tmp_path / "research" / "validation-article.md",
        "## Source Map\n- Status: approved\n",
    )
    scorecard = _write_json(
        tmp_path / "research" / "initial-scorecard.json",
        {"passed": True},
    )
    agent_output = _write_text(
        tmp_path / "research" / "agent-outputs" / "content-analyzer.md",
        "# Current diagnostics\n",
    )
    execution_evidence = {
        "command_definition.write-command": {
            "path": ".claude/commands/write.md",
            "sha256": "a" * 64,
        },
        "agent_output.content-analyzer": canonical_artifact(
            agent_output,
            workspace_root=tmp_path,
        ),
    }
    prior_bom = _write_json(
        tmp_path / "research" / "prior-bom.json",
        {"artifacts": {"execution_evidence": execution_evidence}},
    )
    prior_preflight = _write_json(
        tmp_path / "research" / "prior-preflight.json",
        {
            "input_hashes": {
                "assembly_bom": canonical_artifact(
                    prior_bom,
                    workspace_root=tmp_path,
                )
            }
        },
    )
    optimizer_output = _write_json(
        tmp_path / "research" / "optimizer-output.json",
        {
            "schema": "simpro-optimizer-output/v2",
            "status": "completed",
            "input_bindings": {
                label: canonical_artifact(path, workspace_root=tmp_path)
                for label, path in {
                    "article": article,
                    "editorial_plan": plan,
                    "proof_sidecar": sidecar,
                    "scorecard": scorecard,
                    "prior_preflight_readiness": prior_preflight,
                }.items()
            },
        },
    )
    review_paths: dict[str, Path] = {}
    for phase in ("plan", "article"):
        review_path = tmp_path / "research" / f"machine-review-{phase}.json"
        review = build_machine_review(
            run_id="run-123",
            workflow_stage="rewrite",
            phase=phase,
            command="/rewrite",
            repository_commit="abc123",
            editorial_plan_path=plan,
            article_path=article,
            proof_sidecar_path=sidecar,
            responses=_completed_responses(),
            created_at="2026-09-16T12:00:00Z",
        )
        write_machine_review(review_path, review)
        review_paths[phase] = review_path
    return {
        "article_path": article,
        "editorial_plan_path": plan,
        "proof_sidecar_path": sidecar,
        "machine_review_paths": review_paths,
        "machine_review_collection_statuses": {
            "plan": "review_collected",
            "article": "review_collected",
        },
        "optimizer_output_paths": (optimizer_output,),
        "prior_preflight_readiness_path": prior_preflight,
        "stage_receipts": OPTIMIZED_TAIL_RECEIPTS,
        "agent_output_paths": {"content-analyzer": agent_output},
        "run_id": "run-123",
        "workspace_root": tmp_path,
    }


@pytest.mark.parametrize(
    ("case", "expected_decision", "expected_code"),
    (
        ("fresh_rewrite", NORMAL_CHAIN_REQUIRED, "optimized_tail_evidence_absent"),
        ("valid_optimized_tail", OPTIMIZED_TAIL_ALLOWED, "optimized_tail_evidence_valid"),
        ("stale_optimizer", NORMAL_CHAIN_REQUIRED, "optimizer_output_stale"),
        ("stale_execution", NORMAL_CHAIN_REQUIRED, "execution_evidence_stale"),
        (
            "incomplete_review_collection",
            DRAFT_READY_NOT_RELEASE_READY,
            "machine_review_collection_incomplete",
        ),
        (
            "mismatched_review_collection",
            DRAFT_READY_NOT_RELEASE_READY,
            "machine_review_collection_mismatch",
        ),
    ),
)
def test_release_chain_decision_table(
    tmp_path: Path,
    case: str,
    expected_decision: str,
    expected_code: str,
) -> None:
    inputs = _case_inputs(tmp_path)
    if case == "fresh_rewrite":
        inputs["optimizer_output_paths"] = ()
        inputs["prior_preflight_readiness_path"] = None
    elif case == "stale_optimizer":
        optimizer_path = inputs["optimizer_output_paths"][0]
        payload = json.loads(optimizer_path.read_text(encoding="utf-8"))
        payload["input_bindings"]["article"]["sha256"] = "0" * 64
        _write_json(optimizer_path, payload)
    elif case == "stale_execution":
        inputs["agent_output_paths"]["content-analyzer"].write_text(
            "# Changed diagnostics\n",
            encoding="utf-8",
        )
    elif case == "incomplete_review_collection":
        inputs["machine_review_collection_statuses"]["article"] = (
            DRAFT_READY_NOT_RELEASE_READY
        )
    elif case == "mismatched_review_collection":
        inputs["machine_review_collection_statuses"].pop("article")

    result = decide_release_chain(**inputs)

    assert result.decision == expected_decision
    assert result.code == expected_code
    assert result.reason


def test_mismatched_current_machine_review_is_not_release_ready(tmp_path: Path) -> None:
    inputs = _case_inputs(tmp_path)
    inputs["article_path"].write_text(
        "---\nartifact_type: blog\n---\n# Changed after review\n",
        encoding="utf-8",
    )

    result = decide_release_chain(**inputs)

    assert result.decision == DRAFT_READY_NOT_RELEASE_READY
    assert result.code == "machine_review_invalid"
    assert "machine_review_article_hash_mismatch" in result.blockers
