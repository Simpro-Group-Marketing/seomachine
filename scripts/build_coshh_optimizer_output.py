"""Build the governed no-op optimizer evidence for the COSHH regulations rewrite."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from data_sources.modules.blog_assembly_contract import atomic_write_json, file_sha256


SLUG = "coshh-regulations"
DATE = "2026-09-24"
ARTICLE = ROOT / "rewrites" / f"{SLUG}-{DATE}.md"
PLAN = ROOT / "research" / f"editorial-plan-{SLUG}-{DATE}.json"
SIDECAR = ROOT / "research" / f"validation-{SLUG}-{DATE}.md"
DEFAULT_OUTPUT = ROOT / "research" / f"optimizer-output-{SLUG}-{DATE}.json"

NOT_APPLIED = [
    {
        "fix": "Use contractions like don't, can't, you're, it's",
        "reason": "The article explains legal duties in a UK regulatory register, and the source-support "
                  "negation check does not read contractions such as don't as negation, so contractions "
                  "would weaken claim-to-evidence parity.",
    },
    {
        "fix": "Break long paragraphs into smaller chunks (2-4 sentences max)",
        "reason": "The flagged 10-sentence unit is the five-step ordered list in the assessment section, "
                  "which the paragraph parser reads as one paragraph. Each list item is already 2 sentences.",
    },
    {
        "fix": "Simplify some complex sentences",
        "reason": "Flesch 50.3 reflects regulation names and statutory terms that the Source Map binds "
                  "verbatim. Every sentence is at most 30 words under the simpro-web lint profile.",
    },
    {
        "fix": "Secondary keywords not found: what are the 3 main regulations of coshh",
        "reason": "The H2 'What are the 3 main COSHH regulations?' and its direct answer carry the query "
                  "intent. The verbatim phrase reads unnaturally in UK copy and the SEO score is already 99.",
    },
    {
        "fix": "redundant_public_research_citation warnings at the substances section and Reg 9 table rows",
        "reason": "Each table row and paragraph is an inline_required regulatory claim unit that needs its "
                  "own same-row link under the proof-link policy, so removing a repeat would break a "
                  "required claim binding.",
    },
]


def binding(path: Path) -> dict[str, str]:
    resolved = path.resolve(strict=True)
    return {
        "path": resolved.relative_to(ROOT).as_posix(),
        "sha256": file_sha256(resolved),
    }


def load_object(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected a JSON object: {path}")
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--preflight-readiness", required=True, type=Path)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    preflight = args.preflight_readiness.resolve(strict=True)
    readiness = load_object(preflight)
    if readiness.get("schema") != "simpro-publish-readiness-result/v1":
        raise ValueError("preflight readiness uses the wrong schema")
    if readiness.get("passed") is not True:
        raise ValueError("no-op optimization requires a passed initial preflight")

    reason = (
        "Initial readiness passed every release gate with Content 94.3, SEO 99, and AEO/GEO 100. "
        "The optimizer found no source-safe article change that would materially improve the "
        "rewrite without weakening a bound claim or the approved brief, so article bytes remain "
        "unchanged. The only change is a sidecar wording correction naming the Suzanne exact quote "
        "in Selected Customer Proof Mining."
    )
    payload = {
        "schema": "simpro-optimizer-output/v2",
        "status": "completed",
        "run_id": str(readiness.get("run_id") or ""),
        "completed_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "workflow_mode": "rewrite",
        "decision": "no-op",
        "input_bindings": {
            "article": binding(ARTICLE),
            "editorial_plan": binding(PLAN),
            "proof_sidecar": binding(SIDECAR),
            "scorecard": binding(preflight),
            "prior_preflight_readiness": binding(preflight),
        },
        "applied_fixes": [],
        "not_applied": NOT_APPLIED,
        "no_edit_reason": reason,
        "decision_reason": reason,
        "priority_fixes": readiness.get("priority_fixes", []),
        "aeo_geo_checks": readiness.get("aeo_geo", {}).get("checks", {}),
        "inspected_scorecard": readiness.get("scorecard", {}),
        "inspected_gates": readiness.get("gates", []),
        "inspected_blockers": readiness.get("blockers", []),
    }
    if not payload["run_id"]:
        raise ValueError("preflight readiness is missing run_id")

    output = args.output.resolve(strict=False)
    output.relative_to(ROOT)
    atomic_write_json(output, payload)
    print(output.relative_to(ROOT).as_posix())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
