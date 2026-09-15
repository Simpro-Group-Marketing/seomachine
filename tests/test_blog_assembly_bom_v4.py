from __future__ import annotations

import hashlib
import json
from datetime import date
from pathlib import Path
import shutil

import pytest

from data_sources.modules.blog_assembly_bom import build_blog_assembly_bom_from_files
from data_sources.modules.blog_assembly_bom_guard import check_bom
from data_sources.modules import blog_assembly_contract
from tests.test_blog_assembly_bom import _fixture, _refresh_normal_stage_receipts
from tests.test_blog_assembly_bom_v2 import _reviews


REPO_ROOT = Path(__file__).resolve().parents[1]
EXCERPT = "A field service scheduling guide should balance capacity and dispatch constraints."


@pytest.fixture(autouse=True)
def _freeze_clock(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(blog_assembly_contract, "current_utc_date", lambda: date(2026, 8, 11))


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _upgrade_to_v4(tmp_path: Path) -> dict[str, Path]:
    paths = _fixture(tmp_path)
    article = paths["article"].read_text(encoding="utf-8")
    article = article.replace(
        "title: Scheduling guide\n",
        "title: Scheduling guide\n"
        "meta_title: Field Service Scheduling Guide\n"
        "meta_description: A practical guide to capacity-aware field service scheduling.\n"
        "url_slug: scheduling-guide\n"
        "primary_keyword: field service scheduling guide\n"
        "secondary_keywords:\n"
        "  - capacity planning\n"
        "  - dispatch constraints\n",
    )
    paths["article"].write_text(article, encoding="utf-8")

    plan = json.loads(paths["editorial_plan"].read_text(encoding="utf-8"))
    plan["schema"] = "simpro-blog-editorial-plan/v2"
    for index, section in enumerate(plan["sections"]):
        section.update(
            {
                "reader_question": "How should field service teams schedule work?",
                "section_payoff": "A practical constraint-first scheduling decision.",
                "bridge_from_previous": None if index == 0 else "Apply the sequence to common questions.",
                "bridge_to_next": None if index == len(plan["sections"]) - 1 else "Next, answer the practical questions.",
            }
        )
    plan["original_contributions"] = [
        {
            "contribution_id": "constraint-first-scheduling",
            "planned_contribution": "A constraint-first scheduling decision.",
            "purpose": "Help readers balance capacity and dispatch constraints.",
            "evidence_source": "Bound SERP and keyword-decision artifacts.",
            "target_section": "Scheduling guide",
        }
    ]
    plan["search_strategy"] = {
        "primary_query": "field service scheduling guide",
        "searcher_task": "Choose a practical scheduling workflow.",
        "intent_class": "informational",
        "funnel_stage": "tofu",
        "serp_evidence_artifact": "research/serp-evidence.json",
        "dominant_content_type": "General Article",
        "selected_content_type": "General Article",
        "observed_serp_features": ["featured snippet"],
        "related_query_paa_artifact": "research/paa.json",
        "format_decision": "match_dominant",
        "exception_reason": "none",
        "status": "ready",
    }
    plan["commercial_strategy"] = {
        "article_title": "Scheduling guide",
        "article_primary_keyword": "field service scheduling guide",
        "article_intent": "informational",
        "destination_id": "simpro-us-homepage-field-service-management-software",
        "commercial_pillar_url": "https://www.simprogroup.com/",
        "planned_anchor_text": "field service management software",
        "planned_h2_section": "Scheduling guide",
        "existing_overlapping_urls_checked": ["https://www.bigchange.com/blog/"],
        "pillar_versus_blog_intent_difference": "The article is informational while the destination is commercial.",
        "cannibalization_decision": "different_intent",
        "incoming_link_candidates": ["https://www.bigchange.com/blog/"],
        "status": "aligned",
    }
    plan["lifecycle"] = {
        "last_updated_date": "2026-08-11",
        "volatility": "standard",
        "next_review_date": "2027-02-01",
        "review_command": "/performance-review published/scheduling-guide.md",
        "gsc_lane": "unavailable: new article has no post-publication data",
        "ga4_lane": "unavailable: new article has no post-publication data",
        "semrush_lane": "available: bound keyword decision",
        "ai_citation_lane": "unavailable: new article has no post-publication data",
        "decision": "retain",
        "status": "scheduled",
    }
    del plan["serp_strategy"]
    del plan["query_ownership"]
    paths["editorial_plan"].write_text(
        json.dumps(plan, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    fulfillment = tmp_path / "research" / "plan-fulfillment.json"
    fulfillment.write_text(
        json.dumps(
            {
                "schema": "simpro-blog-plan-fulfillment/v1",
                "editorial_plan_sha256": _sha256(paths["editorial_plan"]),
                "article_sha256": _sha256(paths["article"]),
                "contributions": [
                    {
                        "contribution_id": "constraint-first-scheduling",
                        "actual_excerpt": EXCERPT,
                    }
                ],
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    index = tmp_path / "context" / "commercial-pillar-index.json"
    index.parent.mkdir(exist_ok=True)
    shutil.copyfile(REPO_ROOT / "context" / "commercial-pillar-index.json", index)
    paths["plan_fulfillment"] = fulfillment
    paths["commercial_pillar_index"] = index
    _refresh_normal_stage_receipts(paths)
    return paths


def _build(tmp_path: Path) -> tuple[dict, dict[str, Path]]:
    paths = _upgrade_to_v4(tmp_path)
    plan_review, article_review = _reviews(tmp_path, paths)
    bom = build_blog_assembly_bom_from_files(
        article_path=paths["article"],
        validation_sidecar_path=paths["sidecar"],
        editorial_plan_path=paths["editorial_plan"],
        keyword_decision_path=paths["keyword_decision"],
        serp_evidence_path=paths["serp"],
        plan_fulfillment_path=paths["plan_fulfillment"],
        commercial_pillar_index_path=paths["commercial_pillar_index"],
        paa_artifact_path=paths["paa"],
        plan_review_path=plan_review,
        article_review_path=article_review,
        agent_output_paths=paths["agent_outputs"],
        stage_receipt_paths=paths["stage_receipts"],
        workflow_mode="new",
        assembly_date="2026-08-11",
        workspace_root=tmp_path,
    )
    return bom, paths


def _check(bom: dict, paths: dict[str, Path], tmp_path: Path):
    return check_bom(
        bom,
        article_path=paths["article"],
        validation_sidecar_path=paths["sidecar"],
        workspace_root=tmp_path,
        expected_lifecycle_state="provisional",
    )


def _rules(findings: list[dict]) -> set[str]:
    return {str(row["rule_id"]) for row in findings}


def test_v4_binds_plan_fulfillment_index_and_computed_summaries(tmp_path: Path) -> None:
    bom, paths = _build(tmp_path)

    assert bom["schema"] == "simpro-blog-assembly-bom/v4"
    assert bom["artifacts"]["plan_fulfillment"]["sha256"] == _sha256(paths["plan_fulfillment"])
    assert bom["artifacts"]["commercial_pillar_index"]["sha256"] == _sha256(paths["commercial_pillar_index"])
    assert bom["editorial_plan_summary"]["meta"]["url_slug"] == "scheduling-guide"
    assert bom["editorial_fulfillment"][0]["actual_excerpt"] == EXCERPT
    assert _check(bom, paths, tmp_path) == []


def test_v4_rejects_hand_edited_editorial_fulfillment(tmp_path: Path) -> None:
    bom, paths = _build(tmp_path)
    bom["editorial_fulfillment"][0]["actual_excerpt"] = "Hand edited evidence."

    assert "bom_editorial_fulfillment_mismatch" in _rules(_check(bom, paths, tmp_path))


def test_v4_rejects_changed_article_or_index(tmp_path: Path) -> None:
    bom, paths = _build(tmp_path)
    paths["commercial_pillar_index"].write_text("{}\n", encoding="utf-8")

    assert "bom_commercial_pillar_index_hash_mismatch" in _rules(
        _check(bom, paths, tmp_path)
    )


@pytest.mark.parametrize("field", ["plan_fulfillment", "commercial_pillar_index"])
def test_v4_requires_new_bound_artifacts(tmp_path: Path, field: str) -> None:
    bom, paths = _build(tmp_path)
    bom["artifacts"][field] = None

    assert f"bom_{field}_missing" in _rules(_check(bom, paths, tmp_path))


def test_v4_rejects_legacy_editorial_plan(tmp_path: Path) -> None:
    paths = _fixture(tmp_path)
    plan_review, article_review = _reviews(tmp_path, paths)
    with pytest.raises(ValueError, match="current BOM construction requires simpro-blog-editorial-plan/v2"):
        build_blog_assembly_bom_from_files(
            article_path=paths["article"],
            validation_sidecar_path=paths["sidecar"],
            editorial_plan_path=paths["editorial_plan"],
            keyword_decision_path=paths["keyword_decision"],
            serp_evidence_path=paths["serp"],
            plan_fulfillment_path=paths["editorial_plan"],
            commercial_pillar_index_path=paths["keyword_decision"],
            plan_review_path=plan_review,
            article_review_path=article_review,
            paa_artifact_path=paths["paa"],
            agent_output_paths=paths["agent_outputs"],
            stage_receipt_paths=paths["stage_receipts"],
            workflow_mode="new",
            assembly_date="2026-08-11",
            workspace_root=tmp_path,
        )
