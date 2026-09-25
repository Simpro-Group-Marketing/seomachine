"""Shared SERP raw-capture normalization helpers."""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

from .contracts import SERP_APPROVED_COLLECTORS
from .contracts import SERP_APPROVED_DATAFORSEO_LOCATION_CODES
from .contracts import SERP_APPROVED_GOOGLE_COUNTRIES
from .contracts import SERP_APPROVED_SEMRUSH_DATABASES
from .contracts import SERP_RAW_CAPTURE_ATTESTATION_PURPOSE
from .contracts import SERP_RAW_CAPTURE_FIELDS
from .contracts import SERP_RAW_CAPTURE_SCHEMA
from .contracts import _rfc3339_utc
from .dependencies import EditorialPlanDependencies
from .dependencies import default_editorial_plan_dependencies


def load_json_text(value: str, *, field: str) -> Any:
    """Parse one exact JSON text value with a field-specific failure."""
    try:
        return json.loads(value)
    except (TypeError, json.JSONDecodeError) as error:
        raise ValueError(f"{field} is not valid JSON") from error


def _artifact_workspace_root(
    artifact: Path,
    workspace_root: str | Path | None,
) -> Path:
    if workspace_root is not None:
        return Path(workspace_root).resolve()
    resolved = artifact.resolve()
    cwd = Path.cwd().resolve()
    try:
        resolved.relative_to(cwd)
    except ValueError:
        return resolved.parent.parent if resolved.parent.name == "research" else resolved.parent
    return cwd


def _load_valid_serp_raw_capture(
    path: str | Path,
    *,
    workspace_root: str | Path,
    dependencies: EditorialPlanDependencies,
) -> tuple[Any, Mapping[str, Any], Mapping[str, Any]]:
    root = Path(workspace_root).resolve()
    snapshot = dependencies.load_json_object_snapshot(path, field="SERP raw capture")
    capture, normalized = _validate_serp_raw_snapshot(
        snapshot,
        workspace_root=root,
        dependencies=dependencies,
    )
    return snapshot, capture, normalized


def load_normalized_serp_raw_capture(
    path: str | Path,
    *,
    workspace_root: str | Path,
    dependencies: EditorialPlanDependencies | None = None,
) -> dict[str, Any]:
    """Reopen, validate, and normalize one exact persisted raw capture."""
    dependencies = dependencies or default_editorial_plan_dependencies()
    _, _, normalized = _load_valid_serp_raw_capture(
        path,
        workspace_root=workspace_root,
        dependencies=dependencies,
    )
    return dict(normalized)


def _validate_serp_raw_snapshot(
    snapshot: Any,
    *,
    workspace_root: str | Path,
    dependencies: EditorialPlanDependencies,
) -> tuple[Mapping[str, Any], Mapping[str, Any]]:
    root = Path(workspace_root).resolve()
    capture, collector = _validated_capture_payload(snapshot)
    _validate_capture_identity(capture, root, dependencies)
    _validate_capture_request(capture, collector)
    normalized = _normalize_serp_raw_response(
        capture.get("raw_response"),
        collector_name=str(collector["name"]),
    )
    return capture, normalized


def _validated_capture_payload(
    snapshot: Any,
) -> tuple[Mapping[str, Any], Mapping[str, Any]]:
    capture = snapshot.payload
    if set(capture) != SERP_RAW_CAPTURE_FIELDS:
        raise ValueError("SERP raw capture shape is invalid")
    if capture.get("schema") != SERP_RAW_CAPTURE_SCHEMA:
        raise ValueError("SERP raw capture schema is invalid")
    collector = capture.get("collector")
    if (
        not isinstance(collector, Mapping)
        or set(collector) != {"name", "version"}
        or (collector.get("name"), collector.get("version"))
        not in SERP_APPROVED_COLLECTORS
    ):
        raise ValueError("SERP raw capture collector is not approved")
    return capture, collector


def _validate_capture_identity(
    capture: Mapping[str, Any],
    workspace_root: Path,
    dependencies: EditorialPlanDependencies,
) -> None:
    if not dependencies.verify_mapping_attestation(
        capture,
        purpose=SERP_RAW_CAPTURE_ATTESTATION_PURPOSE,
        workspace_root=workspace_root,
    ):
        raise ValueError("SERP raw capture execution attestation is invalid")
    for field in ("query", "run_id"):
        value = capture.get(field)
        if not isinstance(value, str) or not value.strip() or value != value.strip():
            raise ValueError(f"SERP raw capture {field} is invalid")
    timestamp = _rfc3339_utc(capture.get("collected_at"))
    if timestamp is None:
        raise ValueError("SERP raw capture collected_at is invalid")
    if timestamp > datetime.now(timezone.utc):
        raise ValueError("SERP raw capture collected_at is in the future")


def _validate_capture_request(
    capture: Mapping[str, Any],
    collector: Mapping[str, Any],
) -> None:
    request = capture.get("request")
    if (
        not isinstance(request, Mapping)
        or set(request) != {"url", "locale"}
        or not isinstance(request.get("url"), str)
        or not request.get("url")
        or not isinstance(request.get("locale"), Mapping)
    ):
        raise ValueError("SERP raw capture request binding is invalid")
    request_url = str(request["url"])
    locale = request["locale"]
    if collector.get("name") == "research_serp_analysis:dataforseo":
        if not _dataforseo_request_valid(request_url, locale):
            raise ValueError("DataForSEO raw capture request or locale is not approved")
    elif collector.get("name") == "research_serp_analysis:semrush":
        if not _semrush_request_valid(request_url, locale):
            raise ValueError("Semrush raw capture request or locale is not approved")
    elif not _playwright_request_valid(
        request_url,
        locale,
        query=str(capture["query"]),
    ):
        raise ValueError("Playwright raw capture request or locale is not approved")


def _dataforseo_request_valid(url: str, locale: Mapping[str, Any]) -> bool:
    values = dict(locale)
    return (
        url == "dataforseo://serp/google/organic/live/advanced"
        and set(values) == {"language_code", "location_code"}
        and values.get("language_code") == "en"
        and values.get("location_code") in SERP_APPROVED_DATAFORSEO_LOCATION_CODES
    )


def _semrush_request_valid(url: str, locale: Mapping[str, Any]) -> bool:
    values = dict(locale)
    return (
        url == "semrush://keyword/phrase_organic"
        and set(values) == {"database"}
        and values.get("database") in SERP_APPROVED_SEMRUSH_DATABASES
    )


def _playwright_request_valid(
    url: str,
    locale: Mapping[str, Any],
    *,
    query: str,
) -> bool:
    parsed_url = urlparse(url)
    query_values = parse_qs(parsed_url.query)
    values = dict(locale)
    return (
        parsed_url.scheme == "https"
        and parsed_url.hostname in {"google.com", "www.google.com"}
        and parsed_url.path == "/search"
        and query_values.get("q") == [query]
        and set(values) == {"hl", "gl", "pws"}
        and values.get("hl") == "en"
        and values.get("pws") == "0"
        and values.get("gl") in SERP_APPROVED_GOOGLE_COUNTRIES
        # The declared locale must agree with the URL actually fetched,
        # otherwise a capture can claim one market and request another.
        and query_values.get("gl", [values.get("gl")]) == [values.get("gl")]
    )


def _normalize_serp_raw_response(
    raw_response: Any,
    *,
    collector_name: str,
) -> Mapping[str, Any]:
    value = _decode_playwright_response(raw_response, collector_name)
    if not isinstance(value, Mapping):
        raise ValueError("SERP raw response must resolve to an object")
    if collector_name == "research_serp_analysis:dataforseo" and "tasks" in value:
        value = _normalize_dataforseo_response(value)
    _validate_normalized_response(value)
    return value


def _decode_playwright_response(raw_response: Any, collector_name: str) -> Any:
    value = raw_response
    if collector_name == "research_serp_analysis:playwright":
        if not isinstance(value, str) or not value.strip():
            raise ValueError("Playwright raw response must be the exact CLI text")
        value = load_json_text(value.strip(), field="Playwright CLI raw response")
        if isinstance(value, str):
            value = load_json_text(value, field="Playwright CLI embedded response")
    return value


def _normalize_dataforseo_response(value: Mapping[str, Any]) -> Mapping[str, Any]:
    tasks = value.get("tasks")
    if not isinstance(tasks, list) or len(tasks) != 1 or not isinstance(tasks[0], Mapping):
        raise ValueError("DataForSEO raw response must contain exactly one task")
    results = tasks[0].get("result")
    if not isinstance(results, list) or not results or not isinstance(results[0], Mapping):
        raise ValueError("DataForSEO raw response task result is invalid")
    items = results[0].get("items")
    if not isinstance(items, list):
        raise ValueError("DataForSEO raw response result items are invalid")
    return _normalize_dataforseo_items(items)


def _normalize_dataforseo_items(items: list[Any]) -> Mapping[str, Any]:
    organic_results: list[dict[str, Any]] = []
    features: list[str] = []
    for item in items:
        if not isinstance(item, Mapping):
            raise ValueError("DataForSEO raw response item is invalid")
        item_type = item.get("type")
        if item_type == "organic":
            organic_results.append({
                "title": item.get("title"),
                "url": item.get("url"),
                "description": item.get("description") or "",
            })
        elif isinstance(item_type, str) and item_type and item_type not in features:
            features.append(item_type)
    return {"organic_results": organic_results, "features": features}


def _validate_normalized_response(value: Mapping[str, Any]) -> None:
    organic = value.get("organic_results")
    features = value.get("features")
    if not isinstance(organic, list) or not isinstance(features, list):
        raise ValueError("SERP raw response requires organic_results and features lists")
    for row in organic:
        if (
            not isinstance(row, Mapping)
            or not isinstance(row.get("title"), str)
            or not row.get("title").strip()
            or not isinstance(row.get("url"), str)
            or not row.get("url").strip()
        ):
            raise ValueError("SERP raw organic result is invalid")
    if any(not isinstance(item, str) or not item.strip() for item in features):
        raise ValueError("SERP raw features must be non-empty strings")


def _unique_strings(values: Any) -> list[str]:
    if not isinstance(values, list):
        raise ValueError("SERP observation source must be a list")
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        if not isinstance(value, str) or not value.strip():
            raise ValueError("SERP observations must be non-empty strings")
        text = value.strip()
        key = text.casefold()
        if key not in seen:
            seen.add(key)
            result.append(text)
    return result


def _serp_content_type(title: str) -> str:
    patterns = (
        ("Listicle", (r"\d+\s+(best|top|ways|tips|tools|ideas|examples|reasons)",)),
        ("How-To Guide", (r"how to", r"guide to", r"tutorial")),
        ("Definition", (r"what is", r"what are", r"meaning of", r"definition")),
        ("Comparison", (r"vs\.?", r"versus", r"compared", r"comparison", r"difference between")),
        ("Review", (r"review", r"reviewed")),
        ("Tool/Resource", (r"calculator", r"tool", r"generator", r"template", r"free")),
    )
    for content_type, expressions in patterns:
        if any(re.search(expression, title, re.IGNORECASE) for expression in expressions):
            return content_type
    return "General Article"


__all__ = [
    "load_json_text",
    "load_normalized_serp_raw_capture",
    "_artifact_workspace_root",
    "_load_valid_serp_raw_capture",
    "_serp_content_type",
    "_unique_strings",
    "_validate_serp_raw_snapshot",
]
