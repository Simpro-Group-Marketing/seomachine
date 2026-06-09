"""
FAQ Proof Guard

Deterministic guardrail for FAQ answers. It does not decide whether a source
semantically proves a claim; it enforces the minimum evidence contract:
every FAQ answer must carry a public proof URL in the answer body or have a
question-specific Source Map / FAQ Proof Map entry with a public URL.
"""

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional


Finding = Dict[str, object]

FAQ_H2_RE = re.compile(r"^##\s+(?:Frequently Asked Questions|FAQ)\s*$", re.IGNORECASE)
H2_RE = re.compile(r"^##\s+")
FAQ_QUESTION_RE = re.compile(r"^###\s+(.+\?)\s*$")
PUBLIC_URL_RE = re.compile(r"https?://[^\s)\]|<>\"']+", re.IGNORECASE)
MARKDOWN_LINK_RE = re.compile(r"\[[^\]]+\]\((https?://[^)]+)\)", re.IGNORECASE)


@dataclass
class FaqAnswer:
    question: str
    heading_line: int
    answer: str


def check_content(content: str) -> List[Finding]:
    """
    Check FAQ answers for linked proof.

    Args:
        content: Markdown article or rewrite content.

    Returns:
        Structured findings for FAQ answers missing linked proof.
    """
    faq_answers = _extract_faq_answers(content)
    if not faq_answers:
        return []

    source_map_lines = _extract_source_map_candidate_lines(content)
    findings: List[Finding] = []

    for faq_answer in faq_answers:
        if _has_public_proof_url(faq_answer.answer):
            continue

        if _source_map_supports_question(source_map_lines, faq_answer.question):
            continue

        findings.append(
            {
                "rule_id": "faq_answer_missing_linked_proof",
                "severity": "error",
                "line": faq_answer.heading_line,
                "column": 1,
                "question": faq_answer.question,
                "message": (
                    "FAQ answer has no linked proof in the answer body and no "
                    "question-specific Source Map / FAQ Proof Map entry with a public URL."
                ),
                "suggestion": (
                    "Add 1 public proof link inside the FAQ answer, or add a Source Map "
                    "entry that names this exact FAQ question and includes the public URL "
                    "supporting the answer. Internal context paths alone do not count."
                ),
            }
        )

    return findings


def check_file(
    path: str,
    fail_on: str = "error",
) -> List[Finding]:
    """
    Check a Markdown file for unsupported FAQ answers.

    Args:
        path: Markdown file path.
        fail_on: Included for CLI/API symmetry.

    Returns:
        Structured findings.
    """
    if fail_on not in {"error", "warning", "none"}:
        raise ValueError("fail_on must be one of: error, warning, none")

    content = Path(path).read_text(encoding="utf-8")
    return check_content(content)


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
    """Count FAQ proof findings by severity."""
    summary = {"error": 0, "warning": 0}
    for finding in findings:
        severity = str(finding["severity"])
        if severity in summary:
            summary[severity] += 1
    return summary


def _extract_faq_answers(content: str) -> List[FaqAnswer]:
    lines = content.splitlines()
    faq_start_index: Optional[int] = None

    for index, line in enumerate(lines):
        if FAQ_H2_RE.match(line.strip()):
            faq_start_index = index + 1
            break

    if faq_start_index is None:
        return []

    faq_end_index = len(lines)
    for index in range(faq_start_index, len(lines)):
        if H2_RE.match(lines[index].strip()):
            faq_end_index = index
            break

    faq_answers: List[FaqAnswer] = []
    question_indexes: List[int] = []
    for index in range(faq_start_index, faq_end_index):
        if FAQ_QUESTION_RE.match(lines[index].strip()):
            question_indexes.append(index)

    for position, question_index in enumerate(question_indexes):
        question_match = FAQ_QUESTION_RE.match(lines[question_index].strip())
        if question_match is None:
            continue

        answer_start = question_index + 1
        answer_end = (
            question_indexes[position + 1]
            if position + 1 < len(question_indexes)
            else faq_end_index
        )
        answer = "\n".join(lines[answer_start:answer_end]).strip()
        faq_answers.append(
            FaqAnswer(
                question=question_match.group(1).strip(),
                heading_line=question_index + 1,
                answer=answer,
            )
        )

    return faq_answers


def _has_public_proof_url(text: str) -> bool:
    return bool(MARKDOWN_LINK_RE.search(text) or PUBLIC_URL_RE.search(text))


def _extract_source_map_candidate_lines(content: str) -> List[str]:
    lines = content.splitlines()
    candidates: List[str] = []
    in_source_section = False

    for line in lines:
        stripped = line.strip()
        lower = stripped.lower()

        if re.match(r"^#{1,3}\s+(?:source map|faq proof map|faq proof)\b", stripped, re.IGNORECASE):
            in_source_section = True
            candidates.append(stripped)
            continue

        if in_source_section and re.match(r"^#{1,3}\s+", stripped):
            in_source_section = False

        if (
            in_source_section
            or "source map" in lower
            or "faq proof" in lower
            or lower.startswith("- faq:")
            or lower.startswith("|")
        ):
            candidates.append(stripped)

    return candidates


def _source_map_supports_question(source_map_lines: List[str], question: str) -> bool:
    normalized_question = _normalize_for_match(question)
    if not normalized_question:
        return False

    for line in source_map_lines:
        if not PUBLIC_URL_RE.search(line):
            continue
        if normalized_question in _normalize_for_match(line):
            return True

    return False


def _normalize_for_match(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()


def _main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Check FAQ answers for linked proof.")
    parser.add_argument("path", help="Markdown file to check")
    parser.add_argument(
        "--fail-on",
        default="error",
        choices=["error", "warning", "none"],
        help="Minimum finding severity that returns exit code 1",
    )
    args = parser.parse_args(argv)

    findings = check_file(args.path, fail_on=args.fail_on)
    payload = {
        "path": args.path,
        "fail_on": args.fail_on,
        "summary": summarize_findings(findings),
        "findings": findings,
    }
    print(json.dumps(payload, indent=2))
    return 1 if should_fail(findings, fail_on=args.fail_on) else 0


if __name__ == "__main__":
    sys.exit(_main())
