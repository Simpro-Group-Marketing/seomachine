"""Compatibility entrypoint for the repository-wide structure checker."""

from __future__ import annotations

try:
    from .check_python_structure import main
except ImportError:  # pragma: no cover - direct script execution.
    from check_python_structure import main


if __name__ == "__main__":
    raise SystemExit(main())
