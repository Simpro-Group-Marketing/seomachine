"""PAA provenance artifact responsibilities."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any, List, Mapping, Optional

from .contracts import (
    ANSWERSOCRATES_ARTIFACT_SCHEMA,
    ANSWERSOCRATES_BLOCKER_STATES,
    QuestionArtifact,
)
from .lists import _strict_question_list, _strict_text_list
from .receipt_validation import (
    _parse_utc_timestamp,
    _valid_answersocrates_receipt,
    _valid_raw_capture_binding,
)


def _parse_question_artifact(
    content: str,
    *,
    workspace_root: str | Path | None = None,
    raw_capture_snapshot: Any = None,
) -> Optional[QuestionArtifact]:
    from .matching import _parse_iso_date

    try:
        value = json.loads(content)
    except (TypeError, json.JSONDecodeError):
        return None
    if not isinstance(value, dict) or set(value) != {
        "schema",
        "source_kind",
        "status",
        "query",
        "collection_date",
        "eligible_question_section",
        "eligible_questions",
        "ineligible_fragments",
        "blocker",
        "raw_capture",
        "run_receipt",
    }:
        return None
    status = value.get("status")
    blocker_value = value.get("blocker")
    blocker = ""
    blocker_valid = blocker_value is None
    if status == "blocked" and isinstance(blocker_value, dict):
        blocker_valid = set(blocker_value) == {"kind", "reason"}
        blocker_kind = blocker_value.get("kind")
        blocker_reason = blocker_value.get("reason")
        blocker_valid = bool(
            blocker_valid
            and isinstance(blocker_kind, str)
            and (blocker_kind.casefold() in ANSWERSOCRATES_BLOCKER_STATES)
            and isinstance(blocker_reason, str)
            and blocker_reason.strip()
        )
        if blocker_valid:
            blocker = str(blocker_kind).casefold()
    try:
        eligible = _strict_question_list(
            value.get("eligible_questions"), field="eligible_questions"
        )
        ineligible = _strict_text_list(
            value.get("ineligible_fragments"), field="ineligible_fragments"
        )
    except ValueError:
        return None
    payload = {
        key: value[key]
        for key in (
            "schema",
            "source_kind",
            "status",
            "query",
            "collection_date",
            "eligible_question_section",
            "eligible_questions",
            "ineligible_fragments",
            "blocker",
            "raw_capture",
        )
    }
    receipt = value.get("run_receipt")
    raw_capture = value.get("raw_capture")
    raw_capture_valid = _valid_raw_capture_binding(
        raw_capture,
        workspace_root=workspace_root,
        expected_query=value.get("query"),
        expected_run_id=receipt.get("run_id") if isinstance(receipt, Mapping) else None,
        expected_collection_date=value.get("collection_date"),
        expected_questions=value.get("eligible_questions"),
        expected_fragments=value.get("ineligible_fragments"),
        expected_blocker=value.get("blocker"),
        raw_capture_snapshot=raw_capture_snapshot,
    )
    receipt_valid = _valid_answersocrates_receipt(receipt, payload=payload)
    structural = bool(
        value.get("schema") == ANSWERSOCRATES_ARTIFACT_SCHEMA
        and value.get("source_kind") == "answersocrates"
        and (status in {"collected", "blocked"})
        and isinstance(value.get("query"), str)
        and (str(value.get("query")).strip() == value.get("query"))
        and (_parse_iso_date(str(value.get("collection_date") or "")) is not None)
        and (value.get("eligible_question_section") == "people_also_ask")
        and blocker_valid
        and (status != "blocked" or not eligible)
        and (status != "collected" or blocker_value is None)
        and raw_capture_valid
    )
    if not structural:
        return None
    return QuestionArtifact(
        source_kind="answersocrates",
        status=str(status),
        query=str(value["query"]),
        collection_date=str(value["collection_date"]),
        run_id=str(receipt.get("run_id") if isinstance(receipt, Mapping) else ""),
        eligible_questions=eligible,
        ineligible_fragments=ineligible,
        eligible_section_present=True,
        blocker=blocker,
        run_receipt_valid=receipt_valid,
    )


def _extract_csv_questions(path: Path) -> tuple[str, ...]:
    questions: List[str] = []
    seen = set()
    with path.open("r", encoding="utf-8-sig", newline="") as csv_file:
        for row in csv.reader(csv_file):
            for cell in row:
                question = cell.strip()
                if not question.endswith("?") or question in seen:
                    continue
                questions.append(question)
                seen.add(question)
    return tuple(questions)


__all__ = [
    "_valid_raw_capture_binding",
    "_strict_text_list",
    "_parse_question_artifact",
    "_strict_question_list",
    "_parse_utc_timestamp",
    "_valid_answersocrates_receipt",
    "_extract_csv_questions",
]
