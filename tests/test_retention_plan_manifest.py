from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from data_sources.modules.artifact_runtime.content_store import write_context_trace
from data_sources.modules.artifact_runtime.retention import (
    RETENTION_PLAN_SCHEMA,
    apply_retention,
    persist_retention_plan,
    plan_retention,
)
from data_sources.modules.artifact_runtime import retention_plan_manifests
from data_sources.modules.bounded_io import canonical_json_bytes
from tools import prune_artifacts


NOW = datetime(2026, 9, 14, 12, 0, tzinfo=timezone.utc)


def _orphan(root: Path, name: str = "orphan.json") -> Path:
    pointer = root / "research" / name
    record = write_context_trace(
        pointer,
        {"schema": "simpro-test-context-trace/v1", "value": name},
        workspace_root=root,
        generated_at=NOW,
    )
    pointer.unlink()
    source = root / str(record["object"]["path"])
    old = (NOW - timedelta(days=91)).timestamp()
    os.utime(source, (old, old))
    return source


def test_persisted_retention_plan_is_unique_canonical_and_workspace_relative(
    tmp_path: Path,
) -> None:
    source = _orphan(tmp_path)
    plan = plan_retention(tmp_path, now=NOW, research_retention_days=90)

    first = persist_retention_plan(plan, workspace_root=tmp_path)
    second = persist_retention_plan(plan, workspace_root=tmp_path)

    assert first != second
    assert first.name == second.name == "manifest.json"
    assert first.parent.name.startswith("20260914T120000Z-")
    assert second.parent.name.startswith("20260914T120000Z-")
    payload = json.loads(first.read_text(encoding="utf-8"))
    assert payload == {
        "schema": RETENTION_PLAN_SCHEMA,
        "run_id": first.parent.name.rsplit("-", 1)[1],
        "evaluated_at": "2026-09-14T12:00:00Z",
        "policy": {"research_retention_days": 90},
        "candidate_count": 1,
        "candidate_bytes": source.stat().st_size,
        "candidates": [
            {
                "path": source.relative_to(tmp_path).as_posix(),
                "sha256": plan.candidates[0].sha256,
                "bytes": source.stat().st_size,
                "age_days": 91,
            }
        ],
    }
    assert first.read_bytes() == canonical_json_bytes(payload)
    assert str(tmp_path) not in first.read_text(encoding="utf-8")


def test_apply_accepts_persisted_plan_and_rechecks_references(tmp_path: Path) -> None:
    source = _orphan(tmp_path)
    plan = plan_retention(tmp_path, now=NOW)
    manifest = persist_retention_plan(plan, workspace_root=tmp_path)
    pointer = tmp_path / "research" / "recreated.json"
    pointer.write_text(
        json.dumps(
            {
                "schema": "simpro-context-trace-pointer/v1",
                "trace_schema": "simpro-test-context-trace/v1",
                "generated_at": "2026-09-14T12:00:00Z",
                "object": {
                    "path": source.relative_to(tmp_path).as_posix(),
                    "sha256": plan.candidates[0].sha256,
                    "bytes": source.stat().st_size,
                },
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="became referenced"):
        apply_retention(manifest, workspace_root=tmp_path, now=NOW)

    assert source.is_file()


def test_apply_accepts_persisted_plan_on_success(tmp_path: Path) -> None:
    source = _orphan(tmp_path)
    plan = plan_retention(tmp_path, now=NOW)
    plan_manifest = persist_retention_plan(plan, workspace_root=tmp_path)

    quarantine_manifest = apply_retention(
        plan_manifest,
        workspace_root=tmp_path,
        now=NOW,
    )

    assert not source.exists()
    assert json.loads(quarantine_manifest.read_text(encoding="utf-8"))["status"] == "complete"


def test_apply_rejects_tampered_plan_manifest(tmp_path: Path) -> None:
    _orphan(tmp_path)
    plan = plan_retention(tmp_path, now=NOW)
    manifest = persist_retention_plan(plan, workspace_root=tmp_path)
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    payload["unexpected"] = True
    manifest.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ValueError, match="retention plan manifest is invalid"):
        apply_retention(manifest, workspace_root=tmp_path, now=NOW)


def test_plan_manifest_write_fails_before_exceeding_json_limit(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _orphan(tmp_path)
    plan = plan_retention(tmp_path, now=NOW)
    monkeypatch.setattr(retention_plan_manifests, "JSON_MAX_BYTES", 128)

    with pytest.raises(ValueError, match="retention plan exceeds 128 bytes"):
        persist_retention_plan(plan, workspace_root=tmp_path)

    plan_root = tmp_path / ".seomachine" / "retention-plans" / "v1"
    assert not list(plan_root.rglob("manifest.json"))


def test_dry_run_cli_persists_plan_and_prints_only_compact_summary(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    source = _orphan(tmp_path)
    monkeypatch.setattr(prune_artifacts, "_tracked_paths", lambda _root: set())

    assert prune_artifacts.main(["--workspace-root", str(tmp_path)]) == 0

    output = json.loads(capsys.readouterr().out)
    assert output["status"] == "planned"
    assert output["apply"] is False
    assert output["candidate_count"] == 1
    assert output["candidate_bytes"] == source.stat().st_size
    assert "candidates" not in output
    manifest = tmp_path / output["manifest"]
    assert manifest.is_file()
    assert json.loads(manifest.read_text(encoding="utf-8"))["candidate_count"] == 1


def test_empty_dry_run_still_persists_a_plan_manifest(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(prune_artifacts, "_tracked_paths", lambda _root: set())

    assert prune_artifacts.main(["--workspace-root", str(tmp_path)]) == 0

    output = json.loads(capsys.readouterr().out)
    assert output["candidate_count"] == 0
    assert output["candidate_bytes"] == 0
    assert (tmp_path / output["manifest"]).is_file()
