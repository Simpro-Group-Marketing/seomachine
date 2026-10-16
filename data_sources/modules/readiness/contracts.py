"""Stable publish-readiness result and gate contracts."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping


GateResult = dict[str, Any]
ReadinessResult = dict[str, Any]
READINESS_RESULT_SCHEMA = "simpro-publish-readiness-result/v1"
LANDING_PAGE_SCORE_THRESHOLD = 75


class ExecutedReadinessResult(dict[str, Any]):
    """A readiness result from the gate runner, bound to its workspace."""

    __slots__ = ("_workspace_root",)

    def __init__(self, value: Mapping[str, Any], *, workspace_root: Path) -> None:
        super().__init__(value)
        self._workspace_root = workspace_root.resolve()
