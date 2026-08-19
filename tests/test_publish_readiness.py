from __future__ import annotations

import io
import hashlib
import json
from contextlib import ExitStack, redirect_stdout
from datetime import date
from unittest.mock import Mock, patch

import pytest

from data_sources.modules import publish_readiness
from data_sources.modules.blog_assembly_contract import canonical_artifact
from data_sources.modules.blog_assembly_stage_receipt import (
    build_stage_receipt,
    write_stage_receipt,
)
from data_sources.modules.url_validator import UrlValidationResult, UrlValidationSummary


CURRENT_DATE = date.today().isoformat()


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
    content_score = 91.2 if passed else 81.0
    aeo_score = 96 if passed else 88
    return {
        "passed": passed,
        "content_quality_score": content_score,
        "threshold": 85,
        "aeo_geo": {
            "score": aeo_score,
            "threshold": 90,
            "passed": passed,
        },
        "quality_gates": {
            "content_quality": {
                "score": content_score,
                "threshold": 85,
                "passed": content_score >= 85,
            },
            "seo_quality": {
                "score": 91 if passed else 84,
                "threshold": 90,
                "passed": passed,
                "critical_issues": [] if passed else ["SEO failed"],
                "critical_issue_count": 0 if passed else 1,
            },
            "aeo_geo": {
                "score": aeo_score,
                "threshold": 90,
                "passed": passed,
            },
        },
        "priority_fixes": [] if passed else [{"issue": "AEO failed"}],
    }

@pytest.fixture
def files(tmp_path):
    article = tmp_path / "draft.md"
    article.write_text(
        "---\nartifact_type: blog\nbrand: Simpro\ntitle: Draft\nobjective: Explain the workflow\naudience: Field service leaders\nregion: US\n"
        f"last_updated: {CURRENT_DATE}\n"
        "schema_notes:\n  - BlogPosting\n  - BreadcrumbList\n  - ImageObject for the featured image or logo\n  - Organization as publisher reference only, not a separate full schema block\n---\n# Draft\n\nBody copy.",
        encoding="utf-8",
    )
    sidecar = tmp_path / "validation-draft.md"
    sidecar.write_text(
        "Metric Proof Pack\nAuthor policy: not_provided\nNo named author available.\n",
        encoding="utf-8",
    )
    return article, sidecar


CURRENT_GATES = [
    ("context_binding", "context_binding_guard.validate_context_artifacts"),
    ("public_artifact", "public_artifact_guard.check_file"),
    ("ai_copy_linter", "ai_copy_linter.lint_file"),
    ("public_research_links", "public_research_link_guard.check_file"),
    ("metric_proof_pack", "metric_proof_pack_guard.check_file"),
    ("numeric_claim_source", "numeric_claim_source_guard.check_file"),
    ("faq_answer_quality", "faq_answer_quality_guard.check_file"),
    ("faq_proof", "faq_proof_guard.check_file"),
    ("paa_provenance", "paa_provenance_guard.check_file"),
    ("editorial_plan", "editorial_plan_guard.check_file"),
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
    research = article.parent / "research"
    research.mkdir(exist_ok=True)
    plan = research / "editorial-plan.json"
    plan.write_text(
        json.dumps({
            "meta": {
                "meta_title": "Field Service Scheduling Guide | Simpro",
                "meta_description": "A practical guide to field service scheduling decisions.",
                "primary_keyword": "field service scheduling",
                "secondary_keywords": ["dispatch capacity"],
            }
        }) + "\n",
        encoding="utf-8",
    )
    bom_path = research / "blog-assembly-bom-draft.json"
    visible_faq = "## Frequently asked questions" in article.read_text(encoding="utf-8")
    bom_path.write_text(
        json.dumps(
            {
                "schema": "simpro-blog-assembly-bom/v1",
                "lifecycle_state": "provisional",
                "workflow_mode": "new",
                "assembly_date": CURRENT_DATE,
                "author_policy": {
                    "status": "not_provided",
                    "name": "",
                    "frontmatter_author_required": False,
                    "schema_person_required": False,
                    "named_author_voice_allowed": False,
                },
                "schema_policy": {"visible_faq": visible_faq},
                "faq_policy": {
                    "status": "required" if visible_faq else "not_applicable",
                    "rationale": "No useful FAQ is planned." if not visible_faq else "Visible FAQs are planned.",
                },
                "paa_policy": {
                    "source_kind": "answersocrates",
                    "query": "test query",
                },
                "artifacts": {
                    "article": {
                        "path": article.name,
                        "sha256": hashlib.sha256(article.read_bytes()).hexdigest(),
                    },
                    "validation_sidecar": {
                        "path": sidecar.name,
                        "sha256": hashlib.sha256(sidecar.read_bytes()).hexdigest(),
                    },
                    "editorial_plan": {
                        "path": "research/editorial-plan.json",
                        "sha256": hashlib.sha256(plan.read_bytes()).hexdigest(),
                    },
                    "paa_artifact": None,
                    "content_brief": None,
                    "user_paa_csv": None,
                    "answersocrates_blocker": None,
                },
            }
        ),
        encoding="utf-8",
    )
    return bom_path


def _attach_normal_stage_chain(article, bom_path):
    """Attach a genuine closed pre-readiness chain to the lightweight BOM fixture."""
    article_hash = hashlib.sha256(article.read_bytes()).hexdigest()
    seed_hash = "0" * 64
    draft = build_stage_receipt(
        run_id="run-1",
        stage="draft",
        tool_name="manual_writer",
        tool_version="1.0.0",
        started_at="2026-08-11T14:00:00Z",
        completed_at="2026-08-11T14:01:00Z",
        mutation=True,
        input_artifact_hashes={"article": seed_hash},
        output_artifact_hashes={"article": article_hash},
    )
    scrub = build_stage_receipt(
        run_id="run-1",
        stage="scrub",
        tool_name="content_scrubber",
        tool_version="1.0.0",
        started_at="2026-08-11T14:02:00Z",
        completed_at="2026-08-11T14:03:00Z",
        mutation=False,
        input_artifact_hashes={"article": article_hash},
        output_artifact_hashes={"article": article_hash},
        evidence_hashes={"scrub_statistics": "1" * 64},
        previous_receipt_hash=draft["receipt_hash"],
    )
    binding = build_stage_receipt(
        run_id="run-1",
        stage="context_binding",
        tool_name="context_binding_generator",
        tool_version="1.0.0",
        started_at="2026-08-11T14:04:00Z",
        completed_at="2026-08-11T14:05:00Z",
        mutation=False,
        input_artifact_hashes={"article": article_hash},
        output_artifact_hashes={"article": article_hash},
        evidence_hashes={"context_binding": "2" * 64},
        previous_receipt_hash=scrub["receipt_hash"],
    )
    research = bom_path.parent
    receipt_paths = []
    for name, receipt in (
        ("stage-draft.json", draft),
        ("stage-scrub.json", scrub),
        ("stage-context-binding.json", binding),
    ):
        destination = research / name
        write_stage_receipt(destination, receipt)
        receipt_paths.append(destination)
    bom = json.loads(bom_path.read_text(encoding="utf-8"))
    bom["workflow"] = {"stage_receipts": [draft, scrub, binding]}
    bom["artifacts"]["stage_receipts"] = [
        canonical_artifact(path, workspace_root=article.parent)
        for path in receipt_paths
    ]
    bom_path.write_text(json.dumps(bom), encoding="utf-8")
    return bom_path


def run_with_patches(
    article,
    sidecar,
    *,
    overrides=None,
    score_passed=True,
    include_bom=True,
    mutate_during_score=False,
    **kwargs,
):
    overrides = overrides or {}
    if include_bom and "assembly_bom" not in kwargs:
        kwargs["assembly_bom"] = _write_non_connector_bom(article, sidecar)
    kwargs.setdefault("workspace_root", article.parent)
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
        if mutate_during_score:
            article.write_text(
                article.read_text(encoding="utf-8") + "\nChanged during scoring.\n",
                encoding="utf-8",
            )
        return score(score_passed)

    scorer.score.side_effect = score_content
    with ExitStack() as stack:
        for name, target in CURRENT_GATES:
            if name == "context_binding":
                def validate_context(*args, **call_kwargs):
                    order.append("context_binding")
                    return publish_readiness.context_binding_guard.ContextValidationResult(
                        required=True,
                        findings=tuple(overrides.get("context_binding", [])),
                    )

                mocks[name] = stack.enter_context(
                    patch(
                        f"data_sources.modules.publish_readiness.{target}",
                        side_effect=validate_context,
                    )
                )
                continue
            mocks[name] = stack.enter_context(
                patch(f"data_sources.modules.publish_readiness.{target}", side_effect=gate(name))
            )
        mocks["blog_assembly_bom"] = stack.enter_context(
            patch(
                "data_sources.modules.publish_readiness.blog_assembly_bom_guard.check_bom_file",
                side_effect=gate("blog_assembly_bom"),
            )
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
        "context_binding", "blog_assembly_bom", "public_artifact", "ai_copy_linter", "url_validator", "public_research_links",
        "metric_proof_pack", "numeric_claim_source",
        "paa_provenance", "editorial_plan", "source_support", "customer_proof_diversity",
        "review_story_identity", "early_artifact", "answer_withholding",
        "vault_brand_language", "named_feature_status",
        "fred_authority", "content_scorer",
    ]
    expected_gates = [
        "artifact_identity",
        "context_binding",
        "blog_assembly_bom",
        *expected_order[2:],
        "input_seal",
    ]
    assert result["passed"] is True
    assert order == expected_order
    assert [gate["name"] for gate in result["gates"]] == expected_gates
    assert result["schema"] == "simpro-publish-readiness-result/v1"
    assert result["phase"] == "preflight"
    assert result["verification_scope"] == "source_artifact"


def test_scorer_receives_guard_validated_bom_and_paa_policy(files):
    article, sidecar = files

    result, _, _, scorer = run_with_patches(article, sidecar)

    assert result["passed"] is True
    call = scorer.score.call_args
    assert call.kwargs["finalized_bom"]["lifecycle_state"] == "provisional"
    assert call.kwargs["assembly_date"] == CURRENT_DATE
    assert call.kwargs["metadata"]["faq_policy_status"] == "not_applicable"
    assert call.kwargs["metadata"]["primary_keyword"] == "field service scheduling"
    assert call.kwargs["metadata"]["secondary_keywords"] == ["dispatch capacity"]
    assert call.kwargs["paa_workflow_mode"] == "new"
    assert call.kwargs["paa_expected_query"] == "test query"
    assert call.kwargs["paa_expected_collection_date"] == CURRENT_DATE
    assert "prevalidated_gate_findings" not in call.kwargs
    readiness_context = call.kwargs["readiness_gate_context"]
    assert not isinstance(readiness_context, dict)


def test_readiness_uses_sealed_bom_assembly_date_instead_of_machine_date(files):
    article, sidecar = files
    sealed_date = "2026-08-10"
    article.write_text(
        article.read_text(encoding="utf-8").replace(
            f"last_updated: {CURRENT_DATE}",
            f"last_updated: {sealed_date}",
        ),
        encoding="utf-8",
    )
    bom_path = _write_non_connector_bom(article, sidecar)
    bom = json.loads(bom_path.read_text(encoding="utf-8"))
    bom["assembly_date"] = sealed_date
    bom_path.write_text(json.dumps(bom), encoding="utf-8")

    with patch(
        "data_sources.modules.blog_assembly_contract.current_utc_date",
        return_value=date.fromisoformat(sealed_date),
    ):
        result, _, _, scorer = run_with_patches(
            article,
            sidecar,
            assembly_bom=bom_path,
        )

    assert result["passed"] is True
    assert scorer.score.call_args.kwargs["assembly_date"] == sealed_date


def test_faq_specific_gates_are_skipped_when_bom_records_no_visible_faq(files):
    article, sidecar = files

    result, order, mocks, _ = run_with_patches(article, sidecar)

    assert result["passed"] is True
    assert "faq_answer_quality" not in order
    assert "faq_proof" not in order
    mocks["faq_answer_quality"].assert_not_called()
    mocks["faq_proof"].assert_not_called()


def test_mutation_during_readiness_invalidates_the_input_seal(files):
    article, sidecar = files

    result, _, _, _ = run_with_patches(
        article,
        sidecar,
        mutate_during_score=True,
    )

    assert result["passed"] is False
    assert result["input_seal"] == {"status": "failed"}
    seal = next(gate for gate in result["gates"] if gate["name"] == "input_seal")
    assert any(
        finding["rule_id"] == "readiness_inputs_changed_during_run"
        for finding in seal["findings"]
    )


def test_faq_specific_gates_run_when_visible_faq_is_bound(files):
    article, sidecar = files
    article.write_text(
        article.read_text(encoding="utf-8")
        + "\n## Frequently asked questions\n\n### What is scheduling?\n\nA direct answer.\n",
        encoding="utf-8",
    )

    result, order, mocks, _ = run_with_patches(article, sidecar)

    assert result["passed"] is True
    assert "faq_answer_quality" in order
    assert "faq_proof" in order
    mocks["faq_answer_quality"].assert_called_once()
    mocks["faq_proof"].assert_called_once()


def test_paa_guard_receives_bom_workflow_query_and_assembly_date(files):
    article, sidecar = files

    result, _, mocks, _ = run_with_patches(article, sidecar)

    assert result["passed"] is True
    kwargs = mocks["paa_provenance"].call_args.kwargs
    assert kwargs["workflow_mode"] == "new"
    assert kwargs["expected_query"] == "test query"
    assert kwargs["expected_collection_date"] == CURRENT_DATE
    assert "paa_artifact" in kwargs


def test_invalid_readiness_phase_is_rejected(files):
    article, sidecar = files

    with pytest.raises(ValueError, match="preflight or final"):
        publish_readiness.run_publish_readiness(
            article,
            proof_sidecar=sidecar,
            phase="draft",
        )


def test_preflight_requires_provisional_bom(files):
    article, sidecar = files

    result, _, mocks, _ = run_with_patches(article, sidecar, phase="preflight")

    assert result["passed"] is True
    assert (
        mocks["blog_assembly_bom"].call_args.kwargs["expected_lifecycle_state"]
        == "provisional"
    )


def test_final_readiness_requires_final_bom_and_attests_its_hash(files):
    article, sidecar = files

    result, _, mocks, _ = run_with_patches(article, sidecar, phase="final")

    assert result["passed"] is True
    assert result["phase"] == "final"
    assert result["verification_scope"] == "source_artifact"
    assert result["final_bom_sha256"] == result["input_hashes"]["assembly_bom"]["sha256"]
    assert mocks["blog_assembly_bom"].call_args.kwargs["expected_lifecycle_state"] == "final"


def test_readiness_snapshot_includes_every_bound_bom_artifact(files):
    article, sidecar = files
    bom_path = _write_non_connector_bom(article, sidecar)
    bom = json.loads(bom_path.read_text(encoding="utf-8"))
    optimizer = article.parent / "research" / "optimizer.json"
    optimizer.write_text('{"status": "completed"}\n', encoding="utf-8")
    stage_receipt = article.parent / "research" / "draft-receipt.json"
    stage_receipt.write_text('{"stage": "draft"}\n', encoding="utf-8")
    bom["artifacts"]["optimizer_outputs"] = [
        {
            "path": "research/optimizer.json",
            "sha256": hashlib.sha256(optimizer.read_bytes()).hexdigest(),
        }
    ]
    bom["artifacts"]["stage_receipts"] = [
        {
            "path": "research/draft-receipt.json",
            "sha256": hashlib.sha256(stage_receipt.read_bytes()).hexdigest(),
        }
    ]
    bom_path.write_text(json.dumps(bom), encoding="utf-8")

    result, _, _, _ = run_with_patches(
        article,
        sidecar,
        assembly_bom=bom_path,
    )

    snapshots = result["input_hashes"]
    assert snapshots["editorial_plan"] == bom["artifacts"]["editorial_plan"]
    assert snapshots["optimizer_outputs[0]"] == bom["artifacts"]["optimizer_outputs"][0]
    assert snapshots["stage_receipts[0]"] == bom["artifacts"]["stage_receipts"][0]


def test_bom_article_path_cannot_widen_the_trusted_workspace_root(
    files,
    monkeypatch,
):
    article, sidecar = files
    bom_path = _write_non_connector_bom(article, sidecar)
    bom = json.loads(bom_path.read_text(encoding="utf-8"))
    prefix = article.parent.name
    for row in bom["artifacts"].values():
        if isinstance(row, dict) and isinstance(row.get("path"), str):
            row["path"] = f"{prefix}/{row['path']}"
    bom_path.write_text(json.dumps(bom), encoding="utf-8")
    monkeypatch.chdir(article.parent)

    result, _, _, _ = run_with_patches(
        article,
        sidecar,
        assembly_bom=bom_path,
        workspace_root=None,
    )

    assert result["passed"] is False
    seal = next(gate for gate in result["gates"] if gate["name"] == "input_seal")
    assert any(
        finding["rule_id"] == "readiness_input_snapshot_invalid"
        for finding in seal["findings"]
    )


def test_blog_without_assembly_bom_fails_before_downstream_gates(files):
    article, sidecar = files

    result, order, mocks, scorer = run_with_patches(
        article,
        sidecar,
        include_bom=False,
    )

    gate_names = [gate["name"] for gate in result["gates"]]
    assert result["passed"] is False
    assert gate_names == ["artifact_identity", "context_binding", "blog_assembly_bom"]
    assert order == ["context_binding"]
    bom_gate = result["gates"][2]
    assert bom_gate["findings"][0]["rule_id"] == "bom_missing"
    mocks["public_artifact"].assert_not_called()
    scorer.score.assert_not_called()


def test_missing_explicit_artifact_kind_fails_before_context_binding(files):
    article, sidecar = files
    article.write_text(
        "---\nbrand: Simpro\ntitle: Draft\n---\n# Draft\n\nBody copy.",
        encoding="utf-8",
    )

    result, order, mocks, scorer = run_with_patches(
        article,
        sidecar,
        include_bom=False,
    )

    assert result["passed"] is False
    assert [gate["name"] for gate in result["gates"]] == ["artifact_identity"]
    assert result["gates"][0]["findings"][0]["rule_id"] == "artifact_kind_missing"
    assert order == []
    mocks["context_binding"].assert_not_called()
    scorer.score.assert_not_called()


def test_unsupported_artifact_kind_fails_before_context_binding(files):
    article, sidecar = files
    article.write_text(
        "---\nartifact_type: brochure\nbrand: Simpro\ntitle: Draft\n---\n# Draft\n",
        encoding="utf-8",
    )

    result, order, mocks, scorer = run_with_patches(
        article,
        sidecar,
        include_bom=False,
    )

    assert result["gates"][0]["findings"][0]["rule_id"] == "artifact_kind_unsupported"
    assert order == []
    mocks["context_binding"].assert_not_called()
    scorer.score.assert_not_called()


def test_incomplete_blog_identity_fails_before_context_binding(files):
    article, sidecar = files
    content = article.read_text(encoding="utf-8").replace(
        "objective: Explain the workflow\n",
        "",
    )
    article.write_text(content, encoding="utf-8")

    result, order, mocks, scorer = run_with_patches(
        article,
        sidecar,
        include_bom=False,
    )

    assert any(
        row["rule_id"] == "blog_identity_objective_missing"
        for row in result["gates"][0]["findings"]
    )
    assert order == []
    mocks["context_binding"].assert_not_called()
    scorer.score.assert_not_called()


@pytest.mark.parametrize("brand", ("AroFlo", "BigChange", "ClockShark"))
def test_owned_brand_article_skips_simpro_only_publish_gates(files, brand):
    article, sidecar = files
    article.write_text(
        f"---\nbrand: {brand}\nartifact_type: blog\ntitle: Job management\nobjective: Explain job management\naudience: Service leaders\nregion: US\n"
        f"last_updated: {CURRENT_DATE}\n"
        "schema_notes:\n  - BlogPosting\n  - BreadcrumbList\n  - ImageObject for the featured image or logo\n  - Organization as publisher reference only, not a separate full schema block\n---\n"
        f"# Job management\n\n{brand} helps teams coordinate field work.",
        encoding="utf-8",
    )

    result, order, mocks, _ = run_with_patches(article, sidecar)

    assert result["passed"] is True
    for gate_name in {"vault_brand_language", "named_feature_status", "fred_authority"}:
        assert gate_name not in order
        assert gate_name not in {gate["name"] for gate in result["gates"]}
        mocks[gate_name].assert_not_called()
    assert "customer_proof_diversity" in order

def test_cross_brand_simpro_comparison_runs_all_connector_evidence_gates(files):
    article, sidecar = files
    article.write_text(
        "---\nbrand: ClockShark\nartifact_type: blog\ntitle: Simpro comparison\nobjective: Compare workflows\naudience: Service leaders\nregion: US\n"
        f"last_updated: {CURRENT_DATE}\n"
        "schema_notes:\n  - BlogPosting\n  - BreadcrumbList\n  - ImageObject for the featured image or logo\n  - Organization as publisher reference only, not a separate full schema block\n---\n"
        "# Simpro comparison\n\nClockShark comparison copy mentions Simpro.",
        encoding="utf-8",
    )

    result, order, mocks, _ = run_with_patches(article, sidecar)

    assert result["passed"] is True
    assert "context_binding" in order
    assert "vault_brand_language" in order
    assert "named_feature_status" in order
    assert "fred_authority" in order
    mocks["fred_authority"].assert_called_once()


def test_cross_brand_simpro_comparison_fails_closed_without_context(files):
    article, sidecar = files
    article.write_text(
        "---\nbrand: AroFlo\nartifact_type: blog\ntitle: Simpro comparison\nobjective: Compare workflows\naudience: Service leaders\nregion: US\n"
        f"last_updated: {CURRENT_DATE}\n"
        "schema_notes:\n  - BlogPosting\n  - BreadcrumbList\n  - ImageObject for the featured image or logo\n  - Organization as publisher reference only, not a separate full schema block\n---\n"
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
        "---\nbrand: BigChange\nartifact_type: blog\ntitle: Industry view\nobjective: Explain an industry view\naudience: Service leaders\nregion: US\n"
        f"last_updated: {CURRENT_DATE}\n"
        "schema_notes:\n  - BlogPosting\n  - BreadcrumbList\n  - ImageObject for the featured image or logo\n  - Organization as publisher reference only, not a separate full schema block\n---\n"
        "# Industry view\n\nFred Voccola discusses field service operations at Simpro.",
        encoding="utf-8",
    )

    result, order, mocks, _ = run_with_patches(article, sidecar)

    assert result["passed"] is True
    assert "fred_authority" in order
    mocks["fred_authority"].assert_called_once()

def test_missing_context_binding_stops_before_other_gates_and_scoring(files):
    article, sidecar = files
    article.write_text(
        article.read_text(encoding="utf-8").replace("Body copy.", "Simpro body."),
        encoding="utf-8",
    )
    result, order, mocks, scorer = run_with_patches(
        article,
        sidecar,
        overrides={"context_binding": [finding("context_pack_missing")]},
    )

    assert result["passed"] is False
    assert order == ["context_binding"]
    assert [gate["name"] for gate in result["gates"]] == [
        "artifact_identity",
        "context_binding",
    ]
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
    assert "SEO score: 84/100 (release floor: 90, target: 95, FAIL)" in report
    assert "SEO critical issues: 1" in report
    assert "AEO/GEO score: 88/100 (threshold: 90, FAIL)" in report


def test_text_report_marks_release_pass_below_seo_target(files):
    article, sidecar = files
    result, _, _, _ = run_with_patches(article, sidecar, score_passed=True)
    result["scorecard"]["seo_quality"]["score"] = 92
    result["scorecard"]["seo_quality"]["threshold"] = 90
    result["scorecard"]["seo_quality"]["target"] = 95
    result["scorecard"]["seo_quality"]["passed"] = True
    result["scorecard"]["seo_quality"]["target_met"] = False
    result["scorecard"]["seo_quality"]["target_status"] = "below_target"

    report = publish_readiness.format_text_report(result)

    assert (
        "SEO score: 92/100 (release floor: 90, target: 95, PASS, BELOW TARGET)"
        in report
    )


@pytest.mark.parametrize(
    "gate_name,rule_id",
    [
        ("metric_proof_pack", "metric_source_unavailable"),
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
        if name in {
            "public_artifact",
            "ai_copy_linter",
            "context_binding",
            "editorial_plan",
            "faq_answer_quality",
            "faq_proof",
        }:
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
    bom_path = _write_non_connector_bom(article, sidecar)
    bom = json.loads(bom_path.read_text(encoding="utf-8"))
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
    assert gate_names[0:3] == ["artifact_identity", "context_binding", "blog_assembly_bom"]
    assert order[0] == "context_binding"
    assert "public_artifact" in order


def test_assembly_bom_mismatch_blocks_before_downstream_gates(files, tmp_path):
    article, sidecar = files
    request = tmp_path / "context-request.json"
    pack = tmp_path / "context-pack.json"
    receipt = tmp_path / "context-receipt.json"
    bom_path, bom = _write_assembly_bom(tmp_path, article, sidecar, request, pack, receipt)
    result, order, mocks, scorer = run_with_patches(
        article,
        sidecar,
        context_request=request,
        context_pack=pack,
        context_receipt=receipt,
        assembly_bom=bom_path,
        overrides={
            "blog_assembly_bom": [finding("bom_context_receipt_path_mismatch")]
        },
    )

    gate_names = [gate["name"] for gate in result["gates"]]
    bom_gate = next(gate for gate in result["gates"] if gate["name"] == "blog_assembly_bom")
    assert result["passed"] is False
    assert gate_names == ["artifact_identity", "context_binding", "blog_assembly_bom"]
    assert order == ["context_binding", "blog_assembly_bom"]
    assert any(
        finding["rule_id"] == "bom_context_receipt_path_mismatch"
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


def test_cli_atomically_persists_readiness_output(files, tmp_path):
    article, sidecar = files
    destination = tmp_path / "readiness.json"
    expected, _, _, _ = run_with_patches(article, sidecar)
    with patch(
        "data_sources.modules.publish_readiness.run_publish_readiness",
        return_value=expected,
    ):
        with redirect_stdout(io.StringIO()):
            exit_code = publish_readiness.main(
                [
                    str(article),
                    "--proof-sidecar",
                    str(sidecar),
                    "--phase",
                    "preflight",
                    "--assembly-bom",
                    str(expected["assembly_bom"]),
                        "--output",
                        str(destination),
                        "--workspace-root",
                        str(tmp_path),
                        "--json",
                ]
            )

    assert exit_code == 0
    assert json.loads(destination.read_text(encoding="utf-8")) == expected
    assert (tmp_path / "readiness-stage-receipt.json").is_file()
    assert not any(path.name.endswith(".tmp") for path in tmp_path.iterdir())


def test_persisting_a_fabricated_pass_with_no_gate_inventory_fails(files, tmp_path):
    article, _ = files
    result = {
        "schema": "simpro-publish-readiness-result/v1",
        "tool": {"name": "publish_readiness", "version": "1.0.0"},
        "phase": "preflight",
        "verification_scope": "source_artifact",
        "file": str(article),
        "proof_sidecar": None,
        "context_request": None,
        "context_pack": None,
        "context_receipt": None,
        "assembly_bom": None,
        "passed": True,
        "artifact_kind": "blog",
        "gates": [],
        "score": 100,
        "score_threshold": 85,
        "aeo_geo": {"score": 100, "threshold": 90, "passed": True},
        "scorecard": {
            "passed": True,
            "content_quality": {"score": 100, "threshold": 85, "passed": True},
            "seo_quality": {
                "score": 100,
                "threshold": 90,
                "passed": True,
                "critical_issue_count": 0,
            },
            "aeo_geo": {"score": 100, "threshold": 90, "passed": True},
        },
        "priority_fixes": [],
        "gate_inventory": [],
        "input_hashes": {
            "article": {
                "path": article.as_posix(),
                "sha256": hashlib.sha256(article.read_bytes()).hexdigest(),
            }
        },
        "input_seal": {"status": "verified"},
        "run_id": "fabricated",
        "started_at": "2026-08-11T14:00:00Z",
        "completed_at": "2026-08-11T14:01:00Z",
    }

    with pytest.raises(ValueError, match="expected gate inventory"):
        publish_readiness.write_readiness_result(
            tmp_path / "readiness.json",
            result,
            workspace_root=tmp_path,
        )

    assert not (tmp_path / "readiness.json").exists()
    assert not (tmp_path / "readiness-stage-receipt.json").exists()


def test_passed_readiness_validation_rejects_failed_scorecard_gate(files):
    article, sidecar = files
    result, _, _, _ = run_with_patches(article, sidecar)
    result["scorecard"]["seo_quality"] = {
        "score": 89,
        "threshold": 90,
        "passed": False,
        "critical_issue_count": 0,
        "critical_issues": [],
    }
    result["scorecard"]["passed"] = True

    with pytest.raises(ValueError, match="scorecard"):
        publish_readiness.validate_passed_readiness_result(
            result,
            workspace_root=article.parent,
        )

def test_persisting_a_structurally_complete_copied_pass_cannot_mint_attestation(
    files,
    tmp_path,
):
    article, sidecar = files
    executed, _, _, _ = run_with_patches(article, sidecar)
    forged = json.loads(json.dumps(executed))

    with pytest.raises(ValueError, match="actual publish-readiness execution"):
        publish_readiness.write_readiness_result(
            tmp_path / "forged-readiness.json",
            forged,
            workspace_root=tmp_path,
        )

    assert not (tmp_path / "forged-readiness.json").exists()
    assert not (tmp_path / "forged-readiness-stage-receipt.json").exists()


def test_receipt_build_failure_does_not_leave_passed_readiness_output(files, tmp_path):
    article, sidecar = files
    result, _, _, _ = run_with_patches(article, sidecar)
    destination = tmp_path / "readiness.json"

    with patch(
        "data_sources.modules.publish_readiness.build_stage_receipt",
        side_effect=ValueError("receipt failed"),
    ):
        with pytest.raises(ValueError, match="receipt failed"):
            publish_readiness.write_readiness_result(destination, result)

    assert not destination.exists()
    assert not (tmp_path / "readiness-stage-receipt.json").exists()


def test_receipt_write_failure_restores_previous_readiness_output(files, tmp_path):
    article, sidecar = files
    result, _, _, _ = run_with_patches(article, sidecar)
    destination = tmp_path / "readiness.json"
    destination.write_bytes(b"previous readiness bytes\n")

    with patch(
        "data_sources.modules.publish_readiness.write_stage_receipt",
        side_effect=OSError("receipt replace failed"),
    ):
        with pytest.raises(OSError, match="receipt replace failed"):
            publish_readiness.write_readiness_result(destination, result)

    assert destination.read_bytes() == b"previous readiness bytes\n"
    assert not (tmp_path / "readiness-stage-receipt.json").exists()
    assert not any(path.name.endswith(".tmp") for path in tmp_path.iterdir())


@pytest.mark.parametrize(
    ("mutation", "expected_rule"),
    (
        ("run_id", "stage_receipt_run_id_mismatch"),
        ("timestamp", "stage_receipt_timestamps_not_monotonic"),
        ("predecessor", "stage_receipt_previous_hash_mismatch"),
        ("article", "stage_receipt_article_chain_broken"),
    ),
)
def test_readiness_writer_rejects_a_receipt_that_breaks_the_bound_stage_chain(
    files,
    tmp_path,
    mutation,
    expected_rule,
):
    article, sidecar = files
    bom_path = _attach_normal_stage_chain(
        article,
        _write_non_connector_bom(article, sidecar),
    )
    if mutation == "predecessor":
        bom = json.loads(bom_path.read_text(encoding="utf-8"))
        scrub = bom["workflow"]["stage_receipts"][1]
        article_hash = hashlib.sha256(article.read_bytes()).hexdigest()
        binding = build_stage_receipt(
            run_id="run-1",
            stage="context_binding",
            tool_name="context_binding_generator",
            tool_version="1.0.0",
            started_at="2026-08-11T14:04:00Z",
            completed_at="2026-08-11T14:05:00Z",
            mutation=False,
            input_artifact_hashes={"article": article_hash},
            output_artifact_hashes={"article": article_hash},
            evidence_hashes={"context_binding": "2" * 64},
            previous_receipt_hash="f" * 64,
        )
        binding_path = bom_path.parent / "stage-context-binding.json"
        write_stage_receipt(binding_path, binding)
        bom["workflow"]["stage_receipts"][2] = binding
        bom["artifacts"]["stage_receipts"][2] = canonical_artifact(
            binding_path,
            workspace_root=article.parent,
        )
        bom_path.write_text(json.dumps(bom), encoding="utf-8")
        assert scrub["receipt_hash"] != binding["previous_receipt_hash"]
    elif mutation == "article":
        article.write_text(
            article.read_text(encoding="utf-8") + "\nFinal mutation.\n",
            encoding="utf-8",
        )
        bom = json.loads(bom_path.read_text(encoding="utf-8"))
        bom["artifacts"]["article"] = canonical_artifact(
            article,
            workspace_root=article.parent,
        )
        bom_path.write_text(json.dumps(bom), encoding="utf-8")

    result, _, _, _ = run_with_patches(
        article,
        sidecar,
        assembly_bom=bom_path,
    )
    if mutation == "run_id":
        result["run_id"] = "different-run"
    elif mutation == "timestamp":
        result["started_at"] = "2026-08-11T13:00:00Z"
        result["completed_at"] = "2026-08-11T13:01:00Z"

    destination = tmp_path / f"readiness-{mutation}.json"
    with pytest.raises(ValueError, match=expected_rule):
        publish_readiness.write_readiness_result(destination, result)

    assert not destination.exists()
    assert not publish_readiness.readiness_stage_receipt_path(destination).exists()


def test_failed_readiness_output_cannot_overwrite_article(files):
    article, _ = files
    original = article.read_bytes()
    result = {
        "passed": False,
        "file": str(article),
        "input_hashes": {},
    }

    with pytest.raises(ValueError, match="cannot overwrite input article"):
        publish_readiness.write_readiness_result(
            article,
            result,
            workspace_root=article.parent,
        )

    assert article.read_bytes() == original


def test_readiness_receipt_cannot_overwrite_output_or_bound_input(files, tmp_path):
    article, sidecar = files
    result, _, _, _ = run_with_patches(article, sidecar)
    destination = tmp_path / "readiness.json"

    with pytest.raises(ValueError, match="receipt cannot overwrite readiness output"):
        publish_readiness.write_readiness_result(
            destination,
            result,
            receipt_path=destination,
        )
    with pytest.raises(ValueError, match="cannot overwrite input article"):
        publish_readiness.write_readiness_result(
            destination,
            result,
            receipt_path=article,
        )

    assert not destination.exists()


@pytest.mark.parametrize("mutation", ("missing", "extra"))
def test_passed_readiness_requires_the_complete_exact_bom_input_inventory(
    files,
    tmp_path,
    mutation,
):
    article, sidecar = files
    result, _, _, _ = run_with_patches(article, sidecar)
    if mutation == "missing":
        del result["input_hashes"]["editorial_plan"]
    else:
        result["input_hashes"]["invented"] = {
            "path": article.name,
            "sha256": hashlib.sha256(article.read_bytes()).hexdigest(),
        }

    with pytest.raises(ValueError, match="complete exact readiness input inventory"):
        publish_readiness.write_readiness_result(
            tmp_path / "readiness.json",
            result,
        )

    assert not (tmp_path / "readiness.json").exists()
    assert not (tmp_path / "readiness-stage-receipt.json").exists()


def test_failed_readiness_cannot_overwrite_nested_bom_artifact(files):
    article, sidecar = files
    bom_path = _write_non_connector_bom(article, sidecar)
    bom = json.loads(bom_path.read_text(encoding="utf-8"))
    plan = article.parent / bom["artifacts"]["editorial_plan"]["path"]
    original = plan.read_bytes()
    result = {
        "passed": False,
        "file": str(article),
        "assembly_bom": str(bom_path),
        "input_hashes": {},
    }

    with pytest.raises(ValueError, match="cannot overwrite input editorial_plan"):
        publish_readiness.write_readiness_result(
            plan,
            result,
            workspace_root=article.parent,
        )

    assert plan.read_bytes() == original


def test_final_readiness_outputs_cannot_overwrite_historical_provisional_bom(
    files,
):
    article, sidecar = files
    provisional = _write_non_connector_bom(article, sidecar)
    final_bom = article.parent / "research" / "blog-assembly-bom-final.json"
    final_bom.write_text(
        json.dumps(
            {
                "artifacts": {},
                "preflight": {
                    "input_hashes": {
                        "assembly_bom": canonical_artifact(
                            provisional,
                            workspace_root=article.parent,
                        )
                    }
                },
            }
        ),
        encoding="utf-8",
    )
    result = {
        "passed": False,
        "file": str(article),
        "assembly_bom": str(final_bom),
        "input_hashes": {},
    }
    original = provisional.read_bytes()

    with pytest.raises(ValueError, match="historical_preflight.assembly_bom"):
        publish_readiness.write_readiness_result(
            provisional,
            result,
            workspace_root=article.parent,
        )

    assert provisional.read_bytes() == original


def test_persisting_a_pass_rechecks_attested_inputs(files, tmp_path):
    article, sidecar = files
    result, _, _, _ = run_with_patches(article, sidecar)
    article.write_text(
        article.read_text(encoding="utf-8") + "\nChanged after readiness.\n",
        encoding="utf-8",
    )
    destination = tmp_path / "readiness.json"

    with pytest.raises(ValueError, match="changed after gate execution"):
        publish_readiness.write_readiness_result(destination, result)

    assert not destination.exists()


def test_preflight_rejects_custom_receipt_path_and_bom_requires_output(files):
    article, sidecar = files
    with pytest.raises(SystemExit):
        publish_readiness.main(
            [
                str(article),
                "--proof-sidecar",
                str(sidecar),
                "--assembly-bom",
                "research/bom.json",
            ]
        )
    with pytest.raises(SystemExit):
        publish_readiness.main(
            [
                str(article),
                "--proof-sidecar",
                str(sidecar),
                "--phase",
                "preflight",
                "--output",
                "readiness.json",
                "--stage-receipt-output",
                "custom-receipt.json",
            ]
        )
    with pytest.raises(SystemExit):
        publish_readiness.main(
            [
                str(article),
                "--proof-sidecar",
                str(sidecar),
                "--phase",
                "final",
                "--stage-receipt-output",
                "custom-receipt.json",
            ]
        )


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
            workspace_root=tmp_path,
        )

    scorer_type.assert_called_once_with("ppc", "demo")
    assert result["passed"] is True
    assert result["content_quality_score"] == 82.0
    assert result["threshold"] == 75
    assert result["aeo_geo"]["not_applicable"] is True
    assert result["gate_name"] == "landing_page_scorer"
