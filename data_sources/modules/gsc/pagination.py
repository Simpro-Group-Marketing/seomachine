"""Bounded Search Analytics pagination."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterator, Mapping
from dataclasses import dataclass
from enum import Enum
from types import MappingProxyType
from typing import Any

GSC_MAX_PAGE_ROWS = 25_000
GSC_MAX_WORKFLOW_ROWS = 100_000


class GscPaginationError(RuntimeError):
    """Raised when Search Console returns an invalid or non-advancing page."""


class GscRowCapExceeded(GscPaginationError):
    """Raised when an exhaustive query has more rows than its declared cap."""


class GscQueryMode(str, Enum):
    """Declare whether a bounded query is intentionally limited or exhaustive."""

    TOP_N = "top_n"
    COMPLETE = "complete"


@dataclass(frozen=True, slots=True)
class GscPage:
    """One immutable Search Analytics page and its response metadata."""

    start_row: int
    requested_rows: int
    rows: tuple[Mapping[str, Any], ...]
    metadata: Mapping[str, Any]
    rows_field_present: bool


def query_search_analytics(
    service: Any,
    *,
    site_url: str,
    body: Mapping[str, Any],
    max_rows: int,
    mode: GscQueryMode,
    page_size: int = GSC_MAX_PAGE_ROWS,
) -> dict[str, Any]:
    """Return a bounded Search Analytics response with rows in API order."""
    rows: list[dict[str, Any]] = []
    first_metadata: dict[str, Any] | None = None
    first_rows_field_present = False
    for page in iter_search_analytics_pages(
        service,
        site_url=site_url,
        body=body,
        max_rows=max_rows,
        page_size=page_size,
        mode=mode,
    ):
        if first_metadata is None:
            first_metadata = _thaw_mapping(page.metadata)
            first_rows_field_present = page.rows_field_present
        rows.extend(_thaw_mapping(row) for row in page.rows)
    result = first_metadata or {}
    if first_rows_field_present or rows:
        result["rows"] = rows
    return result


def iter_search_analytics_pages(
    service: Any,
    *,
    site_url: str,
    body: Mapping[str, Any],
    max_rows: int,
    mode: GscQueryMode,
    page_size: int = GSC_MAX_PAGE_ROWS,
) -> Iterator[GscPage]:
    """Yield immutable pages, fetching each page only as iteration advances."""
    _validate_query(body=body, max_rows=max_rows, page_size=page_size, mode=mode)
    offset = 0
    page_digests: set[str] = set()
    while offset < max_rows:
        requested = min(page_size, max_rows - offset)
        response, page_rows = _query_page(
            service,
            site_url=site_url,
            body=body,
            start_row=offset,
            row_limit=requested,
        )
        if page_rows:
            _reject_invalid_page(page_rows, requested=requested, digests=page_digests)
        page = GscPage(
            start_row=offset,
            requested_rows=requested,
            rows=tuple(_freeze_mapping(row) for row in page_rows),
            metadata=_freeze_mapping(
                {key: value for key, value in response.items() if key != "rows"}
            ),
            rows_field_present="rows" in response,
        )
        page_length = len(page_rows)
        del response, page_rows
        yield page
        del page
        if not page_length:
            break
        offset += page_length
        if page_length < requested:
            break
    if mode is GscQueryMode.COMPLETE and offset == max_rows:
        _, overflow_rows = _query_page(
            service,
            site_url=site_url,
            body=body,
            start_row=offset,
            row_limit=1,
        )
        if overflow_rows:
            raise GscRowCapExceeded(
                f"Search Console returned more than {max_rows} rows"
            )


def iter_search_analytics_rows(
    service: Any,
    *,
    site_url: str,
    body: Mapping[str, Any],
    max_rows: int,
    page_size: int = GSC_MAX_PAGE_ROWS,
    require_complete: bool = False,
) -> Iterator[dict[str, Any]]:
    """Yield ordered Search Analytics rows without exceeding declared bounds."""
    mode = GscQueryMode.COMPLETE if require_complete else GscQueryMode.TOP_N
    for page in iter_search_analytics_pages(
        service,
        site_url=site_url,
        body=body,
        max_rows=max_rows,
        page_size=page_size,
        mode=mode,
    ):
        for row in page.rows:
            yield _thaw_mapping(row)


def _query_page(
    service: Any,
    *,
    site_url: str,
    body: Mapping[str, Any],
    start_row: int,
    row_limit: int,
) -> tuple[dict[str, Any], list[Mapping[str, Any]]]:
    request = dict(body)
    request["startRow"] = start_row
    request["rowLimit"] = row_limit
    response = service.searchanalytics().query(siteUrl=site_url, body=request).execute()
    if not isinstance(response, Mapping):
        raise GscPaginationError("Search Console response must be an object")
    rows = response.get("rows", [])
    if not isinstance(rows, list) or not all(isinstance(row, Mapping) for row in rows):
        raise GscPaginationError("Search Console rows must be objects")
    return dict(response), rows


def _reject_invalid_page(
    rows: list[Mapping[str, Any]],
    *,
    requested: int,
    digests: set[str],
) -> None:
    if len(rows) > requested:
        raise GscPaginationError("Search Console returned more rows than requested")
    digest = _page_digest(rows)
    if digest in digests:
        raise GscPaginationError("Search Console returned a repeated page")
    digests.add(digest)


def _page_digest(rows: list[Mapping[str, Any]]) -> str:
    encoder = json.JSONEncoder(
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    digest = hashlib.sha256()
    for chunk in encoder.iterencode(rows):
        digest.update(chunk.encode("utf-8"))
    return digest.hexdigest()


def _freeze_mapping(value: Mapping[str, Any]) -> Mapping[str, Any]:
    return MappingProxyType({key: _freeze_value(item) for key, item in value.items()})


def _freeze_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        return _freeze_mapping(value)
    if isinstance(value, list):
        return tuple(_freeze_value(item) for item in value)
    return value


def _thaw_mapping(value: Mapping[str, Any]) -> dict[str, Any]:
    return {key: _thaw_value(item) for key, item in value.items()}


def _thaw_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        return _thaw_mapping(value)
    if isinstance(value, tuple):
        return [_thaw_value(item) for item in value]
    return value


def _validate_bounds(*, max_rows: int, page_size: int) -> None:
    if (
        isinstance(max_rows, bool)
        or not isinstance(max_rows, int)
        or not 1 <= max_rows <= GSC_MAX_WORKFLOW_ROWS
    ):
        raise ValueError(f"max_rows must be between 1 and {GSC_MAX_WORKFLOW_ROWS}")
    if (
        isinstance(page_size, bool)
        or not isinstance(page_size, int)
        or not 1 <= page_size <= GSC_MAX_PAGE_ROWS
    ):
        raise ValueError(f"page_size must be between 1 and {GSC_MAX_PAGE_ROWS}")


def _validate_query(
    *,
    body: Mapping[str, Any],
    max_rows: int,
    page_size: int,
    mode: GscQueryMode,
) -> None:
    _validate_bounds(max_rows=max_rows, page_size=page_size)
    if not isinstance(body, Mapping):
        raise TypeError("body must be a mapping")
    if not isinstance(mode, GscQueryMode):
        raise ValueError("mode must be GscQueryMode.TOP_N or GscQueryMode.COMPLETE")
    for field in ("startRow", "rowLimit"):
        if field in body:
            raise ValueError(f"body must not define pagination field {field}")
