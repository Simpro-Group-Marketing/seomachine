"""Release integrity: unreachable fact pages, lost quotes, failure records, and evidence routing."""

from __future__ import annotations

import json
import os

import pytest
import requests
from data_sources.modules import vault_claim_receipts
from data_sources.modules.customer_proof import connector_inputs
from data_sources.modules.production import release
from data_sources.modules.production.record import latest_record, verify_publishable
from tests.production_bom_support import ARTICLE, FACT_URL, TODAY, write_json
from tests.production_release_support import (
    LINKED_ARTICLE_TEXT,
    Checks,
    PageTransport,
    release_dirs,
    run,
    workspace,
)

LOST_PAGE = "<html><body><p>Nothing relevant here.</p></body></html>"
CONNECTOR_SCHEMA = "simpro-customer-proof-selector-evidence/v2"


@pytest.fixture(autouse=True)
def _environment(monkeypatch):
    monkeypatch.setenv("SEOMACHINE_TEST_CURRENT_UTC_DATE", TODAY)
    monkeypatch.delenv(release.ENV_WORKERS, raising=False)


@pytest.fixture
def layout(tmp_path):
    return workspace(tmp_path, text=LINKED_ARTICLE_TEXT)


@pytest.fixture
def no_vault(monkeypatch):
    """Fail loudly if anything reaches the brand vault."""
    calls = []

    def refuse(*args, **kwargs):
        calls.append(args)
        raise AssertionError("the vault must not be called")

    monkeypatch.setattr(vault_claim_receipts, "SimproVaultClient", refuse)
    monkeypatch.setattr(vault_claim_receipts, "load_validated_claim_set", refuse)
    monkeypatch.setattr(connector_inputs, "load_validated_claim_set", refuse)
    monkeypatch.setattr(release, "load_validated_claim_set", refuse)
    return calls


def _fact(layout):
    return json.loads(layout.bom.read_text(encoding="utf-8"))["facts"][0]


# ---- C1: unreachable fact pages warn and carry the verified fact forward ------------------


@pytest.mark.parametrize("reply", [(403, ""), requests.Timeout("slow")], ids=["403", "timeout"])
def test_unreachable_fact_page_warns_with_the_original_verified_at(layout, monkeypatch, reply):
    Checks(monkeypatch, real_truth=True)
    original = _fact(layout)["verified_at"]
    assert run(layout, transport=PageTransport({FACT_URL: reply})) == 0
    fact = _fact(layout)
    assert fact["verified_at"] == original and fact["carried_forward"] is True
    warns = [row for row in latest_record(layout)["findings"] if row["check"] == "fact_quote"]
    assert [row["severity"] for row in warns] == ["warn"]
    assert f"last verified at {original}" in warns[0]["message"]
    assert verify_publishable(layout.article, layout.root)["passed"] is True


def test_lost_quote_exits_one_naming_the_fact_and_url_and_blocks_publishing(layout, monkeypatch, capsys):
    Checks(monkeypatch, real_truth=True)
    assert run(layout, transport=PageTransport()) == 0
    assert run(layout, transport=PageTransport({FACT_URL: (200, LOST_PAGE)})) == 1
    err = capsys.readouterr().err
    assert "fact f1" in err and FACT_URL in err and "quote_missing" in err
    with pytest.raises(ValueError, match="did not pass"):
        verify_publishable(layout.article, layout.root)


# ---- I1: every blocked release leaves a failing latest record -------------------------------


def test_failing_record_supersedes_a_pass_even_when_the_refused_rename_fails(layout, monkeypatch, capsys):
    Checks(monkeypatch)
    assert run(layout, transport=PageTransport()) == 0
    kept = layout.bom.read_bytes()
    real_replace = os.replace

    def replace(src, dst, *args, **kwargs):
        if os.fspath(src) == os.fspath(layout.bom):
            raise PermissionError("file is locked")
        return real_replace(src, dst, *args, **kwargs)

    monkeypatch.setattr(os, "replace", replace)
    assert run(layout, transport=PageTransport({FACT_URL: (200, LOST_PAGE)})) == 1
    assert "file is locked" in capsys.readouterr().err
    assert layout.bom.read_bytes() == kept and len(release_dirs(layout)) == 2
    record = latest_record(layout)
    assert record["passed"] is False and record["bom"] is None and record["scores"] is None
    assert [row["check"] for row in record["findings"]] == ["bom_refused"]
    with pytest.raises(ValueError, match="did not pass"):
        verify_publishable(layout.article, layout.root)


# ---- M4: evidence routing by connector or nonconnector ------------------------------------


def _stray_connector_evidence(path):
    write_json(path, {"schema": CONNECTOR_SCHEMA, "inputs": {"topic": "x"}, "artifacts": {}, "roles": []})


def test_stray_connector_evidence_bound_to_a_nonconnector_bom_is_refused_without_the_vault(
    layout, monkeypatch, no_vault, capsys
):
    Checks(monkeypatch)
    _stray_connector_evidence(layout.customer_proof_evidence)
    bom = json.loads(layout.bom.read_text(encoding="utf-8"))
    bom["customer_proof"]["evidence"]["path"] = layout.customer_proof_evidence.relative_to(layout.root).as_posix()
    write_json(layout.bom, bom)
    assert release.run_release(ARTICLE, layout.root, workers=1, transport=PageTransport()) == 2
    assert "nonconnector" in capsys.readouterr().err and no_vault == []


def test_connector_schema_in_the_nonvault_evidence_file_is_refused_without_the_vault(
    layout, monkeypatch, no_vault, capsys
):
    Checks(monkeypatch)
    _stray_connector_evidence(layout.nonvault_customer_proof_evidence)
    assert release.run_release(ARTICLE, layout.root, workers=1, transport=PageTransport()) == 2
    assert CONNECTOR_SCHEMA in capsys.readouterr().err and no_vault == []


# ---- Review Focus 5: a nonconnector release never touches the vault ---------------------------


def test_nonconnector_release_uses_only_nonvault_proof_and_never_the_vault(layout, monkeypatch, no_vault):
    Checks(monkeypatch)
    assert release.run_release(ARTICLE, layout.root, workers=2, transport=PageTransport()) == 0
    bom = json.loads(layout.bom.read_text(encoding="utf-8"))
    assert bom["context"]["status"] == "not_applicable"
    index = json.loads((layout.root / "config" / "nonvault-customer-proof-index.json").read_text(encoding="utf-8"))
    rows = {row["proof_id"]: row for row in index["proof"]}
    assert bom["proof"] and all(item["url"] == rows[item["claim_id"]]["public_url"] for item in bom["proof"])
    assert bom["customer_proof"]["schema"] == "simpro-nonvault-customer-proof-selector-evidence/v1"
    assert no_vault == []
