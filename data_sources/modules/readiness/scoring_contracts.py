"""Lazy landing-page scorer factory."""

from __future__ import annotations

from functools import lru_cache
from typing import Any, Type


@lru_cache(maxsize=1)
def landing_page_scorer_class() -> Type[Any]:
    """Load the landing-page scorer only when a page is scored."""
    try:
        from ..landing_page_scorer import LandingPageScorer
    except ImportError:  # pragma: no cover - direct script compatibility.
        from landing_page_scorer import LandingPageScorer
    return LandingPageScorer


def create_landing_page_scorer(*args: Any, **kwargs: Any) -> Any:
    return landing_page_scorer_class()(*args, **kwargs)
