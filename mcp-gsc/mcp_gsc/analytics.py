"""Common Search Analytics query and overview tools."""

from __future__ import annotations

from datetime import datetime, timedelta

import mcp_gsc.auth as auth
from .contracts import DATA_STATE
from .formatting import site_not_found_error
from data_sources.modules.artifact_runtime.limits import (
    GSC_WORKFLOW_MAX_BYTES,
    MCP_TEXT_MAX_BYTES,
)
from data_sources.modules.bounded_io import OutputByteLimitError


async def get_search_analytics(
    site_url: str,
    days: int = 28,
    dimensions: str = "query",
    row_limit: int = 20,
) -> str:
    """Get grouped Search Analytics data for a property."""
    try:
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=days)
        dimension_list = [dimension.strip() for dimension in dimensions.split(",")]
        request = {
            "startDate": start_date.strftime("%Y-%m-%d"),
            "endDate": end_date.strftime("%Y-%m-%d"),
            "dimensions": dimension_list,
            "dataState": DATA_STATE,
        }
        rows = list(
            _iter_gsc_rows(
                site_url=site_url,
                body=request,
                max_rows=min(max(1, row_limit), 500),
            )
        )
        if not rows:
            return (
                f"No search analytics data found for {site_url} in the last "
                f"{days} days."
            )
        lines = [
            f"Search analytics for {site_url} (last {days} days):",
            "\n" + "-" * 80 + "\n",
        ]
        header = [dimension.capitalize() for dimension in dimension_list]
        header.extend(["Clicks", "Impressions", "CTR", "Position"])
        lines.extend((" | ".join(header), "-" * 80))
        lines.extend(_format_metric_row(row) for row in rows)
        return _bounded_text(lines)
    except Exception as error:
        if "404" in str(error):
            return site_not_found_error(site_url)
        return f"Error retrieving search analytics: {str(error)}"


def _format_metric_row(row: dict) -> str:
    data = [value[:100] for value in row.get("keys", [])]
    data.extend(
        (
            str(row.get("clicks", 0)),
            str(row.get("impressions", 0)),
            f"{row.get('ctr', 0) * 100:.2f}%",
            f"{row.get('position', 0):.1f}",
        )
    )
    return " | ".join(data)


async def get_performance_overview(site_url: str, days: int = 28) -> str:
    """Get aggregate and daily Search Analytics performance."""
    try:
        service = auth.get_gsc_service()
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=days)
        dates = {
            "startDate": start_date.strftime("%Y-%m-%d"),
            "endDate": end_date.strftime("%Y-%m-%d"),
        }
        total_rows = list(
            _iter_gsc_rows(
                service=service,
                site_url=site_url,
                body={**dates, "dimensions": [], "dataState": DATA_STATE},
                max_rows=1,
            )
        )
        date_rows = list(
            _iter_gsc_rows(
                service=service,
                site_url=site_url,
                body={**dates, "dimensions": ["date"], "dataState": DATA_STATE},
                max_rows=max(1, days),
            )
        )
        lines = [
            f"Performance Overview for {site_url} (last {days} days):",
            "-" * 80,
        ]
        if not total_rows:
            lines.append("No data available for the selected period.")
            return _bounded_text(lines)
        row = total_rows[0]
        lines.extend(
            (
                f"Total Clicks: {row.get('clicks', 0):,}",
                f"Total Impressions: {row.get('impressions', 0):,}",
                f"Average CTR: {row.get('ctr', 0) * 100:.2f}%",
                f"Average Position: {row.get('position', 0):.1f}",
            )
        )
        if date_rows:
            lines.extend(("\nDaily Trend:", "Date | Clicks | Impressions | CTR | Position", "-" * 80))
            rows = sorted(date_rows, key=lambda value: value["keys"][0])
            lines.extend(_format_daily_row(row) for row in rows)
        return _bounded_text(lines)
    except Exception as error:
        if "404" in str(error):
            return site_not_found_error(site_url)
        return f"Error retrieving performance overview: {str(error)}"


def _format_daily_row(row: dict) -> str:
    date_text = row["keys"][0]
    try:
        formatted = datetime.strptime(date_text, "%Y-%m-%d").strftime("%m/%d")
    except (TypeError, ValueError):
        formatted = date_text
    return (
        f"{formatted} | {row.get('clicks', 0):.0f} | "
        f"{row.get('impressions', 0):.0f} | {row.get('ctr', 0) * 100:.2f}% | "
        f"{row.get('position', 0):.1f}"
    )


async def get_search_by_page_query(
    site_url: str,
    page_url: str,
    days: int = 28,
    row_limit: int = 20,
) -> str:
    """Get query performance for one exact page."""
    try:
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=days)
        request = {
            "startDate": start_date.strftime("%Y-%m-%d"),
            "endDate": end_date.strftime("%Y-%m-%d"),
            "dimensions": ["query"],
            "dimensionFilterGroups": [
                {
                    "filters": [
                        {
                            "dimension": "page",
                            "operator": "equals",
                            "expression": page_url,
                        }
                    ]
                }
            ],
            "orderBy": [{"metric": "CLICK_COUNT", "direction": "descending"}],
            "dataState": DATA_STATE,
        }
        rows = list(
            _iter_gsc_rows(
                site_url=site_url,
                body=request,
                max_rows=min(max(1, row_limit), 500),
            )
        )
        if not rows:
            return f"No search data found for page {page_url} in the last {days} days."
        lines = [
            f"Search queries for page {page_url} (last {days} days):",
            "\n" + "-" * 80 + "\n",
            "Query | Clicks | Impressions | CTR | Position",
            "-" * 80,
        ]
        for row in rows:
            query = row.get("keys", ["Unknown"])[0]
            lines.append(
                f"{query[:100]} | {row.get('clicks', 0)} | "
                f"{row.get('impressions', 0)} | {row.get('ctr', 0) * 100:.2f}% | "
                f"{row.get('position', 0):.1f}"
            )
        total_clicks = sum(row.get("clicks", 0) for row in rows)
        total_impressions = sum(row.get("impressions", 0) for row in rows)
        average_ctr = (
            total_clicks / total_impressions * 100 if total_impressions > 0 else 0
        )
        lines.extend(
            ("-" * 80, f"TOTAL | {total_clicks} | {total_impressions} | {average_ctr:.2f}% | -")
        )
        return _bounded_text(lines)
    except Exception as error:
        return f"Error retrieving page query data: {str(error)}"


def _iter_gsc_rows(*, site_url: str, body: dict, max_rows: int, service=None):
    from data_sources.modules.gsc.pagination import iter_search_analytics_rows

    return iter_search_analytics_rows(
        service or auth.get_gsc_service(),
        site_url=site_url,
        body=body,
        max_rows=max_rows,
        max_workflow_bytes=GSC_WORKFLOW_MAX_BYTES,
    )


def _bounded_text(lines: list[str]) -> str:
    text = "\n".join(lines)
    if len(text.encode("utf-8")) > MCP_TEXT_MAX_BYTES:
        raise OutputByteLimitError(
            f"MCP text output exceeds {MCP_TEXT_MAX_BYTES} bytes"
        )
    return text


__all__ = [
    "get_performance_overview",
    "get_search_analytics",
    "get_search_by_page_query",
]
