"""Common deterministic helpers for BOM validation."""

from __future__ import annotations

import re
from datetime import date
from typing import Any, Mapping, Sequence

from .. import blog_assembly_capabilities
from ..blog_assembly_contract import is_json_number
from ..guard_common import Finding, make_finding
from .contracts import (
    FORBIDDEN_TOPOLOGY_PATTERNS,
    PATH_SHAPED_RE,
    REQUIRED_ARTIFACT_FIELDS,
)


def _check_topology(value: Any) -> list[Finding]:
    findings: list[Finding] = []
    _visit_topology(value, (), findings)
    unique = {str(finding["rule_id"]): finding for finding in findings}
    return list(unique.values())


def _visit_topology(
    item: Any,
    field_path: tuple[str, ...],
    findings: list[Finding],
) -> None:
    if isinstance(item, Mapping):
        for key, child in item.items():
            _inspect_topology_text(str(key), field_path + ("<key>",), findings)
            _visit_topology(child, field_path + (str(key),), findings)
        return
    if isinstance(item, list):
        for index, child in enumerate(item):
            _visit_topology(child, field_path + (str(index),), findings)
        return
    if isinstance(item, str):
        _inspect_topology_text(item, field_path, findings)


def _inspect_topology_text(
    item: str,
    field_path: tuple[str, ...],
    findings: list[Finding],
) -> None:
    normalized = item.replace("\\", "/").casefold()
    if any(pattern in normalized for pattern in FORBIDDEN_TOPOLOGY_PATTERNS):
        findings.append(
            _finding(
                "bom_hard_coded_vault_topology",
                "BOM must not expose fixed vault topology.",
            )
        )
        return
    if not _is_declared_artifact_path(field_path) and PATH_SHAPED_RE.search(item):
        findings.append(
            _finding(
                "bom_path_leakage",
                "Path-shaped strings are allowed only in declared artifact path fields.",
            )
        )


def _is_declared_artifact_path(field_path: tuple[str, ...]) -> bool:
    singleton_fields = set(REQUIRED_ARTIFACT_FIELDS) - {
        "execution_evidence",
        "optimizer_outputs",
        "stage_receipts",
    }
    if (
        len(field_path) == 3
        and field_path[0] == "artifacts"
        and field_path[1] in singleton_fields
        and field_path[2] == "path"
    ):
        return True
    if (
        len(field_path) == 4
        and field_path[:2] == ("artifacts", "execution_evidence")
        and field_path[3] == "path"
    ):
        return True
    if (
        len(field_path) == 4
        and field_path[0] == "artifacts"
        and field_path[1] in {"optimizer_outputs", "stage_receipts"}
        and field_path[2].isdigit()
        and field_path[3] == "path"
    ):
        return True
    if field_path == ("preflight", "path"):
        return True
    if (
        len(field_path) == 3
        and field_path[0] == "machine_reviews"
        and field_path[1] in {"plan", "article"}
        and field_path[2] == "path"
    ):
        return True
    if (
        len(field_path) == 4
        and field_path[:2] == ("preflight", "input_hashes")
        and field_path[3] == "path"
    ):
        label = field_path[2]
        return label == "assembly_bom" or _is_artifact_snapshot_label(label)
    return False


def _is_artifact_snapshot_label(label: str) -> bool:
    if label.startswith(blog_assembly_capabilities.EXECUTION_EVIDENCE_PREFIXES):
        return True
    if label in set(REQUIRED_ARTIFACT_FIELDS) - {
        "execution_evidence",
        "optimizer_outputs",
        "stage_receipts",
    }:
        return True
    return re.fullmatch(r"(?:optimizer_outputs|stage_receipts)\[\d+\]", label) is not None


def _parse_date(value: Any) -> date | None:
    if not isinstance(value, str):
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def _sorted(findings: Sequence[Finding]) -> list[Finding]:
    return sorted(
        findings,
        key=lambda finding: (
            str(finding.get("rule_id", "")),
            str(finding.get("message", "")),
        ),
    )


def _is_number(value: Any) -> bool:
    return is_json_number(value)


def _finding(rule_id: str, message: str) -> Finding:
    return make_finding(
        rule_id,
        "error",
        1,
        message=message,
        suggestion="Regenerate the BOM from current workflow artifacts.",
    )


__all__ = [
    "_check_topology",
    "_finding",
    "_is_artifact_snapshot_label",
    "_is_declared_artifact_path",
    "_is_number",
    "_parse_date",
    "_sorted",
]
