"""Bounded reads for authenticated HTTP response bodies."""

from __future__ import annotations

import json
from typing import Any


RESPONSE_CHUNK_BYTES = 64 * 1024


def read_response_bytes(response: Any, *, max_bytes: int, field: str) -> bytes:
    """Consume a requests-like streaming response within a hard byte limit."""
    if isinstance(max_bytes, bool) or not isinstance(max_bytes, int) or max_bytes < 1:
        raise ValueError("max_bytes must be a positive integer")
    declared = _content_length(response)
    if declared is not None and declared > max_bytes:
        raise ValueError(f"{field} exceeds {max_bytes} bytes")
    iterator = getattr(response, "iter_content", None)
    if not callable(iterator):
        content = getattr(response, "content", None)
        if not isinstance(content, bytes):
            raise ValueError(f"{field} does not expose a byte response body")
        if len(content) > max_bytes:
            raise ValueError(f"{field} exceeds {max_bytes} bytes")
        return content
    output = bytearray()
    for chunk in iterator(chunk_size=RESPONSE_CHUNK_BYTES):
        if not chunk:
            continue
        if not isinstance(chunk, bytes):
            raise ValueError(f"{field} returned a non-byte response chunk")
        if len(output) + len(chunk) > max_bytes:
            raise ValueError(f"{field} exceeds {max_bytes} bytes")
        output.extend(chunk)
    return bytes(output)


def read_response_json(response: Any, *, max_bytes: int, field: str) -> Any:
    """Decode one bounded UTF-8 JSON response without using response.json()."""
    try:
        content = read_response_bytes(response, max_bytes=max_bytes, field=field)
        return json.loads(content.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError(f"{field} is not valid UTF-8 JSON") from error


def _content_length(response: Any) -> int | None:
    headers = getattr(response, "headers", {})
    if not hasattr(headers, "get"):
        return None
    raw = headers.get("Content-Length")
    if raw is None:
        return None
    try:
        value = int(raw)
    except (TypeError, ValueError) as error:
        raise ValueError("response Content-Length is invalid") from error
    if value < 0:
        raise ValueError("response Content-Length is invalid")
    return value


__all__ = ["read_response_bytes", "read_response_json"]
