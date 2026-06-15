"""
PAA Provenance Guard

Deterministic guardrail for FAQ question provenance. It does not prove FAQ
answers; faq_proof_guard owns answer proof. This guard verifies that every FAQ
question in a draft appears in a saved PAA/FAQ source artifact from an allowed
source such as AnswerSocrates, SERP, Reddit, YouTube, or a user CSV.
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
    from .proof_sidecar import compose_with_sidecar, load_sidecar_content
except ImportError:  # pragma: no cover - supports direct script execution.
    from guard_common import Finding, should_fail, summarize_findings
    from proof_sidecar import compose_with_sidecar, load_sidecar_content


FAQ_H2_RE = re.compile(r"^##\s+(?:Frequently Asked Questions|FAQ)\s*$", re.IGNORECASE)
H2_RE = re.compile(r"^##\s+")
FAQ_QUESTION_RE = re.compile(r"^###\s+(.+\?)\s*$")
PROVENANCE_HEADING_RE = re.compile(r"^(?:#{1,6}\s+)?PAA/FAQ Provenance\s*$", re.IGNORECASE)
SOURCE_RE = re.compile(r"^-\s*Source:\s*(.+?)\s*$", re.IGNORECASE)
ARTIFACT_RE = re.compile(r"^-\s*Artifact:\s*`?([^`\s]+)`?\s*$", re.IGNORECASE)
SELECTED_RE = re.compile(r"^-\s*Selected questions:\s*$", re.IGNORECASE)
BULLET_RE = re.compile(r"^\s*-\s+(.+?)\s*$")

ALLOWED_SOURCE_PATTERNS = (
    "answersocrates",
    "answer socrates",
    "serp",
    "reddit",
    "youtube",
    "user paa/faq csv",
    "user csv",
    "paa/faq csv",
)


@dataclass
class FaqQuestion:
    question: str
    line: int


@dataclass
class ProvenanceBlock:
    source: str
    artifact: str
    selected_questions: List[str]
    line: int


def check_content(
    content: str,
    source_path: Optional[str] = None,
    proof_content: Optional[str] = None,
) -> List[Finding]:
    """
    Check FAQ questions against a saved PAA/FAQ provenance artifact.

    Args:
        content: Markdown article or rewrite content.
        source_path: Optional markdown file path used to resolve relative artifact paths.

    Returns:
        Structured findings for missing, invalid, or unsupported PAA provenance.
    """
    faq_questions = _extract_faq_questions(content)
    if not faq_questions:
        return []

    proof_source = compose_with_sidecar(content, proof_content)
    provenance = _extract_provenance_block(proof_source)
    if provenance is None:
        return [
            _finding(
                "paa_provenance_missing",
                faq_questions[0].line,
                faq_questions[0].question,
                "FAQ section exists, but no PAA/FAQ Provenance block was found.",
                (
                    "Add a PAA/FAQ Provenance block with Source, Artifact, and "
                    "Selected questions before scoring or publishing."
                ),
            )
        ]

    if not _is_allowed_source(provenance.source):
        return [
            _finding(
                "paa_source_unsupported",
                provenance.line,
                None,
                f"PAA/FAQ source is not allowed: {provenance.source}",
                (
                    "Use AnswerSocrates, SERP, Reddit, YouTube, or a user "
                    "PAA/FAQ CSV as the provenance source."
                ),
                match=provenance.source,
            )
        ]

    if not provenance.artifact:
        return [
            _finding(
                "paa_artifact_missing",
                provenance.line,
                None,
                "PAA/FAQ Provenance block does not include an Artifact path.",
                "Add an Artifact path that points to the saved PAA/FAQ source file.",
            )
        ]

    artifact_path = _resolve_artifact_path(provenance.artifact, source_path)
    if artifact_path is None or not artifact_path.exists():
        return [
            _finding(
                "paa_artifact_missing",
                provenance.line,
                None,
                f"PAA/FAQ artifact does not resolve: {provenance.artifact}",
                "Save the source artifact and point Artifact to its repo-relative or absolute path.",
                match=provenance.artifact,
            )
        ]

    if not provenance.selected_questions:
        return [
            _finding(
                "paa_selected_questions_missing",
                provenance.line,
                None,
                "PAA/FAQ Provenance block does not list selected questions.",
                "Add each FAQ question under Selected questions in the provenance block.",
            )
        ]

    artifact_text = artifact_path.read_text(encoding="utf-8")
    selected_normalized = {
        _normalize_for_match(question) for question in provenance.selected_questions
    }
    artifact_normalized = _normalize_for_match(artifact_text)
    findings: List[Finding] = []

    for faq_question in faq_questions:
        normalized_question = _normalize_for_match(faq_question.question)

        if normalized_question not in selected_normalized:
            findings.append(
                _finding(
                    "paa_question_missing_from_provenance",
                    faq_question.line,
                    faq_question.question,
                    "FAQ question is not listed in PAA/FAQ Provenance selected questions.",
                    "Add the exact FAQ question to Selected questions or remove it from the FAQ.",
                )
            )
            continue

        if normalized_question not in artifact_normalized:
            findings.append(
                _finding(
                    "paa_question_missing_from_artifact",
                    faq_question.line,
                    faq_question.question,
                    "FAQ question is not present in the saved PAA/FAQ artifact.",
                    "Use a question from the saved artifact or collect a new source artifact.",
                )
            )

    return findings


def check_file(
    path: str,
    fail_on: str = "error",
    proof_sidecar: Optional[str] = None,
) -> List[Finding]:
    """
    Check a Markdown file for FAQ/PAA provenance.

    Args:
        path: Markdown file path.
        fail_on: Included for CLI/API symmetry.

    Returns:
        Structured findings.
    """
    if fail_on not in {"error", "warning", "none"}:
        raise ValueError("fail_on must be one of: error, warning, none")

    content = Path(path).read_text(encoding="utf-8")
    proof_content = load_sidecar_content(path, proof_sidecar)
    return check_content(content, source_path=path, proof_content=proof_content)


def _extract_faq_questions(content: str) -> List[FaqQuestion]:
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

    questions: List[FaqQuestion] = []
    for index in range(faq_start_index, faq_end_index):
        match = FAQ_QUESTION_RE.match(lines[index].strip())
        if match:
            questions.append(FaqQuestion(question=match.group(1).strip(), line=index + 1))

    return questions


def _extract_provenance_block(content: str) -> Optional[ProvenanceBlock]:
    lines = content.splitlines()

    for index, line in enumerate(lines):
        if not PROVENANCE_HEADING_RE.match(line.strip()):
            continue

        source = ""
        artifact = ""
        selected_questions: List[str] = []
        in_selected_questions = False

        for block_line in lines[index + 1 :]:
            stripped = block_line.strip()
            if not stripped:
                if in_selected_questions:
                    break
                continue
            if stripped.startswith("```"):
                break
            if stripped.startswith("#"):
                break
            if PROVENANCE_HEADING_RE.match(stripped):
                break

            source_match = SOURCE_RE.match(stripped)
            if source_match:
                source = source_match.group(1).strip()
                in_selected_questions = False
                continue

            artifact_match = ARTIFACT_RE.match(stripped)
            if artifact_match:
                artifact = artifact_match.group(1).strip()
                in_selected_questions = False
                continue

            if SELECTED_RE.match(stripped):
                in_selected_questions = True
                continue

            if in_selected_questions:
                bullet_match = BULLET_RE.match(block_line)
                if bullet_match:
                    selected_questions.append(bullet_match.group(1).strip())
                else:
                    break

        return ProvenanceBlock(
            source=source,
            artifact=artifact,
            selected_questions=selected_questions,
            line=index + 1,
        )

    return None


def _is_allowed_source(source: str) -> bool:
    normalized_source = source.lower()
    return any(pattern in normalized_source for pattern in ALLOWED_SOURCE_PATTERNS)


def _resolve_artifact_path(artifact: str, source_path: Optional[str]) -> Optional[Path]:
    artifact_path = Path(artifact)
    if artifact_path.is_absolute():
        return artifact_path

    candidates = [Path.cwd() / artifact_path]

    if source_path:
        source = Path(source_path).resolve()
        candidates.append(source.parent / artifact_path)
        candidates.append(source.parent.parent / artifact_path)

    for candidate in candidates:
        if candidate.exists():
            return candidate

    return candidates[0] if candidates else None


def _normalize_for_match(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()


def _finding(
    rule_id: str,
    line: int,
    question: Optional[str],
    message: str,
    suggestion: str,
    match: Optional[str] = None,
) -> Finding:
    finding: Finding = {
        "rule_id": rule_id,
        "severity": "error",
        "line": line,
        "column": 1,
        "message": message,
        "suggestion": suggestion,
    }
    if question is not None:
        finding["question"] = question
    if match is not None:
        finding["match"] = match
    return finding


def _main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Check FAQ questions for PAA provenance.")
    parser.add_argument("path", help="Markdown file to check")
    parser.add_argument(
        "--fail-on",
        default="error",
        choices=["error", "warning", "none"],
        help="Minimum finding severity that returns exit code 1",
    )
    parser.add_argument(
        "--proof-sidecar",
        help="Optional validation sidecar containing PAA/FAQ provenance.",
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
