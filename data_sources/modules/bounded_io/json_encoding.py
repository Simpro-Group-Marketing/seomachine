"""Incremental, size-bounded JSON encoding."""

from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any


class JsonOutputLimitError(ValueError):
    """Raised before an oversized JSON value can be materialized."""


def bounded_json_bytes(
    payload: Any,
    *,
    max_bytes: int,
    canonical: bool = False,
) -> bytes:
    """Encode JSON incrementally and fail at a strict UTF-8 byte ceiling."""
    if isinstance(max_bytes, bool) or not isinstance(max_bytes, int) or max_bytes < 1:
        raise ValueError("max_bytes must be a positive integer")
    _reject_oversized_strings(payload, max_bytes=max_bytes)
    encoder = json.JSONEncoder(
        ensure_ascii=canonical,
        indent=2 if canonical else None,
        sort_keys=canonical,
        allow_nan=False,
        separators=None if canonical else (",", ":"),
    )
    output = bytearray()
    for chunk in encoder.iterencode(payload):
        encoded = chunk.encode("utf-8")
        if len(output) + len(encoded) > max_bytes:
            raise JsonOutputLimitError(f"JSON output exceeds {max_bytes} bytes")
        output.extend(encoded)
    if canonical:
        if len(output) == max_bytes:
            raise JsonOutputLimitError(f"JSON output exceeds {max_bytes} bytes")
        output.extend(b"\n")
    return bytes(output)


def bounded_canonical_json_bytes(
    payload: Mapping[str, Any],
    *,
    max_bytes: int,
) -> bytes:
    """Encode one canonical JSON object within a strict byte ceiling."""
    if not isinstance(payload, Mapping):
        raise ValueError("payload must be an object")
    return bounded_json_bytes(dict(payload), max_bytes=max_bytes, canonical=True)


def _reject_oversized_strings(payload: Any, *, max_bytes: int) -> None:
    stack = [payload]
    seen: set[int] = set()
    while stack:
        value = stack.pop()
        if isinstance(value, str):
            if len(value) > max_bytes:
                raise JsonOutputLimitError(f"JSON output exceeds {max_bytes} bytes")
            continue
        if isinstance(value, Mapping):
            identity = id(value)
            if identity in seen:
                continue
            seen.add(identity)
            stack.extend(value.keys())
            stack.extend(value.values())
        elif isinstance(value, (list, tuple)):
            identity = id(value)
            if identity in seen:
                continue
            seen.add(identity)
            stack.extend(value)


__all__ = [
    "JsonOutputLimitError",
    "bounded_canonical_json_bytes",
    "bounded_json_bytes",
]
