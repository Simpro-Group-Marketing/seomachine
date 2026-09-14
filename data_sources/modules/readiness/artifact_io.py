"""Bounded filesystem operations for readiness artifact snapshots."""

from __future__ import annotations

import os
from pathlib import Path

from ..bounded_io import HASH_CHUNK_BYTES, read_bounded as _shared_read_bounded
from ..bounded_io import stream_sha256


def read_bounded(path: Path, *, max_bytes: int, field: str) -> bytes:
    """Read at most the configured artifact limit plus one sentinel byte."""
    return _shared_read_bounded(
        path,
        max_bytes=max_bytes,
        field=f"readiness input {field}",
    )


def resolve_workspace_root(value: str | Path) -> Path:
    """Resolve and validate the directory that bounds all artifact access."""
    try:
        root = Path(value).resolve(strict=True)
    except OSError as error:
        raise ValueError(f"workspace_root is unavailable: {error}") from error
    if not root.is_dir():
        raise ValueError("workspace_root must be a directory")
    return root


def resolve_input(value: str | Path, *, workspace_root: Path, field: str) -> Path:
    """Resolve one regular file and reject paths outside the workspace."""
    if not isinstance(value, (str, Path)) or not str(value).strip():
        raise ValueError(f"readiness input {field} path is required")
    candidate = Path(value)
    if not candidate.is_absolute():
        candidate = workspace_root / candidate
    try:
        candidate = candidate.resolve(strict=True)
    except OSError as error:
        raise ValueError(f"readiness input {field} is unavailable: {error}") from error
    try:
        common = os.path.commonpath((str(workspace_root), str(candidate)))
    except ValueError as error:
        raise ValueError(f"readiness input {field} is outside workspace") from error
    if os.path.normcase(common) != os.path.normcase(str(workspace_root)):
        raise ValueError(f"readiness input {field} is outside workspace")
    if not candidate.is_file():
        raise ValueError(f"readiness input {field} must be a file")
    return candidate


__all__ = [
    "HASH_CHUNK_BYTES",
    "read_bounded",
    "resolve_input",
    "resolve_workspace_root",
    "stream_sha256",
]
