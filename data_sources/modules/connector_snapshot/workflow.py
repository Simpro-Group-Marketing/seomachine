"""Lifecycle ownership for one connector workflow snapshot."""

from __future__ import annotations

import threading
from collections.abc import Callable
from typing import Any

from .cache import ConnectorSnapshot


class ConnectorWorkflowSnapshot:
    """Own one connector client, revision snapshot, claim set, and result cache."""

    __slots__ = (
        "_claim_loader",
        "_claim_set",
        "_client",
        "_client_factory",
        "_closed",
        "_lock",
        "_observer",
        "_result_cache",
        "_workflow_context",
    )

    def __init__(
        self,
        *,
        client_factory: Callable[[], Any] | None,
        claim_loader: Callable[[Any], Any] | None,
        observer: Callable[[str], None] | None = None,
    ) -> None:
        self._client_factory = client_factory
        self._claim_loader = claim_loader
        self._observer = observer
        self._client: Any = None
        self._workflow_context: Any = None
        self._claim_set: Any = None
        self._result_cache = ConnectorSnapshot(self._cache_event)
        self._lock = threading.RLock()
        self._closed = False

    def client(self) -> Any:
        with self._lock:
            self._require_open()
            if self._client is None:
                if self._client_factory is None:
                    raise RuntimeError("ValidationSession has no connector factory")
                candidate = self._client_factory()
                context = _enter_workflow_context(candidate)
                self._client = candidate
                self._workflow_context = context
                self._observe("client")
            return self._client

    def validated_claim_set(self) -> Any:
        with self._lock:
            self._require_open()
            if self._claim_set is None:
                if self._claim_loader is None:
                    raise RuntimeError("ValidationSession has no validated-claim loader")
                loaded = self._claim_loader(self.client())
                self._claim_set = loaded
                self._observe("operation")
            return self._claim_set

    def result(
        self,
        operation: str,
        request: Any,
        loader: Callable[[], Any],
    ) -> Any:
        self._require_open()

        def observed_loader() -> Any:
            self._observe("operation")
            return loader()

        return self._result_cache.result(operation, request, observed_loader)

    def close(self) -> None:
        with self._lock:
            if self._closed:
                return
            self._closed = True
            client = self._client
            context = self._workflow_context
            self._client = None
            self._workflow_context = None
            self._claim_set = None
            self._result_cache.clear()
        try:
            if context is not None:
                context.__exit__(None, None, None)
        finally:
            close = getattr(client, "close", None)
            if callable(close):
                close()

    def _cache_event(self, event: str) -> None:
        self._observe(f"cache_{event}")

    def _observe(self, event: str) -> None:
        if self._observer is not None:
            self._observer(event)

    def _require_open(self) -> None:
        if self._closed:
            raise RuntimeError("ValidationSession is closed")


def _enter_workflow_context(client: Any) -> Any:
    workflow_snapshot = getattr(type(client), "workflow_snapshot", None)
    if not callable(workflow_snapshot):
        return None
    context = workflow_snapshot(client)
    enter = getattr(context, "__enter__", None)
    exit_context = getattr(context, "__exit__", None)
    if not callable(enter) or not callable(exit_context):
        return None
    if enter() is client:
        return context
    exit_context(None, None, None)
    raise RuntimeError("connector workflow_snapshot must return its client")


__all__ = ["ConnectorWorkflowSnapshot"]
