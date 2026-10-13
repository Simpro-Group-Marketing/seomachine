"""Score gate: the existing scorers fed a proof view rendered only from the production BOM."""

from __future__ import annotations

import copy
import hashlib
import json
from datetime import date

import pytest
from data_sources.modules.production import scoring
from data_sources.modules.production.layout import Layout
from data_sources.modules.production.proof_view import render_proof_view
from data_sources.modules.public_http import PublicHttpTransport
from tests.production_scoring_support import (
    COMPETITOR_URL,
    ICC_URL,
    OWNED_URL,
    Q1,
    Q2,
    RUN_ID,
    TODAY,
    cite_in_faq,
    commit_source_registry,
    make_scoring_workspace,
    scorer_result,
    sha256,
    without_question,
    write_paa_capture,
)

EXTERNAL_URL = "https://example.org/dispatch-study"


@pytest.fixture(autouse=True)
def _offline(monkeypatch):
    monkeypatch.setenv("SEOMACHINE_TEST_CURRENT_UTC_DATE", TODAY)
    monkeypatch.setattr(
        PublicHttpTransport, "request_many",
        lambda _self, _method, urls, **_kwargs: pytest.fail(f"scoring fetched {list(urls)}"),
    )


@pytest.fixture
def workspace(tmp_path):
    return make_scoring_workspace(tmp_path)


def _failed_aeo_checks(result):
    return result["gates"]["aeo_geo"]["failed_checks"]


# ---- the three gates ---------------------------------------------------------------


def test_compliant_article_passes_all_three_gates(workspace):
    article, bom = workspace
    result = scoring.score_article(article, bom, workers=1)
    assert result["passed"] is True, result["gates"]
    assert result["content"] >= scoring.CONTENT_MIN
    assert result["seo"] >= scoring.SEO_MIN and result["seo_critical"] == 0
    assert result["aeo_geo"] >= scoring.AEO_MIN
    assert all(gate["passed"] for gate in result["gates"].values())


def test_faq_question_removed_from_bom_fails_aeo_on_paa_provenance(workspace):
    article, bom = workspace
    result = scoring.score_article(article, without_question(bom, Q2), workers=1)
    assert result["passed"] is False
    assert result["gates"]["aeo_geo"]["passed"] is False
    assert "paa_provenance" in _failed_aeo_checks(result)


def test_bom_without_proof_or_selector_evidence_fails_aeo_on_eeat_proof(workspace):
    article, bom = workspace
    bom = copy.deepcopy(bom)
    bom["proof"] = []
    del bom["customer_proof"]
    result = scoring.score_article(article, bom, workers=1)
    assert result["gates"]["aeo_geo"]["passed"] is False
    assert "eeat_proof" in _failed_aeo_checks(result)
    assert result["passed"] is False


def test_changed_bound_paa_artifact_is_refused(workspace):
    article, bom = workspace
    path = article.parents[1] / bom["paa"]["artifact"]["path"]
    path.write_text(path.read_text(encoding="utf-8") + " ", encoding="utf-8")
    with pytest.raises(ValueError, match="changed since the BOM was built"):
        scoring.score_article(article, bom, workers=1)


# ---- gate logic and return shape -------------------------------------------------------


def test_seo_critical_issue_fails_even_at_score_90():
    result = scoring.score_gates(scorer_result(seo=90, critical=["Missing H1"]))
    assert result["seo"] == 90.0 and result["seo_critical"] == 1
    assert result["gates"]["seo_quality"]["passed"] is False
    assert result["passed"] is False


@pytest.mark.parametrize(
    ("kwargs", "gate"),
    [({"content": 84.9}, "content_quality"), ({"seo": 89}, "seo_quality"), ({"aeo": 89}, "aeo_geo")],
)
def test_each_gate_fails_below_its_threshold(kwargs, gate):
    result = scoring.score_gates(scorer_result(**kwargs))
    assert result["gates"][gate]["passed"] is False and result["passed"] is False


def test_aeo_rater_fail_is_kept_even_at_score_90():
    result = scoring.score_gates(scorer_result(aeo=90, aeo_passed=False))
    assert result["gates"]["aeo_geo"]["passed"] is False and result["passed"] is False


def test_return_shape_and_gate_thresholds():
    result = scoring.score_gates(scorer_result())
    assert set(result) == {"content", "seo", "seo_critical", "aeo_geo", "priority_fixes", "passed", "gates"}
    assert (scoring.CONTENT_MIN, scoring.SEO_MIN, scoring.AEO_MIN) == (85, 90, 90)
    assert {name: gate["threshold"] for name, gate in result["gates"].items()} == {
        "content_quality": 85, "seo_quality": 90, "aeo_geo": 90,
    }
    assert all(isinstance(result[key], float) for key in ("content", "seo", "aeo_geo"))
    assert result["passed"] is True and result["priority_fixes"] == [{"dimension": "seo", "issue": "x"}]


# ---- processes ---------------------------------------------------------------------------


def test_one_worker_runs_in_process_and_matches_the_pool(workspace, monkeypatch):
    article, bom = workspace
    pooled = scoring.score_article(article, bom, workers=2)

    def no_pool(*_args, **_kwargs):
        raise AssertionError("workers=1 must not start a process pool")

    monkeypatch.setattr(scoring, "ProcessPoolExecutor", no_pool)
    assert scoring.score_article(article, bom, workers=1) == pooled


# ---- proof view ------------------------------------------------------------------------------


def test_proof_view_lists_only_bom_questions_and_binds_paa(workspace):
    _article, bom = workspace
    view = render_proof_view(without_question(bom, Q2))
    assert "## PAA/FAQ Provenance\n- Source: answersocrates\n" in view
    assert f"- Artifact: {bom['paa']['artifact']['path']}\n" in view
    assert f"  - {Q1}\n" in view and Q2 not in view


def test_proof_view_renders_the_four_faq_source_policy_lines(workspace):
    view = render_proof_view(workspace[1])
    assert (
        "## FAQ Source Policy\n"
        "- Allowed source classes: neutral, non_competing_expert, owned_product.\n"
        "- Competitor-owned FAQ sources: prohibited.\n"
        "- Status: aligned.\n"
    ) in view


def test_proof_view_mining_comes_from_selector_evidence(workspace):
    article, bom = workspace
    evidence = article.parents[1] / bom["customer_proof"]["evidence"]["path"]
    sha = hashlib.sha256(evidence.read_bytes()).hexdigest()
    story = next(r for r in bom["customer_proof"]["roles"] if r["role"] == "experience_story")
    selected = story["selected_candidate"]
    view = render_proof_view(bom)
    assert f"- Selector evidence: {bom['customer_proof']['evidence']['path']} | SHA-256: {sha}\n" in view
    assert (
        f"- Proof: {selected['proof_id']} | Customer: {selected['identity']} | URL: {selected['public_url']}\n"
    ) in view
    assert f"- Usable POV/story found: {selected['story']}\n" in view
    assert f"- Final use in copy: experience story: {selected['story']}\n" in view


def test_proof_view_renders_no_fit_decision_only_from_recorded_reason(workspace):
    _article, bom = workspace
    bom = copy.deepcopy(bom)
    reason = "No customer proof selected because none fits; public copy must omit customer proof."
    for role in bom["customer_proof"]["roles"]:
        role.update(selected_id="none", selected_candidate=None, no_fit_reason=reason)
    bom["proof"] = []
    view = render_proof_view(bom)
    assert f"## E-E-A-T Proof Map\n- First-hand evidence decision: Selected: [none] {reason}\n" in view
    assert "Selected Customer Proof Mining" not in view
    for role in bom["customer_proof"]["roles"]:
        role["no_fit_reason"] = ""
    assert "E-E-A-T Proof Map" not in render_proof_view(bom)


def test_faq_proof_map_row_classifies_an_owned_bom_fact_url(workspace):
    article, bom = workspace
    view = render_proof_view(bom, article=article.read_text(encoding="utf-8"), root=article.parents[1])
    assert (
        f"- FAQ: {Q2} | URL: {OWNED_URL} | Source class: owned_product | Competitor check: passed"
        " | Support: field service management software\n"
    ) in view
    assert f"- FAQ: {Q1} |" not in view


def test_faq_proof_map_omits_an_unclassifiable_url(workspace):
    article, bom = workspace
    bom = copy.deepcopy(bom)
    bom["facts"][0]["url"] = EXTERNAL_URL
    text = article.read_text(encoding="utf-8").replace(OWNED_URL, EXTERNAL_URL)
    view = render_proof_view(bom, article=text, root=article.parents[1])
    assert f"- Claim: {bom['facts'][0]['claim']} | URL: {EXTERNAL_URL}" in view
    assert "## FAQ Proof Map" not in view


def test_customer_proof_pack_and_source_map_rows_come_from_the_bom(workspace):
    _article, bom = workspace
    view = render_proof_view(bom)
    item, fact = bom["proof"][0], bom["facts"][0]
    assert (
        f"- Proof: {item['claim_id']} | Kind: experience_story | Customer: {item['customer']}"
        f" | URL: {item['url']} | Evidence: {item['text']}\n"
    ) in view
    assert (
        f"- Claim: {fact['claim']} | URL: {fact['url']} | Evidence: {fact['quote']}"
        f" | Verified at: {fact['verified_at']}\n"
    ) in view


def test_scoring_metadata_and_paa_expectations_come_from_the_bom(workspace):
    _article, bom = workspace
    metadata = scoring.scoring_metadata(bom)
    assert metadata["scorer"]["primary_keyword"] == "field service scheduling guide"
    assert metadata["scorer"]["faq_policy_status"] == "required"
    assert metadata["paa"] == {
        "workflow_mode": "new", "expected_query": "field service scheduling guide",
        "expected_collection_date": TODAY, "expected_run_id": RUN_ID,
    }
    assert json.loads(json.dumps(metadata)) == metadata


# ---- fix round 1 -----------------------------------------------------------------------------

REMEDY = "re-run the customer proof selector and rebuild the production BOM"
CONNECTOR_SCHEMA = "simpro-customer-proof-selector-evidence/v2"


def _connector_evidence(article, bom, reference_date):
    """Swap in connector selector evidence bound to the current ledger, dated reference_date."""
    root = article.parents[1]
    layout = Layout.for_article(article, root)
    ledger = root / "config" / "customer-proof-usage-ledger.json"
    payload = {"schema": CONNECTOR_SCHEMA, "selection_outcome": "customer_proof_candidates_available",
               "inputs": {"reference_date": reference_date},
               "artifacts": {"ledger": {"path": str(ledger), "sha256": sha256(ledger)}}, "roles": []}
    layout.customer_proof_evidence.write_text(json.dumps(payload), encoding="utf-8")
    changed = copy.deepcopy(bom)
    changed["customer_proof"] = {
        "evidence": {"path": f"research/{layout.customer_proof_evidence.name}",
                     "sha256": sha256(layout.customer_proof_evidence)},
        "schema": CONNECTOR_SCHEMA, "selection_outcome": "customer_proof_candidates_available", "roles": [],
    }
    return changed


def test_paa_artifact_dated_away_from_the_article_fails_paa_provenance(workspace):
    article, bom = workspace
    path = write_paa_capture(Layout.for_article(article, article.parents[1]), collection_date="2026-07-01")
    bom = copy.deepcopy(bom)
    bom["paa"]["artifact"]["sha256"] = sha256(path)
    bom["paa"]["collection_date"] = "2026-07-01"
    result = scoring.score_article(article, bom, workers=1)
    assert "paa_provenance" in _failed_aeo_checks(result)
    assert "paa_answersocrates_date_mismatch" in result["gates"]["aeo_geo"]["failed_rules"]


def test_stale_connector_selector_evidence_is_refused_with_the_remedy(workspace):
    article, bom = workspace
    bom = _connector_evidence(article, bom, "2026-08-10")
    with pytest.raises(scoring.ScoringPreflightError, match=REMEDY):
        scoring.score_article(article, bom, workers=1, today=lambda: date(2026, 8, 11))


def test_changed_usage_ledger_is_refused_with_the_remedy(workspace):
    article, bom = workspace
    ledger = article.parents[1] / "config" / "customer-proof-usage-ledger.json"
    ledger.write_text(ledger.read_text(encoding="utf-8") + " ", encoding="utf-8")
    with pytest.raises(scoring.ScoringPreflightError, match=REMEDY):
        scoring.score_article(article, bom, workers=1)
    assert issubclass(scoring.ScoringPreflightError, ValueError)


def test_fresh_selector_evidence_passes_the_preflight(workspace):
    article, bom = workspace
    root = article.parents[1]
    ledger = root / "config" / "customer-proof-usage-ledger.json"
    scoring.preflight_evidence(bom, root, today=lambda: date(2020, 1, 1), ledger_path=ledger)
    connector = _connector_evidence(article, bom, "2026-08-11")
    scoring.preflight_evidence(connector, root, today=lambda: date(2026, 8, 11), ledger_path=ledger)


def test_evidence_edited_after_the_build_is_refused(workspace):
    article, bom = workspace
    path = article.parents[1] / bom["customer_proof"]["evidence"]["path"]
    path.write_text(path.read_text(encoding="utf-8") + " ", encoding="utf-8")
    with pytest.raises(ValueError, match="changed since the BOM was built"):
        scoring.score_article(article, bom, workers=1)


def test_seo_critical_issue_fails_even_when_the_scorer_says_passed():
    result = scoring.score_gates(scorer_result(seo=95, critical=["Missing H1"], seo_passed=True))
    assert result["gates"]["seo_quality"]["passed"] is False and result["passed"] is False


def test_story_selection_missing_from_bom_proof_renders_no_mining(workspace):
    _article, bom = workspace
    bom = copy.deepcopy(bom)
    bom["proof"] = []
    story = next(r for r in bom["customer_proof"]["roles"] if r["role"] == "experience_story")
    assert story["selected_id"] != "none"
    assert "Selected Customer Proof Mining" not in render_proof_view(bom)


def test_registry_independent_authority_renders_neutral_and_passes_faq_proof(workspace):
    article, bom = workspace
    root = article.parents[1]
    commit_source_registry(root)
    bom = cite_in_faq(article, bom, ICC_URL, "ICC special inspections code chapter")
    view = render_proof_view(bom, article=article.read_text(encoding="utf-8"), root=root)
    assert f"- FAQ: {Q2} | URL: {ICC_URL} | Source class: neutral | Competitor check: passed" in view
    assert "faq_proof" not in _failed_aeo_checks(scoring.score_article(article, bom, workers=1))


def test_registry_competitor_row_is_still_rejected(workspace):
    article, bom = workspace
    root = article.parents[1]
    commit_source_registry(root)
    bom = cite_in_faq(article, bom, COMPETITOR_URL, "Knowify electrical contractor guide")
    view = render_proof_view(bom, article=article.read_text(encoding="utf-8"), root=root)
    assert f"| URL: {COMPETITOR_URL} | Source class: competitor | Competitor check: failed" in view
    result = scoring.score_article(article, bom, workers=1)
    assert "faq_answer_competitor_owned_source" in result["gates"]["aeo_geo"]["failed_rules"]


@pytest.mark.parametrize(
    ("source_class", "relationship", "expected"),
    [("primary_authority", "independent", "neutral"), ("independent_research", "independent", "neutral"),
     ("owned_product", "owned", "owned_product"), ("competitor", "competitor", "competitor"),
     ("primary_authority", "competitor", "primary_authority"), ("review_platform", "review_platform", "review_platform")],
)
def test_faq_source_class_maps_only_independent_authorities_to_neutral(source_class, relationship, expected):
    from data_sources.modules.production.proof_view import faq_source_class

    assert faq_source_class(source_class, relationship) == expected
