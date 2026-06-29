"""
AI Copy Linter

Deterministic copy-quality gate for AI writing tells and Simpro web-copy rules.
This module detects risky copy patterns; it does not rewrite content.
"""

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional, Pattern, Tuple


Finding = Dict[str, object]


APPROVED_PROPER_NOUNS = [
    "Simpro",
    "Simpro.ai",
    "Simpro Group",
    "Lightning AI",
    "G2",
    "Capterra",
    "Software Advice",
    "GetApp",
    "TrustRadius",
    "Gartner Digital Markets",
    "Gartner",
    "Trustpilot",
    "Google reviews",
]


BECAUSE_RE = re.compile(r"\bbecause\b", re.IGNORECASE)
FAQ_QUESTION_HEADING_RE = re.compile(r"^\s{0,3}#{2,6}\s+.+\?\s*$")


ERROR_RULES: List[Tuple[str, Pattern[str], str, str]] = [
    (
        "em_dash",
        re.compile(r"\u2014"),
        "Em dashes are not allowed in Simpro web copy.",
        "Replace with a comma, period, colon, or parentheses.",
    ),
    (
        "semicolon",
        re.compile(r";"),
        "Semicolons are not allowed in Simpro web copy.",
        "Split the sentence or use a comma or period.",
    ),
    (
        "hashtag",
        re.compile(r"(?<![#\w])#[A-Za-z][A-Za-z0-9_-]*"),
        "Hashtags are not allowed in final copy.",
        "Remove the hashtag or rewrite it as plain text if needed.",
    ),
    (
        "not_just_but_also",
        re.compile(r"\bnot\s+just\b.{0,100}\bbut\s+also\b", re.IGNORECASE),
        "Avoid the formulaic 'not just X, but also Y' construction.",
        "State the stronger point directly.",
    ),
    (
        "setup_phrase",
        re.compile(
            r"\b(?:in conclusion|in closing|in summary|to summarize|to sum up|"
            r"without further ado|all things considered|at the end of the day)\b,?",
            re.IGNORECASE,
        ),
        "Avoid generic setup or closing language.",
        "Delete the setup phrase and lead with the point.",
    ),
    (
        "ai_phrase",
        re.compile(
            r"\b(?:in today's|in a world where|imagine a world where|shed light|"
            r"dive deep|delve|embark|glimpse into|navigating the landscape|"
            r"ever-evolving|not alone|pave the way|a myriad of|a plethora of)\b",
            re.IGNORECASE,
        ),
        "This phrase is a common AI-writing tell.",
        "Use clear, direct language.",
    ),
    (
        "unsupported_hype",
        re.compile(
            r"\b(?:game[- ]changer|revolutionize|disruptive|skyrocket|"
            r"groundbreaking|cutting-edge|remarkable|pivotal|intricate|"
            r"tapestry|abyss|illuminate|unveil|elucidate|harness|utilize|"
            r"utilizing|unlock|discover|boost|powerful)\b",
            re.IGNORECASE,
        ),
        "Avoid hype terms unless a brief explicitly approves the claim.",
        "Use a specific outcome, metric, or feature instead.",
    ),
    (
        "internal_process_language",
        re.compile(
            r"\b(?:repo context|repository context|approved internal proof path|"
            r"rewrite can route readers|PAA artifact|change summary|source map|"
            r"confirmed WordPress author|WordPress author before publish|schema notes)\b|"
            r"\bcontext/(?:features|internal-links-map|target-keywords|brand-voice|"
            r"aeo-geo-blog-strategy|writing-examples|style-guide)\.md\b",
            re.IGNORECASE,
        ),
        "Internal workflow or repo-context language is not allowed in public blog copy.",
        "Use context files only to guide writing. Cite public URLs or remove the internal note.",
    ),
    (
        "source_meta_commentary",
        re.compile(
            r"\b(?:this|that|the)\s+"
            r"(?:case study|source|statistic|stat|example|proof point|article|blog|section)\s+"
            r"(?:is|are|was|were)\s+"
            r"(?:useful|helpful|relevant|important|good|strong|appropriate)\s+"
            r"for\s+(?:this|the)\s+"
            r"(?:topic|article|blog|post|section|rewrite|draft)\b|"
            r"\b(?:this|that|the)\s+"
            r"(?:case study|source|statistic|stat|example|proof point|article|blog|section)\s+"
            r"(?:belongs|fits|works)\s+(?:in|for)\s+(?:this|the)\s+"
            r"(?:topic|article|blog|post|section|rewrite|draft)\b",
            re.IGNORECASE,
        ),
        "Public blog copy must not explain why a source or proof point is useful for the draft.",
        "Translate the source into an audience-facing takeaway, outcome, or workflow lesson.",
    ),
    (
        "named_fictional_scenario",
        re.compile(
            r"\b(?:Picture|Imagine|Meet)\s+"
            r"(?:Marissa|Sarah|Mike|Marcus|Lisa|John|David|Emily|Chris|Alex|"
            r"Tom|Anna|James|Maria|Rachel|Dan|Kate)\b"
            r"(?=\s*(?:,|\.|\bwho\b|\btrying\b|\bas\b|\ban?\b|\bthe\b))|"
            r"\b(?:Marissa|Sarah|Mike|Marcus|Lisa|John|David|Emily|Chris|Alex|"
            r"Tom|Anna|James|Maria|Rachel|Dan|Kate)\s*,\s+"
            r"(?:an?|the)\s+"
            r"(?:operations manager|office manager|contractor|estimator|"
            r"technician|coordinator|dispatcher|business owner|project manager)\b",
            re.IGNORECASE,
        ),
        "Named fictional scenarios are not allowed in proof-sensitive blog copy.",
        (
            "Use an unnamed workflow example, or use an actual customer/review POV "
            "with proof in the validation sidecar."
        ),
    ),
]


WARNING_RULES: List[Tuple[str, Pattern[str], str, str]] = [
    (
        "modal_verb",
        re.compile(r"\b(?:can|may|could|should|might)\b", re.IGNORECASE),
        "Modal verbs weaken copy and often hide uncertainty.",
        "Use a direct verb when the claim is supported.",
    ),
    (
        "filler_word",
        re.compile(
            r"\b(?:just|very|really|literally|actually|certainly|probably|"
            r"basically|maybe|hence|furthermore|moreover|however|"
            r"additionally|ultimately|essentially|clearly|obviously|quite)\b",
            re.IGNORECASE,
        ),
        "This filler word often adds no useful meaning.",
        "Delete it or replace it with a specific detail.",
    ),
    (
        "passive_voice",
        re.compile(
            r"\b(?:is|are|was|were|be|been|being)\s+"
            r"(?:\w+ed|known|made|built|driven|given|taken|seen|done|set|run)\b",
            re.IGNORECASE,
        ),
        "Passive voice weakens the sentence.",
        "Rewrite with a clear actor and active verb.",
    ),
    (
        "vague_generalization",
        re.compile(
            r"\b(?:many|some|various|numerous|several|often|usually|typically|"
            r"generally|a lot of|things|stuff|businesses today|teams today)\b",
            re.IGNORECASE,
        ),
        "Vague language needs proof or a concrete example.",
        "Use a number, named scenario, or specific operational detail.",
    ),
]


RHETORICAL_QUESTION = re.compile(
    r"^\s*(?:are you|do you|have you|ever wondered|what if|want to|looking for)\b.*\?",
    re.IGNORECASE,
)

SENTENCE_RE = re.compile(r"[^.!?]+[.!?]")
URL_RE = re.compile(r"https?://\S+|www\.\S+")
MARKDOWN_LINK_RE = re.compile(r"\[[^\]]+\]\([^\)]*\)")
INLINE_CODE_RE = re.compile(r"`[^`]*`")
WORD_RE = re.compile(r"\b[A-Za-z][A-Za-z']*\b")
TITLE_FRONTMATTER_RE = re.compile(r"^\s*(?:title|meta_title)\s*:\s*(.+?)\s*$", re.IGNORECASE)
TITLE_PREPOSITIONS = {
    "About",
    "Above",
    "Across",
    "After",
    "Against",
    "Along",
    "Among",
    "Around",
    "As",
    "At",
    "Before",
    "Behind",
    "Below",
    "Beneath",
    "Beside",
    "Between",
    "Beyond",
    "By",
    "Despite",
    "Down",
    "During",
    "For",
    "From",
    "In",
    "Inside",
    "Into",
    "Like",
    "Near",
    "Of",
    "Off",
    "On",
    "Onto",
    "Out",
    "Over",
    "Past",
    "Per",
    "Since",
    "Through",
    "Throughout",
    "To",
    "Toward",
    "Towards",
    "Under",
    "Until",
    "Up",
    "Upon",
    "Via",
    "With",
    "Within",
    "Without",
}


def lint_content(content: str, profile: str = "simpro-web") -> List[Finding]:
    """
    Lint content for AI writing tells and Simpro web-copy issues.

    Args:
        content: Markdown or plain text to check.
        profile: Lint profile. Only "simpro-web" is supported.

    Returns:
        List of structured findings.
    """
    if profile != "simpro-web":
        raise ValueError(f"Unsupported AI copy lint profile: {profile}")

    findings: List[Finding] = []
    active_lines = _iter_active_lines(content)

    for line_number, original_line, masked_line in active_lines:
        for rule_id, pattern, message, suggestion in ERROR_RULES:
            findings.extend(
                _find_pattern(
                    rule_id,
                    "error",
                    pattern,
                    line_number,
                    original_line,
                    masked_line,
                    message,
                    suggestion,
                )
            )

        for rule_id, pattern, message, suggestion in WARNING_RULES:
            if _should_skip_copy_avoid_rule(rule_id, original_line):
                continue
            findings.extend(
                _find_pattern(
                    rule_id,
                    "error",
                    pattern,
                    line_number,
                    original_line,
                    masked_line,
                    message,
                    suggestion,
                )
            )

        match = RHETORICAL_QUESTION.search(masked_line)
        if match:
            findings.append(
                _finding(
                    "rhetorical_question",
                    "warning",
                    line_number,
                    match.start() + 1,
                    original_line[match.start():match.end()].strip(),
                    "Rhetorical setup questions make copy sound formulaic.",
                    "Replace the question with a direct statement about the reader's job.",
                )
            )

        findings.extend(_find_missing_comma_before_because(line_number, original_line, masked_line))
        findings.extend(_find_long_sentences(line_number, original_line, masked_line))

    findings.extend(_find_multiple_links_in_paragraph(content))
    findings.extend(_find_repeated_sentence_starts(content))
    findings.extend(_find_capitalized_title_prepositions(content))
    return sorted(findings, key=lambda item: (item["line"], item["column"], item["rule_id"]))


def _should_skip_copy_avoid_rule(rule_id: str, original_line: str) -> bool:
    if (
        rule_id in {"filler_word", "modal_verb", "passive_voice", "vague_generalization"}
        and FAQ_QUESTION_HEADING_RE.match(original_line)
    ):
        return True
    return False


def lint_file(
    path: str,
    profile: str = "simpro-web",
    fail_on: str = "error",
) -> List[Finding]:
    """
    Lint a file and return structured findings.

    Args:
        path: File path to lint.
        profile: Lint profile.
        fail_on: Included for CLI/API symmetry. Does not change returned findings.

    Returns:
        List of structured findings.
    """
    if fail_on not in {"error", "warning", "none"}:
        raise ValueError("fail_on must be one of: error, warning, none")

    content = Path(path).read_text(encoding="utf-8")
    return lint_content(content, profile=profile)


def should_fail(findings: List[Finding], fail_on: str = "error") -> bool:
    """Return True when findings meet the configured failure threshold."""
    if fail_on == "none":
        return False
    if fail_on == "warning":
        return any(finding["severity"] in {"warning", "error"} for finding in findings)
    if fail_on == "error":
        return any(finding["severity"] == "error" for finding in findings)
    raise ValueError("fail_on must be one of: error, warning, none")


def summarize_findings(findings: List[Finding]) -> Dict[str, int]:
    """Count findings by severity."""
    summary = {"error": 0, "warning": 0}
    for finding in findings:
        severity = str(finding["severity"])
        if severity in summary:
            summary[severity] += 1
    return summary


def _iter_active_lines(content: str) -> List[Tuple[int, str, str]]:
    lines = content.splitlines()
    active: List[Tuple[int, str, str]] = []
    in_code_fence = False
    in_frontmatter = False

    for index, line in enumerate(lines, start=1):
        stripped = line.strip()

        if index == 1 and stripped == "---":
            in_frontmatter = True
            continue

        if in_frontmatter:
            if stripped == "---":
                in_frontmatter = False
            continue

        if stripped.startswith("```"):
            in_code_fence = not in_code_fence
            continue

        if in_code_fence:
            continue

        active.append((index, line, _mask_ignored_spans(line)))

    return active


def _mask_ignored_spans(line: str) -> str:
    masked = line
    for pattern in (MARKDOWN_LINK_RE, URL_RE, INLINE_CODE_RE):
        masked = _mask_matches(masked, pattern)
    for noun in APPROVED_PROPER_NOUNS:
        masked = re.sub(
            re.escape(noun),
            lambda match: " " * (match.end() - match.start()),
            masked,
            flags=re.IGNORECASE,
        )
    return masked


def _mask_matches(text: str, pattern: Pattern[str]) -> str:
    return pattern.sub(lambda match: " " * (match.end() - match.start()), text)


def _find_pattern(
    rule_id: str,
    severity: str,
    pattern: Pattern[str],
    line_number: int,
    original_line: str,
    masked_line: str,
    message: str,
    suggestion: str,
) -> List[Finding]:
    findings: List[Finding] = []
    for match in pattern.finditer(masked_line):
        findings.append(
            _finding(
                rule_id,
                severity,
                line_number,
                match.start() + 1,
                original_line[match.start():match.end()],
                message,
                suggestion,
            )
        )
    return findings


def _find_long_sentences(
    line_number: int,
    original_line: str,
    masked_line: str,
    max_words: int = 30,
) -> List[Finding]:
    findings: List[Finding] = []
    for match in SENTENCE_RE.finditer(masked_line):
        word_count = len(WORD_RE.findall(match.group(0)))
        if word_count > max_words:
            findings.append(
                _finding(
                    "long_sentence",
                    "error",
                    line_number,
                    match.start() + 1,
                    original_line[match.start():match.end()].strip(),
                    f"Sentence is {word_count} words; Simpro copy should stay tighter.",
                    "Split the sentence or remove filler.",
                )
            )
    return findings


def _find_missing_comma_before_because(
    line_number: int,
    original_line: str,
    masked_line: str,
) -> List[Finding]:
    findings: List[Finding] = []

    for match in BECAUSE_RE.finditer(masked_line):
        prefix = masked_line[: match.start()].rstrip()
        if prefix.endswith(","):
            continue
        findings.append(
            _finding(
                "missing_comma_before_because",
                "error",
                line_number,
                match.start() + 1,
                original_line[match.start():match.end()],
                "Use a comma before because in Simpro web copy.",
                "Add a comma before because or rewrite the sentence.",
            )
        )

    return findings


def _find_multiple_links_in_paragraph(content: str) -> List[Finding]:
    findings: List[Finding] = []
    paragraph_lines: List[Tuple[int, str]] = []
    paragraph_start_line = 0

    def flush_paragraph() -> None:
        nonlocal paragraph_lines, paragraph_start_line
        if not paragraph_lines:
            return

        paragraph = " ".join(line for _, line in paragraph_lines)
        markdown_link_count = len(MARKDOWN_LINK_RE.findall(paragraph))
        paragraph_without_markdown_links = MARKDOWN_LINK_RE.sub("", paragraph)
        bare_url_count = len(URL_RE.findall(paragraph_without_markdown_links))
        link_count = markdown_link_count + bare_url_count

        if link_count > 1:
            findings.append(
                _finding(
                    "multiple_links_in_paragraph",
                    "error",
                    paragraph_start_line,
                    1,
                    f"{link_count} links in paragraph",
                    "Only 1 link per paragraph is allowed in Simpro web copy.",
                    "Move the second link to a separate paragraph or remove it.",
                )
            )

        paragraph_lines = []
        paragraph_start_line = 0

    for line_number, original_line, _ in _iter_active_lines(content):
        stripped = original_line.strip()
        if not stripped:
            flush_paragraph()
            continue

        if _is_non_prose_block_line(stripped):
            flush_paragraph()
            continue

        if not paragraph_lines:
            paragraph_start_line = line_number
        paragraph_lines.append((line_number, original_line))

    flush_paragraph()
    return findings


def _is_non_prose_block_line(stripped: str) -> bool:
    return (
        stripped.startswith("#")
        or stripped.startswith(">")
        or stripped.startswith("|")
        or stripped.startswith("<!--")
        or re.match(r"^(?:[-*+]|\d+\.)\s+", stripped) is not None
    )


def _find_repeated_sentence_starts(content: str) -> List[Finding]:
    starts: Dict[str, List[Tuple[int, int, str]]] = {}
    active_lines = _iter_active_lines(content)

    for line_number, original_line, masked_line in active_lines:
        for sentence in SENTENCE_RE.finditer(masked_line):
            words = WORD_RE.findall(sentence.group(0).lower())
            if len(words) < 2:
                continue
            key = " ".join(words[:2])
            starts.setdefault(key, []).append((line_number, sentence.start() + 1, original_line))

    findings: List[Finding] = []
    for key, occurrences in starts.items():
        if len(occurrences) >= 3:
            line_number, column, _ = occurrences[2]
            findings.append(
                _finding(
                    "repeated_sentence_start",
                    "error",
                    line_number,
                    column,
                    key,
                    "Repeated sentence starts make copy sound generated.",
                    "Vary the sentence opening or combine related ideas.",
                )
            )
    return findings


def _find_capitalized_title_prepositions(content: str) -> List[Finding]:
    findings: List[Finding] = []
    in_code_fence = False
    in_frontmatter = False

    for line_number, original_line in enumerate(content.splitlines(), start=1):
        stripped = original_line.strip()

        if index_is_frontmatter_start(line_number, stripped):
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
                title_text, offset_in_raw = _strip_wrapping_quotes(raw_value)
                title_start_column = title_match.start(1) + 1 + offset_in_raw
                findings.extend(
                    _title_preposition_findings(
                        line_number,
                        original_line,
                        title_text,
                        title_start_column,
                    )
                )
            continue

        heading_match = re.match(r"^\s{0,3}#{1,6}\s+(.+?)\s*$", original_line)
        if heading_match:
            title_text = heading_match.group(1).strip()
            title_start_column = heading_match.start(1) + 1
            findings.extend(
                _title_preposition_findings(
                    line_number,
                    original_line,
                    title_text,
                    title_start_column,
                )
            )

    return findings


def index_is_frontmatter_start(line_number: int, stripped: str) -> bool:
    return line_number == 1 and stripped == "---"


def _strip_wrapping_quotes(value: str) -> Tuple[str, int]:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
        return value[1:-1], 1
    return value, 0


def _title_preposition_findings(
    line_number: int,
    original_line: str,
    title_text: str,
    title_start_column: int,
) -> List[Finding]:
    findings: List[Finding] = []

    for match in WORD_RE.finditer(title_text):
        word = match.group(0)
        if word not in TITLE_PREPOSITIONS:
            continue
        findings.append(
            _finding(
                "title_capitalized_preposition",
                "error",
                line_number,
                title_start_column + match.start(),
                word,
                "Prepositions in titles must be lowercase in Simpro blog copy.",
                f"Change '{word}' to '{word.lower()}' unless it is part of a proper noun.",
            )
        )

    return findings


def _finding(
    rule_id: str,
    severity: str,
    line: int,
    column: int,
    match: str,
    message: str,
    suggestion: str,
) -> Finding:
    return {
        "rule_id": rule_id,
        "severity": severity,
        "line": line,
        "column": column,
        "match": match,
        "message": message,
        "suggestion": suggestion,
    }


def _main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Lint content for AI copy tells.")
    parser.add_argument("path", help="Markdown or text file to lint")
    parser.add_argument("--profile", default="simpro-web", help="Lint profile")
    parser.add_argument(
        "--fail-on",
        default="error",
        choices=["error", "warning", "none"],
        help="Minimum finding severity that returns exit code 1",
    )
    args = parser.parse_args(argv)

    findings = lint_file(args.path, profile=args.profile, fail_on=args.fail_on)
    payload = {
        "path": args.path,
        "profile": args.profile,
        "fail_on": args.fail_on,
        "summary": summarize_findings(findings),
        "findings": findings,
    }
    print(json.dumps(payload, indent=2))
    return 1 if should_fail(findings, fail_on=args.fail_on) else 0


if __name__ == "__main__":
    sys.exit(_main())
