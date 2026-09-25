"""Write the simpro-optimizer-output/v2 artifact for the subcontractors rewrite.

Records the fixes the optimizer actually applied against the initial preflight
scorecard, bound to the current article, plan, sidecar and prior readiness.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from data_sources.modules.blog_assembly_contract import atomic_write_json
from data_sources.modules.source_support.persistence import _sha256_file

SLUG = "best-practices-hiring-and-managing-subcontractors"
DATE = "2026-09-18"
RUNHEX = "806632f5"
RELEASE = f"research/releases/{SLUG}-{DATE}-{RUNHEX}-v8"
OUT = ROOT / "research" / f"optimizer-output-{SLUG}-{DATE}.json"

BINDINGS = {
    "article": f"rewrites/{SLUG}-{DATE}.md",
    "editorial_plan": f"research/editorial-plan-{SLUG}-{DATE}.json",
    "proof_sidecar": f"research/validation-{SLUG}-{DATE}.md",
    "scorecard": f"{RELEASE}/preflight-readiness.json",
    "prior_preflight_readiness": f"{RELEASE}/preflight-readiness.json",
}

APPLIED_FIXES = [
    {
        "dimension": "accessibility",
        "issue": "The in-body image alt listed documents but did not name the artifact the reader had just used, and opened on a vague \"including\".",
        "fix": (
            "Rewrote the alt to \"Documents from the subcontractor prequalification "
            "pack: Form W-9, certificate of insurance, workers compensation "
            "certificate and state trade license\", tying the image to the table "
            "above it for screen-reader users and image search."
        ),
        "severity": "low",
    },
]

NO_EDIT_REASON = (
    "One source-safe fix was applied. The inspected preflight scorecard already "
    "cleared every threshold (content 92.9/85, SEO 97/90 with zero critical "
    "issues, AEO/GEO 100/90) with every readiness gate passing, so the remaining "
    "items were soft-score suggestions only. Each was evaluated against the proof "
    "gates and left unchanged for the reason recorded below rather than traded "
    "against an evidence requirement."
)

NOT_APPLIED = [
    {
        "dimension": "seo",
        "issue": "Primary keyword is missing from H2 headings",
        "reason": (
            "Left unchanged. The only H2 that could carry it is the practices "
            "heading, whose wording is specified verbatim by the supplied brief. SEO "
            "already clears its 90 threshold at 94 with zero critical issues, and 95 "
            "is a target rather than a gate, so the brief's structure was kept."
        ),
    },
    {
        "dimension": "humanity",
        "issue": "Lacks contractions (sounds formal)",
        "reason": (
            "Left unchanged. This is the highest-impact soft-score item, but content "
            "quality already clears 92.9 against an 85 threshold, and loosening the "
            "register across legal and insurance copy risks the AI copy lint profile "
            "for a score the gate does not need."
        ),
    },
    {
        "dimension": "structure_balance",
        "issue": "Too much prose (83% prose, target 50-75%)",
        "reason": (
            "Left unchanged. The article already carries the prequalification pack "
            "table inside the early-artifact window and the subcontractor scorecard "
            "table in Step 6. Converting more compliance prose into lists would "
            "strip the same-paragraph evidence links the proof gates require."
        ),
    },
    {
        "dimension": "readability",
        "issue": "Content too difficult (Flesch: 46.6) and 1 paragraph exceeds 4 sentences",
        "reason": (
            "Left unchanged. The long paragraph is the shared-jobsite duty passage in "
            "Step 5, where the controlling-employer sentences depend on the OSHA "
            "multi-employer citation link in the same paragraph. Splitting it would "
            "separate those claims from the link that satisfies inline_required "
            "citation mode."
        ),
    },
    {
        "dimension": "aeo_geo",
        "issue": "No positive E-E-A-T signal (warning eeat_strength_safe_but_weak)",
        "reason": (
            "No approved ClockShark customer proof fits a subcontractor hiring "
            "topic. Both eligible index rows describe in-house crew timekeeping, and "
            "the non-vault v1 contract excludes review-platform sources. Inventing "
            "or stretching proof is prohibited, so the sidecar carries the "
            "proof_unavailable_safe_to_publish decision instead."
        ),
    },
]


def main() -> int:
    payload = {
        "schema": "simpro-optimizer-output/v2",
        "status": "completed",
        "run_id": (ROOT / ".run-subcontractors.env").read_text(encoding="utf-8").split("RUN_ID=")[1].split("\n")[0].strip(),
        "completed_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "workflow_mode": "rewrite",
        "input_bindings": {
            label: {"path": rel, "sha256": _sha256_file(ROOT / rel)}
            for label, rel in BINDINGS.items()
        },
        "applied_fixes": APPLIED_FIXES,
        "not_applied": NOT_APPLIED,
        "no_edit_reason": NO_EDIT_REASON,
        "priority_fixes": json.loads(
            (ROOT / BINDINGS["scorecard"]).read_text(encoding="utf-8")
        )["priority_fixes"],
        "aeo_geo_checks": json.loads(
            (ROOT / BINDINGS["scorecard"]).read_text(encoding="utf-8")
        )["aeo_geo"]["checks"],
        "inspected_scorecard": json.loads(
            (ROOT / BINDINGS["scorecard"]).read_text(encoding="utf-8")
        )["scorecard"],
    }
    atomic_write_json(OUT, payload)
    print(f"optimizer output: {OUT.relative_to(ROOT).as_posix()}")
    for label, row in payload["input_bindings"].items():
        print(f"  {label:26s} {row['sha256'][:16]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
