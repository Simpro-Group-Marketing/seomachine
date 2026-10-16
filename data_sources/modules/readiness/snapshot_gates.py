"""Source-registry state for readiness gates, backed by one immutable artifact snapshot."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from .gates import _json


def source_registry_state(session: Any, captured: Any) -> Any:
    """Return a lazy session cache lookup over exact captured registry bytes."""
    snapshot = captured.optional_snapshot("source_decision_registry")
    if session is None or snapshot is None:
        return None
    source = SimpleNamespace(
        path=snapshot.path,
        data=captured.bytes("source_decision_registry"),
        sha256=snapshot.sha256,
        payload=_json(captured, "source_decision_registry"),
    )
    return lambda: session.git_registry_state(snapshot.path, lambda: source)


__all__ = ["source_registry_state"]
