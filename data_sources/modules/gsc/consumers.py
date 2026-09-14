"""Bounded high-cardinality consumers for Google Search Console rows."""

from __future__ import annotations

import heapq
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, Iterable, Iterator, List, Optional

try:
    from ..artifact_runtime.limits import GSC_WORKFLOW_MAX_BYTES
    from .intent import commercial_intent_score, intent_category
    from .pagination import iter_search_analytics_rows
except ImportError:  # pragma: no cover - supports direct module-path execution.
    from artifact_runtime.limits import GSC_WORKFLOW_MAX_BYTES
    from gsc.intent import commercial_intent_score, intent_category
    from gsc.pagination import iter_search_analytics_rows


def search_rows(
    client: Any,
    request: Dict[str, Any],
    *,
    max_rows: int,
    start_row: int = 0,
    max_output_bytes: int = GSC_WORKFLOW_MAX_BYTES,
) -> Iterator[Dict[str, Any]]:
    return iter_search_analytics_rows(
        client.service,
        site_url=client.site_url,
        body=request,
        max_rows=max_rows,
        start_row=start_row,
        max_workflow_bytes=max_output_bytes,
    )


def iter_keyword_positions(
    client: Any,
    *,
    days: int = 30,
    max_rows: int = 1000,
    min_impressions: int = 0,
    max_output_bytes: int = GSC_WORKFLOW_MAX_BYTES,
) -> Iterator[Dict[str, Any]]:
    """Yield keyword rankings and performance without materializing all rows."""
    start_date, end_date = date_range(days)
    request = {
        "startDate": start_date,
        "endDate": end_date,
        "dimensions": ["query"],
        "dimensionFilterGroups": [],
    }
    for row in search_rows(
        client,
        request,
        max_rows=max_rows,
        max_output_bytes=max_output_bytes,
    ):
        if row["impressions"] < min_impressions:
            continue
        query = row["keys"][0]
        yield {
            "keyword": query,
            "clicks": row["clicks"],
            "impressions": row["impressions"],
            "ctr": row["ctr"],
            "position": round(row["position"], 1),
        }


def iter_quick_win_rows(
    client: Any,
    *,
    days: int = 30,
    position_min: int = 11,
    position_max: int = 20,
    min_impressions: int = 50,
    prioritize_commercial: bool = True,
    max_rows: int = 1000,
    max_output_bytes: int = GSC_WORKFLOW_MAX_BYTES,
) -> Iterator[Dict[str, Any]]:
    """Yield quick-win keyword rows in source order."""
    for keyword_row in iter_keyword_positions(
        client,
        days=days,
        max_rows=max_rows,
        min_impressions=min_impressions,
        max_output_bytes=max_output_bytes,
    ):
        if not position_min <= keyword_row["position"] <= position_max:
            continue
        keyword = keyword_row["keyword"].lower()
        commercial_intent = commercial_intent_score(keyword)
        distance_from_10 = keyword_row["position"] - 10
        base_score = keyword_row["impressions"] / (distance_from_10 + 1)
        opportunity_score = (
            base_score * commercial_intent
            if prioritize_commercial
            else base_score
        )
        yield {
            **keyword_row,
            "commercial_intent": commercial_intent,
            "commercial_intent_category": intent_category(commercial_intent),
            "opportunity_score": round(opportunity_score, 2),
            "priority": "high" if keyword_row["position"] <= 15 else "medium",
        }


def page_performance(
    client: Any,
    url: str,
    *,
    days: int = 30,
    max_output_bytes: int = GSC_WORKFLOW_MAX_BYTES,
) -> Dict[str, Any]:
    """Return bounded search performance for a specific page."""
    start_date, end_date = date_range(days)
    request = {
        "startDate": start_date,
        "endDate": end_date,
        "dimensions": ["page"],
        "dimensionFilterGroups": [_page_filter(url)],
    }
    row = next(search_rows(client, request, max_rows=1), None)
    if row is None:
        return {"url": url, "error": "No data found"}
    page_data = {
        "url": row["keys"][0],
        "clicks": row["clicks"],
        "impressions": row["impressions"],
        "ctr": round(row["ctr"] * 100, 2),
        "avg_position": round(row["position"], 1),
    }
    keywords = list(
        iter_page_keyword_rows(
            client,
            url,
            days=days,
            max_rows=50,
            max_output_bytes=max_output_bytes,
        )
    )
    keywords.sort(key=lambda item: item["clicks"], reverse=True)
    page_data["top_keywords"] = keywords[:10]
    return page_data


def iter_page_keyword_rows(
    client: Any,
    url: str,
    *,
    days: int = 30,
    max_rows: int = 50,
    max_output_bytes: int = GSC_WORKFLOW_MAX_BYTES,
) -> Iterator[Dict[str, Any]]:
    """Yield query rows for a page without collecting them first."""
    start_date, end_date = date_range(days)
    request = {
        "startDate": start_date,
        "endDate": end_date,
        "dimensions": ["query"],
        "dimensionFilterGroups": [_page_filter(url)],
    }
    for row in search_rows(
        client,
        request,
        max_rows=max_rows,
        max_output_bytes=max_output_bytes,
    ):
        yield {
            "keyword": row["keys"][0],
            "clicks": row["clicks"],
            "impressions": row["impressions"],
            "position": round(row["position"], 1),
        }


def iter_low_ctr_page_rows(
    client: Any,
    *,
    days: int = 30,
    ctr_threshold: float = 0.03,
    min_impressions: int = 100,
    path_filter: Optional[str] = "/blog/",
    max_rows: int = 1000,
    max_output_bytes: int = GSC_WORKFLOW_MAX_BYTES,
) -> Iterator[Dict[str, Any]]:
    """Yield low-CTR page opportunities in source order."""
    start_date, end_date = date_range(days)
    request: Dict[str, Any] = {
        "startDate": start_date,
        "endDate": end_date,
        "dimensions": ["page"],
    }
    if path_filter:
        request["dimensionFilterGroups"] = [{
            "filters": [{
                "dimension": "page",
                "operator": "contains",
                "expression": path_filter,
            }]
        }]
    for row in search_rows(
        client,
        request,
        max_rows=max_rows,
        max_output_bytes=max_output_bytes,
    ):
        impressions = row["impressions"]
        ctr = row["ctr"]
        if impressions < min_impressions or ctr >= ctr_threshold:
            continue
        target_ctr = 0.05
        potential_clicks = int(impressions * target_ctr)
        missed_clicks = potential_clicks - row["clicks"]
        yield {
            "url": row["keys"][0],
            "impressions": impressions,
            "clicks": row["clicks"],
            "ctr": round(ctr * 100, 2),
            "avg_position": round(row["position"], 1),
            "potential_clicks": potential_clicks,
            "missed_clicks": missed_clicks,
            "priority": "high" if missed_clicks > 50 else "medium",
        }


def iter_trending_query_rows(
    client: Any,
    *,
    days_recent: int = 7,
    days_comparison: int = 30,
    min_impressions: int = 20,
    max_rows: int = 1000,
    max_output_bytes: int = GSC_WORKFLOW_MAX_BYTES,
) -> Iterator[Dict[str, Any]]:
    """Yield growing query rows without materializing the recent period."""
    now = datetime.now()
    recent_start = (now - timedelta(days=days_recent)).strftime("%Y-%m-%d")
    recent_end = now.strftime("%Y-%m-%d")
    comparison_start = (now - timedelta(days=days_comparison)).strftime("%Y-%m-%d")
    comparison_end = (now - timedelta(days=days_recent)).strftime("%Y-%m-%d")
    comparison_lookup = {
        row["keys"][0]: row["impressions"]
        for row in search_rows(
            client,
            {
                "startDate": comparison_start,
                "endDate": comparison_end,
                "dimensions": ["query"],
            },
            max_rows=max_rows,
            max_output_bytes=max_output_bytes,
        )
    }
    for row in search_rows(
        client,
        {
            "startDate": recent_start,
            "endDate": recent_end,
            "dimensions": ["query"],
        },
        max_rows=max_rows,
        max_output_bytes=max_output_bytes,
    ):
        query = row["keys"][0]
        recent_impressions = row["impressions"]
        if recent_impressions < min_impressions:
            continue
        previous_impressions = comparison_lookup.get(query, 0)
        change_percent = (
            ((recent_impressions - previous_impressions) / previous_impressions) * 100
            if previous_impressions > 0
            else 100
        )
        if change_percent > 20:
            yield {
                "query": query,
                "recent_impressions": recent_impressions,
                "previous_impressions": previous_impressions,
                "change_percent": round(change_percent, 1),
                "clicks": row["clicks"],
                "position": round(row["position"], 1),
            }


def iter_position_change_rows(
    client: Any,
    *,
    days_recent: int = 7,
    days_comparison: int = 30,
    max_rows: int = 1000,
    max_output_bytes: int = GSC_WORKFLOW_MAX_BYTES,
) -> Iterator[Dict[str, Any]]:
    """Yield keyword position comparison rows without collecting both periods."""
    comparison_lookup = {
        row["keyword"]: row["position"]
        for row in iter_keyword_positions(
            client,
            days=days_comparison,
            max_rows=max_rows,
            max_output_bytes=max_output_bytes,
        )
    }
    for row in iter_keyword_positions(
        client,
        days=days_recent,
        max_rows=max_rows,
        max_output_bytes=max_output_bytes,
    ):
        previous_position = comparison_lookup.get(row["keyword"])
        if not previous_position:
            continue
        position_change = previous_position - row["position"]
        yield {
            **row,
            "previous_position": previous_position,
            "position_change": round(position_change, 1),
        }


def top_n(
    rows: Iterable[Dict[str, Any]],
    *,
    limit: int,
    key: Callable[[Dict[str, Any]], float],
) -> List[Dict[str, Any]]:
    """Return the highest scoring rows using a fixed-size heap."""
    if limit < 1:
        return []
    return heapq.nlargest(limit, rows, key=key)


def date_range(days: int) -> tuple[str, str]:
    now = datetime.now()
    return (
        (now - timedelta(days=days)).strftime("%Y-%m-%d"),
        now.strftime("%Y-%m-%d"),
    )


def _page_filter(url: str) -> Dict[str, Any]:
    return {
        "filters": [{
            "dimension": "page",
            "operator": "equals" if url.startswith("http") else "contains",
            "expression": url,
        }]
    }


__all__ = [
    "date_range",
    "iter_keyword_positions",
    "iter_low_ctr_page_rows",
    "iter_page_keyword_rows",
    "iter_position_change_rows",
    "iter_quick_win_rows",
    "iter_trending_query_rows",
    "page_performance",
    "search_rows",
    "top_n",
]
