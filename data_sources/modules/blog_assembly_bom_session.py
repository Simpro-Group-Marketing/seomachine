"""Compatibility facade for session-backed blog BOM checks."""

try:
    from .blog_bom_validation.session_validation import (
        check_editorial_plan,
        check_editorial_plan_dispatch,
    )
except ImportError:  # pragma: no cover - top-level compatibility.
    from blog_bom_validation.session_validation import (
        check_editorial_plan,
        check_editorial_plan_dispatch,
    )

__all__ = ["check_editorial_plan", "check_editorial_plan_dispatch"]
