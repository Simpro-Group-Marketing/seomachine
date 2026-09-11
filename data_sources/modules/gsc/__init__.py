"""Google Search Console client support."""

from .pagination import (
    GSC_MAX_PAGE_ROWS,
    GSC_MAX_WORKFLOW_ROWS,
    GscPaginationError,
    GscQueryMode,
    GscRowCapExceeded,
    iter_search_analytics_rows,
    query_search_analytics,
)

__all__ = [
    "GSC_MAX_PAGE_ROWS",
    "GSC_MAX_WORKFLOW_ROWS",
    "GscPaginationError",
    "GscQueryMode",
    "GscRowCapExceeded",
    "iter_search_analytics_rows",
    "query_search_analytics",
]
