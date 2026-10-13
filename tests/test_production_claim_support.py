"""Claim-to-quote support rules: polarity is one-directional and contraction-aware."""

from __future__ import annotations

import pytest
from data_sources.modules.production.claim_support import claim_support_errors


def _errors(claim: str, quote: str) -> list[str]:
    return claim_support_errors("f1", claim, quote)


@pytest.mark.parametrize(
    ("claim", "quote"),
    [
        (
            "Field service businesses lose revenue to missed appointments",
            "Missed appointments cost field service companies revenue every month",
        ),
        (
            "Technicians spend time at the job site on paperwork",
            "Technicians spend hours at the job site on paperwork each week",
        ),
        (
            "Contractors can set up recurring maintenance schedules",
            "Contractors can set up recurring maintenance schedules in minutes",
        ),
        (
            "Electrician employment is projected to grow 11 percent from 2023 to 2033",
            "Employment of electricians is projected to grow 11 percent from 2023 to 2033, "
            "much faster than the average for all occupations",
        ),
        (
            "Electricians need a license in most states",
            "Electricians need a license in most states",
        ),
        (
            "Plans start at least 30 days out",
            "Plans start at least 30 days out",
        ),
    ],
)
def test_genuine_paraphrases_are_admitted(claim, quote):
    assert _errors(claim, quote) == []


@pytest.mark.parametrize(
    ("claim", "quote"),
    [
        ("Fewer than 24,000 trade businesses worldwide trust it",
         "Trusted by more than 24,000 trade businesses worldwide"),
        ("Savings are up to 30% for crews every year", "Savings are 30% for crews every year"),
        ("Savings are 30% for crews every year", "Savings are up to 30% for crews every year"),
        ("All contractors use it every single day", "Contractors use it every single day"),
        ("Electricians don't need a license in most states",
         "Electricians need a license in most states"),
        ("Electricians must be licensed in most states",
         "Electricians aren't required to be licensed in most states"),
        ("Electricians can't work without a license in most states",
         "Electricians can work without a license in most states"),
        ("Contractors won't pay for late jobs in most cases",
         "Contractors will pay for late jobs in most cases"),
        ("Electricians cannot work alone on live panels",
         "Electricians can work alone on live panels"),
        ("Crews finish jobs at most twice per day on site",
         "Crews finish jobs twice per day on site"),
        ("Crews finish jobs twice per day on site",
         "Crews finish jobs at least twice per day on site"),
        ("Crews rarely finish jobs twice per day on site",
         "Crews finish jobs twice per day on site"),
        ("Crews finish jobs twice per day on site",
         "Crews hardly finish jobs twice per day on site"),
    ],
)
def test_polarity_changes_are_refused(claim, quote):
    errors = _errors(claim, quote)
    assert any("polarity" in e for e in errors), errors


def test_polarity_error_tells_the_writer_how_to_fix_it():
    errors = _errors("All contractors use it every single day", "Contractors use it every single day")
    assert any("trim the quote to the span that supports the claim" in e for e in errors)


def test_quote_side_neutral_words_do_not_count_against_the_claim():
    errors = _errors(
        "Crews log time from any phone",
        "Crews log time from any phone on every job site at the office over the next decade",
    )
    assert errors == []
