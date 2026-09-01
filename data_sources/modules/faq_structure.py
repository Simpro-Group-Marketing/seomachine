"""Shared visible FAQ structure detection for assembly, proof, PAA, and scoring."""

from __future__ import annotations

import re
from dataclasses import dataclass


FAQ_H2_RE = re.compile(
    r"^##\s+(?:"
    r"Pre-picked\s+PAA\s+Questions|"
    r"Frequently\s+Asked\s+Questions(?:(?:\s+(?:about|on|for)\s+|\s*[:\-]\s*).+)?|"
    r"FAQs?(?:(?:\s+(?:about|on|for)\s+|\s*[:\-]\s*).+)?|"
    r"Common(?:\s+.+)?\s+Questions|"
    r"Questions\s+.+\s+Ask|"
    r"Questions\s+and\s+Answers|"
    r"Q\s*&\s*A|"
    r"Your\s+Questions\s+Answered"
    r")\s*$",
    re.IGNORECASE,
)
FAQ_LIKE_H2_RE = re.compile(
    r"^##\s+.*(?:\bFAQs?\b|\bQuestions?\b|\bQ\s*&\s*A\b).*$",
    re.IGNORECASE,
)
H2_RE = re.compile(r"^##\s+")
QUESTION_HEADING_RE = re.compile(r"^#{3,5}\s+(.+?\?)\s*#*\s*$")
DETAILS_QUESTION_RE = re.compile(
    r"<details\b[^>]*>.*?<summary\b[^>]*>\s*(.+?\?)\s*</summary>",
    re.IGNORECASE | re.DOTALL,
)
BOLD_QUESTION_RE = re.compile(r"^\s*\*\*(.+?\?)\*\*\s*$")
FENCE_START_RE = re.compile(r"^\s*(`{3,}|~{3,})")


@dataclass(frozen=True)
class FaqEntry:
    question: str
    answer: str
    line: int
    answer_line: int


@dataclass(frozen=True)
class FaqStructure:
    heading_present: bool
    entries: tuple[FaqEntry, ...]
    unsupported_lines: tuple[int, ...]

    @property
    def visible(self) -> bool:
        return self.heading_present or bool(self.entries) or bool(self.unsupported_lines)


def is_faq_h2(value: str) -> bool:
    return FAQ_H2_RE.match(value.strip()) is not None


def detect_faq_structure(markdown: str) -> FaqStructure:
    """Detect supported heading FAQs and unsupported alternate Q&A markup."""
    visible_markdown = _mask_fenced_blocks(markdown)
    lines = visible_markdown.splitlines()
    in_faq = False
    heading_present = False
    entries: list[FaqEntry] = []
    current_question: str | None = None
    current_line = 0
    answer_lines: list[str] = []
    unsupported_h2_lines: set[int] = set()

    def close_entry() -> None:
        nonlocal current_question, current_line, answer_lines
        if current_question is not None:
            first_visible_offset = next(
                (
                    offset
                    for offset, answer_line in enumerate(answer_lines, start=1)
                    if answer_line.strip()
                ),
                1,
            )
            entries.append(
                FaqEntry(
                    question=current_question,
                    answer="\n".join(answer_lines).strip(),
                    line=current_line,
                    answer_line=current_line + first_visible_offset,
                )
            )
        current_question = None
        current_line = 0
        answer_lines = []

    for line_number, line in enumerate(lines, start=1):
        stripped = line.strip()
        if is_faq_h2(stripped):
            close_entry()
            in_faq = True
            heading_present = True
            continue
        if in_faq and H2_RE.match(stripped):
            close_entry()
            in_faq = False
            if FAQ_LIKE_H2_RE.match(stripped):
                unsupported_h2_lines.add(line_number)
            continue
        if not in_faq and FAQ_LIKE_H2_RE.match(stripped):
            unsupported_h2_lines.add(line_number)
            continue
        if not in_faq:
            continue
        question_match = QUESTION_HEADING_RE.match(stripped)
        if question_match:
            close_entry()
            current_question = question_match.group(1).strip()
            current_line = line_number
            continue
        if current_question is not None:
            answer_lines.append(line)
    close_entry()

    unsupported: set[int] = set(unsupported_h2_lines)
    for match in DETAILS_QUESTION_RE.finditer(visible_markdown):
        unsupported.add(visible_markdown.count("\n", 0, match.start()) + 1)
    for line_number, line in enumerate(lines, start=1):
        stripped = line.strip()
        if BOLD_QUESTION_RE.match(stripped):
            unsupported.add(line_number)
    return FaqStructure(
        heading_present=heading_present,
        entries=tuple(entries),
        unsupported_lines=tuple(sorted(unsupported)),
    )


def _mask_fenced_blocks(markdown: str) -> str:
    """Blank fenced blocks while preserving line numbers for findings."""
    visible_lines: list[str] = []
    fence_character = ""
    fence_length = 0
    for line in markdown.splitlines():
        if fence_character:
            closing = re.match(
                rf"^\s*{re.escape(fence_character)}{{{fence_length},}}\s*$",
                line,
            )
            visible_lines.append("")
            if closing:
                fence_character = ""
                fence_length = 0
            continue

        opening = FENCE_START_RE.match(line)
        if opening:
            token = opening.group(1)
            fence_character = token[0]
            fence_length = len(token)
            visible_lines.append("")
            continue
        visible_lines.append(line)
    return "\n".join(visible_lines)
