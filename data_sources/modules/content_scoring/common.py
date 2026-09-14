"""Explicit dependency contract shared by content-scoring mixins."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class ScoringDependencies:
    """Frozen collaborators for one serial scoring run."""

    readability_scorer_factory: Callable[[], Any]
    seo_rater_factory: Callable[..., Any]
    rate_aeo_geo: Callable[..., dict[str, Any]]
    lint_content: Callable[..., Any]
    check_customer_proof_diversity: Callable[..., Any]
    split_frontmatter: Callable[..., Any]
    check_metric_proof_pack: Callable[..., Any]
    load_sidecar_content: Callable[..., Any]
    resolve_sidecar_path: Callable[..., Any]
    trusted_readiness_findings: Callable[..., Any]
    check_review_story_identity: Callable[..., Any]
    check_source_support: Callable[..., Any]
    validate_content_urls: Callable[..., Any]


def default_scoring_dependencies() -> ScoringDependencies:
    """Load scoring dependencies only when a scorer is instantiated."""
    from data_sources.modules.aeo_geo_rater import rate_aeo_geo
    from data_sources.modules.ai_copy_linter import lint_content
    from data_sources.modules.customer_proof_diversity_guard import (
        check_content as check_customer_proof_diversity,
    )
    from data_sources.modules.frontmatter import split_frontmatter
    from data_sources.modules.metric_proof_pack_guard import (
        check_content as check_metric_proof_pack,
    )
    from data_sources.modules.proof_sidecar import (
        load_sidecar_content,
        resolve_sidecar_path,
    )
    from data_sources.modules.readability_scorer import ReadabilityScorer
    from data_sources.modules.readiness_gate_context import trusted_readiness_findings
    from data_sources.modules.review_story_identity_guard import (
        check_content as check_review_story_identity,
    )
    from data_sources.modules.seo_quality_rater import SEOQualityRater
    from data_sources.modules.source_support_guard import check_content as check_source_support
    from data_sources.modules.url_validator import validate_content_urls

    return ScoringDependencies(
        readability_scorer_factory=ReadabilityScorer,
        seo_rater_factory=SEOQualityRater,
        rate_aeo_geo=rate_aeo_geo,
        lint_content=lint_content,
        check_customer_proof_diversity=check_customer_proof_diversity,
        split_frontmatter=split_frontmatter,
        check_metric_proof_pack=check_metric_proof_pack,
        load_sidecar_content=load_sidecar_content,
        resolve_sidecar_path=resolve_sidecar_path,
        trusted_readiness_findings=trusted_readiness_findings,
        check_review_story_identity=check_review_story_identity,
        check_source_support=check_source_support,
        validate_content_urls=validate_content_urls,
    )


def copy_prevalidated_findings(
    findings_by_gate: Mapping[str, Sequence[Mapping[str, Any]]] | None,
    gate_name: str,
) -> list[dict[str, Any]] | None:
    if findings_by_gate is None or gate_name not in findings_by_gate:
        return None
    raw_findings = findings_by_gate[gate_name]
    if isinstance(raw_findings, (str, bytes)) or not isinstance(raw_findings, Sequence):
        raise TypeError(f"prevalidated findings for {gate_name!r} must be a sequence")
    copied: list[dict[str, Any]] = []
    for index, finding in enumerate(raw_findings):
        if not isinstance(finding, Mapping):
            raise TypeError(f"prevalidated finding {gate_name}[{index}] must be a mapping")
        copied.append(dict(finding))
    return copied


__all__ = [
    "ScoringDependencies",
    "copy_prevalidated_findings",
    "default_scoring_dependencies",
]
