from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from data_sources.modules.blog_assembly_contract import atomic_write_json
from data_sources.modules.editorial_plan_guard import build_serp_evidence
from data_sources.modules.execution_attestation import attest_mapping
from data_sources.modules.paa_provenance_guard import (
    build_answersocrates_artifact,
    write_answersocrates_artifact,
)
from data_sources.modules.semrush_keyword_decision_guard import (
    SOURCE_BOUNDARY,
    build_keyword_decision,
)


SLUG = "ai-field-service-economics"
FILE_DATE = "2026-09-08"
COLLECTION_DATE = "2026-09-09"
RUN_ID = "blog-run-ae3ae7605f4f7f839cfa59730c8b0c0297136f4618ba041b2959a49bab37b497"
EXECUTION_SURFACE = "semrush_ui_chrome_main_browser"

SEMRUSH_RAW_PATH = ROOT / "research" / f"raw-semrush-ui-{SLUG}-{FILE_DATE}.json"
KEYWORD_PATH = ROOT / "research" / f"keyword-decision-{SLUG}-{FILE_DATE}.json"
SERP_RAW_PATH = ROOT / "research" / f"raw-serp-{SLUG}-{FILE_DATE}.json"
SERP_PATH = ROOT / "research" / f"serp-evidence-{SLUG}-{FILE_DATE}.json"
PAA_RAW_PATH = ROOT / "research" / f"raw-answersocrates-{SLUG}-{FILE_DATE}.json"
PAA_PATH = ROOT / "research" / f"answersocrates-{SLUG}-{FILE_DATE}.json"
FRED_PATH = ROOT / "research" / f"fred-transcript-review-{SLUG}-{FILE_DATE}.json"
FRED_TRANSCRIPT_PATH = ROOT / "research" / f"raw-fred-{SLUG}-{FILE_DATE}.vtt"


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def keyword_metric(
    keyword: str,
    *,
    volume: int | None,
    difficulty: int | None,
    cpc: float | None,
    density: float | None,
    results: int | None,
    intent: str | None,
) -> dict:
    return {
        "keyword": keyword,
        "volume": volume,
        "keyword_difficulty": difficulty,
        "cpc": cpc,
        "competitive_density": density,
        "results": results,
        "trend": [],
        "intent": intent,
    }


def build_semrush_evidence() -> tuple[dict, dict]:
    raw_payload = {
        "schema": "simpro-semrush-chrome-ui-capture/v1",
        "execution_surface": EXECUTION_SURFACE,
        "browser": "Chrome main window",
        "market": "US",
        "database": "us",
        "device": "Desktop",
        "ui_date": COLLECTION_DATE,
        "recorded_at": now_utc(),
        "records": [
            {
                "keyword": "ai field service economics",
                "url": "https://www.semrush.com/analytics/keywordoverview/?q=ai+field+service+economics&db=us",
                "volume": None,
                "keyword_difficulty": 41,
                "intent": "informational",
                "cpc": None,
                "competitive_density": None,
                "observation": "The UI displayed volume n/a and KD 41. Treat volume as unmeasured, not zero.",
            },
            {
                "keyword": "ai field service management",
                "url": "https://www.semrush.com/analytics/keywordoverview/?q=ai+field+service+management&db=us",
                "volume": 260,
                "keyword_difficulty": 17,
                "intent": "informational",
                "cpc": 17.70,
                "competitive_density": 0.11,
                "global_volume": 370,
                "results": 125,
                "serp_features": ["Sitelinks", "AI Overview", "Reviews", "Video"],
                "variations": [
                    {"keyword": "ai in field service management", "volume": 260, "keyword_difficulty": 34},
                    {"keyword": "field service management ai", "volume": 260, "keyword_difficulty": 34},
                    {"keyword": "best ai for hvac in field service management platforms", "volume": 70, "keyword_difficulty": None},
                    {"keyword": "ai field service management software", "volume": 30, "keyword_difficulty": None},
                ],
                "questions": [
                    {"keyword": "how is ai transforming field service management", "volume": 20, "keyword_difficulty": None},
                    {"keyword": "how ai is changing field service management", "volume": 10, "keyword_difficulty": None},
                    {"keyword": "what is agentic ai in field service management", "volume": 0, "keyword_difficulty": None},
                ],
            },
            {
                "keyword": "field service automation",
                "url": "https://www.semrush.com/analytics/keywordoverview/?q=field+service+automation&db=us",
                "volume": 590,
                "keyword_difficulty": 12,
                "intent": "informational",
                "cpc": 22.79,
                "competitive_density": 0.13,
                "global_volume": 1100,
                "ads": 6,
            },
            {
                "keyword": "ai for field service",
                "url": "https://www.semrush.com/analytics/keywordoverview/?q=ai+for+field+service&db=us",
                "volume": 90,
                "keyword_difficulty": 32,
                "intent": "informational",
                "cpc": 29.13,
                "competitive_density": 0.13,
                "global_volume": 150,
            },
            {
                "keyword": "ai field service software",
                "url": "https://www.semrush.com/analytics/keywordoverview/?q=ai+field+service+software&db=us",
                "volume": 40,
                "keyword_difficulty": 30,
                "intent": "informational",
                "cpc": 17.16,
                "competitive_density": 0.46,
                "global_volume": 90,
            },
            {
                "keyword": "field service profitability",
                "url": "https://www.semrush.com/analytics/keywordoverview/?q=field+service+profitability&db=us",
                "volume": 10,
                "keyword_difficulty": None,
                "intent": None,
                "cpc": 0.0,
                "competitive_density": 0.0,
                "global_volume": 10,
                "observation": "The UI displayed keyword difficulty n/a, not zero.",
            },
        ],
        "serp_results": [
            {"position": 1, "url": "https://www.totalmobile.com/field-service-management-software/ai-and-field-service-management/", "domain": "totalmobile.com"},
            {"position": 2, "url": "https://www.salesforce.com/service/field-service-management/ai-field-service-management-guide/", "domain": "salesforce.com"},
            {"position": 3, "url": "https://www.ibm.com/think/insights/ai-in-field-service-management", "domain": "ibm.com"},
            {"position": 4, "url": "https://www.ifs.com/en/insights/assets/three-practical-ai-approaches-for-fsm", "domain": "ifs.com"},
            {"position": 5, "url": "https://www.microsoft.com/en-us/worklab/guides/how-ai-can-give-field-service-technicians-a-boost", "domain": "microsoft.com"},
            {"position": 6, "url": "https://www.fieldproxy.ai/resources/blog/top-10-ai-powered-field-service-management-solutions", "domain": "fieldproxy.ai"},
            {"position": 7, "url": "https://www.overit.ai/blog/generative-ai-in-field-service-management/", "domain": "overit.ai"},
            {"position": 8, "url": "https://www.bcg.com/x/product-library/field-service-ai", "domain": "bcg.com"},
            {"position": 9, "url": "https://www.simprogroup.com/blog/ai-for-field-service", "domain": "simprogroup.com"},
            {"position": 10, "url": "https://www.bcg.com/x/product-library/field-service-ai", "domain": "bcg.com"},
        ],
    }
    atomic_write_json(
        SEMRUSH_RAW_PATH,
        attest_mapping(
            raw_payload,
            purpose="simpro-semrush-chrome-ui-capture/v1",
            workspace_root=ROOT,
        ),
    )
    raw_hash = file_sha256(SEMRUSH_RAW_PATH)
    evidence_parameters = {
        "execution_surface": EXECUTION_SURFACE,
        "evidence_path": SEMRUSH_RAW_PATH.relative_to(ROOT).as_posix(),
        "evidence_sha256": raw_hash,
    }
    reports = [
        {"report": "_keyword_research", "parameters": dict(evidence_parameters), "status": "completed"},
        {"report": "_get_report_schema", "parameters": {**evidence_parameters, "reports": "phrase_these,phrase_related,phrase_questions,phrase_organic,phrase_this"}, "status": "completed"},
        {"report": "phrase_these", "parameters": {**evidence_parameters, "phrase": "ai field service management;field service automation;ai for field service;ai field service software;field service profitability;ai field service economics", "database": "us"}, "status": "completed"},
        {"report": "phrase_related", "parameters": {**evidence_parameters, "phrase": "ai field service management", "database": "us"}, "status": "completed"},
        {"report": "phrase_questions", "parameters": {**evidence_parameters, "phrase": "ai field service management", "database": "us"}, "status": "completed"},
        {"report": "phrase_organic", "parameters": {**evidence_parameters, "phrase": "ai field service management", "database": "us", "display_limit": 10}, "status": "completed"},
        {"report": "phrase_this", "parameters": {**evidence_parameters, "phrase": "ai field service economics", "database": "us"}, "status": "completed"},
    ]
    candidates = [
        keyword_metric("ai field service management", volume=260, difficulty=17, cpc=17.70, density=0.11, results=125, intent="informational"),
        keyword_metric("field service automation", volume=590, difficulty=12, cpc=22.79, density=0.13, results=None, intent="informational"),
        keyword_metric("ai for field service", volume=90, difficulty=32, cpc=29.13, density=0.13, results=None, intent="informational"),
        keyword_metric("ai field service software", volume=40, difficulty=30, cpc=17.16, density=0.46, results=None, intent="informational"),
        keyword_metric("field service profitability", volume=10, difficulty=None, cpc=0.0, density=0.0, results=None, intent=None),
        keyword_metric("ai field service economics", volume=None, difficulty=41, cpc=None, density=None, results=None, intent="informational"),
    ]
    serp_rows = [
        {
            "position": row["position"],
            "position_type": "organic",
            "domain": row["domain"],
            "url": row["url"],
            "triggered_serp_features": [],
        }
        for row in raw_payload["serp_results"]
    ]
    decision = build_keyword_decision(
        brand="Simpro",
        market="US",
        database="us",
        collection_date=COLLECTION_DATE,
        source_boundary=SOURCE_BOUNDARY,
        seed_terms=[
            "ai field service economics",
            "ai field service management",
            "field service automation",
            "ai for field service",
            "ai field service software",
            "field service profitability",
        ],
        connector_reports=reports,
        candidate_metrics=candidates,
        serp_finalists=[{"keyword": "ai field service management", "database": "us", "results": serp_rows}],
        question_candidates=[
            {"keyword": "how is ai transforming field service management", "volume": 20, "keyword_difficulty": None, "intent": "informational"},
            {"keyword": "how ai is changing field service management", "volume": 10, "keyword_difficulty": None, "intent": "informational"},
            {"keyword": "what is agentic ai in field service management", "volume": 0, "keyword_difficulty": None, "intent": "informational"},
        ],
        related_candidates=[
            {"keyword": "ai in field service management", "volume": 260, "keyword_difficulty": 34, "relevance": 0.95, "intent": "informational"},
            {"keyword": "field service management ai", "volume": 260, "keyword_difficulty": 34, "relevance": 0.90, "intent": "informational"},
            {"keyword": "ai field service management software", "volume": 30, "keyword_difficulty": None, "relevance": 0.85, "intent": "informational"},
        ],
        selected_primary_keyword="ai field service management",
        selected_secondary_keywords=[
            "field service automation",
            "ai for field service",
            "ai field service software",
            "field service profitability",
        ],
        rejected_keywords=[
            {"keyword": "ai field service economics", "reason": "Semrush displayed US volume n/a and KD 41. Treat the phrase as an unmeasured emerging AEO topic, not a zero-volume SEO target."},
            {"keyword": "field service automation", "reason": "The existing Simpro automation article owns broad end-to-end workflow automation intent."},
        ],
        selection_rationale="Use the measurable informational phrase for supporting SEO discovery while the page owns the distinct economics decision framework. Treat AI field service economics as an emerging AEO topic with unmeasured US volume and a displayed KD of 41.",
        workspace_root=ROOT,
    )
    atomic_write_json(KEYWORD_PATH, decision)
    return raw_payload, decision


def build_serp_artifact(semrush_payload: dict) -> dict:
    raw_results = [
        {
            "url": row["url"],
            "title": row["url"],
        }
        for row in semrush_payload["serp_results"]
    ]
    raw_capture = {
        "schema": "simpro-serp-raw-capture/v1",
        "collector": {"name": "research_serp_analysis:semrush", "version": "1.0.0"},
        "query": "ai field service management",
        "collected_at": now_utc(),
        "run_id": RUN_ID,
        "request": {
            "url": "semrush://keyword/phrase_organic",
            "locale": {"database": "us"},
        },
        "raw_response": {
            "organic_results": raw_results,
            "features": ["Sitelinks", "AI Overview", "Reviews", "Video"],
        },
    }
    atomic_write_json(
        SERP_RAW_PATH,
        attest_mapping(
            raw_capture,
            purpose="simpro-serp-raw-capture/v1",
            workspace_root=ROOT,
        ),
    )
    evidence = build_serp_evidence(
        raw_capture_path=SERP_RAW_PATH,
        workspace_root=ROOT,
        must_have_sections=[
            "Direct answer",
            "AI field service economics scorecard",
            "Reader-supplied business-case worksheet",
            "30-day pilot",
        ],
        competitor_gaps=[
            "The observed SERP is dominated by broad AI field service guides; this article should own the narrower economics decision framework."
        ],
    )
    atomic_write_json(SERP_PATH, evidence)
    return evidence


def build_paa_evidence() -> dict:
    browser_output = {
        "page_url": "https://answersocrates.com/",
        "page_title": "Answer Socrates: Free Question Keyword Research Tool Generator",
        "body_text": (
            "AI field service economics 109 questions generated\n"
            "Country: United States\nLanguage: English\n"
            "People Also Asked\n"
            "What is a $900000 AI job?\n"
            "Which 3 jobs will not survive AI?\n"
            "What is the 30% rule in AI?\n"
            "What is the 10/20-70 rule for AI?\n"
            "All Results 266\nGoogle Search 242\nAI Prompts 24\n"
            "Questions 32 questions"
        ),
        "sections": [
            {
                "heading": "People Also Ask",
                "items": [
                    "What is a $900000 AI job?",
                    "Which 3 jobs will not survive AI?",
                    "What is the 30% rule in AI?",
                    "What is the 10/20-70 rule for AI?",
                ],
            },
            {
                "heading": "Visible question suggestions",
                "items": [
                    "Are AI specialists in demand",
                    "AI and field service",
                    "Artificial intelligence in field service management",
                    "Can AI do economics",
                    "How to use AI for economic analysis",
                    "How does AI affect the service industry",
                ],
            },
        ],
        "blocker_observations": [],
    }
    raw_capture = {
        "schema": "simpro-answersocrates-chrome-connector-capture/v1",
        "collector": {"name": "answersocrates_chrome_connector", "version": "1.0.0"},
        "query": "AI field service economics",
        "run_id": RUN_ID,
        "started_at": now_utc(),
        "completed_at": now_utc(),
        "page_url": "https://answersocrates.com/",
        "raw_response": {
            "stdout": json.dumps(browser_output, ensure_ascii=False),
            "stderr": "",
            "returncode": 0,
        },
    }
    atomic_write_json(
        PAA_RAW_PATH,
        attest_mapping(
            raw_capture,
            purpose="simpro-answersocrates-chrome-connector-capture/v1",
            workspace_root=ROOT,
        ),
    )
    artifact = build_answersocrates_artifact(
        raw_capture_path=PAA_RAW_PATH,
        workspace_root=ROOT,
        expected_query="AI field service economics",
        expected_collection_date=COLLECTION_DATE,
        expected_run_id=RUN_ID,
    )
    write_answersocrates_artifact(PAA_PATH, artifact, workspace_root=ROOT)
    return artifact


def build_fred_transcript_review() -> dict:
    transcript_hash = file_sha256(FRED_TRANSCRIPT_PATH)
    payload = {
        "schema": "simpro-fred-transcript-review/v1",
        "reviewed_at": now_utc(),
        "video": {
            "title": "How Simpro and AI is Reshaping Field Service Economics",
            "public_url": "https://www.youtube.com/watch?v=GU0pqwFXo4Q",
            "asana_attachment_gid": "1217345670211998",
            "transcript_path": FRED_TRANSCRIPT_PATH.relative_to(ROOT).as_posix(),
            "transcript_sha256": transcript_hash,
            "review_scope": "Full attached VTT transcript, approximately 00:00 through 37:47.",
        },
        "source_safe_topics": [
            {"timestamp": "00:01:20-00:03:18", "support": "AI depends on usable data and can help with scheduling, skills matching, routing, materials, preparation, and revisit risk."},
            {"timestamp": "00:03:18-00:04:11", "support": "Captured field activity can become usable records and reduce avoidable office coordination."},
            {"timestamp": "00:06:53-00:10:12", "support": "Operational opportunities vary by workflow and include planning, inventory, routing, analytics, documentation, and job preparation."},
            {"timestamp": "00:20:36-00:23:50", "support": "AI-assisted documentation should be reviewed by a person, while better preparation and streamlined handoffs can reduce avoidable work."},
        ],
        "excluded_claims": [
            {"timestamp": "00:04:11-00:05:40", "reason": "Unvalidated average-margin and profit-multiplier claims."},
            {"timestamp": "00:08:48-00:09:20", "reason": "Unvalidated margin-point and efficiency claims."},
            {"timestamp": "00:12:20-00:19:45", "reason": "Product-status, roadmap, scale, materials-revenue, pricing, and margin claims are not approved for public use here."},
            {"timestamp": "00:21:21-00:22:32", "reason": "Unvalidated 95 percent documentation and additional-jobs-per-day claims."},
            {"timestamp": "00:24:24-00:36:58", "reason": "Forecasts, productivity multiples, 100 percent efficiency, customer counts, and competitive-outcome claims are not validated for this article."},
        ],
        "public_use_decision": {
            "exact_quote": "none",
            "paraphrase": "none",
            "video_link": "required by the bound brief and retained in the lead video placeholder",
            "authority_boundary": "The Fred selector remains authoritative for public quote or paraphrase eligibility. Transcript review does not override a selector no-selection.",
        },
    }
    atomic_write_json(FRED_PATH, payload)
    return payload


def main() -> None:
    semrush_payload, keyword_decision = build_semrush_evidence()
    serp_evidence = build_serp_artifact(semrush_payload)
    paa_evidence = build_paa_evidence()
    fred_review = build_fred_transcript_review()
    print(json.dumps({
        "semrush_raw": SEMRUSH_RAW_PATH.relative_to(ROOT).as_posix(),
        "keyword_decision": KEYWORD_PATH.relative_to(ROOT).as_posix(),
        "keyword_evidence_hash": keyword_decision["evidence_hash"],
        "serp_evidence": SERP_PATH.relative_to(ROOT).as_posix(),
        "serp_evidence_hash": serp_evidence["evidence_hash"],
        "paa_artifact": PAA_PATH.relative_to(ROOT).as_posix(),
        "paa_status": paa_evidence["status"],
        "fred_transcript_review": FRED_PATH.relative_to(ROOT).as_posix(),
        "fred_transcript_sha256": fred_review["video"]["transcript_sha256"],
    }, indent=2))


if __name__ == "__main__":
    main()
