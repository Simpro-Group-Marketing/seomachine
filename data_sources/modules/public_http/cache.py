"""Optional bounded persistent cache for public HTTP response snapshots."""

from __future__ import annotations

from collections import OrderedDict
from contextlib import contextmanager
from pathlib import Path
import threading
from typing import Any

try:  # Cache loss affects performance, never proof verdicts.
    from diskcache import Cache, Lock
except ImportError:  # pragma: no cover - exercised in dependency-light installs.
    Cache = None
    Lock = None


class ResponseMemoryCache:
    """Thread-safe byte-accounted LRU for one transport process."""

    def __init__(self, *, max_bytes: int, observer: Any = None) -> None:
        if isinstance(max_bytes, bool) or not isinstance(max_bytes, int) or max_bytes < 1:
            raise ValueError("HTTP memo budget must be a positive integer")
        self._max_bytes = max_bytes
        self._bytes = 0
        self._entries: OrderedDict[str, tuple[Any, int]] = OrderedDict()
        self._observer = observer
        self._lock = threading.RLock()

    @property
    def retained_bytes(self) -> int:
        return self._bytes

    def get(self, key: str) -> Any | None:
        with self._lock:
            entry = self._entries.get(key)
            if entry is None:
                return None
            self._entries.move_to_end(key)
            return entry[0]

    def set(self, key: str, value: Any, *, weight: int) -> bool:
        if isinstance(weight, bool) or not isinstance(weight, int) or weight < 1:
            raise ValueError("HTTP memo entry weight must be positive")
        with self._lock:
            if weight > self._max_bytes:
                return False
            previous = self._entries.pop(key, None)
            if previous is not None:
                self._bytes -= previous[1]
                self._observe(-previous[1])
            while self._bytes + weight > self._max_bytes:
                _, (_, evicted_weight) = self._entries.popitem(last=False)
                self._bytes -= evicted_weight
                self._observe(-evicted_weight)
            self._entries[key] = (value, weight)
            self._bytes += weight
            self._observe(weight)
            return True

    def clear(self) -> None:
        with self._lock:
            if self._bytes:
                self._observe(-self._bytes)
            self._entries.clear()
            self._bytes = 0

    def _observe(self, amount: int) -> None:
        if self._observer is not None:
            try:
                self._observer(amount)
            except Exception:
                return


class ResponseCache:
    def __init__(self, path: Path, *, size_limit: int) -> None:
        self._cache: Any = None
        if Cache is not None:
            try:
                self._cache = Cache(str(path), size_limit=size_limit)
            except Exception:
                self._cache = None

    def get(self, key: str) -> dict[str, Any] | None:
        if self._cache is None:
            return None
        try:
            value = self._cache.get(key)
        except Exception:
            return None
        if not isinstance(value, dict):
            self.delete(key)
            return None
        return value

    def set(self, key: str, value: dict[str, Any], *, ttl: int) -> None:
        if self._cache is None:
            return
        try:
            self._cache.set(key, value, expire=ttl)
        except Exception:
            return

    def delete(self, key: str) -> None:
        if self._cache is None:
            return
        try:
            self._cache.delete(key)
        except Exception:
            return

    @contextmanager
    def lock(self, key: str):
        if self._cache is None or Lock is None:
            yield False
            return
        try:
            lock = Lock(self._cache, f"request-lock:{key}", expire=30)
            lock.acquire()
        except Exception:
            yield False
            return
        try:
            yield True
        finally:
            try:
                lock.release()
            except Exception:
                pass

    def close(self) -> None:
        if self._cache is None:
            return
        try:
            self._cache.close()
        except Exception:
            pass
        self._cache = None
