from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from data_sources.modules.blog_assembly.common import (
    artifact_inventory_snapshots,
    canonical_artifact,
    canonical_json_sha256,
    expected_blog_gate_inventory,
    file_sha256,
)
from data_sources.modules.blog_assembly_stage_receipt import (
    build_stage_receipt,
    load_stage_receipt,
    receipt_hash,
    stage_evidence_path,
    write_stage_receipt,
)
from data_sources.modules.machine_review import (
    AGENT_ROSTER,
    build_machine_review,
    write_machine_review,
)
from data_sources.modules.machine_review_workflow import COLLECTION_REPORT_SCHEMA
from data_sources.modules.readiness.persistence_api import (
    readiness_stage_receipt_path,
)
from data_sources.modules.release_workflow.chain_decision import (
    DRAFT_READY_NOT_RELEASE_READY,
    NORMAL_CHAIN_REQUIRED,
    OPTIMIZED_TAIL_ALLOWED,
    decide_release_chain,
)
from tests.release_chain_test_support import write_optimized_tail_receipts

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


def _write_collection_report(
    path: Path,
    *,
    phase: str,
    review_path: Path,
    plan: Path,
    article: Path,
    sidecar: Path,
) -> Path:
    payload = {
        "schema": COLLECTION_REPORT_SCHEMA,
        "status": "review_collected",
        "run_id": "run-123",
        "workflow_stage": "rewrite",
        "phase": phase,
        "command": "/rewrite",
        "repository_commit": "abc123",
        "editorial_plan_sha256": file_sha256(plan),
        "article_sha256": file_sha256(article),
        "proof_sidecar_sha256": file_sha256(sidecar),
        "collected_agents": list(AGENT_ROSTER),
        "issues": [],
        "review_path": str(review_path),
        "review_sha256": file_sha256(review_path),
    }
    payload["artifact_hash"] = canonical_json_sha256(payload)
    return _write_json(path, payload)


def _write_prior_preflight(
    tmp_path: Path,
    *,
    article: Path,
    agent_output: Path,
) -> Path:
    artifacts = {
        "article": canonical_artifact(article, workspace_root=tmp_path),
        "execution_evidence": {
            "agent_output.content-analyzer": canonical_artifact(
                agent_output,
                workspace_root=tmp_path,
            ),
        },
    }
    prior_bom = _write_json(
        tmp_path / "research" / "prior-bom.json",
        {
            "schema": "simpro-blog-assembly-bom/v4",
            "lifecycle_state": "provisional",
            "schema_policy": {"visible_faq": False},
            "connector_binding": {"status": "not_required"},
            "artifacts": artifacts,
        },
    )
    input_rows = {
        "assembly_bom": canonical_artifact(prior_bom, workspace_root=tmp_path),
        **artifact_inventory_snapshots(artifacts),
    }
    gate_inventory = expected_blog_gate_inventory(
        visible_faq=False,
        connector_required=False,
        current_strategy=True,
    )
    readiness = {
        "schema": "simpro-publish-readiness-result/v1",
        "tool": {"name": "publish_readiness", "version": "1.0.0"},
        "phase": "preflight",
        "passed": True,
        "artifact_kind": "blog",
        "verification_scope": "source_artifact",
        "input_seal": {"status": "verified"},
        "gate_inventory": gate_inventory,
        "gates": [
            {
                "name": name,
                "passed": True,
                "errors": 0,
                "blockers": [],
            }
            for name in gate_inventory
        ],
        "score": 95,
        "score_threshold": 85,
        "aeo_geo": {"score": 95, "threshold": 90, "passed": True},
        "input_hashes": input_rows,
        "run_id": "run-123",
        "started_at": "2026-01-15T12:00:00Z",
        "completed_at": "2026-01-15T12:01:00Z",
    }
    readiness_path = _write_json(
        tmp_path / "research" / "prior-preflight.json",
        readiness,
    )
    input_hashes = {
        label: row["sha256"] for label, row in input_rows.items()
    }
    receipt = build_stage_receipt(
        run_id="run-123",
        stage="preflight_readiness",
        tool_name="publish_readiness",
        tool_version="1.0.0",
        started_at=readiness["started_at"],
        completed_at=readiness["completed_at"],
        mutation=False,
        input_artifact_hashes=input_hashes,
        output_artifact_hashes={
            "article": input_hashes["article"],
            "readiness_output": file_sha256(readiness_path),
        },
        workspace_root=tmp_path,
    )
    write_stage_receipt(
        readiness_stage_receipt_path(readiness_path),
        receipt,
        workspace_root=tmp_path,
    )
    return readiness_path


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
    prior_preflight = _write_prior_preflight(
        tmp_path,
        article=article,
        agent_output=agent_output,
    )
    article.write_text(
        "---\nartifact_type: blog\n---\n# Current optimized article\n",
        encoding="utf-8",
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
    report_paths: dict[str, Path] = {}
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
        report_paths[phase] = _write_collection_report(
            tmp_path / "research" / f"machine-review-{phase}-collection.json",
            phase=phase,
            review_path=review_path,
            plan=plan,
            article=article,
            sidecar=sidecar,
        )
    receipt_paths = write_optimized_tail_receipts(
        tmp_path,
        article=article,
        sidecar=sidecar,
        prior_preflight=prior_preflight,
    )
    return {
        "article_path": article,
        "editorial_plan_path": plan,
        "proof_sidecar_path": sidecar,
        "machine_review_paths": review_paths,
        "machine_review_collection_report_paths": report_paths,
        "optimizer_output_paths": (optimizer_output,),
        "prior_preflight_readiness_path": prior_preflight,
        "stage_receipt_paths": receipt_paths,
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
        (
            "tampered_collection_report",
            DRAFT_READY_NOT_RELEASE_READY,
            "machine_review_collection_invalid",
        ),
        (
            "minimal_receipts",
            NORMAL_CHAIN_REQUIRED,
            "optimized_tail_receipts_invalid",
        ),
        (
            "minimal_prior_preflight",
            NORMAL_CHAIN_REQUIRED,
            "optimized_tail_receipts_invalid",
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
        report_path = inputs["machine_review_collection_report_paths"]["article"]
        payload = json.loads(report_path.read_text(encoding="utf-8"))
        payload["status"] = DRAFT_READY_NOT_RELEASE_READY
        payload.pop("artifact_hash")
        payload["artifact_hash"] = canonical_json_sha256(payload)
        _write_json(report_path, payload)
    elif case == "mismatched_review_collection":
        inputs["machine_review_collection_report_paths"].pop("article")
    elif case == "tampered_collection_report":
        report_path = inputs["machine_review_collection_report_paths"]["article"]
        payload = json.loads(report_path.read_text(encoding="utf-8"))
        payload["review_sha256"] = "0" * 64
        _write_json(report_path, payload)
    elif case == "minimal_receipts":
        inputs["stage_receipt_paths"] = (
            _write_json(
                tmp_path / "research" / "minimal-scrub.json",
                {"stage": "post_optimization_scrub"},
            ),
            _write_json(
                tmp_path / "research" / "minimal-binding.json",
                {"stage": "post_optimization_context_binding"},
            ),
        )
    elif case == "minimal_prior_preflight":
        _write_json(
            inputs["prior_preflight_readiness_path"],
            {"input_hashes": {}},
        )

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
    assert result.code == "machine_review_collection_invalid"
    assert "machine_review_collection_report_binding_mismatch" in result.blockers


def test_tampered_receipt_chain_requires_normal_chain(tmp_path: Path) -> None:
    inputs = _case_inputs(tmp_path)
    binding_path = inputs["stage_receipt_paths"][2]
    payload = json.loads(binding_path.read_text(encoding="utf-8"))
    payload["previous_receipt_hash"] = "0" * 64
    payload.pop("receipt_hash")
    payload["receipt_hash"] = receipt_hash(payload)
    _write_json(binding_path, payload)

    result = decide_release_chain(**inputs)

    assert result.decision == NORMAL_CHAIN_REQUIRED
    assert result.code == "optimized_tail_receipts_invalid"


def test_missing_tail_evidence_requires_normal_chain(tmp_path: Path) -> None:
    inputs = _case_inputs(tmp_path)
    stage_evidence_path(inputs["stage_receipt_paths"][1]).unlink()

    result = decide_release_chain(**inputs)

    assert result.decision == NORMAL_CHAIN_REQUIRED
    assert result.code == "optimized_tail_receipts_invalid"


def test_arbitrary_external_predecessor_requires_normal_chain(tmp_path: Path) -> None:
    inputs = _case_inputs(tmp_path)
    scrub_path, binding_path = inputs["stage_receipt_paths"][1:]
    scrub = load_stage_receipt(scrub_path, workspace_root=tmp_path)
    replacement_scrub = build_stage_receipt(
        run_id=scrub["run_id"],
        stage=scrub["stage"],
        tool_name=scrub["tool"]["name"],
        tool_version=scrub["tool"]["version"],
        started_at=scrub["started_at"],
        completed_at=scrub["completed_at"],
        mutation=scrub["mutation"],
        input_artifact_hashes=scrub["input_artifact_hashes"],
        output_artifact_hashes=scrub["output_artifact_hashes"],
        evidence_hashes=scrub["evidence_hashes"],
        previous_receipt_hash="a" * 64,
        workspace_root=tmp_path,
    )
    write_stage_receipt(scrub_path, replacement_scrub, workspace_root=tmp_path)
    binding = load_stage_receipt(binding_path, workspace_root=tmp_path)
    replacement_binding = build_stage_receipt(
        run_id=binding["run_id"],
        stage=binding["stage"],
        tool_name=binding["tool"]["name"],
        tool_version=binding["tool"]["version"],
        started_at=binding["started_at"],
        completed_at=binding["completed_at"],
        mutation=binding["mutation"],
        input_artifact_hashes=binding["input_artifact_hashes"],
        output_artifact_hashes=binding["output_artifact_hashes"],
        evidence_hashes=binding["evidence_hashes"],
        previous_receipt_hash=replacement_scrub["receipt_hash"],
        workspace_root=tmp_path,
    )
    write_stage_receipt(binding_path, replacement_binding, workspace_root=tmp_path)
    inputs["stage_receipt_paths"] = (scrub_path, binding_path)

    result = decide_release_chain(**inputs)

    assert result.decision == NORMAL_CHAIN_REQUIRED
    assert result.code == "optimized_tail_receipts_invalid"


def test_collection_report_does_not_replace_review_validation(tmp_path: Path) -> None:
    inputs = _case_inputs(tmp_path)
    review_path = inputs["machine_review_paths"]["article"]
    review = json.loads(review_path.read_text(encoding="utf-8"))
    review["article_sha256"] = "0" * 64
    write_machine_review(review_path, review)
    report_path = inputs["machine_review_collection_report_paths"]["article"]
    report = json.loads(report_path.read_text(encoding="utf-8"))
    report["review_sha256"] = file_sha256(review_path)
    report.pop("artifact_hash")
    report["artifact_hash"] = canonical_json_sha256(report)
    _write_json(report_path, report)

    result = decide_release_chain(**inputs)

    assert result.decision == DRAFT_READY_NOT_RELEASE_READY
    assert result.code == "machine_review_invalid"
    assert "machine_review_article_hash_mismatch" in result.blockers
