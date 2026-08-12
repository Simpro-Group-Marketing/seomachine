from __future__ import annotations

import hashlib
import json
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timezone
from pathlib import Path
from unittest.mock import patch

import pytest

from data_sources.modules.blog_assembly_contract import (
    canonical_article_run_id,
    is_json_number,
    load_json_object_snapshot,
)
from data_sources.modules.blog_assembly_mutation_recorder import (
    finish_mutation,
    mutation_ledger_entry_path,
    start_mutation,
)
from data_sources.modules.blog_assembly_stage_receipt import (
    build_stage_receipt,
    check_receipt_chain,
)


H1 = "1" * 64
H2 = "2" * 64
H3 = "3" * 64


@pytest.mark.parametrize(
    ("raw", "message"),
    [
        (b'{"key": 1, "key": 2}', "duplicate key"),
        (b'{"key": "\xff"}', "UTF-8"),
        (b'{"key": NaN}', "non-finite"),
        (b'{"key": Infinity}', "non-finite"),
        (b'{"key": -Infinity}', "non-finite"),
        (b'{"key": 1e999}', "non-finite"),
    ],
)
def test_strict_snapshot_loader_rejects_ambiguous_or_non_finite_json(
    tmp_path: Path,
    raw: bytes,
    message: str,
):
    source = tmp_path / "control.json"
    source.write_bytes(raw)

    with pytest.raises(ValueError, match=message):
        load_json_object_snapshot(source, field="control")


def test_strict_snapshot_loader_has_a_configurable_byte_limit(tmp_path: Path):
    source = tmp_path / "control.json"
    source.write_bytes(b'{"payload":"1234567890"}')

    with pytest.raises(ValueError, match="exceeds 8 bytes"):
        load_json_object_snapshot(source, field="control", max_bytes=8)


def test_snapshot_hash_and_parse_are_bound_to_the_same_immutable_bytes(tmp_path: Path):
    source = tmp_path / "control.json"
    original = b'{"version":1}'
    source.write_bytes(original)

    snapshot = load_json_object_snapshot(source, field="control")
    source.write_bytes(b'{"version":2}')

    assert snapshot.payload == {"version": 1}
    assert snapshot.sha256 == hashlib.sha256(original).hexdigest()
    assert snapshot.data == original


def test_valid_json_booleans_survive_but_are_never_numeric(tmp_path: Path):
    source = tmp_path / "control.json"
    source.write_text('{"enabled": true, "count": 2}', encoding="utf-8")

    payload = load_json_object_snapshot(source, field="control").payload

    assert payload == {"enabled": True, "count": 2}
    assert is_json_number(payload["count"])
    assert not is_json_number(payload["enabled"])


def test_canonical_run_id_uses_workspace_relative_article_identity_and_date(
    tmp_path: Path,
):
    first = tmp_path / "drafts" / "article.md"
    second = tmp_path / "rewrites" / "article.md"
    first.parent.mkdir()
    second.parent.mkdir()
    first.write_text("first", encoding="utf-8")
    second.write_text("second", encoding="utf-8")

    first_run = canonical_article_run_id(
        first,
        workspace_root=tmp_path,
        assembly_date="2026-08-11",
    )

    assert first_run == canonical_article_run_id(
        first,
        workspace_root=tmp_path,
        assembly_date=date(2026, 8, 11),
    )
    assert first_run != canonical_article_run_id(
        second,
        workspace_root=tmp_path,
        assembly_date="2026-08-11",
    )
    assert first_run != canonical_article_run_id(
        first,
        workspace_root=tmp_path,
        assembly_date="2026-08-12",
    )


def test_mutation_start_can_derive_the_canonical_run_id(tmp_path: Path):
    article = tmp_path / "drafts" / "article.md"
    article.parent.mkdir()
    article.write_text("Before\n", encoding="utf-8")

    state = start_mutation(
        article_path=article,
        state_path=tmp_path / "state.json",
        run_id=None,
        workspace_root=tmp_path,
        assembly_date="2026-08-11",
        stage="draft",
        tool_name="article-command",
        tool_version="1",
        started_at="2026-08-11T14:00:00Z",
    )

    assert state["run_id"] == canonical_article_run_id(
        article,
        workspace_root=tmp_path,
        assembly_date="2026-08-11",
    )


def _receipt(
    stage: str,
    *,
    run_id: str,
    started: str,
    completed: str,
    previous: str = "",
    evidence: dict[str, str] | None = None,
) -> dict[str, object]:
    tools = {
        "draft": ("blog_writer", "1.0.0"),
        "scrub": ("content_scrubber", "1.0.0"),
    }
    tool_name, tool_version = tools[stage]
    article_in = H2 if stage == "draft" else H1
    return build_stage_receipt(
        run_id=run_id,
        stage=stage,
        tool_name=tool_name,
        tool_version=tool_version,
        started_at=started,
        completed_at=completed,
        mutation=stage == "draft",
        input_artifact_hashes={"article": article_in},
        output_artifact_hashes={"article": H1},
        evidence_hashes=evidence or {},
        previous_receipt_hash=previous,
    )


@pytest.mark.parametrize(
    ("started", "completed", "rule"),
    [
        (
            "2026-08-10T23:58:00Z",
            "2026-08-10T23:59:00Z",
            "stage_receipt_stale",
        ),
        (
            "2026-08-11T15:01:00Z",
            "2026-08-11T15:02:00Z",
            "stage_receipt_timestamp_future",
        ),
    ],
)
def test_receipt_chain_rejects_stale_and_future_execution(
    started: str,
    completed: str,
    rule: str,
):
    receipt = _receipt(
        "draft",
        run_id="canonical-run",
        started=started,
        completed=completed,
    )

    findings = check_receipt_chain(
        [receipt],
        expected_run_id="canonical-run",
        assembly_date="2026-08-11",
        now=datetime(2026, 8, 11, 15, 0, tzinfo=timezone.utc),
    )

    assert rule in {finding["rule_id"] for finding in findings}


def test_receipt_chain_rejects_cross_run_identity_even_for_one_receipt():
    receipt = _receipt(
        "draft",
        run_id="other-run",
        started="2026-08-11T14:00:00Z",
        completed="2026-08-11T14:01:00Z",
    )

    findings = check_receipt_chain(
        [receipt],
        expected_run_id="canonical-run",
        assembly_date="2026-08-11",
        now=datetime(2026, 8, 11, 15, 0, tzinfo=timezone.utc),
    )

    assert "stage_receipt_run_id_mismatch" in {
        finding["rule_id"] for finding in findings
    }


def test_receipt_evidence_must_resolve_to_current_artifact_or_definition_hash():
    receipt = _receipt(
        "draft",
        run_id="canonical-run",
        started="2026-08-11T14:00:00Z",
        completed="2026-08-11T14:01:00Z",
        evidence={"command_definition.article": H3},
    )

    unresolved = check_receipt_chain(
        [receipt],
        resolvable_evidence_hashes={H1, H2},
    )
    resolved = check_receipt_chain(
        [receipt],
        resolvable_evidence_hashes={H1, H2, H3},
    )

    assert "stage_receipt_evidence_unresolved" in {
        finding["rule_id"] for finding in unresolved
    }
    assert "stage_receipt_evidence_unresolved" not in {
        finding["rule_id"] for finding in resolved
    }


def _start_optimization(tmp_path: Path, state_name: str = "state.json") -> tuple[Path, Path]:
    article = tmp_path / "article.md"
    article.write_text("Before\n", encoding="utf-8")
    state = tmp_path / state_name
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
    return article, state


def test_copied_or_restored_mutation_state_cannot_replay(tmp_path: Path):
    article, state = _start_optimization(tmp_path)
    active_bytes = state.read_bytes()
    ledger = tmp_path / ".seomachine" / "mutation-consumed"
    finish_mutation(
        state_path=state,
        article_path=article,
        receipt_path=tmp_path / "receipt.json",
        consumed_ledger_path=ledger,
        completed_at="2026-08-11T14:01:00Z",
    )
    state.write_bytes(active_bytes)

    with pytest.raises(ValueError, match="already consumed"):
        finish_mutation(
            state_path=state,
            article_path=article,
            receipt_path=tmp_path / "replay.json",
            consumed_ledger_path=ledger,
            completed_at="2026-08-11T14:02:00Z",
        )


def test_preexisting_ledger_entry_blocks_consumption(tmp_path: Path):
    article, state = _start_optimization(tmp_path)
    payload = json.loads(state.read_text(encoding="utf-8"))
    ledger = tmp_path / ".seomachine" / "mutation-consumed"
    entry = mutation_ledger_entry_path(ledger, payload["state_hash"])
    entry.parent.mkdir(parents=True)
    entry.write_text('{"status":"committed"}\n', encoding="utf-8")

    with pytest.raises(ValueError, match="already consumed"):
        finish_mutation(
            state_path=state,
            article_path=article,
            receipt_path=tmp_path / "receipt.json",
            consumed_ledger_path=ledger,
            completed_at="2026-08-11T14:01:00Z",
        )


def test_concurrent_mutation_consumption_has_exactly_one_winner(tmp_path: Path):
    article, first_state = _start_optimization(tmp_path, "first-state.json")
    second_state = tmp_path / "second-state.json"
    second_state.write_bytes(first_state.read_bytes())
    ledger = tmp_path / ".seomachine" / "mutation-consumed"

    def finish(index: int) -> str:
        try:
            finish_mutation(
                state_path=first_state if index == 1 else second_state,
                article_path=article,
                receipt_path=tmp_path / f"receipt-{index}.json",
                consumed_ledger_path=ledger,
                completed_at=f"2026-08-11T14:0{index}:00Z",
            )
        except ValueError as error:
            return str(error)
        return "won"

    with ThreadPoolExecutor(max_workers=2) as executor:
        outcomes = list(executor.map(finish, (1, 2)))

    assert outcomes.count("won") == 1
    assert sum("already consumed" in outcome for outcome in outcomes) == 1


def test_failed_receipt_write_rolls_back_only_its_uncommitted_reservation(
    tmp_path: Path,
):
    article, state = _start_optimization(tmp_path)
    ledger = tmp_path / ".seomachine" / "mutation-consumed"
    active = json.loads(state.read_text(encoding="utf-8"))

    with patch(
        "data_sources.modules.blog_assembly_mutation_recorder._exclusive_write_json",
        side_effect=OSError("receipt write failed"),
    ):
        with pytest.raises(OSError, match="receipt write failed"):
            finish_mutation(
                state_path=state,
                article_path=article,
                receipt_path=tmp_path / "receipt.json",
                consumed_ledger_path=ledger,
                completed_at="2026-08-11T14:01:00Z",
            )

    assert not mutation_ledger_entry_path(ledger, active["state_hash"]).exists()
    assert json.loads(state.read_text(encoding="utf-8"))["schema"] == (
        "simpro-blog-mutation-state/v1"
    )
