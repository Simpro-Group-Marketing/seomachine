"""Compatibility facade for the historical ``gsc_server`` module."""

from mcp_gsc.auth import (
    GSC_CREDENTIALS_PATH,
    OAUTH_CLIENT_SECRETS_FILE,
    POSSIBLE_CREDENTIAL_PATHS,
    SCOPES,
    SCRIPT_DIR,
    SKIP_OAUTH,
    TOKEN_FILE,
    get_gsc_service,
    get_gsc_service_oauth,
)
from mcp_gsc.contracts import DATA_STATE
from mcp_gsc.formatting import site_not_found_error as _site_not_found_error
from mcp_gsc.server import (
    add_site,
    batch_url_inspection,
    check_indexing_issues,
    compare_search_periods,
    delete_site,
    delete_sitemap,
    get_advanced_search_analytics,
    get_creator_info,
    get_performance_overview,
    get_search_analytics,
    get_search_by_page_query,
    get_site_details,
    get_sitemap_details,
    get_sitemaps,
    inspect_url_enhanced,
    list_properties,
    list_sitemaps_enhanced,
    main,
    manage_sitemaps,
    mcp,
    reauthenticate,
    submit_sitemap,
)

__all__ = [
    "DATA_STATE",
    "GSC_CREDENTIALS_PATH",
    "OAUTH_CLIENT_SECRETS_FILE",
    "POSSIBLE_CREDENTIAL_PATHS",
    "SCOPES",
    "SCRIPT_DIR",
    "SKIP_OAUTH",
    "TOKEN_FILE",
    "_site_not_found_error",
    "add_site",
    "batch_url_inspection",
    "check_indexing_issues",
    "compare_search_periods",
    "delete_site",
    "delete_sitemap",
    "get_advanced_search_analytics",
    "get_creator_info",
    "get_gsc_service",
    "get_gsc_service_oauth",
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


if __name__ == "__main__":
    main()
