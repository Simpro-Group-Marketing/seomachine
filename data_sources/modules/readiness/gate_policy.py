"""Small gate-selection policies shared by readiness orchestration."""

from __future__ import annotations

from .gate_registry import CONNECTOR_GATE_NAMES

RETIRED_BLOG_READINESS = (
    "unsupported artifact_kind blog: readiness serves landing pages only; "
    "blogs release through /publish-readiness (production.release)"
)


def skip_article_gate(name: str, *, simpro_context_required: bool) -> bool:
    """Connector-evidence gates run only for pages that require Simpro context."""
    return name in CONNECTOR_GATE_NAMES and not simpro_context_required


def artifact_kind_rule_id(message: str) -> str:
    normalized = message.casefold()
    if "unsupported" in normalized:
        return "artifact_kind_unsupported"
    if "conflict" in normalized:
        return "artifact_kind_conflict"
    return "artifact_kind_missing"


__all__ = ["RETIRED_BLOG_READINESS", "artifact_kind_rule_id", "skip_article_gate"]
