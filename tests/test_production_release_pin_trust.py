"""Release pins the old BOM's proof selections only when that BOM is the file the pipeline wrote."""

from __future__ import annotations

import json
from unittest.mock import patch

import pytest
from data_sources.modules.production import release, selector_refresh
from tests.production_bom_support import TODAY
from tests.production_release_support import Checks, run, workspace
from tests.test_customer_proof_selector import write_ledger
from tests.test_production_selector_pinning import (
    VAULT_PATCH,
    YAK,
    ZEBRA,
    _connector_release_workspace,
    _selected,
    _zebra_uses,
)
from tests.vault_context_fixture import load_validated_claim_set_for_unit_test


@pytest.fixture(autouse=True)
def _environment(monkeypatch):
    monkeypatch.setenv("SEOMACHINE_TEST_CURRENT_UTC_DATE", TODAY)
    monkeypatch.delenv(release.ENV_WORKERS, raising=False)


def _hand_edit(layout) -> None:
    """Rewrite the BOM with the same content but different bytes, so its hash no longer matches the run state."""
    bom = json.loads(layout.bom.read_text(encoding="utf-8"))
    layout.bom.write_text(json.dumps(bom, indent=1), encoding="utf-8", newline="\n")


def _recorded_boms(layout, monkeypatch) -> list[dict]:
    Checks(monkeypatch)
    seen: list[dict] = []
    run(layout, refresher=lambda _layout, _nonconnector, bom: seen.append(bom))
    return seen


def test_pipeline_written_bom_pins_its_selections(tmp_path, monkeypatch):
    layout = workspace(tmp_path)
    seen = _recorded_boms(layout, monkeypatch)
    assert seen and selector_refresh.pinned_selections(seen[0])


def test_hand_edited_bom_pins_nothing_but_keeps_its_evidence_binding(tmp_path, monkeypatch):
    layout = workspace(tmp_path)
    binding = json.loads(layout.bom.read_text(encoding="utf-8"))["customer_proof"]["evidence"]
    _hand_edit(layout)
    seen = _recorded_boms(layout, monkeypatch)
    assert seen and selector_refresh.pinned_selections(seen[0]) == {}
    assert seen[0]["customer_proof"]["evidence"] == binding


def test_hand_edited_connector_bom_lets_a_moved_ledger_rechoose_and_the_spec_refuses(tmp_path, monkeypatch):
    Checks(monkeypatch)
    layout, ledger = _connector_release_workspace(tmp_path)
    write_ledger(ledger.parent, _zebra_uses())
    _hand_edit(layout)
    monkeypatch.setattr(release, "load_validated_claim_set", load_validated_claim_set_for_unit_test)
    with patch(VAULT_PATCH, new=load_validated_claim_set_for_unit_test):
        assert run(layout, refresher=selector_refresh.refresh_selector_evidence) == 1
    assert _selected(layout) == YAK != ZEBRA
