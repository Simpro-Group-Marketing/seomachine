"""Compatibility facade for blog BOM snapshot adapters."""

try:
    from .blog_bom_validation.snapshot_adapters import (
        check_captured_machine_reviews,
        check_machine_review_pair_payloads,
        check_machine_review_payload,
        expanded_input_rows,
        json_artifact,
        json_snapshot,
        load_primary_artifacts,
        optional_text,
        sidecar_binding_errors,
        text_artifact,
        verify_artifact,
    )
except ImportError:  # pragma: no cover - top-level compatibility.
    from blog_bom_validation.snapshot_adapters import (
        check_captured_machine_reviews,
        check_machine_review_pair_payloads,
        check_machine_review_payload,
        expanded_input_rows,
        json_artifact,
        json_snapshot,
        load_primary_artifacts,
        optional_text,
        sidecar_binding_errors,
        text_artifact,
        verify_artifact,
    )

__all__ = [
    "check_captured_machine_reviews",
    "check_machine_review_pair_payloads",
    "check_machine_review_payload",
    "expanded_input_rows",
    "json_artifact",
    "json_snapshot",
    "load_primary_artifacts",
    "optional_text",
    "sidecar_binding_errors",
    "text_artifact",
    "verify_artifact",
]
