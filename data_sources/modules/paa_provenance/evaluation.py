"""PAA provenance evaluation and source-policy orchestration."""

from __future__ import annotations

from typing import Any, Iterable

from ..faq_structure import detect_faq_structure
from ..guard_common import Finding
from ..proof_sidecar import compose_with_sidecar
from .contracts import (
    PRIMARY_SOURCE_KINDS,
    SUPPLEMENTAL_SOURCE_KINDS,
    WORKFLOW_MODES,
    FaqQuestion,
    ProvenanceBlock,
)
from .evaluation_sources import (
    _ResolvedEvaluation,
    _artifact_path,
    _artifact_questions,
)
from .matching import (
    _exact_match,
    _finding,
    _normalize_for_match,
    _validate_question_match_keys,
)
from .parsing import _extract_faq_questions, _provenance_or_bound_artifact
from .policy import _workflow_policy_finding


def check_content(
    content: str,
    source_path: str | None = None,
    proof_content: str | None = None,
    *,
    workflow_mode: str = "new",
    content_brief: str | None = None,
    answersocrates_blocker: str | None = None,
    expected_query: str | None = None,
    expected_collection_date: str | None = None,
    expected_run_id: str | None = None,
    paa_artifact: str | None = None,
    content_brief_content: str | None = None,
    answersocrates_blocker_content: str | None = None,
    paa_artifact_content: str | None = None,
    raw_capture_snapshot: Any = None,
) -> list[Finding]:
    """Check visible FAQ questions against one primary-source artifact."""
    resolved, finding = _resolve_evaluation(
        content,
        source_path=source_path,
        proof_content=proof_content,
        workflow_mode=workflow_mode,
        content_brief=content_brief,
        paa_artifact=paa_artifact,
    )
    if finding is not None:
        return [finding]
    assert resolved is not None
    policy_finding = _workflow_policy_finding(
        workflow_mode=workflow_mode,
        source_kind=resolved.source_kind,
        provenance=resolved.provenance,
        source_path=source_path,
        content_brief=content_brief,
        content_brief_content=content_brief_content,
    )
    if policy_finding is not None:
        return [policy_finding]
    artifact_path, finding = _artifact_path(
        resolved,
        source_path=source_path,
        paa_artifact_content=paa_artifact_content,
    )
    if finding is not None:
        return [finding]
    assert artifact_path is not None
    questions, fragments, finding = _artifact_questions(
        resolved,
        artifact_path=artifact_path,
        source_path=source_path,
        answersocrates_blocker=answersocrates_blocker,
        expected_query=expected_query,
        expected_collection_date=expected_collection_date,
        expected_run_id=expected_run_id,
        paa_artifact_content=paa_artifact_content,
        answersocrates_blocker_content=answersocrates_blocker_content,
        raw_capture_snapshot=raw_capture_snapshot,
    )
    if finding is not None:
        return [finding]
    normalization = _normalization_finding(resolved, questions)
    if normalization is not None:
        return [normalization]
    return _question_findings(resolved, questions, fragments)


def _resolve_evaluation(
    content: str,
    *,
    source_path: str | None,
    proof_content: str | None,
    workflow_mode: str,
    content_brief: str | None,
    paa_artifact: str | None,
) -> tuple[_ResolvedEvaluation | None, Finding | None]:
    structure = detect_faq_structure(content)
    if structure.unsupported_lines:
        return None, _finding(
            "paa_faq_structure_unsupported",
            structure.unsupported_lines[0],
            None,
            "FAQ-like question markup uses an unsupported structure.",
            "Use a recognized FAQ H2 followed by H3-H5 question headings so provenance can be verified.",
        )
    faq_questions = _extract_faq_questions(content)
    missing = _missing_artifact_finding(faq_questions, workflow_mode, paa_artifact)
    if missing is not None:
        return None, missing
    proof_source = compose_with_sidecar(content, proof_content)
    provenance = _provenance_or_bound_artifact(
        proof_source,
        paa_artifact=paa_artifact,
        content_brief=content_brief,
    )
    if provenance is None:
        first = faq_questions[0]
        return None, _finding(
            "paa_provenance_missing",
            first.line,
            first.question,
            "FAQ section exists, but no PAA/FAQ Provenance block was found.",
            "Add a PAA/FAQ Provenance block with Source, Artifact, and Selected questions before scoring or publishing.",
        )
    source_kind = provenance.source.strip()
    source_finding = _source_kind_finding(source_kind, provenance, workflow_mode)
    if source_finding is not None:
        return None, source_finding
    return _ResolvedEvaluation(faq_questions, provenance, source_kind), None


def _missing_artifact_finding(
    faq_questions: list[FaqQuestion],
    workflow_mode: str,
    paa_artifact: str | None,
) -> Finding | None:
    if faq_questions or paa_artifact:
        return None
    if workflow_mode == "new":
        return _finding(
            "paa_new_answersocrates_required",
            1,
            None,
            "A new blog requires a structured AnswerSocrates artifact even when no FAQ is selected.",
            "Collect and bind the AnswerSocrates artifact, recording an empty selected-question decision when FAQ is not applicable.",
        )
    if workflow_mode == "rewrite":
        return _finding(
            "paa_rewrite_answersocrates_required",
            1,
            None,
            "A rewrite without bound pre-picked brief PAA requires a structured AnswerSocrates artifact.",
            "Bind the dedicated brief PAA artifact when it exists; otherwise collect and bind AnswerSocrates.",
        )
    return None


def _source_kind_finding(
    source_kind: str,
    provenance: ProvenanceBlock,
    workflow_mode: str,
) -> Finding | None:
    if source_kind in SUPPLEMENTAL_SOURCE_KINDS:
        return _finding(
            "paa_supplemental_source_cannot_qualify",
            provenance.line,
            None,
            f"Supplemental PAA source cannot qualify as primary provenance: {source_kind}",
            "Use AnswerSocrates, dedicated brief PAA, or a blocker-backed user CSV.",
            match=source_kind,
        )
    if source_kind not in PRIMARY_SOURCE_KINDS:
        return _finding(
            "paa_source_unsupported",
            provenance.line,
            None,
            f"PAA/FAQ source is not allowed: {provenance.source}",
            "Use the exact source kind answersocrates, brief_paa, or user_csv.",
            match=provenance.source,
        )
    if workflow_mode not in WORKFLOW_MODES:
        return _finding(
            "paa_workflow_mode_invalid",
            provenance.line,
            None,
            f"PAA workflow mode is not supported: {workflow_mode}",
            "Use the exact workflow mode new or rewrite.",
            match=workflow_mode,
        )
    return None


def _normalization_finding(
    resolved: _ResolvedEvaluation,
    eligible_questions: Iterable[str],
) -> Finding | None:
    try:
        _validate_question_match_keys(
            resolved.provenance.selected_questions, field="selected questions"
        )
        _validate_question_match_keys(eligible_questions, field="eligible questions")
        _validate_question_match_keys(
            (question.question for question in resolved.faq_questions),
            field="visible FAQ questions",
        )
    except ValueError as error:
        return _finding(
            "paa_question_normalization_invalid",
            resolved.provenance.line,
            None,
            str(error),
            "Use distinct complete questions that retain a non-empty Unicode-aware match key.",
        )
    return None


def _question_findings(
    resolved: _ResolvedEvaluation,
    eligible_questions: tuple[str, ...],
    ineligible_fragments: tuple[str, ...],
) -> list[Finding]:
    exact_match = resolved.source_kind == "brief_paa"
    match_key = _exact_match if exact_match else _normalize_for_match
    selected = {
        match_key(question) for question in resolved.provenance.selected_questions
    }
    eligible = {match_key(question) for question in eligible_questions}
    ineligible = {match_key(question) for question in ineligible_fragments}
    findings = _visible_question_findings(
        resolved.faq_questions,
        selected=selected,
        eligible=eligible,
        ineligible=ineligible,
        match_key=match_key,
    )
    if resolved.source_kind == "brief_paa":
        findings.extend(_missing_brief_questions(resolved, eligible_questions))
    return findings


def _visible_question_findings(
    questions: list[FaqQuestion],
    *,
    selected: set[str],
    eligible: set[str],
    ineligible: set[str],
    match_key: Any,
) -> list[Finding]:
    findings: list[Finding] = []
    for question in questions:
        normalized = match_key(question.question)
        if normalized not in selected:
            findings.append(
                _finding(
                    "paa_question_missing_from_provenance",
                    question.line,
                    question.question,
                    "FAQ question is not listed in PAA/FAQ Provenance selected questions.",
                    "Add the exact FAQ question to Selected questions or remove it from the FAQ.",
                )
            )
        elif normalized in ineligible:
            findings.append(
                _finding(
                    "paa_question_ineligible_fragment",
                    question.line,
                    question.question,
                    "FAQ question appears in the artifact's ineligible fragment section.",
                    "Use an exact complete question from ## Eligible Questions.",
                )
            )
        elif normalized not in eligible:
            findings.append(
                _finding(
                    "paa_question_missing_from_artifact",
                    question.line,
                    question.question,
                    "FAQ question is not present in the saved PAA/FAQ artifact.",
                    "Use a question from the saved artifact or collect a new source artifact.",
                )
            )
    return findings


def _missing_brief_questions(
    resolved: _ResolvedEvaluation,
    eligible_questions: tuple[str, ...],
) -> list[Finding]:
    visible = {question.question for question in resolved.faq_questions}
    return [
        _finding(
            "paa_brief_question_missing_from_faq",
            resolved.provenance.line,
            question,
            "A pre-picked content-brief PAA question is not an exact visible FAQ heading.",
            "Use every pre-picked question verbatim as a visible FAQ heading.",
        )
        for question in eligible_questions
        if question not in visible
    ]


__all__ = ["check_content"]
