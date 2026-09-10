"""Stable compatibility facade for publish-readiness APIs and CLI."""

from __future__ import annotations

import sys

try:
    from . import publish_readiness_core as _implementation
except ImportError:  # pragma: no cover - supports direct script execution.
    import publish_readiness_core as _implementation


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(_implementation.main())

# Preserve every public and private legacy patch point during the P0 package split.
sys.modules[__name__] = _implementation
