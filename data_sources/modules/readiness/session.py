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
        "_connector_snapshot",
        "_context_result",
        "_findings",
        "_transport",
        "_transport_factory",
        "inputs",
        "telemetry",
    )

    def __init__(
        self,
        inputs: ReadinessInputs,
        *,
        connector_factory: Callable[[], Any] | None = None,
        claim_loader: Callable[[Any], Any] | None = None,
        transport_factory: Callable[[], Any] | None = None,
        telemetry: ReadinessTelemetry | None = None,
    ) -> None:
        if not isinstance(inputs, ReadinessInputs):
            raise TypeError("ValidationSession requires ReadinessInputs")
        self.inputs = inputs
        self.telemetry = telemetry
        self._connector_factory = connector_factory
        self._claim_loader = claim_loader
        self._transport_factory = transport_factory
        self._connector: Any = None
        self._connector_snapshot: Any = None
        self._claim_set: Any = None
        self._context_result: Any = None
        self._findings: dict[str, tuple[dict[str, Any], ...]] = {}
        self._transport: Any = None
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
            workflow_snapshot = getattr(type(self._connector), "workflow_snapshot", None)
            if callable(workflow_snapshot):
                candidate = workflow_snapshot(self._connector)
                enter = getattr(candidate, "__enter__", None)
                exit_snapshot = getattr(candidate, "__exit__", None)
                if callable(enter) and callable(exit_snapshot):
                    self._connector_snapshot = candidate
                    snapshot_client = enter()
                    if snapshot_client is not self._connector:
                        exit_snapshot(None, None, None)
                        self._connector_snapshot = None
                        raise RuntimeError("connector workflow_snapshot must return its client")
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

    def transport(self) -> Any:
        self._require_open()
        if self._transport is None:
            if self._transport_factory is None:
                raise RuntimeError("ValidationSession has no transport factory")
            self._transport = self._transport_factory()
        return self._transport

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
        snapshot = self._connector_snapshot
        transport = self._transport
        self._connector = None
        self._connector_snapshot = None
        self._transport = None
        try:
            if transport is not None:
                counters = getattr(transport, "counters", {})
                if self.telemetry is not None and isinstance(counters, Mapping):
                    self.telemetry.increment("http_requests", int(counters.get("requests", 0)))
                    self.telemetry.increment("cache_hits", int(counters.get("cache_hits", 0)))
                    self.telemetry.increment("cache_misses", int(counters.get("cache_misses", 0)))
                transport.close()
        finally:
            try:
                if snapshot is not None:
                    snapshot.__exit__(None, None, None)
            finally:
                if connector is not None:
                    close = getattr(connector, "close", None)
                    if callable(close):
                        close()

    def _require_open(self) -> None:
        if self._closed:
            raise RuntimeError("ValidationSession is closed")
