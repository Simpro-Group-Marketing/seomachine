from __future__ import annotations

import json
from pathlib import Path

from data_sources.modules import semrush_keyword_decision_guard


def _rule_ids(findings):
    return {finding["rule_id"] for finding in findings}


def _write_json(path: Path, payload: object) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def _article(path: Path, *, primary_keyword: str = "field service scheduling") -> Path:
    path.write_text(
        "---\n"
        "artifact_type: blog\n"
        "brand: Simpro\n"
        "title: Field service scheduling guide\n"
        "objective: Help operations leaders choose a scheduling workflow.\n"
        "audience: Field service operations leaders\n"
        "region: US\n"
        "last_updated: 2026-08-11\n"
        f"primary_keyword: {primary_keyword}\n"
        "secondary_keywords:\n"
        "  - dispatch capacity\n"
        "---\n"
        "# Field service scheduling guide\n\n"
        "Field service scheduling guidance for dispatch capacity decisions.\n",
        encoding="utf-8",
    )
    return path


def _plan(path: Path, *, primary_keyword: str = "field service scheduling") -> Path:
    return _write_json(
        path,
        {
            "schema": "simpro-blog-editorial-plan/v1",
            "topic": "Field service scheduling",
            "date": "2026-08-11",
            "meta": {
                "title_options": ["Field Service Scheduling Guide"],
                "meta_title": "Field Service Scheduling Guide | Simpro",
                "meta_description": "A practical guide to field service scheduling decisions.",
                "url_slug": "field-service-scheduling-guide",
                "primary_keyword": primary_keyword,
                "secondary_keywords": ["dispatch capacity"],
            },
            "keyword_decision": {
                "status": "resolved",
                "artifact_schema": "simpro-semrush-keyword-decision/v1",
                "source": "semrush_connector",
                "database": "us",
                "selected_primary_keyword": primary_keyword,
                "selected_secondary_keywords": ["dispatch capacity"],
                "selection_rationale": "Intent fit is stronger than adjacent schedule software terms.",
            },
        },
    )


def _decision_payload(*, primary_keyword: str = "field service scheduling", collection_date: str = "2026-08-11"):
    return semrush_keyword_decision_guard.build_keyword_decision(
        brand="Simpro",
        market="US",
        database="us",
        collection_date=collection_date,
        source_boundary=semrush_keyword_decision_guard.SOURCE_BOUNDARY,
        seed_terms=["field service scheduling", "dispatch capacity"],
        connector_reports=[
            {
                "report": "_keyword_research",
                "parameters": {},
                "status": "completed",
            },
            {
                "report": "_get_report_schema",
                "parameters": {"report": "phrase_these"},
                "status": "completed",
            },
            {
                "report": "phrase_these",
                "parameters": {
                    "phrase": "field service scheduling;dispatch capacity",
                    "database": "us",
                    "export_columns": "keyword,volume,cpc,competitive_density,results,trend,intent,keyword_difficulty",
                },
                "status": "completed",
            },
            {
                "report": "phrase_related",
                "parameters": {"phrase": "field service scheduling", "database": "us"},
                "status": "completed",
            },
            {
                "report": "phrase_questions",
                "parameters": {"phrase": "field service scheduling", "database": "us"},
                "status": "completed",
            },
            {
                "report": "phrase_organic",
                "parameters": {"phrase": "field service scheduling", "database": "us", "display_limit": 20},
                "status": "completed",
            },
            {
                "report": "phrase_this",
                "parameters": {"phrase": primary_keyword, "database": "us"},
                "status": "completed",
            },
        ],
        candidate_metrics=[
            {
                "keyword": primary_keyword,
                "volume": 720,
                "keyword_difficulty": 32,
                "cpc": 18.5,
                "competitive_density": 0.12,
                "results": 1000000,
                "trend": [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
                "intent": "commercial",
            },
            {
                "keyword": "dispatch capacity",
                "volume": 90,
                "keyword_difficulty": 24,
                "cpc": 8.2,
                "competitive_density": 0.04,
                "results": 250000,
                "trend": [1, 1, 1],
                "intent": "informational",
            },
        ],
        serp_finalists=[
            {
                "keyword": primary_keyword,
                "database": "us",
                "results": [
                    {
                        "position": 1,
                        "position_type": "organic",
                        "domain": "example.com",
                        "url": "https://example.com/field-service-scheduling",
                        "triggered_serp_features": ["featured_snippet"],
                    }
                ],
            }
        ],
        question_candidates=[
            {
                "keyword": "how do field service teams schedule work",
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
        selected_primary_keyword=primary_keyword,
        selected_secondary_keywords=["dispatch capacity"],
        rejected_keywords=[
            {
                "keyword": "employee scheduling software",
                "reason": "Different buyer and page ownership lane.",
            }
        ],
        selection_rationale="Intent fit, page ownership, and SERP feasibility support the selected target.",
    )


def _decision(path: Path, **kwargs) -> Path:
    return _write_json(path, _decision_payload(**kwargs))


def test_guard_rejects_missing_artifact(tmp_path: Path):
    findings = semrush_keyword_decision_guard.check_file(tmp_path / "missing.json")

    assert _rule_ids(findings) == {"semrush_keyword_decision_missing"}


def test_guard_rejects_stale_collection_date(tmp_path: Path):
    decision = _decision(tmp_path / "decision.json", collection_date="2026-08-10")

    findings = semrush_keyword_decision_guard.check_file(decision, assembly_date="2026-08-11")

    assert "semrush_keyword_decision_stale" in _rule_ids(findings)


def test_guard_rejects_missing_selected_primary_keyword(tmp_path: Path):
    payload = _decision_payload()
    payload["selected_primary_keyword"] = ""
    decision = _write_json(tmp_path / "decision.json", payload)

    findings = semrush_keyword_decision_guard.check_file(decision, assembly_date="2026-08-11")

    assert "semrush_keyword_decision_primary_missing" in _rule_ids(findings)


def test_guard_rejects_selected_keyword_without_candidate_metrics(tmp_path: Path):
    payload = _decision_payload(primary_keyword="field scheduling software")
    payload["candidate_metrics"] = [
        row for row in payload["candidate_metrics"] if row["keyword"] != "field scheduling software"
    ]
    decision = _write_json(tmp_path / "decision.json", payload)

    findings = semrush_keyword_decision_guard.check_file(decision, assembly_date="2026-08-11")

    assert "semrush_keyword_decision_primary_unmeasured" in _rule_ids(findings)


def test_guard_rejects_editorial_plan_article_keyword_mismatch(tmp_path: Path):
    article = _article(tmp_path / "article.md")
    plan = _plan(tmp_path / "editorial-plan.json", primary_keyword="job scheduling software")
    decision = _decision(tmp_path / "decision.json")

    findings = semrush_keyword_decision_guard.check_file(
        decision,
        article_path=article,
        editorial_plan_path=plan,
        assembly_date="2026-08-11",
    )

    assert "semrush_keyword_decision_plan_primary_mismatch" in _rule_ids(findings)


def test_guard_accepts_valid_keyword_decision(tmp_path: Path):
    article = _article(tmp_path / "article.md")
    plan = _plan(tmp_path / "editorial-plan.json")
    decision = _decision(tmp_path / "decision.json")

    findings = semrush_keyword_decision_guard.check_file(
        decision,
        article_path=article,
        editorial_plan_path=plan,
        assembly_date="2026-08-11",
    )

    assert findings == []


def test_brand_market_defaults_document_simpro_clockshark_bigchange_and_aroflo():
    assert semrush_keyword_decision_guard.default_databases_for_brand_market("Simpro", "US") == ("us",)
    assert semrush_keyword_decision_guard.default_databases_for_brand_market("ClockShark", "US") == ("us",)
    assert semrush_keyword_decision_guard.default_databases_for_brand_market("BigChange", "UK") == ("uk",)
    assert semrush_keyword_decision_guard.default_databases_for_brand_market("AroFlo", "ANZ") == ("au", "nz")
