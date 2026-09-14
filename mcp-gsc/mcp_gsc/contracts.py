"""Stable environment and tool-registration contracts."""

from __future__ import annotations

import os


RAW_DATA_STATE = os.environ.get("GSC_DATA_STATE", "all").lower().strip()
if RAW_DATA_STATE not in ("all", "final"):
    raise ValueError(
        f"Invalid GSC_DATA_STATE value '{RAW_DATA_STATE}'. "
        "Accepted values are 'all' (default, matches GSC dashboard) or "
        "'final' (2-3 day lag)."
    )
DATA_STATE = RAW_DATA_STATE

TOOL_NAMES = (
    "list_properties",
    "add_site",
    "delete_site",
    "get_search_analytics",
    "get_site_details",
    "get_sitemaps",
    "inspect_url_enhanced",
    "batch_url_inspection",
    "check_indexing_issues",
    "get_performance_overview",
    "get_advanced_search_analytics",
    "compare_search_periods",
    "get_search_by_page_query",
    "list_sitemaps_enhanced",
    "get_sitemap_details",
    "submit_sitemap",
    "delete_sitemap",
    "manage_sitemaps",
    "get_creator_info",
    "reauthenticate",
)

__all__ = ["DATA_STATE", "TOOL_NAMES"]
