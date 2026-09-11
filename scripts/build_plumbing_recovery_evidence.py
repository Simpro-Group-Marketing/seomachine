#!/usr/bin/env python3
"""Build source-bound evidence for the plumbing software SERP recovery."""

from __future__ import annotations

import argparse
import asyncio
import csv
import hashlib
import json
import os
import re
import sys
from collections import defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
from data_sources.modules import gsc  # noqa: E402 - script path bootstrap

SOURCE_DIR = REPO / "research" / "live-blog-performance-corrected-2026-09-03"
OUTPUT_DIR = REPO / "research" / "best-plumbing-job-management-software-remediation-2026-09-03"
SLUG = "best-plumbing-job-management-software"
URL = f"https://www.simprogroup.com/blog/{SLUG}"
PAGE_PATHS = [f"/blog/{SLUG}", f"/blog/{SLUG}/"]
GSC_SITE = "sc-domain:simprogroup.com"
GA4_PROPERTY = "properties/309907809"
GA4_HOST = "www.simprogroup.com"
DEPLOYMENT_DATE = date(2026, 7, 16)
PRIOR_START = date(2026, 5, 29)
PRIOR_END = date(2026, 7, 15)
CURRENT_START = date(2026, 7, 16)
CURRENT_END = date(2026, 9, 1)
WINDOWS = {
    "prior": (PRIOR_START, PRIOR_END),
    "current": (CURRENT_START, CURRENT_END),
}
GSC_TOKEN = Path(
    r"C:\Users\patrick.grueschow\Desktop\Repos\seo-command-centerV3-main\mcp-gsc\token.json"
)
GA4_ADC = Path(
    r"C:\Users\patrick.grueschow\Desktop\Repos\marketingskills-main\credentials\adc.json"
)


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=True, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_float(value: Any) -> float | None:
    if value in (None, ""):
        return None
    return float(value)


def pct_delta(current: float | None, prior: float | None) -> float | None:
    if current is None or prior in (None, 0):
        return None
    return (current - prior) / prior * 100


def verify_baseline() -> dict[str, Any]:
    strict_path = SOURCE_DIR / "strict-url-performance-comparison.csv"
    rows = [row for row in read_csv(strict_path) if row.get("slug") == SLUG]
    if len(rows) != 1:
        raise RuntimeError(f"Expected one strict baseline row for {SLUG}; found {len(rows)}")
    row = rows[0]
    expected = {
        "deployment_date": DEPLOYMENT_DATE.isoformat(),
        "prior_start": PRIOR_START.isoformat(),
        "prior_end": PRIOR_END.isoformat(),
        "current_start": CURRENT_START.isoformat(),
        "current_end": CURRENT_END.isoformat(),
    }
    mismatches = {
        field: {"expected": value, "actual": row.get(field)}
        for field, value in expected.items()
        if row.get(field) != value
    }
    if mismatches:
        raise RuntimeError(f"Strict baseline date mismatch: {mismatches}")
    source_files = [
        strict_path,
        SOURCE_DIR / "raw" / "sources" / "gsc.json",
        SOURCE_DIR / "raw" / "sources" / "ga4.json",
        SOURCE_DIR / "raw" / "sources" / "peec.json",
        SOURCE_DIR / "raw" / "live-playwright-evidence.json",
        SOURCE_DIR / "deployment-date-evidence.csv",
        SOURCE_DIR / "live-content-match-evidence.csv",
        SOURCE_DIR / "source-manifest.json",
    ]
    snapshot = {
        "schema": "simpro-plumbing-serp-recovery-baseline/v1",
        "created_at": datetime.now().astimezone().isoformat(),
        "target_url": URL,
        "deployment_boundary": {
            "date": DEPLOYMENT_DATE.isoformat(),
            "source": "All SEO Published Completed At",
            "source_row": 59,
            "date_role": "verified operational deployment boundary, not a public publication claim",
        },
        "comparison_windows": {
            name: {
                "start": start.isoformat(),
                "end": end.isoformat(),
                "inclusive_days": (end - start).days + 1,
            }
            for name, (start, end) in WINDOWS.items()
        },
        "strict_row": row,
        "source_files": [
            {
                "path": str(path.relative_to(REPO)).replace("\\", "/"),
                "sha256": sha256_file(path),
                "bytes": path.stat().st_size,
            }
            for path in source_files
        ],
        "immutability_rule": "The listed corrected-audit files are inputs only and were not modified by this recovery run.",
    }
    write_json(OUTPUT_DIR / "pre-remediation-baseline.json", snapshot)
    return snapshot


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
        raise RuntimeError("GSC OAuth credentials are invalid")
    return build("searchconsole", "v1", credentials=credentials, cache_discovery=False)


def gsc_query(
    service, start: date, end: date, dimensions: list[str], *,
    row_limit: int = gsc.GSC_MAX_WORKFLOW_ROWS,
) -> dict[str, Any]:
    body = {
        "startDate": start.isoformat(),
        "endDate": end.isoformat(),
        "dimensions": dimensions,
        "type": "web",
        "dataState": "final",
        "dimensionFilterGroups": [
            {
                "groupType": "and",
                "filters": [
                    {
                        "dimension": "page",
                        "operator": "equals",
                        "expression": URL,
                    }
                ],
            }
        ],
    }
    return gsc.query_search_analytics(
        service, site_url=GSC_SITE, body=body, max_rows=row_limit,
        mode=gsc.GscQueryMode.COMPLETE)


def normalize_gsc_date(value: str) -> str:
    if re.fullmatch(r"\d{8}", value):
        return f"{value[:4]}-{value[4:6]}-{value[6:]}"
    return value


def pull_gsc_daily() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    service = create_gsc_service()
    response = gsc_query(service, PRIOR_START, CURRENT_END, ["date"])
    by_date = {}
    for row in response.get("rows") or []:
        day = normalize_gsc_date(str((row.get("keys") or [""])[0]))
        by_date[day] = row
    output = []
    cursor = PRIOR_START
    while cursor <= CURRENT_END:
        day = cursor.isoformat()
        source = by_date.get(day)
        period = "prior" if cursor <= PRIOR_END else "current"
        output.append(
            {
                "date": day,
                "period": period,
                "window_day": (cursor - WINDOWS[period][0]).days + 1,
                "clicks": float(source.get("clicks", 0)) if source else "",
                "impressions": float(source.get("impressions", 0)) if source else "",
                "ctr_pct": float(source.get("ctr", 0)) * 100 if source else "",
                "average_position": float(source.get("position", 0)) if source else "",
                "source_status": "matched" if source else "no_matching_row",
            }
        )
        cursor += timedelta(days=1)
    raw = {
        "arguments": {
            "site_url": GSC_SITE,
            "start_date": PRIOR_START.isoformat(),
            "end_date": CURRENT_END.isoformat(),
            "dimensions": ["date"],
            "type": "web",
            "data_state": "final",
            "page_filter": URL,
        },
        "response": response,
    }
    write_json(OUTPUT_DIR / "raw" / "gsc-daily.json", raw)
    write_csv(
        OUTPUT_DIR / "gsc-daily-trend.csv",
        output,
        [
            "date",
            "period",
            "window_day",
            "clicks",
            "impressions",
            "ctr_pct",
            "average_position",
            "source_status",
        ],
    )
    return output, raw


CLUSTER_RULES = [
    (
        "exact_job_management",
        re.compile(
            r"\bjob\s+management(?:\s+(?:software|system|app))?\b|"
            r"\bplumb(?:er|ers|ing)?\s+job\s+(?:management|software)\b|"
            r"\bjob\s+software\s+for\s+plumb",
            re.I,
        ),
    ),
    ("scheduling", re.compile(r"\bschedul|\bdispatch|\brout(?:e|ing)|\bbooking", re.I)),
    (
        "maintenance",
        re.compile(r"\bmaintenan|\bservice agreement|\brecurring|\basset", re.I),
    ),
    ("project", re.compile(r"\bproject|\bconstruction|\bprogress billing", re.I)),
    (
        "small_business",
        re.compile(r"\bsmall business|\bsmall plumbing|\bsmall team|\bsolo|\bone[- ]person", re.I),
    ),
    ("commercial", re.compile(r"\bcommercial|\blarge crew|\benterprise", re.I)),
    (
        "comparison",
        re.compile(r"\bbest\b|\btop\b|\bcompar|\bversus\b|\bvs\.?\b|\balternative", re.I),
    ),
    (
        "broad_software",
        re.compile(r"\bplumb(?:er|ers|ing)?\b.*\bsoftware\b|\bsoftware\b.*\bplumb", re.I),
    ),
]


def classify_query(query: str) -> tuple[str, list[str]]:
    matches = [name for name, pattern in CLUSTER_RULES if pattern.search(query)]
    return (matches[0] if matches else "other", matches)


def query_map(rows: list[dict[str, Any]]) -> dict[str, dict[str, float]]:
    return {str(row.get("query") or ""): row for row in rows if row.get("query")}


def weighted_position(rows: list[dict[str, Any]], period: str) -> float | None:
    numerator = 0.0
    denominator = 0.0
    for row in rows:
        impressions = parse_float(row.get(f"impressions_{period}"))
        position = parse_float(row.get(f"position_{period}"))
        if impressions is None or position is None:
            continue
        numerator += position * impressions
        denominator += impressions
    return numerator / denominator if denominator else None


def build_query_clusters() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    raw = read_json(SOURCE_DIR / "raw" / "sources" / "gsc.json")
    prior_rows = raw[f"{SLUG}::prior"].get("query_rows") or []
    current_rows = raw[f"{SLUG}::current"].get("query_rows") or []
    prior = query_map(prior_rows)
    current = query_map(current_rows)
    detail = []
    for query in sorted(set(prior) | set(current)):
        prior_row = prior.get(query, {})
        current_row = current.get(query, {})
        primary, all_matches = classify_query(query)
        p_imp = parse_float(prior_row.get("impressions"))
        c_imp = parse_float(current_row.get("impressions"))
        p_clicks = parse_float(prior_row.get("clicks"))
        c_clicks = parse_float(current_row.get("clicks"))
        p_pos = parse_float(prior_row.get("position"))
        c_pos = parse_float(current_row.get("position"))
        detail.append(
            {
                "query": query,
                "primary_cluster": primary,
                "all_matching_clusters": ";".join(all_matches),
                "clicks_prior": p_clicks if p_clicks is not None else "",
                "clicks_current": c_clicks if c_clicks is not None else "",
                "clicks_delta": (c_clicks or 0) - (p_clicks or 0),
                "impressions_prior": p_imp if p_imp is not None else "",
                "impressions_current": c_imp if c_imp is not None else "",
                "impressions_delta": (c_imp or 0) - (p_imp or 0),
                "position_prior": p_pos if p_pos is not None else "",
                "position_current": c_pos if c_pos is not None else "",
                "position_delta": c_pos - p_pos if c_pos is not None and p_pos is not None else "",
                "ctr_pct_prior": prior_row.get("ctr_pct", ""),
                "ctr_pct_current": current_row.get("ctr_pct", ""),
                "source_status_prior": "matched" if query in prior else "no_matching_row",
                "source_status_current": "matched" if query in current else "no_matching_row",
            }
        )
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in detail:
        grouped[row["primary_cluster"]].append(row)
    summary = []
    ordered_clusters = [name for name, _ in CLUSTER_RULES] + ["other"]
    for cluster in ordered_clusters:
        rows = grouped.get(cluster, [])
        p_clicks = sum(parse_float(row.get("clicks_prior")) or 0 for row in rows)
        c_clicks = sum(parse_float(row.get("clicks_current")) or 0 for row in rows)
        p_imp = sum(parse_float(row.get("impressions_prior")) or 0 for row in rows)
        c_imp = sum(parse_float(row.get("impressions_current")) or 0 for row in rows)
        summary.append(
            {
                "cluster": cluster,
                "visible_queries_prior": sum(row["source_status_prior"] == "matched" for row in rows),
                "visible_queries_current": sum(row["source_status_current"] == "matched" for row in rows),
                "clicks_prior": p_clicks,
                "clicks_current": c_clicks,
                "clicks_delta": c_clicks - p_clicks,
                "clicks_pct_delta": pct_delta(c_clicks, p_clicks),
                "impressions_prior": p_imp,
                "impressions_current": c_imp,
                "impressions_delta": c_imp - p_imp,
                "impressions_pct_delta": pct_delta(c_imp, p_imp),
                "weighted_position_prior": weighted_position(rows, "prior"),
                "weighted_position_current": weighted_position(rows, "current"),
                "position_delta": (
                    weighted_position(rows, "current") - weighted_position(rows, "prior")
                    if weighted_position(rows, "current") is not None
                    and weighted_position(rows, "prior") is not None
                    else None
                ),
                "classification_note": "Mutually exclusive primary cluster; all rule matches remain in query detail.",
            }
        )
    write_csv(
        OUTPUT_DIR / "gsc-query-cluster-detail.csv",
        detail,
        list(detail[0].keys()),
    )
    write_csv(
        OUTPUT_DIR / "gsc-query-cluster-summary.csv",
        summary,
        list(summary[0].keys()),
    )
    return detail, summary


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


def ga4_page_filter() -> dict[str, Any]:
    return {
        "and_group": {
            "expressions": [
                exact_filter("hostName", GA4_HOST),
                {
                    "or_group": {
                        "expressions": [exact_filter("pagePath", path) for path in PAGE_PATHS]
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
    output = []
    for row in response.get("rows") or []:
        item: dict[str, Any] = {}
        dimensions = row.get("dimensionValues", row.get("dimension_values", []))
        metrics = row.get("metricValues", row.get("metric_values", []))
        for name, value in zip(dimension_headers, dimensions):
            item[name] = value.get("value")
        for name, value in zip(metric_headers, metrics):
            raw_value = value.get("value")
            try:
                item[name] = float(raw_value)
            except (TypeError, ValueError):
                item[name] = raw_value
        output.append(item)
    return output


async def ga4_report(
    start: date,
    end: date,
    dimensions: list[str],
    metrics: list[str],
    *,
    limit: int = 10_000,
) -> dict[str, Any]:
    from analytics_mcp.tools.reporting.core import run_report

    return await run_report(
        property_id=GA4_PROPERTY,
        date_ranges=[{"start_date": start.isoformat(), "end_date": end.isoformat()}],
        dimensions=dimensions,
        metrics=metrics,
        dimension_filter=ga4_page_filter(),
        limit=limit,
    )


SEGMENTS = {
    "channel": "sessionPrimaryChannelGroup",
    "source_medium": "sessionSourceMedium",
    "device": "deviceCategory",
    "country": "country",
    "new_returning": "newVsReturning",
}


def aggregate_ga4(rows: list[dict[str, Any]]) -> dict[str, float]:
    keys = [
        "sessions",
        "activeUsers",
        "screenPageViews",
        "engagedSessions",
        "userEngagementDuration",
        "keyEvents",
        "eventCount",
    ]
    return {key: sum(float(row.get(key) or 0) for row in rows) for key in keys}


async def pull_ga4_segments() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = str(GA4_ADC)
    metrics = [
        "sessions",
        "activeUsers",
        "screenPageViews",
        "engagedSessions",
        "engagementRate",
        "bounceRate",
        "userEngagementDuration",
        "keyEvents",
        "eventCount",
    ]
    output: list[dict[str, Any]] = []
    raw: dict[str, Any] = {
        "property": GA4_PROPERTY,
        "host": GA4_HOST,
        "page_paths": PAGE_PATHS,
        "periods": {},
    }
    for period, (start, end) in WINDOWS.items():
        period_raw: dict[str, Any] = {}
        total_response = await ga4_report(start, end, ["hostName", "pagePath"], metrics)
        total_rows = ga4_rows(total_response)
        total = aggregate_ga4(total_rows)
        event_response = await ga4_report(
            start,
            end,
            ["eventName"],
            ["eventCount"],
        )
        total_event_rows = ga4_rows(event_response)
        total_events = {str(row.get("eventName")): float(row.get("eventCount") or 0) for row in total_event_rows}
        sessions = total["sessions"]
        output.append(
            {
                "period": period,
                "start_date": start.isoformat(),
                "end_date": end.isoformat(),
                "segment_type": "all",
                "segment_value": "all",
                "sessions": sessions,
                "active_users": total["activeUsers"],
                "views": total["screenPageViews"],
                "engaged_sessions": total["engagedSessions"],
                "engagement_rate_pct": total["engagedSessions"] / sessions * 100 if sessions else 0,
                "bounce_rate_pct": (sessions - total["engagedSessions"]) / sessions * 100 if sessions else 0,
                "avg_engagement_time_per_session_sec": total["userEngagementDuration"] / sessions if sessions else 0,
                "key_events": total["keyEvents"],
                "event_count": total["eventCount"],
                "scroll_event_count": total_events.get("scroll", 0),
                "click_event_count": total_events.get("click", 0),
                "scroll_events_per_session": total_events.get("scroll", 0) / sessions if sessions else 0,
                "click_events_per_session": total_events.get("click", 0) / sessions if sessions else 0,
                "source_status": "matched" if total_rows else "no_matching_row",
            }
        )
        period_raw["all"] = {
            "arguments": {"dimensions": ["hostName", "pagePath"], "metrics": metrics},
            "response": total_response,
            "event_response": event_response,
        }
        for segment_type, dimension in SEGMENTS.items():
            try:
                segment_response, segment_event_response = await asyncio.gather(
                    ga4_report(start, end, [dimension], metrics),
                    ga4_report(start, end, [dimension, "eventName"], ["eventCount"]),
                )
                segment_rows = ga4_rows(segment_response)
                event_rows = ga4_rows(segment_event_response)
                event_map: dict[tuple[str, str], float] = defaultdict(float)
                for event_row in event_rows:
                    event_map[(str(event_row.get(dimension)), str(event_row.get("eventName")))] += float(
                        event_row.get("eventCount") or 0
                    )
                for segment_row in segment_rows:
                    value = str(segment_row.get(dimension) or "(not set)")
                    segment_sessions = float(segment_row.get("sessions") or 0)
                    engaged = float(segment_row.get("engagedSessions") or 0)
                    duration = float(segment_row.get("userEngagementDuration") or 0)
                    scroll_events = event_map[(value, "scroll")]
                    click_events = event_map[(value, "click")]
                    output.append(
                        {
                            "period": period,
                            "start_date": start.isoformat(),
                            "end_date": end.isoformat(),
                            "segment_type": segment_type,
                            "segment_value": value,
                            "sessions": segment_sessions,
                            "active_users": float(segment_row.get("activeUsers") or 0),
                            "views": float(segment_row.get("screenPageViews") or 0),
                            "engaged_sessions": engaged,
                            "engagement_rate_pct": engaged / segment_sessions * 100 if segment_sessions else 0,
                            "bounce_rate_pct": (segment_sessions - engaged) / segment_sessions * 100 if segment_sessions else 0,
                            "avg_engagement_time_per_session_sec": duration / segment_sessions if segment_sessions else 0,
                            "key_events": float(segment_row.get("keyEvents") or 0),
                            "event_count": float(segment_row.get("eventCount") or 0),
                            "scroll_event_count": scroll_events,
                            "click_event_count": click_events,
                            "scroll_events_per_session": scroll_events / segment_sessions if segment_sessions else 0,
                            "click_events_per_session": click_events / segment_sessions if segment_sessions else 0,
                            "source_status": "matched",
                        }
                    )
                period_raw[segment_type] = {
                    "arguments": {"dimensions": [dimension], "metrics": metrics},
                    "response": segment_response,
                    "event_arguments": {"dimensions": [dimension, "eventName"], "metrics": ["eventCount"]},
                    "event_response": segment_event_response,
                }
            except Exception as exc:
                output.append(
                    {
                        "period": period,
                        "start_date": start.isoformat(),
                        "end_date": end.isoformat(),
                        "segment_type": segment_type,
                        "segment_value": "",
                        "source_status": "source_error",
                        "source_error": f"{type(exc).__name__}: {exc}",
                    }
                )
                period_raw[segment_type] = {
                    "arguments": {"dimensions": [dimension], "metrics": metrics},
                    "source_status": "source_error",
                    "error": f"{type(exc).__name__}: {exc}",
                }
        raw["periods"][period] = period_raw
    fields = [
        "period",
        "start_date",
        "end_date",
        "segment_type",
        "segment_value",
        "sessions",
        "active_users",
        "views",
        "engaged_sessions",
        "engagement_rate_pct",
        "bounce_rate_pct",
        "avg_engagement_time_per_session_sec",
        "key_events",
        "event_count",
        "scroll_event_count",
        "click_event_count",
        "scroll_events_per_session",
        "click_events_per_session",
        "source_status",
        "source_error",
    ]
    write_csv(OUTPUT_DIR / "ga4-engagement-segments.csv", output, fields)
    write_json(OUTPUT_DIR / "raw" / "ga4-segments.json", raw)
    return output, raw


def build_peec_baseline() -> list[dict[str, Any]]:
    raw = read_json(SOURCE_DIR / "raw" / "sources" / "peec.json")
    rows = []
    for period, (start, end) in WINDOWS.items():
        for source in raw[f"{SLUG}::{period}"].get("rows") or []:
            rows.append(
                {
                    "period": period,
                    "start_date": start.isoformat(),
                    "end_date": end.isoformat(),
                    "channel_id": source.get("channel_id"),
                    "channel_name": source.get("channel_name"),
                    "retrieval_count": source.get("retrieval_count"),
                    "citation_count": source.get("citation_count"),
                    "citation_rate": source.get("citation_rate"),
                    "source_status": source.get("source_status"),
                    "normalization": "Exact URL across www/non-www and trailing-slash variants; no-row is zero-filled only for Peec.",
                }
            )
    write_csv(OUTPUT_DIR / "peec-pre-remediation-baseline.csv", rows, list(rows[0].keys()))
    return rows


def build_trust_check(ga4_rows_output: list[dict[str, Any]], baseline: dict[str, Any]) -> None:
    strict = baseline["strict_row"]
    rows = []
    for period in ("prior", "current"):
        all_row = next(
            row
            for row in ga4_rows_output
            if row.get("period") == period and row.get("segment_type") == "all"
        )
        organic_row = next(
            (
                row
                for row in ga4_rows_output
                if row.get("period") == period
                and row.get("segment_type") == "channel"
                and row.get("segment_value") == "Organic Search"
            ),
            None,
        )
        gsc_clicks = float(strict[f"gsc_clicks_{period}"])
        organic_sessions = float(organic_row.get("sessions") or 0) if organic_row else None
        rows.append(
            {
                "period": period,
                "gsc_clicks": gsc_clicks,
                "ga4_organic_search_sessions": organic_sessions,
                "absolute_difference": organic_sessions - gsc_clicks if organic_sessions is not None else "",
                "ga4_all_sessions": all_row.get("sessions"),
                "interpretation": "Trust check only; GSC clicks and GA4 sessions have different measurement definitions and are not expected to equal.",
            }
        )
    write_csv(OUTPUT_DIR / "ga4-gsc-trust-check.csv", rows, list(rows[0].keys()))


def build_targets() -> None:
    targets = {
        "schema": "simpro-plumbing-serp-recovery-targets/v1",
        "measurement_start": "D, the actual CMS deployment date recorded after publication",
        "comparison": "D through D+47 versus the immediately preceding 48 days",
        "targets_are_guarantees": False,
        "targets": {
            "gsc_average_position_max": 34.9,
            "gsc_clicks_min": 22,
            "gsc_impressions_min": 19486,
            "ga4_organic_sessions_min": 24,
            "ga4_engagement_rate_pct_min": 47.4,
            "ga4_bounce_rate_pct_max": 52.6,
            "ga4_average_engagement_time_per_session_sec_min": 29.2,
        },
        "checkpoints_days": [7, 14, 28, 48],
        "peec_normalized_decline_alert_pct": -20,
        "source_lanes": {
            "Google Search performance": "GSC Web Search",
            "site traffic and engagement": "GA4",
            "AI retrievals and citations": "Peec",
            "Google generative-search visibility": "GSC Generative AI UI export",
        },
    }
    write_json(OUTPUT_DIR / "recovery-targets.json", targets)


async def main_async() -> int:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    baseline = verify_baseline()
    daily_rows, gsc_raw = pull_gsc_daily()
    query_detail, query_summary = build_query_clusters()
    ga4_output, ga4_raw = await pull_ga4_segments()
    peec_rows = build_peec_baseline()
    build_trust_check(ga4_output, baseline)
    build_targets()
    run_summary = {
        "schema": "simpro-plumbing-serp-recovery-evidence-run/v1",
        "created_at": datetime.now().astimezone().isoformat(),
        "target_url": URL,
        "baseline_hash": sha256_file(OUTPUT_DIR / "pre-remediation-baseline.json"),
        "artifacts": {
            "gsc_daily_rows": len(daily_rows),
            "gsc_daily_matched_rows": sum(row["source_status"] == "matched" for row in daily_rows),
            "gsc_query_detail_rows": len(query_detail),
            "gsc_query_cluster_rows": len(query_summary),
            "ga4_segment_rows": len(ga4_output),
            "ga4_source_error_rows": sum(row.get("source_status") == "source_error" for row in ga4_output),
            "peec_channel_period_rows": len(peec_rows),
        },
        "raw_response_hashes": {
            "gsc_daily": sha256_file(OUTPUT_DIR / "raw" / "gsc-daily.json"),
            "ga4_segments": sha256_file(OUTPUT_DIR / "raw" / "ga4-segments.json"),
        },
        "gsc_arguments": gsc_raw["arguments"],
        "ga4_property": ga4_raw["property"],
    }
    write_json(OUTPUT_DIR / "evidence-run-summary.json", run_summary)
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=OUTPUT_DIR,
        help="Recovery evidence output directory.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    global OUTPUT_DIR
    OUTPUT_DIR = args.output_dir.resolve()
    return asyncio.run(main_async())


if __name__ == "__main__":
    raise SystemExit(main())
