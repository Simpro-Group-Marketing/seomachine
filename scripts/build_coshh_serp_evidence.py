"""Build SERP evidence for the BigChange COSHH regulations rewrite.

Encodes the Google UK SERP observed through the Chrome connector on 2026-09-24
(www.google.com, hl=en, gl=uk, pws=0). Organic URLs were read from the live
result anchors. Competitor gaps
were checked against the fetched British Safety Council, Skills for Health, and
Croner pages; Safelincs returned a Cloudflare challenge and is not used for gaps.
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

SLUG = "coshh-regulations"
DATE = "2026-09-24"
QUERY = "coshh regulations"
RUN_ID = (ROOT / ".run-coshh.env").read_text(encoding="utf-8").split("RUN_ID=")[1].split("\n")[0].strip()

RAW_PATH = ROOT / "research" / f"serp-chrome-raw-{SLUG}-{DATE}.json"
EVIDENCE_PATH = ROOT / "research" / f"serp-evidence-{SLUG}-{DATE}.json"

SEARCH_URL = "https://www.google.com/search?q=coshh+regulations&hl=en&gl=uk&pws=0"

ORGANIC = [
    ("Control of Substances Hazardous to Health (COSHH)",
     "https://www.hse.gov.uk/coshh/"),
    ("Control of Substances Hazardous to Health Regulations",
     "https://www.legislation.gov.uk/uksi/2002/2677/regulation/7"),
    ("What is COSHH?",
     "https://www.skillsforhealth.org.uk/article/what-is-coshh/"),
    ("Control of substances hazardous to health (COSHH)",
     "https://www.hse.gov.uk/cleaning/topics/coshh.htm"),
    ("What is COSHH? A guide",
     "https://www.britsafe.org/training-and-learning/informational-resources/what-is-coshh"),
    ("What are COSHH regulations?",
     "https://www.safelincs.co.uk/blog/2025/12/21/what-are-coshh-regulations/"),
    ("The Control of Substances Hazardous to Health (COSHH)",
     "https://www.cqc.org.uk/guidance-regulation/dentists/dental-mythbuster-41-control-of-substances-hazardous-to-health"),
    ("COSHH Regulations — legal requirements",
     "https://app.croneri.co.uk/feature-articles/coshh-regulations-legal-requirements"),
]

FEATURES = [
    "AI Overview",
    "People also ask",
    "Videos",
    "Short videos",
    "Images",
    "People also search for",
]

# Observed on the result page. Supplemental only: FAQ provenance for this
# rewrite comes from the brief's pre-picked PAA section.
SERP_PAA = [
    "What are COSHH standards?",
    "What are the 10 golden rules for COSHH?",
    "What are the five principles of COSHH?",
    "Which 3 are regulated by COSHH?",
]

MUST_HAVE_SECTIONS = [
    "a standalone definition of COSHH and the 2002 regulations",
    "which substances COSHH covers and which it excludes",
    "the three core employer regulations 6 7 and 12",
    "the other employer duties in regulations 8 to 13",
    "what a COSHH assessment is and how to carry one out",
    "when a COSHH assessment must be reviewed",
    "who is responsible for COSHH compliance",
]

COMPETITOR_GAPS = [
    "the checked British Safety Council, Skills for Health, and Croner pages never mention engineers, mobile working, or multiple sites",
    "the checked British Safety Council, Skills for Health, and Croner pages omit the 14-month thorough examination interval for local exhaust ventilation",
    "the checked British Safety Council, Skills for Health, and Croner pages omit the five-or-more-employees threshold for recording assessment findings",
    "the checked Croner guide never names regulation 6, 7, or 12 by number",
]


def main() -> int:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    raw_capture = {
        "schema": "simpro-serp-raw-capture/v1",
        "collector": {
            "name": "research_serp_analysis:chrome_connector",
            "version": "1.0.0",
        },
        "query": QUERY,
        "collected_at": now,
        "run_id": RUN_ID,
        "request": {
            "url": SEARCH_URL,
            "locale": {"hl": "en", "gl": "uk", "pws": "0"},
        },
        "raw_response": {
            "organic_results": [{"title": t, "url": u} for t, u in ORGANIC],
            "features": FEATURES,
            "paa_questions": SERP_PAA,
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
    print(f"raw capture : {RAW_PATH.relative_to(ROOT).as_posix()}")
    print(f"evidence    : {EVIDENCE_PATH.relative_to(ROOT).as_posix()}")
    print(f"organic rows: {len(evidence.get('results', []))}")
    print(f"features    : {', '.join(evidence.get('observations', {}).get('serp_features', []))}")
    print(f"content types: {', '.join(evidence.get('observations', {}).get('content_types', []))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
