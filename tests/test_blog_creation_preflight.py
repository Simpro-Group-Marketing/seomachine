from __future__ import annotations

import hashlib
import json
from datetime import date
from pathlib import Path
from typing import Any

import pytest

from data_sources.modules import semrush_keyword_decision_guard
from data_sources.modules.blog_assembly_stage_receipt import (
    build_stage_receipt,
    write_stage_receipt,
)
from data_sources.modules.blog_creation_preflight import (
    build_preflight_report,
    main,
)
from data_sources.modules.nonvault_customer_proof_selector import (
    write_nonvault_selector_evidence,
)
from tests.nonvault_proof_fixture import write_nonvault_proof_inputs


def _write_json(path: Path, payload: object) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return path


def _article(path: Path, *, author: str | None = "Corey O'Donnell") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "---",
        "artifact_type: blog",
        "brand: Simpro",
        "title: Field service scheduling guide",
        "objective: Help operations leaders choose a scheduling workflow.",
        "audience: Field service operations leaders",
        "region: US",
        "last_updated: 2026-08-20",
        "primary_keyword: field service scheduling",
    ]
    if author:
        lines.append(f"author: {author}")
    lines.extend(
        [
            "schema_notes:",
            "  - BlogPosting",
            "  - BreadcrumbList",
            "  - ImageObject for the featured image or logo",
            "  - Organization as publisher reference only, not a separate full schema block",
            "---",
            "# Field service scheduling guide",
            "",
            "Field service scheduling guidance for dispatch capacity decisions.",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def _nonconnector_article(path: Path, brand: str, *, author: str | None = "Brian Paul") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "---",
        "artifact_type: blog",
        f"brand: {brand}",
        "title: Field service scheduling guide",
        "objective: Help operations leaders choose a scheduling workflow.",
        "audience: Field service operations leaders",
        "region: US",
        "last_updated: 2026-08-20",
        "primary_keyword: field service scheduling",
    ]
    if author:
        lines.append(f"author: {author}")
    lines.extend(["---", "# Field service scheduling guide", "", "Field service scheduling guidance for dispatch capacity decisions."])
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def _keyword_decision(
    path: Path,
    *,
    collection_date: str = "2026-08-20",
    execution_surface: str = "semrush_ui_chrome_main_browser",
) -> Path:
    surface = {"execution_surface": execution_surface}
    report_params = {
        "_keyword_research": {},
        "_get_report_schema": {"report": "phrase_these"},
        "phrase_these": {"phrase": "field service scheduling;dispatch capacity", "database": "us"},
        "phrase_related": {"phrase": "field service scheduling", "database": "us"},
        "phrase_questions": {"phrase": "field service scheduling", "database": "us"},
        "phrase_organic": {"phrase": "field service scheduling", "database": "us"},
        "phrase_this": {"phrase": "field service scheduling", "database": "us"},
    }
    payload = semrush_keyword_decision_guard.build_keyword_decision(
        brand="Simpro",
        market="US",
        database="us",
        collection_date=collection_date,
        source_boundary=semrush_keyword_decision_guard.SOURCE_BOUNDARY,
        seed_terms=["field service scheduling", "dispatch capacity"],
        connector_reports=[
            {"report": report, "parameters": {**params, **surface}, "status": "completed"}
            for report, params in report_params.items()
        ],
        candidate_metrics=[
            {"keyword": "field service scheduling", "volume": 720},
            {"keyword": "dispatch capacity", "volume": 90},
        ],
        serp_finalists=[
            {
                "keyword": "field service scheduling",
                "database": "us",
                "results": [
                    {"position": 1, "position_type": "organic", "domain": "example.com", "url": "https://example.com/field-service-scheduling", "triggered_serp_features": []}
                ],
            }
        ],
        question_candidates=[],
        related_candidates=[],
        selected_primary_keyword="field service scheduling",
        selected_secondary_keywords=["dispatch capacity"],
        rejected_keywords=[{"keyword": "employee scheduling software", "reason": "Different buyer."}],
        selection_rationale="Intent fit and SERP feasibility support the selected target.",
    )
    return _write_json(path, payload)


def _scrub_receipt(path: Path, article: Path, *, stage: str = "scrub") -> Path:
    article_hash = hashlib.sha256(article.read_bytes()).hexdigest()
    receipt = build_stage_receipt(
        run_id="run-preflight",
        stage=stage,
        tool_name="content_scrubber",
        tool_version="1.0.0",
        started_at="2026-08-20T12:00:00Z",
        completed_at="2026-08-20T12:00:01Z",
        input_artifact_hashes={"article": article_hash},
        output_artifact_hashes={"article": article_hash},
        evidence_hashes={"scrub_statistics": "1" * 64},
        previous_receipt_hash="",
        mutation=False,
    )
    write_stage_receipt(path, receipt)
    return path


def _selector_evidence(path: Path) -> Path:
    return _write_json(
        path,
        {
            "schema": "simpro-customer-proof-selector-evidence/v1",
            "inputs": {"roles": ["experience_story"]},
            "roles": [
                {
                    "role": "experience_story",
                    "candidate_ids": ["review-capterra-qbo-service-jobs-quotes-invoices"],
                }
            ],
        },
    )


def _no_fit_selector_evidence(path: Path) -> Path:
    reason = "No customer proof selected; public copy must omit customer proof."
    return _write_json(
        path,
        {
            "schema": "simpro-customer-proof-selector-evidence/v1",
            "selection_outcome": "no_fit_customer_proof",
            "inputs": {"roles": ["metric", "quote", "theme", "experience_story"], "allow_no_proof": True},
            "roles": [
                {"role": role, "candidate_ids": [], "claim_ids": [], "selected_id": "none", "no_fit_reason": reason}
                for role in ("metric", "quote", "theme", "experience_story")
            ],
        },
    )


def _context_artifacts(root: Path) -> tuple[Path, Path, Path]:
    return (
        _write_json(root / "context-request.json", {"task": "fixture"}),
        _write_json(root / "context-pack.json", {"schema": "simpro-product-context-pack/v2"}),
        _write_json(root / "context-receipt.json", {"schema": "simpro-context-receipt/v1"}),
    )


def _paths(tmp_path: Path, *, author: str | None = "Corey O'Donnell") -> dict[str, Any]:
    article = _article(tmp_path / "rewrites" / "article.md", author=author)
    sidecar = tmp_path / "research" / "validation.md"
    sidecar.parent.mkdir(parents=True, exist_ok=True)
    sidecar.write_text("Author policy: named_author\n", encoding="utf-8")
    request, pack, receipt = _context_artifacts(tmp_path / "research")
    scrub_receipt = _scrub_receipt(tmp_path / "research" / "scrub.json", article)
    return {
        "article": article,
        "proof_sidecar": sidecar,
        "context_request": request,
        "context_pack": pack,
        "context_receipt": receipt,
        "keyword_decision": _keyword_decision(tmp_path / "research" / "keyword.json"),
        "scrub_receipt": scrub_receipt,
        "customer_proof_evidence": _selector_evidence(tmp_path / "research" / "selector.json"),
        "editorial_plan": _write_json(tmp_path / "research" / "editorial-plan.json", {"schema": "fixture"}),
        "serp_evidence": _write_json(tmp_path / "research" / "serp-evidence.json", {"schema": "fixture"}),
        "stage_receipts": [scrub_receipt],
    }


def _drop_connector_artifacts(paths: dict[str, Any]) -> None:
    for key in ("context_request", "context_pack", "context_receipt", "customer_proof_evidence"):
        paths.pop(key)


def _rule_ids(report: dict[str, object]) -> set[str]:
    return {str(blocker["rule_id"]) for blocker in report["blockers"] if isinstance(blocker, dict)}


def test_preflight_blocks_stale_semrush_keyword_decision(tmp_path: Path):
    paths = _paths(tmp_path)
    paths["keyword_decision"] = _keyword_decision(
        tmp_path / "research" / "stale-keyword.json",
        collection_date="2026-08-19",
    )

    report = build_preflight_report(**paths, assembly_date="2026-08-20")

    assert report["ready_for_bom"] is False
    assert "semrush_keyword_decision_stale" in _rule_ids(report)
    assert any("Semrush" in command for command in report["next_required_commands"])


def test_preflight_blocks_semrush_api_fallback_surface(tmp_path: Path):
    paths = _paths(tmp_path)
    paths["keyword_decision"] = _keyword_decision(
        tmp_path / "research" / "api-keyword.json",
        execution_surface="semrush_api_connector",
    )

    report = build_preflight_report(**paths, assembly_date="2026-08-20")

    assert report["ready_for_bom"] is False
    assert "semrush_ui_surface_missing" in _rule_ids(report)
    assert "semrush_api_fallback_prohibited" in _rule_ids(report)


def test_preflight_accepts_legacy_authenticated_main_chrome_semrush_surface(tmp_path: Path):
    paths = _paths(tmp_path)
    paths["keyword_decision"] = _keyword_decision(
        tmp_path / "research" / "legacy-ui-keyword.json",
        execution_surface="authenticated_semrush_ui_in_main_chrome",
    )

    report = build_preflight_report(**paths, assembly_date="2026-08-20")

    assert "semrush_ui_surface_missing" not in _rule_ids(report)


def test_preflight_records_explicit_semrush_ui_refresh_blocker(tmp_path: Path):
    paths = _paths(tmp_path)
    paths["semrush_blocker"] = _write_json(
        tmp_path / "research" / "semrush-ui-blocker.json",
        {"rule_id": "blocked_semrush_ui_refresh", "error": "DOM read timed out"},
    )

    report = build_preflight_report(**paths, assembly_date="2026-08-20")

    assert report["ready_for_bom"] is False
    assert "blocked_semrush_ui_refresh" in _rule_ids(report)


def test_preflight_blocks_missing_scrub_receipt(tmp_path: Path):
    paths = _paths(tmp_path)
    paths["scrub_receipt"] = tmp_path / "research" / "missing-scrub.json"

    report = build_preflight_report(**paths, assembly_date="2026-08-20")

    assert report["ready_for_bom"] is False
    assert "scrub_receipt_missing" in _rule_ids(report)


def test_preflight_blocks_scrub_receipt_for_different_article(tmp_path: Path):
    paths = _paths(tmp_path)
    other_article = _article(tmp_path / "rewrites" / "other-article.md")
    other_article.write_text(
        other_article.read_text(encoding="utf-8") + "\nDifferent article body.\n",
        encoding="utf-8",
    )
    paths["scrub_receipt"] = _scrub_receipt(
        tmp_path / "research" / "other-scrub.json",
        other_article,
    )

    report = build_preflight_report(**paths, assembly_date="2026-08-20")

    assert report["ready_for_bom"] is False
    assert "scrub_receipt_article_hash_mismatch" in _rule_ids(report)


def test_preflight_blocks_missing_bom_dependencies(tmp_path: Path):
    paths = _paths(tmp_path)
    paths.pop("editorial_plan")
    paths.pop("serp_evidence")
    paths.pop("stage_receipts")

    report = build_preflight_report(**paths, assembly_date="2026-08-20")

    assert report["ready_for_bom"] is False
    assert "editorial_plan_missing" in _rule_ids(report)
    assert "serp_evidence_missing" in _rule_ids(report)
    assert "stage_receipts_missing" in _rule_ids(report)


@pytest.mark.parametrize("brand", ("AroFlo", "BigChange", "ClockShark"))
def test_preflight_allows_nonconnector_article_without_context_or_vault_artifacts(
    tmp_path: Path,
    brand: str,
):
    paths = _paths(tmp_path)
    paths["article"] = _nonconnector_article(paths["article"], brand)
    paths["scrub_receipt"] = _scrub_receipt(
        tmp_path / "research" / "scrub-nonconnector.json",
        paths["article"],
    )
    paths["stage_receipts"] = [paths["scrub_receipt"]]
    _drop_connector_artifacts(paths)

    report = build_preflight_report(**paths, assembly_date="2026-08-20")

    assert report["ready_for_bom"] is True, json.dumps(report["blockers"], indent=2)
    assert "context_request_missing" not in _rule_ids(report)
    assert "context_pack_missing" not in _rule_ids(report)
    assert "context_receipt_missing" not in _rule_ids(report)
    assert "customer_proof_selector_evidence_missing" not in _rule_ids(report)


@pytest.mark.parametrize(
    ("argument", "rule_id"),
    (
        ("customer_proof_evidence", "nonconnector_customer_proof_evidence_unexpected"),
        ("fred_authority_evidence", "nonconnector_fred_authority_evidence_unexpected"),
    ),
)
def test_preflight_rejects_vault_dependent_artifacts_for_nonconnector_article(
    tmp_path: Path,
    argument: str,
    rule_id: str,
):
    paths = _paths(tmp_path)
    paths["article"] = _nonconnector_article(paths["article"], "ClockShark")
    _drop_connector_artifacts(paths)
    paths[argument] = _write_json(tmp_path / "research" / f"{argument}.json", {"schema": "fixture"})

    report = build_preflight_report(**paths, assembly_date="2026-08-20")

    assert report["ready_for_bom"] is False
    assert rule_id in _rule_ids(report)


def test_preflight_accepts_nonconnector_nonvault_customer_proof_evidence(
    tmp_path: Path,
):
    paths = _paths(tmp_path)
    paths["article"] = _nonconnector_article(paths["article"], "ClockShark")
    paths["scrub_receipt"] = _scrub_receipt(
        tmp_path / "research" / "scrub-nonconnector-proof.json",
        paths["article"],
    )
    paths["stage_receipts"] = [paths["scrub_receipt"]]
    _drop_connector_artifacts(paths)
    index_path, ledger_path = write_nonvault_proof_inputs(tmp_path / "proof")
    evidence_path = tmp_path / "research" / "nonvault-proof-evidence.json"
    write_nonvault_selector_evidence(
        evidence_path,
        topic="employee time theft",
        brand="ClockShark",
        title="Field service scheduling guide",
        objective="Help operations leaders choose a scheduling workflow.",
        article_slug="field-service-scheduling",
        roles=("metric", "quote", "theme", "experience_story"),
        require_eeat_story=True,
        limit=10,
        reference_date=date(2026, 8, 28),
        selected_overrides={
            "theme": "clockshark-customer-story-mabrys-electrical-service",
            "experience_story": "clockshark-customer-story-mabrys-electrical-service",
        },
        rejected_overrides={},
        index_path=index_path,
        ledger_path=ledger_path,
    )
    paths["customer_proof_evidence"] = evidence_path

    report = build_preflight_report(**paths, assembly_date="2026-08-20")

    assert report["ready_for_bom"] is True, json.dumps(report["blockers"], indent=2)
    assert "nonconnector_customer_proof_evidence_unexpected" not in _rule_ids(report)


def test_preflight_rejects_context_artifacts_for_nonconnector_article(tmp_path: Path):
    paths = _paths(tmp_path)
    paths["article"] = _nonconnector_article(paths["article"], "BigChange", author=None)

    report = build_preflight_report(**paths, assembly_date="2026-08-20")

    assert "nonconnector_context_artifact_unexpected" in _rule_ids(report)


def test_preflight_accepts_no_fit_customer_proof_evidence_and_still_requires_run(tmp_path: Path):
    paths = _paths(tmp_path)
    missing_paths = dict(paths)
    missing_paths.pop("customer_proof_evidence")
    missing_report = build_preflight_report(**missing_paths, assembly_date="2026-08-20")
    assert (missing_report["ready_for_bom"], "customer_proof_selector_evidence_missing" in _rule_ids(missing_report)) == (False, True)

    paths["customer_proof_evidence"] = _no_fit_selector_evidence(
        tmp_path / "research" / "selector-no-fit.json"
    )
    report = build_preflight_report(**paths, assembly_date="2026-08-20")
    assert (report["ready_for_bom"], any(rule.startswith("customer_") for rule in _rule_ids(report))) == (True, False)


def test_preflight_blocks_commercial_no_fit_without_strength_decision(tmp_path: Path):
    paths = _paths(tmp_path, author=None)
    paths["proof_sidecar"].write_text("Author policy: not_provided\n", encoding="utf-8")
    paths["customer_proof_evidence"] = _no_fit_selector_evidence(
        tmp_path / "research" / "selector-no-fit.json"
    )
    paths["editorial_plan"] = _write_json(
        tmp_path / "research" / "editorial-plan-commercial.json",
        {
            "schema": "simpro-blog-editorial-plan/v1",
            "topic": "CRM for electricians",
            "meta": {
                "primary_keyword": "best crm for electricians",
                "title_options": ["7 Best CRM Platforms"],
            },
            "reader_contract": {
                "funnel_stage": "mofu",
                "decision_task_helped": "Compare CRM platforms and build a shortlist.",
            },
            "sections": [
                {
                    "type": "body_comparison",
                    "heading": "Best CRM Platforms",
                    "cta": "commercial_comparison",
                }
            ],
            "engagement_map": {"ctas": {"commercial_comparison": 1}},
            "serp_strategy": {"content_type": {"selected": "comparison list"}},
        },
    )

    missing_report = build_preflight_report(**paths, assembly_date="2026-08-20")
    assert missing_report["ready_for_bom"] is False
    assert "eeat_strength_decision_missing" in _rule_ids(missing_report)
    assert any("E-E-A-T Strength Decision" in command for command in missing_report["next_required_commands"])

    paths["proof_sidecar"].write_text(
        "\n".join(
            [
                "Author policy: not_provided",
                "",
                "## E-E-A-T Strength Decision",
                "- Applicability: required",
                "- Intent: commercial_investigation",
                "- Positive signals: [none]",
                "- Decision: proof_unavailable_safe_to_publish",
                "- Reason: Customer proof and Fred authority selectors returned no directly relevant approved evidence for this comparison.",
                "- Public copy boundary: public copy omits customer proof, named customer claims, review stories, exact quotes, testimonials, customer metrics, and unsupported SME claims.",
                "- Status: approved",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    fallback_report = build_preflight_report(**paths, assembly_date="2026-08-20")

    assert fallback_report["ready_for_bom"] is True
    assert fallback_report["blockers"] == []
    assert any(
        warning["rule_id"] == "eeat_strength_safe_but_weak"
        for warning in fallback_report["warnings"]
    )


def test_preflight_accepts_recorded_no_author_policy_without_expertise_path(tmp_path: Path):
    paths = _paths(tmp_path, author=None)
    paths["proof_sidecar"].write_text("Author policy: not_provided\n", encoding="utf-8")

    report = build_preflight_report(**paths, assembly_date="2026-08-20")

    assert report["ready_for_bom"] is True
    assert "expertise_path_missing" not in _rule_ids(report)
    assert report["required_human_inputs"] == []


def test_preflight_accepts_post_optimization_scrub_receipt(tmp_path: Path):
    paths = _paths(tmp_path)
    post_scrub = _scrub_receipt(
        tmp_path / "research" / "post-optimization-scrub.json",
        paths["article"],
        stage="post_optimization_scrub",
    )
    paths["scrub_receipt"] = post_scrub
    paths["stage_receipts"] = [post_scrub]

    report = build_preflight_report(**paths, assembly_date="2026-08-20")

    assert report["ready_for_bom"] is True
    assert "stage_receipt_stage_mismatch" not in _rule_ids(report)


def test_preflight_blocks_unrecorded_missing_author_policy(tmp_path: Path):
    paths = _paths(tmp_path, author=None)

    report = build_preflight_report(**paths, assembly_date="2026-08-20")

    assert report["ready_for_bom"] is False
    assert "no_author_policy_missing" in _rule_ids(report)
    assert "no-author policy, named author, or selected Fred authority evidence" in report["required_human_inputs"]


def test_preflight_accepts_complete_inputs_and_cli_writes_report(tmp_path: Path):
    paths = _paths(tmp_path)
    output = tmp_path / "research" / "preflight.json"

    exit_code = main(
        [
            str(paths["article"]),
            "--proof-sidecar",
            str(paths["proof_sidecar"]),
            "--context-request",
            str(paths["context_request"]),
            "--context-pack",
            str(paths["context_pack"]),
            "--context-receipt",
            str(paths["context_receipt"]),
            "--keyword-decision",
            str(paths["keyword_decision"]),
            "--scrub-receipt",
            str(paths["scrub_receipt"]),
            "--customer-proof-evidence",
            str(paths["customer_proof_evidence"]),
            "--editorial-plan",
            str(paths["editorial_plan"]),
            "--serp-evidence",
            str(paths["serp_evidence"]),
            "--stage-receipt",
            str(paths["stage_receipts"][0]),
            "--assembly-date",
            "2026-08-20",
            "--output",
            str(output),
        ]
    )
    report = json.loads(output.read_text(encoding="utf-8"))

    assert exit_code == 0
    assert report["ready_for_bom"] is True
    assert report["blockers"] == []
    assert set(report) == {
        "schema",
        "ready_for_bom",
        "blockers",
        "warnings",
        "next_required_commands",
        "required_human_inputs",
        "artifact_paths",
    }
