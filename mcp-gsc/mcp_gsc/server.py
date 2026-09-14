"""FastMCP composition root for the Google Search Console tools."""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from .analytics import (
    get_performance_overview,
    get_search_analytics,
    get_search_by_page_query,
)
from .analytics_advanced import (
    compare_search_periods,
    get_advanced_search_analytics,
)
from .auth import reauthenticate
from .formatting import get_creator_info
from .inspection import (
    batch_url_inspection,
    check_indexing_issues,
    inspect_url_enhanced,
)
from .properties import add_site, delete_site, get_site_details, list_properties
from .sitemaps import (
    delete_sitemap,
    get_sitemap_details,
    get_sitemaps,
    list_sitemaps_enhanced,
    manage_sitemaps,
    submit_sitemap,
)

mcp = FastMCP("gsc-server")

for tool in (
    list_properties,
    add_site,
    delete_site,
    get_search_analytics,
    get_site_details,
    get_sitemaps,
    inspect_url_enhanced,
    batch_url_inspection,
    check_indexing_issues,
    get_performance_overview,
    get_advanced_search_analytics,
    compare_search_periods,
    get_search_by_page_query,
    list_sitemaps_enhanced,
    get_sitemap_details,
    submit_sitemap,
    delete_sitemap,
    manage_sitemaps,
    get_creator_info,
    reauthenticate,
):
    mcp.tool()(tool)


def main() -> None:
    """Run the MCP server over stdio."""
    mcp.run(transport="stdio")


__all__ = [
    "add_site",
    "batch_url_inspection",
    "check_indexing_issues",
    "compare_search_periods",
    "delete_site",
    "delete_sitemap",
    "get_advanced_search_analytics",
    "get_creator_info",
    "get_performance_overview",
    "get_search_analytics",
    "get_search_by_page_query",
    "get_site_details",
    "get_sitemap_details",
    "get_sitemaps",
    "inspect_url_enhanced",
    "list_properties",
    "list_sitemaps_enhanced",
    "main",
    "manage_sitemaps",
    "mcp",
    "reauthenticate",
    "submit_sitemap",
]
