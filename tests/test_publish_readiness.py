from __future__ import annotations

import io
import json
from contextlib import ExitStack, redirect_stdout
from unittest.mock import Mock, patch

import pytest

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
        "aeo_geo": {"score": 96 if passed else 88, "passed": passed},
        "priority_fixes": [] if passed else [{"issue": "AEO failed"}],
    }


@pytest.fixture
def files(tmp_path):
    article = tmp_path / "draft.md"
    article.write_text("# Draft\n\nBody copy.", encoding="utf-8")
    sidecar = tmp_path / "validation-draft.md"
    sidecar.write_text("Metric Proof Pack\n", encoding="utf-8")
    return article, sidecar


CURRENT_GATES = [
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
    ("source_routing", "source_routing_guard.check_file"),
    ("fred_authority", "fred_authority_guard.check_file"),
]


def run_with_patches(article, sidecar, *, overrides=None, score_passed=True, **kwargs):
    overrides = overrides or {}
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
        def context_check(*args, **call_kwargs):
            order.append("context_binding")
            return overrides.get("context_binding", [])

        mocks["context_binding"] = stack.enter_context(
            patch("data_sources.modules.publish_readiness.context_binding_guard.check_file", side_effect=context_check)
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
    expected = [
        "context_binding", "public_artifact", "ai_copy_linter", "url_validator", "public_research_links",
        "metric_proof_pack", "numeric_claim_source", "faq_answer_quality", "faq_proof",
        "paa_provenance", "source_support", "customer_proof_diversity",
        "review_story_identity", "early_artifact", "answer_withholding",
        "vault_brand_language", "named_feature_status", "source_routing",
        "fred_authority", "content_scorer",
    ]
    assert result["passed"] is True
    assert order == expected
    assert [gate["name"] for gate in result["gates"]] == expected


def test_simpro_context_gate_is_first_and_forwards_artifacts(files, tmp_path):
    article, sidecar = files
    article.write_text("# Simpro draft\n\nBody.", encoding="utf-8")
    request = tmp_path / "request.json"
    pack = tmp_path / "pack.json"
    receipt = tmp_path / "receipt.json"
    for path in (request, pack, receipt):
        path.write_text("{}", encoding="utf-8")
    result, order, mocks, _ = run_with_patches(
        article,
        sidecar,
        overrides={"context_binding": []},
        context_request=request,
        context_pack=pack,
        context_receipt=receipt,
        vault_root=tmp_path,
    )
    assert result["passed"] is True
    assert order[0] == "context_binding"
    assert result["gates"][0]["name"] == "context_binding"
    args = mocks["context_binding"].call_args.kwargs
    assert args["context_request"] == str(request)
    assert args["context_pack"] == str(pack)
    assert args["context_receipt"] == str(receipt)
    assert args["vault_root"] == tmp_path
    assert mocks["named_feature_status"].call_args.kwargs["context_pack"] == str(pack)
    assert mocks["fred_authority"].call_args.kwargs["context_receipt"] == str(receipt)
    assert mocks["customer_proof_diversity"].call_args.kwargs["vault_root"] == tmp_path
    assert mocks["customer_proof_diversity"].call_args.kwargs["context_pack"] == str(pack)
    assert mocks["customer_proof_diversity"].call_args.kwargs["context_receipt"] == str(receipt)
    assert mocks["review_story_identity"].call_args.kwargs["context_pack"] == str(pack)
    assert mocks["review_story_identity"].call_args.kwargs["context_receipt"] == str(receipt)


def test_simpro_context_artifacts_are_mandatory(files):
    article, sidecar = files
    article.write_text("# Simpro draft\n\nBody.", encoding="utf-8")
    result, _, _, _ = run_with_patches(
        article,
        sidecar,
        overrides={"context_binding": [finding("context_request_missing")]},
    )
    assert result["passed"] is False
    assert result["gates"][0]["name"] == "context_binding"
    assert "context_request_missing" in {row["rule_id"] for row in result["gates"][0]["findings"]}


def test_blog_context_is_mandatory_without_literal_simpro_token(files):
    article, sidecar = files
    article.write_text("# Scheduling software guide\n\nBody.\n", encoding="utf-8")

    result, order, _, scorer = run_with_patches(
        article,
        sidecar,
        overrides={"context_binding": [finding("context_request_missing")]},
    )

    assert result["passed"] is False
    assert order == ["context_binding"]
    scorer.score.assert_not_called()


def test_landing_hint_cannot_override_blog_frontmatter(files):
    article, sidecar = files
    article.write_text(
        "---\nartifact_type: blog\ntitle: Scheduling software guide\n---\n"
        "# Scheduling software guide\n\nBody.\n",
        encoding="utf-8",
    )

    result, order, _, scorer = run_with_patches(
        article,
        sidecar,
        artifact_kind="landing_page",
    )

    assert result["passed"] is False
    assert order == []
    assert result["gates"][0]["findings"][0]["rule_id"] == "context_artifact_kind_conflict"
    scorer.score.assert_not_called()


def test_landing_hint_cannot_override_blog_path(files, tmp_path):
    _, sidecar = files
    article = tmp_path / "drafts" / "guide.md"
    article.parent.mkdir()
    article.write_text("# Scheduling software guide\n\nBody.\n", encoding="utf-8")

    result, order, _, scorer = run_with_patches(
        article,
        sidecar,
        artifact_kind="landing_page",
    )

    assert result["passed"] is False
    assert order == []
    assert result["gates"][0]["findings"][0]["rule_id"] == "context_artifact_kind_conflict"
    scorer.score.assert_not_called()


def test_failed_context_gate_stops_before_all_other_gates_and_scoring(files):
    article, sidecar = files
    article.write_text("# Simpro draft\n\nBody.", encoding="utf-8")
    result, order, mocks, scorer = run_with_patches(
        article,
        sidecar,
        overrides={"context_binding": [finding("context_pack_stale")]},
        artifact_kind="blog",
    )

    assert result["passed"] is False
    assert order == ["context_binding"]
    assert result["score"] is None
    scorer.score.assert_not_called()
    for gate_name, _ in CURRENT_GATES:
        mocks[gate_name].assert_not_called()


def test_landing_hint_without_positive_evidence_defaults_to_blog_and_conflicts(files):
    article, sidecar = files
    article.write_text("# Simpro service page\n\nBody.", encoding="utf-8")
    result, order, _, scorer = run_with_patches(
        article,
        sidecar,
        artifact_kind="landing_page",
    )

    assert result["passed"] is False
    assert result["artifact_kind"] == "blog"
    assert order == []
    assert result["gates"][0]["findings"][0]["rule_id"] == "context_artifact_kind_conflict"
    scorer.score.assert_not_called()


def test_landing_frontmatter_conflicts_with_requested_blog(files):
    article, sidecar = files
    article.write_text(
        "---\nartifact_type: landing_page\ntitle: Simpro service page\n---\n"
        "# Simpro service page\n\nBody.\n",
        encoding="utf-8",
    )

    result, order, _, scorer = run_with_patches(article, sidecar, artifact_kind="blog")

    assert result["passed"] is False
    assert result["artifact_kind"] == "landing_page"
    assert order == []
    assert result["gates"][0]["findings"][0]["rule_id"] == "context_artifact_kind_conflict"
    scorer.score.assert_not_called()


@pytest.mark.parametrize(
    ("relative_path", "frontmatter"),
    [
        ("landing-pages/service.md", ""),
        ("service.md", "artifact_type: landing_page\n"),
        ("service.md", "workflow: landing_page\n"),
    ],
)
def test_positive_landing_evidence_allows_landing_workflow(
    files, tmp_path, relative_path, frontmatter
):
    _, sidecar = files
    article = tmp_path / relative_path
    article.parent.mkdir(parents=True, exist_ok=True)
    prefix = f"---\n{frontmatter}title: Simpro service page\n---\n" if frontmatter else ""
    article.write_text(f"{prefix}# Simpro service page\n\nBody.\n", encoding="utf-8")

    result, order, _, _ = run_with_patches(
        article,
        sidecar,
        artifact_kind="landing_page",
    )

    assert result["passed"] is True
    assert result["artifact_kind"] == "landing_page"
    assert "context_binding" not in order


def test_landing_path_conflicts_with_requested_blog(files, tmp_path):
    _, sidecar = files
    article = tmp_path / "landing-pages" / "service.md"
    article.parent.mkdir(parents=True)
    article.write_text("# Simpro service page\n\nBody.\n", encoding="utf-8")

    result, order, _, scorer = run_with_patches(article, sidecar, artifact_kind="blog")

    assert result["passed"] is False
    assert result["artifact_kind"] == "landing_page"
    assert order == []
    assert result["gates"][0]["findings"][0]["rule_id"] == "context_artifact_kind_conflict"
    scorer.score.assert_not_called()


def test_contradictory_frontmatter_kind_fields_return_stable_blocker(files):
    article, sidecar = files
    article.write_text(
        "---\nartifact_type: blog\nartifact_kind: landing_page\ntitle: Mixed\n---\n"
        "# Mixed\n\nBody.\n",
        encoding="utf-8",
    )

    result, order, _, scorer = run_with_patches(article, sidecar, artifact_kind="blog")

    assert result["passed"] is False
    assert order == []
    assert result["gates"][0]["findings"][0]["rule_id"] == "context_artifact_kind_conflict"
    scorer.score.assert_not_called()


@pytest.mark.parametrize(
    "frontmatter",
    [
        "artifact_type: blog\nartifact_type: landing_page\n",
        "artifact-type: blog\nartifact_type: landing_page\n",
    ],
)
def test_conflicting_duplicate_frontmatter_control_fields_block_classification(
    files, frontmatter
):
    article, sidecar = files
    article.write_text(
        f"---\n{frontmatter}title: Mixed\n---\n# Mixed\n\nBody.\n",
        encoding="utf-8",
    )

    result, order, _, scorer = run_with_patches(
        article,
        sidecar,
        artifact_kind="landing_page",
    )

    assert result["passed"] is False
    assert order == []
    assert result["gates"][0]["findings"][0]["rule_id"] == "context_artifact_kind_conflict"
    scorer.score.assert_not_called()


def test_non_conflicting_duplicate_frontmatter_control_fields_are_accepted(files):
    article, sidecar = files
    article.write_text(
        "---\nartifact_type: article\nartifact-type: blog\ntitle: Draft\n---\n"
        "# Draft\n\nBody.\n",
        encoding="utf-8",
    )

    result, order, _, _ = run_with_patches(article, sidecar, artifact_kind="post")

    assert result["passed"] is True
    assert result["artifact_kind"] == "blog"
    assert order[0] == "context_binding"


@pytest.mark.parametrize(
    ("article_text", "caller_kind"),
    [
        ("---\nartifact_type: brochure\n---\n# Draft\n\nBody.\n", "blog"),
        ("---\nartifact_kind: brochure\n---\n# Draft\n\nBody.\n", "blog"),
        ("# Draft\n\nBody.\n", "brochure"),
    ],
)
def test_unsupported_artifact_kinds_return_stable_blocker(
    files, article_text, caller_kind
):
    article, sidecar = files
    article.write_text(article_text, encoding="utf-8")

    result, order, _, scorer = run_with_patches(
        article,
        sidecar,
        artifact_kind=caller_kind,
    )

    assert result["passed"] is False
    assert order == []
    assert result["gates"][0]["findings"][0]["rule_id"] == "context_artifact_kind_invalid"
    scorer.score.assert_not_called()


def test_equivalent_independent_artifact_fields_are_accepted(files):
    article, sidecar = files
    article.write_text(
        "---\nartifact_type: article\nartifact_kind: blog\ntitle: Draft\n---\n"
        "# Draft\n\nBody.\n",
        encoding="utf-8",
    )

    result, order, _, _ = run_with_patches(article, sidecar, artifact_kind="post")

    assert result["passed"] is True
    assert result["artifact_kind"] == "blog"
    assert order[0] == "context_binding"


@pytest.mark.parametrize(
    "gate_name,rule_id",
    [
        ("metric_proof_pack", "metric_source_unavailable"),
        ("faq_answer_quality", "faq_answer_generic_opener"),
        ("early_artifact", "early_artifact_missing"),
        ("answer_withholding", "placeholder_table_scaffold"),
        ("vault_brand_language", "vault_brand_language_alignment_missing"),
        ("named_feature_status", "named_feature_status_row_missing"),
        ("source_routing", "source_routing_missing"),
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
        if name == "public_artifact" or name == "ai_copy_linter":
            continue
        assert mocks[name].call_args.kwargs["proof_sidecar"] == str(sidecar)
    assert scorer.score.call_args.kwargs["proof_sidecar"] == str(sidecar)


def test_json_output_has_stable_context_keys(files):
    article, sidecar = files
    output = io.StringIO()
    with patch("data_sources.modules.publish_readiness.run_publish_readiness") as runner:
        runner.return_value = {
            "file": str(article), "proof_sidecar": str(sidecar), "context_request": None,
            "context_pack": None, "context_receipt": None, "passed": True, "score": 91.2,
            "aeo_geo": {"score": 96}, "priority_fixes": [], "gates": [],
        }
        with redirect_stdout(output):
            exit_code = publish_readiness.main([str(article), "--proof-sidecar", str(sidecar), "--json"])
    payload = json.loads(output.getvalue())
    assert exit_code == 0
    assert {"context_request", "context_pack", "context_receipt"} <= payload.keys()
