"""Build the dated Semrush keyword decision for the Simpro California trades rewrite.

Every metric and SERP row below was read from the authenticated Semrush UI in
the main Chrome window on 2026-09-24, US desktop database. The plain-text UI
evidence files in ``research/semrush-ui-best-trade-jobs-california-2026-09-24/``
are hash-bound to the report log rows they support. Nothing is estimated; a
Keyword Difficulty shown as ``n/a`` in the UI remains ``None``.
"""
from __future__ import annotations

import hashlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from data_sources.modules.blog_assembly_contract import atomic_write_json
from data_sources.modules.semrush_keyword_decision_guard import (
    SOURCE_BOUNDARY,
    build_keyword_decision,
    check_decision,
)


SLUG = "best-trade-jobs-california"
DATE = "2026-09-24"
RUN_ID = "0f23f31d-46c1-4b8c-936e-2b2edb8dbbf5"
SURFACE = "semrush_ui_chrome_main_browser"
TARGET_URL = "https://www.simprogroup.com/blog/best-trade-jobs-california"
SIBLING_URL = "https://www.simprogroup.com/blog/highest-paying-trade-jobs"
UI_DIR = ROOT / "research" / f"semrush-ui-{SLUG}-{DATE}"
UI_FILES = {
    "primary_overview": UI_DIR / "keyword-overview-highest-paying-trades-in-california.txt",
    "trade_jobs_overview": UI_DIR / "keyword-overview-highest-paying-trade-jobs-in-california.txt",
    "best_trade_jobs_overview": UI_DIR / "keyword-overview-best-trade-jobs-in-california.txt",
    "pay_well_overview": UI_DIR / "keyword-overview-trades-that-pay-well-in-california.txt",
    "magic_broad": UI_DIR / "keyword-magic-trades-in-california-broad.txt",
    "magic_phrase": UI_DIR / "keyword-magic-trades-in-california-phrase.txt",
    "positions_target": UI_DIR / "organic-positions-best-trade-jobs-california.txt",
    "positions_sibling": UI_DIR / "organic-positions-highest-paying-trade-jobs.txt",
}
OUT = ROOT / "research" / f"semrush-keyword-decision-{SLUG}-{DATE}.json"

PRIMARY = "highest paying trades in california"
SECONDARIES = [
    "trades that pay well in california",
    "best trade jobs in california",
]

CANDIDATES = [
    {
        "keyword": PRIMARY,
        "volume": 70,
        "global_volume": 80,
        "keyword_difficulty": 22,
        "keyword_difficulty_label": "Easy",
        "intent": ["informational", "commercial"],
        "cpc": 8.85,
        "competitive_density": 0.11,
        "results": 144,
        "serp_features": ["Sitelinks", "AI Overview", "Video", "Discussions and forums"],
        "target_url_position": 2,
    },
    {
        "keyword": "highest paying trade jobs in california",
        "volume": 90,
        "global_volume": 110,
        "keyword_difficulty": 28,
        "keyword_difficulty_label": "Easy",
        "intent": ["commercial"],
        "cpc": 1.63,
        "competitive_density": 0.04,
        "results": 151,
        "serp_features": [
            "Sitelinks",
            "AI Overview",
            "Video",
            "People also ask",
            "Discussions and forums",
        ],
        "target_url_position": 2,
    },
    {
        "keyword": "best trade jobs in california",
        "volume": 50,
        "global_volume": 50,
        "keyword_difficulty": 9,
        "keyword_difficulty_label": "Very easy",
        "intent": ["commercial"],
        "cpc": 4.58,
        "competitive_density": 0.13,
        "results": 179,
        "serp_features": ["Sitelinks", "Video", "Discussions and forums"],
        "target_url_position": 2,
    },
    {
        "keyword": "trades that pay well in california",
        "volume": 30,
        "global_volume": 30,
        "keyword_difficulty": 28,
        "keyword_difficulty_label": "Easy",
        "intent": ["informational"],
        "cpc": 3.16,
        "competitive_density": 0.30,
        "results": 141,
        "serp_features": [
            "Sitelinks",
            "AI Overview",
            "Video",
            "People also ask",
            "Discussions and forums",
        ],
        "target_url_position": 1,
    },
    {
        "keyword": "best trades in california",
        "volume": 50,
        "keyword_difficulty": 17,
        "intent": ["commercial"],
        "cpc": 10.14,
        "target_url_position": 2,
    },
    {
        "keyword": "trades in california",
        "volume": 30,
        "keyword_difficulty": 22,
        "intent": ["informational", "commercial"],
        "cpc": 5.56,
    },
    {
        "keyword": "highest paid trades in california",
        "volume": 30,
        "keyword_difficulty": None,
        "cpc": 0.00,
    },
    {
        "keyword": "trade schools in california",
        "volume": 1000,
        "keyword_difficulty": 27,
        "intent": ["commercial"],
        "cpc": 4.65,
    },
    {
        "keyword": "highest paying trade jobs",
        "volume": 6600,
        "keyword_difficulty": 23,
        "target_url_position": 19,
    },
]

QUESTION_CANDIDATES = [
    {
        "keyword": "what is the highest paying trade in california",
        "volume": 20,
        "keyword_difficulty": None,
    },
    {
        "keyword": "what trades are in demand in california",
        "volume": 20,
        "keyword_difficulty": None,
    },
    {
        "keyword": "what trades pay the most in california",
        "volume": 0,
        "keyword_difficulty": None,
    },
    {
        "keyword": "what trades makes the most money in california",
        "volume": 0,
        "keyword_difficulty": None,
    },
]

RELATED_CANDIDATES = [
    {"keyword": "highest paying trade in california", "volume": 20, "keyword_difficulty": None},
    {"keyword": "best paying trades in california", "volume": 20, "keyword_difficulty": None},
    {"keyword": "high paying trades in california", "volume": 20, "keyword_difficulty": None},
    {"keyword": "top paying trades in california", "volume": 20, "keyword_difficulty": None},
    {"keyword": "trades in demand in california", "volume": 20, "keyword_difficulty": None},
    {"keyword": "best trades to learn in california", "volume": 20, "keyword_difficulty": None},
    {"keyword": "skilled trades jobs in california", "volume": 20, "keyword_difficulty": None},
    {"keyword": "best paying trade jobs in california", "volume": 20, "keyword_difficulty": None},
    {"keyword": "highest paid union trades in california", "volume": 0, "keyword_difficulty": None},
    {"keyword": "highest paying skilled trades in california", "volume": 0, "keyword_difficulty": None},
    {"keyword": "highest paying construction trades in california", "volume": 0, "keyword_difficulty": None},
]

SERP_RESULTS = [
    {
        "position": 1,
        "position_type": "organic",
        "domain": "reddit.com",
        "url": "https://www.reddit.com/r/careerguidance/comments/16dfz0s/best_trade_job/",
        "triggered_serp_features": ["Sitelinks"],
    },
    {
        "position": 2,
        "position_type": "organic",
        "domain": "simprogroup.com",
        "url": TARGET_URL,
        "triggered_serp_features": [],
    },
    {
        "position": 3,
        "position_type": "organic",
        "domain": "abcnorcal.org",
        "url": "https://abcnorcal.org/highest-paying-trade-jobs/",
        "triggered_serp_features": ["Sitelinks"],
    },
    {
        "position": 4,
        "position_type": "organic",
        "domain": "indeed.com",
        "url": "https://www.indeed.com/career-advice/finding-a-job/high-paid-trade-school-jobs-los-angeles",
        "triggered_serp_features": [],
    },
    {
        "position": 5,
        "position_type": "organic",
        "domain": "careeronestop.org",
        "url": "https://www.careeronestop.org/Toolkit/Wages/highest-paying-careers.aspx?persist=true&location=CA",
        "triggered_serp_features": [],
    },
    {
        "position": 6,
        "position_type": "organic",
        "domain": "tallo.com",
        "url": "https://tallo.com/careers/job-search/highest-paying-trade-jobs-in-california/",
        "triggered_serp_features": [],
    },
    {
        "position": 7,
        "position_type": "organic",
        "domain": "youtube.com",
        "url": "https://www.youtube.com/watch?v=ooWoKmqrooU",
        "triggered_serp_features": ["Video"],
    },
    {
        "position": 8,
        "position_type": "organic",
        "domain": "forbes.com",
        "url": "https://www.forbes.com/sites/lucianapaulise/article/high-paying-trade-skills-and-jobs/",
        "triggered_serp_features": [],
    },
    {
        "position": 9,
        "position_type": "organic",
        "domain": "accreditedschoolsonline.org",
        "url": "https://www.accreditedschoolsonline.org/vocational-trade-school/highest-paying-trade-jobs/",
        "triggered_serp_features": [],
    },
    {
        "position": 10,
        "position_type": "organic",
        "domain": "intercoast.edu",
        "url": "https://www.intercoast.edu/articles/trade-skills-california/",
        "triggered_serp_features": [],
    },
]

REJECTED = [
    {
        "keyword": "highest paying trade jobs in california",
        "reason": (
            "Measured at 90 US volume and KD 28 with the target URL at position 2, "
            "but it is not a tracked secondary because the locked brief contextual "
            "keyword set is trades that pay well in california and best trade jobs "
            "in california. It is covered by the brief-locked H1 wording instead."
        ),
    },
    {
        "keyword": "highest paying trade jobs",
        "reason": (
            "National 6.6K-volume head term without California qualification; the target "
            "URL ranks at position 19 and the sibling highest-paying-trade-jobs URL targets "
            "near-identical national intent, so it stays out of this California rewrite."
        ),
    },
    {
        "keyword": "trade schools in california",
        "reason": (
            "Highest phrase volume in the Keyword Magic set, but school-selection intent "
            "differs from the salary-ranked trade career guide."
        ),
    },
    {
        "keyword": "best trades in california",
        "reason": (
            "Measured close variant with the target URL at position 2; kept as natural "
            "body coverage rather than a tracked secondary."
        ),
    },
]

RATIONALE = (
    "The authenticated US desktop Semrush UI on September 24, 2026 confirms "
    "highest paying trades in california at 70 US volume, KD 22 Easy, CPC $8.85, "
    "informational plus commercial intent, with the rewrite target ranking "
    "at position 2 in the SERP Analysis table. It matches the brief's shift toward "
    "highest-paying intent and is the locked primary keyword. The two brief contextual "
    "keywords were measured in the same UI session: trades that pay well in california "
    "(30 volume, KD 28, target URL position 1) and best trade jobs in california "
    "(50 volume, KD 9, target URL position 2). The sibling highest-paying-trade-jobs "
    "URL ranks for 7 national keywords, none California-qualified, so cannibalization "
    "risk for the California set is low, and the brief prohibits linking to it."
)


def _sha(key: str) -> tuple[str, str]:
    path = UI_FILES[key]
    return path.relative_to(ROOT).as_posix(), hashlib.sha256(path.read_bytes()).hexdigest()


def _connector_reports() -> list[dict[str, object]]:
    common = {
        "execution_surface": SURFACE,
        "database": "us",
        "device": "desktop",
        "collection_date": DATE,
        "run_id": RUN_ID,
    }
    report_params = {
        "_keyword_research": (
            {**common, "query": PRIMARY,
             "ui_url": "https://www.semrush.com/analytics/keywordoverview/?q=highest+paying+trades+in+california&db=us"},
            "primary_overview",
        ),
        "_get_report_schema": (
            {**common, "report": "phrase_these",
             "schema_source": "repo guard shape mapped to source-visible Semrush UI fields"},
            "primary_overview",
        ),
        "phrase_these": (
            {**common, "keywords": [row["keyword"] for row in CANDIDATES],
             "ui_views": [
                 "keyword-overview-highest-paying-trades-in-california.txt",
                 "keyword-overview-highest-paying-trade-jobs-in-california.txt",
                 "keyword-overview-best-trade-jobs-in-california.txt",
                 "keyword-overview-trades-that-pay-well-in-california.txt",
             ]},
            "primary_overview",
        ),
        "phrase_related": (
            {**common, "phrase": "trades in california", "match": "phrase",
             "ui_url": "https://www.semrush.com/analytics/keywordmagic/?q=trades+in+california&db=us&type=phrase&mode=1"},
            "magic_phrase",
        ),
        "phrase_questions": (
            {**common, "phrase": PRIMARY,
             "ui_basis": "Keyword Overview Questions panel (1 keyword, 20 total volume) plus question-form rows in the Keyword Magic phrase-match view"},
            "primary_overview",
        ),
        "phrase_organic": (
            {**common, "phrase": PRIMARY, "display_limit": 10,
             "ui_basis": "Keyword Overview SERP Analysis positions 1-10"},
            "primary_overview",
        ),
        "phrase_this": (
            {**common, "phrase": PRIMARY},
            "primary_overview",
        ),
        "url_organic_target": (
            {**common, "url": TARGET_URL, "data_date_shown": "Sep 23, 2026"},
            "positions_target",
        ),
        "url_organic_sibling_cannibalization": (
            {**common, "url": SIBLING_URL, "data_date_shown": "Sep 23, 2026"},
            "positions_sibling",
        ),
        "phrase_fullsearch_broad": (
            {**common, "phrase": "trades in california", "match": "all_keywords_broad"},
            "magic_broad",
        ),
    }
    reports = []
    for report, (parameters, evidence_key) in report_params.items():
        evidence_path, evidence_sha = _sha(evidence_key)
        reports.append(
            {
                "report": report,
                "status": "completed",
                "parameters": parameters,
                "completion_basis": (
                    "Authenticated US desktop Semrush UI fields were visible in the "
                    "main Chrome browser on 2026-09-24."
                ),
                "ui_evidence_path": evidence_path,
                "ui_evidence_sha256": evidence_sha,
            }
        )
    return reports


def main() -> int:
    decision = build_keyword_decision(
        brand="Simpro",
        market="US",
        database="us",
        collection_date=DATE,
        source_boundary=SOURCE_BOUNDARY,
        seed_terms=[
            PRIMARY,
            "highest paying trade jobs in california",
            "best trade jobs in california",
            "trades that pay well in california",
            "trades in california",
        ],
        connector_reports=_connector_reports(),
        candidate_metrics=CANDIDATES,
        serp_finalists=[
            {"keyword": PRIMARY, "database": "us", "results": SERP_RESULTS}
        ],
        question_candidates=QUESTION_CANDIDATES,
        related_candidates=RELATED_CANDIDATES,
        selected_primary_keyword=PRIMARY,
        selected_secondary_keywords=SECONDARIES,
        rejected_keywords=REJECTED,
        selection_rationale=RATIONALE,
        workspace_root=ROOT,
    )
    findings = check_decision(decision, assembly_date=DATE)
    atomic_write_json(OUT, decision)
    print(f"keyword decision: {OUT.relative_to(ROOT).as_posix()}")
    print(f"primary: {decision['selected_primary_keyword']}")
    print(f"evidence: {decision['evidence_hash']}")
    print(f"guard findings: {len(findings)}")
    for finding in findings:
        print(f"  {finding['rule_id']}: {finding['message']}")
    return 1 if findings else 0


if __name__ == "__main__":
    raise SystemExit(main())
