"""Persist the Chrome-observed US SERP for the women-in-construction rewrite and build attested evidence.

The raw capture below is an agent-transcribed ``chrome_connector`` observation of
the Google results page loaded in the main Chrome profile on 2026-09-28
(hl=en, gl=us, pws=0; Chrome showed "Results are not personalized"). Google
showed "Can't generate an AI overview right now. Try again later." on two loads,
so AI Overview is recorded as not rendered here; Semrush SERP Analysis reports it
separately in the keyword decision artifact.
"""
from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from data_sources.modules.blog_assembly_contract import atomic_write_json  # noqa: E402
from data_sources.modules.editorial_plan.contracts import (  # noqa: E402
    SERP_RAW_CAPTURE_ATTESTATION_PURPOSE,
)
from data_sources.modules.editorial_plan.serp_capture import build_serp_evidence  # noqa: E402
from data_sources.modules.execution_attestation import attest_mapping  # noqa: E402

QUERY = "women in construction"
RUN_ID = "f1130b43-7baa-4ac4-9bcc-b26c15dde6b6"
SLUG = "women-in-construction"
DATE = "2026-09-28"
RAW = ROOT / "research" / f"serp-chrome-raw-{SLUG}-{DATE}.json"
EVIDENCE = ROOT / "research" / f"serp-evidence-{SLUG}-{DATE}.json"

ORGANIC = [
    ("NAWIC.ORG", "https://nawic.org/"),
    ("Women in Construction", "https://womeninconstructionconference.com/"),
    ("NAWIC Miami - Home", "https://nawicmiami.com/"),
    ("WIC Week", "https://nawic.org/wic-week/"),
    ("National Association of Women in Construction", "https://www.facebook.com/nawicnational/"),
    ("Numbers Matter: Women Working in Construction", "https://iwpr.org/articles/numbers-matter-women-working-in-construction-3/"),
    ("Women in Construction - Biloxi", "https://www.moorecommunityhouse.org/winc"),
    ("Superior Women in Construction (SWiC)", "https://www.superiorconstruction.com/our-company/superior-women-in-construction-swic/"),
    ("Women in construction : r/ConstructionManagers", "https://www.reddit.com/r/ConstructionManagers/comments/180kl58/women_in_construction/"),
    ("Women Represent Highest Share of Construction Industry Personnel in ...", "https://www.nahb.org/blog/2025/09/women-represent-highest-share-of-construction-industry-personnel-in-20-years"),
    ("Women in Construction: Challenges and Solutions Ahead - EasyLlama", "https://www.easyllama.com/blog/women-in-construction-challenges-solutions-and-the-path-forward"),
    ("How NAWIC helps women in construction advance their careers", "https://nawic.org/how-nawic-helps-women-in-construction-advance-their-careers/"),
    ("Beyond the Jobsite: Women in Construction Leadership Roles", "https://www.davron.net/women-in-construction-leadership/"),
]


def main() -> int:
    collected_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    raw_payload = {
        "schema": "simpro-serp-raw-capture/v1",
        "collector": {"name": "research_serp_analysis:chrome_connector", "version": "1.0.0"},
        "query": QUERY,
        "collected_at": collected_at,
        "run_id": RUN_ID,
        "request": {
            "url": "https://www.google.com/search?q=women+in+construction&num=10&hl=en&gl=us&pws=0",
            "locale": {"hl": "en", "gl": "us", "pws": "0"},
        },
        "raw_response": {
            "ai_overview": {
                "answer_pattern": "Not rendered: Google showed 'Can't generate an AI overview right now. Try again later.' on two loads.",
                "visible_sections": [],
                "visible_list_items": [],
                "visible_citations": [],
                "simpro_cited": False,
                "interpretation_boundary": "No AI Overview content was observed, so none is used as evidence.",
            },
            "features": [
                "People also ask",
                "Things to know",
                "Videos",
                "Short videos",
                "Images",
                "People also search for",
                "Sponsored",
            ],
            "organic_results": [{"title": title, "url": url} for title, url in ORGANIC],
            "paa_questions": [
                "What is the theme for women in construction Week in 2026?",
                "Is construction a good job for women?",
                "What percentage of the construction industry is women?",
                "Why are women in construction important?",
            ],
            "things_to_know": [
                "When is Women in Construction Week?",
                "What are the statistics on women in construction?",
                "What are the challenges faced by women in construction?",
                "What are the educational programs for women in construction?",
                "What is the role of women in construction leadership?",
            ],
            "people_also_search_for": [
                "Women in construction Week",
                "Women in Construction Conference",
                "Women in construction jobs",
                "Women in construction course",
                "Women in construction (WIC)",
                "Women in construction Month",
                "Women in construction Statistics",
                "Women in Construction organization",
            ],
            "not_observed": [
                "AI Overview content (generation error shown)",
                "Top stories",
                "Discussions and forums module (the Reddit thread appeared as a standard organic result)",
            ],
            "verification_note": (
                "Chrome showed 'Results are not personalized' on the exact hl=en, gl=us, pws=0 request. "
                "Semrush SERP Analysis for the same query (US desktop, 2026-09-28) separately reports "
                "AI Overview, Video, Video carousel, and Things to know; those Semrush features are "
                "recorded in the keyword decision artifact, not here."
            ),
        },
    }
    atomic_write_json(RAW, attest_mapping(raw_payload, purpose=SERP_RAW_CAPTURE_ATTESTATION_PURPOSE, workspace_root=ROOT))
    evidence = build_serp_evidence(
        raw_capture_path=RAW,
        workspace_root=ROOT,
        must_have_sections=[
            "direct answer on the share of women in construction with an official source",
            "role-level statistics table for women's share of construction jobs",
            "challenges women face in construction and what employers control",
            "career pathways, apprenticeship and leadership roles",
            "recruiting and retention actions for contractors",
            "Women in Construction Week timing as a recognition moment",
        ],
        competitor_gaps=[
            "Page one is dominated by association, chapter, conference and social profile pages that do not give contractors an employer playbook.",
            "Statistics results report shares without role-level breakdowns from one current official dataset.",
            "No result pairs recruiting and retention actions with a time-bound roadmap for trade business owners.",
            "The legacy Simpro week URL does not rank; Semrush shows no Google top-100 data for it.",
        ],
    )
    atomic_write_json(EVIDENCE, evidence)
    print(f"serp_evidence={EVIDENCE.relative_to(ROOT).as_posix()} content_types={evidence['observations']['content_types']} features={evidence['observations']['serp_features']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
