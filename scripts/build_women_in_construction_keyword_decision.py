"""Build the dated Semrush keyword decision for the Simpro women-in-construction rewrite.

Every metric and SERP row below was read from the authenticated Semrush UI in
the main Chrome window on 2026-09-28, US desktop database. The plain-text UI
evidence files in ``research/semrush-ui-women-in-construction-2026-09-28/``
are hash-bound to the report log rows they support. Nothing is estimated; a
Keyword Difficulty shown as ``n/a`` in the UI remains ``None``.
"""
from __future__ import annotations

import hashlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from data_sources.modules.blog_assembly_contract import atomic_write_json  # noqa: E402
from data_sources.modules.semrush_keyword_decision_guard import (  # noqa: E402
    SOURCE_BOUNDARY,
    build_keyword_decision,
    check_decision,
)

SLUG = "women-in-construction"
DATE = "2026-09-28"
RUN_ID = "f1130b43-7baa-4ac4-9bcc-b26c15dde6b6"
SURFACE = "semrush_ui_chrome_main_browser"
TARGET_URL = "https://www.simprogroup.com/blog/women-in-construction-week"
SIBLING_URL = "https://www.simprogroup.com/blog/women-in-skilled-trades-the-ultimate-guide"
UI_DIR = ROOT / "research" / f"semrush-ui-{SLUG}-{DATE}"
UI_FILES = {
    "primary_overview": UI_DIR / "keyword-overview-women-in-construction.txt",
    "woman_overview": UI_DIR / "keyword-overview-woman-in-construction.txt",
    "workers_overview": UI_DIR / "keyword-overview-women-construction-workers.txt",
    "magic_broad": UI_DIR / "keyword-magic-women-in-construction-broad.txt",
    "magic_phrase": UI_DIR / "keyword-magic-women-in-construction-phrase.txt",
    "magic_questions": UI_DIR / "keyword-magic-women-in-construction-questions.txt",
    "positions_target": UI_DIR / "organic-positions-women-in-construction-week.txt",
    "positions_sibling": UI_DIR / "organic-positions-women-in-skilled-trades-the-ultimate-guide.txt",
}
OUT = ROOT / "research" / f"semrush-keyword-decision-{SLUG}-{DATE}.json"

PRIMARY = "women in construction"
SECONDARIES = ["woman in construction", "women construction workers"]

CANDIDATES = [
    {"keyword": PRIMARY, "volume": 1900, "global_volume": 5000, "keyword_difficulty": 42,
     "keyword_difficulty_label": "Possible", "intent": ["informational"], "cpc": 5.47,
     "competitive_density": 0.03, "results": 134,
     "serp_features": ["AI Overview", "Video", "Video carousel", "Things to know"]},
    {"keyword": "woman in construction", "volume": 480, "global_volume": 2100, "keyword_difficulty": 38,
     "keyword_difficulty_label": "Possible", "intent": ["informational"], "cpc": 5.47,
     "competitive_density": 0.03},
    {"keyword": "women construction workers", "volume": 390, "global_volume": 1100, "keyword_difficulty": 27,
     "keyword_difficulty_label": "Easy", "intent": ["informational"], "cpc": 4.97,
     "competitive_density": 0.03},
    {"keyword": "women in construction week", "volume": 1600, "keyword_difficulty": 9, "intent": ["informational"], "cpc": 0.00},
    {"keyword": "construction women", "volume": 320, "keyword_difficulty": 22, "intent": ["informational"], "cpc": 5.47},
    {"keyword": "female construction workers", "volume": 170, "keyword_difficulty": 18, "intent": ["informational"], "cpc": 0.00},
    {"keyword": "percentage of women in construction", "volume": 90, "keyword_difficulty": 33, "intent": ["informational"], "cpc": 0.00},
    {"keyword": "women in construction statistics", "volume": 90, "keyword_difficulty": 26, "intent": ["informational"], "cpc": 0.00},
    {"keyword": "women in construction management", "volume": 110, "keyword_difficulty": 12, "intent": ["informational"], "cpc": 6.67},
]

QUESTION_CANDIDATES = [
    {"keyword": "how many women work in construction", "volume": 50, "keyword_difficulty": 26},
    {"keyword": "how many women are in construction", "keyword_difficulty": None},
    {"keyword": "statistics of women in construction", "volume": 40, "keyword_difficulty": 22},
    {"keyword": "when is women in construction week", "volume": 40, "keyword_difficulty": 1},
]

RELATED_CANDIDATES = [
    {"keyword": "women working in construction", "volume": 40, "keyword_difficulty": 18},
    {"keyword": "construction woman", "volume": 140, "keyword_difficulty": 20},
    {"keyword": "women's construction", "volume": 260, "keyword_difficulty": 28},
    {"keyword": "percent of women in construction", "volume": 70, "keyword_difficulty": 32},
    {"keyword": "professional women in construction", "volume": 260, "keyword_difficulty": 44},
    {"keyword": "national association of women in construction", "volume": 720, "keyword_difficulty": 32},
]

SERP_RESULTS = [
    {"position_type": "organic", "domain": "nawic.org", "url": "https://nawic.org/", "triggered_serp_features": ["AI Overview"]},
    {"position_type": "organic", "domain": "ca.gov", "url": "https://www.dir.ca.gov/WomenInConstruction/", "triggered_serp_features": []},
    {"position_type": "organic", "domain": "womeninconstructionconference.com", "url": "https://womeninconstructionconference.com/", "triggered_serp_features": []},
    {"position_type": "organic", "domain": "pwcusa.org", "url": "https://www.pwcusa.org/", "triggered_serp_features": []},
    {"position_type": "organic", "domain": "facebook.com", "url": "https://www.facebook.com/nawicnational/", "triggered_serp_features": []},
    {"position_type": "organic", "domain": "nawic.org", "url": "https://nawic.org/wic-week/", "triggered_serp_features": ["Things to know"]},
    {"position_type": "organic", "domain": "abccarolinas.org", "url": "https://abccarolinas.org/women-in-construction/", "triggered_serp_features": []},
    {"position_type": "organic", "domain": "instagram.com", "url": "https://www.instagram.com/nawicnational/?hl=en", "triggered_serp_features": ["Video carousel"]},
    {"position_type": "organic", "domain": "cie.foundation", "url": "https://www.cie.foundation/wic.html", "triggered_serp_features": []},
    {"position_type": "organic", "domain": "nawicdenver.com", "url": "https://www.nawicdenver.com/", "triggered_serp_features": []},
]

REJECTED = [
    {"keyword": "women in construction week",
     "reason": "Measured at 1,600 US volume and KD 9, but demand is event-dated to March and the legacy week-framed URL has no Google top-100 rankings; the brief pivots to evergreen employer intent and WIC Week stays as a recognition FAQ."},
    {"keyword": "national association of women in construction",
     "reason": "Navigational intent for NAWIC; the organization owns it and the rewrite links NAWIC only as a source."},
    {"keyword": "trades for women",
     "reason": "Owned by the sibling women-in-skilled-trades guide at position 5 (5.4K volume); job-seeker intent differs from this employer guide."},
    {"keyword": "construction labor shortage",
     "reason": "Owned by the existing skilled-trades and trades labor shortage articles; linked rather than targeted."},
]

RATIONALE = (
    "The authenticated US desktop Semrush UI on September 28, 2026 confirms women in construction at "
    "1,900 US volume, KD 42 Possible, informational intent, CPC $5.47, with a SERP of association, "
    "program and social pages plus AI Overview, Video, Video carousel and Things to know. The two "
    "secondaries were measured in the same session: woman in construction (480, KD 38) and women "
    "construction workers (390, KD 27 Easy). The legacy week URL shows no Google top-100 rankings, "
    "and the sibling women-in-skilled-trades guide ranks for trades-for-women job-seeker terms with no "
    "construction keyword in its first 100 rows, so cannibalization risk for the employer angle is low."
)


def _sha(key: str) -> tuple[str, str]:
    path = UI_FILES[key]
    return path.relative_to(ROOT).as_posix(), hashlib.sha256(path.read_bytes()).hexdigest()


def _connector_reports() -> list[dict[str, object]]:
    common = {"execution_surface": SURFACE, "database": "us", "device": "desktop",
              "collection_date": DATE, "run_id": RUN_ID}
    report_params = {
        "_keyword_research": ({**common, "query": PRIMARY,
                               "ui_url": "https://www.semrush.com/analytics/keywordoverview/?q=women+in+construction&db=us"},
                              "primary_overview"),
        "_get_report_schema": ({**common, "report": "phrase_these",
                                "schema_source": "repo guard shape mapped to source-visible Semrush UI fields"},
                               "primary_overview"),
        "phrase_these": ({**common, "keywords": [row["keyword"] for row in CANDIDATES],
                          "ui_views": ["keyword-overview-women-in-construction.txt",
                                       "keyword-overview-woman-in-construction.txt",
                                       "keyword-overview-women-construction-workers.txt",
                                       "keyword-magic-women-in-construction-phrase.txt"]},
                         "primary_overview"),
        "phrase_related": ({**common, "phrase": PRIMARY, "match": "phrase",
                            "ui_url": "https://www.semrush.com/analytics/keywordmagic/?q=women%20in%20construction&db=us&type=phrase&mode=1"},
                           "magic_phrase"),
        "phrase_questions": ({**common, "phrase": PRIMARY,
                              "ui_basis": "Keyword Overview Questions panel (90 keywords, 860 total volume) plus the Keyword Magic Questions view"},
                             "magic_questions"),
        "phrase_organic": ({**common, "phrase": PRIMARY, "display_limit": 10,
                            "ui_basis": "Keyword Overview SERP Analysis positions 1-10"},
                           "primary_overview"),
        "phrase_this": ({**common, "phrase": PRIMARY}, "primary_overview"),
        "url_organic_target": ({**common, "url": TARGET_URL, "data_date_shown": "Sep 27, 2026"}, "positions_target"),
        "url_organic_sibling_cannibalization": ({**common, "url": SIBLING_URL, "data_date_shown": "Sep 27, 2026"},
                                                "positions_sibling"),
        "phrase_fullsearch_broad": ({**common, "phrase": PRIMARY, "match": "all_keywords_broad"}, "magic_broad"),
    }
    reports = []
    for report, (parameters, evidence_key) in report_params.items():
        evidence_path, evidence_sha = _sha(evidence_key)
        reports.append({
            "report": report,
            "status": "completed",
            "parameters": parameters,
            "completion_basis": "Authenticated US desktop Semrush UI fields were visible in the main Chrome browser on 2026-09-28.",
            "ui_evidence_path": evidence_path,
            "ui_evidence_sha256": evidence_sha,
        })
    return reports


def main() -> int:
    decision = build_keyword_decision(
        brand="Simpro",
        market="US",
        database="us",
        collection_date=DATE,
        source_boundary=SOURCE_BOUNDARY,
        seed_terms=[PRIMARY, "woman in construction", "women construction workers", "construction women"],
        connector_reports=_connector_reports(),
        candidate_metrics=CANDIDATES,
        serp_finalists=[{"keyword": PRIMARY, "database": "us", "results": [{"position": i, **row} for i, row in enumerate(SERP_RESULTS, start=1)]}],
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
    print(f"guard findings: {len(findings)}")
    for finding in findings:
        print(f"  {finding['rule_id']}: {finding['message']}")
    return 1 if findings else 0


if __name__ == "__main__":
    raise SystemExit(main())
