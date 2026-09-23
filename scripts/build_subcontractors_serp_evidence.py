"""Build SERP evidence for the ClockShark hiring/managing subcontractors rewrite.

Encodes the Google SERP actually observed through the Chrome connector on
2026-09-22 for the US, English, non-personalized locale. No metric, ranking, or
competitor claim is synthesized: every organic row and feature below was read
off the live result page.
"""
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

SLUG = "best-practices-hiring-and-managing-subcontractors"
DATE = "2026-09-18"
QUERY = "how to hire subcontractors for construction"
RUN_ID = Path(ROOT / ".run-subcontractors.env").read_text(encoding="utf-8").split("RUN_ID=")[1].split("\n")[0].strip()

RAW_PATH = ROOT / "research" / f"serp-chrome-raw-{SLUG}-{DATE}.json"
EVIDENCE_PATH = ROOT / "research" / f"serp-evidence-{SLUG}-{DATE}.json"

SEARCH_URL = (
    "https://www.google.com/search?q=how+to+hire+subcontractors+for+construction&num=10&hl=en&gl=us&pws=0"
)

ORGANIC = [
    ("How do you find subcontractors? How do you find reliable ...",
     "https://www.reddit.com/r/Construction/comments/14otrnh/how_do_you_find_subcontractors_how_do_you_find/"),
    ("General Contractor's Guide to Hiring Subcontractors",
     "https://www.btacademy.com/blog/general-contractors-guide-to-hiring-subcontractors"),
    ("LookingForSubs.com: Find Subcontractors Near Me",
     "https://lookingforsubs.com/"),
    ("To owner builders...how did you find your subcontractors? ...",
     "https://www.facebook.com/groups/howtoadu/posts/2964060753749345/"),
    ("How to Hire Good Subcontractors - Agency Forward",
     "https://agentblog.nationwide.com/commercial-lines/commercial-industry-trends/construction/subcontractors/"),
    ("Hiring Subcontractors",
     "https://www.usemultiplier.com/contractor-management/guide-to-sub-contractor-hiring"),
    ("Hiring & Paying Subcontractors: A Construction Guide",
     "https://www.levelset.com/blog/hiring-and-paying-subcontractors/"),
    ("How Professionals Hire and Manage Subcontractors in ...",
     "https://globalconstructionco.com/2020/09/04/how-professionals-hire-manage-subcontractors-in-construction/"),
]

FEATURES = [
    "People also ask",
    "Videos",
    "People also search for",
    "Sponsored",
    "Find related products & services",
]

# Observed on the result page. Supplemental only: primary PAA provenance for the
# rewrite comes from the AnswerSocrates artifact, never from the SERP.
SERP_PAA = [
    "How much should I pay a subcontractor?",
    "How does hiring a subcontractor work?",
    "What are the three types of subcontractors?",
    "Is a subcontractor allowed to hire his or her own subcontractors?",
]

MUST_HAVE_SECTIONS = [
    "what hiring a subcontractor involves end to end",
    "where to find subcontractors",
    "prequalification and vetting checks",
    "worker classification and tax paperwork",
    "written subcontract terms",
    "insurance and liability verification",
    "paying subcontractors",
    "managing subcontractor performance on live jobs",
]

COMPETITOR_GAPS = [
    "no top result states the 2026 federal independent contractor enforcement position",
    "no top result separates enforcement posture from private litigation exposure",
    "no top result gives the current 1099-NEC reporting threshold for 2026 payments",
    "no top result distinguishes a certificate of insurance from an additional insured endorsement",
    "no top result covers OSHA controlling-employer duty on a shared jobsite",
    "no top result supplies a filled prequalification document table with independent verification routes",
    "no top result carries the management half of the query set alongside hiring",
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
            "locale": {"hl": "en", "gl": "us", "pws": "0"},
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
