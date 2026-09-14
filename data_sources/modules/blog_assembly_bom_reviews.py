"""Compatibility facade for blog BOM machine-review checks."""

try:
    from .blog_bom_validation.review_validation import check_machine_reviews
except ImportError:  # pragma: no cover - top-level compatibility.
    from blog_bom_validation.review_validation import check_machine_reviews

__all__ = ["check_machine_reviews"]
