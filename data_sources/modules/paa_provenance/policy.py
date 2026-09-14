"""PAA provenance policy responsibilities."""

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

from .contracts import (
    ANSWERSOCRATES_BLOCKER_STATES,
    ProvenanceBlock,
    QuestionArtifact,
    _DuplicateBriefPaaSectionsError,
)


def _answersocrates_record_finding(
    record: Optional[QuestionArtifact],
    *,
    required_status: str,
    expected_query: Optional[str],
    expected_collection_date: Optional[str],
    expected_run_id: Optional[str],
    line: int,
    artifact: str,
    require_eligible_section: bool,
    invalid_rule: str = "paa_answersocrates_artifact_unstructured",
) -> Optional[Finding]:
    from .matching import _finding, _parse_iso_date

    invalid = (
        record is None
        or record.source_kind != "answersocrates"
        or record.status != required_status
        or (not record.query)
        or (_parse_iso_date(record.collection_date) is None)
        or (require_eligible_section and (not record.eligible_section_present))
        or (not record.run_receipt_valid)
        or (
            required_status == "blocked"
            and record.blocker.casefold() not in ANSWERSOCRATES_BLOCKER_STATES
        )
    )
    if invalid:
        return _finding(
            invalid_rule,
            line,
            None,
            f"The AnswerSocrates artifact is not a structured {required_status} record.",
            "Use the receipt-bound simpro-answersocrates-artifact/v1 JSON contract"
            + (
                " with an eligible People Also Ask question section."
                if require_eligible_section
                else " with an exact blocker state and non-empty reason: login, captcha, quota, or unavailability."
            ),
            match=artifact,
        )
    expected_date = _parse_iso_date(str(expected_collection_date or ""))
    if (
        not str(expected_query or "").strip()
        or expected_date is None
        or (not str(expected_run_id or "").strip())
    ):
        return _finding(
            "paa_answersocrates_expectation_missing",
            line,
            None,
            "AnswerSocrates validation requires expected query, collection date, and canonical run ID.",
            "Pass expected_query, expected_collection_date, and expected_run_id from the bound plan and BOM.",
            match=artifact,
        )
    assert record is not None
    if record.query != str(expected_query).strip():
        return _finding(
            "paa_answersocrates_query_mismatch",
            line,
            None,
            "AnswerSocrates artifact query does not match the bound expected query.",
            "Recollect with the bound query or supply the matching artifact.",
            match=record.query,
        )
    if record.run_id != str(expected_run_id).strip():
        return _finding(
            "paa_answersocrates_run_mismatch",
            line,
            None,
            "AnswerSocrates artifact run ID does not match the canonical article run.",
            "Recollect within the current article assembly run.",
            match=record.run_id,
        )
    if record.collection_date != expected_date.isoformat():
        return _finding(
            "paa_answersocrates_date_mismatch",
            line,
            None,
            "AnswerSocrates artifact date does not match the expected collection date.",
            "Collect a current artifact for the bound assembly date.",
            match=record.collection_date,
        )
    return None


def _answersocrates_blocker_finding(
    blocker_artifact: Optional[str],
    *,
    source_path: Optional[str],
    line: int,
    expected_query: Optional[str],
    expected_collection_date: Optional[str],
    expected_run_id: Optional[str],
    blocker_content: Optional[str] = None,
    raw_capture_snapshot: Any = None,
) -> Optional[Finding]:
    from .artifact import _parse_question_artifact
    from .matching import _artifact_workspace_root, _finding, _resolve_artifact_path

    if not blocker_artifact:
        return _finding(
            "paa_user_csv_blocker_missing",
            line,
            None,
            "user_csv is allowed only when a structured AnswerSocrates blocker artifact is supplied.",
            "Supply the blocked AnswerSocrates artifact with Source kind, Status, and Blocker fields.",
        )
    blocker_path = _resolve_artifact_path(str(blocker_artifact), source_path)
    if blocker_path is None or (
        blocker_content is None and (not blocker_path.exists())
    ):
        return _finding(
            "paa_user_csv_blocker_missing",
            line,
            None,
            f"AnswerSocrates blocker artifact does not resolve: {blocker_artifact}",
            "Save the blocked AnswerSocrates record and supply its path.",
            match=str(blocker_artifact),
        )
    try:
        blocker_record = _parse_question_artifact(
            blocker_content
            if blocker_content is not None
            else blocker_path.read_text(encoding="utf-8"),
            workspace_root=_artifact_workspace_root(blocker_path),
            raw_capture_snapshot=raw_capture_snapshot,
        )
    except (OSError, UnicodeError):
        blocker_record = None
    return _answersocrates_record_finding(
        blocker_record,
        required_status="blocked",
        expected_query=expected_query,
        expected_collection_date=expected_collection_date,
        expected_run_id=expected_run_id,
        line=line,
        artifact=str(blocker_artifact),
        require_eligible_section=False,
        invalid_rule="paa_answersocrates_blocker_invalid",
    )


def _workflow_policy_finding(
    *,
    workflow_mode: str,
    source_kind: str,
    provenance: ProvenanceBlock,
    source_path: Optional[str],
    content_brief: Optional[str],
    content_brief_content: Optional[str] = None,
) -> Optional[Finding]:
    from .matching import _extract_brief_paa_questions, _finding, _resolve_artifact_path

    if workflow_mode == "new" and source_kind == "brief_paa":
        return _finding(
            "paa_new_answersocrates_required",
            provenance.line,
            None,
            "A new blog cannot use dedicated brief PAA as its primary source.",
            "Collect structured AnswerSocrates questions or document its blocker before using user_csv.",
            match=source_kind,
        )
    if workflow_mode != "rewrite":
        return None
    if not content_brief:
        if source_kind == "brief_paa":
            return _finding(
                "paa_rewrite_answersocrates_required",
                provenance.line,
                None,
                "This rewrite has no bound content brief with dedicated PAA questions.",
                "Use structured AnswerSocrates questions or a blocker-backed user CSV.",
                match=source_kind,
            )
        return None
    provenance_path = _resolve_artifact_path(provenance.artifact, source_path)
    brief_path = _resolve_artifact_path(str(content_brief), source_path)
    questions, error = _rewrite_brief_questions(
        brief_path,
        content_brief_content,
        line=provenance.line,
        brief=str(content_brief),
    )
    if error is not None:
        return error
    pre_picked_questions = questions
    if not pre_picked_questions:
        if source_kind == "brief_paa":
            return _finding(
                "paa_rewrite_answersocrates_required",
                provenance.line,
                None,
                "The rewrite brief does not contain non-empty pre-picked PAA questions.",
                "Use structured AnswerSocrates questions or a blocker-backed user CSV.",
                match=source_kind,
            )
        return None
    if (
        source_kind != "brief_paa"
        or provenance_path is None
        or brief_path is None
        or (provenance_path.resolve() != brief_path.resolve())
    ):
        return _finding(
            "paa_rewrite_brief_precedence_violation",
            provenance.line,
            None,
            "A rewrite with pre-picked brief PAA must use the bound content brief as primary provenance.",
            "Set Source to brief_paa and Artifact to the supplied content brief file.",
            match=source_kind,
        )
    return None


def _rewrite_brief_questions(
    brief_path: Path | None,
    brief_content: str | None,
    *,
    line: int,
    brief: str,
) -> tuple[tuple[str, ...] | None, Finding | None]:
    from .matching import _extract_brief_paa_questions, _finding

    if brief_path is None or (brief_content is None and not brief_path.is_file()):
        return None, _finding(
            "paa_content_brief_unreadable",
            line,
            None,
            "The bound rewrite content brief cannot be read.",
            "Bind the current readable content brief before evaluating PAA precedence.",
            match=brief,
        )
    try:
        content = (
            brief_content
            if brief_content is not None
            else brief_path.read_text(encoding="utf-8")
        )
        return _extract_brief_paa_questions(content), None
    except _DuplicateBriefPaaSectionsError:
        return None, _finding(
            "paa_brief_sections_duplicate",
            line,
            None,
            "The bound content brief contains duplicate visible Pre-picked PAA Questions sections.",
            "Keep exactly one visible ## Pre-picked PAA Questions section in the rewrite brief.",
            match=brief,
        )
    except (OSError, UnicodeError):
        return None, _finding(
            "paa_content_brief_unreadable",
            line,
            None,
            "The bound rewrite content brief cannot be read as UTF-8.",
            "Save a valid UTF-8 content brief before evaluating PAA precedence.",
            match=brief,
        )


__all__ = [
    "_answersocrates_record_finding",
    "_answersocrates_blocker_finding",
    "_workflow_policy_finding",
]
