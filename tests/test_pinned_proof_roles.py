"""A pin is offered only in a role its claim supports, and every selector entry point keeps it."""

from __future__ import annotations

import json
from datetime import date
from unittest.mock import patch

from data_sources.modules.customer_proof.nonconnector_cli import _main as nonvault_selector_main
from data_sources.modules.customer_proof.nonconnector_selection import select_nonvault_customer_proofs
from data_sources.modules.customer_proof.selection import select_customer_proofs
from data_sources.modules.customer_proof.selector_cli import _main as connector_selector_main
from tests.production_bom_support import NONVAULT_ID, TODAY, make_workspace, nonconnector_spec
from tests.test_customer_proof_selector import write_ledger
from tests.test_production_selector_pinning import VAULT_PATCH, ZEBRA, _claims
from tests.vault_context_fixture import load_validated_claim_set_for_unit_test, write_connector_context_fixture

SLUG = "field-service-software"
ZEBRA_URL = "https://www.simprogroup.com/case-studies/zebra-plumbing"
ROLES = "metric,quote,theme,experience_story"


def _self_use(proof_id: str, url: str = "x") -> dict:
    return {"proof_id": proof_id, "source_url": url, "article_slug": SLUG, "date_used": TODAY}


def _connector_ids(root, role: str, pinned: str) -> list[str]:
    root.mkdir()
    pack, receipt = write_connector_context_fixture(root, _claims())
    ledger = write_ledger(root, [_self_use(ZEBRA, ZEBRA_URL)])
    with patch(VAULT_PATCH, new=load_validated_claim_set_for_unit_test):
        results = select_customer_proofs(
            "quoting invoicing", ledger_path=ledger, context_pack=pack, context_receipt=receipt,
            article_slug=SLUG, proof_role=role, pinned=pinned, reference_date=date.fromisoformat(TODAY),
        )
    return [str(row["proof_id"]) for row in results]


def test_connector_pin_is_refused_in_a_role_its_claim_does_not_support(tmp_path):
    assert ZEBRA in _connector_ids(tmp_path / "metric", "metric", ZEBRA)
    for role in ("quote", "theme", "experience_story"):
        assert ZEBRA not in _connector_ids(tmp_path / role, role, ZEBRA)


def _nonvault_ids(root, role: str, pinned: str, *, eeat: bool = False) -> list[str]:
    make_workspace(root, spec=nonconnector_spec())
    results = select_nonvault_customer_proofs(
        "Crew Time Tracking Guide", brand="ClockShark", index_path=root / "config" / "nonvault-customer-proof-index.json",
        ledger_path=root / "config" / "customer-proof-usage-ledger.json", article_slug=SLUG, proof_role=role,
        require_eeat_story=eeat, limit=1, reference_date=date.fromisoformat(TODAY), pinned=pinned,
    )
    return [str(row["proof_id"]) for row in results]


def test_nonvault_pin_is_refused_in_a_role_its_row_does_not_support(tmp_path):
    assert "clockshark-plain" not in _nonvault_ids(tmp_path / "metric", "metric", "clockshark-plain")
    assert "clockshark-plain" not in _nonvault_ids(tmp_path / "quote", "quote", "clockshark-plain")
    assert NONVAULT_ID not in _nonvault_ids(tmp_path / "story", "experience_story", NONVAULT_ID, eeat=True)
    assert _nonvault_ids(tmp_path / "theme", "theme", "clockshark-plain")[-1] == "clockshark-plain"


def test_connector_decision_block_keeps_a_pin_used_earlier_in_this_article(tmp_path):
    pack, receipt = write_connector_context_fixture(tmp_path, _claims())
    ledger = write_ledger(tmp_path, [_self_use(ZEBRA, ZEBRA_URL)])
    with patch(VAULT_PATCH, new=load_validated_claim_set_for_unit_test):
        assert connector_selector_main([
            "quoting invoicing review story", "--ledger", str(ledger), "--context-pack", str(pack),
            "--context-receipt", str(receipt), "--slate", "--roles", ROLES, "--require-eeat-story",
            "--article-slug", SLUG, "--selected", f"metric={ZEBRA}", "--decision-block",
            "--evidence-output", str(tmp_path / "evidence.json"),
        ]) == 0


def test_nonvault_cli_keeps_a_pin_the_penalty_and_limit_would_drop(tmp_path, capsys):
    make_workspace(tmp_path, spec=nonconnector_spec())
    ledger = tmp_path / "config" / "customer-proof-usage-ledger.json"
    ledger.write_text(json.dumps({"version": 1, "uses": [_self_use(NONVAULT_ID)]}), encoding="utf-8")
    assert nonvault_selector_main([
        "Crew Time Tracking Guide", "--brand", "ClockShark", "--article-slug", SLUG, "--limit", "1",
        "--index", str(tmp_path / "config" / "nonvault-customer-proof-index.json"), "--ledger", str(ledger),
        "--reference-date", TODAY, "--selected", f"theme={NONVAULT_ID}",
    ]) == 0
    rows = json.loads(capsys.readouterr().out)
    assert next(row for row in rows if row["role"] == "theme")["selected_id"] == NONVAULT_ID
