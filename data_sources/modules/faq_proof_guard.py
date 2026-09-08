"""
FAQ Proof Guard

Deterministic guardrail for FAQ answers. It does not decide whether a source
semantically proves a claim. The shared risk-tiered policy decides whether an
answer needs reader-visible proof; this guard exclusively enforces FAQ citation
placement and approved FAQ source classifications.

When a validation sidecar is supplied, every visible non-owned FAQ URL must have
an exact FAQ Proof Map classification as neutral or non_competing_expert; competitor-
owned FAQ sources are prohibited.
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
    from .faq_structure import detect_faq_structure
    from .guard_common import Finding, should_fail, summarize_findings
    from .proof_link_policy import analyze_proof_links, canonicalize_link_identity
except ImportError:  # pragma: no cover - supports direct script execution.
    from faq_structure import detect_faq_structure
    from guard_common import Finding, should_fail, summarize_findings
    from proof_link_policy import analyze_proof_links, canonicalize_link_identity


PUBLIC_URL_RE = re.compile(r"https?://[^\s)\]|<>\"']+", re.IGNORECASE)
H2_RE = re.compile(r"^##\s+")
MARKDOWN_LINK_RE = re.compile(r"\[[^\]]+\]\((https?://[^)]+)\)", re.IGNORECASE)
OWNED_PROOF_DOMAINS = (
    "simprogroup.com",
    "simpro.com",
    "simpro.ai",
    "bigchange.com",
    "clockshark.com",
    "aroflo.com",
)
ALLOWED_FAQ_SOURCE_CLASSES = frozenset({"neutral", "non_competing_expert"})
FAQ_SOURCE_POLICY_HEADING = "## FAQ Source Policy"
FAQ_PROOF_MAP_HEADING = "## FAQ Proof Map"



@dataclass
class FaqAnswer:
    question: str
    heading_line: int
    answer: str


@dataclass
class FaqProofSource:
    question: str
    url: str
    source_class: str
    competitor_check: str
    support: str
    classification_artifact: str
    classification_hash: str


def check_content(
    content: str,
    proof_content: Optional[str] = None,
    base_path: str | Path | None = None,
) -> List[Finding]:
    """
    Check FAQ answers against their machine-assigned risk-tier proof modes.

    Args:
        content: Markdown article or rewrite content.
        proof_content: Optional validation sidecar content. When supplied, it
            must declare the FAQ source policy and classify each visible
            non-owned FAQ URL. It cannot replace the first-paragraph reader link
            when `inline_required` applies; lower-risk answers follow their
            machine-assigned mode without quota-only links.

    Returns:
        Structured findings for FAQ answers that do not satisfy their assigned mode.
    """
    structure = detect_faq_structure(content)
    if structure.unsupported_lines:
        return [
            {
                "rule_id": "faq_structure_unsupported",
                "severity": "error",
                "line": structure.unsupported_lines[0],
                "column": 1,
                "message": "FAQ-like question markup uses an unsupported structure.",
                "suggestion": "Use a recognized FAQ H2 followed by H3-H5 question headings.",
            }
        ]
    faq_answers = _extract_faq_answers(content)
    if not faq_answers:
        return []

    findings: List[Finding] = []

    report = analyze_proof_links(content, proof_content or "")
    requirements = {
        requirement.faq_question: requirement
        for requirement in report.requirements
        if requirement.owner == "faq"
    }

    for faq_answer in faq_answers:
        requirement = requirements.get(faq_answer.question)
        if requirement is None or requirement.mode != "inline_required":
            continue

        first_paragraph = _first_visible_paragraph(faq_answer.answer)
        answer_urls = _non_owned_public_urls(faq_answer.answer)
        first_paragraph_urls = _non_owned_public_urls(first_paragraph)
        if not answer_urls:
            findings.append(
                {
                    "rule_id": "faq_answer_missing_inline_proof",
                    "severity": "error",
                    "line": faq_answer.heading_line,
                    "column": 1,
                    "question": faq_answer.question,
                    "message": (
                        "This fact-driven FAQ answer has no non-owned public evidence "
                        "link in its visible answer body."
                    ),
                    "suggestion": (
                        "Add a descriptive authoritative link in the first visible "
                        "paragraph, or rewrite the answer so it makes no proof-triggering claim."
                    ),
                }
            )
            continue

        if not first_paragraph_urls:
            findings.append(
                {
                    "rule_id": "faq_answer_missing_first_paragraph_proof",
                    "severity": "error",
                    "line": faq_answer.heading_line,
                    "column": 1,
                    "question": faq_answer.question,
                    "message": (
                        "This fact-driven FAQ answer places its proof after the first "
                        "visible paragraph."
                    ),
                    "suggestion": (
                        "Move one approved authority link into the first 40-60-word "
                        "answer paragraph so the extractable answer carries its proof."
                    ),
                }
            )
            continue

        if any(
            link.faq_question == faq_answer.question
            and requirement.line <= link.line <= requirement.end_line
            for link in report.generic_anchors
        ):
            findings.append(
                {
                    "rule_id": "faq_answer_generic_proof_anchor",
                    "severity": "error",
                    "line": faq_answer.heading_line,
                    "column": 1,
                    "question": faq_answer.question,
                    "message": "Required FAQ proof uses generic link text.",
                    "suggestion": (
                        "Use a descriptive anchor naming the authority and evidence topic."
                    ),
                }
            )

    if proof_content is not None:
        findings.extend(
            _check_faq_source_policy(
                faq_answers,
                proof_content,
                base_path=Path(base_path) if base_path is not None else Path.cwd(),
            )
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
        proof_sidecar: Optional validation sidecar used to verify FAQ source
            policy and per-URL classification.

    Returns:
        Structured findings.
    """
    if fail_on not in {"error", "warning", "none"}:
        raise ValueError("fail_on must be one of: error, warning, none")

    proof_content = Path(proof_sidecar).read_text(encoding="utf-8") if proof_sidecar else None
    content = Path(path).read_text(encoding="utf-8")
    return check_content(
        content,
        proof_content=proof_content,
        base_path=Path(path).parent,
    )


def _extract_faq_answers(content: str) -> List[FaqAnswer]:
    return [
        FaqAnswer(
            question=entry.question,
            heading_line=entry.line,
            answer=entry.answer,
        )
        for entry in detect_faq_structure(content).entries
    ]


def _check_faq_source_policy(
    faq_answers: List[FaqAnswer],
    proof_content: str,
    *,
    base_path: Path,
) -> List[Finding]:
    if not any(_non_owned_public_urls(answer.answer) for answer in faq_answers):
        return []
    if not _has_required_faq_source_policy(proof_content):
        first_answer = faq_answers[0]
        return [
            _faq_source_finding(
                first_answer,
                "faq_source_policy_missing",
                "FAQ proof sidecar lacks the required FAQ Source Policy declaration.",
                "Add the allowed source classes, competitor-source prohibition, and Status: aligned.",
            )
        ]

    proof_sources = _extract_faq_proof_sources(proof_content)
    findings: List[Finding] = []
    for faq_answer in faq_answers:
        for url in _non_owned_public_urls(faq_answer.answer):
            source = next(
                (
                    candidate
                    for candidate in proof_sources
                    if candidate.question == faq_answer.question
                    and canonicalize_link_identity(candidate.url)
                    == canonicalize_link_identity(url)
                ),
                None,
            )
            if source is None:
                findings.append(
                    _faq_source_finding(
                        faq_answer,
                        "faq_answer_source_map_url_missing",
                        "Visible non-owned FAQ source has no exact FAQ Proof Map row.",
                        "Add one FAQ Proof Map row for this exact question and URL.",
                    )
                )
                continue

            if not source.source_class:
                findings.append(
                    _faq_source_finding(
                        faq_answer,
                        "faq_answer_source_class_missing",
                        "FAQ Proof Map row lacks a Source class.",
                        "Classify the source as neutral or non_competing_expert.",
                    )
                )
                continue

            if not source.support:
                findings.append(
                    _faq_source_finding(
                        faq_answer,
                        "faq_answer_support_missing",
                        "FAQ Proof Map row has no source-grounded Support proposition.",
                        "State the exact proposition this source supports for the FAQ answer.",
                    )
                )
                continue

            if source.source_class == "competitor_owned" or source.competitor_check == "failed":
                findings.append(
                    _faq_source_finding(
                        faq_answer,
                        "faq_answer_competitor_owned_source",
                        "Competitor-owned sources are prohibited in FAQ answers.",
                        "Replace the source with neutral or non-competing expert evidence.",
                    )
                )
                continue

            if source.source_class not in ALLOWED_FAQ_SOURCE_CLASSES:
                findings.append(
                    _faq_source_finding(
                        faq_answer,
                        "faq_answer_source_class_disallowed",
                        "FAQ source class is not permitted.",
                        "Use only neutral or non_competing_expert evidence.",
                    )
                )
                continue

            if source.competitor_check != "passed":
                findings.append(
                    _faq_source_finding(
                        faq_answer,
                        "faq_answer_competitor_check_missing",
                        "FAQ Proof Map row must record Competitor check: passed.",
                        "Verify the source is non-competing and record Competitor check: passed.",
                    )
                )
                continue

            if not source.classification_artifact or not source.classification_hash:
                findings.append(
                    _faq_source_finding(
                        faq_answer,
                        "faq_answer_source_classification_missing",
                        "FAQ source labels are not bound to a simpro-source-classification/v1 artifact.",
                        "Add the repository-emitted Classification artifact and exact Classification hash.",
                    )
                )
                continue
            classification_error = validate_source_classification_binding(
                source_url=source.url,
                source_class=source.source_class,
                classification_artifact=source.classification_artifact,
                classification_hash=source.classification_hash,
                base_path=base_path,
            )
            if classification_error is not None:
                findings.append(
                    _faq_source_finding(
                        faq_answer,
                        "faq_answer_source_classification_invalid",
                        "FAQ source classification is missing, tampered, mismatched, or not repository-approved.",
                        "Regenerate the classification artifact from the committed source decision registry.",
                    )
                )

    return findings


def _first_visible_paragraph(answer: str) -> str:
    return next(
        (
            paragraph.strip()
            for paragraph in re.split(r"\n\s*\n", answer.strip())
            if paragraph.strip()
        ),
        "",
    )


def _has_required_faq_source_policy(proof_content: str) -> bool:
    required = (
        FAQ_SOURCE_POLICY_HEADING,
        "- Allowed source classes: neutral, non_competing_expert.",
        "- Competitor-owned FAQ sources: prohibited.",
        "- Status: aligned.",
    )
    return all(item in proof_content for item in required)


def _extract_faq_proof_sources(proof_content: str) -> List[FaqProofSource]:
    source_rows: List[FaqProofSource] = []
    in_faq_proof_map = False
    for line in proof_content.splitlines():
        stripped = line.strip()
        if stripped == FAQ_PROOF_MAP_HEADING:
            in_faq_proof_map = True
            continue
        if in_faq_proof_map and H2_RE.match(stripped):
            break
        if not in_faq_proof_map or not stripped.startswith("- FAQ:"):
            continue

        fields = {}
        for segment in stripped[2:].split("|"):
            key, separator, value = segment.partition(":")
            if separator:
                fields[key.strip().lower()] = value.strip()

        question = fields.get("faq", "")
        url = fields.get("url", "")
        if question and url:
            source_rows.append(
                FaqProofSource(
                    question=question,
                    url=url,
                    source_class=fields.get("source class", "").lower(),
                    competitor_check=fields.get("competitor check", "").lower(),
                    support=fields.get("support", "").strip(),
                    classification_artifact=fields.get("classification artifact", "").strip(),
                    classification_hash=fields.get("classification hash", "").strip(),
                )
            )

    return source_rows


def _non_owned_public_urls(text: str) -> List[str]:
    return [url for url in _extract_public_urls(text) if not _is_owned_proof_url(url)]


def _faq_source_finding(
    faq_answer: FaqAnswer,
    rule_id: str,
    message: str,
    suggestion: str,
) -> Finding:
    return {
        "rule_id": rule_id,
        "severity": "error",
        "line": faq_answer.heading_line,
        "column": 1,
        "question": faq_answer.question,
        "message": message,
        "suggestion": suggestion,
    }



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
    parser = argparse.ArgumentParser(
        description="Check FAQ answers against machine-assigned risk-tier proof modes."
    )
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
            "Validation sidecar for FAQ source-policy and per-URL classification; "
            "when inline_required applies, FAQ Proof Map rows cannot replace the "
            "natural authoritative link in the first visible answer paragraph. "
            "The machine assigns lower-risk citation modes."
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
