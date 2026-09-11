"""Reachability scanning and immutable retention plans."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterable

from .content_store import (
    OBJECT_PREFIX,
    POINTER_MAX_BYTES,
    POINTER_SCHEMA,
    _load_json_object,
)


DEFAULT_RESEARCH_RETENTION_DAYS = 90


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
    root = Path(workspace_root).resolve(strict=True)
    current = require_aware(now)
    if research_retention_days < 1:
        raise ValueError("research_retention_days must be positive")
    referenced = referenced_objects(root)
    tracked = {resolve_relative(root, value) for value in tracked_paths}
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
                raise ValueError(
                    f"managed object path escapes its namespace: {path}"
                ) from error
            stat = resolved.stat()
            modified = datetime.fromtimestamp(stat.st_mtime, timezone.utc)
            if resolved in referenced or resolved in tracked or modified > cutoff:
                continue
            candidates.append(
                RetentionCandidate(
                    path=resolved,
                    sha256=file_sha256(resolved),
                    byte_count=stat.st_size,
                    age_days=(current - modified).days,
                )
            )
    return RetentionPlan(
        workspace_root=root,
        candidates=tuple(candidates),
        referenced=tuple(sorted(referenced)),
        evaluated_at=current,
    )


def referenced_objects(root: Path) -> set[Path]:
    """Strictly scan bounded JSON pointer candidates under research."""
    research = root / "research"
    object_root = root.joinpath(*OBJECT_PREFIX.parts).resolve()
    referenced: set[Path] = set()
    if not research.is_dir():
        return referenced
    research_root = research.resolve(strict=True)
    for pointer in sorted(research.rglob("*.json")):
        try:
            resolved = pointer.resolve(strict=True)
            resolved.relative_to(research_root)
        except (OSError, ValueError) as error:
            raise ValueError(f"pointer candidate escapes research: {pointer}") from error
        if resolved.is_relative_to(object_root):
            continue
        try:
            size = resolved.stat().st_size
        except OSError as error:
            raise ValueError(f"pointer candidate is unreadable: {pointer}") from error
        if size > POINTER_MAX_BYTES:
            continue
        try:
            value = _load_json_object(
                resolved,
                max_bytes=POINTER_MAX_BYTES,
                label="pointer candidate",
            )
        except ValueError as error:
            raise ValueError(f"pointer candidate is invalid: {pointer}: {error}") from error
        if value.get("schema") != POINTER_SCHEMA:
            continue
        referenced.add(_validate_pointer(value, root=root))
    return referenced


def _validate_pointer(value: dict[str, object], *, root: Path) -> Path:
    if set(value) != {"schema", "trace_schema", "generated_at", "object"}:
        raise ValueError("pointer candidate claiming the pointer schema has invalid fields")
    record = value.get("object")
    if not isinstance(record, dict) or set(record) != {"path", "sha256", "bytes"}:
        raise ValueError("pointer candidate claiming the pointer schema has invalid object")
    digest = record.get("sha256")
    byte_count = record.get("bytes")
    if not isinstance(digest, str) or len(digest) != 64:
        raise ValueError("pointer candidate claiming the pointer schema has invalid sha256")
    if isinstance(byte_count, bool) or not isinstance(byte_count, int) or byte_count < 0:
        raise ValueError("pointer candidate claiming the pointer schema has invalid bytes")
    return resolve_relative(root, record.get("path"))


def verify_candidate(candidate: RetentionCandidate, *, root: Path) -> None:
    object_root = root.joinpath(*OBJECT_PREFIX.parts).resolve()
    candidate.path.relative_to(object_root)
    if not candidate.path.is_file():
        raise ValueError(f"retention candidate disappeared: {candidate.path}")
    stat = candidate.path.stat()
    if stat.st_size != candidate.byte_count or file_sha256(candidate.path) != candidate.sha256:
        raise ValueError(f"retention candidate changed: {candidate.path}")


def resolve_relative(root: Path, value: object) -> Path:
    if not isinstance(value, (str, Path)) or not str(value):
        raise ValueError("artifact path must be non-empty")
    candidate = Path(value)
    if candidate.is_absolute() or ".." in candidate.parts:
        raise ValueError("artifact path must be workspace-relative")
    resolved = (root / candidate).resolve(strict=False)
    resolved.relative_to(root)
    return resolved


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def require_aware(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("retention time must be timezone-aware")
    return value.astimezone(timezone.utc)


def format_timestamp(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def parse_timestamp(value: object) -> datetime:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise ValueError("quarantine timestamp is invalid")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as error:
        raise ValueError("quarantine timestamp is invalid") from error
    return require_aware(parsed)
