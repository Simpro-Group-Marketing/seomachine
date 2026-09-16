"""Markdown-aware line preparation for the AI copy linter."""

from __future__ import annotations

import re
from typing import Pattern

try:
    from ..image_placeholder import is_production_image_placeholder_line
except ImportError:
    from image_placeholder import is_production_image_placeholder_line

from .rules import (
    APPROVED_PROPER_NOUNS,
    HTML_TAG_RE,
    INLINE_CODE_RE,
    MARKDOWN_LINK_RE,
    NON_VISIBLE_HTML_CLOSE_RE,
    NON_VISIBLE_HTML_OPEN_RE,
    URL_RE,
)


ActiveLine = tuple[int, str, str]


def iter_active_lines(content: str) -> list[ActiveLine]:
    """Return visible, lintable lines with non-copy spans masked."""
    active: list[ActiveLine] = []
    in_code_fence = False
    in_frontmatter = False
    in_non_visible_html = False

    for line_number, line in enumerate(content.splitlines(), start=1):
        stripped = line.strip()
        if line_number == 1 and stripped == "---":
            in_frontmatter = True
            continue
        if in_frontmatter:
            if stripped == "---":
                in_frontmatter = False
            continue
        if stripped.startswith("```"):
            in_code_fence = not in_code_fence
            continue
        if in_code_fence:
            continue
        if in_non_visible_html:
            if NON_VISIBLE_HTML_CLOSE_RE.search(line):
                in_non_visible_html = False
            continue
        if NON_VISIBLE_HTML_OPEN_RE.search(line):
            if not NON_VISIBLE_HTML_CLOSE_RE.search(line):
                in_non_visible_html = True
            continue
        if is_production_image_placeholder_line(stripped):
            continue
        active.append((line_number, line, mask_ignored_spans(line)))
    return active


def mask_ignored_spans(line: str) -> str:
    """Mask markup and approved proper nouns without changing columns."""
    masked = line
    for pattern in (HTML_TAG_RE, MARKDOWN_LINK_RE, URL_RE, INLINE_CODE_RE):
        masked = mask_matches(masked, pattern)
    for noun in APPROVED_PROPER_NOUNS:
        masked = re.sub(
            re.escape(noun),
            lambda match: " " * (match.end() - match.start()),
            masked,
            flags=re.IGNORECASE,
        )
    return masked


def mask_humanizer_protected_spans(original_line: str, masked_line: str) -> str:
    """Mask quoted and blockquoted prose excluded from humanizer policy rules."""
    from .rules import HTML_COMMENT_RE, SMART_QUOTE_RE, STRAIGHT_QUOTE_RE

    if original_line.lstrip().startswith(">"):
        return " " * len(masked_line)
    protected = masked_line
    for pattern in (HTML_COMMENT_RE, STRAIGHT_QUOTE_RE, SMART_QUOTE_RE):
        protected = mask_matches(protected, pattern)
    return protected


def mask_matches(text: str, pattern: Pattern[str]) -> str:
    """Replace matched text with spaces to preserve source columns."""
    return pattern.sub(lambda match: " " * (match.end() - match.start()), text)
