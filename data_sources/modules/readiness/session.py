"""Run-scoped caches and lifecycle for one immutable readiness execution."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from typing import Any

from .inputs import ReadinessInputs
from .telemetry import ReadinessTelemetry


class ValidationSession:
    """Own reusable validation state and close external resources exactly once."""

    __slots__ = (
        "_claim_loader",
        "_claim_set",
        "_closed",
        "_connector",
        "_connector_factory",
        "_context_result",
        "_findings",
        "inputs",
        "telemetry",
    )

    def __init__(
        self,
        inputs: ReadinessInputs,
        *,
        connector_factory: Callable[[], Any] | None = None,
        claim_loader: Callable[[Any], Any] | None = None,
        telemetry: ReadinessTelemetry | None = None,
    ) -> None:
        if not isinstance(inputs, ReadinessInputs):
            raise TypeError("ValidationSession requires ReadinessInputs")
        self.inputs = inputs
        self.telemetry = telemetry
        self._connector_factory = connector_factory
        self._claim_loader = claim_loader
        self._connector: Any = None
        self._claim_set: Any = None
        self._context_result: Any = None
        self._findings: dict[str, tuple[dict[str, Any], ...]] = {}
        self._closed = False

    def __enter__(self) -> "ValidationSession":
        if self._closed:
            raise RuntimeError("ValidationSession is already closed")
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        self.close()

    def connector(self) -> Any:
        self._require_open()
        if self._connector is None:
            if self._connector_factory is None:
                raise RuntimeError("ValidationSession has no connector factory")
            self._connector = self._connector_factory()
            if self.telemetry is not None:
                self.telemetry.increment("connector_clients")
        return self._connector

    def validated_claim_set(self) -> Any:
        self._require_open()
        if self._claim_set is None:
            if self._claim_loader is None:
                raise RuntimeError("ValidationSession has no validated-claim loader")
            self._claim_set = self._claim_loader(self.connector())
            if self.telemetry is not None:
                self.telemetry.increment("connector_operations")
        return self._claim_set

    def context_result(self) -> Any:
        self._require_open()
        return self._context_result

    def set_context_result(self, value: Any) -> None:
        self._require_open()
        if self._context_result is not None:
            raise ValueError("ValidationSession context result is already set")
        self._context_result = value

    def record_findings(
        self,
        gate_name: str,
        findings: Sequence[Mapping[str, Any]],
    ) -> None:
        self._require_open()
        if not isinstance(gate_name, str) or not gate_name:
            raise ValueError("gate_name is required")
        if gate_name in self._findings:
            raise ValueError(f"findings already recorded for gate: {gate_name}")
        self._findings[gate_name] = tuple(dict(row) for row in findings)

    def findings(self, gate_name: str) -> list[dict[str, Any]] | None:
        self._require_open()
        rows = self._findings.get(gate_name)
        return None if rows is None else [dict(row) for row in rows]

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        connector = self._connector
        self._connector = None
        if connector is not None:
            close = getattr(connector, "close", None)
            if callable(close):
                close()

    def _require_open(self) -> None:
        if self._closed:
            raise RuntimeError("ValidationSession is closed")

