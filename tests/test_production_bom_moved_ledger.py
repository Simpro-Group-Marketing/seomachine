"""A rebuild after a publish moved the usage ledger names the remedy instead of only refusing."""

from __future__ import annotations

import pytest
from data_sources.modules.production import bom_build
from tests.production_bom_support import (
    TODAY,
    good_transport,
    make_workspace,
    nonconnector_spec,
    write_json,
)
from tests.test_customer_proof_selector import write_ledger
from tests.test_production_selector_pinning import _connector_release_workspace, _zebra_uses
from tests.vault_context_fixture import load_validated_claim_set_for_unit_test

REMEDY = "re-run the nonvault customer proof selector, then rebuild"


@pytest.fixture(autouse=True)
def _pinned_clock(monkeypatch):
    monkeypatch.setenv("SEOMACHINE_TEST_CURRENT_UTC_DATE", TODAY)


def test_nonconnector_build_after_the_ledger_moved_names_the_remedy(tmp_path):
    layout = make_workspace(tmp_path, spec=nonconnector_spec())
    assert bom_build.build_bom(layout, transport=good_transport())
    write_json(tmp_path / "config" / "customer-proof-usage-ledger.json", {"version": 1, "uses": [
        {"proof_id": "other", "article_slug": "published-article", "date_used": TODAY}]})
    with pytest.raises(ValueError, match=REMEDY):
        bom_build.build_bom(layout, transport=good_transport())


def test_connector_build_does_not_check_the_ledger_so_a_moved_ledger_still_builds(tmp_path):
    layout, ledger = _connector_release_workspace(tmp_path)
    write_ledger(ledger.parent, _zebra_uses())
    bom = bom_build.build_bom(layout, transport=good_transport(), claim_loader=load_validated_claim_set_for_unit_test)
    assert bom["customer_proof"]["roles"]
