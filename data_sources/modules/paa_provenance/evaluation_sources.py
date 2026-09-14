"""Resolve and read PAA source artifacts for content evaluation."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..guard_common import Finding
from . import snapshot_validation
from .artifact import _extract_csv_questions, _parse_question_artifact
from .contracts import FaqQuestion, ProvenanceBlock, _DuplicateBriefPaaSectionsError
from .matching import (
    _artifact_workspace_root,
    _extract_brief_paa_questions,
    _finding,
    _resolve_artifact_path,
)
from .policy import _answersocrates_blocker_finding, _answersocrates_record_finding


@dataclass(frozen=True, slots=True)
class _ResolvedEvaluation:
    faq_questions: list[FaqQuestion]
    provenance: ProvenanceBlock
    source_kind: str


def _artifact_path(
    resolved: _ResolvedEvaluation,
    *,
    source_path: str | None,
    paa_artifact_content: str | None,
) -> tuple[Path | None, Finding | None]:
    provenance = resolved.provenance
    if not provenance.artifact:
        return None, _finding(
            "paa_artifact_missing",
            provenance.line,
            None,
            "PAA/FAQ Provenance block does not include an Artifact path.",
            "Add an Artifact path that points to the saved PAA/FAQ source file.",
        )
    path = _resolve_artifact_path(provenance.artifact, source_path)
    if path is None or (paa_artifact_content is None and not path.is_file()):
        return None, _finding(
            "paa_artifact_missing",
            provenance.line,
            None,
            f"PAA/FAQ artifact does not resolve: {provenance.artifact}",
            "Save the source artifact and point Artifact to its repo-relative or absolute path.",
            match=provenance.artifact,
        )
    if resolved.faq_questions and not provenance.selected_questions:
        return None, _finding(
            "paa_selected_questions_missing",
            provenance.line,
            None,
            "PAA/FAQ Provenance block does not list selected questions.",
            "Add each FAQ question under Selected questions in the provenance block.",
        )
    return path, None


def _artifact_questions(
    resolved: _ResolvedEvaluation,
    *,
    artifact_path: Path,
    source_path: str | None,
    answersocrates_blocker: str | None,
    expected_query: str | None,
    expected_collection_date: str | None,
    expected_run_id: str | None,
    paa_artifact_content: str | None,
    answersocrates_blocker_content: str | None,
    raw_capture_snapshot: Any,
) -> tuple[tuple[str, ...], tuple[str, ...], Finding | None]:
    if resolved.source_kind == "user_csv":
        return _user_csv_questions(
            resolved,
            artifact_path=artifact_path,
            source_path=source_path,
            blocker=answersocrates_blocker,
            blocker_content=answersocrates_blocker_content,
            expected_query=expected_query,
            expected_collection_date=expected_collection_date,
            expected_run_id=expected_run_id,
            content=paa_artifact_content,
            raw_capture_snapshot=raw_capture_snapshot,
        )
    if resolved.source_kind == "brief_paa":
        return _brief_questions(resolved, artifact_path, paa_artifact_content)
    return _answersocrates_questions(
        resolved,
        artifact_path,
        paa_artifact_content,
        expected_query=expected_query,
        expected_collection_date=expected_collection_date,
        expected_run_id=expected_run_id,
        raw_capture_snapshot=raw_capture_snapshot,
    )


def _user_csv_questions(
    resolved: _ResolvedEvaluation,
    *,
    artifact_path: Path,
    source_path: str | None,
    blocker: str | None,
    blocker_content: str | None,
    expected_query: str | None,
    expected_collection_date: str | None,
    expected_run_id: str | None,
    content: str | None,
    raw_capture_snapshot: Any,
) -> tuple[tuple[str, ...], tuple[str, ...], Finding | None]:
    provenance = resolved.provenance
    if artifact_path.suffix.lower() != ".csv":
        return (
            (),
            (),
            _finding(
                "paa_user_csv_invalid",
                provenance.line,
                None,
                "The user_csv primary artifact is not a .csv file.",
                "Save the supplied questions as a CSV and reference that exact file.",
                match=provenance.artifact,
            ),
        )
    blocker_finding = _answersocrates_blocker_finding(
        blocker,
        source_path=source_path,
        line=provenance.line,
        expected_query=expected_query,
        expected_collection_date=expected_collection_date,
        expected_run_id=expected_run_id,
        blocker_content=blocker_content,
        raw_capture_snapshot=raw_capture_snapshot,
    )
    if blocker_finding is not None:
        return (), (), blocker_finding
    try:
        questions = (
            snapshot_validation.extract_csv_questions_content(content)
            if content is not None
            else _extract_csv_questions(artifact_path)
        )
    except (OSError, UnicodeError, csv.Error):
        questions = ()
    if not questions:
        return (
            (),
            (),
            _finding(
                "paa_user_csv_invalid",
                provenance.line,
                None,
                "The user CSV does not contain any complete question cells.",
                "Add exact, complete questions ending in a question mark to the CSV.",
                match=provenance.artifact,
            ),
        )
    return questions, (), None


def _brief_questions(
    resolved: _ResolvedEvaluation,
    path: Path,
    content: str | None,
) -> tuple[tuple[str, ...], tuple[str, ...], Finding | None]:
    provenance = resolved.provenance
    text, unreadable = _artifact_text(path, content)
    if unreadable:
        return (), (), _unreadable_finding(provenance)
    try:
        questions = _extract_brief_paa_questions(text)
    except _DuplicateBriefPaaSectionsError:
        return (
            (),
            (),
            _finding(
                "paa_brief_sections_duplicate",
                provenance.line,
                None,
                "The bound content brief contains duplicate visible Pre-picked PAA Questions sections.",
                "Keep exactly one visible ## Pre-picked PAA Questions section in the rewrite brief.",
                match=provenance.artifact,
            ),
        )
    if not questions:
        return (
            (),
            (),
            _finding(
                "paa_brief_questions_missing",
                provenance.line,
                None,
                "The bound content brief has no dedicated Pre-picked PAA Questions.",
                "Add complete questions under the exact ## Pre-picked PAA Questions heading.",
                match=provenance.artifact,
            ),
        )
    return questions, (), None


def _answersocrates_questions(
    resolved: _ResolvedEvaluation,
    path: Path,
    content: str | None,
    *,
    expected_query: str | None,
    expected_collection_date: str | None,
    expected_run_id: str | None,
    raw_capture_snapshot: Any,
) -> tuple[tuple[str, ...], tuple[str, ...], Finding | None]:
    provenance = resolved.provenance
    text, unreadable = _artifact_text(path, content)
    if unreadable:
        return (), (), _unreadable_finding(provenance)
    record = _parse_question_artifact(
        text,
        workspace_root=_artifact_workspace_root(path),
        raw_capture_snapshot=raw_capture_snapshot,
    )
    finding = _answersocrates_record_finding(
        record,
        required_status="collected",
        expected_query=expected_query,
        expected_collection_date=expected_collection_date,
        expected_run_id=expected_run_id,
        line=provenance.line,
        artifact=provenance.artifact,
        require_eligible_section=True,
    )
    return (
        () if record is None else record.eligible_questions,
        () if record is None else record.ineligible_fragments,
        finding,
    )


def _artifact_text(path: Path, content: str | None) -> tuple[str, bool]:
    if content is not None:
        return content, False
    try:
        return path.read_text(encoding="utf-8"), False
    except (OSError, UnicodeError):
        return "", True


def _unreadable_finding(provenance: ProvenanceBlock) -> Finding:
    return _finding(
        "paa_artifact_unreadable",
        provenance.line,
        None,
        "The bound PAA artifact cannot be read as a UTF-8 file.",
        "Restore a readable UTF-8 PAA artifact and rerun provenance validation.",
        match=provenance.artifact,
    )


__all__ = ["_ResolvedEvaluation", "_artifact_path", "_artifact_questions"]
