"""Release-time selector refresh pins the BOM's proof selections instead of re-choosing them."""

from __future__ import annotations

import json
import shutil
from datetime import date
from unittest.mock import patch

import pytest

from data_sources.modules.customer_proof.selector_cli import _main as connector_selector_main
from data_sources.modules.production import bom_build, release, selector_refresh
from data_sources.modules.production.layout import Layout
from data_sources.modules.production.record import latest_record
from tests.production_bom_support import (
    ARTICLE,
    NONVAULT_ID,
    TODAY,
    connector_spec,
    good_transport,
    make_workspace,
    nonvault_rows,
    write_json,
)
from tests.production_release_support import ARTICLE_TEXT, Checks, run, workspace
from tests.test_customer_proof_selector import proof_claims, write_ledger
from tests.vault_context_fixture import load_validated_claim_set_for_unit_test, write_connector_context_fixture

VAULT_PATCH = "data_sources.modules.customer_proof.connector_inputs.load_validated_claim_set"
ZEBRA, YAK = "claim-zebra-metric", "claim-yak-metric"
ROLES = "metric,quote,theme,experience_story"


@pytest.fixture(autouse=True)
def _environment(monkeypatch):
    monkeypatch.setenv("SEOMACHINE_TEST_CURRENT_UTC_DATE", TODAY)
    monkeypatch.delenv(release.ENV_WORKERS, raising=False)


def _claims(*, zebra: bool = True) -> list[dict]:
    claims = proof_claims()
    yak = dict(claims[0], claim_id=YAK, assertion="Yak Electrical reduced quote-to-cash cycle time with Simpro.",
               source_hash="yak-metric", public_url="https://www.simprogroup.com/case-studies/yak-electrical",
               customer="Yak Electrical")
    return [claim for claim in claims if zebra or claim["claim_id"] != ZEBRA] + [yak]


def _zebra_uses() -> list[dict]:
    """Recent uses of the zebra claim in other articles: enough to rank yak above it."""
    return [{"proof_id": ZEBRA, "public_url": "https://www.simprogroup.com/case-studies/zebra-plumbing",
             "customer": "Zebra Plumbing", "article_slug": f"other-article-{n}",
             "date_used": date.today().isoformat()} for n in range(3)]


def _select(layout: Layout, ledger, pack, receipt) -> dict:
    with patch(VAULT_PATCH, new=load_validated_claim_set_for_unit_test):
        assert connector_selector_main([
            "quoting invoicing review story", "--ledger", str(ledger), "--context-pack", str(pack),
            "--context-receipt", str(receipt), "--slate", "--roles", ROLES, "--require-eeat-story",
            "--evidence-output", str(layout.customer_proof_evidence),
        ]) == 0
    return json.loads(layout.customer_proof_evidence.read_text(encoding="utf-8"))


def _bom_for(layout: Layout, evidence: dict) -> dict:
    roles = [{"role": row["role"], "selected_id": row["selected_id"]} for row in evidence["roles"]]
    path = layout.customer_proof_evidence.relative_to(layout.root).as_posix()
    return {"proof": [{"claim_id": ZEBRA}], "customer_proof": {"evidence": {"path": path}, "roles": roles}}


def _selected(layout: Layout, role: str = "metric") -> str:
    evidence = json.loads(layout.customer_proof_evidence.read_text(encoding="utf-8"))
    return next(row["selected_id"] for row in evidence["roles"] if row["role"] == role)


def _refresh(layout: Layout, bom: dict) -> None:
    with patch(VAULT_PATCH, new=load_validated_claim_set_for_unit_test):
        selector_refresh.refresh_selector_evidence(layout, False, bom)


@pytest.fixture
def connector(tmp_path):
    layout = Layout.for_article(ARTICLE, tmp_path)
    for folder in ("config", "research"):
        (tmp_path / folder).mkdir()
    ledger = write_ledger(tmp_path / "config")
    pack, receipt = write_connector_context_fixture(tmp_path / "research", _claims())
    evidence = _select(layout, ledger, pack, receipt)
    return layout, ledger, evidence


def test_refresh_keeps_the_bom_selection_when_the_ledger_reranks_the_candidates(connector):
    layout, ledger, evidence = connector
    assert _selected(layout) == ZEBRA
    write_ledger(ledger.parent, _zebra_uses())
    recorded = layout.customer_proof_evidence.read_bytes()
    _refresh(layout, {"customer_proof": {"evidence": _bom_for(layout, evidence)["customer_proof"]["evidence"]}})
    assert _selected(layout) == YAK  # unpinned, the moved ledger re-chooses
    layout.customer_proof_evidence.write_bytes(recorded)
    _refresh(layout, _bom_for(layout, evidence))
    assert _selected(layout) == ZEBRA


def test_pinned_claim_that_is_no_longer_approved_fails_closed(connector):
    layout, _ledger, evidence = connector
    write_connector_context_fixture(layout.root / "research", _claims(zebra=False))
    before = layout.customer_proof_evidence.read_bytes()
    with pytest.raises(selector_refresh.PinnedSelectionRejected, match=ZEBRA):
        _refresh(layout, _bom_for(layout, evidence))
    assert layout.customer_proof_evidence.read_bytes() == before


def test_pinned_selections_read_the_bom_roles():
    bom = {"customer_proof": {"roles": [{"role": "metric", "selected_id": ZEBRA}, {"role": "quote", "selected_id": "none"},
                                        {"role": 3}, "junk"]}}
    assert selector_refresh.pinned_selections(bom) == {"metric": ZEBRA}
    assert selector_refresh.pinned_selections({}) == {}


def _connector_release_workspace(root):
    spec = connector_spec()
    spec["proof"] = [{"id": "p1", "claim_id": ZEBRA, "kind": "metric", "priority": "should"}]
    layout = make_workspace(root, spec=spec)
    (root / "fixture").mkdir()
    pack, receipt = write_connector_context_fixture(root / "fixture", _claims())
    shutil.copyfile(pack, layout.context_pack)
    shutil.copyfile(receipt, layout.context_receipt)
    ledger = write_ledger(root / "config")
    assert _select(layout, ledger, layout.context_pack, layout.context_receipt)
    layout.article.parent.mkdir(parents=True, exist_ok=True)
    layout.article.write_text(ARTICLE_TEXT, encoding="utf-8", newline="\n")
    bom = bom_build.build_bom(layout, transport=good_transport(), claim_loader=load_validated_claim_set_for_unit_test)
    bom_build._write_bom(layout, bom)
    return layout, ledger


def test_connector_release_passes_after_a_ledger_rerank(tmp_path, monkeypatch):
    checks = Checks(monkeypatch)
    layout, ledger = _connector_release_workspace(tmp_path)
    assert _selected(layout) == ZEBRA
    write_ledger(ledger.parent, _zebra_uses())
    monkeypatch.setattr(release, "load_validated_claim_set", load_validated_claim_set_for_unit_test)
    with patch(VAULT_PATCH, new=load_validated_claim_set_for_unit_test):
        assert run(layout, refresher=selector_refresh.refresh_selector_evidence) == 0
    assert _selected(layout) == ZEBRA and latest_record(layout)["passed"] is True
    assert checks.calls


def test_release_refuses_the_bom_when_a_pinned_nonvault_proof_lost_approval(tmp_path, monkeypatch):
    Checks(monkeypatch)
    layout = workspace(tmp_path)
    rows = [dict(row, approval_status="pending") if row["proof_id"] == NONVAULT_ID else row for row in nonvault_rows()]
    write_json(tmp_path / "config" / "nonvault-customer-proof-index.json", {
        "schema": "seomachine-nonvault-customer-proof-index/v1", "version": 1, "proof": rows})
    assert run(layout, refresher=selector_refresh.refresh_selector_evidence) == 1
    refused = layout.bom.with_name(layout.bom.name + ".refused")
    assert not layout.bom.exists() and refused.exists()
    record = latest_record(layout)
    assert record["passed"] is False and {row["check"] for row in record["findings"]} == {"bom_refused"}
    assert any(NONVAULT_ID in row["message"] for row in record["findings"])
