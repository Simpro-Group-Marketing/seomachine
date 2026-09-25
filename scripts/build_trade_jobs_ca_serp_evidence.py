"""Persist the Chrome-observed US SERP for the California trades rewrite and build attested evidence.

The raw capture below is an agent-transcribed ``chrome_connector`` observation of
the Google results page loaded in the authenticated main Chrome profile on
2026-09-24 (hl=en, gl=us, pws=0; Chrome showed "Results are not personalized").
Browser-extension panels (Answer Socrates) and the owner-only Search Console
insight card were visible on the page but are not Google SERP features and are
excluded from the feature list.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from data_sources.modules.blog_assembly_contract import atomic_write_json
from data_sources.modules.editorial_plan.contracts import (
    SERP_RAW_CAPTURE_ATTESTATION_PURPOSE,
)
from data_sources.modules.editorial_plan.serp_capture import build_serp_evidence
from data_sources.modules.execution_attestation import attest_mapping


QUERY = "highest paying trades in california"
RUN_ID = "0f23f31d-46c1-4b8c-936e-2b2edb8dbbf5"
SLUG = "best-trade-jobs-california"
DATE = "2026-09-24"
RAW = ROOT / "research" / f"serp-chrome-raw-{SLUG}-{DATE}.json"
EVIDENCE = ROOT / "research" / f"serp-evidence-{SLUG}-{DATE}.json"


def main() -> int:
    collected_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    raw_payload = {
        "schema": "simpro-serp-raw-capture/v1",
        "collector": {
            "name": "research_serp_analysis:chrome_connector",
            "version": "1.0.0",
        },
        "query": QUERY,
        "collected_at": collected_at,
        "run_id": RUN_ID,
        "request": {
            "url": "https://www.google.com/search?q=highest+paying+trades+in+california&num=10&hl=en&gl=us&pws=0",
            "locale": {"hl": "en", "gl": "us", "pws": "0"},
        },
        "raw_response": {
            "ai_overview": {
                "answer_pattern": (
                    "Names elevator installers and repairers, electrical power-line "
                    "installers, and aircraft mechanics as the highest-paying California "
                    "trades, then lists top-paying trades with one-line role descriptions "
                    "and a How to Get Started section on apprenticeships."
                ),
                "visible_sections": [
                    "Top-Paying Trades in California",
                    "How to Get Started",
                ],
                "visible_list_items": [
                    "Elevator Installers and Repairers",
                    "Electrical Power-Line Installers and Repairers",
                    "Aircraft Mechanics and Service Technicians",
                    "Plumbers, Pipefitters, and Steamfitters",
                    "Electricians (Commercial and Industrial)",
                ],
                "visible_citations": [
                    "https://tallo.com/careers/job-search/highest-paying-trade-jobs-in-california/",
                    "https://abcnorcal.org/highest-paying-trade-jobs/",
                    "https://www.ziprecruiter.com/Jobs/Highest-Paying-Trade/-in-Los-Angeles,CA",
                    "https://www.reddit.com/r/careerguidance/comments/16dfz0s/best_trade_job/",
                    "https://www.indeed.com/q-entry-level-trade-l-california-jobs.html",
                    "https://www.simprogroup.com/blog/best-trade-jobs-california",
                    "https://techniciansofamerica.com/blog/highest-paying-trade-jobs",
                    "https://superiorskilledtrades.com/highest-paying-trade-jobs/",
                    "https://www.ziprecruiter.com/Jobs/Best-Paying-Trade/--in-California",
                ],
                "simpro_cited": True,
                "interpretation_boundary": (
                    "The AI Overview is a volatile observation, not proof that its "
                    "rankings, salary claims, or percentage comparisons are correct. "
                    "The rewrite uses only the answer shape (top 3 named trades before a "
                    "ranked list) and verifies every salary figure against BLS or "
                    "California EDD data independently."
                ),
            },
            "features": [
                "AI Overview",
                "People also ask",
                "People also search for",
            ],
            "organic_results": [
                {
                    "title": "18 Best Trade Jobs in California: Descriptions & Salaries!",
                    "url": "https://www.simprogroup.com/blog/best-trade-jobs-california",
                },
                {
                    "title": "Best trade job? : r/careerguidance",
                    "url": "https://www.reddit.com/r/careerguidance/comments/16dfz0s/best_trade_job/",
                },
                {
                    "title": "Top 10 Highest Paying Trade Jobs for 2025",
                    "url": "https://abcnorcal.org/highest-paying-trade-jobs/",
                },
                {
                    "title": "Highest Paying Careers",
                    "url": "https://www.careeronestop.org/Toolkit/Wages/highest-paying-careers.aspx?persist=true&location=CA",
                },
                {
                    "title": "22 High-Paid Trade School Jobs in Los Angeles (With ...",
                    "url": "https://www.indeed.com/career-advice/finding-a-job/high-paid-trade-school-jobs-los-angeles",
                },
                {
                    "title": "Highest Paying Trade Jobs in California",
                    "url": "https://tallo.com/careers/job-search/highest-paying-trade-jobs-in-california/",
                },
                {
                    "title": "15 Highest-Paying Trade Jobs You Can Start Now (2026)",
                    "url": "https://techniciansofamerica.com/blog/highest-paying-trade-jobs",
                },
                {
                    "title": "Skilled Trades Jobs: Your Guide to Construction Careers",
                    "url": "https://abcsocal.org/skilled-trades-jobs/",
                },
            ],
            "paa_questions": [
                "What jobs pay $4000 a week without a degree?",
                "What jobs make $500,000 a year in California?",
                "What jobs make $200,000 in California?",
                "What job makes $10,000 a month without a degree?",
            ],
            "people_also_search_for": [
                "Top 10 highest paying trades in california",
                "Highest paying trades in california without a degree",
                "Highest paying trades in california reddit",
                "Highest paying trades in california without a",
                "Trade jobs that pay $100K",
                "Highest paying trade jobs without a degree",
                "Highest paying trades for women",
                "Top 10 highest-paying trade jobs without a degree",
            ],
            "not_observed": [
                "Sponsored results",
                "Video carousel",
                "Short videos module",
                "Discussions and forums module (the Reddit thread appeared as a standard organic result with answer counts and two sub-threads)",
                "Images pack",
            ],
            "verification_note": (
                "Chrome showed 'Results are not personalized' on the exact hl=en, gl=us, "
                "pws=0 request. Eight organic web results appeared on page 1. Semrush "
                "SERP Analysis for the same query (US desktop, 2026-09-24) separately "
                "reports Sitelinks, AI Overview, Video, and Discussions and forums; "
                "those Semrush features are recorded in the keyword decision artifact, "
                "not here."
            ),
        },
    }
    attested_raw = attest_mapping(
        raw_payload,
        purpose=SERP_RAW_CAPTURE_ATTESTATION_PURPOSE,
        workspace_root=ROOT,
    )
    atomic_write_json(RAW, attested_raw)

    evidence = build_serp_evidence(
        raw_capture_path=RAW,
        workspace_root=ROOT,
        must_have_sections=[
            "direct answer naming the top 3 to 5 highest-paying California trades before the list",
            "at-a-glance comparison table ranked on one California salary dataset",
            "salary methodology and data year stated early",
            "consistent per-trade structure with pay, training route, and licensing",
            "what affects trade salaries in California",
            "how to choose a trade and apprenticeship entry routes",
        ],
        competitor_gaps=[
            "The AI Overview and several results mix salary sources and years; one consistent California dataset with a stated year is uncommon.",
            "Several results mix non-trade occupations (dental hygienist, web developer, occupational therapy assistant, neurologists) into trade rankings.",
            "Results rarely pair each California salary with training length, licensing, and overtime or union effects in the same structure.",
            "People also ask and People also search for lean toward degree-free and $100K earning questions, which the ranked list can answer directly.",
            "The current Simpro result is dated May 17, 2024 and its visible snippet mixes role titles (Electrical Systems Expert, Electrical Grid Worker) that do not match standard occupation names.",
        ],
    )
    atomic_write_json(EVIDENCE, evidence)
    print(f"raw_capture={RAW.relative_to(ROOT).as_posix()}")
    print(f"serp_evidence={EVIDENCE.relative_to(ROOT).as_posix()}")
    print(f"collected_at={collected_at}")
    print(f"run_id={evidence['run_id']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
