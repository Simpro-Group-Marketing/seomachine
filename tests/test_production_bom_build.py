"""Tests for the production BOM builder and its CLI."""

from __future__ import annotations

import copy
import json
import re

import pytest
import requests
from data_sources.modules.production import bom_build
from data_sources.modules.production.bom import validate_bom
from data_sources.modules.vault_claim_receipts import ValidatedClaimSet
from tests.production_bom_support import (
    ARTICLE,
    CLAIM_ID,
    FACT_CLAIM,
    FACT_PAGE,
    FACT_QUOTE,
    FACT_URL,
    NONVAULT_ID,
    PAA_QUESTION,
    PILLAR_ID,
    FakeLoader,
    FakeTransport,
    approved_claim,
    connector_spec,
    good_loader,
    good_transport,
    make_workspace,
    nonconnector_spec,
    TODAY,
    pillar_record,
    response,
    write_json,
    write_pillar_index,
)


@pytest.fixture(autouse=True)
def _pinned_clock(monkeypatch):
    monkeypatch.setenv("SEOMACHINE_TEST_CURRENT_UTC_DATE", TODAY)


def _build(layout, *, transport=None, loader=None):
    return bom_build.build_bom(
        layout,
        transport=transport or good_transport(),
        claim_loader=loader or good_loader(),
    )


def _mutate(layout, change):
    spec = json.loads(layout.bom_spec.read_text(encoding="utf-8"))
    change(spec)
    write_json(layout.bom_spec, spec)


def _refused(layout, match, **kwargs):
    with pytest.raises(ValueError, match=match):
        _build(layout, **kwargs)


# ---- connector happy path -------------------------------------------------


def test_connector_build_is_complete_and_valid(tmp_path):
    layout = make_workspace(tmp_path)
    loader = good_loader()
    bom = _build(layout, loader=loader)
    assert validate_bom(bom) == []
    assert loader.calls == [(layout.context_pack, layout.context_receipt)]
    identity = bom["identity"]
    assert identity["slug"] == "field-service-software"
    assert identity["date"] == "2026-10-13"
    assert identity["workflow_mode"] == "new"
    assert identity["article_path"] == ARTICLE
    assert identity["brand"] == "Simpro" and identity["market"] == "US"
    assert identity["title"] == "Field Service Software Guide"
    assert identity["objective"] and identity["audience"]
    assert identity["cta"]["text"] == "Book a demo"
    assert identity["schema_notes"] == ["BlogPosting", "BreadcrumbList"]
    assert re.fullmatch(r"[0-9a-f-]{36}", identity["run_id"])
    assert bom["context"]["status"] == "bound"
    assert bom["context"]["pack"]["path"] == "research/context-pack-field-service-software.json"
    assert len(bom["context"]["receipt"]["sha256"]) == 64


def test_artifacts_are_bound_with_path_and_sha256(tmp_path):
    layout = make_workspace(tmp_path)
    bom = _build(layout)
    bound = [
        bom["keyword"]["decision"], bom["keyword"]["shortlist"],
        bom["serp"]["evidence"], bom["serp"]["coverage"], bom["paa"]["artifact"],
    ]
    for binding in bound:
        assert set(binding) == {"path", "sha256"}
        assert len(binding["sha256"]) == 64
    assert bom["paa"]["artifact"]["path"] == "research/paa-evidence-field-service-software-2026-10-13.json"


def test_keyword_and_serp_blocks_copy_from_artifacts(tmp_path):
    bom = _build(make_workspace(tmp_path))
    assert bom["keyword"]["primary"] == "field service software"
    assert bom["keyword"]["secondary"] == ["fsm software"]
    assert bom["keyword"]["candidates"] == [{"keyword": "fsm", "volume": 100}]
    assert bom["keyword"]["decision_rule"] == "highest volume under KD 50"
    assert bom["serp"]["query"] == "field service software"
    assert bom["serp"]["topics"][0]["topic"] == "pricing"
    assert bom["serp"]["uncovered_questions"] == ["Is it worth it?"]


def test_facts_carry_one_verification_timestamp(tmp_path):
    spec = connector_spec()
    spec["facts"].append({"id": "f2", "claim": "Crews can log time from any phone",
                          "url": FACT_URL, "quote": "Crews log time from any phone", "priority": "should"})
    layout = make_workspace(tmp_path, spec=spec)
    transport = good_transport()
    bom = _build(layout, transport=transport)
    assert transport.calls == [[FACT_URL]]
    first, second = bom["facts"]
    assert first["id"] == "f1" and first["quote"] == FACT_QUOTE and first["url"] == FACT_URL
    assert first["claim"] == FACT_CLAIM
    assert first["priority"] == "must"
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", first["verified_at"])
    assert first["verified_at"] == second["verified_at"]
    assert first["check_detail"] == "quote found on page"
    assert first["support"] == "quote_overlap"


def test_proof_text_comes_from_the_approved_claim(tmp_path):
    bom = _build(make_workspace(tmp_path))
    item = bom["proof"][0]
    assert item["id"] == "p1" and item["kind"] == "metric" and item["priority"] == "should"
    assert item["claim_id"] == CLAIM_ID
    assert item["text"] == "Customers report 30% faster invoicing."
    assert item["use_mode"] == "public_metric" and item["claim_type"] == "public_metric"
    assert item["url"] == "https://www.simprogroup.com/customers/acme"
    assert item["receipt_revision"] == "rev-7"
    assert item["customer"] == "Acme Electrical"


def test_claim_without_mapping_evidence_has_empty_customer(tmp_path):
    layout = make_workspace(tmp_path)
    loader = FakeLoader(ValidatedClaimSet([approved_claim(evidence=None)]))
    assert _build(layout, loader=loader)["proof"][0]["customer"] == ""


def test_sections_paa_links_and_pillar(tmp_path):
    bom = _build(make_workspace(tmp_path))
    assert bom["sections"] == [{"heading": "What it is", "purpose": "Define the term", "priority": "must"}]
    assert bom["paa"]["questions"] == [{"question": PAA_QUESTION, "priority": "should"}]
    pillar = bom["links"][0]
    assert pillar["kind"] == "commercial_pillar" and pillar["destination_id"] == PILLAR_ID
    assert pillar["priority"] == "must"


def test_paa_match_ignores_case_and_whitespace(tmp_path):
    layout = make_workspace(tmp_path)
    _mutate(layout, lambda s: s["paa_questions"][0].update(question="  WHAT is   field service SOFTWARE? "))
    assert _build(layout)["paa"]["questions"][0]["question"] == PAA_QUESTION


def test_no_paa_questions_needs_no_paa_artifact(tmp_path):
    layout = make_workspace(tmp_path, paa=False)
    _mutate(layout, lambda s: s.update(paa_questions=[]))
    bom = _build(layout)
    assert bom["paa"] == {"artifact": None, "questions": []}


def test_rebuild_reuses_the_stored_run_id(tmp_path):
    layout = make_workspace(tmp_path)
    assert _build(layout)["identity"]["run_id"] == _build(layout)["identity"]["run_id"]


# ---- fact abort paths -----------------------------------------------------


def test_missing_quote_aborts_naming_fact_id(tmp_path):
    layout = make_workspace(tmp_path)
    page = "<html><body><p>Nothing relevant here.</p></body></html>"
    transport = FakeTransport({FACT_URL: response(FACT_URL, 200, page)})
    _refused(layout, r"f1.*quote_missing", transport=transport)


def test_unreachable_page_aborts(tmp_path):
    layout = make_workspace(tmp_path)
    transport = FakeTransport({FACT_URL: requests.Timeout("slow")})
    _refused(layout, r"f1.*unreachable", transport=transport)


def test_gone_page_aborts_naming_url(tmp_path):
    layout = make_workspace(tmp_path)
    transport = FakeTransport({FACT_URL: response(FACT_URL, 404)})
    _refused(layout, rf"f1.*{re.escape(FACT_URL)}.*gone", transport=transport)


def test_unsupported_numbers_abort_naming_missing(tmp_path):
    layout = make_workspace(tmp_path)
    _mutate(layout, lambda s: s["facts"][0].update(claim="99,000 trade businesses use it"))
    _refused(layout, r"f1.*99000")


def test_duplicate_fact_ids_abort(tmp_path):
    layout = make_workspace(tmp_path)
    _mutate(layout, lambda s: s["facts"].append(copy.deepcopy(s["facts"][0])))
    _refused(layout, "duplicate fact id")


def test_aborted_build_does_not_mint_run_state(tmp_path):
    layout = make_workspace(tmp_path, paa=False)
    _mutate(layout, lambda s: s.update(paa_questions=[]))
    transport = FakeTransport({FACT_URL: response(FACT_URL, 200, "<p>none</p>")})
    _refused(layout, "f1", transport=transport)
    assert not layout.run_state.exists()


# ---- proof abort paths ----------------------------------------------------


def test_unknown_claim_id_aborts_naming_id(tmp_path):
    layout = make_workspace(tmp_path)
    _mutate(layout, lambda s: s["proof"][0].update(claim_id="claim-nope"))
    _refused(layout, "claim-nope")


def test_blocked_claim_set_aborts_with_its_blocker(tmp_path):
    layout = make_workspace(tmp_path)
    loader = FakeLoader(ValidatedClaimSet(blocker="receipt is stale"))
    _refused(layout, "receipt is stale", loader=loader)


def test_spec_proof_with_text_aborts(tmp_path):
    layout = make_workspace(tmp_path)
    _mutate(layout, lambda s: s["proof"][0].update(text="typed proof"))
    _refused(layout, "text")


def test_connector_spec_with_not_applicable_reason_aborts(tmp_path):
    layout = make_workspace(tmp_path)
    _mutate(layout, lambda s: s.update(not_applicable_context_reason="skip it"))
    _refused(layout, "not_applicable_context_reason")


# ---- paa / artifact abort paths --------------------------------------------


def test_paa_question_absent_from_artifact_aborts(tmp_path):
    layout = make_workspace(tmp_path)
    _mutate(layout, lambda s: s["paa_questions"][0].update(question="Invented question?"))
    _refused(layout, "Invented question")


def test_paa_questions_without_artifact_abort(tmp_path):
    layout = make_workspace(tmp_path, paa=False)
    _refused(layout, "paa-evidence")


@pytest.mark.parametrize("attr", ["keyword_decision", "keyword_shortlist", "serp_evidence", "serp_coverage"])
def test_missing_always_required_artifact_aborts(tmp_path, attr):
    layout = make_workspace(tmp_path)
    getattr(layout, attr).unlink()
    _refused(layout, re.escape(getattr(layout, attr).name))


@pytest.mark.parametrize("attr", ["context_pack", "context_receipt"])
def test_connector_needs_context_artifacts_and_never_loads_without_them(tmp_path, attr):
    layout = make_workspace(tmp_path)
    getattr(layout, attr).unlink()
    loader = good_loader()
    _refused(layout, re.escape(getattr(layout, attr).name), loader=loader)
    assert loader.calls == []


def test_shortlist_missing_a_key_aborts(tmp_path):
    layout = make_workspace(tmp_path)
    write_json(layout.keyword_shortlist, {"primary": "x"})
    _refused(layout, "decision_rule")


# ---- link abort paths ---------------------------------------------------------


def test_wrong_pillar_url_aborts(tmp_path):
    layout = make_workspace(tmp_path)
    _mutate(layout, lambda s: s["links"][0].update(url="https://www.simprogroup.com/other/"))
    _refused(layout, "canonical")


def test_anchor_without_main_keyword_aborts(tmp_path):
    layout = make_workspace(tmp_path)
    _mutate(layout, lambda s: s["links"][0].update(anchor="click here"))
    _refused(layout, "main keyword")


def test_anchor_match_ignores_case_and_spacing(tmp_path):
    layout = make_workspace(tmp_path)
    _mutate(layout, lambda s: s["links"][0].update(anchor="The  Field SERVICE management   software tool"))
    assert _build(layout)["links"][0]["kind"] == "commercial_pillar"


def test_pillar_must_be_priority_must(tmp_path):
    layout = make_workspace(tmp_path)
    _mutate(layout, lambda s: s["links"][0].update(priority="should"))
    _refused(layout, "must")


def test_connector_requires_exactly_one_pillar(tmp_path):
    layout = make_workspace(tmp_path)
    _mutate(layout, lambda s: s["links"].pop(0))
    _refused(layout, "commercial_pillar")
    layout = make_workspace(tmp_path)
    _mutate(layout, lambda s: s["links"].append(copy.deepcopy(s["links"][0])))
    _refused(layout, "commercial_pillar")


def test_pillar_without_destination_id_aborts(tmp_path):
    layout = make_workspace(tmp_path)
    _mutate(layout, lambda s: s["links"][0].pop("destination_id"))
    _refused(layout, "destination_id")


def test_unknown_destination_id_aborts(tmp_path):
    layout = make_workspace(tmp_path)
    _mutate(layout, lambda s: s["links"][0].update(destination_id="no-such-destination"))
    _refused(layout, "no-such-destination")


def test_destination_for_another_market_aborts(tmp_path):
    layout = make_workspace(tmp_path)
    write_pillar_index(layout.root, pillar_record(market="AU"))
    _refused(layout, "market")


def test_unknown_link_kind_aborts(tmp_path):
    layout = make_workspace(tmp_path)
    _mutate(layout, lambda s: s["links"][1].update(kind="affiliate"))
    _refused(layout, "kind")


def test_bad_spec_lists_every_error_at_once(tmp_path):
    layout = make_workspace(tmp_path)

    def damage(spec):
        spec["facts"][0]["priority"] = "could"
        spec["links"][1]["kind"] = "affiliate"
        del spec["title"]

    _mutate(layout, damage)
    with pytest.raises(ValueError) as caught:
        _build(layout)
    message = str(caught.value)
    assert "priority" in message and "kind" in message and "title" in message


# ---- nonconnector -----------------------------------------------------------


def test_nonconnector_build_never_calls_loader(tmp_path):
    layout = make_workspace(tmp_path, spec=nonconnector_spec(), context=False)
    loader = good_loader()
    bom = _build(layout, loader=loader)
    assert loader.calls == []
    assert validate_bom(bom) == []
    assert bom["context"] == {
        "status": "not_applicable",
        "reason": "ClockShark workflow with no brand-vault signal",
    }
    item = bom["proof"][0]
    assert item["claim_id"] == NONVAULT_ID and item["id"] == "p1"
    assert item["customer"] == "Chesapeake Lawn and Home"
    assert item["url"] == "https://www.clockshark.com/testimonials/chesapeake"
    assert item["text"].startswith("ClockShark page states")
    assert item["restrictions"] == ["Paraphrase only"]
    assert [q["quote"] for q in item["approved_quotes"]] == ["easy to use"]
    assert item["approved_metrics"] == [{"metric": "5 hours saved", "status": "approved"}]
    assert all(link["kind"] != "commercial_pillar" for link in bom["links"])


@pytest.mark.parametrize("claim_id", ["clockshark-pending", "clockshark-nopublic", "clockshark-absent"])
def test_nonconnector_unapproved_or_unknown_row_aborts(tmp_path, claim_id):
    spec = nonconnector_spec()
    spec["proof"][0]["claim_id"] = claim_id
    layout = make_workspace(tmp_path, spec=spec, context=False)
    _refused(layout, claim_id)


def test_nonconnector_without_reason_aborts(tmp_path):
    spec = nonconnector_spec()
    del spec["not_applicable_context_reason"]
    layout = make_workspace(tmp_path, spec=spec, context=False)
    loader = good_loader()
    _refused(layout, "not_applicable_context_reason", loader=loader)


def test_nonconnector_brand_with_simpro_signal_is_connector(tmp_path):
    spec = nonconnector_spec()
    spec["title"] = "Simpro versus ClockShark"
    layout = make_workspace(tmp_path, spec=spec, context=False)
    _refused(layout, "not_applicable_context_reason")


# ---- CLI --------------------------------------------------------------------------


@pytest.fixture
def cli(monkeypatch):
    class FakePublicTransport(FakeTransport):
        def __init__(self):
            super().__init__({FACT_URL: response(FACT_URL, 200, FACT_PAGE)})

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

    monkeypatch.setattr(bom_build, "PublicHttpTransport", FakePublicTransport)
    monkeypatch.setattr(bom_build, "load_validated_claim_set", good_loader())
    return lambda root: bom_build.main([ARTICLE, "--workspace-root", str(root)])


def test_cli_success_writes_bom_and_exits_zero(tmp_path, cli):
    layout = make_workspace(tmp_path)
    assert cli(tmp_path) == 0
    written = json.loads(layout.bom.read_text(encoding="utf-8"))
    assert written["schema"] == "simpro-production-bom/v1"
    assert validate_bom(written) == []


def test_cli_refusal_prints_one_line_per_reason_and_writes_nothing(tmp_path, cli, capsys):
    layout = make_workspace(tmp_path)

    def damage(spec):
        spec["proof"][0]["claim_id"] = "claim-nope"
        spec["paa_questions"][0]["question"] = "Invented?"

    _mutate(layout, damage)
    assert cli(tmp_path) == 1
    lines = [line for line in capsys.readouterr().err.splitlines() if line.strip()]
    assert any("claim-nope" in line for line in lines)
    assert not layout.bom.exists()


def test_cli_missing_spec_exits_two(tmp_path, cli):
    layout = make_workspace(tmp_path)
    layout.bom_spec.unlink()
    assert cli(tmp_path) == 2
    assert not layout.bom.exists()


def test_cli_invalid_json_spec_exits_two(tmp_path, cli):
    layout = make_workspace(tmp_path)
    layout.bom_spec.write_text("{not json", encoding="utf-8")
    assert cli(tmp_path) == 2
    assert not layout.bom.exists()


def test_cli_non_object_spec_exits_two(tmp_path, cli):
    layout = make_workspace(tmp_path)
    layout.bom_spec.write_text("[]", encoding="utf-8")
    assert cli(tmp_path) == 2


def test_cli_layout_error_exits_two(tmp_path, cli):
    make_workspace(tmp_path)
    assert bom_build.main(["notes/elsewhere.md", "--workspace-root", str(tmp_path)]) == 2
