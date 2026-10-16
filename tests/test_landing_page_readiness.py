"""Landing-page publish readiness: the WordPress page gate's gate stack and its refusals."""
from __future__ import annotations

from contextlib import ExitStack
from datetime import date
from unittest.mock import Mock, patch

import pytest

from data_sources.modules import context_binding_guard
from data_sources.modules.readiness.adapters import _score_content
from data_sources.modules.readiness.api import run_publish_readiness
from data_sources.modules.readiness.dependencies import ReadinessDependencies
from data_sources.modules.readiness.gate_registry import expected_landing_gate_inventory
from data_sources.modules.vault_claim_receipts import ValidatedClaimSet
from data_sources.modules.url_validator import UrlValidationResult, UrlValidationSummary

COMMON = "data_sources.modules.readiness.common"
LANDING_GATES = [
    ("public_artifact", "public_artifact_guard.check_content"),
    ("ai_copy_linter", "ai_copy_linter.lint_content"),
    ("public_research_links", "public_research_link_guard.check_content"),
    ("context_boundary", "context_boundary_guard.check_content"),
    ("metric_proof_pack", "metric_proof_pack_guard.check_content"),
    ("numeric_claim_source", "numeric_claim_source_guard.check_content"),
    ("competitive_shortlist", "competitive_shortlist_guard.check_content"),
    ("hindsight_boundary", "hindsight_boundary_guard.check_content"),
    ("source_support", "source_support_guard.check_content"),
    ("customer_proof_diversity", "customer_proof_diversity_guard.check_content"),
    ("review_story_identity", "review_story_identity_guard.check_content"),
    ("eeat_strength", "eeat_strength_guard.check_content"),
    ("early_artifact", "early_artifact_guard.check_content"),
    ("answer_withholding", "answer_withholding_guard.check_content"),
]
CONNECTOR_GATES = [
    ("vault_brand_language", "vault_brand_language_guard.check_content"),
    ("named_feature_status", "named_feature_status_guard.check_content"),
    ("fred_authority", "fred_authority_guard.check_content"),
]
NONCONNECTOR_INVENTORY = [
    "artifact_identity",
    "context_binding",
    "public_artifact",
    "ai_copy_linter",
    "url_validator",
    "public_research_links",
    "context_boundary",
    "metric_proof_pack",
    "numeric_claim_source",
    "faq_answer_quality",
    "faq_proof",
    "competitive_shortlist",
    "hindsight_boundary",
    "source_support",
    "source_quality",
    "customer_proof_diversity",
    "review_story_identity",
    "eeat_strength",
    "early_artifact",
    "answer_withholding",
    "landing_page_scorer",
]
RESULT_KEYS = [
    "aeo_geo", "artifact_kind", "completed_at", "context_pack", "context_receipt",
    "context_request", "file", "gate_inventory", "gates", "input_hashes", "input_seal", "passed",
    "phase", "priority_fixes", "proof_sidecar", "run_id", "schema", "score", "score_threshold",
    "scorecard", "started_at", "tool", "verification_scope",
]


def finding(rule_id="blocked", severity="error"):
    return {
        "rule_id": rule_id,
        "severity": severity,
        "line": 7,
        "column": 1,
        "message": "Blocked by test fixture.",
        "suggestion": "Fix the fixture.",
    }


@pytest.fixture
def page(tmp_path):
    landing = tmp_path / "landing-pages"
    landing.mkdir()
    path = landing / "demo-page.md"
    path.write_text(
        "---\nartifact_type: landing_page\nbrand: AroFlo\npage_type: ppc\nconversion_goal: demo\n"
        "meta_title: Job Management Demo | AroFlo\nmeta_description: Book a demo.\n"
        "primary_keyword: job management demo\n---\n# Book a demo\n\nBody copy.\n",
        encoding="utf-8",
    )
    return path


def run_landing(path, *, overrides=None, connector_required=False, mutate_during_score=False, **kwargs):
    """Run readiness with every article gate and the landing scorer stubbed; return result, gate call order, mocks."""
    overrides = overrides or {}
    order = []
    mocks = {}
    seen_content = {}

    def gate(name):
        def check(*args, **call_kwargs):
            order.append(name)
            seen_content[name] = args[0] if args else None
            return overrides.get(name, [])

        return check

    def validate_context(*args, **call_kwargs):
        order.append("context_binding")
        return context_binding_guard.ContextValidationResult(
            required=connector_required,
            findings=tuple(overrides.get("context_binding", [])),
        )

    def validate_urls(*args, **call_kwargs):
        order.append("url_validator")
        seen_content["url_validator"] = args[0] if args else None
        if "url_validator" in overrides:
            return overrides["url_validator"]
        return UrlValidationSummary(
            [UrlValidationResult(url="https://example.com", status="resolved", status_code=200, reason="HTTP 200")]
        )

    def score_page(*args, **call_kwargs):
        if mutate_during_score:
            path.write_text(path.read_text(encoding="utf-8") + "\nChanged during scoring.\n", encoding="utf-8")
        return {
            "overall_score": 82.0,
            "publishing_ready": True,
            "critical_issues": [],
            "warnings": [],
            "suggestions": [],
        }

    scorer = Mock()
    scorer.score.side_effect = score_page
    with ExitStack() as stack:
        mocks["context_binding"] = stack.enter_context(
            patch(f"{COMMON}.context_binding_guard.validate_context_payloads", side_effect=validate_context)
        )
        for name, target in LANDING_GATES + (CONNECTOR_GATES if connector_required else []):
            mocks[name] = stack.enter_context(patch(f"{COMMON}.{target}", side_effect=gate(name)))
        mocks["source_quality"] = stack.enter_context(
            patch(f"{COMMON}.source_quality_guard.check_content", side_effect=gate("source_quality"))
        )
        stack.enter_context(
            patch("data_sources.modules.readiness.pipeline_tail.validate_content_urls", side_effect=validate_urls)
        )
        mocks["scorer"] = stack.enter_context(
            patch("data_sources.modules.readiness.adapters.LandingPageScorer", return_value=scorer)
        )
        kwargs.setdefault("workspace_root", path.parents[1])
        result = run_publish_readiness(path, artifact_kind="landing_page", **kwargs)
    mocks["seen_content"] = seen_content
    return result, order, mocks


def test_landing_page_runs_its_gates_and_passes(page):
    result, order, mocks = run_landing(page)

    assert result["passed"] is True
    assert result["artifact_kind"] == "landing_page"
    assert order[0] == "context_binding"
    assert {name for name, _ in LANDING_GATES} | {"source_quality"} <= set(order)
    assert "url_validator" in order
    assert result["gates"][-1]["name"] == "landing_page_scorer"
    mocks["scorer"].assert_called_once_with("ppc", "demo")


def test_every_content_gate_reads_the_captured_page_text(page):
    page_text = page.read_bytes().decode("utf-8")

    _, order, mocks = run_landing(page)

    seen = mocks["seen_content"]
    assert set(order) - {"context_binding"} <= set(seen)
    assert {name: text for name, text in seen.items() if text != page_text} == {}
    assert mocks["source_quality"].call_args.kwargs["today"] == date.today()
    assert {
        key: mocks["eeat_strength"].call_args.kwargs[key]
        for key in ("editorial_plan", "customer_proof_evidence", "fred_authority_content")
    } == {"editorial_plan": None, "customer_proof_evidence": None, "fred_authority_content": None}


def test_landing_page_result_shape_and_gate_inventory_are_stable(page):
    result, _, _ = run_landing(page)

    assert sorted(result) == RESULT_KEYS
    assert result["gate_inventory"] == NONCONNECTOR_INVENTORY
    assert expected_landing_gate_inventory(connector_required=False) == NONCONNECTOR_INVENTORY
    assert [gate["name"] for gate in result["gates"]] == NONCONNECTOR_INVENTORY
    assert result["input_seal"] == {"status": "verified"}
    assert result["score"] == 82.0
    assert result["score_threshold"] == 75


def test_simpro_landing_page_runs_the_connector_gates_before_scoring(page):
    page.write_text(page.read_text(encoding="utf-8").replace("brand: AroFlo", "brand: Simpro"), encoding="utf-8")
    connector = Mock()
    loads = []

    def load_claims(*args, **kwargs):
        loads.append(kwargs.get("client"))
        return ValidatedClaimSet(receipt_revision="rev-1")

    result, order, _ = run_landing(
        page,
        connector_required=True,
        dependencies=ReadinessDependencies(
            connector_factory=lambda **_kwargs: connector,
            claim_set_loader=load_claims,
        ),
    )

    names = [gate["name"] for gate in result["gates"]]
    assert result["passed"] is True
    assert names[-4:] == ["vault_brand_language", "named_feature_status", "fred_authority", "landing_page_scorer"]
    assert {"vault_brand_language", "named_feature_status", "fred_authority"} <= set(order)
    assert loads == [connector]


def test_unresolved_url_fails_a_landing_page(page):
    unresolved = UrlValidationSummary(
        [UrlValidationResult(url="https://example.com/missing", status="unresolved", status_code=404, reason="HTTP 404")]
    )

    result, _, _ = run_landing(page, overrides={"url_validator": unresolved})

    assert result["passed"] is False
    assert next(row for row in result["gates"] if row["name"] == "url_validator")["errors"] == 1


def test_changing_the_page_during_readiness_fails_the_input_seal(page):
    result, _, _ = run_landing(page, mutate_during_score=True)

    assert result["input_seal"] == {"status": "failed"}


@pytest.mark.parametrize(
    "gate_name,rule_id",
    [
        ("metric_proof_pack", "metric_source_unavailable"),
        ("early_artifact", "early_artifact_missing"),
        ("answer_withholding", "placeholder_table_scaffold"),
    ],
)
def test_guard_errors_fail_a_landing_page(page, gate_name, rule_id):
    result, _, _ = run_landing(page, overrides={gate_name: [finding(rule_id)]})

    gate = next(row for row in result["gates"] if row["name"] == gate_name)
    assert result["passed"] is False
    assert gate["errors"] == 1


def test_warning_does_not_block_a_landing_page(page):
    result, _, _ = run_landing(page, overrides={"ai_copy_linter": [finding("modal_verb", severity="warning")]})

    lint = next(row for row in result["gates"] if row["name"] == "ai_copy_linter")
    assert result["passed"] is True
    assert lint["warnings"] == 1


def test_context_binding_failure_stops_before_article_gates(page):
    result, order, mocks = run_landing(page, overrides={"context_binding": [finding("context_request_missing")]})

    assert result["passed"] is False
    assert [gate["name"] for gate in result["gates"]][:2] == ["artifact_identity", "context_binding"]
    assert order == ["context_binding"]
    mocks["public_artifact"].assert_not_called()


def test_a_blog_article_is_refused_at_artifact_identity(page):
    page.write_text(
        "---\nartifact_type: blog\nbrand: AroFlo\ntitle: Draft\n---\n# Draft\n\nBody copy.\n",
        encoding="utf-8",
    )

    result, order, _ = run_landing(page)

    identity = result["gates"][0]
    assert result["passed"] is False
    assert identity["name"] == "artifact_identity"
    assert identity["findings"][0]["rule_id"] == "artifact_kind_unsupported"
    assert "production.release" in identity["findings"][0]["message"]
    assert identity["findings"][0]["suggestion"] == "Release blogs with /publish-readiness."
    assert order == []


def test_a_requested_blog_kind_is_refused_at_artifact_identity(page):
    page.write_text(
        "---\nartifact_type: blog\nbrand: AroFlo\ntitle: Draft\n---\n# Draft\n\nBody copy.\n",
        encoding="utf-8",
    )

    result = run_publish_readiness(page, artifact_kind="blog", workspace_root=page.parents[1])

    assert result["passed"] is False
    assert result["gates"][0]["findings"][0]["rule_id"] == "artifact_kind_unsupported"


def test_readiness_no_longer_accepts_an_assembly_bom(page):
    with pytest.raises(TypeError, match="assembly_bom"):
        run_publish_readiness(page, assembly_bom="research/bom.json", workspace_root=page.parents[1])


def test_missing_artifact_kind_fails_before_context_binding(page):
    page.write_text("---\nbrand: AroFlo\ntitle: Draft\n---\n# Draft\n\nBody copy.\n", encoding="utf-8")

    result, order, _ = run_landing(page)

    assert [gate["name"] for gate in result["gates"]] == ["artifact_identity", "input_seal"]
    assert result["gates"][0]["findings"][0]["rule_id"] == "artifact_kind_missing"
    assert result["score_threshold"] == 75
    assert result["aeo_geo"] == {"score": None, "threshold": None, "passed": True, "not_applicable": True}
    assert order == []


def test_unsupported_artifact_kind_fails_before_context_binding(page):
    page.write_text("---\nartifact_type: brochure\nbrand: AroFlo\n---\n# Draft\n", encoding="utf-8")

    result, order, _ = run_landing(page)

    assert result["gates"][0]["findings"][0]["rule_id"] == "artifact_kind_unsupported"
    assert order == []


def test_missing_direct_input_fails_before_any_gate(page):
    result, order, _ = run_landing(page, context_pack=page.parent / "missing-context-pack.json")

    assert result["passed"] is False
    assert [gate["name"] for gate in result["gates"]] == ["input_seal"]
    assert result["score_threshold"] == 75
    assert result["aeo_geo"] == {"score": None, "threshold": None, "passed": True, "not_applicable": True}
    assert order == []


def test_landing_page_uses_landing_scorer_contract(page):
    scorer = Mock()
    scorer.score.return_value = {
        "overall_score": 82.0,
        "publishing_ready": True,
        "critical_issues": [],
        "warnings": [],
        "suggestions": [],
    }

    with patch(
        "data_sources.modules.readiness.adapters.LandingPageScorer",
        return_value=scorer,
    ) as scorer_type:
        result = _score_content(page)

    scorer_type.assert_called_once_with("ppc", "demo")
    assert result["passed"] is True
    assert result["content_quality_score"] == 82.0
    assert result["threshold"] == 75
    assert result["aeo_geo"]["not_applicable"] is True
    assert result["gate_name"] == "landing_page_scorer"
