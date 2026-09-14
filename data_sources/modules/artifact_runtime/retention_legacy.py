"""Legacy mutable quarantine manifest compatibility."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from ..bounded_io import atomic_write_canonical_json
from .limits import GOVERNANCE_JSON_MAX_BYTES
from .retention_planning import parse_timestamp, resolve_relative
from .retention_store import (
    LEGACY_QUARANTINE_SCHEMA,
    LEGACY_QUARANTINE_SCHEMA_V2,
    TERMINAL_STATUSES,
    _artifact_rows,
    _link_no_clobber,
    _load_json,
    _same_file,
    _validate_manifest_payload,
    _verify_file,
)
def _resume_legacy_v2(manifest_path: Path, *, root: Path) -> Path:
    manifest = _load_legacy_manifest(manifest_path, root=root)
    if manifest.get("schema") != LEGACY_QUARANTINE_SCHEMA_V2:
        raise ValueError("only v2 quarantine transactions can be resumed")
    if manifest.get("status") in TERMINAL_STATUSES:
        return manifest_path
    for row in _artifact_rows(manifest):
        _reconcile_legacy_row(row, manifest_path=manifest_path, manifest=manifest, root=root)
    manifest["status"] = "complete"
    _write_legacy_manifest(manifest_path, manifest)
    return manifest_path


def _restore_legacy(manifest_path: Path, *, root: Path) -> list[Path]:
    manifest = _load_legacy_manifest(manifest_path, root=root)
    if manifest.get("schema") == LEGACY_QUARANTINE_SCHEMA_V2 and manifest.get("status") not in {
        "complete",
        "restored",
    }:
        raise ValueError("incomplete quarantine must be resumed before restore")
    restored: list[Path] = []
    for row in _artifact_rows(manifest):
        if row.get("status") == "restored":
            continue
        source = resolve_relative(root, row.get("quarantine_path"))
        destination = resolve_relative(root, row.get("original_path"))
        _verify_file(source, row, label="quarantined artifact")
        if destination.exists():
            raise ValueError(f"restore target already exists: {row['original_path']}")
        destination.parent.mkdir(parents=True, exist_ok=True)
        row["status"] = "restoring"
        _write_legacy_manifest(manifest_path, manifest)
        _link_no_clobber(source, destination)
        source.unlink()
        row["status"] = "restored"
        _write_legacy_manifest(manifest_path, manifest)
        restored.append(destination)
    manifest["status"] = "restored"
    _write_legacy_manifest(manifest_path, manifest)
    return restored


def _purge_legacy(
    manifest_path: Path,
    *,
    root: Path,
    now: datetime,
    apply: bool,
) -> list[Path]:
    manifest = _load_legacy_manifest(manifest_path, root=root)
    if manifest.get("status") != "complete":
        return []
    if parse_timestamp(manifest.get("delete_after")) > now:
        return []
    eligible: list[Path] = []
    rows = []
    for row in _artifact_rows(manifest):
        if row.get("status") != "quarantined":
            continue
        artifact = resolve_relative(root, row.get("quarantine_path"))
        _verify_file(artifact, row, label="quarantined artifact")
        eligible.append(artifact)
        rows.append((artifact, row))
    if apply:
        for artifact, row in rows:
            row["status"] = "purging"
            _write_legacy_manifest(manifest_path, manifest)
            artifact.unlink()
            row["status"] = "purged"
            _write_legacy_manifest(manifest_path, manifest)
        manifest["status"] = "purged"
        _write_legacy_manifest(manifest_path, manifest)
    return eligible


def _load_legacy_manifest(path: Path, *, root: Path) -> dict[str, object]:
    resolved = path.resolve(strict=True)
    resolved.relative_to(root)
    value = _load_json(
        resolved,
        field="quarantine manifest",
        max_bytes=GOVERNANCE_JSON_MAX_BYTES,
    )
    _validate_manifest_payload(value)
    if value.get("schema") not in {LEGACY_QUARANTINE_SCHEMA, LEGACY_QUARANTINE_SCHEMA_V2}:
        raise ValueError("quarantine manifest is invalid")
    return value


def _write_legacy_manifest(path: Path, manifest: dict[str, object]) -> None:
    atomic_write_canonical_json(
        path,
        manifest,
        max_bytes=GOVERNANCE_JSON_MAX_BYTES,
        field="quarantine manifest",
    )


def _reconcile_legacy_row(
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
        if row.get("status") == "quarantined" or not _same_file(source, target):
            raise ValueError("retention source was recreated after quarantine")
        row["status"] = "unlinking"
        _write_legacy_manifest(manifest_path, manifest)
        source.unlink()
    elif source_exists:
        if row.get("status") == "quarantined":
            raise ValueError("quarantine target disappeared and source was recreated")
        _move_legacy_row(row, manifest_path=manifest_path, manifest=manifest, root=root)
        return
    elif target_exists:
        _verify_file(target, row, label="quarantine target")
    else:
        raise ValueError("retention source and quarantine target are both missing")
    row["status"] = "quarantined"
    _write_legacy_manifest(manifest_path, manifest)


def _move_legacy_row(
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
    _write_legacy_manifest(manifest_path, manifest)
    _link_no_clobber(source, target)
    row["status"] = "linked"
    _write_legacy_manifest(manifest_path, manifest)
    row["status"] = "unlinking"
    _write_legacy_manifest(manifest_path, manifest)
    source.unlink()
    row["status"] = "quarantined"
    _write_legacy_manifest(manifest_path, manifest)


