"""Advanced Search Analytics query and comparison tools."""

from __future__ import annotations

import json
from datetime import datetime, timedelta

from . import auth
from .contracts import DATA_STATE
from .formatting import site_not_found_error


async def get_advanced_search_analytics(
    site_url: str,
    start_date: str = None,
    end_date: str = None,
    dimensions: str = "query",
    search_type: str = "WEB",
    row_limit: int = 1000,
    start_row: int = 0,
    sort_by: str = "clicks",
    sort_direction: str = "descending",
    filter_dimension: str = None,
    filter_operator: str = "contains",
    filter_expression: str = None,
    filters: str = None,
    data_state: str = None,
) -> str:
    """Get advanced Search Analytics data with filtering and pagination."""
    try:
        service = auth.get_gsc_service()
        end_date = end_date or datetime.now().date().strftime("%Y-%m-%d")
        start_date = start_date or (
            datetime.now().date() - timedelta(days=28)
        ).strftime("%Y-%m-%d")
        resolved_data_state = (data_state or DATA_STATE).lower().strip()
        if resolved_data_state not in ("all", "final"):
            return (
                f"Invalid data_state value '{data_state}'. "
                "Accepted values are 'all' (matches GSC dashboard) or 'final' "
                "(2-3 day lag)."
            )
        dimension_list = [value.strip() for value in dimensions.split(",")]
        request = _advanced_request(
            start_date,
            end_date,
            dimension_list,
            search_type,
            row_limit,
            start_row,
            resolved_data_state,
            sort_by,
            sort_direction,
        )
        filter_result = _apply_filters(
            request,
            filters,
            filter_dimension,
            filter_operator,
            filter_expression,
        )
        if isinstance(filter_result, str):
            return filter_result
        active_filters = filter_result
        response = service.searchanalytics().query(
            siteUrl=site_url, body=request
        ).execute()
        rows = response.get("rows", [])
        if not rows:
            return _no_data_message(
                site_url,
                start_date,
                end_date,
                dimensions,
                search_type,
                active_filters,
            )
        return _format_advanced_rows(
            site_url,
            start_date,
            end_date,
            search_type,
            active_filters,
            start_row,
            sort_by,
            sort_direction,
            dimension_list,
            rows,
            row_limit,
        )
    except Exception as error:
        if "404" in str(error):
            return site_not_found_error(site_url)
        return f"Error retrieving advanced search analytics: {str(error)}"


def _advanced_request(
    start_date,
    end_date,
    dimensions,
    search_type,
    row_limit,
    start_row,
    data_state,
    sort_by,
    sort_direction,
):
    request = {
        "startDate": start_date,
        "endDate": end_date,
        "dimensions": dimensions,
        "rowLimit": min(row_limit, 25000),
        "startRow": start_row,
        "searchType": search_type.upper(),
        "dataState": data_state,
    }
    metric_map = {
        "clicks": "CLICK_COUNT",
        "impressions": "IMPRESSION_COUNT",
        "ctr": "CTR",
        "position": "POSITION",
    }
    if sort_by and sort_by in metric_map:
        request["orderBy"] = [
            {"metric": metric_map[sort_by], "direction": sort_direction.lower()}
        ]
    return request


def _apply_filters(
    request,
    filters,
    filter_dimension,
    filter_operator,
    filter_expression,
):
    if filters:
        try:
            filter_list = json.loads(filters)
        except json.JSONDecodeError:
            return "Invalid filters JSON. Please provide a valid JSON array of filter objects."
        if not isinstance(filter_list, list) or len(filter_list) == 0:
            return "Invalid filters value. Expected a non-empty JSON array of filter objects."
        for item in filter_list:
            if not all(key in item for key in ("dimension", "operator", "expression")):
                return (
                    "Each filter object must have 'dimension', 'operator', and "
                    f"'expression' keys. Invalid filter: {item}"
                )
        request["dimensionFilterGroups"] = [{"filters": filter_list}]
        return filter_list
    if filter_dimension and filter_expression:
        item = {
            "dimension": filter_dimension,
            "operator": filter_operator,
            "expression": filter_expression,
        }
        request["dimensionFilterGroups"] = [{"filters": [item]}]
        return [item]
    return []


def _no_data_message(
    site_url,
    start_date,
    end_date,
    dimensions,
    search_type,
    active_filters,
):
    message = (
        f"No search analytics data found for {site_url} with the specified parameters.\n\n"
        "Parameters used:\n"
        f"- Date range: {start_date} to {end_date}\n"
        f"- Dimensions: {dimensions}\n"
        f"- Search type: {search_type}\n"
    )
    if active_filters:
        message += "- Filters:\n"
        for item in active_filters:
            message += (
                f"    {item['dimension']} {item['operator']} "
                f"'{item['expression']}'\n"
            )
        return message
    return message + "- No filter applied\n"


def _format_advanced_rows(
    site_url,
    start_date,
    end_date,
    search_type,
    active_filters,
    start_row,
    sort_by,
    sort_direction,
    dimensions,
    rows,
    row_limit,
):
    lines = [
        f"Search analytics for {site_url}:",
        f"Date range: {start_date} to {end_date}",
        f"Search type: {search_type}",
    ]
    if active_filters:
        description = " AND ".join(
            f"{item['dimension']} {item['operator']} '{item['expression']}'"
            for item in active_filters
        )
        lines.append(f"Filters: {description}")
    lines.extend(
        (
            f"Showing rows {start_row + 1} to {start_row + len(rows)} "
            f"(sorted by {sort_by} {sort_direction})",
            "\n" + "-" * 80 + "\n",
            " | ".join(
                [value.capitalize() for value in dimensions]
                + ["Clicks", "Impressions", "CTR", "Position"]
            ),
            "-" * 80,
        )
    )
    lines.extend(_metric_row(row) for row in rows)
    if len(rows) == row_limit:
        lines.extend(
            (
                "\nThere may be more results available. To see the next page, use:",
                f"start_row: {start_row + row_limit}, row_limit: {row_limit}",
            )
        )
    return "\n".join(lines)


def _metric_row(row):
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


async def compare_search_periods(
    site_url: str,
    period1_start: str,
    period1_end: str,
    period2_start: str,
    period2_end: str,
    dimensions: str = "query",
    limit: int = 10,
) -> str:
    """Compare Search Analytics metrics between two date periods."""
    try:
        service = auth.get_gsc_service()
        dimension_list = [value.strip() for value in dimensions.split(",")]
        first = _period_query(service, site_url, period1_start, period1_end, dimension_list)
        second = _period_query(service, site_url, period2_start, period2_end, dimension_list)
        first_rows = first.get("rows", [])
        second_rows = second.get("rows", [])
        if not first_rows and not second_rows:
            return f"No data found for either period for {site_url}."
        comparison = _compare_rows(first_rows, second_rows)
        return _format_comparison(
            site_url,
            period1_start,
            period1_end,
            period2_start,
            period2_end,
            dimensions,
            dimension_list,
            comparison,
            limit,
        )
    except Exception as error:
        if "404" in str(error):
            return site_not_found_error(site_url)
        return f"Error comparing search periods: {str(error)}"


def _period_query(service, site_url, start_date, end_date, dimensions):
    request = {
        "startDate": start_date,
        "endDate": end_date,
        "dimensions": dimensions,
        "rowLimit": 1000,
        "dataState": DATA_STATE,
    }
    return service.searchanalytics().query(siteUrl=site_url, body=request).execute()


def _compare_rows(first_rows, second_rows):
    first = {tuple(row.get("keys", [])): row for row in first_rows}
    second = {tuple(row.get("keys", [])): row for row in second_rows}
    compared = []
    for key in set(first) | set(second):
        first_row = first.get(key, _empty_metrics())
        second_row = second.get(key, _empty_metrics())
        click_difference = second_row.get("clicks", 0) - first_row.get("clicks", 0)
        first_clicks = first_row.get("clicks", 0)
        compared.append(
            {
                "key": key,
                "p1_clicks": first_clicks,
                "p2_clicks": second_row.get("clicks", 0),
                "click_diff": click_difference,
                "click_pct": (
                    click_difference / first_row.get("clicks", 1) * 100
                    if first_clicks > 0
                    else float("inf")
                ),
                "p1_position": first_row.get("position", 0),
                "p2_position": second_row.get("position", 0),
                "pos_diff": first_row.get("position", 0)
                - second_row.get("position", 0),
            }
        )
    compared.sort(key=lambda item: abs(item["click_diff"]), reverse=True)
    return compared


def _empty_metrics():
    return {"clicks": 0, "impressions": 0, "ctr": 0, "position": 0}


def _format_comparison(
    site_url,
    period1_start,
    period1_end,
    period2_start,
    period2_end,
    dimensions,
    dimension_list,
    comparison,
    limit,
):
    lines = [
        f"Search analytics comparison for {site_url}:",
        f"Period 1: {period1_start} to {period1_end}",
        f"Period 2: {period2_start} to {period2_end}",
        f"Dimension(s): {dimensions}",
        f"Top {min(limit, len(comparison))} results by change in clicks:",
        "\n" + "-" * 100 + "\n",
    ]
    header = " | ".join(value.capitalize() for value in dimension_list)
    lines.extend(
        (
            f"{header} | P1 Clicks | P2 Clicks | Change | % | P1 Pos | P2 Pos | Pos delta",
            "-" * 100,
        )
    )
    for item in comparison[:limit]:
        key_text = " | ".join(str(value)[:100] for value in item["key"])
        percentage = item["click_pct"]
        percentage_text = "N/A" if percentage == float("inf") else f"{percentage:.1f}%"
        lines.append(
            f"{key_text} | {item['p1_clicks']} | {item['p2_clicks']} | "
            f"{item['click_diff']:+d} | {percentage_text} | "
            f"{item['p1_position']:.1f} | {item['p2_position']:.1f} | "
            f"{item['pos_diff']:+.1f}"
        )
    return "\n".join(lines)


__all__ = ["compare_search_periods", "get_advanced_search_analytics"]
