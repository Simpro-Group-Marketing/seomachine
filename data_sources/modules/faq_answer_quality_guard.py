"""
FAQ Answer Quality Guard

Deterministic guardrail for answer-first FAQs. It checks the opening of each
FAQ answer and blocks missing answers, generic deflections and bare binary
responses. Evidence remains the responsibility of faq_proof_guard.py.
"""

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

try:
    from .guard_common import Finding, should_fail, summarize_findings
except ImportError:  # pragma: no cover - supports direct script execution.
    from guard_common import Finding, should_fail, summarize_findings


FAQ_H2_RE = re.compile(r"^##\s+(?:Frequently Asked Questions|FAQ)\s*$", re.IGNORECASE)
H2_RE = re.compile(r"^##\s+")
FAQ_QUESTION_RE = re.compile(r"^###\s+(.+\?)\s*$")
YES_NO_QUESTION_RE = re.compile(
    r"^(?:is|are|was|were|do|does|did|can|could|should|would|will|"
    r"has|have|had|may|must)\b",
    re.IGNORECASE,
)
BARE_BINARY_RE = re.compile(r"^(?:yes|no)[.!]?$", re.IGNORECASE)

GENERIC_OPENER_PATTERNS = (
    re.compile(r"^(?:there\s+(?:is|are)|there['’]s)\s+no\b", re.IGNORECASE),
    re.compile(
        r"^no\s+(?:single|universal|one-size-fits-all|one size fits all)\b",
        re.IGNORECASE,
    ),
    re.compile(r"^(?:it|this|that|the answer)\s+depends\b", re.IGNORECASE),
    re.compile(r"^[^.!?]{0,100}\bdepends\s+on\b", re.IGNORECASE),
    re.compile(r"^[^.!?]{0,100}\bvar(?:y|ies)\s+by\b", re.IGNORECASE),
    re.compile(
        r"^(?:we|you|no one)\s+(?:do not|don't|cannot|can't)\s+know\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"^(?:it\s+(?:is|remains)|the answer is)\s+"
        r"(?:unclear|unknown|not known)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"^there\s+(?:is|are)\s+(?:not enough|insufficient|limited)\s+"
        r"(?:data|evidence|information)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"^it\s+(?:is|['’]s)\s+(?:not possible|impossible)\s+to\s+"
        r"(?:say|determine)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"^no\s+(?:(?:official|bls)\s+)?source\s+"
        r"(?:ranks?|identifies?|names?)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"^[^.!?]{1,80}\balone\s+(?:does not|doesn't|cannot|can't)\s+"
        r"(?:determine|decide|show|make)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"^every\s+(?:business|company|job|situation|team)\s+is\s+different\b",
        re.IGNORECASE,
    ),
)


@dataclass(frozen=True)
class FaqAnswer:
    question: str
    heading_line: int
    answer_line: int
    answer: str


def check_content(content: str) -> List[Finding]:
    """Check FAQ answers for extractable, answer-first openings."""
    findings: List[Finding] = []

    for faq_answer in _extract_faq_answers(content):
        first_paragraph = _first_visible_paragraph(faq_answer.answer)
        plain_paragraph = _plain_text(first_paragraph)

        if not plain_paragraph:
            findings.append(
                _finding(
                    faq_answer,
                    "faq_answer_missing",
                    "FAQ question has no visible answer paragraph.",
                )
            )
            continue

        sentences = _sentences(plain_paragraph)
        first_sentence = sentences[0] if sentences else plain_paragraph
        generic_match = _generic_opener_match(first_sentence)
        if generic_match is not None:
            finding = _finding(
                faq_answer,
                "faq_answer_generic_opener",
                (
                    "FAQ answer opens with a generic deflection instead of a "
                    "concrete, extractable answer."
                ),
            )
            finding["matched_text"] = generic_match.group(0)
            findings.append(finding)
            continue

        if BARE_BINARY_RE.fullmatch(first_sentence.strip()):
            has_supported_binary_followup = (
                YES_NO_QUESTION_RE.match(faq_answer.question) is not None
                and len(sentences) > 1
                and _substantive_word_count(sentences[1]) >= 5
                and _generic_opener_match(sentences[1]) is None
            )
            if not has_supported_binary_followup:
                findings.append(
                    _finding(
                        faq_answer,
                        "faq_answer_bare_binary",
                        (
                            "FAQ answer gives a bare yes/no response without an "
                            "immediate substantive explanation."
                        ),
                    )
                )

    return findings


def check_file(
    path: str,
    fail_on: str = "error",
    proof_sidecar: Optional[str] = None,
) -> List[Finding]:
    """
    Check a Markdown file for generic FAQ answers.

    proof_sidecar is accepted for publish-readiness interface symmetry. It
    cannot exempt an article from the answer-quality rule.
    """
    if fail_on not in {"error", "warning", "none"}:
        raise ValueError("fail_on must be one of: error, warning, none")

    del proof_sidecar
    content = Path(path).read_text(encoding="utf-8")
    return check_content(content)


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

    question_indexes = [
        index
        for index in range(faq_start_index, faq_end_index)
        if FAQ_QUESTION_RE.match(lines[index].strip())
    ]
    answers: List[FaqAnswer] = []

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
        answer_lines = lines[answer_start:answer_end]
        first_visible_offset = next(
            (
                offset
                for offset, line in enumerate(answer_lines)
                if line.strip()
            ),
            0,
        )
        answers.append(
            FaqAnswer(
                question=question_match.group(1).strip(),
                heading_line=question_index + 1,
                answer_line=answer_start + first_visible_offset + 1,
                answer="\n".join(answer_lines).strip(),
            )
        )

    return answers


def _first_visible_paragraph(answer: str) -> str:
    paragraph_lines: List[str] = []
    started = False

    for line in answer.splitlines():
        stripped = line.strip()
        if not stripped:
            if started:
                break
            continue
        started = True
        paragraph_lines.append(stripped)

    return " ".join(paragraph_lines)


def _plain_text(markdown: str) -> str:
    text = re.sub(r"!\[[^\]]*\]\([^)]+\)", "", markdown)
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    text = re.sub(r"<https?://[^>]+>", "", text)
    text = re.sub(r"https?://\S+", "", text)
    text = re.sub(r"[`*_~>#]", "", text)
    return re.sub(r"\s+", " ", text).strip()


def _sentences(text: str) -> List[str]:
    return [
        sentence.strip()
        for sentence in re.split(r"(?<=[.!?])\s+", text)
        if sentence.strip()
    ]


def _generic_opener_match(sentence: str) -> Optional[re.Match[str]]:
    for pattern in GENERIC_OPENER_PATTERNS:
        match = pattern.search(sentence)
        if match is not None:
            return match
    return None


def _substantive_word_count(text: str) -> int:
    return len(re.findall(r"\b[\w'-]+\b", text))


def _finding(faq_answer: FaqAnswer, rule_id: str, message: str) -> Finding:
    return {
        "rule_id": rule_id,
        "severity": "error",
        "line": faq_answer.answer_line,
        "column": 1,
        "question": faq_answer.question,
        "message": message,
        "suggestion": (
            "Lead with a supported number or range, named recommendation, "
            "definition, concrete action, or explained yes/no answer. Move "
            "limitations after the direct answer and map its evidence through "
            "the FAQ Proof gate."
        ),
    }


def _main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Check FAQs for answer-first, extractable openings."
    )
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
