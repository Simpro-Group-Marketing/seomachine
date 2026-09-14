"""PAA provenance matching responsibilities."""

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
    ANY_H2_RE,
    BRIEF_PAA_HEADING_RE,
    FENCE_OPEN_RE,
    QUESTION_LIST_ITEM_RE,
    _DuplicateBriefPaaSectionsError,
)


def _lines_outside_fences(lines: List[str]) -> List[str]:
    """Return visible Markdown lines while preserving section order."""
    visible: List[str] = []
    fence_character = ""
    fence_length = 0
    for line in lines:
        if fence_character:
            closing = line.strip()
            if (
                closing
                and set(closing) == {fence_character}
                and (len(closing) >= fence_length)
            ):
                fence_character = ""
                fence_length = 0
            continue
        match = FENCE_OPEN_RE.match(line)
        if match is not None:
            marker = match.group(1)
            fence_character = marker[0]
            fence_length = len(marker)
            continue
        visible.append(line)
    return visible


def _file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _extract_artifact_section(
    lines: List[str], heading_re: re.Pattern[str]
) -> Optional[tuple[str, ...]]:
    heading_indexes = [
        index for index, line in enumerate(lines) if heading_re.fullmatch(line.strip())
    ]
    if not heading_indexes:
        return None
    if len(heading_indexes) > 1:
        raise _DuplicateBriefPaaSectionsError(
            "content brief contains duplicate visible dedicated PAA sections"
        )
    start = heading_indexes[0] + 1
    questions: List[str] = []
    for line in lines[start:]:
        stripped = line.strip()
        if ANY_H2_RE.match(stripped):
            break
        match = QUESTION_LIST_ITEM_RE.match(stripped)
        if match:
            questions.append(match.group(1).strip())
    return tuple(questions)


def _extract_brief_paa_questions(content: str) -> Optional[tuple[str, ...]]:
    return _extract_artifact_section(
        _lines_outside_fences(content.splitlines()), BRIEF_PAA_HEADING_RE
    )


def _normalize_for_match(text: str) -> str:
    normalized = unicodedata.normalize("NFKC", text).casefold()
    return " ".join(
        "".join(
            (character if character.isalnum() else " " for character in normalized)
        ).split()
    )


def _parse_iso_date(value: str) -> Optional[date]:
    try:
        parsed = date.fromisoformat(value)
    except (TypeError, ValueError):
        return None
    return parsed if parsed.isoformat() == value else None


def _artifact_workspace_root(path: Path) -> Path:
    """Resolve the workspace root for conventional research-bound artifacts."""
    resolved = path.resolve()
    for parent in resolved.parents:
        if parent.name == "research":
            return parent.parent
    return resolved.parent


def _exact_match(text: str) -> str:
    return text.strip()


def _resolved_file_sha256(artifact: Optional[str], source_path: Optional[str]) -> str:
    if not artifact:
        return ""
    path = _resolve_artifact_path(str(artifact), source_path)
    if path is None or not path.is_file():
        return ""
    try:
        return _file_sha256(path)
    except OSError:
        return ""


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


def _validate_question_match_keys(questions, *, field: str) -> None:
    """Reject empty or ambiguous Unicode-aware question identities."""
    seen: dict[str, str] = {}
    for question in questions:
        key = _normalize_for_match(question)
        if not key:
            raise ValueError(
                f"{field} contains a question with an empty normalization key"
            )
        previous = seen.get(key)
        if previous is not None:
            raise ValueError(
                f"{field} contains questions that collide after normalization"
            )
        seen[key] = question


__all__ = [
    "_lines_outside_fences",
    "_file_sha256",
    "_extract_artifact_section",
    "_extract_brief_paa_questions",
    "_normalize_for_match",
    "_parse_iso_date",
    "_artifact_workspace_root",
    "_exact_match",
    "_resolved_file_sha256",
    "_resolve_artifact_path",
    "_finding",
    "_validate_question_match_keys",
]
