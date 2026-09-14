"""Immutable Git-backed registry verification for validation sessions."""

from __future__ import annotations

import hashlib
import os
import re
import subprocess
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..artifact_runtime.subprocesses import run_bounded_process
from .artifact_views import freeze_mapping


COMMAND_MAX_BYTES = 1024 * 1024
BLOB_MAX_BYTES = 8 * 1024 * 1024
HEAD_RE = re.compile(r"^[0-9a-f]{40,64}$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


@dataclass(frozen=True, slots=True)
class GitRegistryState:
    """Verified immutable registry bytes, payload, and Git commit identity."""

    registry_path: Path
    repository_root: Path
    relative_path: str
    head: str
    registry_sha256: str
    committed_blob_sha256: str
    byte_count: int
    payload: Mapping[str, Any]


def capture_git_registry_state(
    snapshot: object,
    *,
    workspace_root: str | Path,
) -> GitRegistryState:
    """Verify one strict snapshot against its exact blob at the resolved HEAD."""
    path, data, digest, payload = _snapshot_parts(snapshot)
    requested_root = Path(workspace_root).resolve(strict=True)
    try:
        relative_path = path.relative_to(requested_root).as_posix()
    except ValueError as error:
        raise _registry_error() from error
    head, committed = _repository_blob(
        requested_root,
        relative_path=relative_path,
    )
    committed_digest = hashlib.sha256(committed).hexdigest()
    if committed != data:
        raise _registry_error()
    return GitRegistryState(
        registry_path=path,
        repository_root=requested_root,
        relative_path=relative_path,
        head=head,
        registry_sha256=digest,
        committed_blob_sha256=committed_digest,
        byte_count=len(data),
        payload=freeze_mapping(payload),
    )


def validate_git_registry_state(
    state: object,
    *,
    registry_path: str | Path,
    workspace_root: str | Path,
    expected_sha256: str,
) -> GitRegistryState:
    """Validate a cached state binding without rerunning Git or reading a file."""
    if not isinstance(state, GitRegistryState):
        raise ValueError("source decision registry state is invalid")
    expected_path = Path(registry_path).resolve(strict=True)
    expected_root = Path(workspace_root).resolve(strict=True)
    try:
        expected_relative = expected_path.relative_to(expected_root).as_posix()
    except ValueError as error:
        raise ValueError("source decision registry state is outside its repository") from error
    valid = (
        state.registry_path == expected_path
        and state.repository_root == expected_root
        and state.relative_path == expected_relative
        and state.registry_sha256 == expected_sha256
        and state.committed_blob_sha256 == state.registry_sha256
        and bool(SHA256_RE.fullmatch(state.registry_sha256))
        and state.byte_count > 0
        and bool(HEAD_RE.fullmatch(state.head))
    )
    if not valid:
        raise ValueError("source decision registry state does not match its binding")
    return state


def _snapshot_parts(
    snapshot: object,
) -> tuple[Path, bytes, str, Mapping[str, Any]]:
    path = getattr(snapshot, "path", None)
    data = getattr(snapshot, "data", None)
    digest = getattr(snapshot, "sha256", None)
    payload = getattr(snapshot, "payload", None)
    if (
        not isinstance(path, Path)
        or not isinstance(data, bytes)
        or not isinstance(digest, str)
        or not isinstance(payload, Mapping)
        or hashlib.sha256(data).hexdigest() != digest
    ):
        raise ValueError("source decision registry snapshot is invalid")
    return path.resolve(strict=True), data, digest, payload


def _repository_blob(workspace_root: Path, *, relative_path: str) -> tuple[str, bytes]:
    request = f"info HEAD\0contents HEAD:{relative_path}\0".encode("utf-8")
    environment = dict(os.environ)
    environment["GIT_CEILING_DIRECTORIES"] = str(workspace_root.parent)
    raw = _git_output(
        workspace_root,
        "cat-file",
        "--batch-command",
        "-z",
        max_bytes=BLOB_MAX_BYTES + COMMAND_MAX_BYTES,
        env=environment,
        input_bytes=request,
    )
    try:
        head_line, blob_record = raw.split(b"\n", 1)
        head_raw, object_type, commit_size = head_line.split(b" ")
        blob_line, content = blob_record.split(b"\n", 1)
        blob_raw, blob_type, blob_size_raw = blob_line.split(b" ")
        head = head_raw.decode("ascii", errors="strict").lower()
        blob_id = blob_raw.decode("ascii", errors="strict").lower()
        blob_size = int(blob_size_raw)
        if int(commit_size) <= 0 or blob_size < 0 or blob_size > BLOB_MAX_BYTES:
            raise ValueError
        committed, terminator = content[:blob_size], content[blob_size:]
    except (UnicodeDecodeError, ValueError) as error:
        raise _registry_error() from error
    if (
        object_type != b"commit"
        or blob_type != b"blob"
        or not HEAD_RE.fullmatch(head)
        or not HEAD_RE.fullmatch(blob_id)
        or len(committed) != blob_size
        or terminator != b"\n"
    ):
        raise _registry_error()
    return head, committed


def _git_output(
    repository_root: Path,
    *arguments: str,
    max_bytes: int,
    env: Mapping[str, str] | None = None,
    input_bytes: bytes | None = None,
) -> bytes:
    try:
        with run_bounded_process(
            ["git", "-C", str(repository_root), *arguments],
            timeout=10,
            max_output_bytes=max_bytes,
            env=env,
            input_bytes=input_bytes,
        ) as result:
            output = result.stdout.read_bytes(max_bytes=max_bytes)
            returncode = result.returncode
    except (OSError, RuntimeError, ValueError, subprocess.SubprocessError) as error:
        raise _registry_error() from error
    if returncode != 0:
        raise _registry_error()
    return output


def _registry_error() -> ValueError:
    return ValueError(
        "source classification registry must match its committed HEAD blob"
    )


__all__ = [
    "GitRegistryState",
    "capture_git_registry_state",
    "validate_git_registry_state",
]
