from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from data_sources.modules.artifact_runtime.content_store import (
    resolve_context_trace,
    write_context_trace,
)
from data_sources.modules.artifact_runtime.retention import (
    apply_retention,
    plan_retention,
    purge_expired_quarantine,
    resume_retention,
    restore_quarantine,
)


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


def test_context_trace_store_deduplicates_canonical_payloads(tmp_path: Path) -> None:
    first_pointer, first = _write_trace(tmp_path, "first.json", "dispatch")
    second_pointer, second = _write_trace(tmp_path, "second.json", "dispatch")

    assert first["object"] == second["object"]
    objects = list((tmp_path / "research" / ".objects").rglob("*.json"))
    assert len(objects) == 1
    assert resolve_context_trace(first_pointer, workspace_root=tmp_path) == {
        "schema": "simpro-test-context-trace/v1",
        "searches": [{"query": "dispatch", "resource_ids": ["res-1"]}],
    }
    assert resolve_context_trace(second_pointer, workspace_root=tmp_path) == resolve_context_trace(
        first_pointer,
        workspace_root=tmp_path,
    )


def test_context_trace_resolver_rejects_tampered_blob(tmp_path: Path) -> None:
    pointer, record = _write_trace(tmp_path, "trace.json", "dispatch")
    object_path = tmp_path / str(record["object"]["path"])
    object_path.write_text('{"schema":"tampered"}\n', encoding="utf-8")

    with pytest.raises(ValueError, match="sha256"):
        resolve_context_trace(pointer, workspace_root=tmp_path)


def test_retention_only_selects_old_unreferenced_managed_objects(tmp_path: Path) -> None:
    pinned_pointer, pinned = _write_trace(tmp_path, "pinned.json", "pinned")
    orphan_pointer, orphan = _write_trace(tmp_path, "orphan.json", "orphan")
    orphan_pointer.unlink()
    unknown = tmp_path / "research" / "notes.md"
    unknown.write_text("keep", encoding="utf-8")
    old = (NOW - timedelta(days=91)).timestamp()
    for record in (pinned, orphan):
        os.utime(tmp_path / str(record["object"]["path"]), (old, old))
    os.utime(unknown, (old, old))

    plan = plan_retention(tmp_path, now=NOW, research_retention_days=90)

    assert [item.path for item in plan.candidates] == [
        tmp_path / str(orphan["object"]["path"])
    ]
    assert pinned_pointer.is_file()
    assert unknown.is_file()


def test_retention_rejects_symlink_that_escapes_managed_objects(tmp_path: Path) -> None:
    object_root = tmp_path.joinpath(
        "research", ".objects", "context-traces", "v1", "sha256", "aa"
    )
    object_root.mkdir(parents=True)
    outside = tmp_path.parent / "outside-context-object.json"
    outside.write_text('{"schema":"outside"}\n', encoding="utf-8")
    old = (NOW - timedelta(days=91)).timestamp()
    os.utime(outside, (old, old))
    link = object_root / "escaped.json"
    try:
        link.symlink_to(outside)
    except OSError as error:
        outside.unlink(missing_ok=True)
        pytest.skip(f"symlinks unavailable: {error}")
    try:
        with pytest.raises(ValueError, match="managed object path escapes"):
            plan_retention(tmp_path, now=NOW)
    finally:
        link.unlink(missing_ok=True)
        outside.unlink(missing_ok=True)


def test_retention_quarantine_is_recoverable(tmp_path: Path) -> None:
    pointer, record = _write_trace(tmp_path, "orphan.json", "orphan")
    pointer.unlink()
    source = tmp_path / str(record["object"]["path"])
    old = (NOW - timedelta(days=91)).timestamp()
    os.utime(source, (old, old))
    plan = plan_retention(tmp_path, now=NOW, research_retention_days=90)

    manifest = apply_retention(plan, workspace_root=tmp_path, now=NOW)

    assert not source.exists()
    manifest_payload = json.loads(manifest.read_text(encoding="utf-8"))
    assert manifest_payload["schema"] == "simpro-artifact-quarantine/v2"
    assert manifest_payload["artifacts"][0]["original_path"] == source.relative_to(
        tmp_path
    ).as_posix()

    restored = restore_quarantine(manifest, workspace_root=tmp_path)
    assert restored == [source]
    assert source.is_file()


def test_retention_apply_rejects_object_referenced_after_planning(tmp_path: Path) -> None:
    pointer, record = _write_trace(tmp_path, "orphan.json", "orphan")
    pointer.unlink()
    source = tmp_path / str(record["object"]["path"])
    old = (NOW - timedelta(days=91)).timestamp()
    os.utime(source, (old, old))
    plan = plan_retention(tmp_path, now=NOW, research_retention_days=90)
    pointer.write_text(json.dumps(record), encoding="utf-8")

    with pytest.raises(ValueError, match="became referenced"):
        apply_retention(plan, workspace_root=tmp_path, now=NOW)

    assert source.is_file()


def test_expired_quarantine_is_reported_before_irreversible_purge(tmp_path: Path) -> None:
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

    dry_run = purge_expired_quarantine(
        tmp_path,
        now=NOW + timedelta(days=15),
        apply=False,
    )
    assert len(dry_run) == 1
    assert Path(dry_run[0]).is_file()

    deleted = purge_expired_quarantine(
        tmp_path,
        now=NOW + timedelta(days=15),
        apply=True,
    )
    assert deleted == dry_run
    assert not Path(deleted[0]).exists()
    assert json.loads(manifest.read_text(encoding="utf-8"))["status"] == "purged"


def test_purge_only_updates_rows_that_are_still_quarantined(tmp_path: Path) -> None:
    records = [_write_trace(tmp_path, f"orphan-{index}.json", str(index)) for index in range(2)]
    old = (NOW - timedelta(days=91)).timestamp()
    for pointer, record in records:
        pointer.unlink()
        os.utime(tmp_path / str(record["object"]["path"]), (old, old))
    manifest_path = apply_retention(
        plan_retention(tmp_path, now=NOW),
        workspace_root=tmp_path,
        now=NOW,
    )
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    restored_row = manifest["artifacts"][0]
    restored_source = tmp_path / restored_row["quarantine_path"]
    restored_target = tmp_path / restored_row["original_path"]
    restored_target.parent.mkdir(parents=True, exist_ok=True)
    os.replace(restored_source, restored_target)
    restored_row["status"] = "restored"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    deleted = purge_expired_quarantine(
        tmp_path,
        now=NOW + timedelta(days=15),
        apply=True,
    )

    persisted = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert len(deleted) == 1
    assert [row["status"] for row in persisted["artifacts"]] == ["restored", "purged"]
    assert restored_target.is_file()


def test_retention_runs_in_same_second_use_unique_directories(tmp_path: Path) -> None:
    manifests: list[Path] = []
    for index in range(2):
        pointer, record = _write_trace(tmp_path, f"orphan-{index}.json", str(index))
        pointer.unlink()
        source = tmp_path / str(record["object"]["path"])
        old = (NOW - timedelta(days=91)).timestamp()
        os.utime(source, (old, old))
        manifests.append(
            apply_retention(
                plan_retention(tmp_path, now=NOW),
                workspace_root=tmp_path,
                now=NOW,
            )
        )

    assert manifests[0].parent != manifests[1].parent
    assert all(path.is_file() for path in manifests)


def test_malformed_pointer_candidate_blocks_retention(tmp_path: Path) -> None:
    pointer, record = _write_trace(tmp_path, "orphan.json", "orphan")
    pointer.unlink()
    malformed = tmp_path / "research" / "malformed.json"
    malformed.write_text('{"schema":', encoding="utf-8")
    source = tmp_path / str(record["object"]["path"])
    old = (NOW - timedelta(days=91)).timestamp()
    os.utime(source, (old, old))

    with pytest.raises(ValueError, match="pointer candidate"):
        plan_retention(tmp_path, now=NOW)

    assert source.is_file()


def test_resume_retention_completes_linked_source_and_target_state(
    tmp_path: Path,
) -> None:
    pointer, record = _write_trace(tmp_path, "orphan.json", "orphan")
    pointer.unlink()
    source = tmp_path / str(record["object"]["path"])
    digest = str(record["object"]["sha256"])
    run_root = tmp_path / ".seomachine" / "quarantine" / "v2" / "run-test"
    target = run_root / "objects" / "000001.blob"
    target.parent.mkdir(parents=True)
    os.link(source, target)
    manifest_path = run_root / "manifest.json"
    manifest_path.write_text(
        json.dumps(
            {
                "schema": "simpro-artifact-quarantine/v2",
                "run_id": "run-test",
                "status": "moving",
                "created_at": "2026-09-10T12:00:00Z",
                "delete_after": "2026-09-24T12:00:00Z",
                "artifacts": [
                    {
                        "original_path": source.relative_to(tmp_path).as_posix(),
                        "quarantine_path": target.relative_to(tmp_path).as_posix(),
                        "sha256": digest,
                        "bytes": source.stat().st_size,
                        "status": "linked",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    resumed = resume_retention(manifest_path, workspace_root=tmp_path)

    assert resumed == manifest_path
    assert not source.exists()
    assert target.is_file()
    persisted = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert persisted["status"] == "complete"
    assert persisted["artifacts"][0]["status"] == "quarantined"
