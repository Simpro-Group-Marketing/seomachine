"""Carry-forward of verified facts when a source page is unreachable at release."""

from __future__ import annotations

import json

import pytest
import requests
from data_sources.modules.production import bom_build
from tests.production_bom_support import (
    FACT_URL,
    TODAY,
    FakeTransport,
    good_loader,
    good_transport,
    make_workspace,
    response,
    write_json,
)


@pytest.fixture(autouse=True)
def _pinned_date(monkeypatch):
    monkeypatch.setenv("SEOMACHINE_TEST_CURRENT_UTC_DATE", TODAY)


def _build(layout):
    return bom_build.build_bom(layout, transport=good_transport(), claim_loader=good_loader())


def _mutate(layout, change):
    spec = json.loads(layout.bom_spec.read_text(encoding="utf-8"))
    change(spec)
    write_json(layout.bom_spec, spec)


def _prior(layout):
    return {fact["id"]: fact for fact in _build(layout)["facts"]}


def _build_with_prior(layout, transport, prior):
    return bom_build.build_bom(layout, transport=transport, claim_loader=good_loader(), prior_facts=prior)


@pytest.mark.parametrize("reply", [response(FACT_URL, 403), requests.Timeout("slow")], ids=["403", "timeout"])
def test_unreachable_page_carries_forward_the_matching_prior_fact(tmp_path, reply):
    layout = make_workspace(tmp_path)
    prior = _prior(layout)
    prior["f1"] = {**prior["f1"], "verified_at": "2026-10-01T08:00:00Z"}
    fact = _build_with_prior(layout, FakeTransport({FACT_URL: reply}), prior)["facts"][0]
    assert fact["verified_at"] == "2026-10-01T08:00:00Z"
    assert fact["check_detail"] == "quote found on page" and fact["carried_forward"] is True
    assert fact["release_check"] == ("HTTP 403" if isinstance(reply, requests.Response) else "Timeout: slow")
    assert {k: fact[k] for k in ("id", "claim", "url", "quote", "priority", "support")} == {
        k: prior["f1"][k] for k in ("id", "claim", "url", "quote", "priority", "support")}


def test_first_build_without_prior_facts_still_refuses_an_unreachable_page(tmp_path):
    layout = make_workspace(tmp_path)
    with pytest.raises(ValueError, match=r"f1.*unreachable"):
        _build_with_prior(layout, FakeTransport({FACT_URL: response(FACT_URL, 403)}), None)


def test_changed_quote_with_an_unreachable_page_is_not_carried_forward(tmp_path):
    layout = make_workspace(tmp_path)
    prior = _prior(layout)
    _mutate(layout, lambda s: s["facts"][0].update(quote="Trusted by more than 24,000 trade businesses"))
    with pytest.raises(ValueError, match=r"f1.*unreachable"):
        _build_with_prior(layout, FakeTransport({FACT_URL: response(FACT_URL, 503)}), prior)


@pytest.mark.parametrize("page", [
    response(FACT_URL, 200, "<html><body><p>Nothing relevant here.</p></body></html>"),
    response(FACT_URL, 404),
], ids=["quote_missing", "gone"])
def test_lost_quote_or_gone_page_refuses_even_with_a_prior_fact(tmp_path, page):
    layout = make_workspace(tmp_path)
    prior = _prior(layout)
    with pytest.raises(ValueError, match=r"f1.*(quote_missing|gone)"):
        _build_with_prior(layout, FakeTransport({FACT_URL: page}), prior)
