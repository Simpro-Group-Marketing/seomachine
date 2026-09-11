from __future__ import annotations

import ast
from copy import deepcopy
from pathlib import Path

from data_sources.modules.gsc import GSC_MAX_WORKFLOW_ROWS, GscQueryMode
from scripts import build_plumbing_recovery_evidence as plumbing
from scripts import live_blog_source_pull as live_blog

ROOT = Path(__file__).resolve().parents[1]
ALLOWED_DIRECT_QUERY = Path("data_sources/modules/gsc/pagination.py")


def _direct_search_analytics_query_lines(source: str) -> list[int]:
    tree = ast.parse(source)
    return sorted(
        node.lineno
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and _is_direct_search_analytics_query(node)
    )


def _is_direct_search_analytics_query(node: ast.Call) -> bool:
    query_attribute = node.func
    if not isinstance(query_attribute, ast.Attribute):
        return False
    searchanalytics_call = query_attribute.value
    if query_attribute.attr != "query" or not isinstance(
        searchanalytics_call, ast.Call
    ):
        return False
    searchanalytics_attribute = searchanalytics_call.func
    return (
        isinstance(searchanalytics_attribute, ast.Attribute)
        and searchanalytics_attribute.attr == "searchanalytics"
    )


class _Executable:
    def __init__(self, response: dict[str, object]) -> None:
        self.response = response

    def execute(self) -> dict[str, object]:
        return deepcopy(self.response)


class _SearchAnalytics:
    def query(self, **_: object) -> _Executable:
        raise AssertionError("scripts must use the shared bounded GSC API")


class _Service:
    def searchanalytics(self) -> _SearchAnalytics:
        return _SearchAnalytics()


def test_live_blog_ranking_count_is_complete_and_probes_are_top_n(monkeypatch) -> None:
    calls: list[dict[str, object]] = []

    def fake_query(service, **kwargs):
        assert isinstance(service, _Service)
        calls.append(kwargs)
        dimensions = kwargs["body"]["dimensions"]
        if dimensions == ["page"]:
            return {"rows": [{"keys": ["https://example.com/blog/post"]}]}
        return {"rows": [{"keys": ["query-a"], "impressions": 2}]}

    monkeypatch.setattr(live_blog.gsc, "query_search_analytics", fake_query)

    result = live_blog.pull_gsc_period(
        _Service(),
        "https://example.com/blog/post",
        "2026-08-01",
        "2026-08-31",
    )

    assert result["ranking_query_count"] == 1
    assert calls[0]["mode"] is GscQueryMode.TOP_N
    assert calls[0]["max_rows"] == 10
    assert calls[1]["mode"] is GscQueryMode.COMPLETE
    assert calls[1]["max_rows"] == GSC_MAX_WORKFLOW_ROWS


def test_plumbing_date_query_uses_complete_mode_and_keeps_metadata(monkeypatch) -> None:
    captured: dict[str, object] = {}
    expected = {
        "rows": [{"keys": ["20260901"], "clicks": 1}],
        "responseAggregationType": "byPage",
        "metadata": {"first_incomplete_date": "2026-09-01"},
    }

    def fake_query(service, **kwargs):
        assert isinstance(service, _Service)
        captured.update(kwargs)
        return deepcopy(expected)

    monkeypatch.setattr(plumbing.gsc, "query_search_analytics", fake_query)

    response = plumbing.gsc_query(
        _Service(),
        plumbing.PRIOR_START,
        plumbing.CURRENT_END,
        ["date"],
    )

    assert response == expected
    assert captured["mode"] is GscQueryMode.COMPLETE
    assert captured["max_rows"] == GSC_MAX_WORKFLOW_ROWS


def test_inventory_detects_whitespace_and_multiline_direct_calls() -> None:
    source = """def direct(service, body):
    return (
        service.searchanalytics()
        .query(
            siteUrl="sc-domain:example.com",
            body=body,
        )
        .execute()
    )
"""

    assert len(_direct_search_analytics_query_lines(source)) == 1


def test_repository_direct_query_inventory_is_centralized() -> None:
    findings: dict[str, list[int]] = {}
    for root_name in ("data_sources", "scripts", "tools"):
        for path in (ROOT / root_name).rglob("*.py"):
            relative = path.relative_to(ROOT)
            lines = _direct_search_analytics_query_lines(
                path.read_text(encoding="utf-8")
            )
            if lines and relative != ALLOWED_DIRECT_QUERY:
                findings[relative.as_posix()] = lines

    assert findings == {}
    boundary = ROOT / ALLOWED_DIRECT_QUERY
    assert len(
        _direct_search_analytics_query_lines(boundary.read_text(encoding="utf-8"))
    ) == 1


def test_migrated_scripts_contain_no_direct_search_analytics_query_calls() -> None:
    for path in (live_blog.__file__, plumbing.__file__):
        assert path is not None
        source = Path(path).read_text(encoding="utf-8")
        assert _direct_search_analytics_query_lines(source) == []
