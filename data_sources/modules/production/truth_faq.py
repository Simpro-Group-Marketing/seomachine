"""FAQ checks: every question is a BOM PAA question, in the supported heading format."""

from __future__ import annotations

import re
from collections.abc import Sequence

from data_sources.modules.faq_structure import BOLD_QUESTION_RE, FaqStructure, is_faq_h2
from data_sources.modules.production.truth_index import BomIndex, question_key
from data_sources.modules.production.truth_text import Finding

_FORMAT_MESSAGE = "use ### question headings under the FAQ section"
_HEADING = re.compile(r"^\s*#{1,6}\s")
_HEADING_LEVEL = re.compile(r"^\s*(#{1,6})\s")
_FAQ_HEADING = re.compile(r"^(#{2,4})\s+(?:FAQs?|Frequently\s+asked\s+questions)\s*:?\s*$", re.IGNORECASE)
_EMPHASIS = re.compile(r"\*\*|__|\*|_")
_Q_PREFIX = re.compile(r"^(?:q|question)\s*\d*\s*[:.)]\s*", re.IGNORECASE)
_QUESTION_MARKS = "?？"


def answer_ranges(structure: FaqStructure) -> list[tuple[int, int]]:
    """Line ranges of each FAQ answer, so an answer is checked as one paragraph."""
    return [(entry.answer_line, entry.answer_line + entry.answer.count("\n")) for entry in structure.entries]


def _faq_level(text: str) -> int:
    """Heading level of a FAQ heading (## FAQ, ### FAQ, #### FAQ, or a full FAQ H2), else 0."""
    match = _FAQ_HEADING.match(text)
    if match:
        return len(match.group(1))
    return 2 if is_faq_h2(text) else 0


def _heading_level(line: str) -> int:
    match = _HEADING_LEVEL.match(line)
    return len(match.group(1)) if match else 0


def section_ranges(raw: Sequence[str]) -> list[tuple[int, int]]:
    """Return (first, last) lines of each FAQ section: its heading to the next heading of that level or higher."""
    ranges: list[tuple[int, int]] = []
    number = 1
    while number <= len(raw):
        level = _faq_level(raw[number - 1].strip())
        if not level:
            number += 1
            continue
        end = next(
            (later for later in range(number + 1, len(raw) + 1) if 0 < _heading_level(raw[later - 1]) <= level),
            len(raw) + 1,
        ) - 1
        ranges.append((number, end))
        number = end + 1
    return ranges


def _ends_with_question(plain: str) -> bool:
    """True when the text ends in "?" once closing punctuation, quotes, brackets, and emoji are dropped."""
    stripped = plain.rstrip()
    while stripped and not stripped[-1].isalnum() and stripped[-1] not in _QUESTION_MARKS:
        stripped = stripped[:-1]
    return stripped[-1:] in tuple(_QUESTION_MARKS)


def _looks_like_question(text: str) -> bool:
    parts = text.split("|") if "|" in text else [text]
    for cell in (part.strip() for part in parts if part.strip()):
        plain = _EMPHASIS.sub("", cell).strip()
        if _Q_PREFIX.match(plain) or _ends_with_question(plain):
            return True
    return False


def _section_question_lines(
    raw: Sequence[str], public: Sequence[str], sections: Sequence[tuple[int, int]]
) -> set[int]:
    """Lines inside a FAQ section that read as a question but are not a heading."""
    return {
        number for first, last in sections for number in range(first + 1, last + 1)
        if raw[number - 1].strip() and not _HEADING.match(raw[number - 1]) and _looks_like_question(public[number - 1])
    }


def faq_findings(
    structure: FaqStructure, raw: Sequence[str], public: Sequence[str], index: BomIndex
) -> list[Finding]:
    sections = section_ranges(raw)
    lines = {
        number for number in structure.unsupported_lines
        if any(first <= number <= last for first, last in sections) or not BOLD_QUESTION_RE.match(raw[number - 1])
    }
    lines |= _section_question_lines(raw, public, sections)
    findings = [Finding("faq_question", "block", f"{_FORMAT_MESSAGE}: {raw[n - 1].strip()}", n) for n in sorted(lines)]
    findings += [
        Finding("faq_question", "block", f"FAQ question is not a BOM PAA question: {entry.question}", entry.line)
        for entry in structure.entries
        if question_key(entry.question) not in index.questions
    ]
    return findings
