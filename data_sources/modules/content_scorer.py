"""Compatibility facade for the serial content-scoring package."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .readability_scorer import ReadabilityScorer

try:
    from .content_scoring.common import (
        ScoringDependencies,
        default_scoring_dependencies,
    )
    from .content_scoring.scorer import ContentScorer
    from .seo_quality_rater import (
        PUBLISHING_THRESHOLD as SEO_PUBLISHING_THRESHOLD,
        SEO_TARGET_SCORE,
        SEOQualityRater,
    )
except ImportError:  # pragma: no cover - direct script compatibility.
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from data_sources.modules.content_scoring.common import (
        ScoringDependencies,
        default_scoring_dependencies,
    )
    from data_sources.modules.content_scoring.scorer import ContentScorer
    from data_sources.modules.seo_quality_rater import (
        PUBLISHING_THRESHOLD as SEO_PUBLISHING_THRESHOLD,
        SEO_TARGET_SCORE,
        SEOQualityRater,
    )


def __getattr__(name: str) -> Any:
    """Resolve the historical readability class without eager textstat import."""
    if name == "ReadabilityScorer":
        return default_scoring_dependencies().readability_scorer_factory
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def rate_aeo_geo(*args: Any, **kwargs: Any) -> Any:
    return default_scoring_dependencies().rate_aeo_geo(*args, **kwargs)


def lint_content(*args: Any, **kwargs: Any) -> Any:
    return default_scoring_dependencies().lint_content(*args, **kwargs)


def check_customer_proof_diversity(*args: Any, **kwargs: Any) -> Any:
    dependency = default_scoring_dependencies().check_customer_proof_diversity
    return dependency(*args, **kwargs)


def split_frontmatter(*args: Any, **kwargs: Any) -> Any:
    return default_scoring_dependencies().split_frontmatter(*args, **kwargs)


def check_metric_proof_pack(*args: Any, **kwargs: Any) -> Any:
    return default_scoring_dependencies().check_metric_proof_pack(*args, **kwargs)


def load_sidecar_content(*args: Any, **kwargs: Any) -> Any:
    return default_scoring_dependencies().load_sidecar_content(*args, **kwargs)


def resolve_sidecar_path(*args: Any, **kwargs: Any) -> Any:
    return default_scoring_dependencies().resolve_sidecar_path(*args, **kwargs)


def trusted_readiness_findings(*args: Any, **kwargs: Any) -> Any:
    dependency = default_scoring_dependencies().trusted_readiness_findings
    return dependency(*args, **kwargs)


def check_review_story_identity(*args: Any, **kwargs: Any) -> Any:
    dependency = default_scoring_dependencies().check_review_story_identity
    return dependency(*args, **kwargs)


def check_source_support(*args: Any, **kwargs: Any) -> Any:
    return default_scoring_dependencies().check_source_support(*args, **kwargs)


def validate_content_urls(*args: Any, **kwargs: Any) -> Any:
    return default_scoring_dependencies().validate_content_urls(*args, **kwargs)


def main(argv: Sequence[str] | None = None) -> None:
    """Run the extracted standalone scorer CLI through this compatibility facade."""
    try:
        from .content_scoring.cli import main as cli_main
    except ImportError:  # pragma: no cover - direct script compatibility.
        from data_sources.modules.content_scoring.cli import main as cli_main

    raise SystemExit(cli_main(argv))


__all__ = [
    "ContentScorer",
    "ReadabilityScorer",
    "SEOQualityRater",
    "SEO_PUBLISHING_THRESHOLD",
    "SEO_TARGET_SCORE",
    "ScoringDependencies",
    "check_customer_proof_diversity",
    "check_metric_proof_pack",
    "check_review_story_identity",
    "check_source_support",
    "lint_content",
    "load_sidecar_content",
    "main",
    "rate_aeo_geo",
    "resolve_sidecar_path",
    "split_frontmatter",
    "trusted_readiness_findings",
    "validate_content_urls",
]


if __name__ == "__main__":
    main()
