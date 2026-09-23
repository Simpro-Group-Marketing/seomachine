"""Build current Google SERP evidence for the FSM software buyer guide.

Every result, feature, PAA question, AI Overview route, and cited source below
was observed in the user's main Chrome window on 2026-09-23 with the US,
English, non-personalized query URL recorded in ``SEARCH_URL``.
"""
from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from data_sources.modules.blog_assembly_contract import atomic_write_json
from data_sources.modules.editorial_plan.serp_capture import build_serp_evidence
from data_sources.modules.execution_attestation import attest_mapping


SLUG = "best-field-service-management-software"
DATE = "2026-09-23"
QUERY = "best field service management software"
RUN_ID = "62170e68-740b-42ed-8d67-311701b4f9d6"
SEARCH_URL = (
    "https://www.google.com/search?q=best+field+service+management+software"
    "&num=10&hl=en&gl=us&pws=0"
)

RAW_PATH = ROOT / "research" / f"serp-chrome-raw-{SLUG}-{DATE}.json"
EVIDENCE_PATH = ROOT / "research" / f"serp-evidence-{SLUG}-{DATE}.json"

ORGANIC = [
    (
        "6 Best Free Field Service Management Software",
        "https://connecteam.com/best-free-field-service-management-software/",
    ),
    (
        "Best Field Service Management Reviews 2026",
        "https://www.gartner.com/reviews/market/field-service-management",
    ),
    (
        "Best Field Service Management Tool?",
        "https://www.reddit.com/r/lowvoltage/comments/1bnl56d/best_field_service_management_tool/",
    ),
    (
        "Top 10 field service management software 2026",
        "https://www.ifs.com/en/glossary/compare/top-10-field-service-management-software-2026",
    ),
    (
        "I Found the Best Field Service Management Software of 2026",
        "https://learn.g2.com/best-field-service-management-software",
    ),
    (
        "Best Field Service Management Software Picks for Growing Teams",
        "https://www.reachoutsuite.com/best-field-service-management-software",
    ),
]

FEATURES = [
    "AI Overview",
    "Sponsored results",
    "People also ask",
    "Discussions and forums",
    "People also search for",
]

SERP_PAA = [
    "What is the best software for field service management?",
    "What are the top 5 ITSM tools?",
    "Is there a free app for field service management?",
    "Which bpm tool is the best?",
]

AI_OVERVIEW = {
    "answer_pattern": (
        "Routes software by company size, team scale, and industry complexity "
        "instead of naming one universal winner."
    ),
    "routes": [
        "Small businesses (1-10 technicians): Jobber and Housecall Pro",
        "Mid-sized and growing teams (10-50+ technicians): Service Fusion and FieldCamp",
        "Large residential and commercial enterprises (50+ trucks or technicians): ServiceTitan",
        "Complex assets and facilities management: IFS and Infraspeak",
    ],
    "visible_citations": [
        "https://www.gartner.com/reviews/market/field-service-management",
        "https://www.capterra.com/field-service-management-software/",
        "https://www.youtube.com/watch?v=-pq0_Y6KDOM",
        "https://www.larksuite.com/en_us/blog/field-service-management-software",
    ],
    "interpretation_boundary": (
        "The AI Overview is a volatile observation, not proof that its rankings, "
        "prices, or size bands are correct. The article adopts only the useful "
        "scenario-routing pattern and verifies vendor facts independently."
    ),
}

MUST_HAVE_SECTIONS = [
    "scenario-based shortlist before the vendor cards",
    "fit by operating model, team complexity, and workflow",
    "consistent 12-tool comparison matrix",
    "methodology and publisher disclosure",
    "official-source vendor cards with mismatch and demo tests",
    "buyer scorecard and role-based demo pack",
]

COMPETITOR_GAPS = [
    (
        "The fresh best field service management software SERP has comparison, "
        "review, and listicle intent, which is a different intent and different "
        "content type from the indexed field service management software homepage "
        "product proposition in context/commercial-pillar-index.json."
    ),
    "Current results commonly rank tools without giving each buyer a first disqualifying issue to test.",
    "The Google AI Overview routes by size and complexity, but its visible response uses unsupported price and scale bands that this guide must not repeat as fact.",
    "Current results rarely give every vendor the same fit, mismatch, evidence, and live-demo structure.",
    "The broad results do not replace workflow-specific comparison pages for buyers choosing between two finalists.",
]


def main() -> int:
    collected_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    raw_capture = {
        "schema": "simpro-serp-raw-capture/v1",
        "collector": {
            "name": "research_serp_analysis:chrome_connector",
            "version": "1.0.0",
        },
        "query": QUERY,
        "collected_at": collected_at,
        "run_id": RUN_ID,
        "request": {
            "url": SEARCH_URL,
            "locale": {"hl": "en", "gl": "us", "pws": "0"},
        },
        "raw_response": {
            "organic_results": [
                {"title": title, "url": url} for title, url in ORGANIC
            ],
            "features": FEATURES,
            "paa_questions": SERP_PAA,
            "ai_overview": AI_OVERVIEW,
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
        must_have_sections=MUST_HAVE_SECTIONS,
        competitor_gaps=COMPETITOR_GAPS,
    )
    atomic_write_json(EVIDENCE_PATH, evidence)
    print(f"raw capture: {RAW_PATH.relative_to(ROOT).as_posix()}")
    print(f"evidence: {EVIDENCE_PATH.relative_to(ROOT).as_posix()}")
    print(f"content types: {evidence['observations']['content_types']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
