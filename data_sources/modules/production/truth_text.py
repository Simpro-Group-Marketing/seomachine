"""Finding record and public-copy extraction shared by the production truth checks."""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class Finding:
    check: str
    severity: str  # "block" | "warn"
    message: str
    line: int | None


_FENCE = re.compile(r"(?ms)^[ \t]*(`{3,}|~{3,}).*?(?:^[ \t]*\1[^\n]*$|\Z)")
_COMMENT = re.compile(r"<!--.*?-->", re.DOTALL)
_INLINE_CODE = re.compile(r"`[^`\n]*`")
_LINK = re.compile(r"!?\[([^\]]*)\]\([^)]*\)")
_LINK_DEFINITION = re.compile(r"^\s*\[[^\]]+\]:\s*\S+.*$")
_HTML_TAG = re.compile(r"<[^>]+>")
_BARE_URL = re.compile(r"(?:https?://|www\.)\S+", re.IGNORECASE)
_HEADING = re.compile(r"^\s{0,3}#{1,6}\s+")
_LIST_MARKER = re.compile(r"^\s*(?:\d+[.)]|[-*+])\s+")
_FRONT_KEY = re.compile(r"^([A-Za-z_][\w-]*):\s*(.*)$")
_PUBLIC_FRONT_KEYS = frozenset({"title", "description"})
_BLOCK_SCALARS = frozenset({">", "|", ">-", "|-", ">+", "|+"})


def _blank(match: re.Match[str]) -> str:
    return re.sub(r"[^\n]", "", match.group(0))


def _split_frontmatter(lines: list[str]) -> tuple[list[str], list[str]]:
    """Return (frontmatter lines incl. delimiters, body lines); no frontmatter gives ([], lines)."""
    if not lines or lines[0].strip() != "---":
        return [], lines
    for index in range(1, len(lines)):
        if lines[index].strip() == "---":
            return lines[: index + 1], lines[index + 1 :]
    return [], lines


def _frontmatter_lines(lines: list[str]) -> list[str]:
    """Keep only title and description values; every other line is blanked so line numbers hold."""
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


def _clean_line(line: str) -> str:
    if _LINK_DEFINITION.match(line):
        return ""
    quote_prefix = ">" if line.lstrip().startswith(">") else ""
    if quote_prefix:
        line = line.lstrip().lstrip(">")
    else:
        line = _LIST_MARKER.sub("", _HEADING.sub("", line, count=1), count=1)
    line = _INLINE_CODE.sub(" ", line)
    line = _LINK.sub(r"\1", line)
    line = _HTML_TAG.sub(" ", _BARE_URL.sub(" ", line))
    return quote_prefix + line


def public_copy_lines(article: str) -> list[str]:
    """Return one entry per article line holding only reader-visible text (blank when none).

    Public copy is the body, headings, and the frontmatter title and description. Other
    frontmatter, URLs inside links and images, code, and HTML comments are blanked.
    Index ``n`` is file line ``n + 1``.
    """
    front, body = _split_frontmatter(article.splitlines())
    body_text = _COMMENT.sub(_blank, _FENCE.sub(_blank, "\n".join(body)))
    cleaned = [_clean_line(line) for line in body_text.split("\n")] if body else []
    return _frontmatter_lines(front) + cleaned
