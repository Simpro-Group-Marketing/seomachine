from __future__ import annotations

import io
import json
from contextlib import ExitStack, redirect_stdout
from unittest.mock import Mock, patch

import pytest

from data_sources.modules.blog_assembly_bom import (
    build_blog_assembly_bom,
    build_blog_assembly_bom_from_files,
    write_blog_assembly_bom,
)
from data_sources.modules import publish_readiness
from data_sources.modules.url_validator import UrlValidationResult, UrlValidationSummary


def finding(rule_id="blocked", severity="error"):
    return {
        "rule_id": rule_id,
        "severity": severity,
        "line": 7,
        "column": 1,
        "message": "Blocked by test fixture.",
        "suggestion": "Fix the fixture.",
    }


def score(passed=True):
    return {
        "passed": passed,
        "content_quality_score": 91.2 if passed else 81.0,
        "threshold": 85,
        "aeo_geo": {
            "score": 96 if passed else 88,
            "threshold": 90,
            "passed": passed,
        },
        "priority_fixes": [] if passed else [{"issue": "AEO failed"}],
    }


@pytest.fixture
def files(tmp_path):
    article = tmp_path / "draft.md"
    article.write_text(
        "---\nartifact_type: blog\nbrand: Simpro\ntitle: Draft\nlast_updated: 2026-08-10\nschema_notes:\n  - BlogPosting\n  - BreadcrumbList\n  - ImageObject\n  - Organization publisher reference\n---\n# Draft\n\nBody copy.",
        encoding="utf-8",
    )
    sidecar = tmp_path / "validation-draft.md"
    sidecar.write_text(
        "Metric Proof Pack\nAuthor policy: not_provided\nNo named author available.\n",
        encoding="utf-8",
    )
    return article, sidecar


CURRENT_GATES = [
    ("context_binding", "context_binding_guard.check_file"),
    ("public_artifact", "public_artifact_guard.check_file"),
    ("ai_copy_linter", "ai_copy_linter.lint_file"),
    ("public_research_links", "public_research_link_guard.check_file"),
    ("metric_proof_pack", "metric_proof_pack_guard.check_file"),
    ("numeric_claim_source", "numeric_claim_source_guard.check_file"),
    ("faq_answer_quality", "faq_answer_quality_guard.check_file"),
    ("faq_proof", "faq_proof_guard.check_file"),
    ("paa_provenance", "paa_provenance_guard.check_file"),
    ("source_support", "source_support_guard.check_file"),
    ("customer_proof_diversity", "customer_proof_diversity_guard.check_file"),
    ("review_story_identity", "review_story_identity_guard.check_file"),
    ("early_artifact", "early_artifact_guard.check_file"),
    ("answer_withholding", "answer_withholding_guard.check_file"),
    ("vault_brand_language", "vault_brand_language_guard.check_file"),
    ("named_feature_status", "named_feature_status_guard.check_file"),
    ("fred_authority", "fred_authority_guard.check_file"),
]


def _write_non_connector_bom(article, sidecar):
    bom_path = article.parent / "blog-assembly-bom-draft.json"
    bom = build_blog_assembly_bom_from_files(
        article_path=article,
        validation_sidecar_path=sidecar,
        connector_binding_status="not_applicable",
        connector_not_applicable_reason="Unit test article has no connector-bound claims.",
        stage_names=["draft", "scrub", "context_binding", "publish_readiness"],
    )
    write_blog_assembly_bom(bom_path, bom)
    return bom_path


def run_with_patches(article, sidecar, *, overrides=None, score_passed=True, include_bom=True, **kwargs):
    overrides = overrides or {}
    if include_bom and "assembly_bom" not in kwargs:
        kwargs["assembly_bom"] = _write_non_connector_bom(article, sidecar)
    order = []
    mocks = {}

    def gate(name):
        def check(*args, **call_kwargs):
            order.append(name)
            return overrides.get(name, [])

        return check

    def validate_urls(*args, **call_kwargs):
        order.append("url_validator")
        if "url_validator" in overrides:
            return overrides["url_validator"]
        return UrlValidationSummary(
            [UrlValidationResult(url="https://example.com", status="resolved", status_code=200, reason="HTTP 200")]
        )

    scorer = Mock()

    def score_content(*args, **call_kwargs):
        order.append("content_scorer")
        return score(score_passed)

    scorer.score.side_effect = score_content
    with ExitStack() as stack:
        for name, target in CURRENT_GATES:
            mocks[name] = stack.enter_context(
                patch(f"data_sources.modules.publish_readiness.{target}", side_effect=gate(name))
            )
        stack.enter_context(
            patch("data_sources.modules.publish_readiness.validate_file_urls", side_effect=validate_urls)
        )
        mocks["scorer"] = stack.enter_context(
            patch("data_sources.modules.publish_readiness.ContentScorer", return_value=scorer)
        )
        result = publish_readiness.run_publish_readiness(
            article,
            proof_sidecar=sidecar,
            **kwargs,
        )
    return result, order, mocks, scorer


def test_all_gates_pass_in_required_order(files):
    article, sidecar = files
    result, order, _, _ = run_with_patches(article, sidecar)
    expected_order = [
        "context_binding", "public_artifact", "ai_copy_linter", "url_validator", "public_research_links",
        "metric_proof_pack", "numeric_claim_source", "faq_answer_quality", "faq_proof",
        "paa_provenance", "source_support", "customer_proof_diversity",
        "review_story_identity", "early_artifact", "answer_withholding",
        "vault_brand_language", "named_feature_status",
        "fred_authority", "content_scorer",
    ]
    expected_gates = [
        "context_binding",
        "blog_assembly_bom",
        *expected_order[1:],
    ]
    assert result["passed"] is True
    assert order == expected_order
    assert [gate["name"] for gate in result["gates"]] == expected_gates


def test_blog_without_assembly_bom_fails_before_downstream_gates(files):
    article, sidecar = files

    result, order, mocks, scorer = run_with_patches(
        article,
        sidecar,
        include_bom=False,
    )

    gate_names = [gate["name"] for gate in result["gates"]]
    assert result["passed"] is False
    assert gate_names == ["context_binding", "blog_assembly_bom"]
    assert order == ["context_binding"]
    bom_gate = result["gates"][1]
    assert bom_gate["findings"][0]["rule_id"] == "bom_missing"
    mocks["public_artifact"].assert_not_called()
    scorer.score.assert_not_called()


def test_non_simpro_article_skips_simpro_only_publish_gates(files):
    article, sidecar = files
    article.write_text(
        "---\nbrand: BigChange\nartifact_type: blog\ntitle: Job management\n---\n"
        "# Job management\n\nBigChange helps teams coordinate field work.",
        encoding="utf-8",
    )

    result, order, mocks, _ = run_with_patches(article, sidecar)

    assert result["passed"] is True
    for gate_name in {"vault_brand_language", "named_feature_status", "fred_authority"}:
        assert gate_name not in order
        assert gate_name not in {gate["name"] for gate in result["gates"]}
        mocks[gate_name].assert_not_called()
    assert "customer_proof_diversity" in order

def test_cross_brand_simpro_comparison_runs_context_gates_but_skips_fred(files):
    article, sidecar = files
    article.write_text(
        "---\nbrand: ClockShark\nartifact_type: blog\ntitle: Simpro comparison\n---\n"
        "# Simpro comparison\n\nClockShark comparison copy mentions Simpro.",
        encoding="utf-8",
    )

    result, order, mocks, _ = run_with_patches(article, sidecar)

    assert result["passed"] is True
    assert "context_binding" in order
    assert "vault_brand_language" in order
    assert "named_feature_status" in order
    assert "fred_authority" not in order
    mocks["fred_authority"].assert_not_called()


def test_cross_brand_simpro_comparison_fails_closed_without_context(files):
    article, sidecar = files
    article.write_text(
        "---\nbrand: AroFlo\nartifact_type: blog\ntitle: Simpro comparison\n---\n"
        "# Simpro comparison\n\nAroFlo comparison copy mentions Simpro.",
        encoding="utf-8",
    )

    result, order, mocks, scorer = run_with_patches(
        article,
        sidecar,
        overrides={"context_binding": [finding("context_request_missing")]},
    )

    assert result["passed"] is False
    assert order == ["context_binding"]
    mocks["vault_brand_language"].assert_not_called()
    mocks["named_feature_status"].assert_not_called()
    mocks["fred_authority"].assert_not_called()
    scorer.score.assert_not_called()


def test_cross_brand_fred_use_runs_fred_proof_gate(files):
    article, sidecar = files
    article.write_text(
        "---\nbrand: BigChange\nartifact_type: blog\ntitle: Industry view\n---\n"
        "# Industry view\n\nFred Voccola discusses field service operations at Simpro.",
        encoding="utf-8",
    )

    result, order, mocks, _ = run_with_patches(article, sidecar)

    assert result["passed"] is True
    assert "fred_authority" in order
    mocks["fred_authority"].assert_called_once()

def test_missing_context_binding_stops_before_other_gates_and_scoring(files):
    article, sidecar = files
    article.write_text("# Simpro draft\n\nBody.", encoding="utf-8")
    result, order, mocks, scorer = run_with_patches(
        article,
        sidecar,
        overrides={"context_binding": [finding("context_pack_missing")]},
    )

    assert result["passed"] is False
    assert order == ["context_binding"]
    assert [gate["name"] for gate in result["gates"]] == ["context_binding"]
    assert result["score"] is None
    assert result["aeo_geo"]["score"] is None
    scorer.score.assert_not_called()
    mocks["context_binding"].assert_called_once()
    for gate_name, _ in CURRENT_GATES:
        if gate_name != "context_binding":
            mocks[gate_name].assert_not_called()


def test_text_report_shows_100_point_scales_thresholds_and_gate_status(files):
    article, sidecar = files
    result, _, _, _ = run_with_patches(article, sidecar, score_passed=False)

    report = publish_readiness.format_text_report(result)

    assert "Content score: 81.0/100 (threshold: 85, FAIL)" in report
    assert "AEO/GEO score: 88/100 (threshold: 90, FAIL)" in report


@pytest.mark.parametrize(
    "gate_name,rule_id",
    [
        ("metric_proof_pack", "metric_source_unavailable"),
        ("faq_answer_quality", "faq_answer_generic_opener"),
        ("early_artifact", "early_artifact_missing"),
        ("answer_withholding", "placeholder_table_scaffold"),
        ("vault_brand_language", "vault_brand_language_alignment_missing"),
        ("named_feature_status", "named_feature_status_row_missing"),
        ("fred_authority", "fred_authority_selection_missing"),
    ],
)
def test_guard_errors_fail_runner(files, gate_name, rule_id):
    article, sidecar = files
    result, _, _, _ = run_with_patches(
        article, sidecar, overrides={gate_name: [finding(rule_id)]}
    )
    gate = next(row for row in result["gates"] if row["name"] == gate_name)
    assert result["passed"] is False
    assert gate["errors"] == 1


def test_unresolved_url_and_failed_score_block(files):
    article, sidecar = files
    unresolved = UrlValidationSummary(
        [UrlValidationResult(url="https://example.com/missing", status="unresolved", status_code=404, reason="HTTP 404")]
    )
    result, _, _, _ = run_with_patches(
        article,
        sidecar,
        overrides={"url_validator": unresolved},
        score_passed=False,
    )
    assert result["passed"] is False
    assert next(row for row in result["gates"] if row["name"] == "url_validator")["errors"] == 1
    assert result["score"] == 81.0


def test_warning_does_not_block(files):
    article, sidecar = files
    result, _, _, _ = run_with_patches(
        article,
        sidecar,
        overrides={"ai_copy_linter": [finding("modal_verb", severity="warning")]},
    )
    lint = next(row for row in result["gates"] if row["name"] == "ai_copy_linter")
    assert result["passed"] is True
    assert lint["warnings"] == 1


def test_sidecar_is_forwarded_to_all_proof_gates_and_scorer(files):
    article, sidecar = files
    result, _, mocks, scorer = run_with_patches(article, sidecar)
    assert result["passed"] is True
    for name, _ in CURRENT_GATES:
        if name in {"public_artifact", "ai_copy_linter", "context_binding"}:
            continue
        assert mocks[name].call_args.kwargs["proof_sidecar"] == str(sidecar)
    assert scorer.score.call_args.kwargs["proof_sidecar"] == str(sidecar)


def test_context_artifacts_are_forwarded_to_claim_sensitive_gates(files):
    article, sidecar = files
    request = article.parent / "request.json"
    pack = article.parent / "pack.json"
    receipt = article.parent / "receipt.json"
    result, _, mocks, _ = run_with_patches(
        article,
        sidecar,
        context_request=request,
        context_pack=pack,
        context_receipt=receipt,
        vault_root=article.parent,
    )

    assert result["passed"] is True
    context_kwargs = mocks["context_binding"].call_args.kwargs
    assert context_kwargs["context_request"] == str(request)
    assert context_kwargs["context_pack"] == str(pack)
    assert context_kwargs["context_receipt"] == str(receipt)
    assert context_kwargs["vault_root"] == article.parent
    for name in {
        "named_feature_status",
        "customer_proof_diversity",
        "fred_authority",
        "vault_brand_language",
    }:
        call_kwargs = mocks[name].call_args.kwargs
        assert call_kwargs["context_pack"] == str(pack)
        assert call_kwargs["context_receipt"] == str(receipt)
    assert mocks["named_feature_status"].call_args.kwargs["vault_root"] == article.parent
    assert mocks["fred_authority"].call_args.kwargs["vault_root"] == article.parent


def _write_assembly_bom(tmp_path, article, sidecar, request, pack, receipt):
    request_payload = {
        "task": "Assemble a Simpro blog.",
        "scope": {
            "artifact_type": "blog",
            "brand": "Simpro",
            "title": "AI field service guide",
            "objective": "Explain AI field service software boundaries.",
            "audience": "field service leaders",
            "region": "US",
            "intended_public_use_modes": ["public_paraphrase"],
        },
    }
    revisions = {
        "approval_policy_revision": "policy-1",
        "claim_registry_revision": "claims-1",
        "content_revision": "content-1",
        "contract_revision": "contract-1",
        "inventory_revision": "inventory-1",
        "manifest_revision": "manifest-1",
    }
    pack_payload = {
        "schema": "simpro-product-context-pack/v2",
        "revisions": revisions,
        "sections": {
            "Discovery Trace": {
                "selected_resource_ids": ["res-voice"],
                "selected_resource_purposes": {"res-voice": "guidance"},
            },
            "Approved Claim Evidence": [],
        },
    }
    receipt_payload = {
        "schema": "simpro-context-receipt/v1",
        "pack_sha256": "pack-hash",
        "receipt_sha256": "receipt-hash",
        "revisions": revisions,
        "claim_decisions": [],
    }
    request.write_text(json.dumps(request_payload), encoding="utf-8")
    pack.write_text(json.dumps(pack_payload), encoding="utf-8")
    receipt.write_text(json.dumps(receipt_payload), encoding="utf-8")
    bom = build_blog_assembly_bom_from_files(
        article_path=article,
        validation_sidecar_path=sidecar,
        context_request_path=request,
        context_pack_path=pack,
        context_receipt_path=receipt,
        topic_slug="ai-field-service-guide",
        stage_names=["draft", "scrub", "context_binding", "publish_readiness"],
    )
    bom_path = tmp_path / "blog-assembly-bom-ai-field-service-guide.json"
    write_blog_assembly_bom(bom_path, bom)
    return bom_path, bom


def test_assembly_bom_gate_runs_after_context_binding(files, tmp_path):
    article, sidecar = files
    request = tmp_path / "context-request.json"
    pack = tmp_path / "context-pack.json"
    receipt = tmp_path / "context-receipt.json"
    bom_path, _ = _write_assembly_bom(tmp_path, article, sidecar, request, pack, receipt)

    result, order, _, _ = run_with_patches(
        article,
        sidecar,
        context_request=request,
        context_pack=pack,
        context_receipt=receipt,
        assembly_bom=bom_path,
    )

    gate_names = [gate["name"] for gate in result["gates"]]
    assert result["passed"] is True
    assert gate_names[0:2] == ["context_binding", "blog_assembly_bom"]
    assert order[0] == "context_binding"
    assert "public_artifact" in order


def test_assembly_bom_mismatch_blocks_before_downstream_gates(files, tmp_path):
    article, sidecar = files
    request = tmp_path / "context-request.json"
    pack = tmp_path / "context-pack.json"
    receipt = tmp_path / "context-receipt.json"
    bom_path, bom = _write_assembly_bom(tmp_path, article, sidecar, request, pack, receipt)
    bom["files"]["context_receipt"] = str(tmp_path / "stale-context-receipt.json")
    write_blog_assembly_bom(bom_path, bom)

    result, order, mocks, scorer = run_with_patches(
        article,
        sidecar,
        context_request=request,
        context_pack=pack,
        context_receipt=receipt,
        assembly_bom=bom_path,
    )

    gate_names = [gate["name"] for gate in result["gates"]]
    bom_gate = next(gate for gate in result["gates"] if gate["name"] == "blog_assembly_bom")
    assert result["passed"] is False
    assert gate_names == ["context_binding", "blog_assembly_bom"]
    assert order == ["context_binding"]
    assert any(
        finding["rule_id"] == "bom_context_receipt_mismatch"
        for finding in bom_gate["findings"]
    )
    mocks["public_artifact"].assert_not_called()
    scorer.score.assert_not_called()


def test_json_output_has_stable_scoring_keys(files):
    article, sidecar = files
    output = io.StringIO()
    with patch("data_sources.modules.publish_readiness.run_publish_readiness") as runner:
        runner.return_value = {
            "file": str(article), "proof_sidecar": str(sidecar), "passed": True, "score": 91.2,
            "aeo_geo": {"score": 96}, "priority_fixes": [], "gates": [],
        }
        with redirect_stdout(output):
            exit_code = publish_readiness.main([str(article), "--proof-sidecar", str(sidecar), "--json"])
    payload = json.loads(output.getvalue())
    assert exit_code == 0
    assert {"file", "proof_sidecar", "passed", "score", "aeo_geo", "gates"} <= payload.keys()


def test_landing_page_uses_landing_scorer_contract(tmp_path):
    landing_dir = tmp_path / "landing-pages"
    landing_dir.mkdir()
    article = landing_dir / "demo-page.md"
    article.write_text(
        "---\nartifact_type: landing_page\npage_type: ppc\nconversion_goal: demo\n"
        "meta_title: Demo | Simpro\nmeta_description: Book a demo.\n"
        "primary_keyword: field service demo\n---\n# Book a demo\n\nBody.",
        encoding="utf-8",
    )
    scorer = Mock()
    scorer.score.return_value = {
        "overall_score": 82.0,
        "publishing_ready": True,
        "critical_issues": [],
        "warnings": [],
        "suggestions": [],
    }

    with patch(
        "data_sources.modules.publish_readiness.LandingPageScorer",
        return_value=scorer,
    ) as scorer_type:
        result = publish_readiness._score_content(
            article,
            proof_sidecar=None,
            artifact_kind="landing_page",
        )

    scorer_type.assert_called_once_with("ppc", "demo")
    assert result["passed"] is True
    assert result["content_quality_score"] == 82.0
    assert result["threshold"] == 75
    assert result["aeo_geo"]["not_applicable"] is True
    assert result["gate_name"] == "landing_page_scorer"
