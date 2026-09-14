"""Compatibility facade for AEO/GEO scoring."""

from .content_scoring.aeo_orchestration import (
    NON_VISIBLE_HTML_BLOCK_RE,
    PASS_THRESHOLD,
    rate_aeo_geo,
)
from .content_scoring.aeo_metadata_schema import CANONICAL_SCHEMA_ENTITIES

__all__ = [
    "CANONICAL_SCHEMA_ENTITIES",
    "NON_VISIBLE_HTML_BLOCK_RE",
    "PASS_THRESHOLD",
    "rate_aeo_geo",
]
