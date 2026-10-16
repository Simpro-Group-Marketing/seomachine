"""Explicit dependency contract shared by content-scoring mixins."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class ScoringDependencies:
    """Frozen collaborators for one serial scoring run."""

    readability_scorer_factory: Callable[[], Any]
    seo_rater_factory: Callable[..., Any]
    rate_aeo_geo: Callable[..., dict[str, Any]]
    lint_content: Callable[..., Any]
    split_frontmatter: Callable[..., Any]
    load_sidecar_content: Callable[..., Any]
    resolve_sidecar_path: Callable[..., Any]
    check_source_support: Callable[..., Any]
    validate_content_urls: Callable[..., Any]


def default_scoring_dependencies() -> ScoringDependencies:
    """Load scoring dependencies only when a scorer is instantiated."""
    from data_sources.modules.ai_copy_linter import lint_content
    from data_sources.modules.content_scoring.aeo_orchestration import rate_aeo_geo
    from data_sources.modules.frontmatter import split_frontmatter
    from data_sources.modules.proof_sidecar import (
        load_sidecar_content,
        resolve_sidecar_path,
    )
    from data_sources.modules.readability_scorer import ReadabilityScorer
    from data_sources.modules.content_scoring.seo_rater_orchestration import SEOQualityRater
    from data_sources.modules.source_support_guard import check_content as check_source_support
    from data_sources.modules.url_validator import validate_content_urls

    return ScoringDependencies(
        readability_scorer_factory=ReadabilityScorer,
        seo_rater_factory=SEOQualityRater,
        rate_aeo_geo=rate_aeo_geo,
        lint_content=lint_content,
        split_frontmatter=split_frontmatter,
        load_sidecar_content=load_sidecar_content,
        resolve_sidecar_path=resolve_sidecar_path,
        check_source_support=check_source_support,
        validate_content_urls=validate_content_urls,
    )


__all__ = [
    "ScoringDependencies",
    "default_scoring_dependencies",
]
