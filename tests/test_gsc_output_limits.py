from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import pytest

from data_sources.modules.bounded_io import OutputByteLimitError, atomic_write_text
from data_sources.modules.gsc.pagination import (
    GscOutputLimitError,
    GscQueryMode,
    iter_search_analytics_rows,
    query_search_analytics,
)


class _Executable:
    def __init__(self, response: dict[str, object]) -> None:
        self.response = response

    def execute(self) -> dict[str, object]:
        return deepcopy(self.response)


class _ScriptedSearchAnalytics:
    def __init__(self, outcomes: list[object]) -> None:
        self.outcomes = outcomes

    def query(self, *, siteUrl: str, body: dict[str, object]) -> _Executable:
        assert siteUrl == "sc-domain:example.com"
        assert body["startRow"] >= 0
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, BaseException):
            raise outcome
        return _Executable(outcome)  # type: ignore[arg-type]


class _ScriptedService:
    def __init__(self, outcomes: list[object]) -> None:
        self.analytics = _ScriptedSearchAnalytics(outcomes)

    def searchanalytics(self) -> _ScriptedSearchAnalytics:
        return self.analytics


def _rows(count: int) -> list[dict[str, object]]:
    return [{"keys": [f"query-{index}"], "clicks": index} for index in range(count)]


def _json_size(value: object) -> int:
    return len(
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    )


def test_page_byte_limit_accepts_exact_boundary_and_rejects_one_byte_over() -> None:
    response = {"rows": [{"keys": ["é"], "clicks": 1}]}
    size = _json_size(response)

    assert query_search_analytics(
        _ScriptedService([response]),
        site_url="sc-domain:example.com",
        body={},
        max_rows=1,
        page_size=1,
        mode=GscQueryMode.TOP_N,
        max_page_bytes=size,
    ) == response

    with pytest.raises(GscOutputLimitError, match=f"exceeds {size - 1} bytes"):
        query_search_analytics(
            _ScriptedService([response]),
            site_url="sc-domain:example.com",
            body={},
            max_rows=1,
            page_size=1,
            mode=GscQueryMode.TOP_N,
            max_page_bytes=size - 1,
        )


def test_workflow_byte_limit_counts_each_fetched_page() -> None:
    first = {"rows": _rows(1)}
    second = {"rows": _rows(1)}
    max_bytes = _json_size(first) + _json_size(second) - 1

    with pytest.raises(GscOutputLimitError, match=f"exceeds {max_bytes} bytes"):
        list(
            iter_search_analytics_rows(
                _ScriptedService([first, second]),
                site_url="sc-domain:example.com",
                body={},
                max_rows=2,
                page_size=1,
                max_workflow_bytes=max_bytes,
            )
        )


def test_atomic_text_writer_preserves_existing_file_on_byte_overflow(
    tmp_path: Path,
) -> None:
    destination = tmp_path / "report.txt"
    destination.write_text("old", encoding="utf-8")

    with pytest.raises(OutputByteLimitError, match="MCP report exceeds 3 bytes"):
        atomic_write_text(destination, "éé", max_bytes=3, field="MCP report")

    assert destination.read_text(encoding="utf-8") == "old"
    assert [path.name for path in tmp_path.iterdir()] == ["report.txt"]
