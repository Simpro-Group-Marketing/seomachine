"""Final preflight seal validation for blog assembly BOMs."""

from __future__ import annotations

import copy
from pathlib import Path
from typing import Any, Mapping

from .. import (
    blog_assembly_contract,
)
from ..blog_assembly_bom import validate_preflight_stage_receipt_binding
from ..blog_assembly_contract import (
    canonical_json_sha256,
    expected_blog_gate_inventory,
    load_json_object_snapshot,
    resolve_artifact,
    validate_sha256,
    verify_artifact,
)
from . import preflight_session as blog_assembly_bom_preflight_session
from . import snapshot_adapters as blog_assembly_bom_snapshot
from ..guard_common import Finding
from .common import _finding, _is_number
from .dependencies import BomValidationDependencies
from .editorial import _load_bound_json_object


def _check_preflight(
    bom: Mapping[str, Any],
    artifacts: Mapping[str, Any],
    root: Path,
    *,
    captured: Any = None,
    dependencies: BomValidationDependencies | None = None,
) -> list[Finding]:
    dependencies = dependencies or BomValidationDependencies()
    lifecycle = bom.get("lifecycle_state")
    record = bom.get("preflight")
    if lifecycle == "provisional":
        if record is not None:
            return [
                _finding(
                    "bom_provisional_preflight_present",
                    "A provisional BOM cannot contain a preflight seal.",
                )
            ]
        return []
    if lifecycle != "final":
        return []
    row = artifacts.get("preflight_readiness")
    if not isinstance(row, Mapping):
        return []
    try:
        loaded = blog_assembly_bom_preflight_session.load_preflight_dispatch(
            dependencies.bind(_load_bound_json_object=_load_bound_json_object),
            captured,
            row,
            root,
        )
    except ValueError as error:
        return [
            _finding(
                "bom_preflight_invalid",
                f"Bound preflight readiness is invalid: {error}",
            )
        ]
    path, readiness, digest, payload = loaded
    if not isinstance(readiness, Mapping):
        return [
            _finding(
                "bom_preflight_invalid",
                "Bound preflight readiness must be an object.",
            )
        ]
    return _validate_final_preflight(
        bom,
        artifacts,
        root,
        row,
        path,
        readiness,
        digest,
        payload,
        captured,
        dependencies,
    )


def _validate_final_preflight(
    bom: Mapping[str, Any],
    artifacts: Mapping[str, Any],
    root: Path,
    readiness_row: Mapping[str, Any],
    readiness_path: Path,
    readiness: Mapping[str, Any],
    readiness_sha256: str | None,
    readiness_payload: Mapping[str, Any] | None,
    captured: Any,
    dependencies: BomValidationDependencies,
) -> list[Finding]:
    findings: list[Finding] = []
    if bom.get("preflight") != _expected_record(readiness_row, readiness):
        findings.append(
            _finding(
                "bom_preflight_record_mismatch",
                "Final BOM preflight seal must exactly match its bound readiness output.",
            )
        )
    if not _valid_readiness_header(readiness):
        findings.append(
            _finding(
                "bom_preflight_invalid",
                "Final BOM requires a passed source-artifact preflight result from publish_readiness 1.0.0.",
            )
        )
        return findings
    expected_inventory = _expected_gate_inventory(bom)
    findings.extend(_check_gate_inventory(readiness, expected_inventory))
    findings.extend(_check_scores(readiness))
    findings.extend(
        _check_preflight_inputs(
            bom,
            artifacts,
            root,
            readiness,
            readiness_path,
            readiness_sha256,
            readiness_payload,
            captured,
            dependencies,
        )
    )
    return findings


def _expected_record(
    row: Mapping[str, Any],
    readiness: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "path": row.get("path"),
        "sha256": row.get("sha256"),
        "tool": readiness.get("tool"),
        "verification_scope": readiness.get("verification_scope"),
        "gate_inventory": readiness.get("gate_inventory"),
        "input_hashes": readiness.get("input_hashes"),
    }


def _valid_readiness_header(readiness: Mapping[str, Any]) -> bool:
    return all(
        (
            readiness.get("schema") == "simpro-publish-readiness-result/v1",
            readiness.get("phase") == "preflight",
            readiness.get("passed") is True,
            readiness.get("artifact_kind") == "blog",
            readiness.get("verification_scope") == "source_artifact",
            readiness.get("input_seal") == {"status": "verified"},
            readiness.get("tool")
            == {"name": "publish_readiness", "version": "1.0.0"},
        )
    )


def _expected_gate_inventory(bom: Mapping[str, Any]) -> list[str]:
    schema = bom.get("schema_policy")
    connector = bom.get("connector_binding")
    return expected_blog_gate_inventory(
        visible_faq=isinstance(schema, Mapping) and schema.get("visible_faq") is True,
        connector_required=(
            isinstance(connector, Mapping) and connector.get("status") == "required"
        ),
    )


def _check_gate_inventory(
    readiness: Mapping[str, Any],
    expected_inventory: list[str],
) -> list[Finding]:
    findings: list[Finding] = []
    if readiness.get("gate_inventory") != expected_inventory:
        findings.append(
            _finding(
                "bom_preflight_gate_inventory_invalid",
                "Preflight readiness gate inventory is not the exact expected inventory.",
            )
        )
    gates = readiness.get("gates")
    names = (
        [gate.get("name") if isinstance(gate, Mapping) else None for gate in gates]
        if isinstance(gates, list)
        else None
    )
    invalid_result = not isinstance(gates, list) or any(
        not isinstance(gate, Mapping)
        or gate.get("passed") is not True
        or gate.get("errors") != 0
        or gate.get("blockers") not in ([], ())
        for gate in (gates if isinstance(gates, list) else [])
    )
    if names != expected_inventory or invalid_result:
        findings.append(
            _finding(
                "bom_preflight_gate_results_invalid",
                "Every exact preflight gate must have a passed, blocker-free tool result.",
            )
        )
    return findings


def _check_scores(readiness: Mapping[str, Any]) -> list[Finding]:
    score = readiness.get("score")
    aeo_geo = readiness.get("aeo_geo")
    valid = all(
        (
            readiness.get("score_threshold") == 85,
            _is_number(score),
            _is_number(score) and score >= 85,
            isinstance(aeo_geo, Mapping),
            isinstance(aeo_geo, Mapping) and aeo_geo.get("threshold") == 90,
            isinstance(aeo_geo, Mapping) and aeo_geo.get("passed") is True,
            isinstance(aeo_geo, Mapping) and _is_number(aeo_geo.get("score")),
            isinstance(aeo_geo, Mapping)
            and _is_number(aeo_geo.get("score"))
            and aeo_geo.get("score") >= 90,
        )
    )
    if valid:
        return []
    return [
        _finding(
            "bom_preflight_scores_invalid",
            "Preflight requires content >=85 and AEO/GEO >=90.",
        )
    ]


def _check_preflight_inputs(
    bom: Mapping[str, Any],
    artifacts: Mapping[str, Any],
    root: Path,
    readiness: Mapping[str, Any],
    readiness_path: Path,
    readiness_sha256: str | None,
    readiness_payload: Mapping[str, Any] | None,
    captured: Any,
    dependencies: BomValidationDependencies,
) -> list[Finding]:
    inputs = readiness.get("input_hashes")
    if not isinstance(inputs, Mapping):
        return [
            _finding(
                "bom_preflight_inputs_invalid",
                "Preflight input_hashes must be an object.",
            )
        ]
    provisional_artifacts = _provisional_artifacts(artifacts)
    try:
        expected_inputs = blog_assembly_bom_snapshot.expanded_input_rows(
            blog_assembly_contract,
            provisional_artifacts,
            bom.get("machine_reviews"),
            captured=captured,
            root=root,
            legacy_loader=load_json_object_snapshot,
            legacy_verify=verify_artifact,
        )
    except ValueError as error:
        return [_finding("bom_preflight_inputs_invalid", str(error))]
    findings: list[Finding] = []
    actual_bound = {key: value for key, value in inputs.items() if key != "assembly_bom"}
    if actual_bound != expected_inputs:
        findings.append(
            _finding(
                "bom_preflight_inputs_mismatch",
                "Preflight must bind every provisional BOM artifact exactly.",
            )
        )
    findings.extend(
        _check_historical_bom(
            bom, inputs.get("assembly_bom"), root, captured, dependencies,
        )
    )
    findings.extend(
        _check_preflight_stage(
            bom,
            artifacts,
            root,
            readiness_path,
            readiness_payload,
            readiness_sha256,
        )
    )
    return findings


def _provisional_artifacts(
    artifacts: Mapping[str, Any],
) -> dict[str, Any]:
    provisional = dict(artifacts)
    provisional["preflight_readiness"] = None
    rows = provisional.get("stage_receipts")
    if isinstance(rows, list) and rows:
        provisional["stage_receipts"] = rows[:-1]
    return provisional


def _check_historical_bom(
    bom: Mapping[str, Any],
    assembly_input: Any,
    root: Path,
    captured: Any,
    dependencies: BomValidationDependencies,
) -> list[Finding]:
    try:
        if not isinstance(assembly_input, Mapping):
            raise ValueError("input_hashes.assembly_bom must be an object")
        expected_hash = validate_sha256(
            assembly_input.get("sha256"),
            field="input_hashes.assembly_bom.sha256",
        )
        historical = blog_assembly_bom_preflight_session.load_historical_bom_dispatch(
            dependencies.bind(_load_bound_json_object=_load_bound_json_object),
            captured,
            assembly_input,
            root,
        )
    except ValueError as error:
        return [
            _finding(
                "bom_preflight_bom_artifact_invalid",
                f"Historical provisional BOM is unavailable or changed: {error}",
            )
        ]
    try:
        provisional = _reconstruct_provisional_bom(bom)
        actual_hash = canonical_json_sha256(provisional)
    except (TypeError, ValueError) as error:
        return [_finding("bom_preflight_inputs_invalid", str(error))]
    if actual_hash != expected_hash:
        return [
            _finding(
                "bom_preflight_bom_hash_mismatch",
                "Final BOM base fields do not reconstruct the exact provisional BOM sealed by preflight.",
            )
        ]
    if historical != provisional:
        return [
            _finding(
                "bom_preflight_bom_hash_mismatch",
                "Historical provisional BOM content does not match the final BOM base fields.",
            )
        ]
    return []


def _reconstruct_provisional_bom(bom: Mapping[str, Any]) -> dict[str, Any]:
    provisional = copy.deepcopy(dict(bom))
    provisional["lifecycle_state"] = "provisional"
    provisional["preflight"] = None
    artifacts = provisional.get("artifacts")
    workflow = provisional.get("workflow")
    if not isinstance(artifacts, dict):
        raise ValueError("artifacts must be an object")
    if not isinstance(workflow, dict):
        raise ValueError("workflow must be an object")
    artifacts["preflight_readiness"] = None
    receipt_artifacts = artifacts.get("stage_receipts")
    embedded_receipts = workflow.get("stage_receipts")
    if not isinstance(receipt_artifacts, list) or not receipt_artifacts:
        raise ValueError("final BOM must contain its preflight receipt artifact")
    if not isinstance(embedded_receipts, list) or not embedded_receipts:
        raise ValueError("final BOM must contain its embedded preflight receipt")
    artifacts["stage_receipts"] = receipt_artifacts[:-1]
    workflow["stage_receipts"] = embedded_receipts[:-1]
    return provisional


def _check_preflight_stage(
    bom: Mapping[str, Any],
    artifacts: Mapping[str, Any],
    root: Path,
    readiness_path: Path,
    readiness_payload: Mapping[str, Any] | None,
    readiness_sha256: str | None,
) -> list[Finding]:
    workflow = bom.get("workflow")
    receipts = workflow.get("stage_receipts") if isinstance(workflow, Mapping) else None
    article = artifacts.get("article")
    try:
        if not isinstance(receipts, list) or not receipts:
            raise ValueError("final BOM must contain an embedded preflight receipt")
        if not isinstance(article, Mapping):
            raise ValueError("final BOM article artifact must be an object")
        validate_preflight_stage_receipt_binding(
            receipts[-1],
            prior_receipts=receipts[:-1],
            readiness_path=readiness_path,
            article_sha256=article.get("sha256"),
            article_path=resolve_artifact(article.get("path"), workspace_root=root),
            workspace_root=root,
            assembly_date=str(bom.get("assembly_date") or ""),
            readiness_payload=readiness_payload,
            readiness_sha256=readiness_sha256,
        )
        return []
    except (OSError, UnicodeError, ValueError) as error:
        return [
            _finding(
                "bom_preflight_stage_receipt_invalid",
                f"Final BOM preflight stage receipt is invalid: {error}",
            )
        ]


__all__ = ["_check_preflight"]
