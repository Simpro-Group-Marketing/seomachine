"""A pinned BOM proof survives its own publish-time ledger use; unpinned selection still avoids it."""

from __future__ import annotations

import json
import shutil
from datetime import date
from unittest.mock import patch

import pytest

from data_sources.modules.customer_proof.nonconnector_contracts import NonVaultProofDataError
from data_sources.modules.customer_proof.nonconnector_persistence import write_nonvault_selector_evidence
from data_sources.modules.customer_proof.nonconnector_selection import select_nonvault_customer_proofs
from data_sources.modules.customer_proof.selection import select_customer_proofs
from data_sources.modules.customer_proof.selector_cli import _main as connector_selector_main
from data_sources.modules.production import bom_build, release, selector_refresh
from data_sources.modules.production.layout import Layout
from data_sources.modules.production.record import latest_record
from data_sources.modules.production.usage_ledger import record_publish_use
from tests.production_bom_support import (
    ARTICLE,
    NONVAULT_ID,
    TODAY,
    connector_spec,
    good_transport,
    make_workspace,
    nonconnector_spec,
)
from tests.production_release_support import Checks, run
from tests.test_customer_proof_selector import write_ledger
from tests.test_production_selector_pinning import VAULT_PATCH, ZEBRA, _claims
from tests.test_publisher_usage_ledger import LINKED
from tests.vault_context_fixture import load_validated_claim_set_for_unit_test, write_connector_context_fixture

SLUG = "field-service-software"
ZEBRA_URL = "https://www.simprogroup.com/case-studies/zebra-plumbing"
CONNECTOR_ARTICLE = f"# Field Service Software Guide\n\n## What it is\n\nZebra Plumbing cut [quote time]({ZEBRA_URL}).\n"
ROLES = "metric,quote,theme,experience_story"


@pytest.fixture(autouse=True)
def _environment(monkeypatch):
    monkeypatch.setenv("SEOMACHINE_TEST_CURRENT_UTC_DATE", TODAY)
    monkeypatch.delenv(release.ENV_WORKERS, raising=False)


def _release(layout) -> int:
    with patch(VAULT_PATCH, new=load_validated_claim_set_for_unit_test):
        return run(layout, refresher=selector_refresh.refresh_selector_evidence)


def _connector_workspace(root) -> Layout:
    spec = connector_spec()
    spec["proof"] = [{"id": "p1", "claim_id": ZEBRA, "kind": "metric", "priority": "should"}]
    layout = make_workspace(root, spec=spec)
    (root / "fixture").mkdir()
    pack, receipt = write_connector_context_fixture(root / "fixture", _claims())
    shutil.copyfile(pack, layout.context_pack)
    shutil.copyfile(receipt, layout.context_receipt)
    ledger = write_ledger(root / "config")
    with patch(VAULT_PATCH, new=load_validated_claim_set_for_unit_test):
        assert connector_selector_main([
            "quoting invoicing review story", "--ledger", str(ledger), "--context-pack", str(layout.context_pack),
            "--context-receipt", str(layout.context_receipt), "--slate", "--roles", ROLES, "--require-eeat-story",
            "--article-slug", SLUG, "--evidence-output", str(layout.customer_proof_evidence),
        ]) == 0
    layout.article.parent.mkdir(parents=True, exist_ok=True)
    layout.article.write_text(CONNECTOR_ARTICLE, encoding="utf-8", newline="\n")
    bom = bom_build.build_bom(layout, transport=good_transport(), claim_loader=load_validated_claim_set_for_unit_test)
    bom_build._write_bom(layout, bom)
    return layout


def _nonvault_workspace(root, *, limit: int = 1) -> Layout:
    layout = make_workspace(root, spec=nonconnector_spec())
    write_nonvault_selector_evidence(
        layout.nonvault_customer_proof_evidence, topic="Crew Time Tracking Guide", brand="ClockShark",
        title="Crew Time Tracking Guide", objective="Help owners choose software", article_slug=SLUG,
        roles=["metric", "quote", "theme", "experience_story"], require_eeat_story=True, limit=limit,
        reference_date=date.fromisoformat(TODAY), selected_overrides={"theme": NONVAULT_ID}, rejected_overrides={},
        index_path=root / "config" / "nonvault-customer-proof-index.json",
        ledger_path=root / "config" / "customer-proof-usage-ledger.json",
    )
    layout.article.parent.mkdir(parents=True, exist_ok=True)
    layout.article.write_text(LINKED, encoding="utf-8", newline="\n")
    bom_build._write_bom(layout, bom_build.build_bom(layout, transport=good_transport()))
    return layout


def test_connector_release_publish_release_keeps_the_pinned_proof(tmp_path, monkeypatch):
    Checks(monkeypatch)
    monkeypatch.setattr(release, "load_validated_claim_set", load_validated_claim_set_for_unit_test)
    layout = _connector_workspace(tmp_path)
    assert _release(layout) == 0
    assert [e["proof_id"] for e in record_publish_use(layout.article, layout.root, published_path=ARTICLE)] == [ZEBRA]
    assert _release(layout) == 0
    assert latest_record(layout)["passed"] is True


def test_nonvault_release_publish_release_keeps_the_pinned_proof(tmp_path, monkeypatch):
    Checks(monkeypatch)
    layout = _nonvault_workspace(tmp_path)
    assert _release(layout) == 0
    assert [e["proof_id"] for e in record_publish_use(layout.article, layout.root, published_path=ARTICLE)] == [
        NONVAULT_ID
    ]
    assert _release(layout) == 0
    assert latest_record(layout)["passed"] is True


def _self_use(proof_id: str, url: str) -> dict:
    return {"proof_id": proof_id, "source_url": url, "article_slug": SLUG, "date_used": TODAY}


def _connector_select(root, ledger, **kwargs) -> list[str]:
    pack, receipt = write_connector_context_fixture(root, _claims())
    with patch(VAULT_PATCH, new=load_validated_claim_set_for_unit_test):
        results = select_customer_proofs(
            "quoting invoicing", ledger_path=ledger, context_pack=pack, context_receipt=receipt,
            article_slug=SLUG, proof_role="metric", reference_date=date.fromisoformat(TODAY), **kwargs,
        )
    return [str(row["proof_id"]) for row in results]


def test_connector_unpinned_selection_still_excludes_same_article_uses(tmp_path):
    ledger = write_ledger(tmp_path, [_self_use(ZEBRA, ZEBRA_URL)])
    assert ZEBRA not in _connector_select(tmp_path, ledger)
    assert _connector_select(tmp_path, ledger, pinned=ZEBRA)[-1] == ZEBRA
    assert "claim-missing" not in _connector_select(tmp_path, ledger, pinned="claim-missing")


def _nonvault_select(root, **kwargs) -> list[str]:
    layout = make_workspace(root, spec=nonconnector_spec())
    ledger = layout.root / "config" / "customer-proof-usage-ledger.json"
    ledger.write_text(json.dumps({"version": 1, "uses": [_self_use(NONVAULT_ID, "x")]}), encoding="utf-8")
    results = select_nonvault_customer_proofs(
        "Crew Time Tracking Guide", brand="ClockShark", index_path=root / "config" / "nonvault-customer-proof-index.json",
        ledger_path=ledger, article_slug=SLUG, proof_role="theme", limit=1,
        reference_date=date.fromisoformat(TODAY), **kwargs,
    )
    return [str(row["proof_id"]) for row in results]


def test_nonvault_pin_survives_the_reuse_penalty_and_limit_but_an_ineligible_pin_does_not(tmp_path):
    assert _nonvault_select(tmp_path / "a") != [NONVAULT_ID]
    assert _nonvault_select(tmp_path / "b", pinned=NONVAULT_ID)[-1] == NONVAULT_ID
    assert "clockshark-pending" not in _nonvault_select(tmp_path / "c", pinned="clockshark-pending")


def test_an_ineligible_pinned_nonvault_id_still_fails_closed(tmp_path):
    with pytest.raises(NonVaultProofDataError, match="clockshark-pending"):
        layout = make_workspace(tmp_path, spec=nonconnector_spec())
        write_nonvault_selector_evidence(
            layout.nonvault_customer_proof_evidence, topic="t", brand="ClockShark", title="t", objective="o",
            article_slug=SLUG, roles=["theme"], require_eeat_story=False, limit=10,
            reference_date=date.fromisoformat(TODAY), selected_overrides={"theme": "clockshark-pending"},
            rejected_overrides={}, index_path=tmp_path / "config" / "nonvault-customer-proof-index.json",
            ledger_path=tmp_path / "config" / "customer-proof-usage-ledger.json",
        )
