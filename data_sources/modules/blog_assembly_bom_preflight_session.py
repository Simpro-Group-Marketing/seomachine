"""Compatibility facade for blog BOM preflight session adapters."""

try:
    from .blog_bom_validation.preflight_session import (
        load_historical_bom,
        load_historical_bom_dispatch,
        load_preflight,
        load_preflight_dispatch,
        load_receipts,
        validate_prior_preflight,
    )
except ImportError:  # pragma: no cover - top-level compatibility.
    from blog_bom_validation.preflight_session import (
        load_historical_bom,
        load_historical_bom_dispatch,
        load_preflight,
        load_preflight_dispatch,
        load_receipts,
        validate_prior_preflight,
    )

__all__ = [
    "load_historical_bom",
    "load_historical_bom_dispatch",
    "load_preflight",
    "load_preflight_dispatch",
    "load_receipts",
    "validate_prior_preflight",
]
