"""Adapters for legacy paths and immutable editorial-plan snapshots."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any
import hashlib

from .contracts import Finding
from .contracts import _finding


def link_policy_brief(
    override: Mapping[str, Any],
    *,
    plan_path: str | Path | None,
    brief_content: str | None,
    brief_sha256: str | None,
) -> tuple[bytes, str, Finding | None]:
    """Load legacy brief bytes or use the captured brief payload."""
    if brief_content is not None:
        content = brief_content.encode("utf-8")
        return content, brief_sha256 or hashlib.sha256(content).hexdigest(), None
    brief_path = _resolve_brief_path(override["brief_path"], plan_path=plan_path)
    try:
        content = brief_path.read_bytes()
    except OSError as error:
        return b"", "", _finding(
            "editorial_plan_link_policy_override_brief_unreadable",
            f"Link policy override brief cannot be read: {error}",
            "/link_policy_override/brief_path",
            "Restore the bound brief snapshot or remove the override.",
        )
    return content, hashlib.sha256(content).hexdigest(), None


def link_policy_article(
    article_path: str | Path | None,
    article_content: str | None,
) -> tuple[str, Finding | None]:
    """Load legacy article text or use the captured article payload."""
    if article_content is not None:
        return article_content, None
    try:
        return Path(str(article_path)).read_text(encoding="utf-8"), None
    except (OSError, UnicodeError) as error:
        return "", _finding(
            "editorial_plan_link_policy_override_article_unreadable",
            f"Article cannot be read for link-policy override validation: {error}",
            "/link_policy_override",
            "Restore the article or remove the override.",
        )


def final_article_content(
    article_path: str | Path | None,
    article_content: str | None,
) -> tuple[str, Finding | None]:
    """Load the final article through the compatibility or snapshot path."""
    if article_content is not None:
        return article_content, None
    try:
        return Path(str(article_path)).read_text(encoding="utf-8"), None
    except (OSError, UnicodeError) as error:
        return "", _finding(
            "editorial_plan_article_unreadable",
            f"Final article cannot be read for editorial-plan validation: {error}",
            "/",
            "Bind the current final article and rebuild the plan.",
        )


def _resolve_brief_path(
    raw_path: str,
    *,
    plan_path: str | Path | None,
) -> Path:
    candidate = Path(raw_path)
    if candidate.is_absolute():
        return candidate
    cwd_candidate = Path.cwd() / candidate
    if cwd_candidate.exists():
        return cwd_candidate
    if plan_path is not None:
        parent_candidate = Path(plan_path).parent / candidate
        if parent_candidate.exists():
            return parent_candidate
    return cwd_candidate


__all__ = [
    "final_article_content",
    "link_policy_article",
    "link_policy_brief",
]
