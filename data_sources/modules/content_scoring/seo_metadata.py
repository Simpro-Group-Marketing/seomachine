"""Focused seo metadata scoring."""

from __future__ import annotations

from .seo_constants import META_TITLE_BRAND_SUFFIX_RE
from .seo_constants import SEO_TARGET_SCORE
from data_sources.modules.frontmatter import split_frontmatter
from typing import Dict
from typing import Optional
from typing import Tuple
import argparse
import math
import re

def seo_target_status(
    *,
    score: float,
    publishing_ready: bool,
    target: int = SEO_TARGET_SCORE,
) -> str:
    """Classify SEO target status without changing release readiness."""
    if not publishing_ready:
        return "failed_floor"
    if score >= target:
        return "met"
    return "below_target"

def _non_negative_finite_float(value: str) -> float:
    parsed = float(value)
    if not math.isfinite(parsed) or parsed < 0:
        raise argparse.ArgumentTypeError("must be a finite non-negative number")
    return parsed

def _has_meta_title_brand_suffix(meta_title: str) -> bool:
    return bool(META_TITLE_BRAND_SUFFIX_RE.search(meta_title.strip()))

def _count_visible_words(content: str) -> int:
    """Count reader-visible words in an article body for link-density policy."""
    _, body, _ = split_frontmatter(content)
    body = re.sub(r"!\[[^\]]*\]\([^)]*\)", " ", body)
    body = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", body)
    return len(re.findall(r"[A-Za-z0-9]+", body))

def _extract_frontmatter(content: str) -> Dict[str, str]:
    metadata, _, _ = split_frontmatter(content)
    return {
        key: value
        for key, value in metadata.items()
        if isinstance(value, str)
    }

def _extract_inline_metadata(content: str) -> Dict[str, str]:
    patterns = {
        "meta_title": r"^\s*(?:\*\*)?Meta Title(?:\*\*)?:\s*(.+)$",
        "meta_description": r"^\s*(?:\*\*)?Meta Description(?:\*\*)?:\s*(.+)$",
        "primary_keyword": r"^\s*(?:\*\*)?(?:Primary|Target) Keyword(?:\*\*)?:\s*(.+)$",
    }
    metadata = {}

    for key, pattern in patterns.items():
        match = re.search(pattern, content, re.MULTILINE | re.IGNORECASE)
        if match:
            metadata[key] = match.group(1).strip()

    return metadata

def _resolve_metadata(
    content: str,
    meta_title: Optional[str],
    meta_description: Optional[str],
    primary_keyword: Optional[str],
) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    frontmatter = _extract_frontmatter(content)
    _, body, _ = split_frontmatter(content)
    inline = _extract_inline_metadata(body)

    resolved_title = (
        meta_title
        or inline.get("meta_title")
        or frontmatter.get("meta_title")
        or frontmatter.get("title")
    )
    resolved_description = (
        meta_description
        or inline.get("meta_description")
        or frontmatter.get("meta_description")
        or frontmatter.get("description")
    )
    resolved_keyword = (
        primary_keyword
        or inline.get("primary_keyword")
        or frontmatter.get("primary_keyword")
        or frontmatter.get("target_keyword")
    )

    return resolved_title, resolved_description, resolved_keyword


__all__ = [
    "seo_target_status",
    "_non_negative_finite_float",
    "_has_meta_title_brand_suffix",
    "_count_visible_words",
    "_extract_frontmatter",
    "_extract_inline_metadata",
    "_resolve_metadata",
]
