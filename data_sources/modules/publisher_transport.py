"""Bounded response decoding for authenticated publisher transports."""

from __future__ import annotations

from typing import Any

import requests

from .artifact_runtime.limits import JSON_MAX_BYTES
from .bounded_io import read_response_bytes, read_response_json


def read_wordpress_json(response: Any) -> Any:
    """Bound real response bytes while retaining lightweight test doubles."""
    if isinstance(response, requests.Response):
        return read_response_json(
            response,
            max_bytes=JSON_MAX_BYTES,
            field="WordPress response",
        )
    return response.json()


def publisher_response_preview(response: Any) -> str:
    """Return bounded diagnostic text without leaking an unbounded response."""
    try:
        content = read_response_bytes(
            response,
            max_bytes=JSON_MAX_BYTES,
            field="publisher response",
        )
    except ValueError:
        return f"[response body omitted: exceeds {JSON_MAX_BYTES} bytes]"
    return content.decode("utf-8", errors="replace")


__all__ = ["publisher_response_preview", "read_wordpress_json"]
