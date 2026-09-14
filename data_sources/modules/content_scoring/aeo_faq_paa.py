"""Focused aeo faq paa scoring."""

from __future__ import annotations

from .aeo_text import _first_paragraph
from .aeo_text import _plain_text
from .aeo_text import _word_count
from collections.abc import Mapping
from collections.abc import Sequence
from data_sources.modules.faq_answer_quality_guard import check_content as check_faq_answer_quality
from data_sources.modules.faq_proof_guard import check_content as check_faq_proof
from data_sources.modules.faq_structure import detect_faq_structure
from data_sources.modules.paa_provenance_guard import check_content as check_paa_provenance_content
from typing import Any
from typing import Dict
from typing import List
from typing import Optional
from typing import Tuple

def _findings_passed(findings: Sequence[Mapping[str, Any]]) -> bool:
    return not any(
        str(finding.get("severity", "error")).casefold() == "error"
        for finding in findings
    )

def _check_bound_paa_provenance(
    content: str,
    source_path: Optional[str],
    proof_sidecar_content: Optional[str],
    *,
    workflow_mode: str,
    content_brief: Optional[str],
    answersocrates_blocker: Optional[str],
    expected_query: Optional[str],
    expected_collection_date: Optional[str],
    expected_run_id: Optional[str],
    paa_artifact: Optional[str],
    prevalidated_findings: Optional[Sequence[Mapping[str, Any]]] = None,
) -> Dict[str, Any]:
    findings = (
        [dict(finding) for finding in prevalidated_findings]
        if prevalidated_findings is not None
        else check_paa_provenance_content(
            content,
            source_path=source_path,
            proof_content=proof_sidecar_content,
            workflow_mode=workflow_mode,
            content_brief=content_brief,
            answersocrates_blocker=answersocrates_blocker,
            expected_query=expected_query,
            expected_collection_date=expected_collection_date,
            expected_run_id=expected_run_id,
            paa_artifact=paa_artifact,
        )
    )
    return {
        'passed': _findings_passed(findings),
        'issue': 'PAA provenance does not match the bound workflow, query, or date.',
        'fix': (
            'Pass the BOM-bound workflow mode, exact query, assembly collection '
            'date, and primary PAA artifact into the AEO rater.'
        ),
        'severity': 'high',
        'details': {
            'finding_count': len(findings),
            'findings': findings,
            'prevalidated': prevalidated_findings is not None,
        },
    }

def _extract_faq_questions(body: str) -> List[Tuple[str, str]]:
    return [
        (entry.question, entry.answer)
        for entry in detect_faq_structure(body).entries
    ]

def _check_faq_structure(body: str) -> Dict[str, Any]:
    structure = detect_faq_structure(body)
    passed = not structure.unsupported_lines
    return {
        "passed": passed,
        "issue": "FAQ-like question markup uses an unsupported structure.",
        "fix": "Use a recognized FAQ H2 followed by H3-H5 question headings.",
        "severity": "high",
        "details": {
            "heading_present": structure.heading_present,
            "unsupported_lines": list(structure.unsupported_lines),
        },
    }

def _check_faq_questions(body: str) -> Dict[str, Any]:
    questions = _extract_faq_questions(body)
    question_count = len(questions)
    passed = question_count > 0

    return {
        "passed": passed,
        "issue": "The selected FAQ/PAA section has no natural-language question headings.",
        "fix": "Use the useful complete questions selected by the bound PAA policy, without a fixed count.",
        "severity": "high",
        "details": {
            "question_count": question_count,
            "questions": [question for question, _ in questions],
        },
    }

def _check_faq_answer_lengths(body: str) -> Dict[str, Any]:
    questions = _extract_faq_questions(body)
    lengths = []
    failing = []

    for question, answer_body in questions:
        paragraph = _first_paragraph(answer_body)
        words = _word_count(_plain_text(paragraph))
        lengths.append({"question": question, "words": words})
        if words < 40 or words > 60:
            failing.append({"question": question, "words": words})

    passed = bool(questions) and not failing
    return {
        "passed": passed,
        "issue": "One or more FAQ answers is outside the 40-60 word AEO snippet range.",
        "fix": "Rewrite each FAQ answer as a 40-60 word direct answer, then add context after it if needed.",
        "severity": "medium",
        "details": {
            "answer_lengths": lengths,
            "failing_answers": failing,
        },
    }

def _check_faq_answer_quality(
    content: str,
    *,
    prevalidated_findings: Optional[Sequence[Mapping[str, Any]]] = None,
) -> Dict[str, Any]:
    findings = (
        [dict(finding) for finding in prevalidated_findings]
        if prevalidated_findings is not None
        else check_faq_answer_quality(content)
    )
    passed = _findings_passed(findings)

    return {
        "passed": passed,
        "issue": "One or more FAQ answers opens with a generic non-answer.",
        "fix": (
            "Lead with a supported number or range, named recommendation, "
            "definition, concrete action, or explained yes/no answer. Move "
            "limitations after the direct answer."
        ),
        "severity": "high",
        "details": {
            "finding_count": len(findings),
            "findings": findings,
            "prevalidated": prevalidated_findings is not None,
        },
    }

def _check_faq_proof(
    content: str,
    proof_sidecar_content: Optional[str],
    *,
    prevalidated_findings: Optional[Sequence[Mapping[str, Any]]] = None,
) -> Dict[str, Any]:
    findings = (
        [dict(finding) for finding in prevalidated_findings]
        if prevalidated_findings is not None
        else check_faq_proof(content, proof_content=proof_sidecar_content or None)
    )
    passed = _findings_passed(findings)

    return {
        "passed": passed,
        "issue": (
            "One or more FAQ answers does not satisfy its machine-assigned "
            "citation mode."
        ),
        "fix": (
            "Resolve each finding according to its machine-assigned citation_mode. "
            "For inline_required, add a natural descriptive anchor to an "
            "authoritative owned or non-owned source in the first visible answer "
            "paragraph, map it in the FAQ Proof Map, and do not use competitor-owned "
            "FAQ sources. For section_source_allowed, "
            "sidecar_only, or proof_not_required, satisfy the assigned mode without "
            "quota-only links; a sidecar cannot replace inline evidence when "
            "inline_required applies."
        ),
        "severity": "high",
        "details": {
            "finding_count": len(findings),
            "findings": findings,
            "prevalidated": prevalidated_findings is not None,
        },
    }

def _check_paa_provenance(
    content: str,
    source_path: Optional[str],
    proof_sidecar_content: Optional[str],
    *,
    workflow_mode: str = "new",
    content_brief: Optional[str] = None,
    answersocrates_blocker: Optional[str] = None,
    expected_query: Optional[str] = None,
    expected_collection_date: Optional[str] = None,
    expected_run_id: Optional[str] = None,
    paa_artifact: Optional[str] = None,
) -> Dict[str, Any]:
    return _check_bound_paa_provenance(
        content,
        source_path,
        proof_sidecar_content,
        workflow_mode=workflow_mode,
        content_brief=content_brief,
        answersocrates_blocker=answersocrates_blocker,
        expected_query=expected_query,
        expected_collection_date=expected_collection_date,
        expected_run_id=expected_run_id,
        paa_artifact=paa_artifact,
    )


__all__ = [
    "_findings_passed",
    "_check_bound_paa_provenance",
    "_extract_faq_questions",
    "_check_faq_structure",
    "_check_faq_questions",
    "_check_faq_answer_lengths",
    "_check_faq_answer_quality",
    "_check_faq_proof",
    "_check_paa_provenance",
]
