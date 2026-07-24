"""
FAQ Proof Guard

Deterministic guardrail for FAQ answers. It does not decide whether a source
semantically proves a claim; it enforces the minimum evidence contract:
every FAQ answer must carry a non-owned public proof URL in the visible answer
body. A Source Map or FAQ Proof Map can document evidence, but it cannot replace
the reader-facing link.
"""

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional
from urllib.parse import urlparse

try:
    from .guard_common import Finding, should_fail, summarize_findings
except ImportError:  # pragma: no cover - supports direct script execution.
    from guard_common import Finding, should_fail, summarize_findings


FAQ_H2_RE = re.compile(r"^##\s+(?:Frequently Asked Questions|FAQ)\s*$", re.IGNORECASE)
H2_RE = re.compile(r"^##\s+")
FAQ_QUESTION_RE = re.compile(r"^###\s+(.+\?)\s*$")
PUBLIC_URL_RE = re.compile(r"https?://[^\s)\]|<>\"']+", re.IGNORECASE)
MARKDOWN_LINK_RE = re.compile(r"\[[^\]]+\]\((https?://[^)]+)\)", re.IGNORECASE)
OWNED_PROOF_DOMAINS = (
    "simprogroup.com",
    "simpro.com",
    "bigchange.com",
    "clockshark.com",
    "aroflo.com",
)


@dataclass
class FaqAnswer:
    question: str
    heading_line: int
    answer: str


def check_content(
    content: str,
    proof_content: Optional[str] = None,
) -> List[Finding]:
    """
    Check FAQ answers for linked proof.

    Args:
        content: Markdown article or rewrite content.
        proof_content: Accepted for API compatibility. Sidecar evidence cannot
            replace the required inline public evidence link.

    Returns:
        Structured findings for FAQ answers missing linked proof.
    """
    faq_answers = _extract_faq_answers(content)
    if not faq_answers:
        return []

    del proof_content
    findings: List[Finding] = []

    for faq_answer in faq_answers:
        if _has_non_owned_public_proof_url(faq_answer.answer):
            continue

        findings.append(
            {
                "rule_id": "faq_answer_missing_inline_proof",
                "severity": "error",
                "line": faq_answer.heading_line,
                "column": 1,
                "question": faq_answer.question,
                "message": (
                    "FAQ answer has no non-owned public evidence link in its "
                    "visible answer body."
                ),
                "suggestion": (
                    "Add 1 authoritative public evidence link inside the FAQ answer. "
                    "A Source Map or FAQ Proof Map may document the same evidence, "
                    "but sidecar-only proof and owned product links do not count."
                ),
            }
        )

    return findings


def check_file(
    path: str,
    fail_on: str = "error",
    proof_sidecar: Optional[str] = None,
) -> List[Finding]:
    """
    Check a Markdown file for unsupported FAQ answers.

    Args:
        path: Markdown file path.
        fail_on: Included for CLI/API symmetry.
        proof_sidecar: Accepted for runner compatibility and documentation only.

    Returns:
        Structured findings.
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


def _has_non_owned_public_proof_url(text: str) -> bool:
    return any(not _is_owned_proof_url(url) for url in _extract_public_urls(text))


def _extract_public_urls(text: str) -> List[str]:
    urls = [match.group(1) for match in MARKDOWN_LINK_RE.finditer(text)]
    text_without_markdown = MARKDOWN_LINK_RE.sub("", text)
    urls.extend(match.group(0) for match in PUBLIC_URL_RE.finditer(text_without_markdown))
    return urls


def _is_owned_proof_url(url: str) -> bool:
    host = urlparse(url).netloc.lower()
    if host.startswith("www."):
        host = host[4:]
    return any(host == domain or host.endswith(f".{domain}") for domain in OWNED_PROOF_DOMAINS)


def _main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Check FAQ answers for linked proof.")
    parser.add_argument("path", help="Markdown file to check")
    parser.add_argument(
        "--fail-on",
        default="error",
        choices=["error", "warning", "none"],
        help="Minimum finding severity that returns exit code 1",
    )
    parser.add_argument(
        "--proof-sidecar",
        help=(
            "Optional validation sidecar for interface compatibility; FAQ Proof "
            "Map rows cannot replace inline public evidence links."
        ),
    )
    args = parser.parse_args(argv)

    findings = check_file(args.path, fail_on=args.fail_on, proof_sidecar=args.proof_sidecar)
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
