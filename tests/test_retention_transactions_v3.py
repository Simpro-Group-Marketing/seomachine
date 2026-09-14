from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

from data_sources.modules.artifact_runtime.content_store import write_context_trace
from data_sources.modules.artifact_runtime.retention import (
    QUARANTINE_SCHEMA,
    apply_retention,
    plan_retention,
    resume_retention,
)
from data_sources.modules.bounded_io import canonical_json_bytes, canonical_json_sha256


NOW = datetime(2026, 9, 10, 12, 0, tzinfo=timezone.utc)


def _write_trace(root: Path, name: str, value: str) -> tuple[Path, dict[str, object]]:
    pointer = root / "research" / name
    result = write_context_trace(
        pointer,
        {
            "schema": "simpro-test-context-trace/v1",
            "searches": [{"query": value, "resource_ids": ["res-1"]}],
        },
        workspace_root=root,
        generated_at=NOW,
    )
    return pointer, result


def _write_canonical(path: Path, payload: dict[str, object]) -> None:
    path.write_bytes(canonical_json_bytes(payload))


def _canonical_sha256(payload: dict[str, object]) -> str:
    return canonical_json_sha256(payload)


def test_resume_v3_retention_completes_after_move_intent(
    tmp_path: Path,
) -> None:
    pointer, record = _write_trace(tmp_path, "orphan.json", "orphan")
    pointer.unlink()
    source = tmp_path / str(record["object"]["path"])
    digest = str(record["object"]["sha256"])
    run_root = tmp_path / ".seomachine" / "quarantine" / "v3" / "run-test"
    target = run_root / "objects" / "000001.blob"
    events = run_root / "events"
    target.parent.mkdir(parents=True)
    events.mkdir()
    os.link(source, target)
    base = {
        "schema": "simpro-artifact-quarantine-base/v3",
        "run_id": "run-test",
        "created_at": "2026-09-10T12:00:00Z",
        "delete_after": "2026-09-24T12:00:00Z",
        "artifacts": [
            {
                "original_path": source.relative_to(tmp_path).as_posix(),
                "quarantine_path": target.relative_to(tmp_path).as_posix(),
                "sha256": digest,
                "bytes": source.stat().st_size,
            }
        ],
    }
    _write_canonical(run_root / "base.json", base)
    first = {
        "schema": "simpro-artifact-quarantine-event/v1",
        "run_id": "run-test",
        "sequence": 1,
        "event": "transaction_started",
        "created_at": "2026-09-10T12:00:00Z",
        "previous_event_sha256": "",
    }
    _write_canonical(events / "000001-transaction_started.json", first)
    second = {
        "schema": "simpro-artifact-quarantine-event/v1",
        "run_id": "run-test",
        "sequence": 2,
        "event": "move_intent",
        "created_at": "2026-09-10T12:00:01Z",
        "previous_event_sha256": _canonical_sha256(first),
        "artifact_index": 1,
    }
    _write_canonical(events / "000002-move_intent.json", second)

    resumed = resume_retention(run_root, workspace_root=tmp_path)

    assert resumed == run_root / "manifest.json"
    assert not source.exists()
    assert target.is_file()
    persisted = json.loads(resumed.read_text(encoding="utf-8"))
    assert persisted["schema"] == QUARANTINE_SCHEMA
    assert persisted["status"] == "complete"
    assert persisted["artifacts"][0]["status"] == "quarantined"
    assert not (run_root / "events").exists()


def test_resume_v3_purge_accepts_missing_file_with_durable_intent(
    tmp_path: Path,
) -> None:
    pointer, record = _write_trace(tmp_path, "orphan.json", "orphan")
    pointer.unlink()
    source = tmp_path / str(record["object"]["path"])
    old = (NOW - timedelta(days=91)).timestamp()
    os.utime(source, (old, old))
    manifest = apply_retention(
        plan_retention(tmp_path, now=NOW),
        workspace_root=tmp_path,
        now=NOW,
    )
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    row = payload["artifacts"][0]
    quarantined = tmp_path / row["quarantine_path"]
    run_root = manifest.parent
    manifest.unlink()
    base = {
        "schema": "simpro-artifact-quarantine-base/v3",
        "run_id": payload["run_id"],
        "created_at": payload["created_at"],
        "delete_after": payload["delete_after"],
        "artifacts": [
            {
                key: row[key]
                for key in ("original_path", "quarantine_path", "sha256", "bytes")
            }
        ],
    }
    events = run_root / "events"
    events.mkdir()
    _write_canonical(run_root / "base.json", base)
    first = {
        "schema": "simpro-artifact-quarantine-event/v1",
        "run_id": payload["run_id"],
        "sequence": 1,
        "event": "transaction_started",
        "created_at": payload["created_at"],
        "previous_event_sha256": "",
    }
    _write_canonical(events / "000001-transaction_started.json", first)
    second = {
        "schema": "simpro-artifact-quarantine-event/v1",
        "run_id": payload["run_id"],
        "sequence": 2,
        "event": "move_complete",
        "created_at": payload["created_at"],
        "previous_event_sha256": _canonical_sha256(first),
        "artifact_index": 1,
    }
    _write_canonical(events / "000002-move_complete.json", second)
    third = {
        "schema": "simpro-artifact-quarantine-event/v1",
        "run_id": payload["run_id"],
        "sequence": 3,
        "event": "transaction_complete",
        "created_at": payload["created_at"],
        "previous_event_sha256": _canonical_sha256(second),
    }
    _write_canonical(events / "000003-transaction_complete.json", third)
    fourth = {
        "schema": "simpro-artifact-quarantine-event/v1",
        "run_id": payload["run_id"],
        "sequence": 4,
        "event": "purge_intent",
        "created_at": payload["created_at"],
        "previous_event_sha256": _canonical_sha256(third),
        "artifact_index": 1,
    }
    _write_canonical(events / "000004-purge_intent.json", fourth)
    quarantined.unlink()

    resumed = resume_retention(run_root, workspace_root=tmp_path)

    assert json.loads(resumed.read_text(encoding="utf-8"))["status"] == "purged"
