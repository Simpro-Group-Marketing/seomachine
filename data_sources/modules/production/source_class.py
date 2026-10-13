"""Classify a cited FAQ source with the repository's existing rules; never by hand.

A URL on the article brand's own domains is ``owned_product`` (``proof_link_policy``).
Any other URL needs exactly one approved row in the committed source decision registry
(``source_support``). A URL neither rule covers stays unclassified.
"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from urllib.parse import urlsplit

from data_sources.modules.proof_link_policy import _domain_relationship
from data_sources.modules.source_support.common import SOURCE_DECISIONS_PATH
from data_sources.modules.source_support.persistence import (
    _load_decision_registry,
    _select_approved_decision,
)

COMPETITOR_CLASS = "competitor"


def _registry_class(url: str, hostname: str, root: Path) -> str | None:
    try:
        _snapshot, registry, _revision = _load_decision_registry(root / SOURCE_DECISIONS_PATH, workspace_root=root)
    except (OSError, ValueError):
        return None
    matches = [
        row for row in registry["decisions"]
        if isinstance(row, Mapping) and row.get("source_url") == url and row.get("status") == "approved"
    ]
    if len(matches) != 1:
        return None
    try:
        source_class, _relationship = _select_approved_decision(
            registry["decisions"], decision_id=str(matches[0].get("decision_id")), source_url=url, hostname=hostname
        )
    except ValueError:
        return None
    return source_class


def classify_source(url: str, brand: str, root: Path | None) -> tuple[str, str] | None:
    """Return (source class, competitor check), or None when existing rules cannot classify the URL."""
    hostname = (urlsplit(url).hostname or "").lower().rstrip(".")
    if not hostname:
        return None
    if _domain_relationship(hostname, brand) == "internal":
        return "owned_product", "passed"
    source_class = _registry_class(url, hostname, root) if root is not None else None
    if source_class is None:
        return None
    return source_class, "failed" if source_class == COMPETITOR_CLASS else "passed"
