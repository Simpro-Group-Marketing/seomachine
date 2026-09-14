"""Focused blog assembly BOM validation routines."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from ..blog_assembly_contract import (
    canonical_artifact,
    load_json_object_snapshot,
    resolve_artifact,
    verify_artifact,
)
from ..guard_common import Finding
import data_sources.modules.blog_bom_validation.snapshot_adapters as blog_assembly_bom_snapshot
from .common import _finding
from .contracts import (
    NONVAULT_CUSTOMER_PROOF_SCHEMA,
    OPTIMIZED_TAIL_FINAL_STAGES,
    OPTIMIZED_TAIL_PROVISIONAL_STAGES,
    POST_PUBLISH_MEASUREMENT_RECEIPT_SCHEMA,
    required_artifact_fields as _required_artifact_fields,
)

def _check_artifact_inventory(
    bom: Mapping[str, Any],
    artifacts: Mapping[str, Any],
    root: Path,
    *,
    captured: Any = None,
) -> list[Finding]:
    findings: list[Finding] = []
    required_artifact_fields = _required_artifact_fields(bom.get("schema"))
    findings.extend(
        _verify_inventory_rows(
            artifacts,
            required_artifact_fields,
            root,
            captured=captured,
        )
    )
    findings.extend(
        _check_post_publish_measurement_receipt_exclusion(
            artifacts, root, captured=captured,
        )
    )
    findings.extend(_check_required_inputs(bom, artifacts))
    findings.extend(_check_connector_inventory(bom, artifacts, root, captured))
    findings.extend(_check_lifecycle_inventory(bom, artifacts))
    return findings


def _verify_inventory_rows(
    artifacts: Mapping[str, Any],
    required_artifact_fields: tuple[str, ...],
    root: Path,
    *,
    captured: Any,
) -> list[Finding]:
    findings: list[Finding] = []
    singleton_fields = set(required_artifact_fields) - {
        "execution_evidence",
        "optimizer_outputs",
        "stage_receipts",
        "stage_evidence",
    }
    for field in singleton_fields:
        row = artifacts.get(field)
        if row is None:
            continue
        findings.extend(_verify_row(row, field, root, captured=captured))
    for field in ("optimizer_outputs", "stage_receipts", "stage_evidence"):
        rows = artifacts.get(field)
        if not isinstance(rows, list):
            findings.append(_finding(f"bom_{field}_invalid", f"artifacts.{field} must be a list."))
            continue
        for index, row in enumerate(rows):
            findings.extend(
                _verify_row(row, f"{field}_{index}", root, captured=captured)
            )
    return findings


def _check_required_inputs(
    bom: Mapping[str, Any],
    artifacts: Mapping[str, Any],
) -> list[Finding]:
    findings: list[Finding] = []
    for field in ("article", "validation_sidecar", "editorial_plan", "keyword_decision", "serp_evidence"):
        if artifacts.get(field) is None:
            findings.append(_finding(f"bom_{field}_missing", f"artifacts.{field} is required."))
    paa = bom.get("paa_policy")
    source_kind = paa.get("source_kind") if isinstance(paa, Mapping) else None
    required_paa_artifact = {
        "answersocrates": "paa_artifact",
        "brief_paa": "content_brief",
        "user_csv": "user_paa_csv",
    }.get(source_kind)
    if required_paa_artifact and artifacts.get(required_paa_artifact) is None:
        findings.append(
            _finding(
                f"bom_{required_paa_artifact}_missing",
                f"PAA source {source_kind} requires artifacts.{required_paa_artifact}.",
            )
        )
    if source_kind == "user_csv" and artifacts.get("answersocrates_blocker") is None:
        findings.append(
            _finding(
                "bom_answersocrates_blocker_missing",
                "User CSV PAA requires a bound AnswerSocrates blocker artifact.",
            )
        )
    return findings


def _check_connector_inventory(
    bom: Mapping[str, Any],
    artifacts: Mapping[str, Any],
    root: Path,
    captured: Any,
) -> list[Finding]:
    findings: list[Finding] = []
    connector = bom.get("connector_binding")
    connector_required = isinstance(connector, Mapping) and connector.get("status") == "required"
    if connector_required:
        for field in (
            "context_request",
            "context_pack",
            "context_receipt",
            "customer_proof_selector_evidence",
            "fred_authority_evidence",
        ):
            if artifacts.get(field) is None:
                findings.append(_finding(f"bom_{field}_missing", f"Connector-bound BOM requires artifacts.{field}."))
    else:
        for field in (
            "context_request",
            "context_pack",
            "context_receipt",
            "fred_authority_evidence",
        ):
            if artifacts.get(field) is not None:
                findings.append(
                    _finding(
                        "bom_non_connector_evidence_unexpected",
                        f"Non-connector BOM cannot include artifacts.{field}.",
                    )
                )
        customer_proof_row = artifacts.get("customer_proof_selector_evidence")
        if customer_proof_row is not None and _artifact_json_schema(
            customer_proof_row,
            root,
            captured=captured,
        ) != NONVAULT_CUSTOMER_PROOF_SCHEMA:
            findings.append(
                _finding(
                    "bom_non_connector_evidence_unexpected",
                    "Non-connector BOM customer proof must use the non-vault selector evidence schema.",
                )
            )
    return findings


def _check_lifecycle_inventory(
    bom: Mapping[str, Any],
    artifacts: Mapping[str, Any],
) -> list[Finding]:
    findings: list[Finding] = []
    lifecycle = bom.get("lifecycle_state")
    workflow = bom.get("workflow")
    embedded_receipts = (
        workflow.get("stage_receipts") if isinstance(workflow, Mapping) else None
    )
    stages = (
        tuple(str(receipt.get("stage") or "") for receipt in embedded_receipts)
        if isinstance(embedded_receipts, list)
        else ()
    )
    optimized_tail = stages in {
        OPTIMIZED_TAIL_PROVISIONAL_STAGES,
        OPTIMIZED_TAIL_FINAL_STAGES,
    }
    optimized = "optimization" in stages
    optimizer_evidence_allowed = optimized or optimized_tail
    if optimized and artifacts.get("prior_preflight_readiness") is None:
        findings.append(
            _finding(
                "bom_prior_preflight_readiness_missing",
                "Optimized BOM requires the earlier passed preflight readiness artifact.",
            )
        )
    if (
        not optimizer_evidence_allowed
        and artifacts.get("prior_preflight_readiness") is not None
    ):
        findings.append(
            _finding(
                "bom_prior_preflight_readiness_unexpected",
                "Prior preflight readiness is allowed only for an optimized workflow.",
            )
        )
    if lifecycle == "final" and artifacts.get("preflight_readiness") is None:
        findings.append(_finding("bom_preflight_readiness_missing", "Final BOM requires passed preflight readiness evidence."))
    if lifecycle == "provisional" and artifacts.get("preflight_readiness") is not None:
        findings.append(_finding("bom_provisional_readiness_present", "Provisional BOM cannot bind preflight output before it runs."))
    return findings


def _artifact_json_schema(
    row: Any,
    root: Path,
    *,
    captured: Any = None,
) -> str:
    if not isinstance(row, Mapping):
        return ""
    try:
        payload = blog_assembly_bom_snapshot.json_artifact(
            captured,
            row,
            field="artifact schema",
            root=root,
            legacy_loader=load_json_object_snapshot,
            legacy_verify=verify_artifact,
        )
    except (OSError, UnicodeError, json.JSONDecodeError, TypeError, ValueError):
        return ""
    if not isinstance(payload, Mapping):
        return ""
    return str(payload.get("schema") or "")


def _check_post_publish_measurement_receipt_exclusion(
    artifacts: Mapping[str, Any],
    root: Path,
    *,
    captured: Any = None,
) -> list[Finding]:
    """Keep advisory distribution and measurement artifacts out of every BOM slot."""
    findings: list[Finding] = []
    for field, value in artifacts.items():
        rows = value if isinstance(value, list) else [value]
        for index, row in enumerate(rows):
            if not isinstance(row, Mapping):
                continue
            artifact_path = row.get("path")
            normalized_path = (
                artifact_path.replace("\\", "/").casefold()
                if isinstance(artifact_path, str)
                else ""
            )
            if (
                normalized_path.startswith("repurposed/")
                or normalized_path.startswith("research/performance-review-")
                or normalized_path.startswith("research/performance-receipt-")
            ):
                findings.append(
                    _finding(
                        "bom_post_publish_artifact_forbidden",
                        "Distribution handoffs and post-publish performance artifacts "
                        "are advisory and cannot be BOM artifacts.",
                    )
                )
            try:
                payload = blog_assembly_bom_snapshot.json_artifact(
                    captured,
                    row,
                    field=f"artifacts.{field}[{index}]",
                    root=root,
                    legacy_loader=load_json_object_snapshot,
                    legacy_verify=verify_artifact,
                )
            except (OSError, UnicodeError, json.JSONDecodeError, ValueError):
                continue
            if (
                isinstance(payload, Mapping)
                and payload.get("schema")
                == POST_PUBLISH_MEASUREMENT_RECEIPT_SCHEMA
            ):
                findings.append(
                    _finding(
                        "bom_post_publish_measurement_receipt_forbidden",
                        "Post-publish measurement receipts are advisory and cannot be BOM artifacts.",
                    )
                )
    return findings


def _verify_row(
    row: Any,
    field: str,
    root: Path,
    *,
    captured: Any = None,
) -> list[Finding]:
    if not isinstance(row, Mapping) or set(row) != {"path", "sha256"}:
        return [
            _finding(
                f"bom_{field}_invalid",
                f"artifacts.{field} must contain only path and sha256.",
            )
        ]
    try:
        blog_assembly_bom_snapshot.verify_artifact(
            captured,
            row,
            root=root,
            field=f"artifacts.{field}",
            legacy_verify=verify_artifact,
        )
    except ValueError as error:
        message = str(error)
        if "sha256 does not match" in message:
            suffix = "hash_mismatch"
        elif "unavailable" in message:
            suffix = "unavailable"
        elif "path" in message:
            suffix = "path_invalid"
        else:
            suffix = "invalid"
        return [_finding(f"bom_{field}_{suffix}", message)]
    return []


def _check_supplied_path(
    artifacts: Mapping[str, Any],
    field: str,
    supplied: str | Path,
    root: Path,
    *,
    captured: Any = None,
) -> list[Finding]:
    row = artifacts.get(field)
    if not isinstance(row, Mapping):
        return []
    try:
        if captured is not None:
            expected_snapshot = captured.snapshot(field)
            row_snapshot = captured.snapshot_row(
                row,
                field=f"artifacts.{field}",
            )
            expected = {
                "path": expected_snapshot.relative_path,
                "sha256": expected_snapshot.sha256,
            }
            if row_snapshot.path != expected_snapshot.path:
                expected["path"] = expected_snapshot.relative_path
        else:
            expected = canonical_artifact(supplied, workspace_root=root)
    except ValueError as error:
        return [_finding(f"bom_{field}_input_invalid", str(error))]
    if row.get("path") != expected["path"]:
        return [_finding(f"bom_{field}_path_mismatch", f"BOM {field} path does not match readiness input.")]
    if row.get("sha256") != expected["sha256"]:
        return [_finding(f"bom_{field}_hash_mismatch", f"BOM {field} hash does not match readiness input.")]
    return []


def _is_workspace_file(path: str | Path, root: Path) -> bool:
    try:
        candidate = Path(path)
        relative = (
            candidate.resolve().relative_to(root).as_posix()
            if candidate.is_absolute()
            else candidate.as_posix()
        )
        resolve_artifact(relative, workspace_root=root)
    except ValueError:
        return False
    return True
