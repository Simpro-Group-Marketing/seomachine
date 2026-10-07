"""Declarative context build spec: one validated JSON file replaces per-topic scripts."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date as _date
from pathlib import Path
from typing import Any, Mapping

try:
    from ..bounded_io import canonical_json_sha256, parse_json_object, read_bounded
except ImportError:  # pragma: no cover - supports direct script execution.
    from bounded_io import canonical_json_sha256, parse_json_object, read_bounded

SPEC_SCHEMA = "simpro-context-build-spec/v1"
SPEC_MAX_BYTES = 1024 * 1024
MAX_SEARCH_QUERIES = 20
MAX_QUERY_CHARS = 500
OUTPUT_PREFIX = "research/"
CLAIM_REQUEST_KEYS = frozenset({"claim_id", "query", "use_mode", "brand_scope"})
_SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


class ContextBuildSpecError(ValueError):
    """Raised when a context build spec is invalid; the message names the field path."""


@dataclass(frozen=True)
class StageSpec:
    stage_id: str
    pack_path: str
    receipt_path: str
    claim_requests: tuple[dict[str, str], ...]


@dataclass(frozen=True)
class ContextBuildSpec:
    slug: str
    date: str
    request: dict[str, Any]
    request_path: str
    trace_path: str
    search_queries: tuple[str, ...]
    resource_purposes: dict[str, str]
    expand_resource_ids: tuple[str, ...]
    constraints: tuple[str, ...]
    claim_lookups: tuple[dict[str, Any], ...]
    claim_lookup_path: str | None
    stages: tuple[StageSpec, ...]
    digest: str


def _fail(field: str, message: str) -> ContextBuildSpecError:
    return ContextBuildSpecError(f"{field}: {message}")


def _object(value: Any, field: str) -> Mapping[str, Any]:
    if not isinstance(value, dict):
        raise _fail(field, "must be a JSON object")
    return value


def _check_keys(obj: Mapping[str, Any], required: set[str], optional: set[str], field: str) -> None:
    missing = sorted(required - obj.keys())
    if missing:
        raise _fail(field, f"missing required key(s): {', '.join(missing)}")
    unknown = sorted(obj.keys() - required - optional)
    if unknown:
        raise _fail(field, f"unknown key(s): {', '.join(unknown)}")


def _string(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise _fail(field, "must be a non-empty string")
    return value


def _string_list(value: Any, field: str) -> tuple[str, ...]:
    if not isinstance(value, list):
        raise _fail(field, "must be a list of strings")
    return tuple(_string(item, f"{field}[{index}]") for index, item in enumerate(value))


def _output_path(value: Any, field: str) -> str:
    path = _string(value, field)
    if "\\" in path or not path.startswith(OUTPUT_PREFIX):
        raise _fail(field, f"must be a relative '/' path starting with {OUTPUT_PREFIX}")
    if any(part in ("", ".", "..") for part in path.split("/")):
        raise _fail(field, "must not contain empty, '.', or '..' segments")
    return path


def _slug_and_date(raw: Mapping[str, Any]) -> tuple[str, str]:
    slug = _string(raw["slug"], "slug")
    if not _SLUG_RE.fullmatch(slug):
        raise _fail("slug", "must be lowercase letters, digits, and hyphens")
    date = _string(raw["date"], "date")
    try:
        if not _DATE_RE.fullmatch(date):
            raise ValueError(date)
        _date.fromisoformat(date)
    except ValueError:
        raise _fail("date", "must be a valid YYYY-MM-DD date") from None
    return slug, date


def _search_queries(value: Any) -> tuple[str, ...]:
    field = "discovery.search_queries"
    queries = _string_list(value, field)
    if not 1 <= len(queries) <= MAX_SEARCH_QUERIES:
        raise _fail(field, f"must contain 1 to {MAX_SEARCH_QUERIES} queries")
    if len(set(queries)) != len(queries):
        raise _fail(field, "queries must be unique")
    for index, query in enumerate(queries):
        if len(query) > MAX_QUERY_CHARS:
            raise _fail(f"{field}[{index}]", f"must be at most {MAX_QUERY_CHARS} characters")
    return queries


def _resource_purposes(value: Any) -> dict[str, str]:
    field = "discovery.resource_purposes"
    purposes = _object(value, field)
    return {_string(key, field): _string(item, f"{field}.{key}") for key, item in purposes.items()}


def _discovery(raw: Mapping[str, Any]) -> tuple[tuple[str, ...], dict[str, str], tuple[str, ...]]:
    discovery = _object(raw["discovery"], "discovery")
    _check_keys(discovery, {"search_queries", "resource_purposes", "expand_resource_ids"}, set(), "discovery")
    queries = _search_queries(discovery["search_queries"])
    purposes = _resource_purposes(discovery["resource_purposes"])
    expand = _string_list(discovery["expand_resource_ids"], "discovery.expand_resource_ids")
    for index, resource_id in enumerate(expand):
        if resource_id not in purposes:
            raise _fail(f"discovery.expand_resource_ids[{index}]", f"{resource_id} is not in resource_purposes")
    return queries, purposes, expand


def _outputs(raw: Mapping[str, Any]) -> tuple[str, str, str | None]:
    outputs = _object(raw["outputs"], "outputs")
    _check_keys(outputs, {"request", "trace"}, {"claim_lookup"}, "outputs")
    lookup = outputs.get("claim_lookup")
    return (
        _output_path(outputs["request"], "outputs.request"),
        _output_path(outputs["trace"], "outputs.trace"),
        None if lookup is None else _output_path(lookup, "outputs.claim_lookup"),
    )


def _claim_lookups(value: Any) -> tuple[dict[str, Any], ...]:
    if not isinstance(value, list):
        raise _fail("claim_lookups", "must be a list of objects")
    rows = []
    for index, item in enumerate(value):
        field = f"claim_lookups[{index}]"
        row = _object(item, field)
        _string(row.get("query"), f"{field}.query")
        _string(row.get("use_mode"), f"{field}.use_mode")
        rows.append(dict(row))
    return tuple(rows)


def _claim_requests(value: Any, field: str) -> tuple[dict[str, str], ...]:
    if not isinstance(value, list):
        raise _fail(field, "must be a list of objects")
    rows = []
    for index, item in enumerate(value):
        row_field = f"{field}[{index}]"
        row = _object(item, row_field)
        _check_keys(row, set(CLAIM_REQUEST_KEYS), set(), row_field)
        rows.append({key: _string(row[key], f"{row_field}.{key}") for key in sorted(CLAIM_REQUEST_KEYS)})
    return tuple(rows)


def _stage(item: Any, index: int) -> StageSpec:
    field = f"stages[{index}]"
    stage = _object(item, field)
    _check_keys(stage, {"id", "pack", "receipt", "claim_requests"}, set(), field)
    return StageSpec(
        stage_id=_string(stage["id"], f"{field}.id"),
        pack_path=_output_path(stage["pack"], f"{field}.pack"),
        receipt_path=_output_path(stage["receipt"], f"{field}.receipt"),
        claim_requests=_claim_requests(stage["claim_requests"], f"{field}.claim_requests"),
    )


def _stages(value: Any) -> tuple[StageSpec, ...]:
    if not isinstance(value, list) or not value:
        raise _fail("stages", "must be a non-empty list")
    stages = tuple(_stage(item, index) for index, item in enumerate(value))
    ids = [stage.stage_id for stage in stages]
    if len(set(ids)) != len(ids):
        raise _fail("stages", "stage ids must be unique")
    return stages


def _parse_spec_file(path: str | Path) -> dict[str, Any]:
    try:
        data = read_bounded(path, max_bytes=SPEC_MAX_BYTES, field="context build spec")
        return parse_json_object(data, field="context build spec")
    except ValueError as error:
        raise ContextBuildSpecError(f"context build spec: {error}") from error


def load_spec(path: str | Path) -> ContextBuildSpec:
    """Load and validate one context build spec; raise ContextBuildSpecError on any defect."""
    raw = _parse_spec_file(path)
    _check_keys(
        raw,
        {"schema", "slug", "date", "request", "outputs", "discovery", "constraints", "claim_lookups", "stages"},
        set(),
        "spec",
    )
    if raw["schema"] != SPEC_SCHEMA:
        raise _fail("schema", f"must be {SPEC_SCHEMA}")
    slug, date = _slug_and_date(raw)
    request_path, trace_path, claim_lookup_path = _outputs(raw)
    queries, purposes, expand = _discovery(raw)
    return ContextBuildSpec(
        slug=slug,
        date=date,
        request=dict(_object(raw["request"], "request")),
        request_path=request_path,
        trace_path=trace_path,
        search_queries=queries,
        resource_purposes=purposes,
        expand_resource_ids=expand,
        constraints=_string_list(raw["constraints"], "constraints"),
        claim_lookups=_claim_lookups(raw["claim_lookups"]),
        claim_lookup_path=claim_lookup_path,
        stages=_stages(raw["stages"]),
        digest=canonical_json_sha256(raw),
    )
