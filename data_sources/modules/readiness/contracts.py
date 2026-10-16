"""Stable publish-readiness result and gate contracts."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping


GateResult = dict[str, Any]
ReadinessResult = dict[str, Any]
READINESS_RESULT_SCHEMA = "simpro-publish-readiness-result/v1"



class ExecutedReadinessResult(dict[str, Any]):
    """A readiness result from the gate runner, carrying its workspace and sealed inventory."""

    __slots__ = ("_sealed_inventory", "_workspace_root")

    def __init__(
        self,
        value: Mapping[str, Any],
        *,
        workspace_root: Path,
        sealed_inventory: Any = None,
    ) -> None:
        super().__init__(value)
        self._workspace_root = workspace_root.resolve()
        self._sealed_inventory = sealed_inventory

    @property
    def sealed_inventory(self) -> Any:
        """Return the non-serializable final-session capability, when present."""
        return self._sealed_inventory



