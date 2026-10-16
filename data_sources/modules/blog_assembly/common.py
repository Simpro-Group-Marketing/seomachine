"""Archived blog assembly BOM schema names that the content scorer still recognizes."""

from __future__ import annotations

ARCHIVED_BOM_SCHEMAS = frozenset({
    "simpro-blog-assembly-bom/v1",
    "simpro-blog-assembly-bom/v2",
    "simpro-blog-assembly-bom/v3",
    "simpro-blog-assembly-bom/v4",
})
NON_CONNECTOR_REASON = (
    "Final article contains no Simpro brand, URL, or connector-sensitive language."
)
