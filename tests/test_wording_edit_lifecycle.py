"""A wording edit after Context Binding survives the full unmocked release lifecycle."""

from __future__ import annotations

from pathlib import Path

from data_sources.modules.wording_edit import begin_wording_edit, finish_wording_edit
from tests import test_blog_release_lifecycle_roundtrip as roundtrip
from tests.test_blog_assembly_bom import _machine_reviews


ORIGINAL = "Show the owner in the open."
REWORDED = "Show the owner in plain view."


def test_release_lifecycle_carries_reviews_and_fulfillment_across_a_wording_edit(
    tmp_path: Path,
    monkeypatch,
) -> None:
    original_build = roundtrip._build
    edits: list[Path] = []

    def build_after_wording_edit(workspace, paths, **overrides):
        plan_review, article_review = _machine_reviews(
            workspace,
            {"editorial_plan": paths["editorial_plan"], "article": paths["article"], "sidecar": paths["sidecar"]},
        )
        research = workspace / "research"
        state = research / "wording-edit-state.json"
        receipt = research / "stage-wording-edit.json"
        begin_wording_edit(
            article_path=paths["article"],
            state_path=state,
            previous_receipt_path=paths["stage_receipts"][-1],
            workspace_root=workspace,
            started_at="2026-08-11T14:05:20Z",
        )
        article = Path(paths["article"])
        text = article.read_text(encoding="utf-8")
        assert text.count(ORIGINAL) == 1
        article.write_text(text.replace(ORIGINAL, REWORDED), encoding="utf-8")
        finish_wording_edit(
            state_path=state,
            article_path=article,
            receipt_path=receipt,
            sidecar_path=paths["sidecar"],
            workspace_root=workspace,
            completed_at="2026-08-11T14:05:40Z",
        )
        edits.append(receipt)
        paths["stage_receipts"] = [*paths["stage_receipts"], receipt]
        return original_build(
            workspace,
            paths,
            plan_review_path=plan_review,
            article_review_path=article_review,
            **overrides,
        )

    monkeypatch.setattr(roundtrip, "_build", build_after_wording_edit)

    roundtrip.test_unmocked_blog_release_lifecycle_round_trip(tmp_path, monkeypatch)

    assert len(edits) == 1
