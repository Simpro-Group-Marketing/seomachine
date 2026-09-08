from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from data_sources.modules import blog_assembly_stage_receipt as stage_receipts
from data_sources.modules.blog_assembly_stage_receipt import (
    StageReceiptError,
    build_stage_receipt,
    check_receipt_chain,
    check_stage_receipt,
    load_stage_receipt,
    write_stage_receipt,
)


H1 = "1" * 64
H2 = "2" * 64
H3 = "3" * 64
EMPTY_SHA256 = hashlib.sha256(b"").hexdigest()


def _receipt(
    stage: str,
    *,
    started: str,
    completed: str,
    article_in: str | None,
    article_out: str,
    previous: str = "",
    mutation: bool = False,
    run_id: str = "run-1",
):
    tools = {
        "draft": ("blog_writer", "1.0.0"),
        "scrub": ("content_scrubber", "1.0.0"),
        "context_binding": ("context_binding_generator", "1.0.0"),
        "preflight_readiness": ("publish_readiness", "1.0.0"),
        "optimization": ("manual_optimizer", "1.0.0"),
        "post_optimization_scrub": ("content_scrubber", "1.0.0"),
        "post_optimization_context_binding": ("context_binding_generator", "1.0.0"),
        "final_preflight_readiness": ("publish_readiness", "1.0.0"),
        "final_readiness_attestation": ("publish_readiness", "1.0.0"),
    }
    tool_name, tool_version = tools[stage]
    inputs = {"article": article_in} if article_in is not None else {}
    if stage == "draft":
        inputs["editorial_plan"] = H1
    return build_stage_receipt(
        run_id=run_id,
        stage=stage,
        tool_name=tool_name,
        tool_version=tool_version,
        started_at=started,
        completed_at=completed,
        mutation=mutation,
        input_artifact_hashes=inputs,
        output_artifact_hashes={"article": article_out},
        evidence_hashes={},
        previous_receipt_hash=previous,
    )


def test_build_receipt_uses_canonical_hash_excluding_receipt_hash():
    receipt = _receipt(
        "draft",
        started="2026-08-11T14:00:00Z",
        completed="2026-08-11T14:01:00Z",
        article_in=H2,
        article_out=H1,
        mutation=True,
    )
    unhashed = {key: value for key, value in receipt.items() if key != "receipt_hash"}
    expected = hashlib.sha256(
        json.dumps(
            unhashed,
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
    ).hexdigest()

    assert receipt["schema"] == "simpro-blog-stage-receipt/v1"
    assert receipt["status"] == "completed"
    assert receipt["receipt_hash"] == expected
    assert check_stage_receipt(receipt) == []


def test_plain_rehashed_forged_receipt_cannot_mint_tool_execution():
    receipt = _receipt(
        "scrub",
        started="2026-08-11T14:01:00Z",
        completed="2026-08-11T14:02:00Z",
        article_in=H1,
        article_out=H1,
    )
    forged = json.loads(json.dumps(receipt))
    forged["evidence_hashes"]["scrub_statistics"] = H2
    unhashed = {key: value for key, value in forged.items() if key != "receipt_hash"}
    forged["receipt_hash"] = hashlib.sha256(
        json.dumps(
            unhashed,
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
    ).hexdigest()

    rules = {finding["rule_id"] for finding in check_stage_receipt(forged)}

    assert "stage_receipt_execution_attestation_invalid" in rules
    assert forged["execution_attestation"] == receipt["execution_attestation"]


def test_builder_rejects_invalid_hash_with_field_specific_code():
    with pytest.raises(StageReceiptError) as raised:
        build_stage_receipt(
            run_id="run-1",
            stage="draft",
            tool_name="blog_writer",
            tool_version="1.0.0",
            started_at="2026-08-11T14:00:00Z",
            completed_at="2026-08-11T14:01:00Z",
            mutation=True,
            input_artifact_hashes={"article": H2, "plan": "not-a-hash"},
            output_artifact_hashes={"article": H1},
        )

    assert raised.value.code == "stage_receipt_input_hash_invalid"


def test_same_or_backward_timestamp_is_rejected():
    with pytest.raises(StageReceiptError) as raised:
        _receipt(
            "scrub",
            started="2026-08-11T14:01:00Z",
            completed="2026-08-11T14:01:00Z",
            article_in=H1,
            article_out=H1,
        )

    assert raised.value.code == "stage_receipt_timestamp_order_invalid"


def test_deterministic_stage_requires_exact_tool_identity():
    receipt = _receipt(
        "scrub",
        started="2026-08-11T14:01:00Z",
        completed="2026-08-11T14:02:00Z",
        article_in=H1,
        article_out=H1,
    )
    receipt["tool"]["name"] = "manual"

    assert "stage_receipt_tool_invalid" in {
        finding["rule_id"] for finding in check_stage_receipt(receipt)
    }


def test_write_and_load_are_atomic_and_validated(tmp_path: Path):
    receipt = _receipt(
        "draft",
        started="2026-08-11T14:00:00Z",
        completed="2026-08-11T14:01:00Z",
        article_in=H2,
        article_out=H1,
        mutation=True,
    )
    path = tmp_path / "receipt.json"

    write_stage_receipt(path, receipt)

    assert load_stage_receipt(path) == receipt
    assert not any(item.name.endswith(".tmp") for item in tmp_path.iterdir())


def _normal_chain():
    draft = _receipt(
        "draft",
        started="2026-08-11T14:00:00Z",
        completed="2026-08-11T14:01:00Z",
        article_in=H2,
        article_out=H1,
        mutation=True,
    )
    scrub = _receipt(
        "scrub",
        started="2026-08-11T14:02:00Z",
        completed="2026-08-11T14:03:00Z",
        article_in=H1,
        article_out=H1,
        previous=draft["receipt_hash"],
    )
    binding = _receipt(
        "context_binding",
        started="2026-08-11T14:04:00Z",
        completed="2026-08-11T14:05:00Z",
        article_in=H1,
        article_out=H1,
        previous=scrub["receipt_hash"],
    )
    return [draft, scrub, binding]


def test_valid_provisional_chain_passes():
    assert check_receipt_chain(_normal_chain()) == []


def test_normal_workflow_can_close_with_detached_final_readiness():
    receipts = _normal_chain()
    preflight = _receipt(
        "preflight_readiness",
        started="2026-08-11T14:06:00Z",
        completed="2026-08-11T14:07:00Z",
        article_in=H1,
        article_out=H1,
        previous=receipts[-1]["receipt_hash"],
    )
    final = _receipt(
        "final_readiness_attestation",
        started="2026-08-11T14:08:00Z",
        completed="2026-08-11T14:09:00Z",
        article_in=H1,
        article_out=H1,
        previous=preflight["receipt_hash"],
    )

    assert check_receipt_chain([*receipts, preflight, final]) == []


def test_broken_previous_receipt_hash_fails():
    receipts = _normal_chain()
    receipts[2]["previous_receipt_hash"] = H3

    assert "stage_receipt_previous_hash_mismatch" in {
        finding["rule_id"] for finding in check_receipt_chain(receipts)
    }


def test_article_hash_continuity_is_required():
    receipts = _normal_chain()
    receipts[2]["input_artifact_hashes"]["article"] = H2

    assert "stage_receipt_article_chain_broken" in {
        finding["rule_id"] for finding in check_receipt_chain(receipts)
    }


def test_reordered_stages_fail_closed():
    receipts = _normal_chain()
    receipts[1], receipts[2] = receipts[2], receipts[1]

    assert "stage_receipt_stage_order_invalid" in {
        finding["rule_id"] for finding in check_receipt_chain(receipts)
    }


def test_non_mutating_stage_cannot_change_article_hash():
    with pytest.raises(StageReceiptError) as raised:
        _receipt(
            "scrub",
            started="2026-08-11T14:01:00Z",
            completed="2026-08-11T14:02:00Z",
            article_in=H1,
            article_out=H2,
            mutation=False,
        )

    assert raised.value.code == "stage_receipt_mutation_semantics_invalid"


def test_context_and_readiness_stages_cannot_claim_mutation():
    with pytest.raises(StageReceiptError) as raised:
        _receipt(
            "context_binding",
            started="2026-08-11T14:01:00Z",
            completed="2026-08-11T14:02:00Z",
            article_in=H1,
            article_out=H2,
            mutation=True,
        )

    assert raised.value.code == "stage_receipt_mutation_forbidden"


def test_receipt_chain_requires_one_run_id_and_global_monotonicity():
    receipts = _normal_chain()
    receipts[2]["run_id"] = "run-2"
    receipts[2]["started_at"] = "2026-08-11T14:02:30Z"

    rules = {finding["rule_id"] for finding in check_receipt_chain(receipts)}
    assert "stage_receipt_run_id_mismatch" in rules
    assert "stage_receipt_timestamps_not_monotonic" in rules


def test_receipt_rejects_missing_and_unknown_contract_fields():
    missing = _receipt(
        "draft",
        started="2026-08-11T14:00:00Z",
        completed="2026-08-11T14:01:00Z",
        article_in=H2,
        article_out=H1,
        mutation=True,
    )
    missing.pop("evidence_hashes")
    unknown = _receipt(
        "draft",
        started="2026-08-11T14:00:00Z",
        completed="2026-08-11T14:01:00Z",
        article_in=H2,
        article_out=H1,
        mutation=True,
    )
    unknown["caller_asserted_passed"] = True

    assert "stage_receipt_shape_invalid" in {
        finding["rule_id"] for finding in check_stage_receipt(missing)
    }
    assert "stage_receipt_shape_invalid" in {
        finding["rule_id"] for finding in check_stage_receipt(unknown)
    }


def test_every_receipt_requires_an_article_output_hash():
    receipt = _receipt(
        "scrub",
        started="2026-08-11T14:01:00Z",
        completed="2026-08-11T14:02:00Z",
        article_in=H1,
        article_out=H1,
    )
    receipt["output_artifact_hashes"].pop("article")

    assert "stage_receipt_article_output_missing" in {
        finding["rule_id"] for finding in check_stage_receipt(receipt)
    }


def test_every_receipt_requires_an_article_input_hash():
    receipt = _receipt(
        "context_binding",
        started="2026-08-11T14:01:00Z",
        completed="2026-08-11T14:02:00Z",
        article_in=H1,
        article_out=H1,
    )
    receipt["input_artifact_hashes"].pop("article")

    assert "stage_receipt_article_input_missing" in {
        finding["rule_id"] for finding in check_stage_receipt(receipt)
    }

    draft = _receipt(
        "draft",
        started="2026-08-11T14:01:00Z",
        completed="2026-08-11T14:02:00Z",
        article_in=H2,
        article_out=H1,
        mutation=True,
    )
    draft["input_artifact_hashes"].pop("article")
    assert "stage_receipt_article_input_missing" in {
        finding["rule_id"] for finding in check_stage_receipt(draft)
    }


def test_draft_and_optimization_receipts_must_record_a_mutation():
    receipt = _receipt(
        "draft",
        started="2026-08-11T14:00:00Z",
        completed="2026-08-11T14:01:00Z",
        article_in=H2,
        article_out=H1,
        mutation=True,
    )
    receipt["mutation"] = False

    assert "stage_receipt_mutation_required" in {
        finding["rule_id"] for finding in check_stage_receipt(receipt)
    }


def test_native_draft_edit_is_attested_without_python_creating_the_article(tmp_path: Path):
    article = tmp_path / "drafts" / "topic.md"
    plan = tmp_path / "research" / "plan.json"
    plan.parent.mkdir()
    plan.write_text("{}\n", encoding="utf-8")
    state_path = tmp_path / "research" / "receipts" / "draft-state.json"
    receipt_path = state_path.with_name("draft.json")

    state = stage_receipts.begin_native_edit(
        article_path=article,
        state_path=state_path,
        run_id="run-native",
        stage="draft",
        tool_name="write-command",
        tool_version="1",
        input_artifacts={"editorial_plan": plan},
        started_at="2026-08-18T12:00:00Z",
    )

    assert not article.exists()
    assert state["article_existed"] is False
    assert state["input_artifact_hashes"]["article"] == EMPTY_SHA256

    article.parent.mkdir()
    article.write_text("# Native draft\n", encoding="utf-8")
    receipt = stage_receipts.finish_native_edit(
        state_path=state_path,
        article_path=article,
        receipt_path=receipt_path,
        completed_at="2026-08-18T12:01:00Z",
    )

    assert receipt["stage"] == "draft"
    assert receipt["mutation"] is True
    assert receipt_path.is_file()
    assert json.loads(state_path.read_text(encoding="utf-8"))["schema"].endswith("-consumed/v1")


def test_native_optimization_requires_an_existing_article(tmp_path: Path):
    with pytest.raises(StageReceiptError) as raised:
        stage_receipts.begin_native_edit(
            article_path=tmp_path / "rewrites" / "missing.md",
            state_path=tmp_path / "research" / "optimization-state.json",
            run_id="run-native",
            stage="optimization",
            tool_name="optimize-command",
            tool_version="1",
            started_at="2026-08-18T12:00:00Z",
        )

    assert raised.value.code == "native_edit_article_missing"


def test_native_edit_finish_rejects_an_unchanged_article(tmp_path: Path):
    article = tmp_path / "drafts" / "topic.md"
    article.parent.mkdir()
    article.write_text("# Existing\n", encoding="utf-8")
    state_path = tmp_path / "research" / "optimization-state.json"
    receipt_path = tmp_path / "research" / "optimization.json"
    stage_receipts.begin_native_edit(
        article_path=article,
        state_path=state_path,
        run_id="run-native",
        stage="optimization",
        tool_name="optimize-command",
        tool_version="1",
        started_at="2026-08-18T12:00:00Z",
    )

    with pytest.raises(StageReceiptError) as raised:
        stage_receipts.finish_native_edit(
            state_path=state_path,
            article_path=article,
            receipt_path=receipt_path,
            completed_at="2026-08-18T12:01:00Z",
        )

    assert raised.value.code == "native_edit_unchanged"
    assert not receipt_path.exists()


def test_native_edit_cli_records_draft_without_writing_public_markdown(tmp_path: Path):
    article = tmp_path / "drafts" / "cli-topic.md"
    state = tmp_path / "research" / "cli-state.json"
    receipt = tmp_path / "research" / "cli-receipt.json"

    assert stage_receipts.main(
        [
            "begin-native-edit",
            "--article",
            str(article),
            "--state",
            str(state),
            "--run-id",
            "run-cli",
            "--stage",
            "draft",
            "--tool-name",
            "write-command",
            "--tool-version",
            "1",
        ]
    ) == 0
    assert not article.exists()

    article.parent.mkdir()
    article.write_text("# CLI draft\n", encoding="utf-8")
    assert stage_receipts.main(
        [
            "finish-native-edit",
            "--article",
            str(article),
            "--state",
            str(state),
            "--receipt",
            str(receipt),
        ]
    ) == 0
    assert load_stage_receipt(receipt)["stage"] == "draft"
