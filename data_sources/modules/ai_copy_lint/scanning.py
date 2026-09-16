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
        in_frontmatter, skip_frontmatter = _frontmatter_state(
            line_number,
            stripped,
            in_frontmatter,
        )
        if skip_frontmatter:
            continue
        in_code_fence, skip_code = _code_fence_state(stripped, in_code_fence)
        if skip_code:
            continue
        in_non_visible_html, skip_html = _html_comment_state(
            line,
            in_non_visible_html,
        )
        if skip_html or is_production_image_placeholder_line(stripped):
            continue
        active.append((line_number, line, mask_ignored_spans(line)))
    return active


def _frontmatter_state(
    line_number: int,
    stripped: str,
    in_frontmatter: bool,
) -> tuple[bool, bool]:
    if line_number == 1 and stripped == "---":
        return True, True
    if not in_frontmatter:
        return False, False
    return stripped != "---", True


def _code_fence_state(stripped: str, in_code_fence: bool) -> tuple[bool, bool]:
    if stripped.startswith("```"):
        return not in_code_fence, True
    return in_code_fence, in_code_fence


def _html_comment_state(line: str, in_non_visible_html: bool) -> tuple[bool, bool]:
    if in_non_visible_html:
        return not bool(NON_VISIBLE_HTML_CLOSE_RE.search(line)), True
    if not NON_VISIBLE_HTML_OPEN_RE.search(line):
        return False, False
    return not bool(NON_VISIBLE_HTML_CLOSE_RE.search(line)), True


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
