"""Retention journal state models, replay, and validation."""

from __future__ import annotations

import os
import re
import shutil
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from ..bounded_io import canonical_json_sha256, parse_json_object, read_bounded
from .limits import GOVERNANCE_JSON_MAX_BYTES, RETENTION_JOURNAL_MAX_BYTES
from .retention_planning import (
    RetentionCandidate,
    file_sha256,
    format_timestamp,
    parse_timestamp,
    resolve_relative,
)
QUARANTINE_SCHEMA = "simpro-artifact-quarantine/v3"
LEGACY_QUARANTINE_SCHEMA = "simpro-artifact-quarantine/v1"
LEGACY_QUARANTINE_SCHEMA_V2 = "simpro-artifact-quarantine/v2"
QUARANTINE_BASE_SCHEMA = "simpro-artifact-quarantine-base/v3"
QUARANTINE_EVENT_SCHEMA = "simpro-artifact-quarantine-event/v1"
DEFAULT_QUARANTINE_DAYS = 14
TERMINAL_STATUSES = {"complete", "restored", "purged"}
_EVENT_NAME_RE = re.compile(r"^[a-z][a-z0-9_]*$")


@dataclass(frozen=True, slots=True)
class _Transaction:
    run_root: Path
    manifest_path: Path
    base_path: Path | None
    events_path: Path | None
    payload: dict[str, object]
    event_count: int
    last_event_sha256: str
    compacted: bool
    legacy: bool

def _load_transaction(path: Path, *, root: Path) -> _Transaction:
    if path.is_dir():
        run_root = path
    else:
        run_root = path.parent
    manifest_path = run_root / "manifest.json"
    base_path = run_root / "base.json"
    events_path = run_root / "events"
    if base_path.is_file():
        base = _load_json(
            base_path,
            field="quarantine base inventory",
            max_bytes=GOVERNANCE_JSON_MAX_BYTES,
        )
        _validate_base_payload(base)
        event_count, last_event_sha256, rows, status = _replay_events(
            base,
            events_path=events_path,
        )
        payload = {
            "schema": QUARANTINE_SCHEMA,
            "run_id": base["run_id"],
            "status": status,
            "created_at": base["created_at"],
            "delete_after": base["delete_after"],
            "artifacts": rows,
            "event_count": event_count,
            "last_event_sha256": last_event_sha256,
            "compacted": False,
        }
        return _Transaction(
            run_root=run_root,
            manifest_path=manifest_path,
            base_path=base_path,
            events_path=events_path,
            payload=payload,
            event_count=event_count,
            last_event_sha256=last_event_sha256,
            compacted=False,
            legacy=False,
        )
    if manifest_path.is_file():
        payload = _load_json(
            manifest_path,
            field="quarantine manifest",
            max_bytes=GOVERNANCE_JSON_MAX_BYTES,
        )
        _validate_manifest_payload(payload)
        schema = payload.get("schema")
        return _Transaction(
            run_root=run_root,
            manifest_path=manifest_path,
            base_path=None,
            events_path=None,
            payload=payload,
            event_count=int(payload.get("event_count", 0) or 0),
            last_event_sha256=str(payload.get("last_event_sha256", "")),
            compacted=schema == QUARANTINE_SCHEMA,
            legacy=schema != QUARANTINE_SCHEMA,
        )
    raise ValueError("quarantine transaction is invalid")


def _reload_transaction(path: Path, *, root: Path) -> _Transaction:
    return _load_transaction(path, root=root)


def _replay_events(
    base: dict[str, object],
    *,
    events_path: Path,
) -> tuple[int, str, list[dict[str, object]], str]:
    rows = [
        {**row, "status": "pending"}
        for row in _base_artifact_rows(base)
    ]
    status = "moving"
    previous = ""
    event_count = 0
    if not events_path.is_dir():
        return event_count, previous, rows, status
    for expected_sequence, event_path in enumerate(sorted(events_path.glob("*.json")), start=1):
        event_bytes = read_bounded(
            event_path,
            max_bytes=RETENTION_JOURNAL_MAX_BYTES,
            field="retention journal event",
        )
        event_payload = parse_json_object(
            event_bytes,
            field="retention journal event",
        )
        _validate_event(event_payload, run_id=base["run_id"], sequence=expected_sequence)
        if event_payload.get("previous_event_sha256") != previous:
            raise ValueError("retention journal hash chain is invalid")
        previous = canonical_json_sha256(event_payload)
        event_count = expected_sequence
        _apply_event(rows, event_payload)
        event_name = event_payload["event"]
        if event_name == "restore_started":
            status = "restoring"
        elif event_name == "purge_started":
            status = "purging"
        elif event_name == "transaction_complete":
            status = "complete"
        elif event_name == "transaction_restored":
            status = "restored"
        elif event_name == "transaction_purged":
            status = "purged"
    return event_count, previous, rows, status


def _apply_event(
    rows: list[dict[str, object]],
    event_payload: dict[str, object],
) -> None:
    event = event_payload["event"]
    if event in {
        "transaction_started",
        "restore_started",
        "purge_started",
        "transaction_complete",
        "transaction_restored",
        "transaction_purged",
    }:
        return
    index = _event_artifact_index(event_payload, row_count=len(rows))
    row = rows[index - 1]
    statuses = {
        "move_intent": "moving",
        "move_complete": "quarantined",
        "restore_intent": "restoring",
        "restore_complete": "restored",
        "purge_intent": "purging",
        "purge_complete": "purged",
    }
    if event not in statuses:
        raise ValueError(f"unsupported retention journal event: {event}")
    row["status"] = statuses[event]


def _state_payload(
    transaction: _Transaction,
    *,
    status: str,
    compacted: bool,
) -> dict[str, object]:
    payload = dict(transaction.payload)
    payload["schema"] = QUARANTINE_SCHEMA
    payload["status"] = status
    payload["artifacts"] = _artifact_rows(transaction.payload)
    payload["event_count"] = transaction.event_count
    payload["last_event_sha256"] = transaction.last_event_sha256
    payload["compacted"] = compacted
    return payload


def _base_row(
    candidate: RetentionCandidate,
    *,
    index: int,
    root: Path,
    run_root: Path,
) -> dict[str, object]:
    target = run_root / "objects" / f"{index:06d}.blob"
    return {
        "original_path": candidate.path.relative_to(root).as_posix(),
        "quarantine_path": target.relative_to(root).as_posix(),
        "sha256": candidate.sha256,
        "bytes": candidate.byte_count,
    }


def _reject_incomplete_transactions(root: Path) -> None:
    for path in _open_transaction_paths(root):
        transaction = _load_transaction(path, root=root)
        if transaction.payload.get("status") not in TERMINAL_STATUSES:
            raise ValueError(f"incomplete retention transaction requires resume: {path}")


def _manifest_paths(root: Path) -> list[Path]:
    base = root / ".seomachine" / "quarantine"
    paths: list[Path] = []
    for version in ("v1", "v2", "v3"):
        version_root = base / version
        if version_root.is_dir():
            paths.extend(version_root.glob("*/manifest.json"))
            paths.extend(
                run_root
                for run_root in version_root.iterdir()
                if run_root.is_dir() and (run_root / "base.json").is_file()
            )
    return sorted(set(paths))


def _open_transaction_paths(root: Path) -> list[Path]:
    version_root = root / ".seomachine" / "quarantine" / "v3"
    if not version_root.is_dir():
        return []
    return [
        run_root
        for run_root in sorted(version_root.iterdir())
        if run_root.is_dir() and (run_root / "base.json").is_file()
    ]


def _load_json(path: Path, *, field: str, max_bytes: int) -> dict[str, object]:
    try:
        return parse_json_object(
            read_bounded(path, max_bytes=max_bytes, field=field),
            field=field,
        )
    except (OSError, ValueError) as error:
        raise ValueError(f"{field} is invalid: {error}") from error


def _validate_manifest_payload(value: dict[str, object]) -> None:
    schema = value.get("schema")
    if schema == QUARANTINE_SCHEMA:
        expected = {
            "schema",
            "run_id",
            "status",
            "created_at",
            "delete_after",
            "artifacts",
            "event_count",
            "last_event_sha256",
            "compacted",
        }
        if set(value) != expected or value.get("compacted") is not True:
            raise ValueError("quarantine manifest is invalid")
    elif schema not in {LEGACY_QUARANTINE_SCHEMA, LEGACY_QUARANTINE_SCHEMA_V2}:
        raise ValueError("quarantine manifest is invalid")
    if not isinstance(value.get("run_id"), str):
        raise ValueError("quarantine run_id is invalid")
    parse_timestamp(value.get("created_at"))
    parse_timestamp(value.get("delete_after"))
    rows = value.get("artifacts")
    if not isinstance(rows, list) or not all(isinstance(row, dict) for row in rows):
        raise ValueError("quarantine artifact inventory is invalid")
    for row in rows:
        _validate_manifest_row(row)


def _validate_base_payload(value: dict[str, object]) -> None:
    expected = {"schema", "run_id", "created_at", "delete_after", "artifacts"}
    if set(value) != expected or value.get("schema") != QUARANTINE_BASE_SCHEMA:
        raise ValueError("quarantine base inventory is invalid")
    if not isinstance(value.get("run_id"), str):
        raise ValueError("quarantine run_id is invalid")
    parse_timestamp(value.get("created_at"))
    parse_timestamp(value.get("delete_after"))
    _base_artifact_rows(value)


def _validate_event(
    value: dict[str, object],
    *,
    run_id: object,
    sequence: int,
) -> None:
    allowed = {
        "schema",
        "run_id",
        "sequence",
        "event",
        "created_at",
        "previous_event_sha256",
        "artifact_index",
    }
    if not set(value) <= allowed or value.get("schema") != QUARANTINE_EVENT_SCHEMA:
        raise ValueError("retention journal event is invalid")
    if value.get("run_id") != run_id or value.get("sequence") != sequence:
        raise ValueError("retention journal sequence is invalid")
    event = value.get("event")
    if not isinstance(event, str) or _EVENT_NAME_RE.fullmatch(event) is None:
        raise ValueError("retention journal event name is invalid")
    previous = value.get("previous_event_sha256")
    if not isinstance(previous, str) or (previous and len(previous) != 64):
        raise ValueError("retention journal previous hash is invalid")
    parse_timestamp(value.get("created_at"))


def _artifact_rows(payload: dict[str, object]) -> list[dict[str, object]]:
    rows = payload.get("artifacts")
    if not isinstance(rows, list) or not all(isinstance(row, dict) for row in rows):
        raise ValueError("quarantine artifact inventory is invalid")
    return rows


def _base_artifact_rows(payload: dict[str, object]) -> list[dict[str, object]]:
    rows = _artifact_rows(payload)
    for row in rows:
        _validate_base_row(row)
    return rows


def _validate_base_row(row: dict[str, object]) -> None:
    if set(row) != {"original_path", "quarantine_path", "sha256", "bytes"}:
        raise ValueError("quarantine artifact row is invalid")
    _validate_row_values(row)


def _validate_manifest_row(row: dict[str, object]) -> None:
    if set(row) != {"original_path", "quarantine_path", "sha256", "bytes", "status"}:
        raise ValueError("quarantine artifact row is invalid")
    _validate_row_values(row)
    if row.get("status") not in {
        "pending",
        "moving",
        "linking",
        "linked",
        "unlinking",
        "quarantined",
        "restoring",
        "restored",
        "purging",
        "purged",
    }:
        raise ValueError("quarantine artifact status is invalid")


def _validate_row_values(row: dict[str, object]) -> None:
    digest = row.get("sha256")
    if not isinstance(digest, str) or len(digest) != 64:
        raise ValueError("quarantine artifact hash is invalid")
    byte_count = row.get("bytes")
    if isinstance(byte_count, bool) or not isinstance(byte_count, int) or byte_count < 0:
        raise ValueError("quarantine artifact byte count is invalid")


def _event_artifact_index(value: dict[str, object], *, row_count: int) -> int:
    index = value.get("artifact_index")
    if isinstance(index, bool) or not isinstance(index, int) or not 1 <= index <= row_count:
        raise ValueError("retention journal artifact index is invalid")
    return index


def _verify_file(path: Path, row: dict[str, object], *, label: str) -> None:
    if not path.is_file():
        raise ValueError(f"{label} is missing: {path}")
    if path.stat().st_size != row.get("bytes") or file_sha256(path) != row.get("sha256"):
        raise ValueError(f"{label} hash or size mismatch: {path}")


def _link_no_clobber(source: Path, target: Path) -> None:
    try:
        os.link(source, target)
    except FileExistsError as error:
        raise ValueError(f"quarantine target already exists: {target}") from error


def _same_file(left: Path, right: Path) -> bool:
    try:
        return os.path.samefile(left, right)
    except OSError:
        return False


def _resolve_transaction_path(path: str | Path, *, root: Path) -> Path:
    candidate = Path(path)
    if not candidate.is_absolute():
        candidate = root / candidate
    resolved = candidate.resolve(strict=True)
    resolved.relative_to(root)
    return resolved


def _journal_bytes(events_path: Path) -> int:
    if not events_path.is_dir():
        return 0
    return sum(path.stat().st_size for path in events_path.glob("*.json"))


def _remove_event_journal(events_path: Path | None) -> None:
    if events_path is None or not events_path.is_dir():
        return
    for path in sorted(events_path.iterdir()):
        if path.is_file() and path.suffix == ".json":
            path.unlink()
    events_path.rmdir()


