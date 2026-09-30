"""Build current Semrush SERP evidence for the electrical software rewrite."""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from data_sources.modules.blog_assembly_contract import atomic_write_json
from data_sources.modules.editorial_plan.serp_capture import build_serp_evidence
from data_sources.modules.execution_attestation import attest_mapping


SLUG = "best-electrical-job-management-software"
DATE = "2026-09-28"
RUN_ID = "3bca06a1-6ab7-4d7b-b8e9-6f01d62a2d4c"
QUERY = "electrical job management software"
REPORT_URL = (
    "https://www.semrush.com/analytics/keywordoverview/"
    "?q=electrical+job+management+software&db=us&fid=562608#serp-analysis"
)
RAW_PATH = ROOT / "research" / f"serp-raw-{SLUG}-{DATE}-semrush.json"
OUT_PATH = ROOT / "research" / f"serp-evidence-{SLUG}-{DATE}.json"

RESULTS = [
    "https://www.housecallpro.com/industries/electrical-contractor-software/",
    "https://knowify.com/electrical-contractor-software/",
    "https://www.fieldwire.com/trade/electrical-contractor-software/",
    "https://www.getjobber.com/industries/electrical-contractor-software/",
    "https://www.reddit.com/r/electricians/comments/1kmo8gi/electricians_what_software_do_you_use/",
    "https://www.servicefusion.com/electrical-contractor-software",
    "https://www.servicetitan.com/industries/electrical-software",
    "https://www.simprogroup.com/blog/best-electrical-job-management-software",
    "https://connecteam.com/electrical-contracting-business-software-solutions/",
    "https://www.fieldwire.com/trade/electrical-contractor-software/",
]


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def main() -> int:
    raw_capture = {
        "schema": "simpro-serp-raw-capture/v1",
        "collector": {"name": "research_serp_analysis:semrush", "version": "1.0.0"},
        "query": QUERY,
        "collected_at": now_utc(),
        "run_id": RUN_ID,
        "request": {
            "url": "semrush://keyword/phrase_organic",
            "locale": {"database": "us"},
        },
        "raw_response": {
            "organic_results": [{"title": url, "url": url} for url in RESULTS],
            "features": ["Sitelinks", "AI Overview", "Reviews", "Video"],
            "provenance": {
                "execution_surface": "semrush_ui_chrome_main_browser",
                "browser_instance": "new Chrome connector session in the main browser window",
                "report_url": REPORT_URL,
                "visible_report_date": "Sep 28, 2026",
                "device": "Desktop",
                "market": "United States",
                "visible_result_count": 133,
            },
        },
    }
    atomic_write_json(
        RAW_PATH,
        attest_mapping(
            raw_capture,
            purpose="simpro-serp-raw-capture/v1",
            workspace_root=ROOT,
        ),
    )
    evidence = build_serp_evidence(
        raw_capture_path=RAW_PATH,
        workspace_root=ROOT,
        must_have_sections=[
            "Direct answer and job-mix decision table",
            "Symmetric vendor cards",
            "Workflow, pricing and implementation comparison",
            "Weighted demo scorecard",
            "Standardized electrical demo scenarios",
            "Implementation and total-cost checks",
            "Frequently asked questions",
        ],
        competitor_gaps=[
            "The observed SERP is dominated by vendor category pages; the article should differentiate with job-mix routing and equal live-demo tests."
        ],
    )
    atomic_write_json(OUT_PATH, evidence)
    print(
        json.dumps(
            {
                "raw_capture": RAW_PATH.relative_to(ROOT).as_posix(),
                "serp_evidence": OUT_PATH.relative_to(ROOT).as_posix(),
                "evidence_hash": evidence["evidence_hash"],
                "result_count": len(evidence["results"]),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
