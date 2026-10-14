"""A Simpro AU connector spec resolves an AU commercial pillar in a BOM build."""

from __future__ import annotations

import json

import pytest
from data_sources.modules.production import bom_build
from tests.production_bom_support import (
    FROZEN,
    good_loader,
    good_transport,
    make_workspace,
    write_json,
    write_pillar_index,
)

AU_TODAY = "2026-10-14"
AU_ID = "simpro-au-homepage-field-service-management-software"


@pytest.fixture(autouse=True)
def _pinned_clock(monkeypatch):
    monkeypatch.setenv("SEOMACHINE_TEST_CURRENT_UTC_DATE", AU_TODAY)


def _au_record():
    return json.loads((FROZEN / "pillar-record-au.json").read_text(encoding="utf-8"))


def _build(layout):
    return bom_build.build_bom(layout, transport=good_transport(), claim_loader=good_loader())


def _au_workspace(tmp_path):
    layout = make_workspace(tmp_path)
    spec = json.loads(layout.bom_spec.read_text(encoding="utf-8"))
    spec["market"] = "AU"
    spec["links"][0]["destination_id"] = AU_ID
    write_json(layout.bom_spec, spec)
    write_pillar_index(layout.root, _au_record())
    return layout


def test_au_connector_spec_resolves_au_pillar(tmp_path):
    pillar = _build(_au_workspace(tmp_path))["links"][0]
    assert pillar["kind"] == "commercial_pillar" and pillar["destination_id"] == AU_ID


def test_au_pillar_refuses_a_us_article(tmp_path):
    layout = _au_workspace(tmp_path)
    spec = json.loads(layout.bom_spec.read_text(encoding="utf-8"))
    spec["market"] = "US"
    write_json(layout.bom_spec, spec)
    with pytest.raises(ValueError, match="market"):
        _build(layout)
