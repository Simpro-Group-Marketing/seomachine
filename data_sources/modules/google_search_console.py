"""
Google Search Console Data Integration

Fetches search performance, keyword rankings, and SERP data.
"""

import os
from typing import Any, Dict, Iterator, List, Optional

from google.oauth2 import service_account
from googleapiclient.discovery import build

try:
    from .artifact_runtime.limits import GSC_WORKFLOW_MAX_BYTES
    from .gsc.consumers import (
        date_range as _date_range,
        iter_keyword_positions as _iter_keyword_positions,
        iter_low_ctr_page_rows as _iter_low_ctr_page_rows,
        iter_page_keyword_rows as _iter_page_keyword_rows,
        iter_position_change_rows as _iter_position_change_rows,
        iter_quick_win_rows as _iter_quick_win_rows,
        iter_trending_query_rows as _iter_trending_query_rows,
        page_performance as _page_performance,
        search_rows as _search_rows,
        top_n,
    )
    from .gsc.intent import commercial_intent_score, intent_category
except ImportError:  # pragma: no cover - supports direct module-path execution.
    from artifact_runtime.limits import GSC_WORKFLOW_MAX_BYTES
    from gsc.consumers import (
        date_range as _date_range,
        iter_keyword_positions as _iter_keyword_positions,
        iter_low_ctr_page_rows as _iter_low_ctr_page_rows,
        iter_page_keyword_rows as _iter_page_keyword_rows,
        iter_position_change_rows as _iter_position_change_rows,
        iter_quick_win_rows as _iter_quick_win_rows,
        iter_trending_query_rows as _iter_trending_query_rows,
        page_performance as _page_performance,
        search_rows as _search_rows,
        top_n,
    )
    from gsc.intent import commercial_intent_score, intent_category


class GoogleSearchConsole:
    """Google Search Console data fetcher"""

    def __init__(
        self,
        site_url: Optional[str] = None,
        credentials_path: Optional[str] = None,
    ):
        """
        Initialize GSC client

        Args:
            site_url: Site URL (e.g., "https://castos.com")
            credentials_path: Path to credentials JSON
        """
        self.site_url = site_url or os.getenv("GSC_SITE_URL")
        credentials_path = credentials_path or os.getenv("GSC_CREDENTIALS_PATH")

        if not self.site_url:
            raise ValueError("GSC_SITE_URL must be provided or set in environment")

        if not credentials_path or not os.path.exists(credentials_path):
            raise ValueError(f"Credentials file not found: {credentials_path}")

        credentials = service_account.Credentials.from_service_account_file(
            credentials_path,
            scopes=["https://www.googleapis.com/auth/webmasters.readonly"],
        )
        self.service = build("searchconsole", "v1", credentials=credentials)

    def get_keyword_positions(
        self,
        days: int = 30,
        limit: int = 1000,
        *,
        min_impressions: int = 0,
        max_output_bytes: int = GSC_WORKFLOW_MAX_BYTES,
    ) -> List[Dict[str, Any]]:
        """
        Get keyword rankings and performance

        Args:
            days: Number of days to analyze
            limit: Max number of keywords to return

        Returns:
            List of keywords with position, clicks, impressions
        """
        results = list(
            self.iter_keyword_positions(
                days=days,
                max_rows=limit,
                min_impressions=min_impressions,
                max_output_bytes=max_output_bytes,
            )
        )
        results.sort(key=lambda row: row["impressions"], reverse=True)
        return results

    def iter_keyword_positions(
        self,
        *,
        days: int = 30,
        max_rows: int = 1000,
        min_impressions: int = 0,
        max_output_bytes: int = GSC_WORKFLOW_MAX_BYTES,
    ) -> Iterator[Dict[str, Any]]:
        return _iter_keyword_positions(
            self,
            days=days,
            max_rows=max_rows,
            min_impressions=min_impressions,
            max_output_bytes=max_output_bytes,
        )

    def get_quick_wins(
        self,
        days: int = 30,
        position_min: int = 11,
        position_max: int = 20,
        min_impressions: int = 50,
        prioritize_commercial: bool = True,
        *,
        max_rows: int = 1000,
        max_output_bytes: int = GSC_WORKFLOW_MAX_BYTES,
    ) -> List[Dict[str, Any]]:
        """Find keywords ranking 11-20 that are closest to page-one movement."""
        quick_wins = list(
            self.iter_quick_win_rows(
                days=days,
                position_min=position_min,
                position_max=position_max,
                min_impressions=min_impressions,
                prioritize_commercial=prioritize_commercial,
                max_rows=max_rows,
                max_output_bytes=max_output_bytes,
            )
        )
        quick_wins.sort(key=lambda row: row["opportunity_score"], reverse=True)
        return quick_wins

    def iter_quick_win_rows(
        self,
        *,
        days: int = 30,
        position_min: int = 11,
        position_max: int = 20,
        min_impressions: int = 50,
        prioritize_commercial: bool = True,
        max_rows: int = 1000,
        max_output_bytes: int = GSC_WORKFLOW_MAX_BYTES,
    ) -> Iterator[Dict[str, Any]]:
        return _iter_quick_win_rows(
            self,
            days=days,
            position_min=position_min,
            position_max=position_max,
            min_impressions=min_impressions,
            prioritize_commercial=prioritize_commercial,
            max_rows=max_rows,
            max_output_bytes=max_output_bytes,
        )

    def _calculate_commercial_intent(self, keyword: str) -> float:
        """Calculate the existing deterministic commercial-intent score."""
        return commercial_intent_score(keyword)

    def _get_intent_category(self, score: float) -> str:
        """Get human-readable intent category"""
        return intent_category(score)

    def _search_rows(
        self,
        request: Dict[str, Any],
        *,
        max_rows: int,
        start_row: int = 0,
        max_output_bytes: int = GSC_WORKFLOW_MAX_BYTES,
    ) -> Iterator[Dict[str, Any]]:
        return _search_rows(
            self,
            request,
            max_rows=max_rows,
            start_row=start_row,
            max_output_bytes=max_output_bytes,
        )

    def get_page_performance(
        self,
        url: str,
        days: int = 30,
        *,
        max_output_bytes: int = GSC_WORKFLOW_MAX_BYTES,
    ) -> Dict[str, Any]:
        """Get bounded search performance for a specific page."""
        return _page_performance(
            self,
            url,
            days=days,
            max_output_bytes=max_output_bytes,
        )

    def iter_page_keyword_rows(
        self,
        url: str,
        *,
        days: int = 30,
        max_rows: int = 50,
        max_output_bytes: int = GSC_WORKFLOW_MAX_BYTES,
    ) -> Iterator[Dict[str, Any]]:
        return _iter_page_keyword_rows(
            self,
            url,
            days=days,
            max_rows=max_rows,
            max_output_bytes=max_output_bytes,
        )

    def get_low_ctr_pages(
        self,
        days: int = 30,
        ctr_threshold: float = 0.03,
        min_impressions: int = 100,
        path_filter: Optional[str] = "/blog/",
        *,
        max_rows: int = 1000,
        max_output_bytes: int = GSC_WORKFLOW_MAX_BYTES,
    ) -> List[Dict[str, Any]]:
        """Find pages with high impressions and low CTR."""
        low_ctr = list(
            self.iter_low_ctr_page_rows(
                days=days,
                ctr_threshold=ctr_threshold,
                min_impressions=min_impressions,
                path_filter=path_filter,
                max_rows=max_rows,
                max_output_bytes=max_output_bytes,
            )
        )
        low_ctr.sort(key=lambda row: row["missed_clicks"], reverse=True)
        return low_ctr

    def iter_low_ctr_page_rows(
        self,
        *,
        days: int = 30,
        ctr_threshold: float = 0.03,
        min_impressions: int = 100,
        path_filter: Optional[str] = "/blog/",
        max_rows: int = 1000,
        max_output_bytes: int = GSC_WORKFLOW_MAX_BYTES,
    ) -> Iterator[Dict[str, Any]]:
        return _iter_low_ctr_page_rows(
            self,
            days=days,
            ctr_threshold=ctr_threshold,
            min_impressions=min_impressions,
            path_filter=path_filter,
            max_rows=max_rows,
            max_output_bytes=max_output_bytes,
        )

    def get_trending_queries(
        self,
        days_recent: int = 7,
        days_comparison: int = 30,
        min_impressions: int = 20,
        *,
        max_rows: int = 1000,
        max_output_bytes: int = GSC_WORKFLOW_MAX_BYTES,
    ) -> List[Dict[str, Any]]:
        """Find queries with growing recent impressions."""
        trending = list(
            self.iter_trending_query_rows(
                days_recent=days_recent,
                days_comparison=days_comparison,
                min_impressions=min_impressions,
                max_rows=max_rows,
                max_output_bytes=max_output_bytes,
            )
        )
        trending.sort(key=lambda row: row["change_percent"], reverse=True)
        return trending

    def iter_trending_query_rows(
        self,
        *,
        days_recent: int = 7,
        days_comparison: int = 30,
        min_impressions: int = 20,
        max_rows: int = 1000,
        max_output_bytes: int = GSC_WORKFLOW_MAX_BYTES,
    ) -> Iterator[Dict[str, Any]]:
        return _iter_trending_query_rows(
            self,
            days_recent=days_recent,
            days_comparison=days_comparison,
            min_impressions=min_impressions,
            max_rows=max_rows,
            max_output_bytes=max_output_bytes,
        )

    def get_position_changes(
        self,
        days_recent: int = 7,
        days_comparison: int = 30,
        *,
        max_rows: int = 1000,
        max_output_bytes: int = GSC_WORKFLOW_MAX_BYTES,
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Track keyword position changes across recent and comparison windows."""
        improved = []
        declined = []
        stable = []
        for result in self.iter_position_change_rows(
            days_recent=days_recent,
            days_comparison=days_comparison,
            max_rows=max_rows,
            max_output_bytes=max_output_bytes,
        ):
            position_change = result["position_change"]
            if position_change >= 2:
                improved.append(result)
            elif position_change <= -2:
                declined.append(result)
            else:
                stable.append(result)
        improved.sort(key=lambda row: row["position_change"], reverse=True)
        declined.sort(key=lambda row: row["position_change"])
        return {"improved": improved, "declined": declined, "stable": stable}

    def iter_position_change_rows(
        self,
        *,
        days_recent: int = 7,
        days_comparison: int = 30,
        max_rows: int = 1000,
        max_output_bytes: int = GSC_WORKFLOW_MAX_BYTES,
    ) -> Iterator[Dict[str, Any]]:
        return _iter_position_change_rows(
            self,
            days_recent=days_recent,
            days_comparison=days_comparison,
            max_rows=max_rows,
            max_output_bytes=max_output_bytes,
        )


if __name__ == "__main__":
    from dotenv import load_dotenv

    load_dotenv("data_sources/config/.env")
    gsc = GoogleSearchConsole()
    print("Quick Win Opportunities (Position 11-20):")
    for index, keyword in enumerate(gsc.get_quick_wins()[:10], 1):
        print(f"{index}. {keyword['keyword']}")
        print(
            f"   Position: {keyword['position']} | "
            f"Impressions: {keyword['impressions']:,}"
        )
        print(f"   Opportunity Score: {keyword['opportunity_score']:.1f}")
        print()
    print("\nLow CTR Pages (Need Better Meta):")
    for page in gsc.get_low_ctr_pages()[:5]:
        print(f"- {page['url']}")
        print(f"  {page['impressions']:,} impressions | {page['ctr']:.2f}% CTR")
