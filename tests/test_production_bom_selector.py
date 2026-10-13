"""BOM build: customer-proof selector evidence binding and PAA run identity."""

from __future__ import annotations

import hashlib
import json

import pytest
from data_sources.modules.production import bom_build
from data_sources.modules.production.layout import stored_run_id
from tests.production_bom_support import (
    CLAIM_ID,
    NONVAULT_ID,
    TODAY,
    good_loader,
    good_transport,
    make_workspace,
    nonconnector_spec,
    paa_artifact,
    selector_evidence,
    write_json,
)


@pytest.fixture(autouse=True)
def _pinned_clock(monkeypatch):
    monkeypatch.setenv("SEOMACHINE_TEST_CURRENT_UTC_DATE", TODAY)


def _build(layout):
    return bom_build.build_bom(layout, transport=good_transport(), claim_loader=good_loader())


def _refused(layout, match):
    with pytest.raises(ValueError, match=match):
        _build(layout)


def _sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_layout_names_the_selector_evidence_files(tmp_path):
    layout = make_workspace(tmp_path)
    assert layout.customer_proof_evidence.name == "customer-proof-selector-evidence-field-service-software.json"
    assert layout.nonvault_customer_proof_evidence.name == (
        "nonvault-customer-proof-selector-evidence-field-service-software.json"
    )


def test_connector_bom_binds_selector_evidence_and_its_selection(tmp_path):
    layout = make_workspace(tmp_path)
    bound = _build(layout)["customer_proof"]
    assert bound["evidence"] == {
        "path": "research/customer-proof-selector-evidence-field-service-software.json",
        "sha256": _sha(layout.customer_proof_evidence),
    }
    assert bound["schema"] == "simpro-customer-proof-selector-evidence/v2"
    metric = next(role for role in bound["roles"] if role["role"] == "metric")
    assert metric["selected_id"] == CLAIM_ID


def test_nonconnector_bom_binds_nonvault_selector_evidence(tmp_path):
    layout = make_workspace(tmp_path, spec=nonconnector_spec(), context=False)
    bound = _build(layout)["customer_proof"]
    assert bound["evidence"]["path"] == (
        "research/nonvault-customer-proof-selector-evidence-field-service-software.json"
    )
    assert bound["schema"] == "simpro-nonvault-customer-proof-selector-evidence/v1"
    theme = next(role for role in bound["roles"] if role["role"] == "theme")
    assert theme["selected_id"] == NONVAULT_ID


def test_proof_id_absent_from_selector_evidence_refuses_naming_it(tmp_path):
    layout = make_workspace(tmp_path)
    evidence = selector_evidence({"proof": []}, nonconnector=False)
    write_json(layout.customer_proof_evidence, evidence)
    _refused(layout, rf"p1.*{CLAIM_ID}.*selector evidence")


def test_missing_selector_evidence_refuses_naming_the_file(tmp_path):
    layout = make_workspace(tmp_path)
    layout.customer_proof_evidence.unlink()
    _refused(layout, "customer-proof-selector-evidence-field-service-software.json")


def test_selector_evidence_with_the_wrong_schema_refuses(tmp_path):
    layout = make_workspace(tmp_path)
    evidence = json.loads(layout.customer_proof_evidence.read_text(encoding="utf-8"))
    evidence["schema"] = "simpro-nonvault-customer-proof-selector-evidence/v1"
    write_json(layout.customer_proof_evidence, evidence)
    _refused(layout, "selector evidence schema")


def test_no_fit_selector_evidence_is_recorded_in_the_bom(tmp_path):
    layout = make_workspace(tmp_path)
    reason = "No customer proof selected because none fits; public copy must omit customer proof."
    evidence = selector_evidence({"proof": []}, nonconnector=False)
    evidence["selection_outcome"] = "no_fit_customer_proof"
    for role in evidence["roles"]:
        role.update(selection_outcome="no_fit_customer_proof", no_fit_reason=reason)
    write_json(layout.customer_proof_evidence, evidence)
    spec = json.loads(layout.bom_spec.read_text(encoding="utf-8"))
    spec["proof"] = []
    write_json(layout.bom_spec, spec)
    bound = _build(layout)["customer_proof"]
    assert bound["selection_outcome"] == "no_fit_customer_proof"
    story = next(role for role in bound["roles"] if role["role"] == "experience_story")
    assert story["selected_id"] == "none" and story["no_fit_reason"] == reason


def test_bom_records_paa_collection_date_and_run_id(tmp_path):
    layout = make_workspace(tmp_path)
    bom = _build(layout)
    assert bom["paa"]["collection_date"] == TODAY
    assert bom["paa"]["run_id"] == bom["identity"]["run_id"] == stored_run_id(layout)


def test_paa_artifact_from_another_run_refuses(tmp_path):
    layout = make_workspace(tmp_path)
    write_json(layout.paa_artifact, paa_artifact("another-run"))
    _refused(layout, "PAA artifact run id another-run does not match the production run id")


def test_paa_artifact_without_run_id_refuses(tmp_path):
    layout = make_workspace(tmp_path)
    write_json(layout.paa_artifact, {"eligible_questions": ["What is field service software?"]})
    _refused(layout, "run_receipt.run_id")


def test_paa_artifact_before_any_production_run_refuses(tmp_path):
    layout = make_workspace(tmp_path)
    layout.run_state.unlink()
    _refused(layout, "does not match the production run id")


def test_paa_artifact_dated_before_the_article_refuses(tmp_path):
    layout = make_workspace(tmp_path)
    write_json(layout.paa_artifact, paa_artifact(stored_run_id(layout), collection_date="2026-07-01"))
    _refused(layout, "collection_date 2026-07-01 does not match the article date 2026-10-13")


def test_proof_id_only_among_candidates_but_not_selected_refuses(tmp_path):
    layout = make_workspace(tmp_path)
    evidence = json.loads(layout.customer_proof_evidence.read_text(encoding="utf-8"))
    metric = next(role for role in evidence["roles"] if role["role"] == "metric")
    metric["selected_id"] = "none"
    assert CLAIM_ID in metric["candidate_ids"]
    write_json(layout.customer_proof_evidence, evidence)
    _refused(layout, rf"p1.*{CLAIM_ID}.*not a selected candidate")


def test_forged_nonvault_selector_evidence_refuses(tmp_path):
    spec = nonconnector_spec()
    layout = make_workspace(tmp_path, spec=spec, context=False)
    write_json(layout.nonvault_customer_proof_evidence, selector_evidence(spec, nonconnector=True))
    _refused(layout, "failed verification")
