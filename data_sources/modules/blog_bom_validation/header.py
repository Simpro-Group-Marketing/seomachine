"""BOM envelope, lifecycle, and inventory-shape validation."""

from __future__ import annotations

from typing import Any, Mapping

from .. import blog_assembly_contract
from ..blog_assembly.common import (
    ARCHIVED_BOM_SCHEMAS,
    BOM_SCHEMA,
    BOM_SCHEMA_V1,
    BOM_SCHEMA_V2,
    BOM_SCHEMA_V3,
    BOM_SCHEMA_V4,
    LIFECYCLE_STATES,
    WORKFLOW_MODES,
)
from ..guard_common import Finding
from .common import _finding, _parse_date
from .contracts import (
    REQUIRED_TOP_LEVEL_FIELDS,
    V2_REQUIRED_TOP_LEVEL_FIELDS,
    V3_REQUIRED_TOP_LEVEL_FIELDS,
    V4_REQUIRED_TOP_LEVEL_FIELDS,
    required_artifact_fields,
)


def expected_top_fields(bom: Mapping[str, Any]) -> frozenset[str]:
    if bom.get("schema") == BOM_SCHEMA_V4:
        return V4_REQUIRED_TOP_LEVEL_FIELDS
    if bom.get("schema") == BOM_SCHEMA_V3:
        return V3_REQUIRED_TOP_LEVEL_FIELDS
    if bom.get("schema") == BOM_SCHEMA_V2:
        return V2_REQUIRED_TOP_LEVEL_FIELDS
    return REQUIRED_TOP_LEVEL_FIELDS


def check_archived_header(bom: Mapping[str, Any]) -> tuple[list[Finding], Any]:
    findings: list[Finding] = []
    if set(bom) != expected_top_fields(bom):
        findings.append(
            _finding(
                "bom_archive_shape_invalid",
                "Archived final BOM must use the exact strict top-level field set.",
            )
        )
    findings.extend(_check_schema(bom, require_current=False))
    if bom.get("lifecycle_state") != "final":
        findings.append(
            _finding("bom_lifecycle_state_mismatch", "Archived BOM must be final.")
        )
    if bom.get("workflow_mode") not in WORKFLOW_MODES:
        findings.append(
            _finding("bom_workflow_mode_invalid", "BOM workflow_mode is invalid.")
        )
    assembled = _parse_date(bom.get("assembly_date"))
    if assembled is None:
        findings.append(
            _finding(
                "bom_assembly_date_invalid",
                "BOM assembly_date must be an ISO date.",
            )
        )
    return findings, assembled


def check_current_header(
    bom: Mapping[str, Any],
    *,
    expected_lifecycle_state: str | None,
    require_current_schema: bool,
) -> tuple[list[Finding], Any]:
    findings = _check_shape(bom)
    findings.extend(_check_schema(bom, require_current=require_current_schema))
    lifecycle = bom.get("lifecycle_state")
    if lifecycle not in LIFECYCLE_STATES:
        findings.append(
            _finding("bom_lifecycle_state_invalid", "BOM lifecycle_state is invalid.")
        )
    if expected_lifecycle_state and lifecycle != expected_lifecycle_state:
        findings.append(
            _finding(
                "bom_lifecycle_state_mismatch",
                f"Readiness requires a {expected_lifecycle_state} BOM.",
            )
        )
    if bom.get("workflow_mode") not in WORKFLOW_MODES:
        findings.append(
            _finding("bom_workflow_mode_invalid", "BOM workflow_mode is invalid.")
        )
    assembled = _parse_date(bom.get("assembly_date"))
    findings.extend(_check_assembly_date(assembled))
    return findings, assembled


def _check_shape(bom: Mapping[str, Any]) -> list[Finding]:
    expected = expected_top_fields(bom)
    missing = expected - set(bom)
    unknown = set(bom) - expected
    findings: list[Finding] = []
    if missing:
        findings.append(
            _finding(
                "bom_shape_missing_fields",
                "BOM is missing strict top-level fields: "
                + ", ".join(sorted(missing)),
            )
        )
    if unknown:
        findings.append(
            _finding(
                "bom_shape_unknown_fields",
                "BOM contains unsupported top-level fields: "
                + ", ".join(sorted(unknown)),
            )
        )
    return findings


def _check_schema(
    bom: Mapping[str, Any],
    *,
    require_current: bool,
) -> list[Finding]:
    schema = bom.get("schema")
    if schema not in ARCHIVED_BOM_SCHEMAS:
        return [
            _finding(
                "bom_schema_invalid",
                f"BOM must use {BOM_SCHEMA_V1}, {BOM_SCHEMA_V2}, {BOM_SCHEMA_V3}, or {BOM_SCHEMA_V4}.",
            )
        ]
    if require_current and schema != BOM_SCHEMA:
        return [
            _finding(
                "bom_archived_schema_not_releasable",
                "Archived BOM schemas are readable only as evidence and cannot authorize a new release.",
            )
        ]
    return []


def _check_assembly_date(assembled: Any) -> list[Finding]:
    if assembled is None:
        return [
            _finding(
                "bom_assembly_date_invalid",
                "BOM assembly_date must be an ISO date.",
            )
        ]
    if assembled != blog_assembly_contract.current_utc_date():
        return [
            _finding(
                "bom_assembly_date_not_current",
                "BOM assembly_date must equal the current UTC date.",
            )
        ]
    return []


def check_archived_artifact_shape(
    bom: Mapping[str, Any],
    artifacts: Mapping[str, Any],
) -> list[Finding]:
    if set(artifacts) == set(required_artifact_fields(bom.get("schema"))):
        return []
    return [
        _finding(
            "bom_artifacts_shape_invalid",
            "Archived final BOM artifacts must use the exact strict inventory.",
        )
    ]


def check_current_artifact_shape(
    bom: Mapping[str, Any],
    artifacts: Mapping[str, Any],
) -> list[Finding]:
    required = required_artifact_fields(bom.get("schema"))
    findings = [
        _finding(f"bom_{field}_missing", f"BOM artifacts.{field} is missing.")
        for field in required
        if field not in artifacts
    ]
    unknown = set(artifacts) - set(required)
    if unknown:
        findings.append(
            _finding(
                "bom_artifacts_unknown_fields",
                "BOM artifacts contains unsupported fields: "
                + ", ".join(sorted(str(field) for field in unknown)),
            )
        )
    return findings


__all__ = [
    "check_archived_artifact_shape",
    "check_archived_header",
    "check_current_artifact_shape",
    "check_current_header",
    "expected_top_fields",
]
