"""Legacy URL-result cache retained for explicit compatibility injection."""

from __future__ import annotations

import hashlib
import json
import math
import time
from pathlib import Path
from typing import Any, Callable


FUTURE_SKEW_SECONDS = 60


class UrlResolutionCache:
    def __init__(
        self,
        cache_dir: Path,
        *,
        result_factory: Callable[..., Any],
        expire_seconds: int,
    ) -> None:
        self.cache_dir = cache_dir
        self.expire_seconds = expire_seconds
        self.result_factory = result_factory

    def get(self, url: str) -> Any | None:
        path = self._path(url)
        if not path.exists():
            return None
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None
        if self._expired(payload.get("checked_at")):
            path.unlink(missing_ok=True)
            return None
        if payload.get("status") != "resolved":
            return None
        return self.result_factory(
            url=payload.get("url", url),
            status="resolved",
            status_code=payload.get("status_code"),
            reason=payload.get("reason", "cached resolved URL"),
            final_url=payload.get("final_url", payload.get("url", url)),
        )

    def set(self, result: Any) -> None:
        if not result.passed:
            return
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        payload = {
            "url": result.url,
            "status": result.status,
            "status_code": result.status_code,
            "reason": result.reason,
            "final_url": result.final_url or result.url,
            "checked_at": time.time(),
        }
        path = self._path(result.url)
        temporary = path.with_suffix(".tmp")
        temporary.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
        temporary.replace(path)

    def _expired(self, checked_at: Any) -> bool:
        now = time.time()
        return (
            isinstance(checked_at, bool)
            or not isinstance(checked_at, (int, float))
            or not math.isfinite(checked_at)
            or checked_at > now + FUTURE_SKEW_SECONDS
            or now - checked_at > self.expire_seconds
        )

    def _path(self, url: str) -> Path:
        key = hashlib.sha256(url.encode("utf-8")).hexdigest()
        return self.cache_dir / f"{key}.json"


class NullUrlResolutionCache:
    def get(self, url: str) -> None:
        return None

    def set(self, result: Any) -> None:
        return None
