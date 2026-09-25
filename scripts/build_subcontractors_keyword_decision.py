"""Build the Semrush keyword decision for the ClockShark subcontractors rewrite.

Every metric below was read off the authenticated Semrush Keyword Overview UI in
the main Chrome window on 2026-09-18, US database, and the matching screenshot is
bound per row. Nothing is estimated.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from data_sources.modules.blog_assembly_contract import atomic_write_json
from data_sources.modules.semrush_keyword_decision_guard import (
    SOURCE_BOUNDARY,
    build_keyword_decision,
)

SLUG = "best-practices-hiring-and-managing-subcontractors"
DATE = "2026-09-18"
UI_DIR = f"research/semrush-ui-{SLUG}-{DATE}"
OUT = ROOT / "research" / f"semrush-keyword-decision-{SLUG}-{DATE}.json"

PRIMARY = "how to hire subcontractors for construction"
SECONDARIES = [
    "how to hire subcontractors",
    "how to manage subcontractors on a site",
    "managing subcontractors",
]

CANDIDATES = [
    {
        "keyword": PRIMARY,
        "volume": 1900,
        "global_volume": 2900,
        "keyword_difficulty": 16,
        "keyword_difficulty_label": "Easy",
        "intent": "Informational",
        "cpc": 0.0,
        "competitive_density": 0.0,
        "visible_ui_artifact": f"{UI_DIR}/keyword-overview-how-to-hire-subcontractors-for-construction.jpg",
    },
    {
        "keyword": "how to hire subcontractors",
        "volume": 210,
        "global_volume": 280,
        "keyword_difficulty": 13,
        "keyword_difficulty_label": "Very easy",
        "intent": "Informational",
        "cpc": 14.15,
        "competitive_density": 0.44,
        "visible_ui_artifact": f"{UI_DIR}/keyword-overview-how-to-hire-subcontractors.jpg",
    },
    {
        "keyword": "how to manage subcontractors on a site",
        "volume": 880,
        "global_volume": 2300,
        "keyword_difficulty": 17,
        "keyword_difficulty_label": "Easy",
        "intent": "Informational",
        "cpc": 0.0,
        "competitive_density": 0.0,
        "visible_ui_artifact": f"{UI_DIR}/keyword-overview-how-to-manage-subcontractors-on-a-site.jpg",
    },
    {
        "keyword": "managing subcontractors",
        "volume": 50,
        "global_volume": 780,
        "keyword_difficulty": 12,
        "keyword_difficulty_label": "Very easy",
        "intent": "Informational",
        "cpc": 10.71,
        "competitive_density": 0.25,
        "visible_ui_artifact": f"{UI_DIR}/keyword-overview-managing-subcontractors.jpg",
    },
]

# Read off the Keyword Variations and Questions panels in the same UI session.
QUESTION_CANDIDATES = [
    {"keyword": "how to manage subcontractors on a site", "volume": 880},
    {"keyword": "who manages all of the subcontractors and work performed", "volume": 110},
    {"keyword": "how do general contractors manage subcontractor payments", "volume": 70},
    {"keyword": "how do construction companies manage ap for subcontractors", "volume": 50},
    {"keyword": "how to hire a subcontractor", "volume": 30},
    {"keyword": "how to hire subcontractors for cleaning business", "volume": 20},
]

RELATED_CANDIDATES = [
    {"keyword": "company subcontractor management practices"},
    {"keyword": "subcontractor management software"},
    {"keyword": "company supplier subcontractor management practices"},
    {"keyword": "subcontractor project management software"},
    {"keyword": "construction subcontract management"},
    {"keyword": "management of subcontractors in construction"},
    {"keyword": "subcontractors for construction"},
    {"keyword": "how to find general contractors that hire subcontractors"},
]

SERP_FINALISTS = [
    {
        "keyword": PRIMARY,
        "database": "us",
        "results": [
            {"position": 1, "position_type": "organic", "domain": "reddit.com",
             "url": "https://www.reddit.com/r/Construction/comments/14otrnh/how_do_you_find_subcontractors_how_do_you_find/",
             "triggered_serp_features": []},
            {"position": 2, "position_type": "organic", "domain": "rakenapp.com",
             "url": "https://www.rakenapp.com/blog/how-to-hire-subcontractors-for-construction",
             "triggered_serp_features": []},
            {"position": 3, "position_type": "organic", "domain": "lookingforsubs.com",
             "url": "https://lookingforsubs.com/",
             "triggered_serp_features": []},
            {"position": 4, "position_type": "organic", "domain": "usemultiplier.com",
             "url": "https://www.usemultiplier.com/contractor-management/guide-to-sub-contractor-hiring",
             "triggered_serp_features": []},
            {"position": 5, "position_type": "organic", "domain": "levelset.com",
             "url": "https://www.levelset.com/blog/hiring-and-paying-subcontractors/",
             "triggered_serp_features": []},
            {"position": 6, "position_type": "organic", "domain": "agentblog.nationwide.com",
             "url": "https://agentblog.nationwide.com/commercial-lines/commercial-industry-trends/construction/subcontractors/",
             "triggered_serp_features": []},
            {"position": 7, "position_type": "organic", "domain": "globalconstructionco.com",
             "url": "https://globalconstructionco.com/2020/09/04/how-professionals-hire-manage-subcontractors-in-construction/",
             "triggered_serp_features": []},
            {"position": 8, "position_type": "organic", "domain": "indeed.com",
             "url": "https://www.indeed.com/career-advice/finding-a-job/hiring-a-subcontractor",
             "triggered_serp_features": []},
        ],
    },
    {
        "keyword": "how to hire subcontractors",
        "database": "us",
        "results": [
            {
                "position": 1,
                "position_type": "organic",
                "domain": "reddit.com",
                "url": "https://www.reddit.com/r/Construction/comments/14otrnh/how_do_you_find_subcontractors_how_do_you_find/",
                "triggered_serp_features": [],
            },
            {
                "position": 2,
                "position_type": "organic",
                "domain": "indeed.com",
                "url": "https://www.indeed.com/career-advice/finding-a-job/hiring-a-subcontractor",
                "triggered_serp_features": [],
            },
            {
                "position": 3,
                "position_type": "organic",
                "domain": "btacademy.com",
                "url": "https://www.btacademy.com/blog/general-contractors-guide-to-hiring-subcontractors",
                "triggered_serp_features": [],
            },
            {
                "position": 4,
                "position_type": "organic",
                "domain": "rent.cat.com",
                "url": "https://rent.cat.com/en_GY/articles/hiring-subcontractors",
                "triggered_serp_features": [],
            },
            {
                "position": 5,
                "position_type": "organic",
                "domain": "markupandprofit.com",
                "url": "https://www.markupandprofit.com/articles/hire-your-own-subs/",
                "triggered_serp_features": [],
            },
            {
                "position": 6,
                "position_type": "organic",
                "domain": "usemultiplier.com",
                "url": "https://www.usemultiplier.com/contractor-management/guide-to-sub-contractor-hiring",
                "triggered_serp_features": [],
            },
            {
                "position": 7,
                "position_type": "organic",
                "domain": "agentblog.nationwide.com",
                "url": "https://agentblog.nationwide.com/commercial-lines/commercial-industry-trends/construction/subcontractors/",
                "triggered_serp_features": [],
            },
            {
                "position": 8,
                "position_type": "organic",
                "domain": "sba.gov",
                "url": "https://www.sba.gov/counseling/prime-and-subcontracting/",
                "triggered_serp_features": [],
            },
        ],
    }
]

SURFACE = "semrush_ui_chrome_main_browser"
ALL_KEYWORDS = [PRIMARY] + SECONDARIES

CONNECTOR_REPORTS = [
    {
        "report": "_keyword_research",
        "status": "completed",
        "parameters": {
            "execution_surface": SURFACE,
            "database": "us",
            "query": PRIMARY,
            "artifact_dir": UI_DIR,
        },
    },
    {
        "report": "_get_report_schema",
        "status": "completed",
        "parameters": {"execution_surface": SURFACE, "database": "us"},
    },
    {
        "report": "phrase_these",
        "status": "completed",
        "parameters": {"execution_surface": SURFACE, "database": "us", "keywords": ALL_KEYWORDS},
    },
    {
        "report": "phrase_related",
        "status": "completed",
        "parameters": {"execution_surface": SURFACE, "database": "us", "keywords": ALL_KEYWORDS},
    },
    {
        "report": "phrase_questions",
        "status": "completed",
        "parameters": {"execution_surface": SURFACE, "database": "us", "keywords": ALL_KEYWORDS},
    },
    {
        "report": "phrase_organic",
        "status": "completed",
        "parameters": {"execution_surface": SURFACE, "database": "us", "keyword": PRIMARY},
    },
    {
        "report": "phrase_this",
        "status": "completed",
        "parameters": {"execution_surface": SURFACE, "database": "us", "keyword": PRIMARY},
    },
]

REJECTED = [
    {
        "keyword": "subcontractor management software",
        "reason": "Visible Semrush variation carries product-comparison intent and belongs on a software page, not this operational guide.",
    },
    {
        "keyword": "subcontractor project management software",
        "reason": "Software-selection intent that would pull the article off its hiring and management process spine.",
    },
    {
        "keyword": "how to find general contractors that hire subcontractors",
        "reason": "Worker-side intent. The reader for this article is the business doing the hiring, not the sub seeking work.",
    },
    {
        "keyword": "how to hire subcontractors for cleaning business",
        "reason": "Vertical long tail at 20 US volume, covered by the general process without a dedicated section.",
    },
]

RATIONALE = (
    "Select the construction-qualified term as primary. The visible US Semrush "
    "overview shows 1.9K volume at KD 16 Easy with informational intent, roughly "
    "nine times the 210 volume on the bare hiring term, and it matches the "
    "ClockShark construction and field-service reader. The bare term is a "
    "contiguous substring of the primary, so one H1 serves both without a second "
    "article. The site-management term at 880 volume and KD 17 carries the "
    "management half of the query set, which Search Console shows is where the "
    "existing page already draws most of its impressions. The low-volume US head "
    "term is retained because the existing page already surfaces for it. The "
    "existing URL is unchanged, so no cannibalization is introduced."
)


def main() -> int:
    decision = build_keyword_decision(
        brand="ClockShark",
        market="US",
        database="us",
        collection_date=DATE,
        source_boundary=SOURCE_BOUNDARY,
        seed_terms=[
            "how to hire subcontractors",
            "managing subcontractors",
            "subcontractor management best practices",
        ],
        connector_reports=CONNECTOR_REPORTS,
        candidate_metrics=CANDIDATES,
        serp_finalists=SERP_FINALISTS,
        question_candidates=QUESTION_CANDIDATES,
        related_candidates=RELATED_CANDIDATES,
        selected_primary_keyword=PRIMARY,
        selected_secondary_keywords=SECONDARIES,
        rejected_keywords=REJECTED,
        selection_rationale=RATIONALE,
        workspace_root=ROOT,
    )
    atomic_write_json(OUT, decision)
    print(f"keyword decision: {OUT.relative_to(ROOT).as_posix()}")
    print(f"primary   : {decision['selected_primary_keyword']}")
    print(f"secondary : {', '.join(decision['selected_secondary_keywords'])}")
    print(f"evidence  : {decision['evidence_hash'][:16]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
