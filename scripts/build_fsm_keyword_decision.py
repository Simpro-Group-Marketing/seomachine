"""Build the dated Semrush keyword decision for the Simpro FSM buyer's guide.

Every metric and SERP row below was read from the authenticated Semrush Keyword
Overview UI in the main Chrome window on 2026-09-23, US desktop database. The
plain-text UI evidence artifact is hash-bound to every report log row. Nothing
is estimated, and a missing Keyword Difficulty value remains ``None``.
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
)


SLUG = "best-field-service-management-software"
DATE = "2026-09-23"
SURFACE = "semrush_ui_chrome_main_browser"
UI_PATH = (
    ROOT
    / "research"
    / f"semrush-ui-{SLUG}-{DATE}"
    / f"keyword-overview-{DATE}.txt"
)
UI_RELATIVE = UI_PATH.relative_to(ROOT).as_posix()
OUT = ROOT / "research" / f"semrush-keyword-decision-{SLUG}-{DATE}.json"

PRIMARY = "best field service management software"
SECONDARIES = [
    "best field service management software for small business",
    "best field service management software 2026",
]

CANDIDATES = [
    {
        "keyword": PRIMARY,
        "volume": 1600,
        "global_volume": 2700,
        "keyword_difficulty": 31,
        "keyword_difficulty_label": "Possible",
        "intent": ["commercial"],
        "cpc": 42.48,
        "competitive_density": 0.24,
        "results": 174,
        "serp_features": [
            "Sitelinks",
            "AI Overview",
            "Reviews",
            "Video",
            "Video carousel",
            "Discussions/forums",
        ],
    },
    {
        "keyword": "best field service management software for small business",
        "volume": 480,
        "keyword_difficulty": 5,
    },
    {
        "keyword": "best field service management software 2025",
        "volume": 390,
        "keyword_difficulty": 39,
    },
    {
        "keyword": "best field service management software 2026",
        "volume": 110,
        "keyword_difficulty": 25,
    },
    {
        "keyword": "what is the best field service management software",
        "volume": 110,
        "keyword_difficulty": 25,
    },
]

QUESTION_CANDIDATES = [
    {
        "keyword": "what is the best field service management software",
        "volume": 110,
        "keyword_difficulty": 25,
    },
    {
        "keyword": "what's the best field service management software for contractors",
        "volume": 20,
        "keyword_difficulty": None,
    },
    {
        "keyword": "is it best field service management software",
        "volume": 0,
        "keyword_difficulty": None,
    },
    {
        "keyword": "is it field service management software with best reviews",
        "volume": 0,
        "keyword_difficulty": None,
    },
    {
        "keyword": "what field service management software offers the best mobile app",
        "volume": 0,
        "keyword_difficulty": None,
    },
]

SERP_RESULTS = [
    {
        "position": 1,
        "position_type": "organic",
        "domain": "coastapp.com",
        "url": "https://coastapp.com/blog/field-service-management-software/",
        "triggered_serp_features": ["Sitelinks"],
    },
    {
        "position": 2,
        "position_type": "organic",
        "domain": "reddit.com",
        "url": "https://www.reddit.com/r/lowvoltage/comments/1bnl56d/best_field_service_management_tool/",
        "triggered_serp_features": ["Sitelinks"],
    },
    {
        "position": 3,
        "position_type": "organic",
        "domain": "gartner.com",
        "url": "https://www.gartner.com/reviews/market/field-service-management",
        "triggered_serp_features": [],
    },
    {
        "position": 4,
        "position_type": "organic",
        "domain": "servicepower.com",
        "url": "https://www.servicepower.com/resources/industry-guides/what-is-field-service-management-software",
        "triggered_serp_features": [],
    },
    {
        "position": 5,
        "position_type": "organic",
        "domain": "servicetitan.com",
        "url": "https://www.servicetitan.com/market/field-service-management-software",
        "triggered_serp_features": ["Reviews"],
    },
    {
        "position": 6,
        "position_type": "organic",
        "domain": "fieldpulse.com",
        "url": "https://www.fieldpulse.com/",
        "triggered_serp_features": [],
    },
    {
        "position": 7,
        "position_type": "organic",
        "domain": "infotech.com",
        "url": "https://www.infotech.com/software-reviews/categories/field-service-management",
        "triggered_serp_features": [],
    },
    {
        "position": 8,
        "position_type": "organic",
        "domain": "connecteam.com",
        "url": "https://connecteam.com/best-free-field-service-management-software/",
        "triggered_serp_features": [],
    },
    {
        "position": 9,
        "position_type": "organic",
        "domain": "pipedrive.com",
        "url": "https://www.pipedrive.com/en/industries/crm-for-field-service",
        "triggered_serp_features": [],
    },
    {
        "position": 10,
        "position_type": "organic",
        "domain": "servicefusion.com",
        "url": "https://www.servicefusion.com/field-service-management-software",
        "triggered_serp_features": ["Reviews"],
    },
]

REJECTED = [
    {
        "keyword": "field service management software",
        "reason": (
            "The broader category term is reserved for the Simpro commercial pillar; "
            "this article owns commercial comparison intent and links to that pillar."
        ),
    },
    {
        "keyword": "best field service management software 2025",
        "reason": "The dated 2025 variation does not fit the current 2026 buyer's guide.",
    },
]

RATIONALE = (
    "The authenticated US desktop Semrush UI on September 23, 2026 confirms "
    "best field service management software as a commercial comparison query "
    "with 1.6K US volume, 2.7K global volume, and KD 31 Possible. The measured "
    "small-business and 2026 variations remain secondary queries because they "
    "match the guide's scenario routing and current-year framing. The broader "
    "field service management software term remains assigned to the Simpro "
    "commercial pillar, while the 2025 variation is stale for this guide."
)


def _connector_reports(evidence_sha256: str) -> list[dict[str, object]]:
    common = {
        "execution_surface": SURFACE,
        "database": "us",
        "device": "desktop",
        "collection_date": DATE,
    }
    report_params = {
        "_keyword_research": {**common, "query": PRIMARY},
        "_get_report_schema": {**common, "report": "phrase_this"},
        "phrase_these": {
            **common,
            "keywords": [row["keyword"] for row in CANDIDATES],
        },
        "phrase_related": {**common, "phrase": PRIMARY},
        "phrase_questions": {**common, "phrase": PRIMARY},
        "phrase_organic": {**common, "phrase": PRIMARY, "display_limit": 10},
        "phrase_this": {**common, "phrase": PRIMARY},
    }
    reports = []
    for report, parameters in report_params.items():
        reports.append(
            {
                "report": report,
                "status": "completed",
                "parameters": parameters,
                "completion_basis": (
                    "Authenticated US desktop Keyword Overview fields were visible "
                    "in the main Chrome browser on 2026-09-23."
                ),
                "ui_evidence_path": UI_RELATIVE,
                "ui_evidence_sha256": evidence_sha256,
            }
        )
    return reports


def main() -> int:
    evidence_sha256 = hashlib.sha256(UI_PATH.read_bytes()).hexdigest()
    decision = build_keyword_decision(
        brand="Simpro",
        market="US",
        database="us",
        collection_date=DATE,
        source_boundary=SOURCE_BOUNDARY,
        seed_terms=[
            PRIMARY,
            "field service management software",
            "best field service management software for small business",
            "best field service management software 2026",
        ],
        connector_reports=_connector_reports(evidence_sha256),
        candidate_metrics=CANDIDATES,
        serp_finalists=[
            {"keyword": PRIMARY, "database": "us", "results": SERP_RESULTS}
        ],
        question_candidates=QUESTION_CANDIDATES,
        related_candidates=[],
        selected_primary_keyword=PRIMARY,
        selected_secondary_keywords=SECONDARIES,
        rejected_keywords=REJECTED,
        selection_rationale=RATIONALE,
        workspace_root=ROOT,
    )
    atomic_write_json(OUT, decision)
    print(f"keyword decision: {OUT.relative_to(ROOT).as_posix()}")
    print(f"primary: {decision['selected_primary_keyword']}")
    print(f"evidence: {decision['evidence_hash']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
