"""What a finished article offers to the coverage checks: headings, links, title, lead, FAQ questions."""

from __future__ import annotations

import html
import re
from dataclasses import dataclass

from data_sources.modules.artifact_detection import extract_frontmatter
from data_sources.modules.faq_structure import detect_faq_structure
from data_sources.modules.frontmatter import FrontmatterError
from data_sources.modules.production.serp_coverage import normalize_heading
from data_sources.modules.production.truth_index import canonical, question_key
from data_sources.modules.production.truth_quotes import normalize_passage
from data_sources.modules.production.truth_text import (
    IMAGE_LINE_MARK,
    Unit,
    body_lines,
    paragraph_units,
    public_copy_lines,
)
from data_sources.modules.public_http.markdown_urls import ExtractedUrl, extract_urls

LEAD_WORDS = 100
_HEADING = re.compile(r"^\s{0,3}(#{1,6})\s+")
_EMPHASIS = re.compile(r"[*_~`]")
_NON_WORD = re.compile(r"[^\w\s]")
_DEFINITION = re.compile(r"^\s*\[([^\^\]][^\]]*)\]:\s*<?(\S+?)>?(?:\s+.*)?$")
_REFERENCE = re.compile(r"(?<!!)\[([^\]\^]+)\](?:\[([^\]]*)\])?(?![(:])")


@dataclass(frozen=True)
class Heading:
    level: int
    line: int
    text: str


def anchor_key(text: str) -> str:
    """Compare anchors ignoring HTML entities, markdown emphasis, punctuation, case, and whitespace."""
    plain = _EMPHASIS.sub("", html.unescape(text)).casefold()
    return " ".join(_NON_WORD.sub(" ", plain).split())


def _plain(text: str) -> str:
    """Drop HTML entities, underscore emphasis, and code ticks before heading normalization."""
    return html.unescape(text).replace("_", " ").replace("`", "")


def contains_phrase(text: str, phrase: str) -> bool:
    """True when ``phrase`` appears in ``text`` as a contiguous run of normalized tokens."""
    words, wanted = normalize_heading(_plain(text)).split(), normalize_heading(_plain(phrase)).split()
    return bool(wanted) and any(words[i : i + len(wanted)] == wanted for i in range(len(words) - len(wanted) + 1))


def inline_references(raw: list[str]) -> list[str]:
    """Rewrite used reference-style links as inline links and blank every reference definition.

    A definition nothing refers to therefore cites nothing; footnote definitions are left alone.
    """
    targets = {}
    for line in raw:
        match = _DEFINITION.match(line)
        if match:
            targets.setdefault(match.group(1).casefold(), match.group(2))

    def inline(match: re.Match[str]) -> str:
        url = targets.get((match.group(2) or match.group(1)).casefold())
        return f"[{match.group(1)}]({url})" if url else match.group(0)

    return ["" if _DEFINITION.match(line) else _REFERENCE.sub(inline, line) for line in raw]


@dataclass(frozen=True)
class ArticleView:
    raw: tuple[str, ...]
    public: tuple[str, ...]
    links: tuple[ExtractedUrl, ...]
    headings: tuple[Heading, ...]
    units: tuple[Unit, ...]
    title: str | None  # None when the frontmatter cannot be parsed
    faq_keys: frozenset[str]

    @classmethod
    def build(cls, article: str) -> "ArticleView":
        raw = body_lines(article)
        public = public_copy_lines(article)
        headings = []
        for number, line in enumerate(raw, start=1):
            match = _HEADING.match(line)
            if match:
                headings.append(Heading(len(match.group(1)), number, public[number - 1].strip()))
        try:
            title = extract_frontmatter(article).get("title", "")
        except FrontmatterError:
            title = None
        entries = detect_faq_structure(article).entries
        return cls(
            tuple(raw), tuple(public), tuple(extract_urls("\n".join(inline_references(raw)))), tuple(headings),
            tuple(paragraph_units(article)), title, frozenset(question_key(entry.question) for entry in entries),
        )

    @property
    def linked(self) -> frozenset[str]:
        return frozenset(canonical(link.url) for link in self.links)

    def section_headings(self) -> list[str]:
        return [heading.text for heading in self.headings if heading.level in (2, 3)]

    def h1_headings(self) -> list[str]:
        return [heading.text for heading in self.headings if heading.level == 1]

    def lead_text(self) -> str:
        """The first 100 words of body prose: headings, comments, code, and frontmatter are left out."""
        words: list[str] = []
        for line, text in zip(self.raw, self.public):
            if not line.strip() or _HEADING.match(line) or IMAGE_LINE_MARK in text:
                continue
            words += [word for word in text.lstrip(">").split() if any(char.isalnum() for char in word)]
            if len(words) >= LEAD_WORDS:
                break
        return " ".join(words[:LEAD_WORDS])

    def prose(self) -> str:
        """All public text as one normalized string, for verbatim quote lookups."""
        return normalize_passage(" ".join(line.lstrip(">").replace(IMAGE_LINE_MARK, "") for line in self.public))

    def paragraphs_linking(self, url: str) -> list[str]:
        """Public text of each paragraph, list item, or table row that links ``url``."""
        lines = {link.line for link in self.links if canonical(link.url) == url}
        return [" ".join(unit.text) for unit in self.units if any(unit.line <= n <= unit.end_line for n in lines)]
