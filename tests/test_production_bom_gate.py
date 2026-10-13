"""Gate tests: claim support, brand scope, proof kinds, pillar validation, free text, binding."""

from __future__ import annotations

import copy
import json

import pytest
from data_sources.modules.production import bom_artifacts, bom_build
from data_sources.modules.production.bom import BuildEnvironmentError, validate_spec
from data_sources.modules.production.claim_support import claim_support_errors
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
    STORY_ID,
    TODAY,
    FakeLoader,
    FakeTransport,
    approved_claim,
    connector_spec,
    good_loader,
    good_transport,
    make_workspace,
    nonconnector_spec,
    response,
    write_json,
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


def _nonconnector(tmp_path, **proof):
    spec = nonconnector_spec()
    spec["proof"][0].update(proof)
    return make_workspace(tmp_path, spec=spec, context=False)


# ---- C1: claim support -------------------------------------------------------


def test_support_happy_path():
    assert claim_support_errors("f1", FACT_CLAIM, FACT_QUOTE) == []


def test_one_word_quote_cannot_certify_a_claim():
    errors = claim_support_errors("f1", "Simpro is the most trusted platform in America", "trade")
    assert any("f1" in e and "quote_min_words" in e for e in errors)


def test_claim_sharing_no_words_with_quote_is_refused():
    errors = claim_support_errors("f9", "Technicians love scheduling dashboards daily",
                                  "Trusted by more than 24,000 trade businesses worldwide")
    assert any("f9" in e and "quote_overlap" in e for e in errors)


def test_comparator_flip_is_refused():
    errors = claim_support_errors("f2", "Fewer than 24,000 trade businesses worldwide trust it", FACT_QUOTE)
    assert any("f2" in e and "polarity" in e for e in errors)


def test_negation_only_in_quote_is_refused():
    errors = claim_support_errors("f3", "Crews log time from any phone",
                                  "Crews never log time from any phone")
    assert any("polarity" in e for e in errors)


def test_claim_without_content_words_is_refused():
    errors = claim_support_errors("f4", "It is the one", FACT_QUOTE)
    assert any("quote_overlap" in e for e in errors)


def test_build_refuses_trivial_quote(tmp_path):
    layout = make_workspace(tmp_path)
    _mutate(layout, lambda s: s["facts"][0].update(claim="Trade is great", quote="trade"))
    page = FakeTransport({FACT_URL: response(FACT_URL, 200, "<p>trade</p>")})
    _refused(layout, r"f1.*quote_min_words", transport=page)


def test_build_refuses_flipped_comparator(tmp_path):
    layout = make_workspace(tmp_path)
    _mutate(layout, lambda s: s["facts"][0].update(claim="Fewer than 24,000 trade businesses worldwide trust it"))
    _refused(layout, r"f1.*polarity")


# ---- C2: brand and market scope ------------------------------------------------


def test_cross_brand_row_is_refused(tmp_path):
    _refused(_nonconnector(tmp_path, claim_id="bigchange-story"), "bigchange-story")


def test_uk_row_is_refused_for_us_market(tmp_path):
    _refused(_nonconnector(tmp_path, claim_id="clockshark-uk"), r"clockshark-uk.*region")


@pytest.mark.parametrize("row", ["clockshark-global", "clockshark-noregion"])
def test_global_and_unscoped_rows_are_admitted(tmp_path, row):
    bom = _build(_nonconnector(tmp_path, claim_id=row))
    assert bom["proof"][0]["claim_id"] == row


def test_nonconnector_identity_uses_canonical_brand(tmp_path):
    spec = nonconnector_spec()
    spec["brand"] = "clockshark"
    bom = _build(make_workspace(tmp_path, spec=spec, context=False))
    assert bom["identity"]["brand"] == "ClockShark"


# ---- I1: proof kind --------------------------------------------------------------


def test_unknown_kind_is_refused_for_connector(tmp_path):
    layout = make_workspace(tmp_path)
    _mutate(layout, lambda s: s["proof"][0].update(kind="narrative"))
    _refused(layout, r"p1.*kind")


@pytest.mark.parametrize("kind", ["quote", "theme", "experience_story"])
def test_connector_use_mode_must_match_kind(tmp_path, kind):
    layout = make_workspace(tmp_path)
    _mutate(layout, lambda s: s["proof"][0].update(kind=kind))
    _refused(layout, r"p1.*use_mode")


def test_connector_paraphrase_claim_serves_theme(tmp_path):
    layout = make_workspace(tmp_path)
    _mutate(layout, lambda s: s["proof"][0].update(kind="theme"))
    loader = FakeLoader(ValidatedClaimSet([approved_claim(use_mode="public_paraphrase")]))
    assert _build(layout, loader=loader)["proof"][0]["kind"] == "theme"


def test_connector_unknown_use_mode_is_refused(tmp_path):
    layout = make_workspace(tmp_path)
    loader = FakeLoader(ValidatedClaimSet([approved_claim(use_mode="invented")]))
    _refused(layout, r"p1.*use_mode", loader=loader)


def test_nonconnector_unknown_kind_is_refused(tmp_path):
    _refused(_nonconnector(tmp_path, kind="story"), r"p1.*kind")


@pytest.mark.parametrize(
    ("kind", "row"),
    [("metric", "clockshark-plain"), ("quote", "clockshark-plain"), ("experience_story", NONVAULT_ID)],
)
def test_nonconnector_role_needs_matching_evidence(tmp_path, kind, row):
    _refused(_nonconnector(tmp_path, kind=kind, claim_id=row), rf"p1.*{kind}")


@pytest.mark.parametrize(
    ("kind", "row"),
    [("metric", NONVAULT_ID), ("quote", NONVAULT_ID), ("experience_story", STORY_ID)],
)
def test_nonconnector_role_with_evidence_is_admitted(tmp_path, kind, row):
    assert _build(_nonconnector(tmp_path, kind=kind, claim_id=row))["proof"][0]["kind"] == kind


# ---- I2: pillar index validation -------------------------------------------------


def test_expired_pillar_evidence_refuses(tmp_path, monkeypatch):
    layout = make_workspace(tmp_path)
    monkeypatch.setenv("SEOMACHINE_TEST_CURRENT_UTC_DATE", "2027-03-01")
    _refused(layout, "commercial_pillar_title_evidence_expired")


def test_tampered_evidence_refuses(tmp_path):
    layout = make_workspace(tmp_path)
    evidence = next((tmp_path / "research").glob("semrush-commercial-pillar-homepage*.md"))
    evidence.write_text(evidence.read_text(encoding="utf-8").replace("9,900", "9,901"), encoding="utf-8")
    _refused(layout, "commercial_pillar_evidence")


def test_unsupported_index_schema_refuses(tmp_path):
    layout = make_workspace(tmp_path)
    path = tmp_path / "context" / "commercial-pillar-index.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["schema_version"] = "other/v9"
    write_json(path, payload)
    _refused(layout, "commercial_pillar_schema_unsupported")


def test_missing_pillar_index_is_operational(tmp_path):
    layout = make_workspace(tmp_path)
    (tmp_path / "context" / "commercial-pillar-index.json").unlink()
    with pytest.raises(BuildEnvironmentError):
        _build(layout)


def test_missing_nonvault_index_is_operational(tmp_path):
    layout = _nonconnector(tmp_path)
    (tmp_path / "config" / "nonvault-customer-proof-index.json").unlink()
    with pytest.raises(BuildEnvironmentError):
        _build(layout)


def test_vault_outage_is_operational(tmp_path):
    from data_sources.modules.vault_claim_receipts import VaultClaimReceiptError

    def outage(pack, receipt):
        raise VaultClaimReceiptError("vault unreachable")

    with pytest.raises(BuildEnvironmentError):
        _build(make_workspace(tmp_path), loader=outage)


# ---- I3: spec binding and stale BOM -------------------------------------------------


def test_bom_binds_the_spec_bytes(tmp_path):
    import hashlib

    layout = make_workspace(tmp_path)
    bom = _build(layout)
    binding = bom["identity"]["spec"]
    assert binding["path"] == "research/production-bom-spec-field-service-software-2026-10-13.json"
    assert binding["sha256"] == hashlib.sha256(layout.bom_spec.read_bytes()).hexdigest()


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


def test_refused_rebuild_retires_the_old_bom(tmp_path, cli):
    layout = make_workspace(tmp_path)
    assert cli(tmp_path) == 0
    assert layout.bom.exists()
    _mutate(layout, lambda s: s["proof"][0].update(claim_id="claim-nope"))
    assert cli(tmp_path) == 1
    assert not layout.bom.exists()
    assert layout.bom.with_name(layout.bom.name + ".refused").exists()


def test_operational_failure_also_retires_the_old_bom(tmp_path, cli):
    layout = make_workspace(tmp_path)
    assert cli(tmp_path) == 0
    layout.bom_spec.unlink()
    assert cli(tmp_path) == 2
    assert not layout.bom.exists()
    assert layout.bom.with_name(layout.bom.name + ".refused").exists()


def test_second_refusal_replaces_the_earlier_refused_copy(tmp_path, cli):
    layout = make_workspace(tmp_path)
    refused = layout.bom.with_name(layout.bom.name + ".refused")
    refused.write_text("old", encoding="utf-8")
    layout.bom.write_text("newer", encoding="utf-8")
    layout.bom_spec.unlink()
    assert cli(tmp_path) == 2
    assert refused.read_text(encoding="utf-8") == "newer"


def test_cli_exit_two_for_missing_pillar_index(tmp_path, cli):
    make_workspace(tmp_path)
    (tmp_path / "context" / "commercial-pillar-index.json").unlink()
    assert cli(tmp_path) == 2


def test_cli_never_leaks_a_traceback(tmp_path, cli, monkeypatch, capsys):
    make_workspace(tmp_path)

    def boom(*args, **kwargs):
        raise RuntimeError("kaboom")

    monkeypatch.setattr(bom_build, "build_bom", boom)
    assert cli(tmp_path) == 2
    assert "kaboom" in capsys.readouterr().err


# ---- I4: free-text numbers and schema notes ---------------------------------------------


@pytest.mark.parametrize("field", ["title", "cta", "anchor", "heading"])
def test_unsupported_number_in_public_text_is_refused(tmp_path, field):
    layout = make_workspace(tmp_path)

    def change(spec):
        if field == "title":
            spec["title"] = "17 Field Service Tips"
        elif field == "cta":
            spec["cta"]["text"] = "Save 40% today"
        elif field == "anchor":
            spec["links"][1]["anchor"] = "our 99 point checklist"
        else:
            spec["sections"][0]["heading"] = "Why 7 crews switch"

    _mutate(layout, change)
    _refused(layout, field)


def test_numbers_from_facts_proof_and_year_are_allowed(tmp_path):
    layout = make_workspace(tmp_path)

    def change(spec):
        spec["title"] = "Field Service Software in 2026"
        spec["sections"][0]["heading"] = "24,000 trade businesses and 30% faster invoicing"

    _mutate(layout, change)
    assert _build(layout)["identity"]["title"] == "Field Service Software in 2026"


@pytest.mark.parametrize("heading", ["Step 1: Plan the route", "24/7 dispatch", "Tip 3 and Phase 2", "Rule #4 of dispatch", "STEP 10: Review"])
def test_list_numbering_and_24_7_are_not_claims(tmp_path, heading):
    layout = make_workspace(tmp_path)
    _mutate(layout, lambda s: s["sections"][0].update(heading=heading))
    assert _build(layout)["sections"][0]["heading"] == heading


def test_other_numbers_next_to_exempt_words_are_still_refused(tmp_path):
    layout = make_workspace(tmp_path)
    _mutate(layout, lambda s: s["sections"][0].update(heading="Save 15 hours"))
    _refused(layout, "heading")
    _mutate(layout, lambda s: s["sections"][0].update(heading="Step 1 saves 15 hours"))
    _refused(layout, "heading")


def test_section_purpose_numbers_are_exempt(tmp_path):
    layout = make_workspace(tmp_path)
    _mutate(layout, lambda s: s["sections"][0].update(purpose="Cover the top 5 buyer questions"))
    assert _build(layout)["sections"][0]["purpose"].startswith("Cover")


def test_schema_notes_are_restricted():
    spec = connector_spec()
    spec["schema_notes"] = ["BlogPosting", "HowTo"]
    assert any("schema_notes" in e and "HowTo" in e for e in validate_spec(spec))
    spec["schema_notes"] = ["Organization as publisher reference", "Question and Answer inside FAQPage"]
    assert validate_spec(spec) == []


# ---- M2: Unicode evasion of the connector signal ------------------------------------------


@pytest.mark.parametrize("sneaky", ["sim­pro", "ｓｉｍｐｒｏ", "sim​pro"])
def test_hidden_simpro_signal_makes_the_spec_connector(tmp_path, sneaky):
    spec = nonconnector_spec()
    spec["title"] = f"{sneaky} versus the rest"
    layout = make_workspace(tmp_path, spec=spec, context=False)
    _refused(layout, "not_applicable_context_reason")


# ---- M3: PAA ------------------------------------------------------------------------------------


def test_paa_question_is_copied_from_the_artifact(tmp_path):
    layout = make_workspace(tmp_path)
    _mutate(layout, lambda s: s["paa_questions"][0].update(question="what is  FIELD service software?"))
    assert _build(layout)["paa"]["questions"][0]["question"] == PAA_QUESTION


def test_duplicate_paa_questions_are_refused(tmp_path):
    layout = make_workspace(tmp_path)
    _mutate(layout, lambda s: s["paa_questions"].append(
        {"question": PAA_QUESTION.upper(), "priority": "must"}))
    _refused(layout, "duplicate PAA")


# ---- M4: anchor word boundaries -----------------------------------------------------------------


def test_anchor_keyword_needs_word_boundaries(tmp_path):
    layout = make_workspace(tmp_path)
    _mutate(layout, lambda s: s["links"][0].update(anchor="subfield service management softwares"))
    _refused(layout, "main keyword")


# ---- M6: hashes bind the parsed bytes ----------------------------------------------------------------


def test_artifact_changed_after_parsing_is_refused(tmp_path, monkeypatch):
    layout = make_workspace(tmp_path)
    real = bom_artifacts.canonical_artifact

    def drifted(path, *, workspace_root):
        binding = real(path, workspace_root=workspace_root)
        return {**binding, "sha256": "0" * 64} if path == layout.keyword_shortlist else binding

    monkeypatch.setattr(bom_artifacts, "canonical_artifact", drifted)
    _refused(layout, "changed while the BOM was built")


def test_context_changed_during_loading_is_refused(tmp_path):
    layout = make_workspace(tmp_path)

    class MutatingLoader(FakeLoader):
        def __call__(self, pack, receipt):
            write_json(receipt, {"receipt": "rewritten"})
            return super().__call__(pack, receipt)

    loader = MutatingLoader(ValidatedClaimSet([approved_claim(CLAIM_ID)]))
    _refused(layout, "changed while the BOM was built", loader=loader)


def test_spec_dict_is_not_mutated_by_build(tmp_path):
    layout = make_workspace(tmp_path)
    before = copy.deepcopy(json.loads(layout.bom_spec.read_text(encoding="utf-8")))
    _build(layout)
    assert json.loads(layout.bom_spec.read_text(encoding="utf-8")) == before
