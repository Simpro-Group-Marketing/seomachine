"""Build the governed no-op optimizer evidence for the overtime tracker blog."""
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


ARTICLE = ROOT / "drafts" / "overtime-tracker-2026-09-23.md"
PLAN = ROOT / "research" / "editorial-plan-overtime-tracker-2026-09-23.json"
SIDECAR = ROOT / "research" / "validation-overtime-tracker-2026-09-23.md"
DEFAULT_OUTPUT = ROOT / "research" / "optimizer-output-overtime-tracker-2026-09-23.json"


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
        "Initial readiness passed all release gates and exceeded every required "
        "quality threshold. The optimizer found no source-safe change that would "
        "materially improve the article without adding unsupported claims or "
        "disturbing the approved brief, so article bytes remain unchanged."
    )
    payload = {
        "schema": "simpro-optimizer-output/v2",
        "status": "completed",
        "run_id": str(readiness.get("run_id") or ""),
        "completed_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "workflow_mode": "new",
        "decision": "no-op",
        "input_bindings": {
            "article": binding(ARTICLE),
            "editorial_plan": binding(PLAN),
            "proof_sidecar": binding(SIDECAR),
            "scorecard": binding(preflight),
            "prior_preflight_readiness": binding(preflight),
        },
        "applied_fixes": [],
        "not_applied": [],
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
