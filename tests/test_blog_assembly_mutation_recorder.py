from __future__ import annotations

import json
import hashlib
import os
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

import pytest

from data_sources.modules.blog_assembly_mutation_recorder import (
    finish_mutation,
    main,
    start_mutation as _start_mutation,
)
from data_sources.modules.blog_assembly_stage_receipt import load_stage_receipt


def start_mutation(**kwargs: object) -> dict[str, object]:
    """Supply the mandatory canonical workflow boundary for legacy test cases."""
    state_path = Path(str(kwargs["state_path"]))
    kwargs["workspace_root"] = state_path.parent
    kwargs["assembly_date"] = "2026-08-11"
    kwargs["run_id"] = None
    return _start_mutation(**kwargs)  # type: ignore[arg-type]


def test_optimizer_recorder_captures_real_before_and_after_hashes(tmp_path: Path):
    article = tmp_path / "article.md"
    article.write_text("Before\n", encoding="utf-8")
    state = tmp_path / "optimization-state.json"
    receipt_path = tmp_path / "optimization-receipt.json"
    start_mutation(
        article_path=article,
        state_path=state,
        run_id="run-1",
        stage="optimization",
        tool_name="manual_optimizer",
        tool_version="1.0.0",
        started_at="2026-08-11T14:00:00Z",
    )
    article.write_text("After\n", encoding="utf-8")

    receipt = finish_mutation(
        state_path=state,
        article_path=article,
        receipt_path=receipt_path,
        completed_at="2026-08-11T14:01:00Z",
    )

    assert receipt["input_artifact_hashes"]["article"] != receipt["output_artifact_hashes"]["article"]
    assert load_stage_receipt(receipt_path) == receipt


def test_finish_rejects_no_change_mutation(tmp_path: Path):
    article = tmp_path / "article.md"
    article.write_text("Unchanged\n", encoding="utf-8")
    state = tmp_path / "state.json"
    start_mutation(
        article_path=article,
        state_path=state,
        run_id="run-1",
        stage="optimization",
        tool_name="manual_optimizer",
        tool_version="1.0.0",
        started_at="2026-08-11T14:00:00Z",
    )

    with pytest.raises(ValueError, match="did not change"):
        finish_mutation(
            state_path=state,
            article_path=article,
            receipt_path=tmp_path / "receipt.json",
            completed_at="2026-08-11T14:01:00Z",
        )


def test_draft_recorder_captures_seed_article_and_binds_plan_input(tmp_path: Path):
    article = tmp_path / "article.md"
    article.write_text("---\nartifact_type: blog\n---\n", encoding="utf-8")
    plan = tmp_path / "plan.json"
    plan.write_text("{}\n", encoding="utf-8")
    state = tmp_path / "state.json"
    start_mutation(
        article_path=article,
        state_path=state,
        run_id="run-1",
        stage="draft",
        tool_name="blog_writer",
        tool_version="1.0.0",
        input_artifacts={"editorial_plan": plan},
        started_at="2026-08-11T14:00:00Z",
    )
    article.write_text("---\nartifact_type: blog\n---\n# Drafted\n", encoding="utf-8")

    receipt = finish_mutation(
        state_path=state,
        article_path=article,
        receipt_path=tmp_path / "receipt.json",
        completed_at="2026-08-11T14:01:00Z",
    )

    assert "article" in receipt["input_artifact_hashes"]
    assert (
        receipt["input_artifact_hashes"]["article"]
        != receipt["output_artifact_hashes"]["article"]
    )
    assert "editorial_plan" in receipt["input_artifact_hashes"]
    assert "article" in receipt["output_artifact_hashes"]


def test_draft_recorder_atomically_initializes_and_hashes_a_missing_seed(tmp_path: Path):
    article = tmp_path / "drafts" / "article.md"
    state_path = tmp_path / "state.json"

    state = start_mutation(
        article_path=article,
        state_path=state_path,
        run_id="run-1",
        stage="draft",
        tool_name="blog_writer",
        tool_version="1.0.0",
        started_at="2026-08-11T14:00:00Z",
    )

    assert article.read_bytes() == b""
    assert state["input_artifact_hashes"]["article"] == hashlib.sha256(b"").hexdigest()
    assert len(state["state_hash"]) == 64
    assert json.loads(state_path.read_text(encoding="utf-8")) == state


def test_start_rejects_an_existing_state_without_overwriting_it(tmp_path: Path):
    article = tmp_path / "article.md"
    article.write_text("Before\n", encoding="utf-8")
    state_path = tmp_path / "state.json"
    original = b'{"existing": true}\n'
    state_path.write_bytes(original)

    with pytest.raises(ValueError, match="state output already exists"):
        start_mutation(
            article_path=article,
            state_path=state_path,
            run_id="run-1",
            stage="optimization",
            tool_name="manual_optimizer",
            tool_version="1.0.0",
        )

    assert state_path.read_bytes() == original


def test_start_preserves_state_created_during_exclusive_publish(tmp_path: Path):
    article = tmp_path / "article.md"
    article.write_text("Before\n", encoding="utf-8")
    state_path = tmp_path / "state.json"
    original = b'{"concurrent": true}\n'

    def create_competing_state(_source: object, destination: object) -> None:
        Path(destination).write_bytes(original)
        raise FileExistsError("concurrent state")

    with patch(
        "data_sources.modules.blog_assembly_mutation_recorder.os.link",
        side_effect=create_competing_state,
    ):
        with pytest.raises(ValueError, match="state output already exists"):
            start_mutation(
                article_path=article,
                state_path=state_path,
                run_id="run-1",
                stage="optimization",
                tool_name="manual_optimizer",
                tool_version="1.0.0",
            )

    assert state_path.read_bytes() == original


def test_finish_rejects_tampered_mutation_state(tmp_path: Path):
    article = tmp_path / "article.md"
    article.write_text("Before\n", encoding="utf-8")
    state_path = tmp_path / "state.json"
    receipt_path = tmp_path / "receipt.json"
    start_mutation(
        article_path=article,
        state_path=state_path,
        run_id="run-1",
        stage="optimization",
        tool_name="manual_optimizer",
        tool_version="1.0.0",
        started_at="2026-08-11T14:00:00Z",
    )
    state = json.loads(state_path.read_text(encoding="utf-8"))
    state["tool"]["name"] = "forged_optimizer"
    state_path.write_text(json.dumps(state), encoding="utf-8")
    article.write_text("After\n", encoding="utf-8")

    with pytest.raises(ValueError, match="state hash"):
        finish_mutation(
            state_path=state_path,
            article_path=article,
            receipt_path=receipt_path,
            completed_at="2026-08-11T14:01:00Z",
        )

    assert not receipt_path.exists()


def test_finish_rejects_unknown_mutation_state_fields(tmp_path: Path):
    article = tmp_path / "article.md"
    article.write_text("Before\n", encoding="utf-8")
    state_path = tmp_path / "state.json"
    receipt_path = tmp_path / "receipt.json"
    start_mutation(
        article_path=article,
        state_path=state_path,
        run_id="run-1",
        stage="optimization",
        tool_name="manual_optimizer",
        tool_version="1.0.0",
        started_at="2026-08-11T14:00:00Z",
    )
    state = json.loads(state_path.read_text(encoding="utf-8"))
    state["unexpected"] = "forged"
    state_path.write_text(json.dumps(state), encoding="utf-8")
    article.write_text("After\n", encoding="utf-8")

    with pytest.raises(ValueError, match="exact field set"):
        finish_mutation(
            state_path=state_path,
            article_path=article,
            receipt_path=receipt_path,
            completed_at="2026-08-11T14:01:00Z",
        )

    assert not receipt_path.exists()


def test_finish_rejects_existing_receipt_without_overwriting_it(tmp_path: Path):
    article = tmp_path / "article.md"
    article.write_text("Before\n", encoding="utf-8")
    state_path = tmp_path / "state.json"
    receipt_path = tmp_path / "receipt.json"
    start_mutation(
        article_path=article,
        state_path=state_path,
        run_id="run-1",
        stage="optimization",
        tool_name="manual_optimizer",
        tool_version="1.0.0",
        started_at="2026-08-11T14:00:00Z",
    )
    article.write_text("After\n", encoding="utf-8")
    original = b'{"existing": true}\n'
    receipt_path.write_bytes(original)

    with pytest.raises(ValueError, match="receipt output already exists"):
        finish_mutation(
            state_path=state_path,
            article_path=article,
            receipt_path=receipt_path,
            completed_at="2026-08-11T14:01:00Z",
        )

    assert receipt_path.read_bytes() == original


def test_finish_preserves_receipt_created_during_exclusive_publish(tmp_path: Path):
    article = tmp_path / "article.md"
    article.write_text("Before\n", encoding="utf-8")
    state_path = tmp_path / "state.json"
    receipt_path = tmp_path / "receipt.json"
    start_mutation(
        article_path=article,
        state_path=state_path,
        run_id="run-1",
        stage="optimization",
        tool_name="manual_optimizer",
        tool_version="1.0.0",
        started_at="2026-08-11T14:00:00Z",
    )
    article.write_text("After\n", encoding="utf-8")
    original_state = state_path.read_bytes()
    original_receipt = b'{"concurrent": true}\n'

    def create_competing_receipt(_source: object, destination: object) -> None:
        Path(destination).write_bytes(original_receipt)
        raise FileExistsError("concurrent receipt")

    with patch(
        "data_sources.modules.blog_assembly_mutation_recorder.os.link",
        side_effect=create_competing_receipt,
    ):
        with pytest.raises(ValueError, match="receipt output already exists"):
            finish_mutation(
                state_path=state_path,
                article_path=article,
                receipt_path=receipt_path,
                completed_at="2026-08-11T14:01:00Z",
            )

    assert receipt_path.read_bytes() == original_receipt
    assert state_path.read_bytes() == original_state


def test_successful_finish_consumes_state_and_blocks_replay(tmp_path: Path):
    article = tmp_path / "article.md"
    article.write_text("Before\n", encoding="utf-8")
    state_path = tmp_path / "state.json"
    receipt_path = tmp_path / "receipt.json"
    start_mutation(
        article_path=article,
        state_path=state_path,
        run_id="run-1",
        stage="optimization",
        tool_name="manual_optimizer",
        tool_version="1.0.0",
        started_at="2026-08-11T14:00:00Z",
    )
    article.write_text("After\n", encoding="utf-8")

    receipt = finish_mutation(
        state_path=state_path,
        article_path=article,
        receipt_path=receipt_path,
        completed_at="2026-08-11T14:01:00Z",
    )
    consumed = json.loads(state_path.read_text(encoding="utf-8"))

    assert consumed["schema"] == "simpro-blog-mutation-state-consumed/v1"
    assert consumed["receipt_hash"] == receipt["receipt_hash"]
    replay_receipt = tmp_path / "replay-receipt.json"
    with pytest.raises(ValueError, match="already consumed"):
        finish_mutation(
            state_path=state_path,
            article_path=article,
            receipt_path=replay_receipt,
            completed_at="2026-08-11T14:02:00Z",
        )
    assert not replay_receipt.exists()


def test_draft_seed_is_removed_when_state_write_fails(tmp_path: Path):
    article = tmp_path / "drafts" / "article.md"

    with patch(
        "data_sources.modules.blog_assembly_mutation_recorder._exclusive_write_json",
        side_effect=OSError("state write failed"),
    ):
        with pytest.raises(OSError, match="state write failed"):
            start_mutation(
                article_path=article,
                state_path=tmp_path / "state.json",
                run_id="run-1",
                stage="draft",
                tool_name="blog_writer",
                tool_version="1.0.0",
                started_at="2026-08-11T14:00:00Z",
            )

    assert not article.exists()


def test_optimization_recorder_rejects_missing_article(tmp_path: Path):
    with pytest.raises(ValueError, match="existing article"):
        start_mutation(
            article_path=tmp_path / "article.md",
            state_path=tmp_path / "state.json",
            run_id="run-1",
            stage="optimization",
            tool_name="blog_writer",
            tool_version="1.0.0",
            started_at="2026-08-11T14:00:00Z",
        )


def test_finish_rejects_different_article_identity(tmp_path: Path):
    article = tmp_path / "article.md"
    other = tmp_path / "other.md"
    article.write_text("Before\n", encoding="utf-8")
    other.write_text("After\n", encoding="utf-8")
    state = tmp_path / "state.json"
    start_mutation(
        article_path=article,
        state_path=state,
        run_id="run-1",
        stage="optimization",
        tool_name="manual_optimizer",
        tool_version="1.0.0",
        started_at="2026-08-11T14:00:00Z",
    )

    with pytest.raises(ValueError, match="same article"):
        finish_mutation(
            state_path=state,
            article_path=other,
            receipt_path=tmp_path / "receipt.json",
            completed_at="2026-08-11T14:01:00Z",
        )


@pytest.mark.parametrize("collision", ("article", "input"))
def test_start_rejects_state_output_collision_without_overwriting_input(
    tmp_path: Path,
    collision: str,
):
    article = tmp_path / "article.md"
    article.write_text("Before\n", encoding="utf-8")
    plan = tmp_path / "plan.json"
    plan.write_text('{"plan": true}\n', encoding="utf-8")
    destination = article if collision == "article" else plan
    original = destination.read_bytes()

    with pytest.raises(ValueError, match="state output cannot overwrite"):
        start_mutation(
            article_path=article,
            state_path=destination,
            run_id="run-1",
            stage="draft",
            tool_name="blog_writer",
            tool_version="1.0.0",
            input_artifacts={"editorial_plan": plan},
            started_at="2026-08-11T14:00:00Z",
        )

    assert destination.read_bytes() == original


@pytest.mark.parametrize("collision", ("article", "state", "evidence"))
def test_finish_rejects_receipt_output_collision_without_overwriting_input(
    tmp_path: Path,
    collision: str,
):
    article = tmp_path / "article.md"
    article.write_text("Before\n", encoding="utf-8")
    state = tmp_path / "state.json"
    evidence = tmp_path / "optimizer.json"
    evidence.write_text('{"optimizer": true}\n', encoding="utf-8")
    start_mutation(
        article_path=article,
        state_path=state,
        run_id="run-1",
        stage="optimization",
        tool_name="manual_optimizer",
        tool_version="1.0.0",
        started_at="2026-08-11T14:00:00Z",
    )
    article.write_text("After\n", encoding="utf-8")
    destinations = {"article": article, "state": state, "evidence": evidence}
    destination = destinations[collision]
    original = destination.read_bytes()

    with pytest.raises(ValueError, match="receipt output cannot overwrite"):
        finish_mutation(
            state_path=state,
            article_path=article,
            receipt_path=destination,
            evidence_artifacts={"optimizer_output": evidence},
            completed_at="2026-08-11T14:01:00Z",
        )

    assert destination.read_bytes() == original


def test_cli_rejects_duplicate_artifact_labels_with_concise_error(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
):
    article = tmp_path / "article.md"
    article.write_text("Before\n", encoding="utf-8")
    first = tmp_path / "first.json"
    second = tmp_path / "second.json"
    first.write_text("{}\n", encoding="utf-8")
    second.write_text("{}\n", encoding="utf-8")
    state = tmp_path / "state.json"

    with pytest.raises(SystemExit) as raised:
        main(
            [
                "start",
                "--article",
                str(article),
                "--state",
                str(state),
                "--assembly-date",
                "2026-08-11",
                "--workspace-root",
                str(tmp_path),
                "--stage",
                "draft",
                "--tool-name",
                "blog_writer",
                "--tool-version",
                "1.0.0",
                "--input",
                f"editorial_plan={first}",
                "--input",
                f"editorial_plan={second}",
            ]
        )

    captured = capsys.readouterr()
    assert raised.value.code == 2
    assert "duplicate artifact label: editorial_plan" in captured.err
    assert "Traceback" not in captured.err
    assert not state.exists()


def test_start_rejects_reserved_article_input_label(tmp_path: Path):
    article = tmp_path / "article.md"
    article.write_text("Before\n", encoding="utf-8")
    other = tmp_path / "other.json"
    other.write_text("{}\n", encoding="utf-8")

    with pytest.raises(ValueError, match="reserved artifact label: article"):
        start_mutation(
            article_path=article,
            state_path=tmp_path / "state.json",
            run_id="run-1",
            stage="draft",
            tool_name="blog_writer",
            tool_version="1.0.0",
            input_artifacts={"article": other},
            started_at="2026-08-11T14:00:00Z",
        )


def test_evidence_label_cannot_hide_receipt_collision_with_article(tmp_path: Path):
    article = tmp_path / "article.md"
    article.write_text("Before\n", encoding="utf-8")
    state = tmp_path / "state.json"
    evidence = tmp_path / "optimizer.json"
    evidence.write_text("{}\n", encoding="utf-8")
    start_mutation(
        article_path=article,
        state_path=state,
        run_id="run-1",
        stage="optimization",
        tool_name="manual_optimizer",
        tool_version="1.0.0",
        started_at="2026-08-11T14:00:00Z",
    )
    article.write_text("After\n", encoding="utf-8")
    original = article.read_bytes()

    with pytest.raises(ValueError, match="receipt output cannot overwrite input article"):
        finish_mutation(
            state_path=state,
            article_path=article,
            receipt_path=article,
            evidence_artifacts={"article": evidence},
            completed_at="2026-08-11T14:01:00Z",
        )

    assert article.read_bytes() == original


def test_cli_reports_missing_optimization_article_without_traceback(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
):
    with pytest.raises(SystemExit) as raised:
        main(
            [
                "start",
                "--article",
                str(tmp_path / "missing.md"),
                "--state",
                str(tmp_path / "state.json"),
                "--assembly-date",
                "2026-08-11",
                "--workspace-root",
                str(tmp_path),
                "--stage",
                "optimization",
                "--tool-name",
                "blog_writer",
                "--tool-version",
                "1.0.0",
            ]
        )

    captured = capsys.readouterr()
    assert raised.value.code == 2
    assert "optimization must start from an existing article" in captured.err
    assert "Traceback" not in captured.err


@pytest.mark.skipif(os.name != "nt", reason="Windows path identity regression")
def test_finish_accepts_case_alias_for_the_same_windows_article(tmp_path: Path):
    article = tmp_path / "article.md"
    article.write_text("Before\n", encoding="utf-8")
    state = tmp_path / "state.json"
    start_mutation(
        article_path=article,
        state_path=state,
        run_id="run-1",
        stage="optimization",
        tool_name="manual_optimizer",
        tool_version="1.0.0",
        started_at="2026-08-11T14:00:00Z",
    )
    article.write_text("After\n", encoding="utf-8")

    receipt = finish_mutation(
        state_path=state,
        article_path=Path(str(article).upper()),
        receipt_path=tmp_path / "receipt.json",
        completed_at="2026-08-11T14:01:00Z",
    )

    assert receipt["stage"] == "optimization"
