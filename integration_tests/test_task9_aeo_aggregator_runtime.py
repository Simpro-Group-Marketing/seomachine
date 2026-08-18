from __future__ import annotations

import importlib

from data_sources.modules.aeo_geo_rater import (
    _check_direct_answer,
    _has_documented_no_fit_experience_boundary,
)


def test_definition_equivalent_does_not_accept_unresolved_question_framing():
    result = _check_direct_answer(
        "Whether a job sheet is useful remains an open question for many field "
        "service teams today.",
        {"primary_keyword": "what is a job sheet"},
    )

    assert result["passed"] is False
    assert result["details"]["includes_target"] is False


def test_definition_equivalent_accepts_declarative_answer_at_sentence_start():
    result = _check_direct_answer(
        "A job sheet is a working record for a job or site visit. "
        "It captures tasks, time, materials, evidence and sign-off.",
        {"primary_keyword": "what is a job sheet"},
    )

    assert result["passed"] is True


def _empty_slate(*, execution_line: str = "") -> str:
    return f'''## Customer proof selector
- Selector command: python data_sources/modules/customer_proof_selector.py "job sheets" --title "What is a job sheet?" --objective "Define job sheets" --slate --roles experience_story --require-eeat-story --limit 10
{execution_line}
## E-E-A-T Proof Map
- First-hand evidence decision: Selected: [none] because no approved customer story supports this article objective.

## Customer Proof Slate
- Role: experience_story | Top candidates: [none] | Selected: [none] | Rejected stronger candidates: [none: no eligible candidate exists because the proof index has no story for this article section]
'''


def test_copied_selector_command_is_not_execution_evidence():
    assert not _has_documented_no_fit_experience_boundary(_empty_slate())


def test_completed_selector_receipt_without_artifact_is_not_execution_evidence():
    execution = (
        "- Selector execution: completed | Exit code: 0 | Output SHA-256: "
        + "a" * 64
    )

    assert not _has_documented_no_fit_experience_boundary(
        _empty_slate(execution_line=execution)
    )


def test_data_aggregator_import_does_not_eagerly_import_optional_google_analytics():
    module = importlib.import_module("data_sources.modules.data_aggregator")

    assert module.DataAggregator is not None


def test_data_aggregator_initializes_available_lanes_when_one_factory_fails(tmp_path):
    module = importlib.import_module("data_sources.modules.data_aggregator")
    gsc = object()
    dfs = object()

    def missing_ga():
        raise ModuleNotFoundError("google.analytics")

    aggregator = module.DataAggregator(
        client_factories={"ga": missing_ga, "gsc": lambda: gsc, "dfs": lambda: dfs},
        env_path=tmp_path / "missing.env",
        print_fn=lambda *args, **kwargs: None,
    )

    assert aggregator.ga is None
    assert aggregator.gsc is gsc
    assert aggregator.dfs is dfs
    assert "google.analytics" in aggregator.source_errors["ga"]
