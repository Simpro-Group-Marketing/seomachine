"""Build governed optimizer evidence for the AI for field service rewrite."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from data_sources.modules.blog_assembly_contract import atomic_write_json, file_sha256


SLUG = "ai-for-field-service"
ARTICLE_DATE = "2026-09-28"
ASSEMBLY_DATE = "2026-09-29"
ARTICLE = ROOT / "rewrites" / f"{SLUG}-rewrite-{ARTICLE_DATE}.md"
PLAN = ROOT / "research" / f"editorial-plan-{SLUG}-{ASSEMBLY_DATE}.json"
SIDECAR = ROOT / "research" / f"validation-{SLUG}-{ARTICLE_DATE}.md"
DEFAULT_OUTPUT = ROOT / "research" / f"optimizer-output-{SLUG}-{ASSEMBLY_DATE}.json"


def workspace_relative(path: Path) -> str:
    resolved = path.resolve(strict=True)
    if not resolved.is_file():
        raise ValueError(f"required artifact is not a file: {path}")
    return resolved.relative_to(ROOT).as_posix()


def read_object(path: Path, *, label: str) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"{label} is not readable JSON: {path}") from error
    if not isinstance(payload, dict):
        raise ValueError(f"{label} must contain a JSON object: {path}")
    return payload


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(
        description="Build simpro-optimizer-output/v2 for the AI field service rewrite."
    )
    result.add_argument("--preflight-readiness", required=True, type=Path)
    result.add_argument("--decision", required=True, choices=("no-op", "edited"))
    result.add_argument("--reason", required=True)
    result.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return result


def binding(path: Path) -> dict[str, str]:
    return {"path": workspace_relative(path), "sha256": file_sha256(path)}


def main() -> int:
    args = parser().parse_args()
    preflight = args.preflight_readiness.resolve(strict=True)
    readiness = read_object(preflight, label="preflight readiness")
    if readiness.get("schema") != "simpro-publish-readiness-result/v1":
        raise ValueError(
            "--preflight-readiness must use simpro-publish-readiness-result/v1"
        )
    if readiness.get("passed") is not True:
        raise ValueError("optimizer evidence requires a passed initial preflight")
    run_id = str(readiness.get("run_id") or "").strip()
    if not run_id:
        raise ValueError("preflight readiness must provide a run_id")
    reason = args.reason.strip()
    if not reason:
        raise ValueError("--reason must not be blank")

    aeo_geo = readiness.get("aeo_geo")
    if not isinstance(aeo_geo, Mapping):
        aeo_geo = {}
    applied_fixes: list[dict[str, Any]] = []
    if args.decision == "edited":
        raise ValueError("this release builder records the approved no-op decision only")

    payload = {
        "schema": "simpro-optimizer-output/v2",
        "status": "completed",
        "run_id": run_id,
        "completed_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "workflow_mode": "rewrite",
        "decision": args.decision,
        "input_bindings": {
            "article": binding(ARTICLE),
            "editorial_plan": binding(PLAN),
            "proof_sidecar": binding(SIDECAR),
            "scorecard": binding(preflight),
            "prior_preflight_readiness": binding(preflight),
        },
        "applied_fixes": applied_fixes,
        "not_applied": readiness.get("priority_fixes", []),
        "no_edit_reason": reason,
        "decision_reason": reason,
        "priority_fixes": readiness.get("priority_fixes", []),
        "aeo_geo_checks": aeo_geo.get("checks", []),
        "inspected_scorecard": readiness.get("scorecard", {}),
        "inspected_gates": readiness.get("gates", []),
        "inspected_blockers": readiness.get("blockers", []),
    }
    output = args.output.resolve(strict=False)
    output.relative_to(ROOT)
    atomic_write_json(output, payload)
    print(f"optimizer output: {output.relative_to(ROOT).as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
