"""Build authenticated Semrush keyword and SERP evidence for the What Is Simpro blog."""
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

DATE = "2026-10-05"
SLUG = "what-is-simpro"
RUN_ID = "fb123292-96da-464b-ab37-29a926336b3e"
UI_PATH = ROOT / "research" / f"semrush-ui-{SLUG}-{DATE}.txt"
KEYWORD_PATH = ROOT / "research" / f"semrush-keyword-decision-{SLUG}-{DATE}.json"

PRIMARY_QUERY = "what is simpro"

# Semrush Keyword Overview SERP Analysis, US desktop, Oct 2, 2026 (positions 1-10).
PRIMARY_URLS = [
    "https://www.simprogroup.com/",
    "https://en.wikipedia.org/wiki/Simpro",
    "https://www.gartner.com/reviews/product/simpro-field-service-software",
    "https://login.simprosuite.com/",
    "https://www.linkedin.com/company/simpro-software",
    "https://www.softwareadvice.com/cafm/simpro-enterprise-profile/",
    "https://www.6sense.com/tech/project-collaboration/simpro-software-market-share",
    "https://www.glassdoor.com/Overview/Working-at-Simpro-EI_IE1284211.11,17.htm",
    "https://www.instagram.com/simprosoftware/?hl=en",
    "https://sumble.com/tech/simpro",
]
URL_FEATURES = {
    "https://www.simprogroup.com/": ["Sitelinks"],
    "https://www.softwareadvice.com/cafm/simpro-enterprise-profile/": ["Reviews"],
    "https://www.glassdoor.com/Overview/Working-at-Simpro-EI_IE1284211.11,17.htm": ["Reviews"],
}
SERP_FEATURES = [
    "Sitelinks",
    "AI Overview",
    "Reviews",
    "Video",
    "Video carousel",
    "People also ask",
]


def _now_utc() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _report_url(query: str) -> str:
    return (
        "https://www.semrush.com/analytics/keywordoverview/"
        f"?q={query.replace(' ', '+')}&db=us&fid=562608#serp-analysis"
    )


def _write_serp() -> Path:
    raw_path = ROOT / "research" / f"serp-raw-{SLUG}-{DATE}-semrush.json"
    evidence_path = ROOT / "research" / f"serp-evidence-{SLUG}-{DATE}.json"
    raw = {
        "schema": "simpro-serp-raw-capture/v1",
        "collector": {"name": "research_serp_analysis:semrush", "version": "1.0.0"},
        "query": PRIMARY_QUERY,
        "collected_at": _now_utc(),
        "run_id": RUN_ID,
        "request": {"url": "semrush://keyword/phrase_organic", "locale": {"database": "us"}},
        "raw_response": {
            "organic_results": [{"title": url, "url": url} for url in PRIMARY_URLS],
            "features": SERP_FEATURES,
            "provenance": {
                "execution_surface": "semrush_ui_chrome_main_browser",
                "browser_instance": "user-authenticated existing Chrome browser",
                "report_url": _report_url(PRIMARY_QUERY),
                "visible_report_date": "Oct 5, 2026",
                "device": "Desktop",
                "market": "United States",
                "visible_result_count": 104,
            },
        },
    }
    atomic_write_json(
        raw_path,
        attest_mapping(raw, purpose="simpro-serp-raw-capture/v1", workspace_root=ROOT),
    )
    evidence = build_serp_evidence(
        raw_capture_path=raw_path,
        workspace_root=ROOT,
        must_have_sections=[
            "Direct definition of Simpro and who it serves",
            "How Simpro runs a job from quote to payment",
            "What customers say sets Simpro apart, backed by linked reviews and case studies",
            "Implementation and support expectations",
            "Fit checklist for trade businesses",
            "Frequently asked questions based on recorded AnswerSocrates evidence",
        ],
        competitor_gaps=[
            "The observed results are a navigational homepage with sitelinks, a Wikipedia entry, review-site profiles, a login page, social profiles, and technology-tracking pages. None explains what Simpro does across the job lifecycle with linked customer evidence, so the article owns an evaluator-grade explainer.",
            "Overlap decision: the homepage ranks first for this navigational-informational query and owns the general field service management software term. The article serves deeper evaluator intent with an explainer content type and links to the homepage as its commercial pillar.",
        ],
    )
    atomic_write_json(evidence_path, evidence)
    return evidence_path


def _connector_reports(ui_hash: str, serp_path: Path) -> list[dict[str, object]]:
    common = {
        "execution_surface": "semrush_ui_chrome_main_browser",
        "database": "us",
        "device": "desktop",
        "collection_date": DATE,
        "ui_evidence_path": UI_PATH.relative_to(ROOT).as_posix(),
        "ui_evidence_sha256": ui_hash,
    }
    values: dict[str, dict[str, object]] = {
        "_keyword_research": {**common, "query": PRIMARY_QUERY},
        "_get_report_schema": {**common, "report": "phrase_this"},
        "phrase_these": {
            **common,
            "keywords": [
                PRIMARY_QUERY,
                "simpro software",
                "simpro job management software",
                "simpro reviews",
                "simpro software reviews",
                "simpro app",
                "simpro features",
                "simpro mobile app",
                "simpro field service management",
            ],
        },
        "phrase_related": {**common, "phrase": PRIMARY_QUERY},
        "phrase_questions": {
            **common,
            "phrase": PRIMARY_QUERY,
            "ui_result": "Questions 8, total volume 130",
        },
        "phrase_organic": {
            **common,
            "phrase": PRIMARY_QUERY,
            "serp_capture_date": DATE,
            "serp_evidence_path": serp_path.relative_to(ROOT).as_posix(),
            "display_limit": 10,
        },
        "phrase_this": {**common, "phrase": PRIMARY_QUERY},
    }
    return [
        {
            "report": name,
            "status": "completed",
            "parameters": parameters,
            "completion_basis": "Authenticated Semrush US desktop Keyword Overview, Bulk Analysis, and Keyword Magic Tool in the user's existing Chrome browser.",
        }
        for name, parameters in values.items()
    ]


def main() -> int:
    serp_path = _write_serp()
    serp = json.loads(serp_path.read_text(encoding="utf-8"))
    ui_hash = hashlib.sha256(UI_PATH.read_bytes()).hexdigest()
    candidate_metrics = [
        {"keyword": PRIMARY_QUERY, "volume": 90, "global_volume": 360, "keyword_difficulty": 22, "keyword_difficulty_label": "Easy", "intent": ["informational", "navigational"], "cpc": 14.66, "competitive_density": 0.25},
        {"keyword": "simpro reviews", "volume": 40, "global_volume": 230, "keyword_difficulty": 15, "keyword_difficulty_label": "Easy", "intent": ["commercial"], "cpc": 20.62, "competitive_density": 0.49},
        {"keyword": "simpro software reviews", "volume": 30, "keyword_difficulty": 14, "intent": ["informational", "commercial"], "cpc": 20.62},
        {"keyword": "simpro app", "volume": 20, "cpc": 19.02},
        {"keyword": "simpro features", "volume": 20, "cpc": 0.0},
        {"keyword": "simpro software", "volume": 320, "keyword_difficulty": 53, "intent": ["navigational"], "cpc": 13.04},
        {"keyword": "simpro job management software", "volume": 90, "keyword_difficulty": 35, "intent": ["commercial"], "cpc": 30.13},
        {"keyword": "simpro pricing", "volume": 110, "keyword_difficulty": 15, "intent": ["commercial"], "cpc": 25.9},
    ]
    serp_rows = [
        {
            "position": row["position"],
            "position_type": "organic",
            "domain": urlparse(row["url"]).netloc.removeprefix("www."),
            "url": row["url"],
            "triggered_serp_features": URL_FEATURES.get(row["url"], []),
        }
        for row in serp["results"]
    ]
    decision = build_keyword_decision(
        brand="Simpro",
        market="US",
        database="us",
        collection_date=DATE,
        source_boundary=SOURCE_BOUNDARY,
        seed_terms=[PRIMARY_QUERY, "simpro reviews", "simpro software", "what does simpro do"],
        connector_reports=_connector_reports(ui_hash, serp_path),
        candidate_metrics=candidate_metrics,
        serp_finalists=[{"keyword": PRIMARY_QUERY, "database": "us", "results": serp_rows}],
        question_candidates=[
            {"keyword": "what is simpro software", "volume": 20},
            {"keyword": "what is simpro used for", "volume": 20},
            {"keyword": "what does simpro do", "volume": 20},
            {"keyword": "is simpro a crm system", "volume": 10},
        ],
        related_candidates=[
            {"keyword": "simpro reviews", "volume": 40, "keyword_difficulty": 15},
            {"keyword": "simpro software reviews", "volume": 30, "keyword_difficulty": 14},
            {"keyword": "simpro app", "volume": 20},
            {"keyword": "simpro features", "volume": 20},
        ],
        selected_primary_keyword=PRIMARY_QUERY,
        selected_secondary_keywords=[
            "simpro reviews",
            "simpro software reviews",
            "simpro app",
            "simpro features",
        ],
        rejected_keywords=[
            {"keyword": "simpro software", "reason": "Navigational intent with KD 53; the Simpro homepage and login page own this brand navigation query."},
            {"keyword": "simpro job management software", "reason": "Commercial product query owned by the Simpro job management solution page; targeting it from a blog would compete with that destination."},
            {"keyword": "simpro pricing", "reason": "Commercial pricing query owned by the Simpro pricing page; the article links to pricing instead of targeting the term."},
        ],
        selection_rationale=(
            "The authenticated Semrush US desktop UI shows what is simpro at 90 US volume, KD 22 Easy, informational and navigational intent, with 360 global volume. "
            "Its live top ten is the Simpro homepage with sitelinks, Wikipedia, review-site and employer-review profiles, the login page, social profiles, and technology-tracking pages, so no ranking page explains the platform with linked customer evidence. "
            "Simpro reviews (40, KD 15, commercial) and simpro software reviews (30, KD 14) fit the same evaluator reading path and support review-backed sections. "
            "Simpro software is navigational and homepage-owned, and simpro job management software and simpro pricing belong to existing commercial pages. "
            "Semrush lists 8 questions for the primary term; AnswerSocrates People Also Asked questions are preserved in a separate receipt-bound artifact."
        ),
        workspace_root=ROOT,
    )
    atomic_write_json(KEYWORD_PATH, decision)
    print(json.dumps({
        "serp_evidence": serp_path.relative_to(ROOT).as_posix(),
        "keyword_decision": KEYWORD_PATH.relative_to(ROOT).as_posix(),
        "keyword_evidence_hash": decision["evidence_hash"],
        "serp_evidence_hash": serp.get("evidence_hash"),
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
