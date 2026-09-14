"""Atomic byte-counted output writers."""

from __future__ import annotations

import os
import tempfile
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

from .json_encoding import bounded_canonical_json_bytes


class OutputByteLimitError(ValueError):
    """Raised when an output would exceed its declared byte policy."""


def atomic_write_bytes(
    path: str | Path,
    chunks: Iterable[bytes],
    *,
    max_bytes: int,
    field: str,
    replace: bool = True,
) -> None:
    """Write bytes to a sibling temporary file and install only on success."""
    if isinstance(max_bytes, bool) or not isinstance(max_bytes, int) or max_bytes < 1:
        raise ValueError("max_bytes must be a positive integer")
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    written = 0
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb",
            dir=destination.parent,
            prefix=f".{destination.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            temporary = Path(handle.name)
            for chunk in chunks:
                if not isinstance(chunk, bytes):
                    raise TypeError(f"{field} writer chunks must be bytes")
                written += len(chunk)
                if written > max_bytes:
                    raise OutputByteLimitError(f"{field} exceeds {max_bytes} bytes")
                handle.write(chunk)
            handle.flush()
            os.fsync(handle.fileno())
        if replace:
            os.replace(temporary, destination)
            temporary = None
        else:
            os.link(temporary, destination)
            temporary.unlink()
            temporary = None
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def atomic_write_text(
    path: str | Path,
    text: str,
    *,
    max_bytes: int,
    field: str,
    replace: bool = True,
) -> None:
    """Atomically write UTF-8 text under a strict byte ceiling."""
    atomic_write_bytes(
        path,
        (text.encode("utf-8"),),
        max_bytes=max_bytes,
        field=field,
        replace=replace,
    )


def atomic_write_canonical_json(
    path: str | Path,
    payload: Mapping[str, Any],
    *,
    max_bytes: int,
    field: str,
    replace: bool = True,
) -> None:
    """Atomically write canonical JSON under a strict byte ceiling."""
    try:
        encoded = bounded_canonical_json_bytes(payload, max_bytes=max_bytes)
    except ValueError as error:
        raise OutputByteLimitError(f"{field} exceeds {max_bytes} bytes") from error
    atomic_write_bytes(
        path,
        (encoded,),
        max_bytes=max_bytes,
        field=field,
        replace=replace,
    )


__all__ = [
    "OutputByteLimitError",
    "atomic_write_bytes",
    "atomic_write_canonical_json",
    "atomic_write_text",
]
