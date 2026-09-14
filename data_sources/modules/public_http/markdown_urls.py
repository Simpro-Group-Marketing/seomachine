"""Extract normalized public URLs from reader-visible Markdown."""

from __future__ import annotations

import re
from dataclasses import dataclass
from urllib.parse import urljoin, urlparse


DEFAULT_BASE_URL = "https://www.simprogroup.com"
MARKDOWN_LINK_RE = re.compile(r"(?<!!)\[([^\]]+)\]\(([^)]+)\)")
MARKDOWN_IMAGE_RE = re.compile(r"!\[[^\]]*\]\([^)]+\)")
BARE_URL_RE = re.compile(r"https?://[^\s<>\]\"')]+")
FENCED_CODE_RE = re.compile(r"```.*?```", re.DOTALL)
INLINE_CODE_RE = re.compile(r"`[^`\n]*`")
FRONTMATTER_RE = re.compile(r"\A---\s*\n.*?\n---\s*", re.DOTALL)
SKIPPED_SCHEMES = {"mailto", "tel"}


@dataclass(frozen=True)
class ExtractedUrl:
    """A URL found in article content."""

    url: str
    line: int
    source: str
    anchor: str = ""
    raw_url: str = ""


def extract_urls(content: str, base_url: str = DEFAULT_BASE_URL) -> list[ExtractedUrl]:
    """Extract Markdown and bare URLs from article body content."""
    prepared = _strip_frontmatter_preserve_lines(content)
    prepared = _blank_fenced_code(prepared)
    prepared = INLINE_CODE_RE.sub("", prepared)
    prepared = MARKDOWN_IMAGE_RE.sub(
        lambda match: " " * (match.end() - match.start()),
        prepared,
    )
    markdown_links: list[ExtractedUrl] = []

    def blank_markdown_link(match: re.Match[str]) -> str:
        anchor = match.group(1).strip()
        raw_url = _normalize_markdown_destination(match.group(2))
        normalized = _normalize_url(raw_url, base_url)
        if normalized:
            markdown_links.append(
                ExtractedUrl(
                    url=normalized,
                    line=_line_number(prepared, match.start()),
                    source="markdown",
                    anchor=anchor,
                    raw_url=raw_url,
                )
            )
        return " " * (match.end() - match.start())

    without_markdown = MARKDOWN_LINK_RE.sub(blank_markdown_link, prepared)
    return markdown_links + _bare_urls(without_markdown, base_url=base_url)


def _bare_urls(content: str, *, base_url: str) -> list[ExtractedUrl]:
    values: list[ExtractedUrl] = []
    for match in BARE_URL_RE.finditer(content):
        raw_url = _strip_trailing_url_punctuation(match.group(0))
        normalized = _normalize_url(raw_url, base_url)
        if normalized:
            values.append(
                ExtractedUrl(
                    url=normalized,
                    line=_line_number(content, match.start()),
                    source="bare",
                    raw_url=raw_url,
                )
            )
    return values


def _strip_frontmatter_preserve_lines(content: str) -> str:
    match = FRONTMATTER_RE.match(content)
    if not match:
        return content
    return "\n" * match.group(0).count("\n") + content[match.end():]


def _blank_fenced_code(content: str) -> str:
    return FENCED_CODE_RE.sub(lambda match: "\n" * match.group(0).count("\n"), content)


def _line_number(content: str, index: int) -> int:
    return content.count("\n", 0, index) + 1


def _normalize_markdown_destination(destination: str) -> str:
    cleaned = destination.strip()
    if cleaned.startswith("<") and ">" in cleaned:
        return cleaned[1:cleaned.index(">")]
    return cleaned.split()[0].strip("<>") if cleaned else ""


def _normalize_url(raw_url: str, base_url: str) -> str:
    cleaned = _strip_trailing_url_punctuation(raw_url.strip())
    if not cleaned:
        return ""
    parsed = urlparse(cleaned)
    if parsed.scheme in SKIPPED_SCHEMES or cleaned.startswith("#"):
        return ""
    if parsed.scheme in {"http", "https"}:
        return cleaned
    if cleaned.startswith("www."):
        return f"https://{cleaned}"
    if parsed.scheme:
        return ""
    return urljoin(base_url.rstrip("/") + "/", cleaned)


def _strip_trailing_url_punctuation(url: str) -> str:
    return url.rstrip(".,;:!?")
