from __future__ import annotations

from copy import deepcopy

import pytest

from data_sources.modules.gsc.pagination import (
    GscPaginationError,
    GscQueryMode,
    GscRowCapExceeded,
    iter_search_analytics_rows,
    query_search_analytics,
)


class _Executable:
    def __init__(self, response: dict[str, object]) -> None:
        self.response = response

    def execute(self) -> dict[str, object]:
        return deepcopy(self.response)


class _SearchAnalytics:
    def __init__(self, rows: list[dict[str, object]]) -> None:
        self.rows = rows
        self.requests: list[dict[str, object]] = []

    def query(self, *, siteUrl: str, body: dict[str, object]) -> _Executable:
        assert siteUrl == "sc-domain:example.com"
        self.requests.append(deepcopy(body))
        start = int(body["startRow"])
        limit = int(body["rowLimit"])
        return _Executable({"rows": self.rows[start : start + limit]})


class _Service:
    def __init__(self, rows: list[dict[str, object]]) -> None:
        self.analytics = _SearchAnalytics(rows)

    def searchanalytics(self) -> _SearchAnalytics:
        return self.analytics


def _rows(count: int) -> list[dict[str, object]]:
    return [{"keys": [f"query-{index}"], "clicks": index} for index in range(count)]


def test_paginator_advances_start_row_and_preserves_input_order() -> None:
    service = _Service(_rows(5))

    actual = list(
        iter_search_analytics_rows(
            service,
            site_url="sc-domain:example.com",
            body={"dimensions": ["query"]},
            max_rows=10,
            page_size=2,
            require_complete=True,
        )
    )

    assert actual == _rows(5)
    assert [request["startRow"] for request in service.analytics.requests] == [0, 2, 4]
    assert [request["rowLimit"] for request in service.analytics.requests] == [2, 2, 2]


def test_paginator_does_not_mutate_the_callers_request() -> None:
    service = _Service(_rows(1))
    body = {"dimensions": ["query"]}

    list(
        iter_search_analytics_rows(
            service,
            site_url="sc-domain:example.com",
            body=body,
            max_rows=5,
            page_size=2,
        )
    )

    assert body == {"dimensions": ["query"]}


def test_exhaustive_paginator_fails_when_rows_exist_beyond_the_cap() -> None:
    service = _Service(_rows(5))

    with pytest.raises(GscRowCapExceeded, match="more than 4 rows"):
        list(
            iter_search_analytics_rows(
                service,
                site_url="sc-domain:example.com",
                body={"dimensions": ["query"]},
                max_rows=4,
                page_size=2,
                require_complete=True,
            )
        )

    assert [request["startRow"] for request in service.analytics.requests] == [0, 2, 4]
    assert service.analytics.requests[-1]["rowLimit"] == 1


def test_intentional_limit_stops_without_an_overflow_probe() -> None:
    service = _Service(_rows(5))

    actual = list(
        iter_search_analytics_rows(
            service,
            site_url="sc-domain:example.com",
            body={"dimensions": ["query"]},
            max_rows=4,
            page_size=2,
            require_complete=False,
        )
    )

    assert actual == _rows(4)
    assert [request["startRow"] for request in service.analytics.requests] == [0, 2]


@pytest.mark.parametrize(
    ("max_rows", "page_size"),
    [(0, 1), (100_001, 1), (1, 0), (1, 25_001), (True, 1)],
)
def test_paginator_rejects_invalid_bounds(max_rows: int, page_size: int) -> None:
    with pytest.raises(ValueError):
        list(
            iter_search_analytics_rows(
                _Service([]),
                site_url="sc-domain:example.com",
                body={},
                max_rows=max_rows,
                page_size=page_size,
            )
        )


class _ScriptedSearchAnalytics:
    def __init__(self, outcomes: list[object]) -> None:
        self.outcomes = outcomes
        self.requests: list[dict[str, object]] = []

    def query(self, *, siteUrl: str, body: dict[str, object]) -> _Executable:
        assert siteUrl == "sc-domain:example.com"
        self.requests.append(deepcopy(body))
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, BaseException):
            raise outcome
        return _Executable(outcome)  # type: ignore[arg-type]


class _ScriptedService:
    def __init__(self, outcomes: list[object]) -> None:
        self.analytics = _ScriptedSearchAnalytics(outcomes)

    def searchanalytics(self) -> _ScriptedSearchAnalytics:
        return self.analytics


def test_query_aggregates_pages_in_order_and_preserves_response_metadata() -> None:
    service = _ScriptedService(
        [
            {
                "rows": _rows(2),
                "responseAggregationType": "byPage",
                "metadata": {"first_incomplete_date": "2026-09-09"},
            },
            {"rows": _rows(1)},
        ]
    )

    response = query_search_analytics(
        service,
        site_url="sc-domain:example.com",
        body={"dimensions": ["query"]},
        max_rows=10,
        page_size=2,
        mode=GscQueryMode.COMPLETE,
    )

    assert response == {
        "rows": [*_rows(2), *_rows(1)],
        "responseAggregationType": "byPage",
        "metadata": {"first_incomplete_date": "2026-09-09"},
    }
    assert [request["startRow"] for request in service.analytics.requests] == [0, 2]


@pytest.mark.parametrize("field", ["startRow", "rowLimit"])
def test_query_rejects_caller_owned_pagination_fields(field: str) -> None:
    service = _ScriptedService([])

    with pytest.raises(ValueError, match=field):
        query_search_analytics(
            service,
            site_url="sc-domain:example.com",
            body={field: 1},
            max_rows=10,
            mode=GscQueryMode.TOP_N,
        )

    assert service.analytics.requests == []


def test_complete_query_fails_closed_when_a_row_exists_beyond_the_cap() -> None:
    all_rows = _rows(5)
    service = _ScriptedService(
        [{"rows": all_rows[:2]}, {"rows": all_rows[2:4]}, {"rows": all_rows[4:]}]
    )

    with pytest.raises(GscRowCapExceeded, match="more than 4 rows"):
        query_search_analytics(
            service,
            site_url="sc-domain:example.com",
            body={},
            max_rows=4,
            page_size=2,
            mode=GscQueryMode.COMPLETE,
        )


def test_query_propagates_an_error_from_a_later_page() -> None:
    service = _ScriptedService([{"rows": _rows(2)}, RuntimeError("quota exhausted")])

    with pytest.raises(RuntimeError, match="quota exhausted"):
        query_search_analytics(
            service,
            site_url="sc-domain:example.com",
            body={},
            max_rows=4,
            page_size=2,
            mode=GscQueryMode.COMPLETE,
        )


def test_query_rejects_a_repeated_page() -> None:
    page = {"rows": _rows(2)}
    service = _ScriptedService([page, page])

    with pytest.raises(GscPaginationError, match="repeated page"):
        query_search_analytics(
            service,
            site_url="sc-domain:example.com",
            body={},
            max_rows=4,
            page_size=2,
            mode=GscQueryMode.COMPLETE,
        )


@pytest.mark.parametrize(
    "response",
    [None, [], {"rows": None}, {"rows": "invalid"}, {"rows": ["invalid"]}],
)
def test_query_rejects_invalid_response_shapes(response: object) -> None:
    service = _ScriptedService([response])

    with pytest.raises(GscPaginationError):
        query_search_analytics(
            service,
            site_url="sc-domain:example.com",
            body={},
            max_rows=2,
            page_size=2,
            mode=GscQueryMode.TOP_N,
        )
