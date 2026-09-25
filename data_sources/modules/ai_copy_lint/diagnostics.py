"""Finding builders and specialized diagnostics for the AI copy linter."""

from __future__ import annotations

import re
from typing import Pattern

try:
    from data_sources.modules.source_support.instructional_context import (
        instructional_line_numbers,
    )
except ModuleNotFoundError:
    from source_support.instructional_context import (
        instructional_line_numbers,
    )

from .rules import (
    COMPARISON_LABEL_RE,
    FAQ_QUESTION_HEADING_RE,
    LOCKED_TITLE_CASE_EXCEPTIONS,
    SENTENCE_RE,
    TITLE_FRONTMATTER_RE,
    TITLE_PREPOSITIONS,
    WORD_RE,
)
from .scanning import iter_active_lines


Finding = dict[str, object]
INSTRUCTIONAL_IMPERATIVE_RE = re.compile(
    r"^(?:add|apply|check|clarify|compare|confirm|create|define|describe|"
    r"document|draft|ensure|explain|identify|include|list|make|name|note|"
    r"outline|prepare|provide|record|review|revise|select|show|state|"
    r"summarize|update|use|verify|write)\b",
    re.IGNORECASE,
)


def finding(
    rule_id: str,
    severity: str,
    line: int,
    column: int,
    match: str,
    message: str,
    suggestion: str,
    **details: object,
) -> Finding:
    """Build one serializable lint finding."""
    return {
        "rule_id": rule_id,
        "severity": severity,
        "line": line,
        "column": column,
        "match": match,
        "message": message,
        "suggestion": suggestion,
        **details,
    }


def find_pattern(
    rule_id: str,
    severity: str,
    pattern: Pattern[str],
    line_number: int,
    original_line: str,
    masked_line: str,
    message: str,
    suggestion: str,
) -> list[Finding]:
    """Return a finding for every rule-pattern match on one line."""
    return [
        finding(
            rule_id, severity, line_number, match.start() + 1,
            original_line[match.start():match.end()], message, suggestion,
        )
        for match in pattern.finditer(masked_line)
    ]


def find_long_sentences(
    line_number: int,
    original_line: str,
    masked_line: str,
    max_words: int = 30,
) -> list[Finding]:
    """Return findings for sentences that exceed the word limit."""
    findings: list[Finding] = []
    for match in SENTENCE_RE.finditer(masked_line):
        word_count = len(WORD_RE.findall(match.group(0)))
        if word_count > max_words:
            findings.append(finding(
                "long_sentence", "error", line_number, match.start() + 1,
                original_line[match.start():match.end()].strip(),
                f"Sentence is {word_count} words; Simpro copy should stay tighter.",
                "Split the sentence or remove filler.",
            ))
    return findings


def find_repeated_sentence_starts(content: str) -> list[Finding]:
    """Report every repeated two-word opener cluster with all occurrence lines."""
    starts: dict[str, list[tuple[int, int, str]]] = {}
    instructional_lines = instructional_line_numbers(content)

    for line_number, original_line, masked_line in iter_active_lines(content):
        if FAQ_QUESTION_HEADING_RE.match(original_line) or COMPARISON_LABEL_RE.match(original_line):
            continue
        for sentence in SENTENCE_RE.finditer(masked_line):
            words = WORD_RE.findall(sentence.group(0).lower())
            if len(words) >= 2:
                key = " ".join(words[:2])
                starts.setdefault(key, []).append((line_number, sentence.start() + 1, sentence.group(0)))

    findings: list[Finding] = []
    for key, occurrences in starts.items():
        if len(occurrences) < 3:
            continue
        lines = [line_number for line_number, _, _ in occurrences]
        first_line, first_column, first_sentence = occurrences[0]
        severity = _repeated_opener_severity(
            first_sentence,
            lines,
            instructional_lines,
        )
        findings.append(finding(
            "repeated_sentence_start", severity, first_line, first_column, key,
            f"Repeated sentence start '{key}' appears on lines {', '.join(map(str, lines))}.",
            "Vary the sentence opening or combine related ideas.", lines=lines,
        ))
    return findings


def _repeated_opener_severity(
    first_sentence: str,
    lines: list[int],
    instructional_lines: frozenset[int],
) -> str:
    if (
        all(line_number in instructional_lines for line_number in lines)
        and INSTRUCTIONAL_IMPERATIVE_RE.match(
            _normalized_instructional_sentence(first_sentence)
        )
    ):
        return "warning"
    return "error"


def _normalized_instructional_sentence(sentence: str) -> str:
    """Remove leading markdown row or checklist syntax before verb matching."""
    normalized = re.sub(r"^\s*\|\s*", "", sentence)
    return re.sub(r"^\s*(?:[-*+]\s+)?(?:\[[ xX]\]\s+)?", "", normalized)


def find_capitalized_title_prepositions(content: str) -> list[Finding]:
    """Return title-case preposition findings from frontmatter and headings."""
    findings: list[Finding] = []
    in_code_fence = False
    in_frontmatter = False
    for line_number, original_line in enumerate(content.splitlines(), start=1):
        stripped = original_line.strip()
        if line_number == 1 and stripped == "---":
            in_frontmatter = True
            continue
        if stripped.startswith("```"):
            in_code_fence = not in_code_fence
            continue
        if in_code_fence:
            continue
        if in_frontmatter:
            if stripped == "---":
                in_frontmatter = False
                continue
            title_match = TITLE_FRONTMATTER_RE.match(original_line)
            if title_match:
                raw_value = title_match.group(1).strip()
                title_text, offset = strip_wrapping_quotes(raw_value)
                findings.extend(title_preposition_findings(line_number, title_text, title_match.start(1) + 1 + offset))
            continue
        heading_match = re.match(r"^\s{0,3}#{1,6}\s+(.+?)\s*$", original_line)
        if heading_match:
            findings.extend(title_preposition_findings(line_number, heading_match.group(1).strip(), heading_match.start(1) + 1))
    return findings


def strip_wrapping_quotes(value: str) -> tuple[str, int]:
    """Remove matched wrapping quotes and report the resulting offset."""
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
        return value[1:-1], 1
    return value, 0


def title_preposition_findings(line_number: int, title_text: str, column: int) -> list[Finding]:
    """Return findings for uppercase title prepositions outside approved titles."""
    if title_text in LOCKED_TITLE_CASE_EXCEPTIONS:
        return []
    findings: list[Finding] = []
    for match in WORD_RE.finditer(title_text):
        if match.start() == 0 or title_text[:match.start()].rstrip().endswith(":"):
            continue
        word = match.group(0)
        if word in TITLE_PREPOSITIONS:
            findings.append(finding(
                "title_capitalized_preposition", "error", line_number,
                column + match.start(), word,
                "Prepositions in titles must be lowercase in Simpro blog copy.",
                f"Change '{word}' to '{word.lower()}' unless it is part of a proper noun.",
            ))
    return findings
