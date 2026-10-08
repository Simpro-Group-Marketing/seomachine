from __future__ import annotations

import ast
from pathlib import Path

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
