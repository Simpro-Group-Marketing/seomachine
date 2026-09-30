"""Build the 2026-09-28 Semrush keyword decision for the electrical buyer guide."""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from data_sources.modules.blog_assembly_contract import atomic_write_json
from data_sources.modules.semrush_keyword_decision_guard import SOURCE_BOUNDARY, build_keyword_decision

SLUG = "best-electrical-job-management-software"
DATE = "2026-09-28"
UI = ROOT / "research" / f"semrush-ui-{SLUG}-{DATE}.txt"
SERP = ROOT / "research" / f"serp-evidence-{SLUG}-{DATE}.json"
OUT = ROOT / "research" / f"semrush-keyword-decision-{SLUG}-{DATE}.json"
PRIMARY = "electrical job management software"
SECONDARIES = [
    "electrical contractor job management software",
    "job management software for electrical contractors",
]

CANDIDATES = [
    {"keyword": PRIMARY, "volume": 320, "global_volume": 960, "keyword_difficulty": 26,
     "keyword_difficulty_label": "Easy", "intent": ["commercial"], "cpc": 54.74,
     "competitive_density": 0.05},
    {"keyword": "electrical contractor job management software", "volume": 210, "keyword_difficulty": 21},
    {"keyword": "job management software for electrical contractor", "volume": 210, "keyword_difficulty": 23},
    {"keyword": "job management software for electrical contractors", "volume": 70, "keyword_difficulty": 25},
    {"keyword": "job management software benefits for electrical service businesses", "volume": 20,
     "keyword_difficulty": None},
]


def reports(evidence_hash: str) -> list[dict[str, object]]:
    common = {"execution_surface": "semrush_ui_chrome_main_browser", "database": "us",
              "device": "desktop", "collection_date": DATE, "ui_evidence_path": UI.relative_to(ROOT).as_posix(),
              "ui_evidence_sha256": evidence_hash}
    params = {
        "_keyword_research": {**common, "query": PRIMARY},
        "_get_report_schema": {**common, "report": "phrase_this"},
        "phrase_these": {**common, "keywords": [r["keyword"] for r in CANDIDATES]},
        "phrase_related": {**common, "phrase": PRIMARY},
        "phrase_questions": {**common, "phrase": PRIMARY, "ui_result": "Questions n/a"},
        "phrase_organic": {**common, "phrase": PRIMARY, "serp_capture_date": DATE,
                           "display_limit": 10},
        "phrase_this": {**common, "phrase": PRIMARY},
    }
    return [{"report": name, "status": "completed", "parameters": value,
             "completion_basis": "Authenticated Semrush US desktop Keyword Overview in the main Chrome browser."}
            for name, value in params.items()]


def main() -> int:
    serp = json.loads(SERP.read_text(encoding="utf-8"))
    ui_hash = hashlib.sha256(UI.read_bytes()).hexdigest()
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
        brand="Simpro", market="US", database="us", collection_date=DATE,
        source_boundary=SOURCE_BOUNDARY,
        seed_terms=[PRIMARY, "electrical contractor software", *SECONDARIES],
        connector_reports=reports(ui_hash), candidate_metrics=CANDIDATES,
        serp_finalists=[{"keyword": PRIMARY, "database": "us", "results": serp_rows}], question_candidates=[],
        related_candidates=[
            {"keyword": "software for electricians", "intent": ["informational", "commercial"]},
            {"keyword": "electrical contractor invoicing software", "intent": ["informational", "commercial"]},
            {"keyword": "electrical scheduling software", "intent": ["commercial"]},
            {"keyword": "best software for electrical contractors", "intent": ["informational", "commercial"]},
        ],
        selected_primary_keyword=PRIMARY, selected_secondary_keywords=SECONDARIES,
        rejected_keywords=[
            {"keyword": "electrical contractor software", "reason": "Reserved for the verified industry commercial pillar; the blog owns comparison and shortlisting intent."},
            {"keyword": "electrical scheduling software", "reason": "Too narrow for the guide's estimating, costing, maintenance and project evaluation scope."},
        ],
        selection_rationale=(
            "The authenticated Semrush US desktop UI on September 28, 2026 shows commercial intent, "
            "320 US volume and KD 26 for electrical job management software. The broader electrical "
            "contractor software term has 1,300 US volume and KD 21 but remains assigned to the industry "
            "commercial pillar. The authenticated September 28 SERP Analysis shows 133 results and a top "
            "ten dominated by vendor category pages, with the existing Simpro comparison at position eight. "
            "The rewrite keeps the comparison keyword while differentiating through job-mix routing and "
            "equal live-demo tests."
        ), workspace_root=ROOT,
    )
    atomic_write_json(OUT, decision)
    print(f"wrote {OUT.relative_to(ROOT).as_posix()} evidence={decision['evidence_hash']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
