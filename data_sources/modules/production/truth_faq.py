"""FAQ checks: every question is a BOM PAA question, in the supported heading format."""

from __future__ import annotations

import re
from collections.abc import Sequence

from data_sources.modules.faq_structure import BOLD_QUESTION_RE, FaqStructure, is_faq_h2
from data_sources.modules.production.truth_index import BomIndex, question_key
from data_sources.modules.production.truth_text import Finding

_FORMAT_MESSAGE = "use ### question headings under the FAQ section"
_H2 = re.compile(r"^##\s")
_HEADING = re.compile(r"^\s*#{1,6}\s")
_EMPHASIS = re.compile(r"\*\*|__|\*|_")
_Q_PREFIX = re.compile(r"^(?:q|question)\s*\d*\s*[:.)]\s*", re.IGNORECASE)


def answer_ranges(structure: FaqStructure) -> list[tuple[int, int]]:
    """Line ranges of each FAQ answer, so an answer is checked as one paragraph."""
    return [(entry.answer_line, entry.answer_line + entry.answer.count("\n")) for entry in structure.entries]


def section_range(raw: Sequence[str]) -> tuple[int, int] | None:
    """Return (first, last) line of the FAQ section: from the FAQ H2 to the next H2."""
    start = next((n for n, line in enumerate(raw, start=1) if is_faq_h2(line.strip())), 0)
    if not start:
        return None
    end = next((n for n in range(start + 1, len(raw) + 1) if _H2.match(raw[n - 1].strip())), len(raw) + 1)
    return start, end - 1


def _question_cells(text: str) -> list[str]:
    parts = text.split("|") if "|" in text else [text]
    return [part.strip() for part in parts if part.strip()]


def _looks_like_question(text: str) -> bool:
    for cell in _question_cells(text):
        plain = _EMPHASIS.sub("", cell).strip()
        if _Q_PREFIX.match(plain) or plain.endswith("?"):
            return True
    return False


def _section_question_lines(raw: Sequence[str], public: Sequence[str], section: tuple[int, int]) -> set[int]:
    """Lines inside the FAQ section that read as a question but are not a ### heading."""
    return {
        number for number in range(section[0] + 1, section[1] + 1)
        if raw[number - 1].strip() and not _HEADING.match(raw[number - 1]) and _looks_like_question(public[number - 1])
    }


def faq_findings(
    structure: FaqStructure, raw: Sequence[str], public: Sequence[str], index: BomIndex
) -> list[Finding]:
    section = section_range(raw)
    lines = {
        number for number in structure.unsupported_lines
        if (section and section[0] <= number <= section[1]) or not BOLD_QUESTION_RE.match(raw[number - 1])
    }
    if section:
        lines |= _section_question_lines(raw, public, section)
    findings = [Finding("faq_question", "block", f"{_FORMAT_MESSAGE}: {raw[n - 1].strip()}", n) for n in sorted(lines)]
    findings += [
        Finding("faq_question", "block", f"FAQ question is not a BOM PAA question: {entry.question}", entry.line)
        for entry in structure.entries
        if question_key(entry.question) not in index.questions
    ]
    return findings
