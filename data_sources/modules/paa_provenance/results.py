"""PAA provenance results responsibilities."""

from __future__ import annotations

# ruff: noqa: F401
import argparse
import csv
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unicodedata
from dataclasses import dataclass, replace
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, List, Mapping, Optional

from ..blog_assembly_contract import (
    atomic_write_json,
    canonical_json_sha256,
    canonical_snapshot_artifact,
    load_json_object_snapshot,
    resolve_artifact,
)
from ..execution_attestation import attest_mapping, verify_mapping_attestation
from ..faq_structure import detect_faq_structure
from ..guard_common import Finding, should_fail, summarize_findings
from ..proof_sidecar import compose_with_sidecar, load_sidecar_content
from . import snapshot_validation as paa_provenance_snapshot

from .contracts import (
    PaaProvenanceResult,
    _DuplicateBriefPaaSectionsError,
)


def check_file(
    path: str,
    fail_on: str = "error",
    proof_sidecar: Optional[str] = None,
    *,
    workflow_mode: str = "new",
    content_brief: Optional[str] = None,
    answersocrates_blocker: Optional[str] = None,
    expected_query: Optional[str] = None,
    expected_collection_date: Optional[str] = None,
    expected_run_id: Optional[str] = None,
    paa_artifact: Optional[str] = None,
) -> List[Finding]:
    """
    Check a Markdown file for FAQ/PAA provenance.

    Args:
        path: Markdown file path.
        fail_on: Included for CLI/API symmetry.

    Returns:
        Structured findings.
    """
    result = evaluate_file(
        path,
        fail_on=fail_on,
        proof_sidecar=proof_sidecar,
        workflow_mode=workflow_mode,
        content_brief=content_brief,
        answersocrates_blocker=answersocrates_blocker,
        expected_query=expected_query,
        expected_collection_date=expected_collection_date,
        expected_run_id=expected_run_id,
        paa_artifact=paa_artifact,
    )
    return list(result.findings)


def evaluate_file(
    path: str,
    fail_on: str = "error",
    proof_sidecar: Optional[str] = None,
    *,
    workflow_mode: str = "new",
    content_brief: Optional[str] = None,
    answersocrates_blocker: Optional[str] = None,
    expected_query: Optional[str] = None,
    expected_collection_date: Optional[str] = None,
    expected_run_id: Optional[str] = None,
    paa_artifact: Optional[str] = None,
) -> PaaProvenanceResult:
    """Return reusable PAA provenance state and findings for a Markdown file."""
    from .matching import _file_sha256, _finding, _resolve_artifact_path

    if fail_on not in {"error", "warning", "none"}:
        raise ValueError("fail_on must be one of: error, warning, none")
    content = Path(path).read_text(encoding="utf-8")
    proof_content = load_sidecar_content(path, proof_sidecar)
    result = evaluate_content(
        content,
        source_path=path,
        proof_content=proof_content,
        workflow_mode=workflow_mode,
        content_brief=content_brief,
        answersocrates_blocker=answersocrates_blocker,
        expected_query=expected_query,
        expected_collection_date=expected_collection_date,
        expected_run_id=expected_run_id,
        paa_artifact=paa_artifact,
    )
    if paa_artifact:
        expected_path = Path(paa_artifact).resolve()
        actual_path = _resolve_artifact_path(result.artifact, path)
        mismatch = actual_path is None or actual_path.resolve() != expected_path
        artifact_hash_unreadable = False
        try:
            hash_mismatch = bool(
                expected_path.is_file()
                and result.artifact_sha256
                and (_file_sha256(expected_path) != result.artifact_sha256)
            )
        except OSError:
            artifact_hash_unreadable = True
            hash_mismatch = False
        extra: list[Finding] = []
        if mismatch:
            extra.append(
                _finding(
                    "paa_artifact_binding_mismatch",
                    1,
                    None,
                    "PAA provenance does not reference the exact BOM-bound artifact.",
                    "Regenerate provenance from the exact bound PAA artifact.",
                )
            )
        elif artifact_hash_unreadable:
            extra.append(
                _finding(
                    "paa_artifact_unreadable",
                    1,
                    None,
                    "The BOM-bound PAA artifact disappeared during validation.",
                    "Restore the exact artifact and rerun PAA provenance validation.",
                    match=str(paa_artifact),
                )
            )
        elif hash_mismatch:
            extra.append(
                _finding(
                    "paa_artifact_hash_mismatch",
                    1,
                    None,
                    "The BOM-bound PAA artifact changed after provenance was recorded.",
                    "Regenerate the PAA binding from current artifact bytes.",
                )
            )
        if extra:
            result = replace(result, findings=tuple([*result.findings, *extra]))
    return result


def evaluate_content(
    content: str,
    source_path: Optional[str] = None,
    proof_content: Optional[str] = None,
    *,
    workflow_mode: str = "new",
    content_brief: Optional[str] = None,
    answersocrates_blocker: Optional[str] = None,
    expected_query: Optional[str] = None,
    expected_collection_date: Optional[str] = None,
    expected_run_id: Optional[str] = None,
    paa_artifact: Optional[str] = None,
) -> PaaProvenanceResult:
    """Return reusable PAA provenance state and findings for article content."""
    from .artifact import _extract_csv_questions, _parse_question_artifact
    from .evaluation import check_content
    from .matching import (
        _artifact_workspace_root,
        _extract_brief_paa_questions,
        _file_sha256,
        _resolve_artifact_path,
        _resolved_file_sha256,
    )
    from .parsing import _extract_faq_questions, _provenance_or_bound_artifact

    faq_questions = tuple(
        (question.question for question in _extract_faq_questions(content))
    )
    proof_source = compose_with_sidecar(content, proof_content)
    provenance = _provenance_or_bound_artifact(
        proof_source, paa_artifact=paa_artifact, content_brief=content_brief
    )
    source_kind = provenance.source.strip() if provenance is not None else ""
    artifact = provenance.artifact if provenance is not None else ""
    selected_questions = (
        tuple(provenance.selected_questions) if provenance is not None else ()
    )
    artifact_sha256 = ""
    artifact_questions: tuple[str, ...] = ()
    artifact_query = ""
    artifact_collection_date = ""
    artifact_path = _resolve_artifact_path(artifact, source_path) if artifact else None
    if artifact_path is not None and artifact_path.is_file():
        try:
            artifact_sha256 = _file_sha256(artifact_path)
            if source_kind == "user_csv":
                artifact_questions = _extract_csv_questions(artifact_path)
            else:
                artifact_text = artifact_path.read_text(encoding="utf-8")
                if source_kind == "brief_paa":
                    artifact_questions = (
                        _extract_brief_paa_questions(artifact_text) or ()
                    )
                elif source_kind == "answersocrates":
                    artifact_record = _parse_question_artifact(
                        artifact_text,
                        workspace_root=_artifact_workspace_root(artifact_path),
                    )
                    if artifact_record is not None:
                        artifact_questions = artifact_record.eligible_questions
                        artifact_query = artifact_record.query
                        artifact_collection_date = artifact_record.collection_date
        except (OSError, UnicodeError, csv.Error, _DuplicateBriefPaaSectionsError):
            artifact_questions = ()
    findings = check_content(
        content,
        source_path=source_path,
        proof_content=proof_content,
        workflow_mode=workflow_mode,
        content_brief=content_brief,
        answersocrates_blocker=answersocrates_blocker,
        expected_query=expected_query,
        expected_collection_date=expected_collection_date,
        expected_run_id=expected_run_id,
        paa_artifact=paa_artifact,
    )
    return PaaProvenanceResult(
        workflow_mode=workflow_mode,
        source_kind=source_kind,
        artifact=artifact,
        artifact_sha256=artifact_sha256,
        artifact_questions=artifact_questions,
        artifact_query=artifact_query,
        artifact_collection_date=artifact_collection_date,
        content_brief=str(content_brief or ""),
        content_brief_sha256=_resolved_file_sha256(content_brief, source_path),
        answersocrates_blocker=str(answersocrates_blocker or ""),
        answersocrates_blocker_sha256=_resolved_file_sha256(
            answersocrates_blocker, source_path
        ),
        expected_query=str(expected_query or ""),
        expected_collection_date=str(expected_collection_date or ""),
        expected_run_id=str(expected_run_id or ""),
        faq_questions=faq_questions,
        selected_questions=selected_questions,
        findings=tuple(findings),
    )


__all__ = [
    "check_file",
    "evaluate_file",
    "evaluate_content",
]
