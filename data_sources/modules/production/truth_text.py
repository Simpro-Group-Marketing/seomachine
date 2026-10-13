"""Finding record, public-copy extraction, and paragraph units shared by the truth checks."""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass

from data_sources.modules.image_placeholder import (
    is_production_image_placeholder_line,
    is_production_video_placeholder_line,
)


@dataclass(frozen=True)
class Finding:
    check: str
    severity: str  # "block" | "warn"
    message: str
    line: int | None


@dataclass(frozen=True)
class Unit:
    """One public paragraph, list item, table row, heading, or FAQ answer."""

    line: int
    end_line: int
    heading: bool
    text: tuple[str, ...]  # reader-visible text, one entry per line


_FENCE = re.compile(r"(?ms)^[ \t]*(`{3,}|~{3,}).*?(?:^[ \t]*\1[^\n]*$|\Z)")
_COMMENT = re.compile(r"<!--.*?-->", re.DOTALL)
_BLOCKQUOTE_ELEMENT = re.compile(r"<blockquote\b[^>]*>.*?</blockquote>", re.DOTALL | re.IGNORECASE)
_Q_ELEMENT = re.compile(r"<q\b[^>]*>(.*?)</q>", re.IGNORECASE)
_INLINE_CODE = re.compile(r"`[^`\n]*`")
_LINK = re.compile(r"!?\[([^\]]*)\]\([^)]*\)")
_FOOTNOTE_DEFINITION = re.compile(r"^\s*\[\^[^\]]+\]:\s*")
_FOOTNOTE_REFERENCE = re.compile(r"\[\^[^\]]+\]")
_LINK_DEFINITION = re.compile(r"^\s*\[[^\]^][^\]]*\]:\s*\S+.*$")
_HTML_TAG = re.compile(r"<[^>]+>")
_ALT_ATTRIBUTE = re.compile(r"""\balt\s*=\s*(?:"([^"]*)"|'([^']*)')""", re.IGNORECASE)
_BARE_URL = re.compile(r"(?:https?://|www\.)\S+", re.IGNORECASE)
_HEADING = re.compile(r"^\s{0,3}#{1,6}\s+")
_LIST_MARKER = re.compile(r"^\s*(?:\d+[.)]|[-*+])\s+")
_FRONT_KEY = re.compile(r"^([A-Za-z_][\w-]*):\s*(.*)$")
_PUBLIC_FRONT_KEYS = frozenset({"title", "description", "meta_title", "meta_description"})
_BLOCK_SCALARS = frozenset({">", "|", ">-", "|-", ">+", "|+"})
_PLACEHOLDER_START = re.compile(r"^\s*\[(?:IMAGE|VIDEO|CMS\s+MODULE)\s+PLACEHOLDER\b", re.IGNORECASE)
_PLACEHOLDER_CALLOUT = re.compile(r"^\s*>\s*\*\*(?:Hero\s+)?(?:Image|Video)\s+placeholder:\*\*", re.IGNORECASE)
_H3 = re.compile(r"^\s{0,3}###\s+\S")


def _blank(match: re.Match[str]) -> str:
    return re.sub(r"[^\n]", "", match.group(0))


def _quote_lines(match: re.Match[str]) -> str:
    """Turn a <blockquote> element into markdown blockquote lines, keeping the line count."""
    return "\n".join("> " + _HTML_TAG.sub(" ", line).strip() for line in match.group(0).split("\n"))


def _is_placeholder(line: str) -> bool:
    return (
        _PLACEHOLDER_START.match(line) is not None
        or _PLACEHOLDER_CALLOUT.match(line) is not None
        or is_production_image_placeholder_line(line)
        or is_production_video_placeholder_line(line)
    )


def _split_frontmatter(lines: list[str]) -> tuple[list[str], list[str]]:
    """Return (frontmatter lines incl. delimiters, body lines); no frontmatter gives ([], lines)."""
    if not lines or lines[0].strip() != "---":
        return [], lines
    for index in range(1, len(lines)):
        if lines[index].strip() == "---":
            return lines[: index + 1], lines[index + 1 :]
    return [], lines


def _frontmatter_lines(lines: list[str]) -> list[str]:
    """Keep only the public metadata values; every other line is blanked so line numbers hold."""
    kept: list[str] = []
    public = False
    for position, line in enumerate(lines):
        if position in (0, len(lines) - 1):
            kept.append("")
            continue
        match = _FRONT_KEY.match(line)
        if match:
            public = match.group(1).lower() in _PUBLIC_FRONT_KEYS
            value = match.group(2).strip()
            kept.append("" if value in _BLOCK_SCALARS or not public else value.strip("\"'"))
        else:
            kept.append(line.strip() if public else "")
    return kept


def _strip_tags(line: str) -> str:
    """Drop HTML tags but keep the text of any alt attribute, which readers and engines see."""
    def keep_alt(match: re.Match[str]) -> str:
        values = [first or second for first, second in _ALT_ATTRIBUTE.findall(match.group(0))]
        return " " + " ".join(values) + " "

    return _HTML_TAG.sub(keep_alt, line)


def _clean_line(line: str) -> str:
    if _LINK_DEFINITION.match(line):
        return ""
    quote_prefix = ">" if line.lstrip().startswith(">") else ""
    if quote_prefix:
        line = line.lstrip().lstrip(">")
    else:
        line = _LIST_MARKER.sub("", _HEADING.sub("", line, count=1), count=1)
    line = _Q_ELEMENT.sub(lambda match: f'"{match.group(1)}"', line)
    line = _FOOTNOTE_REFERENCE.sub(" ", _FOOTNOTE_DEFINITION.sub("", line))
    line = _LINK.sub(r"\1", _INLINE_CODE.sub(" ", line))
    return quote_prefix + _strip_tags(_BARE_URL.sub(" ", line))


def _views(article: str) -> tuple[list[str], list[str]]:
    """Return (frontmatter lines, body lines) with code, comments, and placeholders blanked."""
    front, body = _split_frontmatter(article.splitlines())
    text = _COMMENT.sub(_blank, _FENCE.sub(_blank, "\n".join(body)))
    text = _BLOCKQUOTE_ELEMENT.sub(_quote_lines, text)
    rows = [("" if _is_placeholder(line) else line) for line in text.split("\n")] if body else []
    return front, rows


def body_lines(article: str) -> list[str]:
    """Raw markdown per article line (links kept), with frontmatter, code, and comments blanked."""
    front, rows = _views(article)
    return [""] * len(front) + rows


def public_copy_lines(article: str) -> list[str]:
    """Return one entry per article line holding only reader-visible text (blank when none).

    Public copy is the body, headings, footnotes, alt text, quotes, and the frontmatter
    title, description, meta_title, and meta_description. Other frontmatter, URLs inside
    links and images, code, HTML comments, and media placeholder markers are blanked.
    Index ``n`` is file line ``n + 1``.
    """
    front, rows = _views(article)
    return _frontmatter_lines(front) + [_clean_line(line) for line in rows]


def _kind(line: str) -> str:
    if _HEADING.match(line):
        return "heading"
    if line.lstrip().startswith("|"):
        return "row"
    return "item" if _LIST_MARKER.match(line) else "text"


def _unit_ranges(raw: Sequence[str]) -> list[tuple[int, int, bool]]:
    """Split raw lines into (first line, last line, is_heading) units."""
    ranges: list[tuple[int, int, bool]] = []
    start = 0

    def close(end: int) -> None:
        nonlocal start
        if start:
            ranges.append((start, end, False))
        start = 0

    for number, line in enumerate(raw, start=1):
        if not line.strip():
            close(number - 1)
            continue
        kind = _kind(line)
        if kind in ("heading", "row", "item"):
            close(number - 1)
        if kind in ("heading", "row"):
            ranges.append((number, number, kind == "heading"))
        elif not start:
            start = number
    close(len(raw))
    return ranges


def paragraph_units(article: str, answer_ranges: Sequence[tuple[int, int]] = ()) -> list[Unit]:
    """Return public units; each FAQ answer range (first line, last line) becomes one unit."""
    raw, public = body_lines(article), public_copy_lines(article)
    ranges = [item for item in _unit_ranges(raw) if not any(a <= item[0] <= b for a, b in answer_ranges)]
    ranges += [(first, last, False) for first, last in answer_ranges]
    return [
        Unit(first, last, heading, tuple(public[first - 1 : last]))
        for first, last, heading in sorted(ranges)
    ]


def meta_lines(article: str) -> list[tuple[int, str]]:
    """Return (line number, text) for each public frontmatter value (title, description, meta_*)."""
    front, _ = _views(article)
    return [(number, text) for number, text in enumerate(_frontmatter_lines(front), start=1) if text.strip()]


def h3_count(raw: Sequence[str], skip: tuple[int, int] | None = None) -> int:
    """Count ### headings in the body, leaving out those inside the ``skip`` line range."""
    first, last = skip or (0, -1)
    return sum(1 for number, line in enumerate(raw, start=1) if _H3.match(line) and not first <= number <= last)
