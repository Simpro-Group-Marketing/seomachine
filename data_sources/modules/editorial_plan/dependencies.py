"""Explicit external collaborators for editorial-plan validation."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class EditorialPlanDependencies:
    """Frozen external operations used by one serial validation run."""

    canonical_json_sha256: Callable[..., str]
    canonical_snapshot_artifact: Callable[..., dict[str, Any]]
    load_json_object_snapshot: Callable[..., Any]
    resolve_artifact: Callable[..., Any]
    attest_mapping: Callable[..., dict[str, Any]]
    verify_mapping_attestation: Callable[..., bool]
    split_frontmatter: Callable[..., Any]
    resolve_required_industry_policy: Callable[..., Any]
    editorial_plan_industry_findings: Callable[..., list[dict[str, Any]]]
    link_policy_override_count_supported: Callable[..., bool]


def default_editorial_plan_dependencies() -> EditorialPlanDependencies:
    """Resolve the production collaborators without module-object dispatch."""
    from data_sources.modules.blog_assembly_contract import (
        canonical_json_sha256,
        canonical_snapshot_artifact,
        load_json_object_snapshot,
        resolve_artifact,
    )
    from data_sources.modules.execution_attestation import (
        attest_mapping,
        verify_mapping_attestation,
    )
    from data_sources.modules.frontmatter import split_frontmatter
    from data_sources.modules.industry_cluster_link_policy import (
        editorial_plan_findings,
        link_policy_override_count_supported,
        resolve_required_policy,
    )

    return EditorialPlanDependencies(
        canonical_json_sha256=canonical_json_sha256,
        canonical_snapshot_artifact=canonical_snapshot_artifact,
        load_json_object_snapshot=load_json_object_snapshot,
        resolve_artifact=resolve_artifact,
        attest_mapping=attest_mapping,
        verify_mapping_attestation=verify_mapping_attestation,
        split_frontmatter=split_frontmatter,
        resolve_required_industry_policy=resolve_required_policy,
        editorial_plan_industry_findings=editorial_plan_findings,
        link_policy_override_count_supported=link_policy_override_count_supported,
    )


__all__ = [
    "EditorialPlanDependencies",
    "default_editorial_plan_dependencies",
]
