"""Rejection-row parsing must survive both slate separators and prose punctuation.

The nonconnector slate writer joins rejected candidates with "; "
(customer_proof/nonconnector_persistence.py) while the vault writer joins them
with ", " (customer_proof/slate.py). Rejection reasons are free prose and
routinely contain commas. Every case below is a slate string one of those two
writers can emit today.
"""

import pytest

from data_sources.modules.customer_proof.diversity_parsing import (
    _parse_rejected_candidates,
)


def test_semicolon_joined_pairs_split_into_separate_rejections():
    """The nonconnector writer's "; " join must round-trip."""
    parsed = _parse_rejected_candidates(
        "proof-one: first reason; proof-two: second reason"
    )

    assert parsed == {
        "proof-one": "first reason",
        "proof-two": "second reason",
    }


def test_comma_joined_pairs_split_into_separate_rejections():
    """The vault writer's ", " join must round-trip."""
    parsed = _parse_rejected_candidates(
        "proof-one: first reason, proof-two: second reason"
    )

    assert parsed == {
        "proof-one": "first reason",
        "proof-two": "second reason",
    }


def test_comma_inside_a_single_reason_is_preserved():
    """Reasons are prose; a comma inside one must not truncate it."""
    parsed = _parse_rejected_candidates(
        "proof-one: needs case-study workflow proof, not a review POV story"
    )

    assert parsed == {
        "proof-one": "needs case-study workflow proof, not a review POV story"
    }


def test_commas_inside_reasons_survive_semicolon_joined_pairs():
    parsed = _parse_rejected_candidates(
        "proof-one: cost, schedule and risk; proof-two: lawn care, no fit"
    )

    assert parsed == {
        "proof-one": "cost, schedule and risk",
        "proof-two": "lawn care, no fit",
    }


def test_semicolon_inside_a_single_reason_is_preserved():
    parsed = _parse_rejected_candidates(
        "proof-one: first point; second point is longer"
    )

    assert parsed == {"proof-one": "first point; second point is longer"}


def test_colon_inside_a_reason_does_not_start_a_new_rejection():
    """Only a hyphenated proof-id slug may open a new pair."""
    parsed = _parse_rejected_candidates(
        "proof-one: rejected, reason: not a construction story"
    )

    assert parsed == {"proof-one": "rejected, reason: not a construction story"}


def test_real_clockshark_proof_ids_round_trip():
    parsed = _parse_rejected_candidates(
        "clockshark-customer-story-chesapeake-lawn-home: no construction content; "
        "clockshark-customer-story-mabrys-electrical-service: not machine verifiable"
    )

    assert parsed == {
        "clockshark-customer-story-chesapeake-lawn-home": "no construction content",
        "clockshark-customer-story-mabrys-electrical-service": "not machine verifiable",
    }


@pytest.mark.parametrize("value", ["none", "", "[none]", "not selected"])
def test_empty_selection_values_yield_no_rejections(value):
    assert _parse_rejected_candidates(value) == {}


def test_bracketed_value_is_unwrapped():
    parsed = _parse_rejected_candidates("[proof-one: simple reason]")

    assert parsed == {"proof-one": "simple reason"}
