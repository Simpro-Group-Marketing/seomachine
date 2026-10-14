"""The spec market must agree with the bound Semrush keyword decision's market and database."""

from __future__ import annotations

import pytest
from data_sources.modules.production import bom_build
from tests.production_bom_support import TODAY, good_loader, good_transport, make_workspace, write_json


@pytest.fixture(autouse=True)
def _pinned_clock(monkeypatch):
    monkeypatch.setenv("SEOMACHINE_TEST_CURRENT_UTC_DATE", TODAY)


def _build(layout):
    return bom_build.build_bom(layout, transport=good_transport(), claim_loader=good_loader())


def _decision(layout, **fields):
    write_json(layout.keyword_decision, {"schema": "decision", "primary": "fsm", **fields})


def test_agreeing_market_and_database_build(tmp_path):
    layout = make_workspace(tmp_path)
    _decision(layout, market="US", database="us")
    assert _build(layout)["identity"]["market"] == "US"


@pytest.mark.parametrize(
    ("fields", "expected"),
    [
        ({"market": "AU", "database": "au"}, r"keyword decision market 'AU' does not match the spec market US"),
        ({"market": "US", "database": "uk"}, r"keyword decision database 'uk' does not match .*US.* us"),
        ({}, r"keyword decision market None does not match the spec market US"),
    ],
)
def test_disagreeing_market_or_database_refuses(tmp_path, fields, expected):
    layout = make_workspace(tmp_path)
    _decision(layout, **fields)
    with pytest.raises(ValueError, match=expected):
        _build(layout)
