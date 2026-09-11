"""Run- and worker-scoped locations for disposable runtime state."""

from __future__ import annotations

import os
from pathlib import Path


RUNTIME_ROOT_ENV = "SEOMACHINE_RUNTIME_ROOT"


def cache_path(*parts: str) -> Path:
    """Return a cache path below the injected runtime root or local .cache."""
    return _base_path("cache", fallback=Path(".cache")).joinpath(*parts)


def spool_path() -> Path:
    """Return the directory used for temporary subprocess spools."""
    return _base_path("spool", fallback=Path(".cache") / "subprocess") / "v1"


def _base_path(kind: str, *, fallback: Path) -> Path:
    configured = os.getenv(RUNTIME_ROOT_ENV)
    if not configured:
        return fallback
    return Path(configured) / kind
