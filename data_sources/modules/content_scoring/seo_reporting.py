"""Focused seo reporting scoring."""

from __future__ import annotations

from .seo_constants import PUBLISHING_THRESHOLD
from .seo_constants import SEO_TARGET_SCORE
from .seo_link import _count_markdown_links
from .seo_link import _resolve_article_brand
from .seo_metadata import _extract_frontmatter
from .seo_metadata import _non_negative_finite_float
from .seo_metadata import _resolve_metadata
from pathlib import Path
from typing import Any
from typing import Dict
from typing import List
from typing import Optional
import argparse
import sys
from .seo_rater_orchestration import rate_seo_quality


def _format_report(result: Dict[str, Any]) -> str:
    lines = [
        "=== SEO Quality Report ===",
        "",
        f"Overall Score: {result['overall_score']}/100",
        f"Grade: {result['grade']}",
        f"Publishing Ready: {result['publishing_ready']}",
        f"Release Floor: {result.get('threshold', PUBLISHING_THRESHOLD)}",
        f"Optimization Target: {result.get('target', SEO_TARGET_SCORE)}",
        f"Target Status: {result.get('target_status', 'unknown')}",
        "",
        "Category Scores:",
    ]

    for category, score in result["category_scores"].items():
        lines.append(f"  {category}: {score}/100")

    if result["critical_issues"]:
        lines.append("")
        lines.append("Critical Issues:")
        for issue in result["critical_issues"]:
            lines.append(f"  ERROR: {issue}")

    if result["warnings"]:
        lines.append("")
        lines.append("Warnings:")
        for warning in result["warnings"]:
            lines.append(f"  WARNING: {warning}")

    if result["suggestions"]:
        lines.append("")
        lines.append("Suggestions:")
        for suggestion in result["suggestions"][:5]:
            lines.append(f"  SUGGESTION: {suggestion}")

    details = result.get("details", {})
    if details:
        lines.append("")
        lines.append("Details:")
        for key, value in details.items():
            lines.append(f"  {key}: {value}")

    return "\n".join(lines)

def _sample_content() -> str:
    return """
# How to Start a Podcast

Starting a podcast is easier than you think. This complete guide shows you how to start a podcast from scratch.

## Choose Your Topic

Pick a topic you're passionate about. Your podcast topic should resonate with your target audience.

## Get Equipment

You'll need a microphone, headphones, and recording software.

## Record Your First Episode

Start recording! Don't worry about perfection on your first try.

## Publish Your Podcast

Upload to a podcast hosting platform and distribute to directories.

Ready to start your podcast? Begin today with these simple steps.
    """

def _run_sample() -> Dict[str, Any]:
    return rate_seo_quality(
        content=_sample_content(),
        meta_title="How to Start a Podcast: Complete Guide for 2024",
        meta_description="Learn how to start a podcast from scratch with this step-by-step guide. Everything you need to know about podcast equipment, recording, and publishing.",
        primary_keyword="start a podcast",
        secondary_keywords=["podcast hosting", "recording software"],
        keyword_density=1.8,
        internal_link_count=4,
        external_link_count=2,
    )

def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Rate markdown content against SEO quality rules.")
    parser.add_argument("path", nargs="?", help="Markdown file to rate. If omitted, runs the built-in sample.")
    parser.add_argument("--meta-title", help="Override or provide meta title.")
    parser.add_argument("--meta-description", help="Override or provide meta description.")
    parser.add_argument("--primary-keyword", help="Override or provide primary keyword.")
    parser.add_argument("--secondary-keywords", help="Comma-separated secondary keywords.")
    parser.add_argument(
        "--keyword-density",
        type=_non_negative_finite_float,
        help=(
            "Deprecated diagnostic percentage retained for compatibility; "
            "it does not change the quality score."
        ),
    )
    parser.add_argument(
        "--validate-urls",
        action="store_true",
        help=(
            "Resolve article URLs and fail readiness on unresolved/manual-review links. "
            "Standard posts use 2+ distinct non-owned authority sources as the baseline. "
            "Add no quota-only third source, and apply no maximum to claim-required "
            "evidence."
        ),
    )

    args = parser.parse_args(argv)

    if not args.path:
        result = _run_sample()
        print(_format_report(result))
        return 0

    file_path = Path(args.path)
    if not file_path.exists():
        print(f"Error: File not found: {file_path}", file=sys.stderr)
        return 1

    content = file_path.read_text(encoding="utf-8")
    meta_title, meta_description, primary_keyword = _resolve_metadata(
        content,
        args.meta_title,
        args.meta_description,
        args.primary_keyword,
    )
    secondary_keywords = None
    if args.secondary_keywords:
        secondary_keywords = [
            keyword.strip()
            for keyword in args.secondary_keywords.split(",")
            if keyword.strip()
        ]

    frontmatter = _extract_frontmatter(content)
    article_brand = _resolve_article_brand(
        explicit_brand=None,
        frontmatter_brand=frontmatter.get("brand"),
        meta_title=meta_title,
    )
    internal_links, external_links = _count_markdown_links(
        content,
        brand=article_brand,
    )
    result = rate_seo_quality(
        content=content,
        meta_title=meta_title,
        meta_description=meta_description,
        primary_keyword=primary_keyword,
        secondary_keywords=secondary_keywords,
        keyword_density=args.keyword_density,
        internal_link_count=internal_links,
        external_link_count=external_links,
        validate_urls=args.validate_urls,
        brand=article_brand,
    )

    print(_format_report(result))
    return 0 if result["publishing_ready"] else 1


__all__ = [
    "_format_report",
    "_sample_content",
    "_run_sample",
    "main",
]
