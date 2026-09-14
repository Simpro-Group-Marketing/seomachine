"""Workflow receipt-chain validation for blog assembly BOMs."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from .. import (
    blog_assembly_stage_receipt,
)
from ..blog_assembly_bom import (
    _validate_prior_preflight_payloads,
    _validate_prior_preflight_readiness,
)
from ..blog_assembly_contract import (
    load_json_object_snapshot,
    verify_artifact,
)
from . import preflight_session as blog_assembly_bom_preflight_session
from . import snapshot_adapters as blog_assembly_bom_snapshot
from ..guard_common import Finding
from .common import _finding, _parse_date
from .contracts import (
    NORMAL_FINAL_STAGES,
    NORMAL_PROVISIONAL_STAGES,
    OPTIMIZED_FINAL_STAGES,
    OPTIMIZED_PROVISIONAL_STAGES,
    OPTIMIZED_TAIL_FINAL_STAGES,
    OPTIMIZED_TAIL_PROVISIONAL_STAGES,
)
from .dependencies import BomValidationDependencies
from .workflow_receipts import (
    _check_context_receipts,
    _check_draft_receipt,
    _check_final_article_binding,
    _check_optimization_receipt,
    _check_scrub_receipts,
)


def _check_workflow(
    bom: Mapping[str, Any],
    artifacts: Mapping[str, Any],
    root: Path,
    *,
    captured: Any = None,
    dependencies: BomValidationDependencies | None = None,
) -> list[Finding]:
    dependencies = dependencies or BomValidationDependencies()
    bound = _workflow_dependencies(dependencies)
    workflow = bom.get("workflow")
    if not isinstance(workflow, Mapping):
        return [_finding("bom_workflow_missing", "BOM requires workflow stage receipts.")]
    findings = _check_workflow_shape(workflow, bom)
    embedded = workflow.get("stage_receipts")
    rows = artifacts.get("stage_receipts")
    if not isinstance(embedded, list) or not isinstance(rows, list):
        findings.append(
            _finding(
                "bom_stage_receipts_invalid",
                "BOM stage receipts must be strict lists.",
            )
        )
        return findings
    loaded, receipt_findings = blog_assembly_bom_preflight_session.load_receipts(
        bound, captured, rows, root,
    )
    findings.extend(receipt_findings)
    if loaded != embedded:
        findings.append(
            _finding(
                "bom_stage_receipts_mismatch",
                "Embedded stage receipts must exactly match bound receipt artifacts.",
            )
        )
    stages = tuple(str(receipt.get("stage") or "") for receipt in loaded)
    optimized_tail = stages in {
        OPTIMIZED_TAIL_PROVISIONAL_STAGES,
        OPTIMIZED_TAIL_FINAL_STAGES,
    }
    optimized = "optimization" in stages
    findings.extend(
        _check_stage_contract(bom, artifacts, stages, optimized, optimized_tail)
    )
    findings.extend(
        blog_assembly_stage_receipt.check_receipt_chain(loaded, workspace_root=root)
    )
    by_stage = {str(row.get("stage") or ""): row for row in loaded}
    prior, prior_findings = _load_prior_readiness(
        bom,
        artifacts,
        root,
        by_stage,
        optimized,
        captured,
        bound,
    )
    findings.extend(prior_findings)
    findings.extend(_check_draft_receipt(by_stage, artifacts))
    findings.extend(_check_scrub_receipts(by_stage))
    findings.extend(_check_context_receipts(bom, artifacts, by_stage, prior))
    findings.extend(_check_optimization_receipt(by_stage, artifacts, loaded))
    findings.extend(_check_final_article_binding(loaded, artifacts))
    return findings


def _workflow_dependencies(
    dependencies: BomValidationDependencies,
) -> BomValidationDependencies:
    return dependencies.bind(
        _finding=_finding,
        _validate_prior_preflight_payloads=_validate_prior_preflight_payloads,
        blog_assembly_bom_snapshot=blog_assembly_bom_snapshot,
        load_json_object_snapshot=load_json_object_snapshot,
        verify_artifact=verify_artifact,
    )


def _check_workflow_shape(
    workflow: Mapping[str, Any],
    bom: Mapping[str, Any],
) -> list[Finding]:
    findings: list[Finding] = []
    if set(workflow) != {"stage_receipts"}:
        findings.append(
            _finding(
                "bom_workflow_shape_invalid",
                "BOM workflow must contain only stage_receipts.",
            )
        )
    if _parse_date(bom.get("assembly_date")) is None:
        findings.append(
            _finding(
                "bom_stage_canonical_identity_invalid",
                "Stage receipt canonical article identity cannot be validated without a valid BOM assembly date.",
            )
        )
    return findings


def _check_stage_contract(
    bom: Mapping[str, Any],
    artifacts: Mapping[str, Any],
    stages: tuple[str, ...],
    optimized: bool,
    optimized_tail: bool,
) -> list[Finding]:
    lifecycle = bom.get("lifecycle_state")
    if optimized_tail:
        expected = (
            OPTIMIZED_TAIL_FINAL_STAGES
            if lifecycle == "final"
            else OPTIMIZED_TAIL_PROVISIONAL_STAGES
        )
    elif optimized:
        expected = (
            OPTIMIZED_FINAL_STAGES
            if lifecycle == "final"
            else OPTIMIZED_PROVISIONAL_STAGES
        )
    else:
        expected = (
            NORMAL_FINAL_STAGES
            if lifecycle == "final"
            else NORMAL_PROVISIONAL_STAGES
        )
    findings: list[Finding] = []
    if stages != expected:
        findings.append(
            _finding(
                "bom_stage_order_invalid",
                f"BOM stage sequence must be exactly: {' -> '.join(expected)}.",
            )
        )
    if optimized and not artifacts.get("optimizer_outputs"):
        findings.append(
            _finding(
                "bom_optimizer_evidence_missing",
                "Optimization stage requires optimizer output evidence.",
            )
        )
    if not (optimized or optimized_tail) and artifacts.get("optimizer_outputs"):
        findings.append(
            _finding(
                "bom_optimizer_evidence_unexpected",
                "Optimizer evidence is allowed only for an optimized workflow.",
            )
        )
    return findings


def _load_prior_readiness(
    bom: Mapping[str, Any],
    artifacts: Mapping[str, Any],
    root: Path,
    by_stage: Mapping[str, Mapping[str, Any]],
    optimized: bool,
    captured: Any,
    dependencies: BomValidationDependencies,
) -> tuple[Mapping[str, Any] | None, list[Finding]]:
    if not optimized:
        return None, []
    prior_row = artifacts.get("prior_preflight_readiness")
    prior_receipt = by_stage.get("preflight_readiness")
    try:
        if not isinstance(prior_receipt, Mapping):
            raise ValueError("missing preflight stage receipt")
        if captured is not None:
            readiness = blog_assembly_bom_preflight_session.validate_prior_preflight(
                dependencies, captured, prior_row, prior_receipt, bom,
            )
        else:
            readiness = _load_legacy_prior(
                bom, prior_row, prior_receipt, root,
            )
        return readiness, []
    except (ValueError, OSError, UnicodeError, json.JSONDecodeError) as error:
        return None, [
            _finding(
                "bom_prior_preflight_invalid",
                f"Optimized workflow prior preflight is invalid: {error}",
            )
        ]


def _load_legacy_prior(
    bom: Mapping[str, Any],
    prior_row: Any,
    prior_receipt: Mapping[str, Any],
    root: Path,
) -> Mapping[str, Any]:
    schema = bom.get("schema_policy")
    connector = bom.get("connector_binding")
    path = verify_artifact(
        prior_row,
        workspace_root=root,
        field="artifacts.prior_preflight_readiness",
    )
    return _validate_prior_preflight_readiness(
        path,
        workspace_root=root,
        receipt=prior_receipt,
        visible_faq=isinstance(schema, Mapping) and schema.get("visible_faq") is True,
        connector_required=(
            isinstance(connector, Mapping) and connector.get("status") == "required"
        ),
    )




__all__ = ["_check_workflow"]
