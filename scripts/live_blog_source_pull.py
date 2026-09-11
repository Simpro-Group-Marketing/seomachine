#!/usr/bin/env python3
"""Pull source-bound GSC, GA4, and Peec evidence for the corrected blog rerun."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from datetime import date, timedelta
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from data_sources.modules import gsc  # noqa: E402 - script path bootstrap

GSC_SITE = "sc-domain:simprogroup.com"
GA4_PROPERTY = "properties/309907809"
GA4_HOST = "www.simprogroup.com"
PEEC_PROJECT = "or_a1efbfcd-d5aa-428a-ad3b-dbfd867e037b"
PEEC_CHANNELS = {
    "openai-0": "ChatGPT UI",
    "google-0": "Google AI Overview",
    "perplexity-0": "Perplexity UI",
}
MARKETINGSKILLS = Path(
    "/mnt/c/Users/patrick.grueschow/Desktop/Repos/marketingskills-main"
)
GSC_TOKEN = Path(
    "/mnt/c/Users/patrick.grueschow/Desktop/Repos/seo-command-centerV3-main/"
    "mcp-gsc/token.json"
)
ADC_PATH = MARKETINGSKILLS / "credentials/adc.json"


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=True, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def load_dotenv(path: Path) -> None:
    if not path.is_file():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def normalize_url(value: str) -> str:
    cleaned = value.strip().split("?", 1)[0].split("#", 1)[0].rstrip("/").lower()
    return cleaned


def normalize_peec_url(value: str) -> str:
    return normalize_url(value).replace("https://www.", "https://", 1)


def page_path_variants(url: str) -> list[str]:
    from urllib.parse import urlsplit

    path = urlsplit(url).path.rstrip("/")
    return [path, f"{path}/"]


def url_variants(url: str) -> list[str]:
    base = normalize_url(url)
    without_www = base.replace("https://www.", "https://", 1)
    variants = [base, f"{base}/", without_www, f"{without_www}/"]
    return list(dict.fromkeys(variants))


def create_gsc_service():
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build

    if not GSC_TOKEN.is_file():
        raise FileNotFoundError(f"GSC OAuth token not found: {GSC_TOKEN}")
    credentials = Credentials.from_authorized_user_file(
        str(GSC_TOKEN), ["https://www.googleapis.com/auth/webmasters"]
    )
    if credentials.expired and credentials.refresh_token:
        credentials.refresh(Request())
    if not credentials.valid:
        raise RuntimeError("GSC OAuth credentials are not valid")
    return build("searchconsole", "v1", credentials=credentials, cache_discovery=False)


def gsc_query(
    service,
    start_date: str, end_date: str, dimensions: list[str], *,
    page_url: str | None = None,
    row_limit: int = 25_000, mode: gsc.GscQueryMode,
) -> dict[str, Any]:
    body: dict[str, Any] = {
        "startDate": start_date,
        "endDate": end_date,
        "dimensions": dimensions,
        "type": "web",
        "dataState": "final",
    }
    if page_url:
        body["dimensionFilterGroups"] = [
            {
                "groupType": "and",
                "filters": [
                    {
                        "dimension": "page",
                        "operator": "equals",
                        "expression": page_url,
                    }
                ],
            }
        ]
    return gsc.query_search_analytics(
        service, site_url=GSC_SITE, body=body, max_rows=row_limit, mode=mode
    )


def pull_gsc_period(service, url: str, start_date: str, end_date: str) -> dict[str, Any]:
    selected_variant = None
    page_rows: list[dict[str, Any]] = []
    probes: list[dict[str, Any]] = []
    for variant in [normalize_url(url), f"{normalize_url(url)}/"]:
        response = gsc_query(
            service,
            start_date,
            end_date,
            ["page"],
            page_url=variant,
            row_limit=10, mode=gsc.GscQueryMode.TOP_N,
        )
        rows = response.get("rows") or []
        probes.append({"variant": variant, "row_count": len(rows)})
        if rows:
            selected_variant = variant
            page_rows = rows
            break
    if selected_variant is None:
        return {
            "source_status": "no_matching_row",
            "clicks": None,
            "impressions": None,
            "ctr_pct": None,
            "position": None,
            "ranking_query_count": None,
            "top_query": None,
            "matched_page": None,
            "matched_variant": None,
            "raw_probe": probes,
            "query_rows": [],
        }
    row = page_rows[0]
    query_response = gsc_query(
        service,
        start_date,
        end_date,
        ["query"],
        page_url=selected_variant,
        row_limit=gsc.GSC_MAX_WORKFLOW_ROWS, mode=gsc.GscQueryMode.COMPLETE,
    )
    query_rows = []
    for query_row in query_response.get("rows") or []:
        query_rows.append(
            {
                "query": (query_row.get("keys") or [""])[0],
                "clicks": float(query_row.get("clicks", 0)),
                "impressions": float(query_row.get("impressions", 0)),
                "ctr_pct": float(query_row.get("ctr", 0)) * 100,
                "position": float(query_row.get("position", 0)),
            }
        )
    top_query = None
    if query_rows:
        top_query = max(query_rows, key=lambda item: item["impressions"])["query"]
    return {
        "source_status": "matched",
        "clicks": float(row.get("clicks", 0)),
        "impressions": float(row.get("impressions", 0)),
        "ctr_pct": float(row.get("ctr", 0)) * 100,
        "position": float(row.get("position", 0)),
        "ranking_query_count": len(query_rows),
        "top_query": top_query,
        "matched_page": (row.get("keys") or [selected_variant])[0],
        "matched_variant": selected_variant,
        "raw_probe": probes,
        "query_rows": query_rows,
    }


def exact_filter(field_name: str, value: str) -> dict[str, Any]:
    return {
        "filter": {
            "field_name": field_name,
            "string_filter": {
                "match_type": "EXACT",
                "value": value,
                "case_sensitive": False,
            },
        }
    }


def ga4_page_filter(url: str) -> dict[str, Any]:
    return {
        "and_group": {
            "expressions": [
                exact_filter("hostName", GA4_HOST),
                {
                    "or_group": {
                        "expressions": [
                            exact_filter("pagePath", path)
                            for path in page_path_variants(url)
                        ]
                    }
                },
            ]
        }
    }


def ga4_rows(response: dict[str, Any]) -> list[dict[str, Any]]:
    dimension_headers = [
        item.get("name", "")
        for item in response.get("dimensionHeaders", response.get("dimension_headers", []))
    ]
    metric_headers = [
        item.get("name", "")
        for item in response.get("metricHeaders", response.get("metric_headers", []))
    ]
    rows = []
    for row in response.get("rows", []) or []:
        result: dict[str, Any] = {}
        dimension_values = row.get("dimensionValues", row.get("dimension_values", []))
        metric_values = row.get("metricValues", row.get("metric_values", []))
        for name, value in zip(dimension_headers, dimension_values):
            result[name] = value.get("value")
        for name, value in zip(metric_headers, metric_values):
            raw_value = value.get("value")
            try:
                result[name] = float(raw_value)
            except (TypeError, ValueError):
                result[name] = raw_value
        rows.append(result)
    return rows


async def ga4_report(
    start_date: str,
    end_date: str,
    dimensions: list[str],
    metrics: list[str],
    dimension_filter: dict[str, Any],
    limit: int = 1000,
) -> dict[str, Any]:
    from analytics_mcp.tools.reporting.core import run_report

    return await run_report(
        property_id=GA4_PROPERTY,
        date_ranges=[{"start_date": start_date, "end_date": end_date}],
        dimensions=dimensions,
        metrics=metrics,
        dimension_filter=dimension_filter,
        limit=limit,
    )


async def pull_ga4_period(url: str, start_date: str, end_date: str) -> dict[str, Any]:
    dimension_filter = ga4_page_filter(url)
    aggregate_response, channel_response, event_response = await asyncio.gather(
        ga4_report(
            start_date,
            end_date,
            ["hostName", "pagePath"],
            [
                "sessions",
                "activeUsers",
                "screenPageViews",
                "engagedSessions",
                "engagementRate",
                "bounceRate",
                "userEngagementDuration",
                "keyEvents",
                "eventCount",
            ],
            dimension_filter,
        ),
        ga4_report(
            start_date,
            end_date,
            ["hostName", "pagePath", "sessionPrimaryChannelGroup"],
            ["sessions"],
            dimension_filter,
        ),
        ga4_report(
            start_date,
            end_date,
            ["hostName", "pagePath", "eventName"],
            ["eventCount", "keyEvents"],
            dimension_filter,
            limit=10_000,
        ),
    )
    aggregate_rows = ga4_rows(aggregate_response)
    channel_rows = ga4_rows(channel_response)
    event_rows = ga4_rows(event_response)
    if not aggregate_rows:
        return {
            "source_status": "no_matching_row",
            "sessions": None,
            "organic_sessions": None,
            "ai_assistants_sessions": None,
            "users": None,
            "views": None,
            "engagement_rate_pct": None,
            "bounce_rate_pct": None,
            "average_engagement_time_per_session_sec": None,
            "key_events": None,
            "event_count": None,
            "views_per_session": None,
            "matched_page_paths": None,
            "channel_rows": [],
            "event_rows": [],
            "metadata": {},
        }
    totals = {
        key: sum(float(row.get(key) or 0) for row in aggregate_rows)
        for key in (
            "sessions",
            "activeUsers",
            "screenPageViews",
            "engagedSessions",
            "userEngagementDuration",
            "keyEvents",
            "eventCount",
        )
    }
    sessions = totals["sessions"]
    engaged_sessions = totals["engagedSessions"]
    organic_sessions = sum(
        float(row.get("sessions") or 0)
        for row in channel_rows
        if row.get("sessionPrimaryChannelGroup") == "Organic Search"
    )
    ai_sessions = sum(
        float(row.get("sessions") or 0)
        for row in channel_rows
        if row.get("sessionPrimaryChannelGroup") == "AI Assistants"
    )
    return {
        "source_status": "matched",
        "sessions": sessions,
        "organic_sessions": organic_sessions,
        "ai_assistants_sessions": ai_sessions,
        "users": totals["activeUsers"],
        "views": totals["screenPageViews"],
        "engagement_rate_pct": (engaged_sessions / sessions * 100) if sessions else 0,
        "bounce_rate_pct": ((sessions - engaged_sessions) / sessions * 100) if sessions else 0,
        "average_engagement_time_per_session_sec": (
            totals["userEngagementDuration"] / sessions if sessions else 0
        ),
        "key_events": totals["keyEvents"],
        "event_count": totals["eventCount"],
        "views_per_session": totals["screenPageViews"] / sessions if sessions else 0,
        "matched_page_paths": ";".join(
            sorted({str(row.get("pagePath")) for row in aggregate_rows})
        ),
        "channel_rows": channel_rows,
        "event_rows": sorted(
            event_rows,
            key=lambda item: float(item.get("eventCount") or 0),
            reverse=True,
        ),
        "metadata": {
            "currency_code": aggregate_response.get("metadata", {}).get(
                "currencyCode",
                aggregate_response.get("metadata", {}).get("currency_code"),
            ),
            "time_zone": aggregate_response.get("metadata", {}).get(
                "timeZone",
                aggregate_response.get("metadata", {}).get("time_zone"),
            ),
            "row_count": len(aggregate_rows),
        },
    }


def peec_rows(payload: dict[str, Any]) -> list[dict[str, Any]]:
    columns = payload.get("columns") or []
    results = []
    for row in payload.get("rows") or []:
        values = row.get("value") if isinstance(row, dict) else row
        if isinstance(values, list):
            results.append(dict(zip(columns, values)))
        elif isinstance(row, dict):
            results.append(dict(row))
    return results


async def peec_call(session, tool: str, arguments: dict[str, Any]) -> dict[str, Any]:
    from automation.peec_mcp_collector import parse_tool_result

    result = await session.call_tool(tool, arguments)
    return parse_tool_result(result, tool=tool)


async def pull_peec_period(session, url: str, start_date: str, end_date: str) -> dict[str, Any]:
    context = (
        "Measure exact Simpro blog URL retrievals and citations for the corrected "
        "live blog performance comparison."
    )
    normalized_rows = []
    payloads = []
    raw_row_count = 0
    columns: list[str] = []
    for channel_id, channel_name in PEEC_CHANNELS.items():
        arguments = {
            "project_id": PEEC_PROJECT,
            "start_date": start_date,
            "end_date": end_date,
            "limit": 1000,
            "offset": 0,
            "filters": [
                {"field": "url", "operator": "in", "values": url_variants(url)},
                {"field": "model_channel_id", "operator": "in", "values": [channel_id]},
            ],
            "context": context,
        }
        payload = await peec_call(session, "get_url_report", arguments)
        payloads.append({"channel_id": channel_id, "arguments": arguments, "payload": payload})
        columns = columns or payload.get("columns") or []
        channel_matches = [
            row
            for row in peec_rows(payload)
            if normalize_peec_url(str(row.get("url") or "")) == normalize_peec_url(url)
        ]
        raw_row_count += len(channel_matches)
        retrievals = sum(float(row.get("retrieval_count") or 0) for row in channel_matches)
        citations = sum(float(row.get("citation_count") or 0) for row in channel_matches)
        normalized_rows.append(
            {
                "channel_id": channel_id,
                "channel_name": channel_name,
                "retrieval_count": retrievals,
                "citation_count": citations,
                "citation_rate": citations / retrievals if retrievals else 0,
                "url": url,
                "source_status": (
                    "matched"
                    if channel_matches
                    else "no_matching_row_zero_filled"
                ),
            }
        )
    return {
        "source_status": "matched" if raw_row_count else "no_matching_row_zero_filled",
        "rows": normalized_rows,
        "row_count": raw_row_count,
        "columns": columns,
        "channel_payloads": payloads,
    }


async def probe_sources(output_path: Path) -> None:
    from automation.peec_mcp_collector import peec_mcp_session

    load_dotenv(MARKETINGSKILLS / ".env")
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = str(ADC_PATH)
    token = os.environ.get("PEEC_MCP_PAT", "")
    if not token:
        raise RuntimeError("PEEC_MCP_PAT is unavailable")
    gsc_service = create_gsc_service()
    probes = []
    async with peec_mcp_session("https://api.peec.ai/mcp", token) as peec_session:
        for offset in range(0, 15):
            candidate = date(2026, 9, 2) - timedelta(days=offset)
            candidate_text = candidate.isoformat()
            gsc_response = gsc_query(
                gsc_service,
                candidate_text,
                candidate_text,
                ["page"],
                row_limit=1, mode=gsc.GscQueryMode.TOP_N,
            )
            gsc_available = bool(gsc_response.get("rows"))
            ga4_response = await ga4_report(
                candidate_text,
                candidate_text,
                ["pagePath"],
                ["sessions"],
                {
                    "filter": {
                        "field_name": "pagePath",
                        "string_filter": {
                            "match_type": "BEGINS_WITH",
                            "value": "/blog/",
                            "case_sensitive": False,
                        },
                    }
                },
                limit=1,
            )
            ga4_available = bool(ga4_response.get("rows"))
            peec_payload = await peec_call(
                peec_session,
                "get_url_report",
                {
                    "project_id": PEEC_PROJECT,
                    "start_date": candidate_text,
                    "end_date": candidate_text,
                    "limit": 1,
                    "offset": 0,
                    "context": (
                        "Confirm Peec reporting availability for the corrected live blog "
                        "performance comparison."
                    ),
                },
            )
            peec_available = bool(peec_rows(peec_payload))
            probe = {
                "date": candidate_text,
                "gsc_available": gsc_available,
                "gsc_row_count": len(gsc_response.get("rows") or []),
                "ga4_available": ga4_available,
                "ga4_row_count": len(ga4_response.get("rows") or []),
                "peec_available": peec_available,
                "peec_row_count": len(peec_rows(peec_payload)),
            }
            probes.append(probe)
            if gsc_available and ga4_available and peec_available:
                write_json(
                    output_path,
                    {
                        "probe_started_from": "2026-09-02",
                        "selected_latest_common_end": candidate_text,
                        "probes": probes,
                    },
                )
                return
    raise RuntimeError("No common final date found in the 15-day probe window")


async def pull_sources(windows_path: Path, output_dir: Path) -> None:
    from automation.peec_mcp_collector import peec_mcp_session

    load_dotenv(MARKETINGSKILLS / ".env")
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = str(ADC_PATH)
    token = os.environ.get("PEEC_MCP_PAT", "")
    if not token:
        raise RuntimeError("PEEC_MCP_PAT is unavailable")
    windows = read_json(windows_path)
    gsc_service = create_gsc_service()
    gsc_output: dict[str, Any] = {}
    ga4_output: dict[str, Any] = {}
    peec_output: dict[str, Any] = {}
    ledger = []
    async with peec_mcp_session("https://api.peec.ai/mcp", token) as peec_session:
        for item in windows:
            slug = item["slug"]
            url = item["final_url"]
            for period in ("current", "prior"):
                start_date = item[f"{period}_start"]
                end_date = item[f"{period}_end"]
                key = f"{slug}::{period}"
                gsc_output[key] = pull_gsc_period(
                    gsc_service, url, start_date, end_date
                )
                ga4_output[key] = await pull_ga4_period(
                    url, start_date, end_date
                )
                peec_output[key] = await pull_peec_period(
                    peec_session, url, start_date, end_date
                )
                ledger.append(
                    {
                        "key": key,
                        "url": url,
                        "period": period,
                        "start_date": start_date,
                        "end_date": end_date,
                        "gsc_status": gsc_output[key]["source_status"],
                        "ga4_status": ga4_output[key]["source_status"],
                        "peec_status": peec_output[key]["source_status"],
                    }
                )
    output_dir.mkdir(parents=True, exist_ok=True)
    write_json(output_dir / "gsc.json", gsc_output)
    write_json(output_dir / "ga4.json", ga4_output)
    write_json(output_dir / "peec.json", peec_output)
    write_json(output_dir / "source-pull-ledger.json", ledger)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)
    probe = subparsers.add_parser("probe")
    probe.add_argument("--output", required=True, type=Path)
    pull = subparsers.add_parser("pull")
    pull.add_argument("--windows", required=True, type=Path)
    pull.add_argument("--output-dir", required=True, type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    sys.path.insert(0, str(MARKETINGSKILLS))
    if args.command == "probe":
        asyncio.run(probe_sources(args.output))
    else:
        asyncio.run(pull_sources(args.windows, args.output_dir))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
