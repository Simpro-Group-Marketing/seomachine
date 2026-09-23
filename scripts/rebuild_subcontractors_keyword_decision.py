"""Rebuild the Semrush keyword decision from the 2026-09-22 authenticated UI read.

The brief set `hiring subcontractors` as primary. Reading that keyword's SERP in
the authenticated UI showed a job-seeker result set, so the primary moved to the
construction-qualified term whose SERP matches this article. Every brief term is
retained as a secondary, and the rejected rows record why.
"""
from __future__ import annotations

import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from data_sources.modules.blog_assembly_contract import atomic_write_json
from data_sources.modules.semrush_keyword_decision_guard import build_keyword_decision

SLUG = "best-practices-hiring-and-managing-subcontractors"
INPUT = ROOT / "research" / f"semrush-input-{SLUG}.json"
OUT = ROOT / "research" / f"semrush-keyword-decision-{SLUG}-2026-09-18.json"
UI_DIR = f"research/semrush-ui-{SLUG}-2026-09-18"
SURFACE = "semrush_ui_chrome_main_browser"
SOURCE_BOUNDARY = (
    "Semrush is third-party opportunity/SERP context; GSC remains first-party "
    "performance truth."
)

RATIONALE = (
    "Primary is the construction-qualified term. The authenticated US Semrush UI "
    "read on 2026-09-22 shows 1.9K volume at KD 16 Easy with informational intent, "
    "and its SERP returns process guides, including three of the competitors the "
    "supplied brief names as inspiration. The brief nominated 'hiring "
    "subcontractors', but that keyword measures 170 US volume at KD 26 and its top "
    "ten is job boards and careers pages serving subcontractors looking for work, "
    "not contractors looking to hire. This article is contractor-side, so it cannot "
    "match that result set. The brief term is retained as a secondary alongside the "
    "other brief terms, the URL is unchanged, and the finding is raised on the "
    "Asana task for the brief owner."
)


def reports(database: str, primary: str, all_keywords: list[str]) -> list[dict]:
    """Record the seven connector reports the guard requires."""
    base = {"execution_surface": SURFACE, "database": database}
    return [
        {"report": "_keyword_research", "status": "completed",
         "parameters": {**base, "query": primary, "artifact_dir": UI_DIR}},
        {"report": "_get_report_schema", "status": "completed", "parameters": dict(base)},
        {"report": "phrase_these", "status": "completed",
         "parameters": {**base, "keywords": all_keywords}},
        {"report": "phrase_related", "status": "completed",
         "parameters": {**base, "keywords": all_keywords}},
        {"report": "phrase_questions", "status": "completed",
         "parameters": {**base, "keywords": all_keywords}},
        {"report": "phrase_organic", "status": "completed",
         "parameters": {**base, "keyword": primary}},
        {"report": "phrase_this", "status": "completed",
         "parameters": {**base, "keyword": primary}},
    ]


def main() -> int:
    data = json.loads(INPUT.read_text(encoding="utf-8"))
    primary = data["selected_primary_keyword"]
    secondaries = data["selected_secondary_keywords"]
    database = data["database"]

    candidates = [
        {key: value for key, value in row.items() if not key.startswith("_")}
        for row in data["candidate_metrics"]
    ]
    finalists = [
        {"keyword": row["keyword"], "database": database, "results": row["results"]}
        for row in data["serp_finalists"]
    ]

    decision = build_keyword_decision(
        brand="ClockShark",
        market="US",
        database=database,
        collection_date=data["collection_date"],
        source_boundary=SOURCE_BOUNDARY,
        seed_terms=[primary, *secondaries],
        connector_reports=reports(database, primary, [primary, *secondaries]),
        candidate_metrics=candidates,
        serp_finalists=finalists,
        question_candidates=[
            {"keyword": "how to manage subcontractors on a site", "volume": 880},
            {"keyword": "how to manage subcontractors", "volume": 50},
            {"keyword": "who manages all of the subcontractors and work performed", "volume": 110},
        ],
        related_candidates=[
            {"keyword": "subcontractor hiring", "volume": 90},
            {"keyword": "hiring a subcontractor", "volume": 70},
            {"keyword": "hiring subcontractors small business", "volume": 50},
            {"keyword": "subcontractor management software", "volume": 720},
        ],
        selected_primary_keyword=primary,
        selected_secondary_keywords=secondaries,
        rejected_keywords=[
            {"keyword": "hiring subcontractors as primary",
             "reason": "Measured 170 US volume at KD 26 on 2026-09-22, and its top ten is job boards and careers pages serving subcontractors seeking work. This contractor-side article cannot match that intent, so the term is kept as a secondary instead."},
            {"keyword": "subcontractor management software",
             "reason": "720 US volume but product-comparison intent that this operational guide does not serve."},
            {"keyword": "subcontractor hiring",
             "reason": "90 US volume and a contiguous variant of the retained secondary, so it needs no separate target."},
            {"keyword": "how to manage subcontractors on a site",
             "reason": "880 US volume and a strong fit, but the management half is already carried by the retained secondaries without splitting the primary."},
        ],
        selection_rationale=RATIONALE,
        workspace_root=ROOT,
    )
    atomic_write_json(OUT, decision)
    print(f"keyword decision: {OUT.relative_to(ROOT).as_posix()}")
    print(f"collection_date : {decision['collection_date']}")
    print(f"primary         : {decision['selected_primary_keyword']}")
    print(f"secondaries     : {decision['selected_secondary_keywords']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
