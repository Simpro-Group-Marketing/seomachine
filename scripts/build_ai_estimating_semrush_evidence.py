"""Build authenticated Semrush evidence for the AI estimating software brief."""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from data_sources.modules.blog_assembly_contract import atomic_write_json
from data_sources.modules.editorial_plan.serp_capture import build_serp_evidence
from data_sources.modules.execution_attestation import attest_mapping
from data_sources.modules.semrush_keyword_decision_guard import SOURCE_BOUNDARY, build_keyword_decision

DATE = "2026-09-29"
SLUG = "ai-estimating-software-trade-businesses"
UI_PATH = ROOT / "research" / f"semrush-ui-{SLUG}-{DATE}.txt"
KEYWORD_PATH = ROOT / "research" / f"semrush-keyword-decision-{SLUG}-{DATE}.json"

PRIMARY_QUERY = "ai estimating software"
PILLAR_QUERY = "estimating software"
PRIMARY_RUN_ID = f"{SLUG}-{DATE}-semrush-primary"
PILLAR_RUN_ID = f"{SLUG}-{DATE}-semrush-pillar"

PRIMARY_URLS = [
    "https://www.reddit.com/r/estimators/comments/1il8afs/looking_for_ai_estimating_software_recommendations/",
    "https://www.togal.ai/",
    "https://www.ibeam.ai/",
    "https://drawer.ai/",
    "https://www.trybeam.com/resources/top-ai-construction-estimating-software-and-other-tools",
    "https://thedigitalprojectmanager.com/tools/best-ai-estimating-software/",
    "https://www.trimble.com/blog/construction/en-US/article/stop-counting-start-winning-how-ai-is-transforming-your-estimating-workflow",
    "https://www.stackct.com/stack-assist/",
    "https://www.autodesk.com/blogs/construction/ai-estimating/",
    "https://www.youtube.com/watch?v=-ZfwmItC9o0",
]
PILLAR_URLS = [
    "https://www.planswift.com/",
    "https://www.nichessp.com/blog/most-popular-construction-estimating-software",
    "https://www.reddit.com/r/estimators/comments/1benglf/top_5_estimating_software_programs/",
    "https://www.clearestimates.com/",
    "https://www.autodesk.com/blogs/construction/construction-estimating-software-guide/",
    "https://www.buildxact.com/us/",
    "https://www.estimatingedge.com/",
    "https://methvin.org/",
    "https://www.stackct.com/blog/free-construction-cost-estimating-software/",
    "https://en.wikipedia.org/wiki/Construction_estimating_software",
]


def _now_utc() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _report_url(query: str) -> str:
    return (
        "https://www.semrush.com/analytics/keywordoverview/"
        f"?q={query.replace(' ', '+')}&db=us&fid=562608#serp-analysis"
    )


def _write_serp(
    *,
    query: str,
    run_id: str,
    urls: list[str],
    features: list[str],
    visible_result_count: int,
    label: str,
    must_have_sections: list[str],
    competitor_gaps: list[str],
) -> Path:
    raw_path = ROOT / "research" / f"serp-raw-{label}-{DATE}-semrush.json"
    evidence_path = ROOT / "research" / f"serp-evidence-{label}-{DATE}.json"
    raw = {
        "schema": "simpro-serp-raw-capture/v1",
        "collector": {"name": "research_serp_analysis:semrush", "version": "1.0.0"},
        "query": query,
        "collected_at": _now_utc(),
        "run_id": run_id,
        "request": {"url": "semrush://keyword/phrase_organic", "locale": {"database": "us"}},
        "raw_response": {
            "organic_results": [{"title": url, "url": url} for url in urls],
            "features": features,
            "provenance": {
                "execution_surface": "semrush_ui_chrome_main_browser",
                "browser_instance": "user-authenticated existing Chrome browser",
                "report_url": _report_url(query),
                "visible_report_date": "Sep 29, 2026",
                "device": "Desktop",
                "market": "United States",
                "visible_result_count": visible_result_count,
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
        must_have_sections=must_have_sections,
        competitor_gaps=competitor_gaps,
    )
    atomic_write_json(evidence_path, evidence)
    return evidence_path


def _connector_reports(ui_hash: str, primary_serp_path: Path) -> list[dict[str, object]]:
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
                "ai construction estimating software",
                "ai electrical estimating software",
                "best ai estimating software",
                "ai estimating software for construction",
                "ai quote generator",
                PILLAR_QUERY,
            ],
        },
        "phrase_related": {**common, "phrase": PRIMARY_QUERY},
        "phrase_questions": {**common, "phrase": PRIMARY_QUERY, "ui_result": "Questions n/a"},
        "phrase_organic": {
            **common,
            "phrase": PRIMARY_QUERY,
            "serp_capture_date": DATE,
            "serp_evidence_path": primary_serp_path.relative_to(ROOT).as_posix(),
            "display_limit": 10,
        },
        "phrase_this": {**common, "phrase": PRIMARY_QUERY},
    }
    return [
        {
            "report": name,
            "status": "completed",
            "parameters": parameters,
            "completion_basis": "Authenticated Semrush US desktop Keyword Overview in the user's existing Chrome browser.",
        }
        for name, parameters in values.items()
    ]


def main() -> int:
    primary_evidence_path = _write_serp(
        query=PRIMARY_QUERY,
        run_id=PRIMARY_RUN_ID,
        urls=PRIMARY_URLS,
        features=[
            "Sitelinks",
            "AI Overview",
            "Reviews",
            "Video",
            "Video carousel",
            "Short videos",
            "People also ask",
            "Discussions and forums",
        ],
        visible_result_count=121,
        label=SLUG,
        must_have_sections=[
            "Direct definition and human-review boundary",
            "Estimating workflow mapped from scope to approved quote",
            "Evaluation checklist for trade businesses",
            "Failure modes and human checkpoints",
            "Frequently asked questions based on recorded AnswerSocrates evidence",
        ],
        competitor_gaps=[
            "The observed results mix AI estimating products, recommendation discussions, comparison lists, workflow education, and video; the brief should answer evaluation intent without asserting an unapproved Simpro AI-estimating capability.",
            "Overlap decision: ai estimating software and estimating software have different intent and different content type. The article owns AI-specific educational workflow guidance; the commercial pillar owns the estimating software feature destination."
        ],
    )
    pillar_evidence_path = _write_serp(
        query=PILLAR_QUERY,
        run_id=PILLAR_RUN_ID,
        urls=PILLAR_URLS,
        features=["Sitelinks", "AI Overview", "Reviews", "Video", "Video carousel", "Things to know"],
        visible_result_count=120,
        label="estimating-software-commercial-pillar",
        must_have_sections=["Commercial estimating software category and product evaluation"],
        competitor_gaps=[
            "The observed broad query mixes product homepages, category guides, software lists, a discussion, and a reference page; it is broader and more commercially oriented than the AI-specific workflow article query."
        ],
    )
    primary_serp = json.loads(primary_evidence_path.read_text(encoding="utf-8"))
    ui_hash = hashlib.sha256(UI_PATH.read_bytes()).hexdigest()
    candidate_metrics = [
        {"keyword": PRIMARY_QUERY, "volume": 590, "global_volume": 860, "keyword_difficulty": 35, "keyword_difficulty_label": "Possible", "intent": ["informational"], "cpc": 13.24, "competitive_density": 0.74},
        {"keyword": "ai construction estimating software", "volume": 480, "keyword_difficulty": 25},
        {"keyword": "ai electrical estimating software", "volume": 260, "keyword_difficulty": 13},
        {"keyword": "best ai estimating software", "volume": 110, "keyword_difficulty": 20},
        {"keyword": "ai estimating software for construction", "volume": 70, "keyword_difficulty": 14},
        {"keyword": "ai quote generator", "volume": 880, "global_volume": 2500, "keyword_difficulty": 26, "intent": ["commercial"], "cpc": 1.85, "competitive_density": 0.51},
        {"keyword": PILLAR_QUERY, "volume": 2900, "global_volume": 7700, "keyword_difficulty": 55, "keyword_difficulty_label": "Difficult", "intent": ["informational", "commercial"], "cpc": 15.86, "competitive_density": 0.37},
    ]
    serp_rows = [
        {
            "position": row["position"],
            "position_type": "organic",
            "domain": urlparse(row["url"]).netloc.removeprefix("www."),
            "url": row["url"],
            "triggered_serp_features": [],
        }
        for row in primary_serp["results"]
    ]
    decision = build_keyword_decision(
        brand="Simpro",
        market="US",
        database="us",
        collection_date=DATE,
        source_boundary=SOURCE_BOUNDARY,
        seed_terms=[PRIMARY_QUERY, "AI software for generating estimates and quotes for trade businesses", PILLAR_QUERY, "ai quote generator"],
        connector_reports=_connector_reports(ui_hash, primary_evidence_path),
        candidate_metrics=candidate_metrics,
        serp_finalists=[{"keyword": PRIMARY_QUERY, "database": "us", "results": serp_rows}],
        question_candidates=[],
        related_candidates=[
            {"keyword": "ai construction estimating software", "volume": 480, "keyword_difficulty": 25},
            {"keyword": "ai electrical estimating software", "volume": 260, "keyword_difficulty": 13},
            {"keyword": "best ai estimating software", "volume": 110, "keyword_difficulty": 20},
            {"keyword": "ai estimating software for construction", "volume": 70, "keyword_difficulty": 14},
        ],
        selected_primary_keyword=PRIMARY_QUERY,
        selected_secondary_keywords=[
            "ai construction estimating software",
            "ai electrical estimating software",
            "best ai estimating software",
            "ai estimating software for construction",
        ],
        rejected_keywords=[
            {"keyword": "ai quote generator", "reason": "The visible related clusters are generic quote-maker and inspirational-quote tools, so this term does not reliably express trade-estimating workflow intent."},
            {"keyword": PILLAR_QUERY, "reason": "Reserved for the verified Simpro estimating-software commercial destination; the broader mixed commercial/category SERP differs from the AI-specific evaluation and workflow article SERP."},
        ],
        selection_rationale=(
            "The authenticated Semrush US desktop UI shows informational intent, 590 US volume and KD 35 for ai estimating software. Its live top ten mixes AI estimating products, recommendation and comparison pages, workflow education, discussion, and video. The broader estimating software term has 2,900 US volume, KD 55, informational and commercial intent, and a result set led by software products and general category guides. The article therefore owns AI-specific evaluation and a human-reviewed workflow, while the verified Simpro feature page owns the broader commercial term. Semrush's Questions report returned n/a; AnswerSocrates questions are preserved in a separate receipt-bound artifact."
        ),
        workspace_root=ROOT,
    )
    atomic_write_json(KEYWORD_PATH, decision)
    print(json.dumps({
        "primary_serp": primary_evidence_path.relative_to(ROOT).as_posix(),
        "pillar_serp": pillar_evidence_path.relative_to(ROOT).as_posix(),
        "keyword_decision": KEYWORD_PATH.relative_to(ROOT).as_posix(),
        "keyword_evidence_hash": decision["evidence_hash"],
        "pillar_serp_evidence_hash": json.loads(pillar_evidence_path.read_text(encoding="utf-8"))["evidence_hash"],
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
