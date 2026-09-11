"""Reachability-safe retention for managed local research objects."""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterable

from ..blog_assembly_contract import atomic_write_json
from .content_store import OBJECT_PREFIX, POINTER_MAX_BYTES, POINTER_SCHEMA


QUARANTINE_SCHEMA = "simpro-artifact-quarantine/v1"
DEFAULT_RESEARCH_RETENTION_DAYS = 90
DEFAULT_QUARANTINE_DAYS = 14


@dataclass(frozen=True, slots=True)
class RetentionCandidate:
    path: Path
    sha256: str
    byte_count: int
    age_days: int


@dataclass(frozen=True, slots=True)
class RetentionPlan:
    workspace_root: Path
    candidates: tuple[RetentionCandidate, ...]
    referenced: tuple[Path, ...]
    evaluated_at: datetime


def plan_retention(
    workspace_root: str | Path,
    *,
    now: datetime,
    research_retention_days: int = DEFAULT_RESEARCH_RETENTION_DAYS,
    tracked_paths: Iterable[str | Path] = (),
) -> RetentionPlan:
    """Return old managed objects that are neither referenced nor tracked."""
    root = Path(workspace_root).resolve()
    current = _require_aware(now)
    if research_retention_days < 1:
        raise ValueError("research_retention_days must be positive")
    referenced = _referenced_objects(root)
    tracked = {_resolve_relative(root, value) for value in tracked_paths}
    object_root = root.joinpath(*OBJECT_PREFIX.parts)
    resolved_object_root = object_root.resolve()
    cutoff = current - timedelta(days=research_retention_days)
    candidates: list[RetentionCandidate] = []
    if object_root.is_dir():
        for path in sorted(object_root.rglob("*.json")):
            resolved = path.resolve(strict=True)
            try:
                resolved.relative_to(resolved_object_root)
            except ValueError as error:
                raise ValueError(f"managed object path escapes its namespace: {path}") from error
            modified = datetime.fromtimestamp(path.stat().st_mtime, timezone.utc)
            if resolved in referenced or resolved in tracked or modified > cutoff:
                continue
            candidates.append(
                RetentionCandidate(
                    path=resolved,
                    sha256=_sha256(resolved),
                    byte_count=resolved.stat().st_size,
                    age_days=(current - modified).days,
                )
            )
    return RetentionPlan(
        workspace_root=root,
        candidates=tuple(candidates),
        referenced=tuple(sorted(referenced)),
        evaluated_at=current,
    )


def apply_retention(
    plan: RetentionPlan,
    *,
    workspace_root: str | Path,
    now: datetime,
    quarantine_days: int = DEFAULT_QUARANTINE_DAYS,
) -> Path:
    """Move planned objects into a recoverable quarantine and persist a manifest."""
    root = Path(workspace_root).resolve()
    if root != plan.workspace_root or quarantine_days < 1:
        raise ValueError("retention plan does not match the workspace or policy")
    current = _require_aware(now)
    current_references = _referenced_objects(root)
    newly_referenced = [
        candidate.path
        for candidate in plan.candidates
        if candidate.path in current_references
    ]
    if newly_referenced:
        relative = newly_referenced[0].relative_to(root).as_posix()
        raise ValueError(f"retention candidate became referenced: {relative}")
    stamp = current.strftime("%Y%m%dT%H%M%SZ")
    run_root = root / ".seomachine" / "quarantine" / "v1" / stamp
    manifest = run_root / "manifest.json"
    artifacts = [
        _manifest_row(candidate, index=index, root=root, run_root=run_root)
        for index, candidate in enumerate(plan.candidates, start=1)
    ]
    payload: dict[str, object] = {
        "schema": QUARANTINE_SCHEMA,
        "status": "moving",
        "created_at": _format_timestamp(current),
        "delete_after": _format_timestamp(current + timedelta(days=quarantine_days)),
        "artifacts": artifacts,
    }
    atomic_write_json(manifest, payload)
    for candidate, row in zip(plan.candidates, artifacts, strict=True):
        _verify_candidate(candidate, root=root)
        target = _resolve_relative(root, row["quarantine_path"])
        target.parent.mkdir(parents=True, exist_ok=True)
        os.replace(candidate.path, target)
        row["status"] = "quarantined"
        atomic_write_json(manifest, payload)
    payload["status"] = "complete"
    atomic_write_json(manifest, payload)
    return manifest


def restore_quarantine(
    manifest_path: str | Path,
    *,
    workspace_root: str | Path,
) -> list[Path]:
    """Restore every intact quarantined artifact to its original path."""
    root = Path(workspace_root).resolve()
    manifest = _load_manifest(manifest_path, root=root)
    restored: list[Path] = []
    for row in manifest["artifacts"]:
        source = _resolve_relative(root, row["quarantine_path"])
        destination = _resolve_relative(root, row["original_path"])
        if destination.exists():
            raise ValueError(f"restore target already exists: {row['original_path']}")
        if _sha256(source) != row["sha256"]:
            raise ValueError(f"quarantined artifact hash mismatch: {row['original_path']}")
        destination.parent.mkdir(parents=True, exist_ok=True)
        os.replace(source, destination)
        row["status"] = "restored"
        restored.append(destination)
    manifest["status"] = "restored"
    atomic_write_json(Path(manifest_path), manifest)
    return restored


def purge_expired_quarantine(
    workspace_root: str | Path,
    *,
    now: datetime,
    apply: bool,
) -> list[Path]:
    """Report or delete intact artifacts whose quarantine grace period elapsed."""
    root = Path(workspace_root).resolve()
    current = _require_aware(now)
    quarantine_root = root / ".seomachine" / "quarantine" / "v1"
    eligible: list[Path] = []
    if not quarantine_root.is_dir():
        return eligible
    for manifest_path in sorted(quarantine_root.glob("*/manifest.json")):
        manifest = _load_manifest(manifest_path, root=root)
        if manifest.get("status") != "complete":
            continue
        delete_after = _parse_timestamp(manifest.get("delete_after"))
        if delete_after > current:
            continue
        rows = manifest["artifacts"]
        manifest_entries: list[tuple[Path, dict[str, object]]] = []
        for row in rows:
            if row.get("status") != "quarantined":
                continue
            path = _resolve_relative(root, row.get("quarantine_path"))
            if not path.is_file() or _sha256(path) != row.get("sha256"):
                raise ValueError(f"quarantined artifact changed: {path}")
            eligible.append(path)
            manifest_entries.append((path, row))
        if apply:
            for path, row in manifest_entries:
                path.unlink()
                row["status"] = "purged"
            manifest["status"] = "purged"
            atomic_write_json(manifest_path, manifest)
    return eligible


def _referenced_objects(root: Path) -> set[Path]:
    research = root / "research"
    object_root = root.joinpath(*OBJECT_PREFIX.parts).resolve()
    referenced: set[Path] = set()
    if not research.is_dir():
        return referenced
    for pointer in research.rglob("*.json"):
        try:
            resolved_pointer = pointer.resolve(strict=True)
            resolved_pointer.relative_to(research.resolve())
            if resolved_pointer.is_relative_to(object_root):
                continue
            if resolved_pointer.stat().st_size > POINTER_MAX_BYTES:
                continue
            value = json.loads(resolved_pointer.read_text(encoding="utf-8"))
            if isinstance(value, dict) and value.get("schema") == POINTER_SCHEMA:
                record = value.get("object")
                if isinstance(record, dict):
                    referenced.add(_resolve_relative(root, record.get("path")))
        except (OSError, UnicodeError, json.JSONDecodeError, ValueError, TypeError):
            continue
    return referenced


def _manifest_row(
    candidate: RetentionCandidate,
    *,
    index: int,
    root: Path,
    run_root: Path,
) -> dict[str, object]:
    relative = candidate.path.relative_to(root)
    target = run_root / "objects" / f"{index:06d}.blob"
    return {
        "original_path": relative.as_posix(),
        "quarantine_path": target.relative_to(root).as_posix(),
        "sha256": candidate.sha256,
        "bytes": candidate.byte_count,
        "status": "pending",
    }


def _verify_candidate(candidate: RetentionCandidate, *, root: Path) -> None:
    object_root = root.joinpath(*OBJECT_PREFIX.parts).resolve()
    candidate.path.relative_to(object_root)
    if not candidate.path.is_file():
        raise ValueError(f"retention candidate disappeared: {candidate.path}")
    if candidate.path.stat().st_size != candidate.byte_count or _sha256(candidate.path) != candidate.sha256:
        raise ValueError(f"retention candidate changed: {candidate.path}")


def _load_manifest(path: str | Path, *, root: Path) -> dict[str, object]:
    resolved = Path(path).resolve(strict=True)
    resolved.relative_to(root)
    value = json.loads(resolved.read_text(encoding="utf-8"))
    if not isinstance(value, dict) or value.get("schema") != QUARANTINE_SCHEMA:
        raise ValueError("quarantine manifest is invalid")
    artifacts = value.get("artifacts")
    if not isinstance(artifacts, list) or not all(isinstance(row, dict) for row in artifacts):
        raise ValueError("quarantine artifact inventory is invalid")
    return value


def _resolve_relative(root: Path, value: object) -> Path:
    if not isinstance(value, (str, Path)) or not str(value):
        raise ValueError("artifact path must be non-empty")
    candidate = Path(value)
    if candidate.is_absolute() or ".." in candidate.parts:
        raise ValueError("artifact path must be workspace-relative")
    resolved = (root / candidate).resolve(strict=False)
    resolved.relative_to(root)
    return resolved


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _require_aware(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("retention time must be timezone-aware")
    return value.astimezone(timezone.utc)


def _format_timestamp(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _parse_timestamp(value: object) -> datetime:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise ValueError("quarantine timestamp is invalid")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as error:
        raise ValueError("quarantine timestamp is invalid") from error
    return _require_aware(parsed)
