"""Atomic persistence primitives for readiness result and receipt pairs."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Any, Callable, Mapping

from ..blog_assembly_contract import atomic_write_json


def persist_result_pair(
    output: Path,
    result: Mapping[str, Any],
    receipt_path: Path,
    receipt: Mapping[str, Any],
    *,
    receipt_writer: Callable[[Path, Mapping[str, Any]], Any],
) -> Path:
    """Atomically write a result and roll it back if its receipt write fails."""
    output_existed = output.is_file()
    previous_output = output.read_bytes() if output_existed else None
    atomic_write_json(output, result)
    try:
        receipt_writer(receipt_path, receipt)
    except Exception:
        _restore_file(
            output,
            existed=output_existed,
            previous_bytes=previous_output,
        )
        raise
    return receipt_path


def _restore_file(
    path: Path,
    *,
    existed: bool,
    previous_bytes: bytes | None,
) -> None:
    if not existed:
        path.unlink(missing_ok=True)
        return
    if previous_bytes is None:
        raise RuntimeError("readiness output rollback bytes are unavailable")
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".rollback.tmp",
            delete=False,
        ) as handle:
            temporary = Path(handle.name)
            handle.write(previous_bytes)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        temporary = None
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
