"""Identify markdown lines that provide reader-facing writing instructions."""

from __future__ import annotations

import re


CHECKLIST_HEADING_RE = re.compile(r"^#{1,6}\s+.*\bchecklist\b", re.IGNORECASE)
HEADING_RE = re.compile(r"^#{1,6}\s+")
INSTRUCTIONAL_VERB_RE = re.compile(
    r"^\s*(?:[-*+]\s+)?(?:\[[ xX]\]\s+)?(?:"
    r"add|clarify|define|describe|draft|explain|identify|include|list|"
    r"make|name|note|outline|show|state|summarize|tell|write)\b",
    re.IGNORECASE,
)


def instructional_line_numbers(content: str) -> frozenset[int]:
    """Return lines whose local markdown context signals writing instruction."""
    lines = content.splitlines()
    table_lines = _what_to_write_table_lines(lines)
    checklist_active = False
    instructional = set(table_lines)

    for line_number, line in enumerate(lines, start=1):
        stripped = line.strip()
        if HEADING_RE.match(stripped):
            checklist_active = bool(CHECKLIST_HEADING_RE.match(stripped))
            continue
        if INSTRUCTIONAL_VERB_RE.match(stripped):
            instructional.add(line_number)
            continue
        if checklist_active and _is_checklist_item(stripped):
            instructional.add(line_number)

    return frozenset(instructional)


def _what_to_write_table_lines(lines: list[str]) -> set[int]:
    table_lines: set[int] = set()
    index = 0
    while index < len(lines):
        if not _is_table_row(lines[index]):
            index += 1
            continue
        start = index
        while index < len(lines) and _is_table_row(lines[index]):
            index += 1
        if "what to write" in lines[start].casefold():
            table_lines.update(range(start + 1, index + 1))
    return table_lines


def _is_table_row(line: str) -> bool:
    stripped = line.strip()
    return stripped.startswith("|") and stripped.endswith("|")


def _is_checklist_item(line: str) -> bool:
    return bool(re.match(r"^(?:[-*+]\s+)?\[[ xX]\]\s+", line))


__all__ = ["instructional_line_numbers"]
