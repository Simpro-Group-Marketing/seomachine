"""Deterministic SHA-256 and canonical JSON encoding."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any


HASH_CHUNK_BYTES = 1024 * 1024


def stream_sha256(path: str | Path) -> str:
    """Hash exact file bytes while keeping transient memory bounded."""
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        while chunk := handle.read(HASH_CHUNK_BYTES):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_json_bytes(payload: Mapping[str, Any]) -> bytes:
    """Serialize a JSON object using the repository's durable wire format."""
    if not isinstance(payload, Mapping):
        raise ValueError("payload must be an object")
    return (
        json.dumps(
            dict(payload),
            ensure_ascii=True,
            indent=2,
            sort_keys=True,
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def canonical_json_sha256(payload: Mapping[str, Any]) -> str:
    """Hash one canonical durable JSON object."""
    return hashlib.sha256(canonical_json_bytes(payload)).hexdigest()


__all__ = [
    "HASH_CHUNK_BYTES",
    "canonical_json_bytes",
    "canonical_json_sha256",
    "stream_sha256",
]
