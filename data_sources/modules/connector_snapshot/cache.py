"""Canonical connector request caching for explicitly read-only operations."""

from __future__ import annotations

import json
import threading
from collections.abc import Callable, Mapping
from pathlib import Path
from types import MappingProxyType
from typing import Any

from ..artifact_runtime.limits import CONNECTOR_RESULT_CACHE_MAX_BYTES


CACHEABLE_CONNECTOR_OPERATIONS = frozenset(
    {
        "build_context",
        "claims",
        "describe",
        "expand",
        "pack_internal_strategy",
        "read",
        "read_internal_strategy",
        "search",
        "search_internal_strategy",
        "status",
        "validate_context",
        "vault_build_context",
        "vault_claims",
        "vault_describe",
        "vault_expand",
        "vault_pack_internal_strategy",
        "vault_read",
        "vault_read_internal_strategy",
        "vault_search",
        "vault_search_internal_strategy",
        "vault_status",
        "vault_validate_context",
    }
)


class ConnectorSnapshot:
    """Cache immutable successful connector results for one validation run."""

    __slots__ = ("_cache", "_bytes", "_byte_observer", "_lock", "_max_bytes", "_observer")

    def __init__(
        self,
        observer: Callable[[str], None] | None = None,
        *,
        max_bytes: int = CONNECTOR_RESULT_CACHE_MAX_BYTES,
        byte_observer: Callable[[int], None] | None = None,
    ) -> None:
        if isinstance(max_bytes, bool) or not isinstance(max_bytes, int) or max_bytes < 1:
            raise ValueError("connector cache budget must be a positive integer")
        self._cache: dict[str, Any] = {}
        self._bytes = 0
        self._max_bytes = max_bytes
        self._byte_observer = byte_observer
        self._lock = threading.RLock()
        self._observer = observer

    def result(
        self,
        operation: str,
        request: Any,
        loader: Callable[[], Any],
    ) -> Any:
        """Return one immutable result; failures are never memoized."""
        key = connector_cache_key(operation, request)
        if operation.strip() not in CACHEABLE_CONNECTOR_OPERATIONS:
            raise ValueError(f"connector operation is not cacheable: {operation.strip()}")
        if not callable(loader):
            raise TypeError("connector result loader is required")
        with self._lock:
            if key in self._cache:
                self._observe("hit")
                return self._cache[key]
            self._observe("miss")
            loaded = loader()
            encoded = json.dumps(
                canonical_connector_value(loaded),
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
            projected = self._bytes + len(encoded)
            if projected > self._max_bytes:
                raise ValueError("connector result cache byte budget exceeded")
            value = freeze_connector_value(loaded)
            self._cache[key] = value
            self._bytes = projected
            self._observe_bytes(len(encoded))
            return value

    def clear(self) -> None:
        with self._lock:
            self._cache.clear()
            if self._bytes:
                self._observe_bytes(-self._bytes)
            self._bytes = 0

    @property
    def retained_bytes(self) -> int:
        with self._lock:
            return self._bytes

    def _observe_bytes(self, amount: int) -> None:
        if self._byte_observer is not None:
            self._byte_observer(amount)

    def _observe(self, event: str) -> None:
        if self._observer is not None:
            self._observer(event)


def connector_cache_key(operation: str, request: Any) -> str:
    if not isinstance(operation, str) or not operation.strip():
        raise ValueError("connector operation is required")
    canonical = canonical_connector_value(request)
    encoded = json.dumps(canonical, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
    return f"{operation.strip()}\0{encoded}"


def canonical_connector_value(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, Path):
        return str(value.resolve(strict=False))
    if isinstance(value, Mapping):
        if not all(isinstance(key, str) for key in value):
            raise TypeError("connector request mapping keys must be strings")
        return {key: canonical_connector_value(value[key]) for key in sorted(value)}
    if isinstance(value, (list, tuple)):
        return [canonical_connector_value(item) for item in value]
    raise TypeError(f"unsupported connector request cache value: {type(value).__name__}")


def freeze_connector_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        return MappingProxyType(
            {str(key): freeze_connector_value(item) for key, item in value.items()}
        )
    if isinstance(value, (list, tuple)):
        return tuple(freeze_connector_value(item) for item in value)
    if isinstance(value, (set, frozenset)):
        return frozenset(freeze_connector_value(item) for item in value)
    return value


__all__ = [
    "CACHEABLE_CONNECTOR_OPERATIONS",
    "ConnectorSnapshot",
    "canonical_connector_value",
    "connector_cache_key",
    "freeze_connector_value",
]
