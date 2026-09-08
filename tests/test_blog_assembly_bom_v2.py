from __future__ import annotations

import hashlib
from datetime import date
from pathlib import Path

import pytest

from data_sources.modules import blog_assembly_contract
from data_sources.modules.blog_assembly_bom import build_blog_assembly_bom_from_files
from data_sources.modules.blog_assembly_bom_guard import check_bom
from data_sources.modules.machine_review import AGENT_ROSTER, build_machine_review, write_machine_review
from tests.test_blog_assembly_bom import _fixture


@pytest.fixture(autouse=True)
def _freeze_clock(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(blog_assembly_contract, "current_utc_date", lambda: date(2026, 8, 11))


def _reviews(tmp_path: Path, paths: dict[str, Path]) -> tuple[Path, Path]:
    responses = [{"agent": agent, "status": "completed", "findings": []} for agent in AGENT_ROSTER]
    output = []
    for phase in ("plan", "article"):
        path = tmp_path / "research" / f"machine-review-{phase}.json"
        write_machine_review(path, build_machine_review(run_id="run-1", workflow_stage="rewrite", phase=phase, command="/rewrite", repository_commit="abc123", editorial_plan_path=paths["editorial_plan"], article_path=paths["article"], proof_sidecar_path=paths["sidecar"], responses=responses, created_at="2026-08-11T14:00:00Z"))
        output.append(path)
    return output[0], output[1]


def _build(paths: dict[str, Path], plan_review: Path, article_review: Path, tmp_path: Path):
    return build_blog_assembly_bom_from_files(
        article_path=paths["article"],
        validation_sidecar_path=paths["sidecar"],
        editorial_plan_path=paths["editorial_plan"],
        keyword_decision_path=paths["keyword_decision"],
        serp_evidence_path=paths["serp"],
        paa_artifact_path=paths["paa"],
        plan_review_path=plan_review,
        article_review_path=article_review,
        agent_output_paths=paths["agent_outputs"],
        stage_receipt_paths=paths["stage_receipts"],
        workflow_mode="new",
        assembly_date="2026-08-11",
        workspace_root=tmp_path,
    )


def test_bom_v2_binds_machine_reviews_and_rejects_stale_article_review(tmp_path: Path):
    paths = _fixture(tmp_path); plan_review, article_review = _reviews(tmp_path, paths)
    bom = _build(paths, plan_review, article_review, tmp_path)
    assert bom["schema"] == "simpro-blog-assembly-bom/v2"
    assert set(bom["machine_reviews"]) == {"plan", "article"}
    assert check_bom(bom, article_path=paths["article"], validation_sidecar_path=paths["sidecar"], workspace_root=tmp_path, expected_lifecycle_state="provisional") == []
    paths["article"].write_text(paths["article"].read_text(encoding="utf-8") + "\nChanged after review.\n", encoding="utf-8")
    with pytest.raises(ValueError, match="machine_review_article_hash_mismatch"):
        _build(paths, plan_review, article_review, tmp_path)


def test_bom_v2_rejects_machine_reviews_bound_to_a_stale_validation_sidecar(tmp_path: Path):
    paths = _fixture(tmp_path); plan_review, article_review = _reviews(tmp_path, paths)
    bom = _build(paths, plan_review, article_review, tmp_path)

    paths["sidecar"].write_text(
        paths["sidecar"].read_text(encoding="utf-8") + "\nChanged after review.\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="machine_review_proof_sidecar_hash_mismatch"):
        _build(paths, plan_review, article_review, tmp_path)
    rules = {
        finding["rule_id"]
        for finding in check_bom(
            bom,
            article_path=paths["article"],
            validation_sidecar_path=paths["sidecar"],
            workspace_root=tmp_path,
            expected_lifecycle_state="provisional",
        )
    }
    assert "machine_review_proof_sidecar_hash_mismatch" in rules


def test_new_bom_build_cannot_fall_back_to_archived_v1(tmp_path: Path):
    paths = _fixture(tmp_path)

    with pytest.raises(ValueError, match="requires both plan_review_path and article_review_path"):
        build_blog_assembly_bom_from_files(
            article_path=paths["article"],
            validation_sidecar_path=paths["sidecar"],
            editorial_plan_path=paths["editorial_plan"],
            keyword_decision_path=paths["keyword_decision"],
            serp_evidence_path=paths["serp"],
            paa_artifact_path=paths["paa"],
            stage_receipt_paths=paths["stage_receipts"],
            workflow_mode="new",
            assembly_date="2026-08-11",
            workspace_root=tmp_path,
        )


def test_archived_v1_remains_readable_but_cannot_authorize_release(tmp_path: Path):
    paths = _fixture(tmp_path)
    plan_review, article_review = _reviews(tmp_path, paths)
    archived = _build(paths, plan_review, article_review, tmp_path)
    archived["schema"] = "simpro-blog-assembly-bom/v1"
    archived.pop("machine_reviews")

    ordinary_rules = {
        finding["rule_id"]
        for finding in check_bom(
            archived,
            article_path=paths["article"],
            validation_sidecar_path=paths["sidecar"],
            workspace_root=tmp_path,
            expected_lifecycle_state="provisional",
        )
    }
    release_rules = {
        finding["rule_id"]
        for finding in check_bom(
            archived,
            article_path=paths["article"],
            validation_sidecar_path=paths["sidecar"],
            workspace_root=tmp_path,
            expected_lifecycle_state="provisional",
            require_current_schema=True,
        )
    }

    assert "bom_archived_schema_not_releasable" not in ordinary_rules
    assert "bom_archived_schema_not_releasable" in release_rules


@pytest.mark.parametrize(
    ("field", "other_value", "expected_rule"),
    [
        ("run_id", "run-other", "machine_review_pair_run_id_mismatch"),
        ("workflow_stage", "optimize", "machine_review_pair_workflow_stage_mismatch"),
        ("command", "/optimize", "machine_review_pair_command_mismatch"),
        ("repository_commit", "def456", "machine_review_pair_repository_commit_mismatch"),
    ],
)
def test_bom_v2_rejects_mixed_machine_review_provenance(
    tmp_path: Path,
    field: str,
    other_value: str,
    expected_rule: str,
):
    paths = _fixture(tmp_path)
    plan_review, article_review = _reviews(tmp_path, paths)
    bom = _build(paths, plan_review, article_review, tmp_path)

    responses = [
        {"agent": agent, "status": "completed", "findings": []}
        for agent in AGENT_ROSTER
    ]
    kwargs = {
        "run_id": "run-1",
        "workflow_stage": "rewrite",
        "phase": "article",
        "command": "/rewrite",
        "repository_commit": "abc123",
        "editorial_plan_path": paths["editorial_plan"],
        "article_path": paths["article"],
        "proof_sidecar_path": paths["sidecar"],
        "responses": responses,
        "created_at": "2026-08-11T14:00:00Z",
    }
    kwargs[field] = other_value
    write_machine_review(article_review, build_machine_review(**kwargs))
    bom["machine_reviews"]["article"]["sha256"] = hashlib.sha256(
        article_review.read_bytes()
    ).hexdigest()

    rules = {
        finding["rule_id"]
        for finding in check_bom(
            bom,
            article_path=paths["article"],
            validation_sidecar_path=paths["sidecar"],
            workspace_root=tmp_path,
            expected_lifecycle_state="provisional",
        )
    }

    assert expected_rule in rules
