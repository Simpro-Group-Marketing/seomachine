"""Run-scoped ownership, caches, and external-resource lifecycle."""

from __future__ import annotations

import json
import threading
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Any

from ..connector_snapshot import ConnectorWorkflowSnapshot
from ..connector_snapshot.cache import canonical_connector_value
from ..public_http import DEFAULT_HTTP_BATCH_POLICY
from .artifact_io import resolve_input
from .artifact_store import InstrumentedArtifactStore
from .artifact_views import freeze_value
from .git_registry import GitRegistryState, capture_git_registry_state
from .inputs import ReadinessInputs
from .telemetry import ReadinessTelemetry


class ValidationSession:
    """Own all reusable validation state and close resources exactly once."""

    __slots__ = (
        "_cache_lock",
        "_closed",
        "_connector_workflow",
        "_context_result",
        "_findings",
        "_git_registry_states",
        "_normalized_sources",
        "_normalized_source_bytes",
        "_network_material_budget_bytes",
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
        network_material_budget_bytes: int = (
            DEFAULT_HTTP_BATCH_POLICY.max_aggregate_response_bytes
        ),
    ) -> None:
        if not isinstance(inputs, ReadinessInputs):
            raise TypeError("ValidationSession requires ReadinessInputs")
        self.inputs = inputs
        self.telemetry = telemetry
        self._transport_factory = transport_factory
        _validate_network_material_budget(network_material_budget_bytes)
        self._network_material_budget_bytes = network_material_budget_bytes
        self._connector_workflow = ConnectorWorkflowSnapshot(
            client_factory=connector_factory,
            claim_loader=claim_loader,
            observer=self._connector_event,
        )
        self._context_result: Any = None
        self._findings: dict[str, tuple[dict[str, Any], ...]] = {}
        self._transport: Any = None
        self._normalized_sources: dict[str, Any] = {}
        self._normalized_source_bytes = 0
        self._git_registry_states: dict[Path, GitRegistryState] = {}
        self._cache_lock = threading.RLock()
        self._closed = False

    @classmethod
    def capture(
        cls,
        input_paths: Mapping[str, str | Path | None],
        *,
        workspace_root: str | Path,
        connector_factory: Callable[[], Any] | None = None,
        claim_loader: Callable[[Any], Any] | None = None,
        transport_factory: Callable[[], Any] | None = None,
        telemetry: ReadinessTelemetry | None = None,
        network_material_budget_bytes: int = (
            DEFAULT_HTTP_BATCH_POLICY.max_aggregate_response_bytes
        ),
    ) -> "ValidationSession":
        """Capture all inputs and transfer ownership to one session."""
        inputs = ReadinessInputs.capture(
            input_paths,
            workspace_root=workspace_root,
            telemetry=telemetry,
        )
        return cls(
            inputs,
            connector_factory=connector_factory,
            claim_loader=claim_loader,
            transport_factory=transport_factory,
            telemetry=telemetry,
            network_material_budget_bytes=network_material_budget_bytes,
        )

    @property
    def artifacts(self) -> InstrumentedArtifactStore:
        return self.inputs.artifacts

    def __enter__(self) -> "ValidationSession":
        if self._closed:
            raise RuntimeError("ValidationSession is already closed")
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        self.close()

    def connector(self) -> Any:
        self._require_open()
        return self._connector_workflow.client()

    def validated_claim_set(self) -> Any:
        self._require_open()
        return self._connector_workflow.validated_claim_set()

    def connector_result(
        self,
        operation: str,
        request: Any,
        loader: Callable[[], Any] | None = None,
    ) -> Any:
        """Cache one successful connector operation by canonical request data."""
        self._require_open()
        if loader is None:
            if not callable(request):
                raise TypeError("connector result loader is required")
            loader = request
            request = None
        return self._connector_workflow.result(operation, request, loader)

    def normalized_source(self, source_key: str, loader: Callable[[], Any]) -> Any:
        """Cache one successful, immutable normalized-source parse."""
        self._require_open()
        key = _normalized_source_key(source_key)
        with self._cache_lock:
            if key in self._normalized_sources:
                self._increment("normalized_source_cache_hits")
                return self._normalized_sources[key]
            loaded = loader()
            byte_count = _normalized_material_bytes(loaded)
            projected = self._normalized_source_bytes + byte_count
            if projected > self._network_material_budget_bytes:
                raise ValueError("normalized source exceeds session network material budget")
            value = freeze_value(loaded)
            self._normalized_sources[key] = value
            self._normalized_source_bytes = projected
            self._increment("normalized_source_parses")
            if self.telemetry is not None:
                self.telemetry.set_gauge("normalized_source_bytes", projected)
            return value

    def git_registry_state(
        self,
        registry_path: str | Path,
        loader: Callable[[], object],
        verifier: Callable[..., GitRegistryState] | None = None,
    ) -> GitRegistryState:
        """Cache one successfully verified Git registry by canonical path."""
        self._require_open()
        path = resolve_input(
            registry_path,
            workspace_root=self.inputs.workspace_root,
            field="Git registry",
        )
        with self._cache_lock:
            cached = self._git_registry_states.get(path)
            if cached is not None:
                return cached
            state = (verifier or capture_git_registry_state)(
                loader(),
                workspace_root=self.inputs.workspace_root,
            )
            if not isinstance(state, GitRegistryState) or state.registry_path != path:
                raise ValueError("Git registry verifier returned mismatched state")
            self._git_registry_states[path] = state
            self._increment("git_state_loads")
            return state

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
        transport = self._detach_transport()
        self._clear_caches()
        try:
            self._close_transport(transport)
        finally:
            self._connector_workflow.close()

    def _detach_transport(self) -> Any:
        transport = self._transport
        self._transport = None
        return transport

    def _close_transport(self, transport: Any) -> None:
        if transport is None:
            return
        if not bool(getattr(transport, "reports_events", False)):
            counters = getattr(transport, "counters", {})
            if isinstance(counters, Mapping):
                self._increment("http_requests", int(counters.get("requests", 0)))
                self._increment("cache_hits", int(counters.get("cache_hits", 0)))
                self._increment("cache_misses", int(counters.get("cache_misses", 0)))
        transport.close()

    def _clear_caches(self) -> None:
        with self._cache_lock:
            self._normalized_sources.clear()
            self._normalized_source_bytes = 0
            self._git_registry_states.clear()
            if self.telemetry is not None:
                self.telemetry.set_gauge("normalized_source_bytes", 0)

    def _increment(self, counter: str, amount: int = 1) -> None:
        if self.telemetry is not None:
            self.telemetry.increment(counter, amount)

    def _connector_event(self, event: str) -> None:
        counter = {
            "client": "connector_clients",
            "operation": "connector_operations",
            "cache_hit": "connector_result_cache_hits",
            "cache_miss": "connector_result_cache_misses",
        }.get(event)
        if counter is None:
            raise ValueError(f"unknown connector telemetry event: {event}")
        self._increment(counter)

    def _require_open(self) -> None:
        if self._closed:
            raise RuntimeError("ValidationSession is closed")


def _normalized_source_key(value: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("normalized source key is required")
    return value.strip()


def _normalized_material_bytes(value: Any) -> int:
    if isinstance(value, str):
        return len(value.encode("utf-8"))
    canonical = canonical_connector_value(value)
    return len(
        json.dumps(
            canonical,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    )


def _validate_network_material_budget(value: object) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ValueError("network material budget must be a positive integer")


__all__ = ["GitRegistryState", "ValidationSession"]
