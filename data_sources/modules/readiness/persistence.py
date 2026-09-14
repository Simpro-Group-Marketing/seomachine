"""Atomic persistence primitives for readiness result and receipt pairs."""

from __future__ import annotations

import hashlib
import os
import tempfile
from pathlib import Path
from typing import Any, Callable, Mapping

from ..blog_assembly_contract import atomic_write_json, canonical_json_bytes


def persist_new_result_pair(
    output: Path,
    result: Mapping[str, Any],
    receipt_path: Path,
    receipt: Mapping[str, Any],
) -> Path:
    """Stage and install a final result pair without replacing either output."""
    if output.exists() or receipt_path.exists():
        raise ValueError("final release output already exists")
    output.parent.mkdir(parents=True, exist_ok=True)
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    staged = [
        _stage_bytes(output, canonical_json_bytes(result)),
        _stage_bytes(receipt_path, canonical_json_bytes(receipt)),
    ]
    digests = [_sha256_file(temporary) for temporary in staged]
    installed: list[tuple[Path, Path, str]] = []
    try:
        destinations = (output, receipt_path)
        for temporary, destination, digest in zip(
            staged,
            destinations,
            digests,
            strict=True,
        ):
            try:
                os.link(temporary, destination)
            except FileExistsError as error:
                raise ValueError("final release output already exists") from error
            installed.append((temporary, destination, digest))
            _verify_installed_link(temporary, destination, digest)
        return receipt_path
    except BaseException as error:
        try:
            _rollback_installed(installed)
        except RuntimeError as cleanup_error:
            raise cleanup_error from error
        raise
    finally:
        for temporary in staged:
            temporary.unlink(missing_ok=True)


def _stage_bytes(destination: Path, content: bytes) -> Path:
    with tempfile.NamedTemporaryFile(
        mode="wb",
        dir=destination.parent,
        prefix=f".{destination.name}.",
        suffix=".bundle.tmp",
        delete=False,
    ) as handle:
        temporary = Path(handle.name)
        handle.write(content)
        handle.flush()
        os.fsync(handle.fileno())
    return temporary


def _verify_installed_link(temporary: Path, destination: Path, digest: str) -> None:
    try:
        if not os.path.samefile(temporary, destination):
            raise RuntimeError("installed output identity does not match staged bytes")
        if _sha256_file(destination) != digest:
            raise RuntimeError("installed output digest does not match staged bytes")
    except OSError as error:
        raise RuntimeError(f"installed output could not be verified: {error}") from error


def _rollback_installed(installed: list[tuple[Path, Path, str]]) -> None:
    for temporary, destination, digest in reversed(installed):
        try:
            _verify_installed_link(temporary, destination, digest)
            destination.unlink()
        except (OSError, RuntimeError) as error:
            raise RuntimeError(
                "final release rollback could not safely remove installed output"
            ) from error


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


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
