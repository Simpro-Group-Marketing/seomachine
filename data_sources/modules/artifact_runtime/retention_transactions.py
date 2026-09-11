"""Locked, crash-resumable quarantine transactions."""

from __future__ import annotations

import os
from datetime import datetime, timedelta
from pathlib import Path
from uuid import uuid4

from ..blog_assembly_contract import atomic_write_json, load_json_object_snapshot
from .retention_planning import (
    RetentionCandidate,
    RetentionPlan,
    file_sha256,
    format_timestamp,
    parse_timestamp,
    referenced_objects,
    require_aware,
    resolve_relative,
    verify_candidate,
)
from .workspace_lock import artifact_workspace_lock


QUARANTINE_SCHEMA = "simpro-artifact-quarantine/v2"
LEGACY_QUARANTINE_SCHEMA = "simpro-artifact-quarantine/v1"
DEFAULT_QUARANTINE_DAYS = 14
TERMINAL_STATUSES = {"complete", "restored", "purged"}


def apply_retention(
    plan: RetentionPlan,
    *,
    workspace_root: str | Path,
    now: datetime,
    quarantine_days: int = DEFAULT_QUARANTINE_DAYS,
) -> Path:
    """Move verified objects through an exclusive, resumable transaction."""
    root = Path(workspace_root).resolve(strict=True)
    if root != plan.workspace_root or quarantine_days < 1:
        raise ValueError("retention plan does not match the workspace or policy")
    current = require_aware(now)
    with artifact_workspace_lock(root):
        _reject_incomplete_transactions(root)
        current_references = referenced_objects(root)
        for candidate in plan.candidates:
            if candidate.path in current_references:
                relative = candidate.path.relative_to(root).as_posix()
                raise ValueError(f"retention candidate became referenced: {relative}")
            verify_candidate(candidate, root=root)
        manifest_path, payload = _create_transaction(
            root,
            candidates=plan.candidates,
            now=current,
            quarantine_days=quarantine_days,
        )
        for row in payload["artifacts"]:
            _move_row(row, manifest_path=manifest_path, manifest=payload, root=root)
        payload["status"] = "complete"
        _persist(manifest_path, payload)
        return manifest_path


def resume_retention(
    manifest_path: str | Path,
    *,
    workspace_root: str | Path,
) -> Path:
    """Reconcile and complete one interrupted v2 quarantine transaction."""
    root = Path(workspace_root).resolve(strict=True)
    path = _resolve_manifest(manifest_path, root=root)
    with artifact_workspace_lock(root):
        manifest = _load_manifest(path, root=root)
        if manifest.get("schema") != QUARANTINE_SCHEMA:
            raise ValueError("only v2 quarantine transactions can be resumed")
        if manifest.get("status") in TERMINAL_STATUSES:
            return path
        for row in manifest["artifacts"]:
            _reconcile_row(row, manifest_path=path, manifest=manifest, root=root)
        manifest["status"] = "complete"
        _persist(path, manifest)
        return path


def restore_quarantine(
    manifest_path: str | Path,
    *,
    workspace_root: str | Path,
) -> list[Path]:
    """Restore every intact quarantined artifact without replacement."""
    root = Path(workspace_root).resolve(strict=True)
    path = _resolve_manifest(manifest_path, root=root)
    with artifact_workspace_lock(root):
        manifest = _load_manifest(path, root=root)
        if manifest.get("schema") == QUARANTINE_SCHEMA and manifest.get("status") not in {
            "complete",
            "restored",
        }:
            raise ValueError("incomplete quarantine must be resumed before restore")
        restored: list[Path] = []
        for row in manifest["artifacts"]:
            if row.get("status") == "restored":
                continue
            source = resolve_relative(root, row.get("quarantine_path"))
            destination = resolve_relative(root, row.get("original_path"))
            _verify_file(source, row, label="quarantined artifact")
            if destination.exists():
                raise ValueError(f"restore target already exists: {row['original_path']}")
            destination.parent.mkdir(parents=True, exist_ok=True)
            row["status"] = "restoring"
            _persist(path, manifest)
            _link_no_clobber(source, destination)
            source.unlink()
            row["status"] = "restored"
            _persist(path, manifest)
            restored.append(destination)
        manifest["status"] = "restored"
        _persist(path, manifest)
        return restored


def purge_expired_quarantine(
    workspace_root: str | Path,
    *,
    now: datetime,
    apply: bool,
) -> list[Path]:
    """Report or delete hash-verified artifacts after their grace period."""
    root = Path(workspace_root).resolve(strict=True)
    current = require_aware(now)
    with artifact_workspace_lock(root):
        eligible: list[Path] = []
        for manifest_path in _manifest_paths(root):
            manifest = _load_manifest(manifest_path, root=root)
            if manifest.get("status") != "complete":
                continue
            if parse_timestamp(manifest.get("delete_after")) > current:
                continue
            rows: list[tuple[Path, dict[str, object]]] = []
            for row in manifest["artifacts"]:
                if row.get("status") != "quarantined":
                    continue
                artifact = resolve_relative(root, row.get("quarantine_path"))
                _verify_file(artifact, row, label="quarantined artifact")
                eligible.append(artifact)
                rows.append((artifact, row))
            if apply:
                for artifact, row in rows:
                    row["status"] = "purging"
                    _persist(manifest_path, manifest)
                    artifact.unlink()
                    row["status"] = "purged"
                    _persist(manifest_path, manifest)
                manifest["status"] = "purged"
                _persist(manifest_path, manifest)
        return eligible


def _create_transaction(
    root: Path,
    *,
    candidates: tuple[RetentionCandidate, ...],
    now: datetime,
    quarantine_days: int,
) -> tuple[Path, dict[str, object]]:
    run_id = uuid4().hex
    stamp = now.strftime("%Y%m%dT%H%M%SZ")
    run_root = root / ".seomachine" / "quarantine" / "v2" / f"{stamp}-{run_id}"
    run_root.mkdir(parents=True, exist_ok=False)
    rows = [
        _manifest_row(candidate, index=index, root=root, run_root=run_root)
        for index, candidate in enumerate(candidates, start=1)
    ]
    payload: dict[str, object] = {
        "schema": QUARANTINE_SCHEMA,
        "run_id": run_id,
        "status": "moving",
        "created_at": format_timestamp(now),
        "delete_after": format_timestamp(now + timedelta(days=quarantine_days)),
        "artifacts": rows,
    }
    manifest_path = run_root / "manifest.json"
    _persist(manifest_path, payload)
    return manifest_path, payload


def _move_row(
    row: dict[str, object],
    *,
    manifest_path: Path,
    manifest: dict[str, object],
    root: Path,
) -> None:
    source = resolve_relative(root, row["original_path"])
    target = resolve_relative(root, row["quarantine_path"])
    _verify_file(source, row, label="retention candidate")
    target.parent.mkdir(parents=True, exist_ok=True)
    row["status"] = "linking"
    _persist(manifest_path, manifest)
    _link_no_clobber(source, target)
    row["status"] = "linked"
    _persist(manifest_path, manifest)
    row["status"] = "unlinking"
    _persist(manifest_path, manifest)
    source.unlink()
    row["status"] = "quarantined"
    _persist(manifest_path, manifest)


def _reconcile_row(
    row: dict[str, object],
    *,
    manifest_path: Path,
    manifest: dict[str, object],
    root: Path,
) -> None:
    source = resolve_relative(root, row["original_path"])
    target = resolve_relative(root, row["quarantine_path"])
    source_exists = source.is_file()
    target_exists = target.is_file()
    if source_exists and target_exists:
        _verify_file(source, row, label="retention source")
        _verify_file(target, row, label="quarantine target")
        if row.get("status") == "quarantined" or not os.path.samefile(source, target):
            raise ValueError("retention source was recreated after quarantine")
        row["status"] = "unlinking"
        _persist(manifest_path, manifest)
        source.unlink()
    elif source_exists:
        if row.get("status") == "quarantined":
            raise ValueError("quarantine target disappeared and source was recreated")
        _move_row(row, manifest_path=manifest_path, manifest=manifest, root=root)
        return
    elif target_exists:
        _verify_file(target, row, label="quarantine target")
    else:
        raise ValueError("retention source and quarantine target are both missing")
    row["status"] = "quarantined"
    _persist(manifest_path, manifest)


def _manifest_row(
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
        "status": "pending",
    }


def _reject_incomplete_transactions(root: Path) -> None:
    for path in _manifest_paths(root, versions=("v2",)):
        manifest = _load_manifest(path, root=root)
        if manifest.get("status") not in TERMINAL_STATUSES:
            raise ValueError(f"incomplete retention transaction requires resume: {path}")


def _manifest_paths(root: Path, *, versions: tuple[str, ...] = ("v1", "v2")) -> list[Path]:
    base = root / ".seomachine" / "quarantine"
    paths: list[Path] = []
    for version in versions:
        version_root = base / version
        if version_root.is_dir():
            paths.extend(version_root.glob("*/manifest.json"))
    return sorted(paths)


def _load_manifest(path: Path, *, root: Path) -> dict[str, object]:
    resolved = path.resolve(strict=True)
    resolved.relative_to(root)
    value = load_json_object_snapshot(resolved, field="quarantine manifest").payload
    schema = value.get("schema")
    if schema not in {QUARANTINE_SCHEMA, LEGACY_QUARANTINE_SCHEMA}:
        raise ValueError("quarantine manifest is invalid")
    artifacts = value.get("artifacts")
    if not isinstance(artifacts, list) or not all(isinstance(row, dict) for row in artifacts):
        raise ValueError("quarantine artifact inventory is invalid")
    if schema == QUARANTINE_SCHEMA and not isinstance(value.get("run_id"), str):
        raise ValueError("quarantine run_id is invalid")
    for row in artifacts:
        _validate_row(row)
    return value


def _validate_row(row: dict[str, object]) -> None:
    if set(row) != {"original_path", "quarantine_path", "sha256", "bytes", "status"}:
        raise ValueError("quarantine artifact row is invalid")
    if not isinstance(row.get("sha256"), str) or len(str(row["sha256"])) != 64:
        raise ValueError("quarantine artifact hash is invalid")
    byte_count = row.get("bytes")
    if isinstance(byte_count, bool) or not isinstance(byte_count, int) or byte_count < 0:
        raise ValueError("quarantine artifact byte count is invalid")


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


def _resolve_manifest(path: str | Path, *, root: Path) -> Path:
    candidate = Path(path)
    if not candidate.is_absolute():
        candidate = root / candidate
    resolved = candidate.resolve(strict=True)
    resolved.relative_to(root)
    return resolved


def _persist(path: Path, manifest: dict[str, object]) -> None:
    atomic_write_json(path, manifest)
