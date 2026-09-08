from __future__ import annotations

import hashlib
import os
import json
import subprocess
import sys
from datetime import date
from pathlib import Path

import pytest
from unittest.mock import patch

from data_sources.modules.blog_assembly_bom import (
    NON_CONNECTOR_REASON,
    _reject_bom_output_collision,
    _schema_policy,
    build_blog_assembly_bom_from_files,
    finalize_blog_assembly_bom,
    main as bom_main,
    write_blog_assembly_bom,
)
from data_sources.modules.context_binding_guard import ContextValidationResult
from data_sources.modules.editorial_plan_guard import build_serp_evidence
from data_sources.modules.paa_provenance_guard import build_answersocrates_artifact
from data_sources.modules.semrush_keyword_decision_guard import (
    SOURCE_BOUNDARY,
    build_keyword_decision,
)
from data_sources.modules.context_binding_generator import (
    generate_not_applicable_receipt,
)
from data_sources.modules.publishable_markdown import read_publishable_markdown
from data_sources.modules.publish_readiness import write_readiness_result
from data_sources.modules.blog_assembly_stage_receipt import (
    build_stage_receipt,
    write_stage_receipt,
)
from data_sources.modules.blog_assembly_contract import expected_blog_gate_inventory
from data_sources.modules import blog_assembly_contract
from data_sources.modules.blog_assembly_bom_guard import check_bom
from data_sources.modules.machine_review import (
    AGENT_ROSTER,
    build_machine_review,
    write_machine_review,
)
from data_sources.modules.nonvault_customer_proof_selector import (
    write_nonvault_selector_evidence,
)
from tests.nonvault_proof_fixture import write_nonvault_proof_inputs


NON_CONNECTOR_REASON_SHA256 = hashlib.sha256(
    NON_CONNECTOR_REASON.encode("utf-8")
).hexdigest()


@pytest.fixture(autouse=True)
def _freeze_workflow_clock(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(
        blog_assembly_contract,
        "current_utc_date",
        lambda: date(2026, 8, 11),
    )


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _json(path: Path, payload: object) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return path


def _fixture(
    tmp_path: Path,
    *,
    author: str | None = None,
    visible_faq: bool = False,
    brand: str = "BigChange",
) -> dict[str, Path]:
    research = tmp_path / "research"
    drafts = tmp_path / "drafts"
    research.mkdir()
    drafts.mkdir()
    schema = [
        "BlogPosting",
        "BreadcrumbList",
        "ImageObject for the featured image or logo",
        "Organization as publisher reference only, not a separate full schema block",
    ]
    if visible_faq:
        schema.extend(("FAQPage", "Question and Answer inside FAQPage"))
    if author:
        schema.append("Person as author")
    lines = [
        "---",
        "artifact_type: blog",
        f"brand: {brand}",
        "title: Scheduling guide",
        "objective: Help service leaders improve scheduling decisions",
        "audience: Field service leaders",
        "region: US",
        "last_updated: 2026-08-11",
    ]
    if author:
        lines.append(f"author: {author}")
    lines.append("schema_notes:")
    lines.extend(f"  - {entity}" for entity in schema)
    lines.extend(
        (
            "---",
            "# Scheduling guide",
            "",
            "A field service scheduling guide should balance capacity and dispatch constraints.",
            "",
            "[Explore field service management software](https://www.bigchange.com/field-service-management-software/).",
        )
    )
    if visible_faq:
        lines.extend(
            (
                "",
                "## Frequently asked questions",
                "",
                "### How should field service teams schedule work?",
                "",
                "Use current capacity and job constraints to assign work.",
            )
        )
    article = drafts / "scheduling-guide-2026-08-11.md"
    article.write_text("\n".join(lines) + "\n", encoding="utf-8")
    sidecar = research / "validation-scheduling-guide-2026-08-11.md"
    sidecar.write_text(
        f"Author policy: {'named_author' if author else 'no_author'}\n"
        + (f"Author: {author}\n" if author else "No named author available.\n"),
        encoding="utf-8",
    )
    question = "How should field service teams schedule work?"
    plan = {
        "schema": "simpro-blog-editorial-plan/v1",
        "topic": "field service scheduling guide",
        "date": "2026-08-11",
        "meta": {
            "title_options": ["Scheduling guide"],
            "meta_title": "Field Service Scheduling Guide",
            "meta_description": "A practical guide to capacity-aware field service scheduling.",
            "url_slug": "scheduling-guide",
            "primary_keyword": "field service scheduling guide",
            "secondary_keywords": ["capacity planning", "dispatch constraints"],
        },
        "keyword_decision": {
            "status": "resolved",
            "artifact_schema": "simpro-semrush-keyword-decision/v1",
            "source": "semrush_connector",
            "database": "us",
            "selected_primary_keyword": "field service scheduling guide",
            "selected_secondary_keywords": ["capacity planning", "dispatch constraints"],
            "selection_rationale": "Intent fit and SERP feasibility support the guide target.",
        },
        "total_word_target": 300,
        "sections": [
            {
                "section_number": 1,
                "type": "intro",
                "heading": "Scheduling guide",
                "word_target": 300,
                "strategic_angle": "Give a constraint-first scheduling decision.",
                "engagement_hook": None,
                "knowledge_gaps": [],
                "unique_data": [],
                "internal_links": [
                    "https://www.bigchange.com/field-service-management-software/"
                ],
                "cta": None,
                "next_action": None,
                "mini_story": False,
                "featured_snippet": False,
            }
        ],
        "engagement_map": {
            "mini_stories": [],
            "ctas": {},
            "featured_snippets": [],
            "next_actions": {},
            "cta_exception_reason": None,
        },
        "gap_mapping": {},
        "insight_mapping": {},
        "reader_contract": {
            "primary_reader": "Field service leaders",
            "sophistication_level": "experienced",
            "trigger_problem": "Scheduling friction",
            "existing_belief": "More dispatching effort fixes capacity",
            "decision_task_helped": "Choose a scheduling workflow",
            "distinctive_angle": "Constraint-first planning",
            "promised_payoff": "A practical scheduling decision",
            "funnel_stage": "tofu",
            "exclusions": [],
        },
        "serp_strategy": {
            "status": "resolved",
            "content_type": {
                "observed": "guide",
                "selected": "guide",
                "status": "matched_default",
            },
            "serp_features": {"featured snippet": "targeted"},
            "serp_structure": {"scheduling guide": "included"},
            "competitor_gaps": {},
            "exception_reasons": {
                "serp_features": {},
                "serp_structure": {},
                "competitor_gaps": {},
            },
        },
        "original_contributions": [
            {
                "description": "Constraint-first scheduling checklist",
                "final_section": "Scheduling guide",
                "visible_evidence": "A field service scheduling guide should balance capacity and dispatch constraints.",
            }
        ],
        "entity_map": {
            "primary": ["field service scheduling"],
            "supporting": ["capacity", "dispatch"],
        },
        "query_ownership": {
            "decision": "clear",
            "rationale": "No existing owned page serves this intent.",
        },
        "internal_link_plan": [
            {
                "target": "https://www.bigchange.com/field-service-management-software/",
                "role": "down_funnel",
                "rationale": "Provides an intent-appropriate product next step.",
            }
        ],
        "faq_policy": {
            "status": "required" if visible_faq else "not_applicable",
            "rationale": "No useful FAQ selected." if not visible_faq else "PAA fits intent.",
        },
        "paa_policy": {
            "source_kind": "answersocrates",
            "query": "field service scheduling guide",
            "selected_questions": [question] if visible_faq else [],
        },
    }
    if visible_faq:
        plan["total_word_target"] = 400
        plan["sections"].append(
            {
                "section_number": 2,
                "type": "faq",
                "heading": "Frequently asked questions",
                "word_target": 100,
                "strategic_angle": "Answer the selected PAA question directly.",
                "engagement_hook": None,
                "knowledge_gaps": [],
                "unique_data": [],
                "internal_links": [],
                "cta": None,
                "next_action": None,
                "mini_story": False,
                "featured_snippet": True,
            }
        )
        plan["engagement_map"]["featured_snippets"] = [2]
    editorial_plan = _json(research / "editorial-plan.json", plan)
    keyword_decision = _json(
        research / "semrush-keyword-decision-scheduling-guide-2026-08-11.json",
        build_keyword_decision(
            brand=brand,
            market="US",
            database="us",
            collection_date="2026-08-11",
            source_boundary=SOURCE_BOUNDARY,
            seed_terms=["field service scheduling guide", "capacity planning"],
            connector_reports=[
                {"report": "_keyword_research", "parameters": {}, "status": "completed"},
                {"report": "_get_report_schema", "parameters": {"report": "phrase_these"}, "status": "completed"},
                {
                    "report": "phrase_these",
                    "parameters": {
                        "phrase": "field service scheduling guide;capacity planning;dispatch constraints",
                        "database": "us",
                        "export_columns": "keyword,volume,cpc,competitive_density,results,trend,intent,keyword_difficulty",
                    },
                    "status": "completed",
                },
                {"report": "phrase_related", "parameters": {"phrase": "field service scheduling guide", "database": "us"}, "status": "completed"},
                {"report": "phrase_questions", "parameters": {"phrase": "field service scheduling guide", "database": "us"}, "status": "completed"},
                {"report": "phrase_organic", "parameters": {"phrase": "field service scheduling guide", "database": "us", "display_limit": 20}, "status": "completed"},
                {"report": "phrase_this", "parameters": {"phrase": "field service scheduling guide", "database": "us"}, "status": "completed"},
            ],
            candidate_metrics=[
                {
                    "keyword": "field service scheduling guide",
                    "volume": 720,
                    "keyword_difficulty": 32,
                    "cpc": 18.5,
                    "competitive_density": 0.12,
                    "results": 1000000,
                    "trend": [1, 1, 1],
                    "intent": "commercial",
                },
                {
                    "keyword": "capacity planning",
                    "volume": 260,
                    "keyword_difficulty": 29,
                    "cpc": 11.2,
                    "competitive_density": 0.08,
                    "results": 800000,
                    "trend": [1, 1, 1],
                    "intent": "informational",
                },
                {
                    "keyword": "dispatch constraints",
                    "volume": 90,
                    "keyword_difficulty": 21,
                    "cpc": 7.2,
                    "competitive_density": 0.03,
                    "results": 250000,
                    "trend": [1, 1, 1],
                    "intent": "informational",
                },
            ],
            serp_finalists=[
                {
                    "keyword": "field service scheduling guide",
                    "database": "us",
                    "results": [
                        {
                            "position": 1,
                            "position_type": "organic",
                            "domain": "example.com",
                            "url": "https://example.com/scheduling-guide",
                            "triggered_serp_features": ["featured snippet"],
                        }
                    ],
                }
            ],
            question_candidates=[
                {
                    "keyword": "how should field service teams schedule work",
                    "volume": 40,
                    "keyword_difficulty": 18,
                    "intent": "informational",
                }
            ],
            related_candidates=[
                {
                    "keyword": "field dispatch scheduling",
                    "volume": 110,
                    "keyword_difficulty": 28,
                    "relevance": 0.74,
                    "intent": "commercial",
                }
            ],
            selected_primary_keyword="field service scheduling guide",
            selected_secondary_keywords=["capacity planning", "dispatch constraints"],
            rejected_keywords=[
                {
                    "keyword": "employee scheduling software",
                    "reason": "Different buyer and page ownership lane.",
                }
            ],
            selection_rationale="Intent fit, page ownership, and SERP feasibility support the selected target.",
        ),
    )
    serp = _json(
        research / "serp-evidence.json",
        build_serp_evidence(
            query="field service scheduling guide",
            collected_at="2026-08-11T14:00:00Z",
            collector_name="serp_research",
            collector_version="1.0.0",
            run_id="serp-fixture-run",
            results=[{
                "position": 1,
                "url": "https://example.com/scheduling-guide",
                "title": "Field service scheduling guide",
                "result_type": "organic",
            }],
            content_types=["guide"],
            serp_features=["featured snippet"],
            must_have_sections=["scheduling guide"],
            competitor_gaps=[],
        ),
    )
    paa = research / "paa-questions.md"
    paa.write_text(
        json.dumps(
            build_answersocrates_artifact(
                query="field service scheduling guide",
                collection_date="2026-08-11",
                eligible_questions=(question,),
                run_id="answersocrates-fixture-run",
                started_at="2026-08-11T14:00:00Z",
                completed_at="2026-08-11T14:01:00Z",
            ),
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    draft_receipt = build_stage_receipt(
        run_id="run-1",
        stage="draft",
        tool_name="blog_writer",
        tool_version="1.0.0",
        started_at="2026-08-11T14:00:00Z",
        completed_at="2026-08-11T14:01:00Z",
        mutation=True,
        input_artifact_hashes={
            "article": "0" * 64,
            "editorial_plan": _sha256(editorial_plan),
        },
        output_artifact_hashes={"article": _sha256(article)},
        evidence_hashes={
            "serp_evidence": _sha256(serp),
            "keyword_decision": _sha256(keyword_decision),
        },
    )
    draft_path = research / "stage-draft.json"
    write_stage_receipt(draft_path, draft_receipt)
    scrub_receipt = build_stage_receipt(
        run_id="run-1",
        stage="scrub",
        tool_name="content_scrubber",
        tool_version="1.0.0",
        started_at="2026-08-11T14:02:00Z",
        completed_at="2026-08-11T14:03:00Z",
        mutation=False,
        input_artifact_hashes={"article": _sha256(article)},
        output_artifact_hashes={"article": _sha256(article)},
        evidence_hashes={"scrub_statistics": "f" * 64},
        previous_receipt_hash=draft_receipt["receipt_hash"],
    )
    scrub_path = research / "stage-scrub.json"
    write_stage_receipt(scrub_path, scrub_receipt)
    binding_receipt = build_stage_receipt(
        run_id="run-1",
        stage="context_binding",
        tool_name="context_binding_generator",
        tool_version="1.0.0",
        started_at="2026-08-11T14:04:00Z",
        completed_at="2026-08-11T14:05:00Z",
        mutation=False,
        input_artifact_hashes={"article": _sha256(article)},
        output_artifact_hashes={
            "article": _sha256(article),
            "validation_sidecar": _sha256(sidecar),
        },
        evidence_hashes={
            "context_binding": "e" * 64,
            "not_applicable_reason": NON_CONNECTOR_REASON_SHA256,
        },
        previous_receipt_hash=scrub_receipt["receipt_hash"],
    )
    binding_path = research / "stage-context-binding.json"
    write_stage_receipt(binding_path, binding_receipt)
    return {
        "article": article,
        "sidecar": sidecar,
        "editorial_plan": editorial_plan,
        "keyword_decision": keyword_decision,
        "serp": serp,
        "paa": paa,
        "stage_receipts": [draft_path, scrub_path, binding_path],
    }


def _machine_reviews(tmp_path: Path, paths: dict[str, Path]) -> tuple[Path, Path]:
    responses = [
        {"agent": agent, "status": "completed", "findings": []}
        for agent in AGENT_ROSTER
    ]
    reviews: list[Path] = []
    for phase in ("plan", "article"):
        review_path = tmp_path / "research" / f"machine-review-{phase}.json"
        write_machine_review(
            review_path,
            build_machine_review(
                run_id="run-1",
                workflow_stage="write",
                phase=phase,
                command="/write",
                repository_commit="abc123",
                editorial_plan_path=paths["editorial_plan"],
                article_path=paths["article"],
                proof_sidecar_path=paths["sidecar"],
                responses=responses,
                created_at="2026-08-11T14:06:00Z",
            ),
        )
        reviews.append(review_path)
    return reviews[0], reviews[1]


def _build(tmp_path: Path, paths: dict[str, Path], **overrides):
    kwargs = {
        "article_path": paths["article"],
        "validation_sidecar_path": paths["sidecar"],
        "editorial_plan_path": paths["editorial_plan"],
        "keyword_decision_path": paths["keyword_decision"],
        "serp_evidence_path": paths["serp"],
        "paa_artifact_path": paths["paa"],
        "stage_receipt_paths": paths["stage_receipts"],
        "workflow_mode": "new",
        "assembly_date": "2026-08-11",
        "workspace_root": tmp_path,
    }
    kwargs.update(overrides)
    if "plan_review_path" not in kwargs and "article_review_path" not in kwargs:
        review_paths = _machine_reviews(
            tmp_path,
            {
                "editorial_plan": Path(kwargs["editorial_plan_path"]),
                "article": Path(kwargs["article_path"]),
                "sidecar": Path(kwargs["validation_sidecar_path"]),
            },
        )
        kwargs["plan_review_path"], kwargs["article_review_path"] = review_paths
    context_paths = (
        kwargs.get("context_request_path"),
        kwargs.get("context_pack_path"),
        kwargs.get("context_receipt_path"),
    )
    if all(context_paths):
        scrub_receipt = json.loads(
            paths["stage_receipts"][1].read_text(encoding="utf-8")
        )
        binding_receipt = build_stage_receipt(
            run_id="run-1",
            stage="context_binding",
            tool_name="context_binding_generator",
            tool_version="1.0.0",
            started_at="2026-08-11T14:04:00Z",
            completed_at="2026-08-11T14:05:00Z",
            mutation=False,
            input_artifact_hashes={
                "article": _sha256(paths["article"]),
                "context_request": _sha256(Path(context_paths[0])),
                "context_pack": _sha256(Path(context_paths[1])),
                "context_receipt": _sha256(Path(context_paths[2])),
            },
            output_artifact_hashes={
                "article": _sha256(paths["article"]),
                "validation_sidecar": _sha256(paths["sidecar"]),
            },
            evidence_hashes={"context_binding": "e" * 64},
            previous_receipt_hash=scrub_receipt["receipt_hash"],
        )
        write_stage_receipt(paths["stage_receipts"][2], binding_receipt)
    return build_blog_assembly_bom_from_files(**kwargs)


def _refresh_normal_stage_receipts(paths: dict[str, Path]) -> None:
    draft_receipt = build_stage_receipt(
        run_id="run-1",
        stage="draft",
        tool_name="blog_writer",
        tool_version="1.0.0",
        started_at="2026-08-11T14:00:00Z",
        completed_at="2026-08-11T14:01:00Z",
        mutation=True,
        input_artifact_hashes={
            "article": "0" * 64,
            "editorial_plan": _sha256(paths["editorial_plan"]),
        },
        output_artifact_hashes={"article": _sha256(paths["article"])},
        evidence_hashes={
            "serp_evidence": _sha256(paths["serp"]),
            "keyword_decision": _sha256(paths["keyword_decision"]),
        },
    )
    write_stage_receipt(paths["stage_receipts"][0], draft_receipt)
    scrub_receipt = build_stage_receipt(
        run_id="run-1",
        stage="scrub",
        tool_name="content_scrubber",
        tool_version="1.0.0",
        started_at="2026-08-11T14:02:00Z",
        completed_at="2026-08-11T14:03:00Z",
        mutation=False,
        input_artifact_hashes={"article": _sha256(paths["article"])},
        output_artifact_hashes={"article": _sha256(paths["article"])},
        evidence_hashes={"scrub_statistics": "f" * 64},
        previous_receipt_hash=draft_receipt["receipt_hash"],
    )
    write_stage_receipt(paths["stage_receipts"][1], scrub_receipt)
    binding_receipt = build_stage_receipt(
        run_id="run-1",
        stage="context_binding",
        tool_name="context_binding_generator",
        tool_version="1.0.0",
        started_at="2026-08-11T14:04:00Z",
        completed_at="2026-08-11T14:05:00Z",
        mutation=False,
        input_artifact_hashes={"article": _sha256(paths["article"])},
        output_artifact_hashes={
            "article": _sha256(paths["article"]),
            "validation_sidecar": _sha256(paths["sidecar"]),
        },
        evidence_hashes={
            "context_binding": "e" * 64,
            "not_applicable_reason": NON_CONNECTOR_REASON_SHA256,
        },
        previous_receipt_hash=scrub_receipt["receipt_hash"],
    )
    write_stage_receipt(paths["stage_receipts"][2], binding_receipt)


def test_builder_snapshots_actual_files_as_workspace_relative_paths(tmp_path: Path):
    paths = _fixture(tmp_path)

    bom = _build(tmp_path, paths)

    assert bom["schema"] == "simpro-blog-assembly-bom/v2"
    assert set(bom["machine_reviews"]) == {"plan", "article"}
    assert bom["lifecycle_state"] == "provisional"
    assert bom["workflow_mode"] == "new"
    assert bom["artifacts"]["article"] == {
        "path": "drafts/scheduling-guide-2026-08-11.md",
        "sha256": _sha256(paths["article"]),
    }
    assert bom["artifacts"]["editorial_plan"]["sha256"] == _sha256(
        paths["editorial_plan"]
    )
    assert bom["artifacts"]["keyword_decision"] == {
        "path": "research/semrush-keyword-decision-scheduling-guide-2026-08-11.json",
        "sha256": _sha256(paths["keyword_decision"]),
    }
    assert bom["editorial_plan_summary"]["keyword_decision"]["selected_primary_keyword"] == (
        "field service scheduling guide"
    )
    assert bom["connector_binding"]["status"] == "not_applicable"
    assert bom["eeat_strength_policy"] == {
        "applicability": "not_applicable",
        "intent": "not_applicable",
        "intent_reasons": [],
        "positive_signals": [],
        "decision": "",
        "sidecar_status": "",
        "status": "not_applicable",
        "findings": [],
        "customer_proof_selector_evidence": "",
        "fred_authority_evidence": "",
    }
    assert bom["paa_policy"]["source_kind"] == "answersocrates"


def test_builder_requires_semrush_keyword_decision_artifact(tmp_path: Path):
    paths = _fixture(tmp_path)

    with pytest.raises(ValueError, match="keyword_decision_path"):
        _build(tmp_path, paths, keyword_decision_path=None)


def test_schemeless_official_simpro_host_forces_connector_bound_bom(
    tmp_path: Path,
):
    paths = _fixture(tmp_path)
    paths["article"].write_text(
        paths["article"].read_text(encoding="utf-8")
        + "\nSee helpguide.simprogroup.com/article/123 for product context.\n",
        encoding="utf-8",
    )
    _refresh_normal_stage_receipts(paths)

    with pytest.raises(ValueError, match="connector-bound blog requires"):
        _build(tmp_path, paths)


def test_schemeless_simpro_host_lookalike_remains_non_connector(
    tmp_path: Path,
):
    paths = _fixture(tmp_path)
    paths["article"].write_text(
        paths["article"].read_text(encoding="utf-8")
        + "\nSee simprogroup.com.evil.example/path for unrelated context.\n",
        encoding="utf-8",
    )
    _refresh_normal_stage_receipts(paths)

    bom = _build(tmp_path, paths)

    assert bom["connector_binding"]["status"] == "not_applicable"


@pytest.mark.parametrize("brand", ("AroFlo", "BigChange", "ClockShark"))
def test_builder_accepts_real_non_connector_context_binding_receipt(
    tmp_path: Path,
    brand: str,
):
    paths = _fixture(tmp_path, brand=brand)
    article_before = paths["article"].read_bytes()
    sidecar_before = paths["sidecar"].read_bytes()

    reason = (
        "Final article contains no Simpro brand, URL, or connector-sensitive "
        "language."
    )
    result = generate_not_applicable_receipt(
        paths["article"],
        paths["sidecar"],
        reason,
        stage_receipt_output=paths["stage_receipts"][2],
        previous_receipt=paths["stage_receipts"][1],
        run_id="run-1",
    )

    bom = _build(tmp_path, paths)

    assert bom["connector_binding"]["status"] == "not_applicable"
    assert bom["connector_binding"]["reason"] == reason
    assert bom["artifacts"]["context_request"] is None
    assert bom["artifacts"]["context_pack"] is None
    assert bom["artifacts"]["context_receipt"] is None
    assert bom["artifacts"]["customer_proof_selector_evidence"] is None
    assert bom["artifacts"]["fred_authority_evidence"] is None
    assert result["stage_receipt"]["evidence_hashes"][
        "not_applicable_reason"
    ] == hashlib.sha256(reason.encode("utf-8")).hexdigest()
    assert paths["article"].read_bytes() == article_before
    assert paths["sidecar"].read_bytes() == sidecar_before
    assert check_bom(
        bom,
        article_path=paths["article"],
        validation_sidecar_path=paths["sidecar"],
        workspace_root=tmp_path,
        expected_lifecycle_state="provisional",
    ) == []


@pytest.mark.parametrize("brand", ("AroFlo", "BigChange", "ClockShark"))
@pytest.mark.parametrize(
    ("argument", "filename"),
    (
        ("customer_proof_selector_evidence_path", "selector.json"),
        ("fred_authority_evidence_path", "fred.md"),
    ),
)
def test_non_connector_builder_rejects_vault_dependent_evidence(
    tmp_path: Path,
    brand: str,
    argument: str,
    filename: str,
):
    paths = _fixture(tmp_path, brand=brand)
    evidence = tmp_path / "research" / filename
    evidence.write_text("vault-dependent evidence\n", encoding="utf-8")

    with pytest.raises(ValueError, match="non-connector blog cannot include"):
        _build(tmp_path, paths, **{argument: evidence})


@pytest.mark.parametrize(
    "field",
    ("customer_proof_selector_evidence", "fred_authority_evidence"),
)
def test_non_connector_guard_rejects_vault_dependent_evidence(
    tmp_path: Path,
    field: str,
):
    paths = _fixture(tmp_path, brand="AroFlo")
    bom = _build(tmp_path, paths)
    evidence = tmp_path / "research" / f"{field}.txt"
    evidence.write_text("vault-dependent evidence\n", encoding="utf-8")
    bom["artifacts"][field] = {
        "path": evidence.relative_to(tmp_path).as_posix(),
        "sha256": _sha256(evidence),
    }

    findings = check_bom(
        bom,
        article_path=paths["article"],
        validation_sidecar_path=paths["sidecar"],
        workspace_root=tmp_path,
        expected_lifecycle_state="provisional",
    )

    assert any(
        finding["rule_id"] == "bom_non_connector_evidence_unexpected"
        for finding in findings
    )


def test_builder_records_nonvault_customer_proof_for_nonconnector_article(
    tmp_path: Path,
):
    paths = _fixture(tmp_path, brand="ClockShark")
    index_path, ledger_path = write_nonvault_proof_inputs(tmp_path / "proof")
    evidence_path = tmp_path / "research" / "nonvault-proof-evidence.json"
    write_nonvault_selector_evidence(
        evidence_path,
        topic="employee time theft",
        brand="ClockShark",
        title="Scheduling guide",
        objective="Help service leaders improve scheduling decisions",
        article_slug="scheduling-guide",
        roles=("metric", "quote", "theme", "experience_story"),
        require_eeat_story=True,
        limit=10,
        reference_date=date(2026, 8, 11),
        selected_overrides={
            "theme": "clockshark-customer-story-mabrys-electrical-service",
            "experience_story": "clockshark-customer-story-mabrys-electrical-service",
        },
        rejected_overrides={},
        index_path=index_path,
        ledger_path=ledger_path,
    )

    bom = _build(
        tmp_path,
        paths,
        customer_proof_selector_evidence_path=evidence_path,
    )

    assert bom["connector_binding"]["status"] == "not_applicable"
    assert (
        bom["artifacts"]["customer_proof_selector_evidence"]["sha256"]
        == _sha256(evidence_path)
    )
    assert bom["eeat_strength_policy"]["positive_signals"] == [
        "selected_customer_proof"
    ]
    findings = check_bom(
        bom,
        article_path=paths["article"],
        validation_sidecar_path=paths["sidecar"],
        workspace_root=tmp_path,
        expected_lifecycle_state="provisional",
    )
    assert not any(
        finding["rule_id"] == "bom_non_connector_evidence_unexpected"
        for finding in findings
    )


def test_builder_rejects_non_connector_receipt_bound_to_a_different_reason(
    tmp_path: Path,
):
    paths = _fixture(tmp_path)
    scrub = json.loads(paths["stage_receipts"][1].read_text(encoding="utf-8"))
    binding = build_stage_receipt(
        run_id="run-1",
        stage="context_binding",
        tool_name="context_binding_generator",
        tool_version="1.0.0",
        started_at="2026-08-11T14:04:00Z",
        completed_at="2026-08-11T14:05:00Z",
        mutation=False,
        input_artifact_hashes={"article": _sha256(paths["article"])},
        output_artifact_hashes={
            "article": _sha256(paths["article"]),
            "validation_sidecar": _sha256(paths["sidecar"]),
        },
        evidence_hashes={
            "context_binding": "e" * 64,
            "not_applicable_reason": hashlib.sha256(
                b"A different connector decision."
            ).hexdigest(),
        },
        previous_receipt_hash=scrub["receipt_hash"],
    )
    write_stage_receipt(paths["stage_receipts"][2], binding)

    with pytest.raises(ValueError, match="not-applicable reason"):
        _build(tmp_path, paths)


def test_context_binding_receipt_must_bind_the_sidecar_output(tmp_path: Path):
    paths = _fixture(tmp_path)
    scrub = json.loads(paths["stage_receipts"][1].read_text(encoding="utf-8"))
    binding = build_stage_receipt(
        run_id="run-1",
        stage="context_binding",
        tool_name="context_binding_generator",
        tool_version="1.0.0",
        started_at="2026-08-11T14:04:00Z",
        completed_at="2026-08-11T14:05:00Z",
        mutation=False,
        input_artifact_hashes={"article": _sha256(paths["article"])},
        output_artifact_hashes={"article": _sha256(paths["article"])},
        evidence_hashes={
            "context_binding": "e" * 64,
            "not_applicable_reason": NON_CONNECTOR_REASON_SHA256,
        },
        previous_receipt_hash=scrub["receipt_hash"],
    )
    write_stage_receipt(paths["stage_receipts"][2], binding)

    with pytest.raises(ValueError, match="validation sidecar"):
        _build(tmp_path, paths)


def test_scrub_receipt_must_bind_scrub_statistics(tmp_path: Path):
    paths = _fixture(tmp_path)
    draft = json.loads(paths["stage_receipts"][0].read_text(encoding="utf-8"))
    scrub = build_stage_receipt(
        run_id="run-1",
        stage="scrub",
        tool_name="content_scrubber",
        tool_version="1.0.0",
        started_at="2026-08-11T14:02:00Z",
        completed_at="2026-08-11T14:03:00Z",
        mutation=False,
        input_artifact_hashes={"article": _sha256(paths["article"])},
        output_artifact_hashes={"article": _sha256(paths["article"])},
        evidence_hashes={},
        previous_receipt_hash=draft["receipt_hash"],
    )
    write_stage_receipt(paths["stage_receipts"][1], scrub)
    binding = build_stage_receipt(
        run_id="run-1",
        stage="context_binding",
        tool_name="context_binding_generator",
        tool_version="1.0.0",
        started_at="2026-08-11T14:04:00Z",
        completed_at="2026-08-11T14:05:00Z",
        mutation=False,
        input_artifact_hashes={"article": _sha256(paths["article"])},
        output_artifact_hashes={
            "article": _sha256(paths["article"]),
            "validation_sidecar": _sha256(paths["sidecar"]),
        },
        evidence_hashes={
            "context_binding": "e" * 64,
            "not_applicable_reason": NON_CONNECTOR_REASON_SHA256,
        },
        previous_receipt_hash=scrub["receipt_hash"],
    )
    write_stage_receipt(paths["stage_receipts"][2], binding)

    with pytest.raises(ValueError, match="scrub statistics"):
        _build(tmp_path, paths)


def test_same_inputs_and_receipts_build_byte_identical_bom(tmp_path: Path):
    paths = _fixture(tmp_path)

    first = _build(tmp_path, paths)
    second = _build(tmp_path, paths)

    assert json.dumps(first, sort_keys=True) == json.dumps(second, sort_keys=True)


def test_builder_rejects_a_failed_or_invented_stage_receipt(tmp_path: Path):
    paths = _fixture(tmp_path)
    receipt_path = paths["stage_receipts"][1]
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    receipt["status"] = "passed"
    receipt_path.write_text(json.dumps(receipt), encoding="utf-8")

    with pytest.raises(ValueError, match="stage_receipt_status_invalid"):
        _build(tmp_path, paths)


def test_builder_derives_exact_optional_author_contract(tmp_path: Path):
    no_author = _build(tmp_path, _fixture(tmp_path))
    assert no_author["author_policy"] == {
        "status": "no_author",
        "name": "",
        "frontmatter_author_required": False,
        "schema_person_required": False,
        "named_author_voice_allowed": False,
    }


def test_question_heading_outside_faq_does_not_trigger_faq_schema(tmp_path: Path):
    paths = _fixture(tmp_path)
    article = paths["article"]
    article.write_text(
        article.read_text(encoding="utf-8")
        + "\n## Scheduling decisions\n\n### How should dispatchers decide?\n\nUse constraints.\n",
        encoding="utf-8",
    )

    policy = _schema_policy(read_publishable_markdown(article))
    assert policy["visible_faq"] is False
    assert "FAQPage" not in policy["required_entities"]


@pytest.mark.parametrize(
    "heading",
    ("FAQs", "Common questions", "Questions and answers"),
)
def test_supported_faq_heading_variants_trigger_faq_schema(
    tmp_path: Path,
    heading: str,
):
    paths = _fixture(tmp_path, visible_faq=True)
    article = paths["article"]
    article.write_text(
        article.read_text(encoding="utf-8").replace(
            "## Frequently asked questions",
            f"## {heading}",
        ),
        encoding="utf-8",
    )

    policy = _schema_policy(read_publishable_markdown(article))

    assert policy["visible_faq"] is True
    assert policy["faq_questions"] == [
        "How should field service teams schedule work?"
    ]
    assert "FAQPage" in policy["required_entities"]


@pytest.mark.parametrize(
    "markup",
    (
        "<details><summary>How should teams schedule work?</summary>Use capacity.</details>",
        "**How should teams schedule work?**\n\nUse capacity.",
    ),
)
def test_unsupported_faq_markup_cannot_bypass_schema_policy(
    tmp_path: Path,
    markup: str,
):
    paths = _fixture(tmp_path)
    article = paths["article"]
    article.write_text(
        article.read_text(encoding="utf-8") + f"\n{markup}\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="FAQ-like .* unsupported"):
        _schema_policy(read_publishable_markdown(article))


def test_named_author_is_derived_from_final_article(tmp_path: Path):
    paths = _fixture(tmp_path, author="Corey O'Donnell")

    bom = _build(tmp_path, paths)

    assert bom["author_policy"]["status"] == "named_author"
    assert bom["author_policy"]["name"] == "Corey O'Donnell"
    assert bom["author_policy"]["schema_person_required"] is True


def test_schema_policy_requires_videoobject_only_for_supported_embed(tmp_path: Path):
    paths = _fixture(tmp_path)
    unsupported = paths["article"].read_text(encoding="utf-8") + (
        '\n<iframe src="https://notyoutube.com/embed/fake"></iframe>\n'
    )
    paths["article"].write_text(unsupported, encoding="utf-8")
    assert _schema_policy(read_publishable_markdown(paths["article"]))["video_embed"] is False

    supported = unsupported + (
        '\n<iframe src="https://www.youtube-nocookie.com/embed/dQw4w9WgXcQ"></iframe>\n'
    )
    paths["article"].write_text(supported, encoding="utf-8")
    policy = _schema_policy(read_publishable_markdown(paths["article"]))

    assert policy["video_embed"] is True
    assert "VideoObject" in policy["required_entities"]


def test_placeholder_identity_is_rejected(tmp_path: Path):
    paths = _fixture(tmp_path)
    text = paths["article"].read_text(encoding="utf-8").replace(
        "audience: Field service leaders",
        "audience: Not provided",
    )
    paths["article"].write_text(text, encoding="utf-8")

    with pytest.raises(ValueError, match="blog_identity_audience_placeholder"):
        _build(tmp_path, paths)


def test_last_updated_must_match_assembly_date(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    paths = _fixture(tmp_path)
    monkeypatch.setattr(
        blog_assembly_contract,
        "current_utc_date",
        lambda: date(2026, 8, 10),
    )

    with pytest.raises(ValueError, match="last_updated_mismatch"):
        _build(tmp_path, paths, assembly_date="2026-08-10")


def test_builder_rejects_past_or_future_assembly_date_against_utc_today(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    paths = _fixture(tmp_path)
    monkeypatch.setattr(
        blog_assembly_contract,
        "current_utc_date",
        lambda: date(2026, 8, 12),
    )

    with pytest.raises(ValueError, match="current UTC date"):
        _build(tmp_path, paths, assembly_date="2026-08-11")


def test_guard_rejects_a_bom_after_its_assembly_date_becomes_stale(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    paths = _fixture(tmp_path)
    bom = _build(tmp_path, paths)
    monkeypatch.setattr(
        blog_assembly_contract,
        "current_utc_date",
        lambda: date(2026, 8, 12),
    )

    rules = {
        finding["rule_id"]
        for finding in check_bom(
            bom,
            article_path=paths["article"],
            validation_sidecar_path=paths["sidecar"],
            workspace_root=tmp_path,
        )
    }

    assert "bom_assembly_date_not_current" in rules


def test_simpro_article_derives_required_connector_binding(tmp_path: Path):
    paths = _fixture(tmp_path, brand="Simpro")

    with pytest.raises(ValueError, match="requires context_request_path"):
        _build(tmp_path, paths)


def test_connector_summary_comes_only_from_structured_validated_result(tmp_path: Path):
    paths = _fixture(tmp_path, brand="Simpro")
    request = _json(tmp_path / "research" / "context-request.json", {"scope": {}})
    pack = _json(tmp_path / "research" / "context-pack.json", {"schema": "simpro-product-context-pack/v2"})
    receipt = _json(tmp_path / "research" / "context-receipt.json", {"schema": "simpro-context-receipt/v1"})
    selector = _json(tmp_path / "research" / "selector.json", {"status": "complete"})
    fred = tmp_path / "research" / "fred.md"
    fred.write_text(
        "## Fred Voccola Authority Selection\n"
        "- Evaluation status: completed\n"
        "- Selected: [none]\n",
        encoding="utf-8",
    )
    paths["sidecar"].write_text(
        paths["sidecar"].read_text(encoding="utf-8")
        + f"\n- Selector evidence: research/selector.json | SHA-256: {_sha256(selector)}\n\n"
        + fred.read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    _refresh_normal_stage_receipts(paths)
    validated = ContextValidationResult(
        required=True,
        findings=(),
        resource_ids=("resource-1",),
        approved_claim_ids=("claim-approved",),
        pack_canonical_sha256="a" * 64,
        receipt_canonical_sha256="b" * 64,
        revisions=(("manifest_revision", "manifest-r1"),),
    )

    with patch(
        "data_sources.modules.blog_assembly_bom.context_binding_guard.validate_context_artifacts",
        return_value=validated,
    ):
        bom = _build(
            tmp_path,
            paths,
            context_request_path=request,
            context_pack_path=pack,
            context_receipt_path=receipt,
            customer_proof_selector_evidence_path=selector,
            fred_authority_evidence_path=fred,
        )

    context = bom["connector_binding"]["context"]
    assert bom["connector_binding"]["status"] == "required"
    assert context["selected_resource_ids"] == ["resource-1"]
    assert context["claim_ids"] == ["claim-approved"]
    assert context["revisions"] == {"manifest_revision": "manifest-r1"}

    other_selector = _json(
        tmp_path / "research" / "other-selector.json",
        {"status": "different"},
    )
    other_fred = tmp_path / "research" / "other-fred.md"
    other_fred.write_text(
        "## Fred Voccola Authority Selection\n- Evaluation status: blocked\n",
        encoding="utf-8",
    )
    bom["artifacts"]["customer_proof_selector_evidence"] = {
        "path": "research/other-selector.json",
        "sha256": _sha256(other_selector),
    }
    bom["artifacts"]["fred_authority_evidence"] = {
        "path": "research/other-fred.md",
        "sha256": _sha256(other_fred),
    }
    rules = {
        finding["rule_id"]
        for finding in check_bom(
            bom,
            article_path=paths["article"],
            validation_sidecar_path=paths["sidecar"],
            context_request_path=request,
            context_pack_path=pack,
            context_receipt_path=receipt,
            workspace_root=tmp_path,
            context_result=validated,
        )
    }
    assert "bom_customer_proof_evidence_binding_mismatch" in rules
    assert "bom_fred_evidence_binding_mismatch" in rules


def test_check_bom_connector_fallback_passes_bound_plan_to_context_guard(tmp_path: Path):
    paths = _fixture(tmp_path, brand="Simpro")
    request = _json(tmp_path / "research" / "context-request.json", {"scope": {}})
    pack = _json(tmp_path / "research" / "context-pack.json", {"schema": "simpro-product-context-pack/v2"})
    receipt = _json(tmp_path / "research" / "context-receipt.json", {"schema": "simpro-context-receipt/v1"})
    selector = _json(tmp_path / "research" / "selector.json", {"status": "complete"})
    fred = tmp_path / "research" / "fred.md"
    fred.write_text(
        "## Fred Voccola Authority Selection\n"
        "- Evaluation status: completed\n"
        "- Selected: [none]\n",
        encoding="utf-8",
    )
    paths["sidecar"].write_text(
        paths["sidecar"].read_text(encoding="utf-8")
        + f"\n- Selector evidence: research/selector.json | SHA-256: {_sha256(selector)}\n\n"
        + fred.read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    _refresh_normal_stage_receipts(paths)
    validated = ContextValidationResult(
        required=True,
        findings=(),
        resource_ids=("resource-1",),
        approved_claim_ids=("claim-approved",),
        pack_canonical_sha256="a" * 64,
        receipt_canonical_sha256="b" * 64,
        revisions=(("manifest_revision", "manifest-r1"),),
    )

    with patch(
        "data_sources.modules.blog_assembly_bom.context_binding_guard.validate_context_artifacts",
        return_value=validated,
    ):
        bom = _build(
            tmp_path,
            paths,
            context_request_path=request,
            context_pack_path=pack,
            context_receipt_path=receipt,
            customer_proof_selector_evidence_path=selector,
            fred_authority_evidence_path=fred,
        )

    with patch(
        "data_sources.modules.blog_assembly_bom_guard.context_binding_guard.validate_context_artifacts",
        return_value=validated,
    ) as validate:
        findings = check_bom(
            bom,
            article_path=paths["article"],
            validation_sidecar_path=paths["sidecar"],
            context_request_path=request,
            context_pack_path=pack,
            context_receipt_path=receipt,
            workspace_root=tmp_path,
        )

    assert findings == []
    assert validate.call_args.kwargs["editorial_plan"]["schema"] == "simpro-blog-editorial-plan/v1"


def test_builder_records_industry_cluster_link_policy(tmp_path: Path):
    paths = _fixture(tmp_path)

    bom = _build(tmp_path, paths)

    assert bom["industry_cluster_link_policy"] == {
        "status": "not_applicable",
        "reason": "No single-trade Simpro industry cluster link is required.",
    }


def test_connector_builder_rejects_orphaned_proof_and_fred_inventory(tmp_path: Path):
    paths = _fixture(tmp_path, brand="Simpro")
    request = _json(tmp_path / "research" / "context-request.json", {"scope": {}})
    pack = _json(tmp_path / "research" / "context-pack.json", {"schema": "simpro-product-context-pack/v2"})
    receipt = _json(tmp_path / "research" / "context-receipt.json", {"schema": "simpro-context-receipt/v1"})
    selector = _json(tmp_path / "research" / "selector.json", {"status": "complete"})
    fred = tmp_path / "research" / "fred.md"
    fred.write_text(
        "## Fred Voccola Authority Selection\n- Evaluation status: completed\n",
        encoding="utf-8",
    )
    validated = ContextValidationResult(
        required=True,
        findings=(),
        resource_ids=("resource-1",),
        approved_claim_ids=("claim-approved",),
        pack_canonical_sha256="a" * 64,
        receipt_canonical_sha256="b" * 64,
        revisions=(("manifest_revision", "manifest-r1"),),
    )

    with patch(
        "data_sources.modules.blog_assembly_bom.context_binding_guard.validate_context_artifacts",
        return_value=validated,
    ):
        with pytest.raises(ValueError, match="bom_customer_proof_evidence_binding_missing"):
            _build(
                tmp_path,
                paths,
                context_request_path=request,
                context_pack_path=pack,
                context_receipt_path=receipt,
                customer_proof_selector_evidence_path=selector,
                fred_authority_evidence_path=fred,
            )


def test_rewrite_preselected_brief_paa_binds_brief_instead_of_answersocrates(tmp_path: Path):
    paths = _fixture(tmp_path, visible_faq=True)
    plan = json.loads(paths["editorial_plan"].read_text(encoding="utf-8"))
    plan["paa_policy"]["source_kind"] = "brief_paa"
    _json(paths["editorial_plan"], plan)
    _refresh_normal_stage_receipts(paths)
    brief = tmp_path / "research" / "content-brief.md"
    brief.write_text(
        "## Pre-picked PAA Questions\n\n"
        "- How should field service teams schedule work?\n",
        encoding="utf-8",
    )

    bom = _build(
        tmp_path,
        paths,
        workflow_mode="rewrite",
        paa_artifact_path=None,
        content_brief_path=brief,
    )

    assert bom["paa_policy"]["source_kind"] == "brief_paa"
    assert bom["artifacts"]["paa_artifact"] is None
    assert bom["artifacts"]["content_brief"]["sha256"] == _sha256(brief)


def test_user_csv_requires_bound_answersocrates_blocker(tmp_path: Path):
    paths = _fixture(tmp_path)
    plan = json.loads(paths["editorial_plan"].read_text(encoding="utf-8"))
    plan["paa_policy"]["source_kind"] = "user_csv"
    _json(paths["editorial_plan"], plan)
    _refresh_normal_stage_receipts(paths)
    csv = tmp_path / "research" / "user-paa.csv"
    csv.write_text("question\nHow should teams schedule work?\n", encoding="utf-8")

    with pytest.raises(ValueError, match="answersocrates_blocker_path"):
        _build(
            tmp_path,
            paths,
            paa_artifact_path=None,
            user_paa_csv_path=csv,
        )


def _preflight(
    tmp_path: Path,
    bom_path: Path,
    bom: dict,
    *,
    passed: bool = True,
    filename: str = "preflight-readiness.json",
) -> Path:
    artifacts = bom["artifacts"]
    input_hashes = {}
    for label, row in artifacts.items():
        if row is None:
            continue
        if isinstance(row, list):
            for index, item in enumerate(row):
                input_hashes[f"{label}[{index}]"] = item
        else:
            input_hashes[label] = row
    input_hashes["assembly_bom"] = {
        "path": bom_path.relative_to(tmp_path).as_posix(),
        "sha256": _sha256(bom_path),
    }
    gate_inventory = expected_blog_gate_inventory(
        visible_faq=bool(bom["schema_policy"]["visible_faq"]),
        connector_required=bom["connector_binding"]["status"] == "required",
    )
    gates = [
        {
            "name": name,
            "label": name.replace("_", " ").title(),
            "passed": passed,
            "errors": 0 if passed else 1,
            "warnings": 0,
            "findings": [],
            "blockers": [] if passed else ["fixture failure"],
        }
        for name in gate_inventory
    ]
    optimized = any(
        receipt.get("stage") == "optimization"
        for receipt in bom["workflow"]["stage_receipts"]
    )

    def artifact_path(label: str) -> str | None:
        row = artifacts.get(label)
        if not isinstance(row, dict):
            return None
        return str((tmp_path / row["path"]).resolve())

    readiness = {
        "schema": "simpro-publish-readiness-result/v1",
        "tool": {"name": "publish_readiness", "version": "1.0.0"},
        "phase": "preflight",
        "verification_scope": "source_artifact",
        "file": artifact_path("article"),
        "proof_sidecar": artifact_path("validation_sidecar"),
        "context_request": artifact_path("context_request"),
        "context_pack": artifact_path("context_pack"),
        "context_receipt": artifact_path("context_receipt"),
        "assembly_bom": str(bom_path.resolve()),
        "passed": passed,
        "artifact_kind": "blog",
        "gates": gates,
        "gate_inventory": gate_inventory,
        "score": 95 if passed else 0,
        "score_threshold": 85,
        "aeo_geo": {
            "score": 95 if passed else 0,
            "threshold": 90,
            "passed": passed,
        },
        "scorecard": {
            "passed": passed,
            "content_quality": {
                "score": 95 if passed else 0,
                "threshold": 85,
                "passed": passed,
            },
            "seo_quality": {
                "score": 95 if passed else 0,
                "threshold": 90,
                "passed": passed,
                "critical_issue_count": 0 if passed else 1,
                "critical_issues": [] if passed else ["Fixture SEO failure."],
            },
            "aeo_geo": {
                "score": 95 if passed else 0,
                "threshold": 90,
                "passed": passed,
            },
        },        "priority_fixes": [],
        "input_seal": {"status": "verified" if passed else "failed"},
        "input_hashes": input_hashes,
        "run_id": "run-1",
        "started_at": (
            "2026-08-11T14:14:00Z" if optimized else "2026-08-11T14:06:00Z"
        ),
        "completed_at": (
            "2026-08-11T14:15:00Z" if optimized else "2026-08-11T14:07:00Z"
        ),
    }
    readiness_path = tmp_path / "research" / filename
    if passed:
        with patch(
            "data_sources.modules.publish_readiness._validate_actual_readiness_execution"
        ):
            write_readiness_result(
                readiness_path,
                readiness,
                workspace_root=tmp_path,
            )
    else:
        _json(readiness_path, readiness)
    return readiness_path


def _finalize_fixture_bom(
    *,
    bom_path: Path,
    preflight_readiness_path: Path,
    workspace_root: Path,
) -> dict:
    """Finalize a fixture while leaving production rerun verification enabled by default.

    These focused BOM tests use deliberately small article fixtures that are not
    intended to pass every editorial readiness gate. Tests that exercise behavior
    after the live-rerun boundary provide the exact persisted result as the rerun
    result; the dedicated rerun-adversary test below covers disagreement.
    """
    readiness = json.loads(preflight_readiness_path.read_text(encoding="utf-8"))
    with patch(
        "data_sources.modules.blog_assembly_bom._rerun_preflight_readiness",
        return_value=readiness,
    ):
        return finalize_blog_assembly_bom(
            bom_path=bom_path,
            preflight_readiness_path=preflight_readiness_path,
            workspace_root=workspace_root,
        )


def _prepare_optimized_workflow(
    tmp_path: Path,
    paths: dict[str, Path],
) -> tuple[Path, Path]:
    initial_bom = _build(tmp_path, paths)
    initial_bom_path = tmp_path / "research" / "initial-bom.json"
    write_blog_assembly_bom(initial_bom_path, initial_bom)
    prior_readiness = _preflight(tmp_path, initial_bom_path, initial_bom)
    prior_receipt_path = (
        prior_readiness.parent
        / f"{prior_readiness.stem}-stage-receipt.json"
    )
    prior_receipt = json.loads(prior_receipt_path.read_text(encoding="utf-8"))
    before_hash = _sha256(paths["article"])
    paths["article"].write_text(
        paths["article"].read_text(encoding="utf-8")
        + "\n## Optimization contribution\n\nA clearer final decision framework.\n",
        encoding="utf-8",
    )
    after_hash = _sha256(paths["article"])
    optimizer = _json(
        tmp_path / "research" / "optimizer-output.json",
        {"schema": "simpro-optimizer-output/v1", "status": "completed"},
    )
    optimization = build_stage_receipt(
        run_id="run-1",
        stage="optimization",
        tool_name="manual_optimizer",
        tool_version="1.0.0",
        started_at="2026-08-11T14:08:00Z",
        completed_at="2026-08-11T14:09:00Z",
        mutation=True,
        input_artifact_hashes={"article": before_hash},
        output_artifact_hashes={"article": after_hash},
        evidence_hashes={"optimizer_output": _sha256(optimizer)},
        previous_receipt_hash=prior_receipt["receipt_hash"],
    )
    optimization_path = tmp_path / "research" / "stage-optimization.json"
    write_stage_receipt(optimization_path, optimization)
    post_scrub = build_stage_receipt(
        run_id="run-1",
        stage="post_optimization_scrub",
        tool_name="content_scrubber",
        tool_version="1.0.0",
        started_at="2026-08-11T14:10:00Z",
        completed_at="2026-08-11T14:11:00Z",
        mutation=False,
        input_artifact_hashes={"article": after_hash},
        output_artifact_hashes={"article": after_hash},
        evidence_hashes={"scrub_statistics": "d" * 64},
        previous_receipt_hash=optimization["receipt_hash"],
    )
    post_scrub_path = tmp_path / "research" / "stage-post-scrub.json"
    write_stage_receipt(post_scrub_path, post_scrub)
    paths["sidecar"].write_text(
        paths["sidecar"].read_text(encoding="utf-8")
        + "Final Context Binding regenerated.\n",
        encoding="utf-8",
    )
    post_binding = build_stage_receipt(
        run_id="run-1",
        stage="post_optimization_context_binding",
        tool_name="context_binding_generator",
        tool_version="1.0.0",
        started_at="2026-08-11T14:12:00Z",
        completed_at="2026-08-11T14:13:00Z",
        mutation=False,
        input_artifact_hashes={"article": after_hash},
        output_artifact_hashes={
            "article": after_hash,
            "validation_sidecar": _sha256(paths["sidecar"]),
        },
        evidence_hashes={
            "context_binding": "c" * 64,
            "not_applicable_reason": NON_CONNECTOR_REASON_SHA256,
        },
        previous_receipt_hash=post_scrub["receipt_hash"],
    )
    post_binding_path = tmp_path / "research" / "stage-post-binding.json"
    write_stage_receipt(post_binding_path, post_binding)
    paths["stage_receipts"] = [
        *paths["stage_receipts"],
        prior_receipt_path,
        optimization_path,
        post_scrub_path,
        post_binding_path,
    ]
    return prior_readiness, optimizer


def test_optimized_bom_binds_the_earlier_preflight_output(tmp_path: Path):
    paths = _fixture(tmp_path)
    prior_readiness, optimizer = _prepare_optimized_workflow(tmp_path, paths)

    bom = _build(
        tmp_path,
        paths,
        optimizer_output_paths=[optimizer],
        prior_preflight_readiness_path=prior_readiness,
    )

    assert bom["artifacts"]["prior_preflight_readiness"] == {
        "path": "research/preflight-readiness.json",
        "sha256": _sha256(prior_readiness),
    }
    assert [
        receipt["stage"] for receipt in bom["workflow"]["stage_receipts"]
    ][-4:] == [
        "preflight_readiness",
        "optimization",
        "post_optimization_scrub",
        "post_optimization_context_binding",
    ]


def test_optimized_bom_output_cannot_replace_prior_preflight_bom(
    tmp_path: Path,
):
    paths = _fixture(tmp_path)
    prior_readiness, optimizer = _prepare_optimized_workflow(tmp_path, paths)
    prior_bom_path = tmp_path / "research" / "initial-bom.json"
    prior_bom_bytes = prior_bom_path.read_bytes()
    optimized_bom = _build(
        tmp_path,
        paths,
        optimizer_output_paths=[optimizer],
        prior_preflight_readiness_path=prior_readiness,
    )

    with pytest.raises(
        ValueError,
        match="prior_preflight_readiness input assembly_bom",
    ):
        _reject_bom_output_collision(
            "research/initial-bom.json",
            optimized_bom,
            workspace_root=tmp_path,
        )

    post_optimization_bom = (
        tmp_path / "research" / "blog-assembly-bom-post-optimization.json"
    )
    _reject_bom_output_collision(
        post_optimization_bom,
        optimized_bom,
        workspace_root=tmp_path,
    )
    write_blog_assembly_bom(post_optimization_bom, optimized_bom)

    assert prior_bom_path.read_bytes() == prior_bom_bytes
    assert post_optimization_bom.exists()


def test_optimized_bom_rejects_missing_prior_preflight_artifact(tmp_path: Path):
    paths = _fixture(tmp_path)
    _, optimizer = _prepare_optimized_workflow(tmp_path, paths)

    with pytest.raises(ValueError, match="prior preflight readiness evidence"):
        _build(
            tmp_path,
            paths,
            optimizer_output_paths=[optimizer],
            prior_preflight_readiness_path=None,
        )


def test_optimized_bom_rejects_changed_prior_provisional_bom(tmp_path: Path):
    paths = _fixture(tmp_path)
    prior_readiness, optimizer = _prepare_optimized_workflow(tmp_path, paths)
    prior_bom = tmp_path / "research" / "initial-bom.json"
    prior_bom.write_text(
        prior_bom.read_text(encoding="utf-8") + "\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="prior preflight BOM artifact is invalid"):
        _build(
            tmp_path,
            paths,
            optimizer_output_paths=[optimizer],
            prior_preflight_readiness_path=prior_readiness,
        )


def test_optimized_bom_finalizes_with_a_distinct_final_preflight(tmp_path: Path):
    paths = _fixture(tmp_path)
    prior_readiness, optimizer = _prepare_optimized_workflow(tmp_path, paths)
    provisional = _build(
        tmp_path,
        paths,
        optimizer_output_paths=[optimizer],
        prior_preflight_readiness_path=prior_readiness,
    )
    bom_path = tmp_path / "research" / "optimized-bom.json"
    write_blog_assembly_bom(bom_path, provisional)
    final_preflight = _preflight(
        tmp_path,
        bom_path,
        provisional,
        filename="final-preflight-readiness.json",
    )

    final = _finalize_fixture_bom(
        bom_path=bom_path,
        preflight_readiness_path=final_preflight,
        workspace_root=tmp_path,
    )

    assert final["lifecycle_state"] == "final"
    assert final["workflow"]["stage_receipts"][-1]["stage"] == (
        "final_preflight_readiness"
    )
    assert final["artifacts"]["prior_preflight_readiness"]["sha256"] == (
        _sha256(prior_readiness)
    )


def test_caller_invented_minimal_passed_preflight_cannot_finalize(tmp_path: Path):
    paths = _fixture(tmp_path)
    bom = _build(tmp_path, paths)
    bom_path = tmp_path / "research" / "bom.json"
    write_blog_assembly_bom(bom_path, bom)
    preflight = _preflight(tmp_path, bom_path, bom)
    readiness = json.loads(preflight.read_text(encoding="utf-8"))
    readiness.pop("gates")
    readiness.pop("score")
    readiness.pop("aeo_geo")
    readiness["gate_inventory"] = [
        "artifact_identity",
        "context_binding",
        "blog_assembly_bom",
        "paa_provenance",
        "source_support",
        "content_scorer",
    ]
    _json(preflight, readiness)

    with pytest.raises(ValueError, match="gate inventory|gate results|score"):
        finalize_blog_assembly_bom(
            bom_path=bom_path,
            preflight_readiness_path=preflight,
            workspace_root=tmp_path,
        )


def test_structurally_complete_fabricated_preflight_cannot_survive_rerun(
    tmp_path: Path,
):
    paths = _fixture(tmp_path)
    bom = _build(tmp_path, paths)
    bom_path = tmp_path / "research" / "bom.json"
    write_blog_assembly_bom(bom_path, bom)
    preflight = _preflight(tmp_path, bom_path, bom)
    actual_rerun = json.loads(preflight.read_text(encoding="utf-8"))
    actual_rerun["passed"] = False

    with patch(
        "data_sources.modules.blog_assembly_bom._rerun_preflight_readiness",
        return_value=actual_rerun,
    ) as rerun:
        with pytest.raises(ValueError, match="verification rerun did not pass"):
            finalize_blog_assembly_bom(
                bom_path=bom_path,
                preflight_readiness_path=preflight,
                workspace_root=tmp_path,
            )

    rerun.assert_called_once()


def test_failed_preflight_cannot_finalize(tmp_path: Path):
    paths = _fixture(tmp_path)
    bom = _build(tmp_path, paths)
    bom_path = tmp_path / "research" / "bom.json"
    write_blog_assembly_bom(bom_path, bom)
    preflight = _preflight(tmp_path, bom_path, bom, passed=False)

    with pytest.raises(ValueError, match="failed preflight"):
        finalize_blog_assembly_bom(
            bom_path=bom_path,
            preflight_readiness_path=preflight,
            workspace_root=tmp_path,
        )


def test_finalization_reruns_the_full_provisional_bom_guard(tmp_path: Path):
    paths = _fixture(tmp_path)
    bom = _build(tmp_path, paths)
    bom["caller_asserted_policy"] = {"passed": True}
    bom_path = tmp_path / "research" / "bom.json"
    write_blog_assembly_bom(bom_path, bom)
    preflight = _preflight(tmp_path, bom_path, bom)

    with pytest.raises(ValueError, match="provisional BOM is invalid"):
        finalize_blog_assembly_bom(
            bom_path=bom_path,
            preflight_readiness_path=preflight,
            workspace_root=tmp_path,
        )


def test_finalize_adds_passed_preflight_without_self_reference(tmp_path: Path):
    paths = _fixture(tmp_path)
    bom = _build(tmp_path, paths)
    bom_path = tmp_path / "research" / "bom.json"
    write_blog_assembly_bom(bom_path, bom)
    preflight = _preflight(tmp_path, bom_path, bom)

    final = _finalize_fixture_bom(
        bom_path=bom_path,
        preflight_readiness_path=preflight,
        workspace_root=tmp_path,
    )

    assert final["lifecycle_state"] == "final"
    assert final["artifacts"]["preflight_readiness"]["sha256"] == _sha256(preflight)
    assert final["preflight"]["verification_scope"] == "source_artifact"
    assert "final_readiness" not in final["artifacts"]


def test_direct_script_build_cli_uses_the_same_strict_contract(tmp_path: Path):
    paths = _fixture(tmp_path)
    plan_review, article_review = _machine_reviews(tmp_path, paths)
    output = tmp_path / "research" / "direct-script-bom.json"
    script = Path(__file__).parents[1] / "data_sources" / "modules" / "blog_assembly_bom.py"

    arguments = [
        sys.executable,
        str(script),
        "build",
        str(paths["article"]),
        "--validation-sidecar",
        str(paths["sidecar"]),
        "--editorial-plan",
        str(paths["editorial_plan"]),
        "--keyword-decision",
        str(paths["keyword_decision"]),
        "--serp-evidence",
        str(paths["serp"]),
        "--plan-review",
        str(plan_review),
        "--article-review",
        str(article_review),
        "--paa-artifact",
        str(paths["paa"]),
    ]
    for receipt in paths["stage_receipts"]:
        arguments.extend(("--stage-receipt", str(receipt)))
    arguments.extend(
        (
            "--workflow-mode",
            "new",
            "--assembly-date",
            "2026-08-11",
            "--workspace-root",
            str(tmp_path),
            "--output",
            str(output),
        )
    )

    completed = subprocess.run(
        arguments,
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
        env={**os.environ, "SEOMACHINE_TEST_CURRENT_UTC_DATE": "2026-08-11"},
    )

    assert completed.returncode == 0, completed.stderr
    assert json.loads(output.read_text(encoding="utf-8"))["lifecycle_state"] == (
        "provisional"
    )


def test_build_cli_rejects_output_collision_without_overwriting_article(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
):
    paths = _fixture(tmp_path)
    plan_review, article_review = _machine_reviews(tmp_path, paths)
    original = paths["article"].read_bytes()
    arguments = [
        "build",
        str(paths["article"]),
        "--validation-sidecar",
        str(paths["sidecar"]),
        "--editorial-plan",
        str(paths["editorial_plan"]),
        "--keyword-decision",
        str(paths["keyword_decision"]),
        "--serp-evidence",
        str(paths["serp"]),
        "--plan-review",
        str(plan_review),
        "--article-review",
        str(article_review),
        "--paa-artifact",
        str(paths["paa"]),
    ]
    for receipt in paths["stage_receipts"]:
        arguments.extend(("--stage-receipt", str(receipt)))
    arguments.extend(
        (
            "--workflow-mode",
            "new",
            "--assembly-date",
            "2026-08-11",
            "--workspace-root",
            str(tmp_path),
            "--output",
            str(paths["article"]),
        )
    )

    with pytest.raises(SystemExit) as raised:
        bom_main(arguments)

    captured = capsys.readouterr()
    assert raised.value.code == 2
    assert "BOM output cannot overwrite artifact article" in captured.err
    assert "Traceback" not in captured.err
    assert paths["article"].read_bytes() == original


def test_finalize_cli_rejects_output_collision_without_overwriting_preflight(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
):
    paths = _fixture(tmp_path)
    bom = _build(tmp_path, paths)
    bom_path = tmp_path / "research" / "bom.json"
    write_blog_assembly_bom(bom_path, bom)
    preflight = _preflight(tmp_path, bom_path, bom)
    original = preflight.read_bytes()

    readiness = json.loads(preflight.read_text(encoding="utf-8"))
    with patch(
        "data_sources.modules.blog_assembly_bom._rerun_preflight_readiness",
        return_value=readiness,
    ):
        with pytest.raises(SystemExit) as raised:
            bom_main(
                [
                    "finalize",
                    "--bom",
                    str(bom_path),
                    "--preflight-readiness",
                    str(preflight),
                    "--workspace-root",
                    str(tmp_path),
                    "--output",
                    str(preflight),
                ]
            )

    captured = capsys.readouterr()
    assert raised.value.code == 2
    assert "BOM output cannot overwrite artifact preflight_readiness" in captured.err
    assert "Traceback" not in captured.err
    assert preflight.read_bytes() == original


def test_finalize_cli_rejects_in_place_replacement_of_preflight_bom(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
):
    paths = _fixture(tmp_path)
    bom = _build(tmp_path, paths)
    bom_path = tmp_path / "research" / "bom.json"
    write_blog_assembly_bom(bom_path, bom)
    preflight = _preflight(tmp_path, bom_path, bom)
    original_bom = bom_path.read_bytes()

    readiness = json.loads(preflight.read_text(encoding="utf-8"))
    with patch(
        "data_sources.modules.blog_assembly_bom._rerun_preflight_readiness",
        return_value=readiness,
    ):
        with pytest.raises(SystemExit) as raised:
            bom_main(
                [
                    "finalize",
                    "--bom",
                    str(bom_path),
                    "--preflight-readiness",
                    str(preflight),
                    "--workspace-root",
                    str(tmp_path),
                    "--output",
                    str(bom_path),
                ]
            )

    captured = capsys.readouterr()
    assert raised.value.code == 2
    assert (
        "BOM output cannot overwrite preflight_readiness input assembly_bom"
        in captured.err
    )
    assert "Traceback" not in captured.err
    assert bom_path.read_bytes() == original_bom


def test_bom_cli_reports_invalid_input_without_traceback(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
):
    missing = tmp_path / "missing.md"

    with pytest.raises(SystemExit) as raised:
        bom_main(
            [
                "build",
                str(missing),
                "--validation-sidecar",
                str(missing),
                "--editorial-plan",
                str(missing),
                "--keyword-decision",
                str(missing),
                "--serp-evidence",
                str(missing),
                "--paa-artifact",
                str(missing),
                "--stage-receipt",
                str(missing),
                "--workflow-mode",
                "new",
                "--assembly-date",
                "2026-08-11",
                "--workspace-root",
                str(tmp_path),
                "--output",
                str(tmp_path / "bom.json"),
            ]
        )

    captured = capsys.readouterr()
    assert raised.value.code == 2
    assert "error:" in captured.err
    assert "Traceback" not in captured.err


def test_changed_artifact_after_preflight_blocks_finalization(tmp_path: Path):
    paths = _fixture(tmp_path)
    bom = _build(tmp_path, paths)
    bom_path = tmp_path / "research" / "bom.json"
    write_blog_assembly_bom(bom_path, bom)
    preflight = _preflight(tmp_path, bom_path, bom)
    paths["serp"].write_text('{"tampered": true}\n', encoding="utf-8")

    with pytest.raises(
        ValueError,
        match="bom_serp_evidence_hash_mismatch|does not match current file contents",
    ):
        finalize_blog_assembly_bom(
            bom_path=bom_path,
            preflight_readiness_path=preflight,
            workspace_root=tmp_path,
        )


def test_preflight_missing_bound_plan_hash_cannot_finalize(tmp_path: Path):
    paths = _fixture(tmp_path)
    bom = _build(tmp_path, paths)
    bom_path = tmp_path / "research" / "bom.json"
    write_blog_assembly_bom(bom_path, bom)
    preflight = _preflight(tmp_path, bom_path, bom)
    readiness = json.loads(preflight.read_text(encoding="utf-8"))
    readiness["input_hashes"].pop("editorial_plan")
    preflight.write_text(json.dumps(readiness), encoding="utf-8")

    with pytest.raises(ValueError, match="editorial_plan"):
        finalize_blog_assembly_bom(
            bom_path=bom_path,
            preflight_readiness_path=preflight,
            workspace_root=tmp_path,
        )
