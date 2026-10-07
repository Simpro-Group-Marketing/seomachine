"""A chained wording-edit receipt carries earlier release artifacts forward."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from data_sources.modules.blog_assembly_bom_guard import check_bom
from data_sources.modules.blog_assembly_stage_receipt import StageReceiptError
from data_sources.modules.wording_edit import begin_wording_edit, finish_wording_edit
from tests.test_blog_assembly_bom import (  # noqa: F401 - autouse clock fixture
    _build,
    _fixture as _base_fixture,
    _freeze_workflow_clock,
    _machine_reviews,
    _refresh_normal_stage_receipts,
)


ORIGINAL = "Dispatchers review the board each morning and assign the first visits before crews leave the yard."
REWORDED = "Dispatchers check the board each morning and assign the first visits before crews leave the yard."


def _fixture(tmp_path: Path) -> dict:
    paths = _base_fixture(tmp_path)
    article = Path(paths["article"])
    article.write_text(article.read_text(encoding="utf-8") + f"\n{ORIGINAL}\n", encoding="utf-8")
    _refresh_normal_stage_receipts(paths)
    return paths


def _edit(tmp_path: Path, paths: dict, old: str, new: str, *, name: str = "edit-1") -> Path:
    research = tmp_path / "research"
    state = research / f"wording-{name}-state.json"
    receipt = research / f"stage-wording-{name}.json"
    previous = paths["stage_receipts"][-1]
    begin_wording_edit(
        article_path=paths["article"],
        state_path=state,
        previous_receipt_path=previous,
        workspace_root=tmp_path,
        started_at="2026-08-11T14:07:00Z",
    )
    article = Path(paths["article"])
    article.write_text(article.read_text(encoding="utf-8").replace(old, new), encoding="utf-8")
    finish_wording_edit(
        state_path=state,
        article_path=article,
        receipt_path=receipt,
        sidecar_path=paths["sidecar"],
        workspace_root=tmp_path,
        completed_at="2026-08-11T14:08:00Z",
    )
    return receipt


def test_builder_accepts_a_wording_edit_with_reviews_bound_to_the_anchor(tmp_path: Path):
    paths = _fixture(tmp_path)
    plan_review, article_review = _machine_reviews(
        tmp_path,
        {"editorial_plan": paths["editorial_plan"], "article": paths["article"], "sidecar": paths["sidecar"]},
    )
    receipt = _edit(tmp_path, paths, ORIGINAL, REWORDED)

    bom = _build(
        tmp_path,
        {**paths, "stage_receipts": [*paths["stage_receipts"], receipt]},
        plan_review_path=plan_review,
        article_review_path=article_review,
    )

    stages = [row["stage"] for row in bom["workflow"]["stage_receipts"]]
    assert stages == ["draft", "scrub", "context_binding", "wording_edit"]
    assert check_bom(
        bom,
        article_path=paths["article"],
        validation_sidecar_path=paths["sidecar"],
        workspace_root=tmp_path,
        expected_lifecycle_state="provisional",
    ) == []
    evidence = json.loads(receipt.with_name(f"{receipt.stem}-evidence.json").read_text(encoding="utf-8"))
    assert evidence["payload"]["violations"] == []


def test_cli_begins_and_finishes_a_wording_edit(tmp_path: Path, capsys):
    from data_sources.modules import wording_edit

    paths = _fixture(tmp_path)
    research = tmp_path / "research"
    common = ["--state", str(research / "cli-state.json"), "--article", str(paths["article"])]
    assert wording_edit.main([
        "begin", *common, "--previous-receipt", str(paths["stage_receipts"][-1]),
        "--workspace-root", str(tmp_path),
    ]) == 0
    article = Path(paths["article"])
    article.write_text(article.read_text(encoding="utf-8").replace(ORIGINAL, REWORDED), encoding="utf-8")
    receipt = research / "stage-wording-cli.json"

    assert wording_edit.main([
        "finish", *common, "--receipt", str(receipt), "--sidecar", str(paths["sidecar"]),
        "--workspace-root", str(tmp_path),
    ]) == 0
    assert json.loads(receipt.read_text(encoding="utf-8"))["stage"] == "wording_edit"

    article.write_text(article.read_text(encoding="utf-8").replace(
        "[Explore field service management software]", "[Compare field service management software]"
    ), encoding="utf-8")
    capsys.readouterr()
    assert wording_edit.main([
        "begin", "--state", str(research / "cli-state-2.json"), "--article", str(article),
        "--previous-receipt", str(receipt), "--workspace-root", str(tmp_path),
    ]) == 2
    assert "wording_edit_article_changed" in capsys.readouterr().err


def test_generic_native_edit_cli_does_not_offer_wording_edit(tmp_path: Path):
    from data_sources.modules import blog_assembly_stage_receipt

    state = tmp_path / "state.json"
    with pytest.raises(SystemExit):
        blog_assembly_stage_receipt.main([
            "begin-native-edit", "--article", str(tmp_path / "a.md"), "--state", str(state),
            "--run-id", "r", "--stage", "wording_edit", "--tool-name", "wording_edit",
            "--tool-version", "1.0.0",
        ])
    assert not state.exists()


def test_finish_refuses_a_link_change_and_leaves_the_edit_open(tmp_path: Path):
    paths = _fixture(tmp_path)
    with pytest.raises(StageReceiptError) as refused:
        _edit(
            tmp_path,
            paths,
            "[Explore field service management software]",
            "[Compare field service management software]",
        )

    assert refused.value.code == "wording_edit_not_wording_only"
    assert "links" in str(refused.value)
    assert not (tmp_path / "research" / "stage-wording-edit-1.json").exists()


def test_finish_refuses_an_edit_over_the_cumulative_word_budget(tmp_path: Path):
    paths = _fixture(tmp_path)
    with pytest.raises(StageReceiptError) as refused:
        _edit(
            tmp_path,
            paths,
            ORIGINAL,
            "Each morning the lead dispatcher plans first visits so crews can leave on time.",
        )

    assert refused.value.code == "wording_edit_budget_exceeded"


def test_begin_requires_a_context_binding_or_wording_edit_predecessor(tmp_path: Path):
    paths = _fixture(tmp_path)
    with pytest.raises(StageReceiptError) as refused:
        begin_wording_edit(
            article_path=paths["article"],
            state_path=tmp_path / "research" / "state.json",
            previous_receipt_path=paths["stage_receipts"][1],
            workspace_root=tmp_path,
        )

    assert refused.value.code == "wording_edit_predecessor_invalid"


def test_builder_rejects_a_wording_edit_whose_evidence_was_altered(tmp_path: Path):
    paths = _fixture(tmp_path)
    plan_review, article_review = _machine_reviews(
        tmp_path,
        {"editorial_plan": paths["editorial_plan"], "article": paths["article"], "sidecar": paths["sidecar"]},
    )
    receipt = _edit(tmp_path, paths, ORIGINAL, REWORDED)
    article = Path(paths["article"])
    article.write_text(
        article.read_text(encoding="utf-8").replace(REWORDED, "Dispatchers check the board each morning."),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="wording edit receipts are invalid"):
        _build(
            tmp_path,
            {**paths, "stage_receipts": [*paths["stage_receipts"], receipt]},
            plan_review_path=plan_review,
            article_review_path=article_review,
        )
