"""Validate BOM v4 plan-fulfillment bindings and derived evidence."""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from ..blog_assembly.policy import _editorial_fulfillment
from ..blog_assembly_contract import validate_sha256, verify_artifact
from ..editorial_plan.plan_fulfillment import check_fulfillment
from ..guard_common import Finding
from .common import _finding


def check_editorial_fulfillment(
    bom: Mapping[str, Any],
    artifacts: Mapping[str, Any],
    root: Path,
    *,
    plan: Mapping[str, Any],
    article_content: str,
) -> list[Finding]:
    if bom.get("schema") != "simpro-blog-assembly-bom/v4":
        return []
    fulfillment_row = artifacts.get("plan_fulfillment")
    plan_row = artifacts.get("editorial_plan")
    if not isinstance(fulfillment_row, Mapping) or not isinstance(plan_row, Mapping):
        return []
    try:
        path = verify_artifact(
            fulfillment_row,
            workspace_root=root,
            field="artifacts.plan_fulfillment",
        )
        fulfillment = json.loads(path.read_text(encoding="utf-8"))
        plan_hash = validate_sha256(
            plan_row.get("sha256"),
            field="artifacts.editorial_plan.sha256",
        )
    except (ValueError, OSError, UnicodeError, json.JSONDecodeError) as error:
        return [_finding("bom_plan_fulfillment_invalid", f"Plan fulfillment is invalid: {error}")]
    if not isinstance(fulfillment, Mapping):
        return [_finding("bom_plan_fulfillment_invalid", "Plan fulfillment must be a JSON object.")]
    findings = [
        _finding(
            f"bom_{finding.get('rule_id')}",
            str(finding.get("message") or "Plan fulfillment is invalid."),
        )
        for finding in check_fulfillment(
            fulfillment,
            editorial_plan=plan,
            editorial_plan_sha256=plan_hash,
            article_content=article_content,
        )
    ]
    if bom.get("editorial_fulfillment") != _editorial_fulfillment(plan, fulfillment):
        findings.append(_finding(
            "bom_editorial_fulfillment_mismatch",
            "BOM editorial_fulfillment does not match its bound plan and fulfillment artifact.",
        ))
    return findings


__all__ = ["check_editorial_fulfillment"]
