"""Content-addressed storage for bounded context trace payloads."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from collections.abc import Mapping
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any

from ..blog_assembly_contract import atomic_write_json, canonical_json_bytes
from .limits import JSON_MAX_BYTES
from .workspace_lock import artifact_workspace_lock


POINTER_SCHEMA = "simpro-context-trace-pointer/v1"
OBJECT_PREFIX = PurePosixPath("research/.objects/context-traces/v1/sha256")
POINTER_MAX_BYTES = 64 * 1024


def write_context_trace(
    pointer_path: str | Path,
    payload: Mapping[str, Any],
    *,
    workspace_root: str | Path,
    generated_at: datetime,
) -> dict[str, object]:
    """Write one canonical trace blob and an atomic human-facing pointer."""
    root = Path(workspace_root).resolve()
    pointer = _resolve_output(pointer_path, workspace_root=root)
    trace_schema = payload.get("schema")
    if not isinstance(trace_schema, str) or not trace_schema:
        raise ValueError("context trace payload requires a schema")
    serialized = canonical_json_bytes(payload)
    if len(serialized) > JSON_MAX_BYTES:
        raise ValueError(f"context trace exceeds {JSON_MAX_BYTES} bytes")
    digest = hashlib.sha256(serialized).hexdigest()
    relative_object = OBJECT_PREFIX / digest[:2] / f"{digest}.json"
    object_path = root.joinpath(*relative_object.parts)
    pointer_payload: dict[str, object] = {
        "schema": POINTER_SCHEMA,
        "trace_schema": trace_schema,
        "generated_at": _format_timestamp(generated_at),
        "object": {
            "path": relative_object.as_posix(),
            "sha256": digest,
            "bytes": len(serialized),
        },
    }
    with artifact_workspace_lock(root):
        _store_immutable_object(object_path, serialized, digest=digest)
        atomic_write_json(pointer, pointer_payload)
    return pointer_payload


def resolve_context_trace(
    pointer_path: str | Path,
    *,
    workspace_root: str | Path,
) -> dict[str, Any]:
    """Resolve and authenticate a trace pointer and return its JSON object."""
    root = Path(workspace_root).resolve()
    pointer = _resolve_existing(pointer_path, workspace_root=root)
    record = _load_json_object(pointer, max_bytes=POINTER_MAX_BYTES, label="context trace pointer")
    if record.get("schema") != POINTER_SCHEMA:
        raise ValueError("context trace pointer schema is invalid")
    object_record = record.get("object")
    if not isinstance(object_record, dict):
        raise ValueError("context trace pointer object is invalid")
    object_path = _resolve_object_path(object_record.get("path"), workspace_root=root)
    expected_hash = object_record.get("sha256")
    expected_bytes = object_record.get("bytes")
    if not isinstance(expected_hash, str) or len(expected_hash) != 64:
        raise ValueError("context trace object sha256 is invalid")
    if isinstance(expected_bytes, bool) or not isinstance(expected_bytes, int):
        raise ValueError("context trace object byte count is invalid")
    content = _read_bounded(object_path, max_bytes=JSON_MAX_BYTES, label="context trace object")
    if hashlib.sha256(content).hexdigest() != expected_hash:
        raise ValueError("context trace object sha256 does not match")
    if len(content) != expected_bytes:
        raise ValueError("context trace object byte count does not match")
    payload = _parse_json_object(content, label="context trace object")
    if payload.get("schema") != record.get("trace_schema"):
        raise ValueError("context trace schema does not match its pointer")
    return payload


def _store_immutable_object(path: Path, content: bytes, *, digest: str) -> None:
    if path.exists():
        existing = _read_bounded(path, max_bytes=JSON_MAX_BYTES, label="context trace object")
        if existing != content or hashlib.sha256(existing).hexdigest() != digest:
            raise ValueError("content-addressed trace object does not match its path")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            temporary = Path(handle.name)
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        try:
            os.link(temporary, path)
        except FileExistsError:
            existing = _read_bounded(path, max_bytes=JSON_MAX_BYTES, label="context trace object")
            if existing != content:
                raise ValueError("concurrent context trace object differs")
        except OSError:
            if path.exists():
                existing = _read_bounded(path, max_bytes=JSON_MAX_BYTES, label="context trace object")
                if existing != content:
                    raise ValueError("concurrent context trace object differs")
            else:
                os.replace(temporary, path)
                temporary = None
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def _load_json_object(path: Path, *, max_bytes: int, label: str) -> dict[str, Any]:
    return _parse_json_object(_read_bounded(path, max_bytes=max_bytes, label=label), label=label)


def _read_bounded(path: Path, *, max_bytes: int, label: str) -> bytes:
    try:
        with path.open("rb") as handle:
            content = handle.read(max_bytes + 1)
    except OSError as error:
        raise ValueError(f"{label} is unreadable: {error}") from error
    if len(content) > max_bytes:
        raise ValueError(f"{label} exceeds {max_bytes} bytes")
    return content


def _parse_json_object(content: bytes, *, label: str) -> dict[str, Any]:
    def pairs(values: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in values:
            if key in result:
                raise ValueError(f"{label} contains duplicate JSON key {key!r}")
            result[key] = value
        return result

    try:
        value = json.loads(content.decode("utf-8"), object_pairs_hook=pairs)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError(f"{label} is not valid UTF-8 JSON") from error
    if not isinstance(value, dict):
        raise ValueError(f"{label} must contain a JSON object")
    return value


def _resolve_output(path: str | Path, *, workspace_root: Path) -> Path:
    candidate = Path(path)
    if not candidate.is_absolute():
        candidate = workspace_root / candidate
    resolved = candidate.resolve(strict=False)
    _require_within(resolved, workspace_root)
    return resolved


def _resolve_existing(path: str | Path, *, workspace_root: Path) -> Path:
    resolved = _resolve_output(path, workspace_root=workspace_root).resolve(strict=True)
    if not resolved.is_file():
        raise ValueError("context trace pointer is unavailable")
    return resolved


def _resolve_object_path(value: Any, *, workspace_root: Path) -> Path:
    if not isinstance(value, str):
        raise ValueError("context trace object path is invalid")
    pure = PurePosixPath(value)
    if pure.is_absolute() or "\\" in value or any(part in {"", ".", ".."} for part in pure.parts):
        raise ValueError("context trace object path is invalid")
    if tuple(pure.parts[: len(OBJECT_PREFIX.parts)]) != OBJECT_PREFIX.parts:
        raise ValueError("context trace object path is outside its managed namespace")
    resolved = workspace_root.joinpath(*pure.parts).resolve(strict=True)
    _require_within(resolved, workspace_root)
    return resolved


def _require_within(path: Path, root: Path) -> None:
    try:
        path.relative_to(root)
    except ValueError as error:
        raise ValueError("context trace path must stay inside the workspace") from error


def _format_timestamp(value: datetime) -> str:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("generated_at must be timezone-aware")
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
