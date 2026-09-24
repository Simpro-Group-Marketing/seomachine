"""Persist the current Chrome-verified US SERP and build attested evidence."""
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


QUERY = "best field service management software"
RUN_ID = "d946520a-f4f5-4a48-b11f-266852efb413"
RAW = ROOT / "research" / "serp-chrome-raw-best-field-service-management-software-2026-09-24.json"
EVIDENCE = ROOT / "research" / "serp-evidence-best-field-service-management-software-2026-09-24.json"


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
            "url": "https://www.google.com/search?q=best+field+service+management+software&num=10&hl=en&gl=us&pws=0",
            "locale": {"hl": "en", "gl": "us", "pws": "0"},
        },
        "raw_response": {
            "ai_overview": {
                "answer_pattern": "Routes FSM software by business size and use case rather than naming one universal winner.",
                "visible_route": "Small businesses and solo operators were routed toward Jobber and Housecall Pro.",
                "visible_citations": [
                    "https://www.gartner.com/reviews/market/field-service-management",
                    "https://www.capterra.com/field-service-management-software/",
                ],
                "interpretation_boundary": "The AI Overview is a volatile observation, not proof that its rankings, prices, scale bands, or vendor claims are correct. The article uses only the scenario-routing pattern and verifies vendor facts independently.",
            },
            "features": [
                "AI Overview",
                "Sponsored results",
                "People also ask",
                "Discussions and forums",
                "People also search for",
            ],
            "organic_results": [
                {
                    "title": "6 Best Free Field Service Management Software",
                    "url": "https://connecteam.com/best-free-field-service-management-software/",
                },
                {
                    "title": "Best Field Service Management Reviews 2026",
                    "url": "https://www.gartner.com/reviews/market/field-service-management",
                },
                {
                    "title": "Best Field Service Management Tool?",
                    "url": "https://www.reddit.com/r/lowvoltage/comments/1bnl56d/best_field_service_management_tool/",
                },
                {
                    "title": "Best Field Service Management Software: 2026 Compared",
                    "url": "https://elogii.com/blog/field-service-management-software",
                },
                {
                    "title": "Best Field Service Management Software Picks for Growing Teams",
                    "url": "https://www.reachoutsuite.com/best-field-service-management-software",
                },
                {
                    "title": "Top 10 field service management software 2026",
                    "url": "https://www.ifs.com/en/glossary/compare/top-10-field-service-management-software-2026",
                },
                {
                    "title": "I Found the Best Field Service Management Software of 2026",
                    "url": "https://learn.g2.com/best-field-service-management-software",
                },
            ],
            "paa_questions": [
                "What is the best software for field service management?",
                "What are the top 5 ITSM tools?",
                "Is there a free app for field service management?",
                "Which bpm tool is the best?",
            ],
            "verification_note": "Chrome showed 'Results are not personalized' on the exact hl=en, gl=us, pws=0 request.",
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
            "scenario-based shortlist before the vendor cards",
            "fit by operating model, team complexity, and workflow",
            "consistent 12-tool comparison matrix",
            "methodology and publisher disclosure",
            "official-source vendor cards with mismatch and demo tests",
            "buyer scorecard and role-based demo pack",
        ],
        competitor_gaps=[
            "The query best field service management software has comparison-listicle intent and a different content type from the field service management software homepage, which has different intent as a product proposition.",
            "The current SERP retains comparison, review, and listicle intent, which differs from the indexed homepage product proposition.",
            "The current AI Overview routes by business size and use case, but its visible price and scale bands are not evidence for public copy.",
            "Current results commonly rank tools without giving each buyer a first disqualifying issue and common live-demo test.",
            "Current results rarely give every vendor the same fit, mismatch, official evidence, and live-demo structure.",
            "Broad results do not replace workflow-specific comparison pages for buyers choosing between finalists.",
        ],
    )
    atomic_write_json(EVIDENCE, evidence)
    print(f"raw_capture={RAW.relative_to(ROOT).as_posix()}")
    print(f"serp_evidence={EVIDENCE.relative_to(ROOT).as_posix()}")
    print(f"collected_at={collected_at}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
