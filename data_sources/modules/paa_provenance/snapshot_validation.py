"""PAA provenance snapshot validation responsibilities."""

from __future__ import annotations

import csv
import io
from datetime import datetime, timezone
from typing import Any, Callable, Mapping


def valid_raw_capture_binding(
    binding: object,
    *,
    workspace_root: Any,
    expected_query: object,
    expected_run_id: object,
    expected_collection_date: object,
    expected_questions: object,
    expected_fragments: object,
    expected_blocker: object,
    raw_capture_snapshot: Any,
    capture_contracts: Mapping[str, tuple[object, str]],
    raw_capture_fields: frozenset[str],
    resolve_artifact_fn: Callable[..., Any],
    load_snapshot_fn: Callable[..., Any],
    verify_attestation_fn: Callable[..., bool],
    parse_timestamp_fn: Callable[[object], Any],
    derive_observations_fn: Callable[[object], tuple[list[str], list[str], Any]],
) -> bool:
    """Validate an AnswerSocrates raw capture from snapshot or legacy storage."""
    if workspace_root is None:
        return isinstance(binding, Mapping) and set(binding) == {"path", "sha256"}
    if not isinstance(binding, Mapping) or set(binding) != {"path", "sha256"}:
        return False
    snapshot = _snapshot(
        binding,
        workspace_root=workspace_root,
        supplied=raw_capture_snapshot,
        resolve_artifact_fn=resolve_artifact_fn,
        load_snapshot_fn=load_snapshot_fn,
    )
    if snapshot is None or snapshot.sha256 != binding.get("sha256"):
        return False
    capture = _payload(snapshot)
    if not isinstance(capture, Mapping):
        return False
    contract = capture_contracts.get(capture.get("schema"))
    if contract is None:
        return False
    collector, purpose = contract
    if (
        set(capture) != raw_capture_fields
        or capture.get("collector") != collector
        or capture.get("query") != expected_query
        or capture.get("run_id") != expected_run_id
        or not verify_attestation_fn(
            capture,
            purpose=purpose,
            workspace_root=workspace_root,
        )
    ):
        return False
    completed = parse_timestamp_fn(capture.get("completed_at"))
    started = parse_timestamp_fn(capture.get("started_at"))
    if (
        started is None
        or completed is None
        or completed <= started
        or completed > datetime.now(timezone.utc)
        or completed.date().isoformat() != expected_collection_date
    ):
        return False
    try:
        questions, fragments, blocker = derive_observations_fn(
            capture.get("raw_response")
        )
    except ValueError:
        return False
    return (
        questions == expected_questions
        and fragments == expected_fragments
        and blocker == expected_blocker
    )


def _snapshot(
    binding: Mapping[str, Any],
    *,
    workspace_root: Any,
    supplied: Any,
    resolve_artifact_fn: Callable[..., Any],
    load_snapshot_fn: Callable[..., Any],
) -> Any:
    if supplied is not None:
        if getattr(supplied, "relative_path", None) != binding.get("path") or getattr(
            supplied, "sha256", None
        ) != binding.get("sha256"):
            return None
        return supplied
    try:
        path = resolve_artifact_fn(
            binding.get("path"),
            workspace_root=workspace_root,
        )
        return load_snapshot_fn(
            path,
            field="AnswerSocrates raw capture",
        )
    except ValueError:
        return None


def _payload(snapshot: Any) -> Any:
    return getattr(snapshot, "json_payload", getattr(snapshot, "payload", None))


def extract_csv_questions_content(content: str) -> tuple[str, ...]:
    """Extract stable, distinct question cells from captured CSV text."""
    questions: list[str] = []
    seen: set[str] = set()
    for row in csv.reader(io.StringIO(content)):
        for cell in row:
            question = cell.strip()
            if not question.endswith("?") or question in seen:
                continue
            questions.append(question)
            seen.add(question)
    return tuple(questions)


__all__ = ["extract_csv_questions_content", "valid_raw_capture_binding"]
