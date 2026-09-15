"""Hindsight strategy evidence checks for BOM validation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from ..blog_assembly.common import BOM_SCHEMA_V3, BOM_SCHEMA_V4
from ..blog_assembly_contract import verify_artifact
from ..guard_common import Finding
from .common import _finding

def _check_hindsight_strategy_policy(
    bom: Mapping[str, Any],
    artifacts: Mapping[str, Any],
    root: Path,
) -> list[Finding]:
    if bom.get("schema") not in {BOM_SCHEMA_V3, BOM_SCHEMA_V4}:
        return []
    policy = bom.get("hindsight_strategy_policy")
    if not isinstance(policy, Mapping):
        return [
            _finding(
                "bom_hindsight_strategy_policy_missing",
                "BOM v3 requires hindsight_strategy_policy.",
            )
        ]
    required = {
        "status",
        "public_claim_use",
        "claim_support_allowed",
        "evidence_required",
    }
    if not required <= set(policy):
        return [
            _finding(
                "bom_hindsight_strategy_policy_invalid",
                "BOM hindsight_strategy_policy is missing required fields.",
            )
        ]
    status = policy.get("status")
    if status not in {"internal_strategy_only", "not_applicable", "blocked"}:
        return [
            _finding(
                "bom_hindsight_strategy_status_invalid",
                "BOM hindsight_strategy_policy.status is invalid.",
            )
        ]
    findings: list[Finding] = []
    if policy.get("public_claim_use") != "prohibited":
        findings.append(
            _finding(
                "bom_hindsight_public_claim_use_invalid",
                "Hindsight strategy policy must prohibit public claim use.",
            )
        )
    if policy.get("claim_support_allowed") is not False:
        findings.append(
            _finding(
                "bom_hindsight_claim_support_invalid",
                "Hindsight strategy policy cannot allow public claim support.",
            )
        )
    findings.extend(_check_hindsight_evidence(policy, artifacts, root))
    return findings


def _check_hindsight_evidence(
    policy: Mapping[str, Any],
    artifacts: Mapping[str, Any],
    root: Path,
) -> list[Finding]:
    findings: list[Finding] = []
    status = policy.get("status")
    evidence_required = policy.get("evidence_required")
    evidence_row = artifacts.get("hindsight_strategy_evidence")
    if status == "internal_strategy_only":
        if evidence_required is not True:
            findings.append(
                _finding(
                    "bom_hindsight_evidence_required_invalid",
                    "Hindsight internal_strategy_only policy must require evidence.",
                )
            )
        if evidence_row is None:
            findings.append(
                _finding(
                    "bom_hindsight_strategy_evidence_missing",
                    "Hindsight internal_strategy_only policy requires artifacts.hindsight_strategy_evidence.",
                )
            )
            return findings
        try:
            path = verify_artifact(
                evidence_row,
                workspace_root=root,
                field="artifacts.hindsight_strategy_evidence",
            )
            evidence = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as error:
            findings.append(
                _finding(
                    "bom_hindsight_strategy_evidence_invalid",
                    f"Hindsight strategy evidence is invalid: {error}",
                )
            )
            return findings
        if not isinstance(evidence, Mapping):
            findings.append(
                _finding(
                    "bom_hindsight_strategy_evidence_invalid",
                    "Hindsight strategy evidence must be a JSON object.",
                )
            )
            return findings
        findings.extend(_check_hindsight_payload(evidence))
        return findings
    if evidence_required is not False:
        findings.append(
            _finding(
                "bom_hindsight_evidence_required_invalid",
                "Hindsight not_applicable or blocked policy cannot require evidence.",
            )
        )
    if evidence_row is not None:
        findings.append(
            _finding(
                "bom_hindsight_strategy_evidence_unexpected",
                "Hindsight evidence is allowed only when status is internal_strategy_only.",
            )
        )
    return findings


def _check_hindsight_payload(evidence: Mapping[str, Any]) -> list[Finding]:
    findings: list[Finding] = []
    pack = evidence.get("pack")
    receipt = evidence.get("receipt")
    sidecar = evidence.get("sidecar")
    if not isinstance(pack, Mapping) or pack.get("schema") != "simpro-internal-strategy-pack/v1":
        findings.append(
            _finding(
                "bom_hindsight_strategy_pack_invalid",
                "Hindsight strategy evidence requires simpro-internal-strategy-pack/v1.",
            )
        )
    if not isinstance(receipt, Mapping) or receipt.get("schema") != "simpro-internal-strategy-receipt/v1":
        findings.append(
            _finding(
                "bom_hindsight_strategy_receipt_invalid",
                "Hindsight strategy evidence requires simpro-internal-strategy-receipt/v1.",
            )
        )
    if (
        not isinstance(sidecar, Mapping)
        or sidecar.get("schema") != "simpro-content-validation-sidecar/v1"
        or sidecar.get("public_claim_use") != "prohibited"
        or sidecar.get("claim_support_allowed") is not False
    ):
        findings.append(
            _finding(
                "bom_hindsight_strategy_sidecar_invalid",
                "Hindsight strategy evidence sidecar must prohibit public claim use and claim support.",
            )
        )
    return findings


__all__ = ["_check_hindsight_strategy_policy"]
