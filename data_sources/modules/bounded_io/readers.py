"""Bounded byte reads and stable file identity capture."""

from __future__ import annotations

from pathlib import Path
from typing import TypeAlias


FileIdentity: TypeAlias = tuple[int, int, int, int, int]


def read_bounded(path: str | Path, *, max_bytes: int, field: str) -> bytes:
    """Read at most ``max_bytes`` plus one internal sentinel byte."""
    if isinstance(max_bytes, bool) or not isinstance(max_bytes, int) or max_bytes < 1:
        raise ValueError("max_bytes must be a positive integer")
    source = Path(path)
    try:
        with source.open("rb") as handle:
            data = handle.read(max_bytes + 1)
    except OSError as error:
        raise ValueError(f"{field} is unreadable: {error}") from error
    if len(data) > max_bytes:
        raise ValueError(f"{field} exceeds {max_bytes} bytes")
    return data


def file_identity(path: str | Path) -> FileIdentity:
    """Return the identity tuple used by readiness and release seals."""
    stat = Path(path).stat()
    return (stat.st_dev, stat.st_ino, stat.st_size, stat.st_mtime_ns, stat.st_ctime_ns)


__all__ = ["FileIdentity", "file_identity", "read_bounded"]
