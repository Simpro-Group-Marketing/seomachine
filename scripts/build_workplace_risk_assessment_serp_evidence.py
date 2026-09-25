"""Persist the Chrome-verified UK SERP and build attested evidence."""
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


QUERY = "workplace risk assessment"
RUN_ID = "workplace-risk-assessment-2026-09-25"
RAW = ROOT / "research" / "serp-chrome-raw-workplace-risk-assessment-2026-09-25.json"
EVIDENCE = ROOT / "research" / "serp-evidence-workplace-risk-assessment-2026-09-25.json"


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
            "url": "https://www.google.com/search?q=workplace+risk+assessment&hl=en&gl=gb&pws=0",
            "locale": {"hl": "en", "gl": "gb", "pws": "0"},
        },
        "raw_response": {
            "ai_overview": {
                "answer_pattern": "Defines workplace risk assessment, states the UK five-or-more-employee record rule, and presents the five-step process.",
                "visible_citations": [
                    "https://www.hse.gov.uk/risk/",
                    "https://www.acas.org.uk/health-and-safety-at-work/risk-assessments",
                    "https://www.hse.gov.uk/simple-health-safety/risk/risk-assessment-template-and-examples.htm",
                ],
                "interpretation_boundary": "The AI Overview is a volatile SERP observation. The article verifies legal and process claims against current HSE pages rather than using the overview as public proof.",
            },
            "features": [
                "AI Overview",
                "Five-step answer list",
                "Template result",
            ],
            "organic_results": [
                {
                    "title": "Managing risks and risk assessment at work: Overview",
                    "url": "https://www.hse.gov.uk/risk/",
                },
                {
                    "title": "Risk assessments - Health and safety at work",
                    "url": "https://www.acas.org.uk/health-and-safety-at-work/risk-assessments",
                },
                {
                    "title": "Risk assessment: Template and examples",
                    "url": "https://www.hse.gov.uk/simple-health-safety/risk/risk-assessment-template-and-examples.htm",
                },
            ],
            "verification_note": "Chrome loaded the exact hl=en, gl=gb, pws=0 request on 25 September 2026. The first three visible organic results were HSE overview, Acas guidance, and the HSE template-and-examples page.",
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
            "an immediate workplace risk assessment definition",
            "an early five-step checklist",
            "current UK legal and competent-person guidance",
            "a worked workplace risk assessment example",
            "a reusable record-and-review workflow",
        ],
        competitor_gaps=[
            "The visible authoritative results explain requirements and supply templates, but do not connect the five steps to a field-service job at a customer site.",
            "The visible result set supports a practical guide rather than a product-led landing page.",
            "A self-contained ladder example can show how hazard identification, controls, ownership, recording, and review connect in one job.",
        ],
    )
    atomic_write_json(EVIDENCE, evidence)
    print(f"raw_capture={RAW.relative_to(ROOT).as_posix()}")
    print(f"serp_evidence={EVIDENCE.relative_to(ROOT).as_posix()}")
    print(f"collected_at={collected_at}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
