"""A capture-verified fact never carries forward: it re-verifies through its capture or refuses."""

from __future__ import annotations

import datetime

import pytest
from data_sources.modules.production import bom_build, page_capture
from tests.production_bom_support import FACT_URL, TODAY
from tests.production_capture_support import BLOCKED, build_blocked, capture_workspace
from tests.production_release_support import PageTransport


@pytest.fixture(autouse=True)
def _environment(monkeypatch):
    monkeypatch.setenv("SEOMACHINE_TEST_CURRENT_UTC_DATE", TODAY)


def _clock(monkeypatch, moved: datetime.timedelta) -> None:
    real = datetime.datetime.now(datetime.timezone.utc)
    monkeypatch.setattr(page_capture, "utc_now", lambda: real + moved)


def _captured_workspace(tmp_path, monkeypatch, captured_ago: datetime.timedelta = datetime.timedelta(0)):
    _clock(monkeypatch, -captured_ago)
    layout = capture_workspace(tmp_path)
    _clock(monkeypatch, datetime.timedelta(0))
    bom = build_blocked(layout)
    assert bom["facts"][0]["verified_via"] == "chrome_capture"
    prior = bom_build._pipeline_prior_facts(layout)
    assert prior is not None and prior["f1"]["verified_via"] == "chrome_capture"
    return layout, prior


@pytest.mark.parametrize("status", [500, 401])
def test_capture_fact_is_not_carried_forward_when_the_page_now_errors(tmp_path, monkeypatch, status):
    layout, prior = _captured_workspace(tmp_path, monkeypatch)
    _clock(monkeypatch, datetime.timedelta(days=200))
    transport = PageTransport({FACT_URL: (status, "")})
    with pytest.raises(ValueError, match=r"fact f1 .* is unreachable"):
        bom_build.build_bom(layout, transport=transport, prior_facts=prior)


def test_capture_older_than_90_days_is_refused_even_with_a_prior_bom(tmp_path, monkeypatch):
    layout, prior = _captured_workspace(tmp_path, monkeypatch)
    _clock(monkeypatch, datetime.timedelta(days=bom_build.CAPTURE_MAX_AGE_DAYS + 1))
    with pytest.raises(ValueError, match=r"fact f1.*older than 90 days"):
        bom_build.build_bom(layout, transport=BLOCKED, prior_facts=prior)


def test_blocked_page_within_90_days_reverifies_from_the_capture_dated_at_capture(tmp_path, monkeypatch):
    layout, prior = _captured_workspace(tmp_path, monkeypatch, datetime.timedelta(days=10))
    _clock(monkeypatch, datetime.timedelta(days=30))
    fact = bom_build.build_bom(layout, transport=BLOCKED, prior_facts=prior)["facts"][0]
    assert fact["verified_via"] == "chrome_capture"
    assert "carried_forward" not in fact
    assert fact["verified_at"] == fact["capture"]["captured_at"]
