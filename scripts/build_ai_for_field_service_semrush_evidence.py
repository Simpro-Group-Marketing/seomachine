"""Build current keyword and SERP evidence for the AI field service rewrite."""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from data_sources.modules.blog_assembly_contract import atomic_write_json  # noqa: E402
from data_sources.modules.editorial_plan.serp_capture import build_serp_evidence  # noqa: E402
from data_sources.modules.execution_attestation import attest_mapping  # noqa: E402
from data_sources.modules.semrush_keyword_decision_guard import (  # noqa: E402
    SOURCE_BOUNDARY,
    build_keyword_decision,
)


DATE = "2026-09-29"
SLUG = "ai-for-field-service"
RUN_ID = "8edda1b8-e7b3-4d70-96ed-aa01505a4c95"
PRIMARY = "AI in field service management"
SECONDARIES = [
    "best AI-powered field service management software",
    "best AI-powered software for trades and field service companies",
]
UI_PATH = ROOT / "research" / f"semrush-ui-{SLUG}-{DATE}.txt"
RAW_PATH = ROOT / "research" / f"serp-raw-{SLUG}-{DATE}-web-search.json"
SERP_PATH = ROOT / "research" / f"serp-evidence-{SLUG}-{DATE}.json"
KEYWORD_PATH = ROOT / "research" / f"semrush-keyword-decision-{SLUG}-{DATE}.json"


SERP_RESULTS = [
    ("AI in Field Service Management: A Complete Guide", "https://www.salesforce.com/service/field-service-management/ai-field-service-management-guide/?bc=OTH"),
    ("The Guide to AI in Field Service Management", "https://www.ibm.com/think/insights/ai-in-field-service-management"),
    ("AI in Field Service Management: Boost Efficiency", "https://www.ifs.com/en/glossary/ai-in-field-service-management"),
    ("AI and the Next Frontier of Field Service", "https://www.bcg.com/publications/2025/the-next-frontier-of-field-service"),
    ("AI and Field Service Management", "https://www.totalmobile.com/field-service-management-software/ai-and-field-service-management/"),
    ("AI and Field Service Management Industry Guide", "https://www.servicepower.com/resources/industry-guides/ai-and-field-service-management"),
    ("Basic Principles of Artificial Intelligence in Field Service Management", "https://www.ecisolutions.com/blog/basic-principles-of-artificial-intelligence-in-field-service-management/"),
    ("How AI can give field service technicians a boost", "https://www.microsoft.com/en-us/worklab/guides/how-ai-can-give-field-service-technicians-a-boost"),
]


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def write_serp_evidence() -> dict[str, object]:
    raw = {
        "schema": "simpro-serp-raw-capture/v1",
        "collector": {"name": "research_serp_analysis:chrome_connector", "version": "1.0.0"},
        "query": PRIMARY,
        "collected_at": now_utc(),
        "run_id": RUN_ID,
        "request": {
            "url": "https://www.google.com/search?q=AI%20in%20field%20service%20management&hl=en&gl=us&pws=0",
            "locale": {"hl": "en", "gl": "us", "pws": "0"},
        },
        "raw_response": {
            "organic_results": [
                {"title": title, "url": url} for title, url in SERP_RESULTS
            ],
            "features": ["Ads", "AI Overview", "People also ask"],
            "provenance": {
                "execution_surface": "Chrome extension browser control in a fresh session named AI field service SERP",
                "query": PRIMARY,
                "collection_date": DATE,
                "market": "United States",
                "device": "Desktop",
                "result_scope": "eight visible organic results on page one",
                "personalization_status": "The query URL used pws=0; the signed-in page also exposed account-only Google Ads and Search Console panels, which were excluded from organic-result evidence.",
            },
        },
    }
    atomic_write_json(
        RAW_PATH,
        attest_mapping(raw, purpose="simpro-serp-raw-capture/v1", workspace_root=ROOT),
    )
    evidence = build_serp_evidence(
        raw_capture_path=RAW_PATH,
        workspace_root=ROOT,
        must_have_sections=[
            "Direct buyer answer for AI-powered field service management software",
            "Trade and field service company selection answer",
            "Demo-ready selection criteria table",
            "Qualified explanation of where Simpro fits",
            "Job-lifecycle use cases and measurement guidance",
            "Implementation, adoption, and human-oversight checks",
        ],
        competitor_gaps=[
            "The current results are dominated by broad educational guides. The existing Simpro URL can preserve that format while adding early commercial-selection utility instead of launching a competing listicle."
        ],
    )
    atomic_write_json(SERP_PATH, evidence)
    return evidence


def connector_reports(ui_hash: str) -> list[dict[str, object]]:
    common = {
        "execution_surface": "semrush_ui_chrome_main_browser",
        "database": "us",
        "device": "desktop",
        "collection_date": DATE,
        "ui_evidence_path": UI_PATH.relative_to(ROOT).as_posix(),
        "ui_evidence_sha256": ui_hash,
    }
    parameters = {
        "_keyword_research": {**common, "query": PRIMARY},
        "_get_report_schema": {**common, "report": "phrase_this"},
        "phrase_these": {**common, "keywords": [PRIMARY, *SECONDARIES]},
        "phrase_related": {**common, "phrase": PRIMARY},
        "phrase_questions": {**common, "phrase": PRIMARY, "ui_result": "1 question, total volume 0"},
        "phrase_organic": {
            **common,
            "phrase": PRIMARY,
            "serp_capture_date": DATE,
            "serp_evidence_path": SERP_PATH.relative_to(ROOT).as_posix(),
            "display_limit": 10,
        },
        "phrase_this": {**common, "phrase": PRIMARY},
    }
    return [
        {
            "report": report,
            "status": "completed",
            "parameters": values,
            "completion_basis": "Authenticated Semrush US desktop Keyword Overview observed through the installed Chrome extension control surface in the user's main Chrome profile.",
        }
        for report, values in parameters.items()
    ]


def main() -> int:
    serp = write_serp_evidence()
    ui_hash = hashlib.sha256(UI_PATH.read_bytes()).hexdigest()
    candidates = [
        {
            "keyword": PRIMARY,
            "volume": 260,
            "global_volume": 450,
            "keyword_difficulty": 34,
            "keyword_difficulty_label": "Possible",
            "intent": ["informational"],
            "cpc": 28.48,
            "competitive_density": 0.01,
        },
        {"keyword": SECONDARIES[0], "volume": None, "keyword_difficulty": None},
        {"keyword": SECONDARIES[1], "volume": None, "keyword_difficulty": None},
        {"keyword": "ai software for field service management in trades", "volume": 20, "keyword_difficulty": None},
        {"keyword": "best ai for hvac in field service management platforms", "volume": 70, "keyword_difficulty": None},
    ]
    serp_rows = [
        {
            "position": row["position"],
            "position_type": "organic",
            "domain": urlparse(row["url"]).netloc.removeprefix("www."),
            "url": row["url"],
            "triggered_serp_features": [],
        }
        for row in serp["results"]
    ]
    decision = build_keyword_decision(
        brand="Simpro",
        market="US",
        database="us",
        collection_date=DATE,
        source_boundary=SOURCE_BOUNDARY,
        seed_terms=[PRIMARY, *SECONDARIES, "ai software for field service management in trades"],
        connector_reports=connector_reports(ui_hash),
        candidate_metrics=candidates,
        serp_finalists=[{"keyword": PRIMARY, "database": "us", "results": serp_rows}],
        question_candidates=[],
        related_candidates=[
            {"keyword": "ai software for field service management in trades", "volume": 20, "keyword_difficulty": None},
            {"keyword": "best ai for hvac in field service management platforms", "volume": 70, "keyword_difficulty": None},
        ],
        selected_primary_keyword=PRIMARY,
        selected_secondary_keywords=SECONDARIES,
        rejected_keywords=[
            {
                "keyword": "field service management software",
                "reason": "Reserved for the verified US homepage commercial pillar; this blog owns AI education and AI-powered software evaluation.",
            },
            {
                "keyword": "best field service management software",
                "reason": "The existing generic comparison article retains non-AI FSM selection intent.",
            },
        ],
        selection_rationale=(
            "The authenticated Semrush US desktop UI dated September 29, 2026 shows 260 US volume, KD 34, and informational intent for AI in field service management. The first requested best-software prompt has no direct exact-query metrics but has nine variations with total volume 10; the second exact prompt returns Nothing found. A related trades query has volume 20. Current search results are dominated by educational AI-in-FSM guides. Preserve the established primary topic, add both requested prompts as secondary commercial-investigation targets, and update the existing URL instead of creating a competing article."
        ),
        workspace_root=ROOT,
    )
    atomic_write_json(KEYWORD_PATH, decision)
    print(json.dumps({
        "keyword_decision": KEYWORD_PATH.relative_to(ROOT).as_posix(),
        "keyword_evidence_hash": decision["evidence_hash"],
        "serp_evidence": SERP_PATH.relative_to(ROOT).as_posix(),
        "serp_evidence_hash": serp["evidence_hash"],
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
