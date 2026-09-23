"""Build current-release optimizer evidence for the FSM software rewrite.

The script is intentionally unusable before the governed initial preflight
exists. It binds the current article, editorial plan, proof sidecar, scorecard,
and prior preflight readiness bytes into a ``simpro-optimizer-output/v2``
artifact. A no-op decision is allowed only when the inspected preflight passed.
"""
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


SLUG = "best-field-service-management-software"
DATE = "2026-09-22"
RELEASE_DATE = "2026-09-23"
ARTICLE = ROOT / "rewrites" / "best-field-service-management-software-rewrite-2026-08-28.md"
PLAN = ROOT / "research" / f"editorial-plan-{SLUG}-{DATE}.json"
SIDECAR = ROOT / "research" / f"validation-{SLUG}-{DATE}.md"
DEFAULT_OUTPUT = ROOT / "research" / f"optimizer-output-{SLUG}-{RELEASE_DATE}.json"


def workspace_relative(path: Path) -> str:
    """Return one canonical workspace-relative POSIX path."""
    resolved = path.resolve(strict=True)
    if not resolved.is_file():
        raise ValueError(f"required artifact is not a file: {path}")
    return resolved.relative_to(ROOT).as_posix()


def read_object(path: Path, *, label: str) -> dict[str, Any]:
    """Read one JSON object or fail with an artifact-specific error."""
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"{label} is not readable JSON: {path}") from error
    if not isinstance(payload, dict):
        raise ValueError(f"{label} must contain a JSON object: {path}")
    return payload


def read_edit_record(path: Path | None) -> dict[str, Any]:
    """Load the optimizer's exact applied/not-applied decision record."""
    if path is None:
        return {"applied_fixes": [], "not_applied": []}
    payload = read_object(path, label="edit record")
    allowed = {"applied_fixes", "not_applied"}
    unexpected = sorted(set(payload) - allowed)
    if unexpected:
        raise ValueError(
            "edit record contains unsupported keys: " + ", ".join(unexpected)
        )
    result: dict[str, Any] = {}
    for key in ("applied_fixes", "not_applied"):
        value = payload.get(key, [])
        if not isinstance(value, list):
            raise ValueError(f"edit record {key} must be a list")
        result[key] = value
    return result


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(
        description="Build simpro-optimizer-output/v2 for the FSM rewrite."
    )
    result.add_argument(
        "--preflight-readiness",
        required=True,
        type=Path,
        help="Initial wrapper preflight-readiness.json to inspect and bind.",
    )
    result.add_argument(
        "--decision",
        required=True,
        choices=("no-op", "edited"),
        help="Whether /optimize changed the governed article bytes.",
    )
    result.add_argument(
        "--reason",
        required=True,
        help="Concise evidence-based rationale for the optimizer decision.",
    )
    result.add_argument(
        "--edit-record",
        type=Path,
        help="Optional JSON with applied_fixes and not_applied lists.",
    )
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
        raise ValueError(
            "optimizer evidence requires the mandatory passed initial preflight"
        )
    run_id = str(readiness.get("run_id") or "").strip()
    if not run_id:
        raise ValueError("preflight readiness must provide a run_id")
    reason = args.reason.strip()
    if not reason:
        raise ValueError("--reason must not be blank")

    edit_record = read_edit_record(
        args.edit_record.resolve(strict=True) if args.edit_record else None
    )
    applied_fixes = edit_record["applied_fixes"]
    if args.decision == "no-op":
        if applied_fixes:
            raise ValueError("a no-op decision cannot declare applied fixes")
    elif not applied_fixes:
        raise ValueError("an edited decision requires at least one applied fix")

    aeo_geo = readiness.get("aeo_geo")
    if not isinstance(aeo_geo, Mapping):
        aeo_geo = {}

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
        "not_applied": edit_record["not_applied"],
        "no_edit_reason": reason if args.decision == "no-op" else None,
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
    for label, row in payload["input_bindings"].items():
        print(f"  {label:26s} {row['sha256'][:16]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
