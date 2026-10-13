"""What a finished article offers to the coverage checks: headings, links, title, lead, FAQ questions."""

from __future__ import annotations

import html
import re
from dataclasses import dataclass

from data_sources.modules.artifact_detection import extract_frontmatter
from data_sources.modules.faq_structure import detect_faq_structure
from data_sources.modules.frontmatter import FrontmatterError
from data_sources.modules.production.serp_coverage import _tokens, normalize_heading
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


@dataclass(frozen=True)
class Heading:
    level: int
    line: int
    text: str


def anchor_key(text: str) -> str:
    """Compare anchors ignoring HTML entities, markdown emphasis, punctuation, case, and whitespace."""
    plain = _EMPHASIS.sub("", html.unescape(text)).casefold()
    return " ".join(_NON_WORD.sub(" ", plain).split())


def content_tokens(text: str) -> frozenset[str]:
    """Heading tokens with the shared stopwords removed."""
    return _tokens(text)


def contains_phrase(text: str, phrase: str) -> bool:
    """True when ``phrase`` appears in ``text`` as a contiguous run of normalized tokens."""
    words, wanted = normalize_heading(text).split(), normalize_heading(phrase).split()
    return bool(wanted) and any(words[i : i + len(wanted)] == wanted for i in range(len(words) - len(wanted) + 1))


@dataclass(frozen=True)
class ArticleView:
    raw: tuple[str, ...]
    public: tuple[str, ...]
    links: tuple[ExtractedUrl, ...]
    headings: tuple[Heading, ...]
    units: tuple[Unit, ...]
    title: str
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
            title = ""
        entries = detect_faq_structure(article).entries
        return cls(
            tuple(raw), tuple(public), tuple(extract_urls("\n".join(raw))), tuple(headings),
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
