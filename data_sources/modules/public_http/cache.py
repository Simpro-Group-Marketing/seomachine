"""Optional bounded persistent cache for public HTTP response snapshots."""

from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from typing import Any

try:  # Cache loss affects performance, never proof verdicts.
    from diskcache import Cache, Lock
except ImportError:  # pragma: no cover - exercised in dependency-light installs.
    Cache = None
    Lock = None


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
