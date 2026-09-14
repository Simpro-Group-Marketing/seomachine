"""Injected external seams for final readiness attestation."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable

from ..blog_bom_validation.api import check_bom


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


@dataclass(frozen=True, slots=True)
class FinalizationDependencies:
    """Dependencies used only by the final readiness delta."""

    final_bom_guard: Callable[..., list[dict[str, Any]]] = check_bom
    now: Callable[[], str] = utc_now


DEFAULT_FINALIZATION_DEPENDENCIES = FinalizationDependencies()


__all__ = ["DEFAULT_FINALIZATION_DEPENDENCIES", "FinalizationDependencies"]
