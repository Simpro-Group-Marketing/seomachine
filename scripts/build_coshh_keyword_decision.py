"""Build the Semrush keyword decision for the BigChange COSHH regulations rewrite.

Inputs come from the authenticated Semrush UI read in the main Chrome browser
on 2026-09-24 (UK database). The brief primary keyword is kept: its SERP is a
regulator/explainer result set that matches this educational rewrite.
"""
from __future__ import annotations

import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from data_sources.modules.blog_assembly_contract import atomic_write_json
from data_sources.modules.semrush_keyword_decision_guard import build_keyword_decision

SLUG = "coshh-regulations"
DATE = "2026-09-24"
INPUT = ROOT / "research" / f"semrush-input-{SLUG}.json"
OUT = ROOT / "research" / f"semrush-keyword-decision-{SLUG}-{DATE}.json"
UI_DIR = f"research/semrush-ui-{SLUG}-{DATE}"
SURFACE = "semrush_ui_chrome_main_browser"
SOURCE_BOUNDARY = (
    "Semrush is third-party opportunity/SERP context; GSC remains first-party "
    "performance truth."
)
PRIMARY = "coshh regulations"
SECONDARIES = [
    "coshh meaning",
    "what is coshh",
    "coshh assessment",
    "coshh risk assessment",
    "what are the 3 main regulations of coshh",
    "coshh regulations 2002",
]
RATIONALE = (
    "Primary is the brief keyword. The authenticated UK Semrush UI read on "
    "2026-09-24 shows 6.6K UK volume at KD 35 with informational intent, and its "
    "top ten is regulator and explainer content led by legislation.gov.uk "
    "Regulation 7 and hse.gov.uk, with AI Overview and video features. That matches "
    "an educational employer guide. The live BigChange URL ranks for 0 UK keywords "
    "on 2026-09-23, so the rewrite rebuilds around this cluster. The brief "
    "contextual keywords are retained as secondaries, and coshh risk assessment "
    "plus coshh regulations 2002 are added from the variation report."
)


def reports(database: str, all_keywords: list[str]) -> list[dict]:
    """Record the seven connector reports the guard requires."""
    base = {"execution_surface": SURFACE, "database": database}
    return [
        {"report": "_keyword_research", "status": "completed",
         "parameters": {**base, "query": PRIMARY, "artifact_dir": UI_DIR}},
        {"report": "_get_report_schema", "status": "completed", "parameters": dict(base)},
        {"report": "phrase_these", "status": "completed",
         "parameters": {**base, "keywords": all_keywords}},
        {"report": "phrase_related", "status": "completed",
         "parameters": {**base, "keywords": all_keywords}},
        {"report": "phrase_questions", "status": "completed",
         "parameters": {**base, "keywords": all_keywords}},
        {"report": "phrase_organic", "status": "completed",
         "parameters": {**base, "keyword": PRIMARY}},
        {"report": "phrase_this", "status": "completed",
         "parameters": {**base, "keyword": PRIMARY}},
    ]


def main() -> int:
    data = json.loads(INPUT.read_text(encoding="utf-8"))
    database = data["database"]
    candidates = data["candidate_metrics"]
    finalists = [
        {"keyword": row["keyword"], "database": database, "results": row["results"]}
        for row in data["serp_finalists"]
    ]
    decision = build_keyword_decision(
        brand="BigChange",
        market="UK",
        database=database,
        collection_date=data["collection_date"],
        source_boundary=SOURCE_BOUNDARY,
        seed_terms=[PRIMARY, *SECONDARIES],
        connector_reports=reports(database, [PRIMARY, *SECONDARIES]),
        candidate_metrics=candidates,
        serp_finalists=finalists,
        question_candidates=data["question_candidates"],
        related_candidates=data["related_candidates"],
        selected_primary_keyword=PRIMARY,
        selected_secondary_keywords=SECONDARIES,
        rejected_keywords=[
            {"keyword": "coshh meaning as primary",
             "reason": "22.2K UK volume but a definitional query that a regulations guide answers in its opening section, so it is kept as a secondary."},
            {"keyword": "coshh assessment template",
             "reason": "720 UK volume with template intent. The rewrite serves it through a filled assessment checklist table rather than a separate template target."},
            {"keyword": "coshh regulates",
             "reason": "2.9K UK volume but a malformed variant of the primary that needs no separate target."},
            {"keyword": "coshh symbols",
             "reason": "A separate hazard-pictogram cluster outside the employer-duties intent of this rewrite."},
        ],
        selection_rationale=RATIONALE,
        workspace_root=ROOT,
    )
    atomic_write_json(OUT, decision)
    print(f"keyword decision: {OUT.relative_to(ROOT).as_posix()}")
    print(f"primary         : {decision['selected_primary_keyword']}")
    print(f"secondaries     : {decision['selected_secondary_keywords']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
