from __future__ import annotations

import pytest

from data_sources.modules.blog_assembly_stage_receipt import (
    StageReceiptError,
    build_stage_receipt,
    check_receipt_chain,
)


A, B, C, PLAN = "a" * 64, "b" * 64, "c" * 64, "1" * 64
TOOLS = {
    "draft": ("blog_writer", "1.0.0"),
    "scrub": ("content_scrubber", "1.0.0"),
    "context_binding": ("context_binding_generator", "1.0.0"),
    "preflight_readiness": ("publish_readiness", "1.0.0"),
    "wording_edit": ("wording_edit", "1.0.0"),
}
MUTATING = {"draft", "wording_edit"}


def _chain(*steps: tuple[str, str, str]) -> list[dict]:
    receipts: list[dict] = []
    for index, (stage, article_in, article_out) in enumerate(steps):
        tool_name, tool_version = TOOLS[stage]
        inputs = {"article": article_in}
        if stage == "draft":
            inputs["editorial_plan"] = PLAN
        receipts.append(
            build_stage_receipt(
                run_id="run-1",
                stage=stage,
                tool_name=tool_name,
                tool_version=tool_version,
                started_at=f"2026-10-07T10:{index:02d}:00Z",
                completed_at=f"2026-10-07T10:{index:02d}:30Z",
                mutation=stage in MUTATING,
                input_artifact_hashes=inputs,
                output_artifact_hashes={"article": article_out},
                previous_receipt_hash=receipts[-1]["receipt_hash"] if receipts else "",
            )
        )
    return receipts


BASE = (("draft", "e" * 64, A), ("scrub", A, A), ("context_binding", A, A))


def _rules(receipts) -> set[str]:
    return {finding["rule_id"] for finding in check_receipt_chain(receipts)}


def test_chained_wording_edits_after_context_binding_are_a_valid_chain():
    receipts = _chain(*BASE, ("wording_edit", A, B), ("wording_edit", B, C))

    assert _rules(receipts) == set()


def test_preflight_readiness_may_follow_wording_edits():
    receipts = _chain(*BASE, ("wording_edit", A, B), ("preflight_readiness", B, B))

    assert _rules(receipts) == set()


@pytest.mark.parametrize(
    "steps",
    [
        (("draft", "e" * 64, A), ("scrub", A, A), ("wording_edit", A, B)),
        (*BASE, ("preflight_readiness", A, A), ("wording_edit", A, B)),
    ],
)
def test_misplaced_wording_edit_breaks_the_closed_stage_order(steps):
    assert "stage_receipt_stage_order_invalid" in _rules(_chain(*steps))


def test_wording_edit_must_record_a_real_mutation_with_its_fixed_tool():
    with pytest.raises(StageReceiptError) as unchanged:
        _chain(*BASE, ("wording_edit", A, A))
    assert unchanged.value.code == "stage_receipt_mutation_semantics_invalid"

    with pytest.raises(StageReceiptError) as wrong_tool:
        build_stage_receipt(
            run_id="run-1",
            stage="wording_edit",
            tool_name="blog_writer",
            tool_version="1.0.0",
            started_at="2026-10-07T10:00:00Z",
            completed_at="2026-10-07T10:00:30Z",
            mutation=True,
            input_artifact_hashes={"article": A},
            output_artifact_hashes={"article": B},
        )
    assert wrong_tool.value.code == "stage_receipt_tool_invalid"
