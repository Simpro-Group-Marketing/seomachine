"""
DataForSEO API Integration

Fetches SERP data, competitor rankings, keyword research, and more.
"""

import os
import base64
import calendar
import re
import requests
from typing import Dict, List, Optional, Any
from datetime import date

try:
    from .domain_identity import hostnames_equal, normalize_hostname
except ImportError:  # pragma: no cover - supports direct script execution.
    from domain_identity import hostnames_equal, normalize_hostname


REQUEST_TIMEOUT_SECONDS = 30
QUESTION_PREFIX_RE = re.compile(
    r"^(?:how|what|why|when|where|who|can|should|is|are|does)\b",
    re.IGNORECASE,
)


class DataForSEOError(RuntimeError):
    """Base error for an unusable DataForSEO response."""


class DataForSEOAvailabilityError(DataForSEOError):
    """DataForSEO could not satisfy the request."""


class DataForSEOContractError(DataForSEOError):
    """DataForSEO returned a malformed or unsupported response shape."""


class DataForSEO:
    """DataForSEO API client"""

    def __init__(self, login: Optional[str] = None, password: Optional[str] = None):
        """
        Initialize DataForSEO client

        Args:
            login: API login (defaults to env var)
            password: API password (defaults to env var)
        """
        self.login = login or os.getenv("DATAFORSEO_LOGIN")
        self.password = password or os.getenv("DATAFORSEO_PASSWORD")
        self.base_url = os.getenv("DATAFORSEO_BASE_URL", "https://api.dataforseo.com")

        if not self.login or not self.password:
            raise ValueError("DATAFORSEO_LOGIN and DATAFORSEO_PASSWORD must be set")

        # Create auth header
        cred = f"{self.login}:{self.password}"
        encoded_cred = base64.b64encode(cred.encode("ascii")).decode("ascii")
        self.headers = {
            "Authorization": f"Basic {encoded_cred}",
            "Content-Type": "application/json",
        }

        self.session = requests.Session()
        self.session.headers.update(self.headers)

    def _post(self, endpoint: str, data: List[Dict]) -> Dict[str, Any]:
        """Make a bounded POST request and return a JSON object."""
        url = f"{self.base_url}{endpoint}"
        try:
            response = self.session.post(
                url,
                json=data,
                timeout=REQUEST_TIMEOUT_SECONDS,
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            raise DataForSEOAvailabilityError(
                f"DataForSEO request failed for {endpoint}: {exc}"
            ) from exc

        try:
            payload = response.json()
        except ValueError as exc:
            raise DataForSEOContractError(
                f"DataForSEO returned non-JSON data for {endpoint}"
            ) from exc
        if not isinstance(payload, dict):
            raise DataForSEOContractError(
                f"DataForSEO returned a non-object response for {endpoint}"
            )
        return payload

    def _require_task(
        self,
        response: Dict[str, Any],
        operation: str,
        *,
        index: int = 0,
    ) -> Dict[str, Any]:
        """Return one successful task or raise a typed provider/contract error."""
        if not isinstance(response, dict):
            raise DataForSEOContractError(
                f"DataForSEO {operation} response must be an object"
            )
        status_code = response.get("status_code")
        if isinstance(status_code, bool) or not isinstance(status_code, int):
            raise DataForSEOContractError(
                f"DataForSEO {operation} response has invalid status_code"
            )
        if status_code != 20000:
            message = response.get("status_message") or "Unknown API error"
            raise DataForSEOAvailabilityError(
                f"DataForSEO {operation} API error {status_code}: {message}"
            )

        tasks = response.get("tasks")
        if not isinstance(tasks, list) or index >= len(tasks):
            raise DataForSEOContractError(
                f"DataForSEO {operation} response is missing task {index}"
            )
        task = tasks[index]
        if not isinstance(task, dict):
            raise DataForSEOContractError(
                f"DataForSEO {operation} task {index} must be an object"
            )
        task_status = task.get("status_code")
        if isinstance(task_status, bool) or not isinstance(task_status, int):
            raise DataForSEOContractError(
                f"DataForSEO {operation} task {index} has invalid status_code"
            )
        if task_status != 20000:
            message = task.get("status_message") or "Unknown task error"
            raise DataForSEOAvailabilityError(
                f"DataForSEO {operation} task error {task_status}: {message}"
            )
        return task

    def _require_result(
        self,
        task: Dict[str, Any],
        operation: str,
        *,
        index: int = 0,
    ) -> Dict[str, Any]:
        """Return one documented result object from a successful task."""
        results = task.get("result")
        if not isinstance(results, list) or index >= len(results):
            raise DataForSEOContractError(
                f"DataForSEO {operation} task is missing result {index}"
            )
        result = results[index]
        if not isinstance(result, dict):
            raise DataForSEOContractError(
                f"DataForSEO {operation} result {index} must be an object"
            )
        return result

    def get_rankings(
        self,
        domain: str,
        keywords: List[str],
        location_code: int = 2840,
        language_code: str = "en",
    ) -> List[Dict[str, Any]]:
        """Get exact-host organic ranking positions for specific keywords."""
        target_domain = normalize_hostname(domain)
        if not target_domain:
            raise ValueError("domain must contain a valid hostname")
        if not keywords:
            return []

        tasks = [
            {
                "keyword": keyword,
                "location_code": location_code,
                "language_code": language_code,
                "device": "desktop",
                "os": "windows",
            }
            for keyword in keywords
        ]
        response = self._post("/v3/serp/google/organic/live/advanced", tasks)

        rankings = []
        for index, keyword in enumerate(keywords):
            task = self._require_task(response, "rankings", index=index)
            result = self._require_result(task, "rankings")
            items = result.get("items")
            if not isinstance(items, list):
                raise DataForSEOContractError(
                    "DataForSEO rankings result items must be an array"
                )

            match = next(
                (
                    item
                    for item in items
                    if isinstance(item, dict)
                    and item.get("type") == "organic"
                    and hostnames_equal(target_domain, item.get("domain", ""))
                ),
                None,
            )
            rank_group = match.get("rank_group") if match else None
            rank_absolute = match.get("rank_absolute") if match else None
            rankings.append(
                {
                    "keyword": keyword,
                    "domain": target_domain,
                    "position": _item_rank(match) if match else None,
                    "rank_group": rank_group,
                    "rank_absolute": rank_absolute,
                    "url": match.get("url") if match else None,
                    "ranking": match is not None and _item_rank(match) is not None,
                    "search_volume": result.get("keyword_data", {})
                    .get("keyword_info", {})
                    .get("search_volume"),
                    "cpc": result.get("keyword_data", {})
                    .get("keyword_info", {})
                    .get("cpc"),
                }
            )
        return rankings

    def get_serp_data(
        self, keyword: str, location_code: int = 2840, limit: int = 100
    ) -> Dict[str, Any]:
        """Get complete structured SERP data for a keyword."""
        data = [
            {
                "keyword": keyword,
                "location_code": location_code,
                "language_code": "en",
                "device": "desktop",
                "os": "windows",
                "depth": limit,
            }
        ]
        response = self._post("/v3/serp/google/organic/live/advanced", data)
        task = self._require_task(response, "SERP data")
        result = self._require_result(task, "SERP data")
        items = result.get("items")
        if not isinstance(items, list):
            raise DataForSEOContractError(
                "DataForSEO SERP data result items must be an array"
            )

        organic_results = []
        features = []
        for item in items:
            if not isinstance(item, dict):
                raise DataForSEOContractError(
                    "DataForSEO SERP data item must be an object"
                )
            if item.get("type") == "organic":
                organic_results.append(
                    {
                        "position": item.get("rank_absolute"),
                        "url": item.get("url"),
                        "domain": item.get("domain"),
                        "title": item.get("title"),
                        "description": item.get("description"),
                        "breadcrumb": item.get("breadcrumb"),
                    }
                )
            elif item.get("type"):
                features.append(item["type"])

        keyword_data = result.get("keyword_data", {}).get("keyword_info", {})
        return {
            "keyword": keyword,
            "search_volume": keyword_data.get("search_volume"),
            "cpc": keyword_data.get("cpc"),
            "competition": keyword_data.get("competition"),
            "organic_results": organic_results,
            "features": list(dict.fromkeys(features)),
            "total_results": result.get("items_count", 0),
        }

    def analyze_competitor(
        self,
        competitor_domain: str,
        keywords: List[str],
        your_domain: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Analyze exact-host competitor rankings against an optional owned domain."""
        competitor_host = normalize_hostname(competitor_domain)
        owned_host = normalize_hostname(your_domain) if your_domain else None
        if not competitor_host:
            raise ValueError("competitor_domain must contain a valid hostname")
        if not keywords:
            return {
                "competitor": competitor_host,
                "your_domain": owned_host,
                "comparison": [],
            }

        tasks = [
            {
                "keyword": keyword,
                "location_code": 2840,
                "language_code": "en",
                "device": "desktop",
            }
            for keyword in keywords
        ]
        response = self._post("/v3/serp/google/organic/live/advanced", tasks)

        comparison = []
        for index, keyword in enumerate(keywords):
            task = self._require_task(response, "competitor analysis", index=index)
            result = self._require_result(task, "competitor analysis")
            items = result.get("items")
            if not isinstance(items, list):
                raise DataForSEOContractError(
                    "DataForSEO competitor analysis result items must be an array"
                )

            competitor_position = None
            owned_position = None
            for item in items:
                if not isinstance(item, dict) or item.get("type") != "organic":
                    continue
                item_domain = item.get("domain", "")
                if competitor_position is None and hostnames_equal(
                    competitor_host, item_domain
                ):
                    competitor_position = _item_rank(item)
                if (
                    owned_position is None
                    and owned_host
                    and hostnames_equal(owned_host, item_domain)
                ):
                    owned_position = _item_rank(item)

            gap = None
            if competitor_position and owned_position:
                gap = owned_position - competitor_position
            elif competitor_position and not owned_position:
                gap = "Not ranking"
            comparison.append(
                {
                    "keyword": keyword,
                    "competitor_position": competitor_position,
                    "your_position": owned_position,
                    "gap": gap,
                    "opportunity": "high"
                    if competitor_position and not owned_position
                    else "medium"
                    if isinstance(gap, (int, float)) and gap > 10
                    else "low",
                }
            )

        return {
            "competitor": competitor_host,
            "your_domain": owned_host,
            "comparison": comparison,
        }

    def get_keyword_ideas(
        self, seed_keyword: str, location_code: int = 2840, limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get related keyword ideas with documented keyword and SERP metrics."""
        data = [
            {
                "keyword": seed_keyword,
                "location_code": location_code,
                "language_code": "en",
                "include_serp_info": True,
                "limit": limit,
            }
        ]
        response = self._post("/v3/dataforseo_labs/google/related_keywords/live", data)
        task = self._require_task(response, "related keywords")
        result = self._require_result(task, "related keywords")
        items = result.get("items")
        if not isinstance(items, list):
            raise DataForSEOContractError(
                "DataForSEO related keywords result items must be an array"
            )

        keywords = []
        for item in items:
            if not isinstance(item, dict):
                raise DataForSEOContractError(
                    "DataForSEO related keyword item must be an object"
                )
            keyword_info = item.get("keyword_data", {}).get("keyword_info", {})
            keywords.append(
                {
                    "keyword": item.get("keyword_data", {}).get("keyword"),
                    "search_volume": keyword_info.get("search_volume"),
                    "cpc": keyword_info.get("cpc"),
                    "competition": keyword_info.get("competition"),
                    "serp_results_count": item.get("serp_info", {}).get(
                        "se_results_count"
                    ),
                }
            )
        keywords.sort(key=lambda row: row["search_volume"] or 0, reverse=True)
        return keywords

    def get_questions(
        self, keyword: str, location_code: int = 2840, limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get question-form related keywords."""
        data = [
            {
                "keyword": keyword,
                "location_code": location_code,
                "language_code": "en",
                "limit": limit,
            }
        ]
        response = self._post("/v3/dataforseo_labs/google/related_keywords/live", data)
        task = self._require_task(response, "related questions")
        result = self._require_result(task, "related questions")
        items = result.get("items")
        if not isinstance(items, list):
            raise DataForSEOContractError(
                "DataForSEO related questions result items must be an array"
            )

        questions = []
        for item in items:
            if not isinstance(item, dict):
                raise DataForSEOContractError(
                    "DataForSEO related question item must be an object"
                )
            keyword_data = item.get("keyword_data", {})
            candidate = keyword_data.get("keyword", "")
            if QUESTION_PREFIX_RE.match(candidate.strip()):
                keyword_info = keyword_data.get("keyword_info", {})
                questions.append(
                    {
                        "question": candidate,
                        "search_volume": keyword_info.get("search_volume"),
                        "cpc": keyword_info.get("cpc"),
                    }
                )
        questions.sort(key=lambda row: row["search_volume"] or 0, reverse=True)
        return questions

    def get_domain_metrics(self, domain: str) -> Dict[str, Any]:
        """Get documented organic domain rank-overview metrics."""
        target_domain = normalize_hostname(domain)
        if not target_domain:
            raise ValueError("domain must contain a valid hostname")
        data = [
            {
                "target": target_domain,
                "location_code": 2840,
                "language_code": "en",
            }
        ]
        response = self._post(
            "/v3/dataforseo_labs/google/domain_rank_overview/live", data
        )
        task = self._require_task(response, "domain rank overview")
        result = self._require_result(task, "domain rank overview")
        items = result.get("items")
        if not isinstance(items, list):
            raise DataForSEOContractError(
                "DataForSEO domain rank overview result items must be an array"
            )

        organic: Dict[str, Any] = {}
        if items:
            first_item = items[0]
            if not isinstance(first_item, dict):
                raise DataForSEOContractError(
                    "DataForSEO domain rank overview item must be an object"
                )
            metrics = first_item.get("metrics")
            if not isinstance(metrics, dict) or not isinstance(
                metrics.get("organic"), dict
            ):
                raise DataForSEOContractError(
                    "DataForSEO domain rank overview item is missing organic metrics"
                )
            organic = metrics["organic"]

        position_keys = (
            "pos_1",
            "pos_2_3",
            "pos_4_10",
            "pos_11_20",
            "pos_21_30",
            "pos_31_40",
            "pos_41_50",
            "pos_51_60",
            "pos_61_70",
            "pos_71_80",
            "pos_81_90",
            "pos_91_100",
        )
        movement_keys = ("is_new", "is_up", "is_down", "is_lost")
        return {
            "domain": target_domain,
            "location_code": result.get("location_code"),
            "language_code": result.get("language_code"),
            "organic_keywords": organic.get("count"),
            "organic_traffic": organic.get("etv"),
            "organic_estimated_paid_traffic_cost": organic.get(
                "estimated_paid_traffic_cost"
            ),
            "organic_position_distribution": {
                key: organic.get(key) for key in position_keys if key in organic
            },
            "organic_movement": {
                key: organic.get(key) for key in movement_keys if key in organic
            },
        }

    def check_ranking_history(
        self, domain: str, keyword: str, months_back: int = 3
    ) -> List[Dict[str, Any]]:
        """Get monthly exact-host organic rankings from historical SERP snapshots."""
        if (
            isinstance(months_back, bool)
            or not isinstance(months_back, int)
            or months_back <= 0
            or months_back > 12
        ):
            raise ValueError("months_back must be an integer from 1 through 12")
        target_domain = normalize_hostname(domain)
        if not target_domain:
            raise ValueError("domain must contain a valid hostname")

        date_to = _today()
        date_from = _months_before(date_to, months_back)
        data = [
            {
                "keyword": keyword,
                "location_code": 2840,
                "language_code": "en",
                "date_from": date_from.isoformat(),
                "date_to": date_to.isoformat(),
            }
        ]
        response = self._post("/v3/dataforseo_labs/google/historical_serps/live", data)
        task = self._require_task(response, "historical SERPs")
        result = self._require_result(task, "historical SERPs")
        snapshots = result.get("items")
        if not isinstance(snapshots, list):
            raise DataForSEOContractError(
                "DataForSEO historical SERPs result items must be an array"
            )

        history = []
        for snapshot in snapshots:
            if not isinstance(snapshot, dict):
                raise DataForSEOContractError(
                    "DataForSEO historical SERP snapshot must be an object"
                )
            if snapshot.get("type") != "organic":
                continue
            items = snapshot.get("items")
            if not isinstance(items, list):
                raise DataForSEOContractError(
                    "DataForSEO historical SERP snapshot items must be an array"
                )
            match = next(
                (
                    item
                    for item in items
                    if isinstance(item, dict)
                    and item.get("type") == "organic"
                    and hostnames_equal(target_domain, item.get("domain", ""))
                ),
                None,
            )
            rank_group = match.get("rank_group") if match else None
            rank_absolute = match.get("rank_absolute") if match else None
            position = _item_rank(match) if match else None
            history.append(
                {
                    "keyword": keyword,
                    "domain": target_domain,
                    "datetime": snapshot.get("datetime"),
                    "position": position,
                    "rank_group": rank_group,
                    "rank_absolute": rank_absolute,
                    "url": match.get("url") if match else None,
                    "ranking": position is not None,
                }
            )
        return history


def _today() -> date:
    return date.today()


def _months_before(value: date, months: int) -> date:
    month_index = value.year * 12 + value.month - 1 - months
    year, zero_based_month = divmod(month_index, 12)
    month = zero_based_month + 1
    day = min(value.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


def _item_rank(item: Dict[str, Any]) -> Optional[int]:
    rank_group = item.get("rank_group")
    if isinstance(rank_group, int):
        return rank_group
    rank_absolute = item.get("rank_absolute")
    return rank_absolute if isinstance(rank_absolute, int) else None


# Example usage
if __name__ == "__main__":
    from dotenv import load_dotenv

    load_dotenv("data_sources/config/.env")

    dfs = DataForSEO()

    print("Checking rankings for Castos...")
    rankings = dfs.get_rankings(
        domain="castos.com",
        keywords=["podcast hosting", "podcast analytics", "private podcast"],
    )

    for rank in rankings:
        print(f"\nKeyword: {rank['keyword']}")
        print(f"Position: {rank['position'] or 'Not ranking'}")
        print(
            f"Search Volume: {rank['search_volume']:,}"
            if rank["search_volume"]
            else "Search Volume: N/A"
        )

    print("\n\nGetting SERP data for 'podcast monetization'...")
    serp = dfs.get_serp_data("podcast monetization")

    print(f"Search Volume: {serp['search_volume']:,}")
    print(f"SERP Features: {', '.join(serp['features'])}")
    print("\nTop 10 Results:")
    for result in serp["organic_results"][:10]:
        print(f"{result['position']}. {result['domain']}")
        print(f"   {result['url']}")

    print("\n\nRelated questions for 'podcast monetization':")
    questions = dfs.get_questions("podcast monetization")
    for q in questions[:10]:
        print(f"- {q['question']}")
        print(
            f"  Volume: {q['search_volume']:,}"
            if q["search_volume"]
            else "  Volume: N/A"
        )
