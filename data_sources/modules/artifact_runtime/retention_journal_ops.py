"""Retention v3 journal side-effect operations."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

from ..bounded_io import (
    atomic_write_canonical_json,
    bounded_canonical_json_bytes,
    parse_json_object,
    read_bounded,
)
from .limits import GOVERNANCE_JSON_MAX_BYTES, RETENTION_JOURNAL_MAX_BYTES
from .retention_planning import RetentionCandidate, format_timestamp, resolve_relative
from .retention_store import (
    QUARANTINE_BASE_SCHEMA,
    QUARANTINE_EVENT_SCHEMA,
    TERMINAL_STATUSES,
    _EVENT_NAME_RE,
    _Transaction,
    _artifact_rows,
    _base_row,
    _journal_bytes,
    _link_no_clobber,
    _load_json,
    _load_transaction,
    _reload_transaction,
    _remove_event_journal,
    _same_file,
    _state_payload,
    _verify_file,
)
def _create_transaction(
    root: Path,
    *,
    candidates: tuple[RetentionCandidate, ...],
    now: datetime,
    quarantine_days: int,
) -> _Transaction:
    run_id = uuid4().hex
    stamp = now.strftime("%Y%m%dT%H%M%SZ")
    run_root = root / ".seomachine" / "quarantine" / "v3" / f"{stamp}-{run_id}"
    objects_root = run_root / "objects"
    events_root = run_root / "events"
    objects_root.mkdir(parents=True, exist_ok=False)
    events_root.mkdir(parents=True, exist_ok=False)
    rows = [
        _base_row(candidate, index=index, root=root, run_root=run_root)
        for index, candidate in enumerate(candidates, start=1)
    ]
    base_payload: dict[str, object] = {
        "schema": QUARANTINE_BASE_SCHEMA,
        "run_id": run_id,
        "created_at": format_timestamp(now),
        "delete_after": format_timestamp(now + timedelta(days=quarantine_days)),
        "artifacts": rows,
    }
    base_path = run_root / "base.json"
    atomic_write_canonical_json(
        base_path,
        base_payload,
        max_bytes=GOVERNANCE_JSON_MAX_BYTES,
        field="quarantine base inventory",
        replace=False,
    )
    transaction = _load_transaction(base_path, root=root)
    _append_event(transaction, "transaction_started")
    return _reload_transaction(run_root, root=root)


def _move_row_v3(
    row: dict[str, object],
    *,
    index: int,
    transaction: _Transaction,
    root: Path,
) -> None:
    source = resolve_relative(root, row["original_path"])
    target = resolve_relative(root, row["quarantine_path"])
    _verify_file(source, row, label="retention candidate")
    target.parent.mkdir(parents=True, exist_ok=True)
    _append_event(transaction, "move_intent", artifact_index=index)
    _link_no_clobber(source, target)
    _verify_file(target, row, label="quarantine target")
    source.unlink()
    _append_event(
        _reload_transaction(transaction.run_root, root=root),
        "move_complete",
        artifact_index=index,
    )


def _reconcile_quarantine_row_v3(
    row: dict[str, object],
    *,
    index: int,
    transaction: _Transaction,
    root: Path,
) -> None:
    if row.get("status") == "quarantined":
        return
    source = resolve_relative(root, row["original_path"])
    target = resolve_relative(root, row["quarantine_path"])
    source_exists = source.is_file()
    target_exists = target.is_file()
    if source_exists and target_exists:
        _verify_file(source, row, label="retention source")
        _verify_file(target, row, label="quarantine target")
        if not _same_file(source, target):
            raise ValueError("retention source was recreated after quarantine")
        source.unlink()
        _append_event(transaction, "move_complete", artifact_index=index)
    elif source_exists:
        _move_row_v3(row, index=index, transaction=transaction, root=root)
    elif target_exists:
        _verify_file(target, row, label="quarantine target")
        _append_event(transaction, "move_complete", artifact_index=index)
    else:
        raise ValueError("retention source and quarantine target are both missing")


def _restore_row_v3(
    row: dict[str, object],
    *,
    index: int,
    transaction: _Transaction,
    root: Path,
) -> Path:
    source = resolve_relative(root, row.get("quarantine_path"))
    destination = resolve_relative(root, row.get("original_path"))
    if destination.exists() and not source.exists():
        _verify_file(destination, row, label="restored artifact")
        _append_event(transaction, "restore_complete", artifact_index=index)
        return destination
    _verify_file(source, row, label="quarantined artifact")
    if destination.exists():
        raise ValueError(f"restore target already exists: {row['original_path']}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    _append_event(transaction, "restore_intent", artifact_index=index)
    _link_no_clobber(source, destination)
    _verify_file(destination, row, label="restored artifact")
    source.unlink()
    _append_event(
        _reload_transaction(transaction.run_root, root=root),
        "restore_complete",
        artifact_index=index,
    )
    return destination


def _purge_row_v3(
    row: dict[str, object],
    *,
    index: int,
    artifact: Path,
    transaction: _Transaction,
    root: Path,
) -> None:
    _verify_file(artifact, row, label="quarantined artifact")
    _append_event(transaction, "purge_intent", artifact_index=index)
    artifact.unlink()
    _append_event(
        _reload_transaction(transaction.run_root, root=root),
        "purge_complete",
        artifact_index=index,
    )


def _resume_restore_v3(transaction: _Transaction, *, root: Path) -> None:
    for index, row in enumerate(_artifact_rows(transaction.payload), start=1):
        if row.get("status") == "restored":
            continue
        transaction = _reload_transaction(transaction.run_root, root=root)
        source = resolve_relative(root, row.get("quarantine_path"))
        destination = resolve_relative(root, row.get("original_path"))
        source_exists = source.is_file()
        destination_exists = destination.is_file()
        if source_exists and destination_exists:
            _verify_file(source, row, label="quarantined artifact")
            _verify_file(destination, row, label="restored artifact")
            if not _same_file(source, destination):
                raise ValueError("restore target was recreated during recovery")
            source.unlink()
            _append_event(transaction, "restore_complete", artifact_index=index)
        elif source_exists:
            _restore_row_v3(row, index=index, transaction=transaction, root=root)
        elif destination_exists:
            _verify_file(destination, row, label="restored artifact")
            _append_event(transaction, "restore_complete", artifact_index=index)
        else:
            raise ValueError("quarantine source and restore target are both missing")
    transaction = _reload_transaction(transaction.run_root, root=root)
    _append_event(transaction, "transaction_restored")
    transaction = _reload_transaction(transaction.run_root, root=root)
    _compact_transaction(transaction, root=root, status="restored")


def _resume_purge_v3(transaction: _Transaction, *, root: Path) -> None:
    purge_all = _has_event(transaction, "purge_started")
    for index, row in enumerate(_artifact_rows(transaction.payload), start=1):
        status = row.get("status")
        if status == "purged" or status == "restored":
            continue
        if status != "purging" and not purge_all:
            continue
        transaction = _reload_transaction(transaction.run_root, root=root)
        artifact = resolve_relative(root, row.get("quarantine_path"))
        if artifact.is_file():
            _verify_file(artifact, row, label="quarantined artifact")
            if status != "purging":
                _append_event(transaction, "purge_intent", artifact_index=index)
                transaction = _reload_transaction(transaction.run_root, root=root)
            artifact.unlink()
        elif status != "purging":
            raise ValueError("quarantined artifact is missing without purge intent")
        _append_event(transaction, "purge_complete", artifact_index=index)
    transaction = _reload_transaction(transaction.run_root, root=root)
    if all(row.get("status") in {"purged", "restored"} for row in _artifact_rows(transaction.payload)):
        _append_event(transaction, "transaction_purged")
        transaction = _reload_transaction(transaction.run_root, root=root)
        _compact_transaction(transaction, root=root, status="purged")
    else:
        _compact_transaction(transaction, root=root, status="complete")


def _compact_transaction(
    transaction: _Transaction,
    *,
    root: Path,
    status: str,
) -> None:
    if status not in TERMINAL_STATUSES:
        raise ValueError("terminal retention status is invalid")
    payload = _state_payload(transaction, status=status, compacted=True)
    atomic_write_canonical_json(
        transaction.manifest_path,
        payload,
        max_bytes=GOVERNANCE_JSON_MAX_BYTES,
        field="quarantine manifest",
    )
    persisted = _load_json(
        transaction.manifest_path,
        field="quarantine manifest",
        max_bytes=GOVERNANCE_JSON_MAX_BYTES,
    )
    if persisted != payload:
        raise ValueError("quarantine manifest compaction verification failed")
    _remove_event_journal(transaction.events_path)
    if transaction.base_path is not None:
        transaction.base_path.unlink(missing_ok=True)


def _append_event(
    transaction: _Transaction,
    event: str,
    *,
    artifact_index: int | None = None,
) -> None:
    if transaction.events_path is None:
        raise ValueError("compacted retention transaction cannot append journal events")
    if _EVENT_NAME_RE.fullmatch(event) is None:
        raise ValueError("retention event name is invalid")
    sequence = transaction.event_count + 1
    payload: dict[str, object] = {
        "schema": QUARANTINE_EVENT_SCHEMA,
        "run_id": transaction.payload["run_id"],
        "sequence": sequence,
        "event": event,
        "created_at": format_timestamp(datetime.now(timezone.utc)),
        "previous_event_sha256": transaction.last_event_sha256,
    }
    if artifact_index is not None:
        payload["artifact_index"] = artifact_index
    existing_bytes = _journal_bytes(transaction.events_path)
    encoded = bounded_canonical_json_bytes(
        payload,
        max_bytes=RETENTION_JOURNAL_MAX_BYTES - existing_bytes,
    )
    name = f"{sequence:06d}-{event}.json"
    atomic_write_canonical_json(
        transaction.events_path / name,
        payload,
        max_bytes=len(encoded),
        field="retention journal event",
        replace=False,
    )


def _ensure_open_journal(transaction: _Transaction, *, root: Path) -> _Transaction:
    if transaction.events_path is not None:
        return transaction
    if transaction.legacy:
        raise ValueError("legacy retention transaction cannot use v3 journal")
    base_path = transaction.run_root / "base.json"
    events_path = transaction.run_root / "events"
    if not base_path.exists():
        base_payload = {
            "schema": QUARANTINE_BASE_SCHEMA,
            "run_id": transaction.payload["run_id"],
            "created_at": transaction.payload["created_at"],
            "delete_after": transaction.payload["delete_after"],
            "artifacts": [
                {
                    key: row[key]
                    for key in ("original_path", "quarantine_path", "sha256", "bytes")
                }
                for row in _artifact_rows(transaction.payload)
            ],
        }
        atomic_write_canonical_json(
            base_path,
            base_payload,
            max_bytes=GOVERNANCE_JSON_MAX_BYTES,
            field="quarantine base inventory",
            replace=False,
        )
    events_path.mkdir(exist_ok=True)
    reopened = _reload_transaction(transaction.run_root, root=root)
    if reopened.event_count == 0:
        _append_event(reopened, "transaction_started")
        for index, row in enumerate(_artifact_rows(transaction.payload), start=1):
            status = row.get("status")
            reopened = _reload_transaction(transaction.run_root, root=root)
            if status == "quarantined":
                _append_event(reopened, "move_complete", artifact_index=index)
            elif status == "restored":
                _append_event(reopened, "restore_complete", artifact_index=index)
            elif status == "purged":
                _append_event(reopened, "purge_complete", artifact_index=index)
        reopened = _reload_transaction(transaction.run_root, root=root)
        terminal = {
            "complete": "transaction_complete",
            "restored": "transaction_restored",
            "purged": "transaction_purged",
        }.get(str(transaction.payload.get("status")))
        if terminal is not None:
            _append_event(reopened, terminal)
    return _reload_transaction(transaction.run_root, root=root)


def _open_operation(transaction: _Transaction) -> str:
    rows = _artifact_rows(transaction.payload)
    if transaction.payload.get("status") == "purging" or any(
        row.get("status") == "purging" for row in rows
    ):
        return "purge"
    if transaction.payload.get("status") == "restoring" or any(
        row.get("status") == "restoring" for row in rows
    ):
        return "restore"
    if _has_event(transaction, "purge_started"):
        return "purge"
    if _has_event(transaction, "restore_started"):
        return "restore"
    return "move"


def _has_event(transaction: _Transaction, event: str) -> bool:
    events_path = transaction.events_path
    if events_path is None or not events_path.is_dir():
        return False
    for event_path in events_path.glob("*.json"):
        payload = parse_json_object(
            read_bounded(
                event_path,
                max_bytes=RETENTION_JOURNAL_MAX_BYTES,
                field="retention journal event",
            ),
            field="retention journal event",
        )
        if payload.get("event") == event:
            return True
    return False


