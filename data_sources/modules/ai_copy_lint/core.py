"""Public lint orchestration for the AI copy linter."""

from __future__ import annotations

from pathlib import Path

try:
    from ..humanizer_policy import load_policy_regex_rules
except ImportError:
    from humanizer_policy import load_policy_regex_rules

from .diagnostics import (
    Finding,
    finding,
    find_capitalized_title_prepositions,
    find_long_sentences,
    find_pattern,
    find_repeated_sentence_starts,
)
from .rules import (
    APPROVED_MODAL_CAVEAT_LINES,
    COPY_AVOID_RULES,
    ERROR_RULES,
    FAQ_QUESTION_HEADING_RE,
    HOW_CAN_HEADING_RE,
    LOCKED_MODAL_HEADING_EXCEPTIONS,
    MODAL_VERB_TOKEN_RE,
    RHETORICAL_QUESTION,
)
from .scanning import iter_active_lines, mask_humanizer_protected_spans


def copy_avoid_findings(
    rule_id: str,
    severity: str,
    pattern,
    line_number: int,
    original_line: str,
    masked_line: str,
    protected_line: str,
    message: str,
    suggestion: str,
) -> list[Finding]:
    """Return COPY_AVOID findings, downgrading those inside quoted source text.

    These rules describe how Simpro writes, so a verbatim quote from a review
    or interview cannot be edited to satisfy them and must not block a release.
    Suppressing them outright would let any prose clear the linter by being
    wrapped in quotation marks, so a match inside a quoted or blockquoted span
    is reported at warning severity instead of dropped.
    """
    outside = find_pattern(
        rule_id, severity, pattern, line_number, original_line,
        protected_line, message, suggestion,
    )
    unquoted_columns = {item["column"] for item in outside}
    quoted = [
        {
            **item,
            "severity": "warning",
            "suggestion": (
                f"{suggestion} This match is inside quoted source text, so it "
                "does not block release; reword the surrounding copy instead."
            ),
        }
        for item in find_pattern(
            rule_id, severity, pattern, line_number, original_line,
            masked_line, message, suggestion,
        )
        if item["column"] not in unquoted_columns
    ]
    return outside + quoted


def lint_content(content: str, profile: str = "simpro-web") -> list[Finding]:
    """Lint markdown or plain text for AI writing tells and Simpro copy issues."""
    if profile != "simpro-web":
        raise ValueError(f"Unsupported AI copy lint profile: {profile}")

    findings: list[Finding] = []
    humanizer_rules = load_policy_regex_rules()
    for line_number, original_line, masked_line in iter_active_lines(content):
        for rule_id, pattern, message, suggestion in ERROR_RULES:
            findings.extend(find_pattern(
                rule_id, "error", pattern, line_number, original_line,
                masked_line, message, suggestion,
            ))
        protected_line = mask_humanizer_protected_spans(original_line, masked_line)
        for rule_id, severity, pattern, message, suggestion in COPY_AVOID_RULES:
            if should_skip_copy_avoid_rule(rule_id, original_line):
                continue
            findings.extend(copy_avoid_findings(
                rule_id, severity, pattern, line_number, original_line,
                masked_line, protected_line, message, suggestion,
            ))
        match = RHETORICAL_QUESTION.search(masked_line)
        if match:
            findings.append(finding(
                "rhetorical_question", "warning", line_number, match.start() + 1,
                original_line[match.start():match.end()].strip(),
                "Rhetorical setup questions make copy sound formulaic.",
                "Replace the question with a direct statement about the reader's job.",
            ))
        findings.extend(find_long_sentences(line_number, original_line, masked_line))
        for rule in humanizer_rules:
            findings.extend(find_pattern(
                rule.rule_id, rule.severity, rule.pattern, line_number,
                original_line, protected_line, rule.message, rule.suggestion,
            ))

    findings.extend(find_repeated_sentence_starts(content))
    findings.extend(find_capitalized_title_prepositions(content))
    return sorted(findings, key=lambda item: (item["line"], item["column"], item["rule_id"]))


def lint_file(path: str, profile: str = "simpro-web", fail_on: str = "error") -> list[Finding]:
    """Lint a UTF-8 text file and return structured findings."""
    validate_fail_on(fail_on)
    return lint_content(Path(path).read_text(encoding="utf-8"), profile=profile)


def should_fail(findings: list[Finding], fail_on: str = "error") -> bool:
    """Return whether findings meet the configured failure threshold."""
    validate_fail_on(fail_on)
    if fail_on == "none":
        return False
    if fail_on == "warning":
        return any(finding["severity"] in {"warning", "error"} for finding in findings)
    return any(finding["severity"] == "error" for finding in findings)


def summarize_findings(findings: list[Finding]) -> dict[str, int]:
    """Count findings by severity."""
    summary = {"error": 0, "warning": 0}
    for item in findings:
        severity = str(item["severity"])
        if severity in summary:
            summary[severity] += 1
    return summary


def validate_fail_on(fail_on: str) -> None:
    """Validate a public failure threshold argument."""
    if fail_on not in {"error", "warning", "none"}:
        raise ValueError("fail_on must be one of: error, warning, none")


def should_skip_copy_avoid_rule(rule_id: str, original_line: str) -> bool:
    """Preserve explicitly reviewed exceptions to generic copy-avoid rules."""
    disclosure = (
        "This guide is published by AroFlo, a software provider included in this comparison. "
        "We evaluated AroFlo against the same criteria used for every other platform listed. "
        "Product information was reviewed using official vendor documentation and independent "
        "software review sources in August 2026."
    )
    normalized = " ".join(original_line.split())
    if rule_id == "passive_voice" and normalized == disclosure:
        return True
    if rule_id == "modal_verb" and normalized in APPROVED_MODAL_CAVEAT_LINES:
        return True
    if rule_id == "modal_verb" and normalized in LOCKED_MODAL_HEADING_EXCEPTIONS:
        return True
    if rule_id == "modal_verb" and HOW_CAN_HEADING_RE.match(original_line):
        words = MODAL_VERB_TOKEN_RE.findall(original_line)
        if len(words) == 1 and words[0].lower() == "can":
            return True
    return rule_id in {"filler_word", "modal_verb", "passive_voice", "vague_generalization"} and bool(FAQ_QUESTION_HEADING_RE.match(original_line))
