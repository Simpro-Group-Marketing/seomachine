"""Strict UTF-8 and JSON decoding without duplicate or non-finite values."""

from __future__ import annotations

import json
import math
from typing import Any


def decode_utf8(data: bytes, *, field: str) -> str:
    """Decode exact bytes as UTF-8 with a field-specific stable error."""
    if not isinstance(data, bytes):
        raise TypeError("data must be bytes")
    try:
        return data.decode("utf-8", errors="strict")
    except UnicodeDecodeError as error:
        raise ValueError(f"{field} must use valid UTF-8: {error}") from error


def parse_json(value: bytes | str, *, field: str) -> Any:
    """Parse strict JSON and reject duplicate keys and non-finite numbers."""
    text = decode_utf8(value, field=field) if isinstance(value, bytes) else value
    if not isinstance(text, str):
        raise ValueError(f"{field} must be strict JSON text")
    try:
        return json.loads(
            text,
            object_pairs_hook=_reject_duplicate_object_keys,
            parse_constant=_reject_non_finite_constant,
            parse_float=_finite_float,
        )
    except (json.JSONDecodeError, ValueError) as error:
        raise ValueError(f"{field} must be strict JSON: {error}") from error


def parse_json_object(value: bytes | str, *, field: str) -> dict[str, Any]:
    """Parse one strict JSON object."""
    payload = parse_json(value, field=field)
    if not isinstance(payload, dict):
        raise ValueError(f"{field} must be a JSON object")
    return payload


def _reject_duplicate_object_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate key: {key}")
        result[key] = value
    return result


def _reject_non_finite_constant(value: str) -> Any:
    raise ValueError(f"non-finite number: {value}")


def _finite_float(value: str) -> float:
    parsed = float(value)
    if not math.isfinite(parsed):
        raise ValueError(f"non-finite number: {value}")
    return parsed


__all__ = ["decode_utf8", "parse_json", "parse_json_object"]
