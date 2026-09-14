"""Explicit dependency contract for deterministic BOM construction."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from types import MappingProxyType
from typing import Any, Callable, Mapping

from .common import (
    NORMAL_PROVISIONAL_STAGES,
    context_binding_guard,
    load_json_object_snapshot,
)


@dataclass(frozen=True)
class BomValidationDependencies:
    """Injectable external operations owned by the BOM orchestrator."""

    load_json_object_snapshot: Callable[..., Any] = field(
        default_factory=lambda: load_json_object_snapshot
    )
    validate_context_artifacts: Callable[..., Any] = field(
        default_factory=lambda: context_binding_guard.validate_context_artifacts
    )
    normal_provisional_stages: tuple[str, ...] = NORMAL_PROVISIONAL_STAGES
    bindings: Mapping[str, Any] = field(
        default_factory=lambda: MappingProxyType({}),
        repr=False,
        compare=False,
    )

    def bind(self, **bindings: Any) -> BomValidationDependencies:
        """Return an immutable view with explicit validator operations."""
        merged = dict(self.bindings)
        merged.update(bindings)
        return replace(self, bindings=MappingProxyType(merged))

    def __getitem__(self, name: str) -> Any:
        """Resolve a named validator operation without module-global dispatch."""
        return self.bindings[name]


DEFAULT_BOM_VALIDATION_DEPENDENCIES = BomValidationDependencies()


__all__ = ["BomValidationDependencies", "DEFAULT_BOM_VALIDATION_DEPENDENCIES"]
