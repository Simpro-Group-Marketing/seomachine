"""Compatibility facade for editorial-plan snapshot adapters."""

from .editorial_plan.snapshot_adapters import (
    final_article_content,
    link_policy_article,
    link_policy_brief,
)

__all__ = [
    "final_article_content",
    "link_policy_article",
    "link_policy_brief",
]
