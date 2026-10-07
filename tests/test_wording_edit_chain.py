from __future__ import annotations

from data_sources.modules.wording_edit_chain import accepted_article_sha256s, base_stages


def _receipt(stage: str, article_in: str, article_out: str) -> dict:
    return {
        "stage": stage,
        "input_artifact_hashes": {"article": article_in},
        "output_artifact_hashes": {"article": article_out},
    }


def test_base_stages_drops_edits_that_follow_a_context_binding_or_another_edit():
    assert base_stages(
        ("draft", "scrub", "context_binding", "wording_edit", "wording_edit")
    ) == ("draft", "scrub", "context_binding")
    assert base_stages(
        ("post_optimization_scrub", "post_optimization_context_binding", "wording_edit")
    ) == ("post_optimization_scrub", "post_optimization_context_binding")


def test_base_stages_keeps_misplaced_edits_so_sequence_checks_fail():
    assert base_stages(("draft", "scrub", "wording_edit", "context_binding")) == (
        "draft",
        "scrub",
        "wording_edit",
        "context_binding",
    )
    assert base_stages(
        ("draft", "scrub", "context_binding", "preflight_readiness", "wording_edit")
    ) == ("draft", "scrub", "context_binding", "preflight_readiness", "wording_edit")
    assert base_stages(("wording_edit",)) == ("wording_edit",)


def test_accepted_hashes_cover_the_anchor_and_every_trailing_edit():
    receipts = [
        _receipt("draft", "e" * 64, "a" * 64),
        _receipt("scrub", "a" * 64, "a" * 64),
        _receipt("context_binding", "a" * 64, "a" * 64),
        _receipt("wording_edit", "a" * 64, "b" * 64),
        _receipt("wording_edit", "b" * 64, "c" * 64),
    ]

    assert accepted_article_sha256s(receipts, "c" * 64) == frozenset(
        {"a" * 64, "b" * 64, "c" * 64}
    )


def test_accepted_hashes_are_only_the_final_article_without_valid_trailing_edits():
    plain = [
        _receipt("draft", "e" * 64, "a" * 64),
        _receipt("scrub", "a" * 64, "a" * 64),
        _receipt("context_binding", "a" * 64, "a" * 64),
    ]
    broken = [*plain, _receipt("wording_edit", "x" * 64, "c" * 64)]
    wrong_final = [*plain, _receipt("wording_edit", "a" * 64, "b" * 64)]
    misplaced = [
        _receipt("draft", "e" * 64, "a" * 64),
        _receipt("wording_edit", "a" * 64, "c" * 64),
    ]

    assert accepted_article_sha256s(plain, "a" * 64) == frozenset({"a" * 64})
    assert accepted_article_sha256s(broken, "c" * 64) == frozenset({"c" * 64})
    assert accepted_article_sha256s(wrong_final, "c" * 64) == frozenset({"c" * 64})
    assert accepted_article_sha256s(misplaced, "c" * 64) == frozenset({"c" * 64})
