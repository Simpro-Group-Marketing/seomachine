"""Explicit runtime dependencies for PAA collection."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable


ExecutableResolver = Callable[[], str | None]
SubprocessRunner = Callable[..., Any]


@dataclass(frozen=True, slots=True)
class PaaDependencies:
    """Inject environment discovery and bounded subprocess execution."""

    executable_resolver: ExecutableResolver
    subprocess_runner: SubprocessRunner


__all__ = ["ExecutableResolver", "PaaDependencies", "SubprocessRunner"]
