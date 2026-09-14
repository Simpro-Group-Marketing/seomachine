"""PAA provenance parsing responsibilities."""

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
    ARTIFACT_RE,
    BULLET_RE,
    FaqQuestion,
    PROVENANCE_HEADING_RE,
    ProvenanceBlock,
    SELECTED_RE,
    SOURCE_RE,
)


def _provenance_or_bound_artifact(
    content: str, *, paa_artifact: Optional[str], content_brief: Optional[str]
) -> Optional[ProvenanceBlock]:
    provenance = _extract_provenance_block(content)
    if provenance is not None or not paa_artifact:
        return provenance
    artifact_path = Path(paa_artifact)
    source_kind = "answersocrates"
    if artifact_path.suffix.casefold() == ".csv":
        source_kind = "user_csv"
    elif content_brief:
        try:
            if artifact_path.resolve() == Path(content_brief).resolve():
                source_kind = "brief_paa"
        except OSError:
            pass
    return ProvenanceBlock(
        source=source_kind,
        artifact=str(paa_artifact),
        selected_questions=[
            question.question for question in _extract_faq_questions(content)
        ],
        line=1,
    )


def _extract_provenance_block(content: str) -> Optional[ProvenanceBlock]:
    lines = content.splitlines()
    for index, line in enumerate(lines):
        if PROVENANCE_HEADING_RE.match(line.strip()):
            source, artifact, selected = _parse_provenance_lines(lines[index + 1 :])
            return ProvenanceBlock(
                source=source,
                artifact=artifact,
                selected_questions=selected,
                line=index + 1,
            )
    return None


def _parse_provenance_lines(lines: list[str]) -> tuple[str, str, list[str]]:
    source = ""
    artifact = ""
    selected: list[str] = []
    in_selected = False
    for line in lines:
        stripped = line.strip()
        if _ends_provenance_block(stripped, in_selected=in_selected):
            break
        if not stripped:
            continue
        source_match = SOURCE_RE.match(stripped)
        artifact_match = ARTIFACT_RE.match(stripped)
        if source_match:
            source = source_match.group(1).strip()
            in_selected = False
        elif artifact_match:
            artifact = artifact_match.group(1).strip()
            in_selected = False
        elif SELECTED_RE.match(stripped):
            in_selected = True
        elif in_selected:
            bullet = BULLET_RE.match(line)
            if not bullet:
                break
            selected.append(bullet.group(1).strip())
    return source, artifact, selected


def _ends_provenance_block(value: str, *, in_selected: bool) -> bool:
    return bool(
        (not value and in_selected)
        or value.startswith("```")
        or value.startswith("#")
        or PROVENANCE_HEADING_RE.match(value)
    )


def _extract_faq_questions(content: str) -> List[FaqQuestion]:
    return [
        FaqQuestion(question=entry.question, line=entry.line)
        for entry in detect_faq_structure(content).entries
    ]


__all__ = [
    "_provenance_or_bound_artifact",
    "_extract_provenance_block",
    "_extract_faq_questions",
]
