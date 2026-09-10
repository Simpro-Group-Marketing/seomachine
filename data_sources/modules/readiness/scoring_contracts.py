"""Dependency-free scoring thresholds and lazy scorer factories."""

from __future__ import annotations

from functools import lru_cache
from typing import Any, Type


SEO_PUBLISHING_THRESHOLD = 90
SEO_TARGET_SCORE = 95


@lru_cache(maxsize=1)
def content_scorer_class() -> Type[Any]:
    """Load the blog scorer only after all pre-scoring gates pass."""
    try:
        from ..content_scorer import ContentScorer
    except ImportError:  # pragma: no cover - direct script compatibility.
        from content_scorer import ContentScorer
    return ContentScorer


@lru_cache(maxsize=1)
def landing_page_scorer_class() -> Type[Any]:
    """Load the landing-page scorer only when that artifact is scored."""
    try:
        from ..landing_page_scorer import LandingPageScorer
    except ImportError:  # pragma: no cover - direct script compatibility.
        from landing_page_scorer import LandingPageScorer
    return LandingPageScorer


def create_content_scorer(*args: Any, **kwargs: Any) -> Any:
    return content_scorer_class()(*args, **kwargs)


def create_landing_page_scorer(*args: Any, **kwargs: Any) -> Any:
    return landing_page_scorer_class()(*args, **kwargs)


def compatibility_symbols() -> tuple[Any, Any, int, int]:
    """Return legacy factories and thresholds without importing scorer modules."""
    return (
        create_content_scorer,
        create_landing_page_scorer,
        SEO_PUBLISHING_THRESHOLD,
        SEO_TARGET_SCORE,
    )
