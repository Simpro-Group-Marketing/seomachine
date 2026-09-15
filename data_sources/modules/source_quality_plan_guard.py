"""Validate source quality using lifecycle decisions from editorial-plan v2."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import date
from typing import Any

from . import source_quality_guard as legacy_guard
from .blog_strategy_plan_guard import _legacy_projection
from .blog_strategy_contract import validate_contract
from .editorial_plan.v2 import EDITORIAL_PLAN_SCHEMA_V2
from .guard_common import Finding


def check_content(
    content: str,
    *,
    proof_content: str,
    editorial_plan: Mapping[str, Any] | None,
    today: date,
) -> list[Finding]:
    findings = legacy_guard.check_source_map(proof_content, today=today)
    if not legacy_guard._requires_lifecycle_contract(content, proof_content):
        return legacy_guard._sort_findings(findings)
    if not legacy_guard._extract_source_rows(proof_content):
        findings.append(legacy_guard._finding(
            "source_quality_source_map_missing",
            1,
            "Lifecycle-required Simpro blog sidecars require at least one executable Source Map claim row.",
        ))
    if not isinstance(editorial_plan, Mapping) or editorial_plan.get("schema") != EDITORIAL_PLAN_SCHEMA_V2:
        findings.append(legacy_guard._finding(
            "source_quality_editorial_plan_invalid",
            1,
            f"Current lifecycle validation requires {EDITORIAL_PLAN_SCHEMA_V2}.",
        ))
        return legacy_guard._sort_findings(findings)
    search = editorial_plan.get("search_strategy")
    commercial = editorial_plan.get("commercial_strategy")
    lifecycle = editorial_plan.get("lifecycle")
    if not all(isinstance(row, Mapping) for row in (search, commercial, lifecycle)):
        findings.append(legacy_guard._finding(
            "source_quality_editorial_plan_invalid",
            1,
            "Editorial plan is missing its structured lifecycle strategy.",
        ))
        return legacy_guard._sort_findings(findings)
    contract, contract_findings = validate_contract(
        _legacy_projection(search, commercial, lifecycle)
    )
    if contract_findings or contract is None:
        return legacy_guard._sort_findings(findings + contract_findings)
    findings.extend(
        legacy_guard._lifecycle_findings(
            content,
            proof_content,
            contract,
            today=today,
        )
    )
    return legacy_guard._sort_findings(findings)


__all__ = ["check_content"]
