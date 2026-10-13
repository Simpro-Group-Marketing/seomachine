"""Helpers shared by the coverage checks."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from data_sources.modules.production.truth_text import Finding


def items(bom: Mapping[str, Any], key: str) -> list[Mapping[str, Any]]:
    value = bom.get(key)
    return [item for item in value if isinstance(item, Mapping)] if isinstance(value, list) else []


def missing(item: Mapping[str, Any], check: str, message: str) -> Finding:
    """A block for a ``must`` item and a warning for any other priority."""
    return Finding(check, "block" if item.get("priority") == "must" else "warn", message, None)
