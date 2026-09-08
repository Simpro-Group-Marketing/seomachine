"""Build the evidence manifest for the plumbing SERP recovery package."""

from __future__ import annotations

import csv
import hashlib
import json
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
PACKAGE = REPO_ROOT / "research" / "best-plumbing-job-management-software-remediation-2026-09-03"
CORRECTED_AUDIT = REPO_ROOT / "research" / "live-blog-performance-corrected-2026-09-03"
ARTICLE = REPO_ROOT / "published" / "best-plumbing-job-management-software-rewrite-2026-09-03.md"
SIDECAR = REPO_ROOT / "research" / "validation-best-plumbing-job-management-software-2026-09-03.md"
OUTPUT = PACKAGE / "source-manifest.json"
TARGET_URL = "https://www.simprogroup.com/blog/best-plumbing-job-management-software"


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _file_record(path: Path) -> dict[str, Any]:
    return {
        "path": str(path.relative_to(REPO_ROOT)).replace("\\", "/"),
        "sha256": _sha256(path),
        "bytes": path.stat().st_size,
    }


def _csv_record(path: Path) -> dict[str, Any]:
    rows = _read_csv(path)
    status_counts = Counter()
    for row in rows:
        for key, value in row.items():
            if key.startswith("source_status") and value:
                status_counts[f"{key}:{value}"] += 1
    return {
        **_file_record(path),
        "row_count": len(rows),
        "source_status_counts": dict(sorted(status_counts.items())),
    }


def _package_inventory() -> list[dict[str, Any]]:
    return [
        _file_record(path)
        for path in sorted(PACKAGE.rglob("*"))
        if path.is_file() and path.resolve() != OUTPUT.resolve()
    ]


def main() -> int:
    baseline = _read_json(PACKAGE / "pre-remediation-baseline.json")
    evidence = _read_json(PACKAGE / "evidence-run-summary.json")
    corrected_manifest = _read_json(CORRECTED_AUDIT / "source-manifest.json")
    publication = _read_json(PACKAGE / "publication-date-evidence.json")
    serp = _read_json(PACKAGE / "raw" / "google-serp" / "google-serp-captures.json")
    live = _read_json(PACKAGE / "raw" / "live-page" / "live-page-captures.json")
    vendors = _read_json(
        PACKAGE / "raw" / "vendor-sources" / "official-vendor-page-captures.json"
    )
    paa = _read_json(PACKAGE / "answersocrates-source-evidence.json")
    context = _read_json(PACKAGE / "context-run-summary.json")
    quality = _read_json(PACKAGE / "quality-gate-report.json")
    readiness = _read_json(PACKAGE / "readiness-preflight.json")
    browser_render = _read_json(
        PACKAGE / "raw" / "replacement-render" / "browser-validation.json"
    )
    static_render = _read_json(
        PACKAGE / "raw" / "replacement-render" / "static-validation.json"
    )
    proof = _read_json(PACKAGE / "customer-proof-selector-evidence.json")
    peec_rows = _read_csv(PACKAGE / "peec-pre-remediation-baseline.csv")
    ga4_raw = _read_json(PACKAGE / "raw" / "ga4-segments.json")

    csv_files = [
        "gsc-daily-trend.csv",
        "gsc-query-cluster-detail.csv",
        "gsc-query-cluster-summary.csv",
        "ga4-engagement-segments.csv",
        "ga4-gsc-trust-check.csv",
        "peec-pre-remediation-baseline.csv",
        "google-serp-results.csv",
        "google-serp-features.csv",
        "vendor-source-evidence.csv",
        "answersocrates-paa-questions.csv",
    ]
    row_evidence = {
        name: _csv_record(PACKAGE / name)
        for name in csv_files
    }

    ga4_dimensions = set()
    ga4_metrics = set()
    for period in ga4_raw.get("periods", {}).values():
        for segment in period.values():
            arguments = segment.get("arguments", {})
            ga4_dimensions.update(arguments.get("dimensions", []))
            ga4_metrics.update(arguments.get("metrics", []))
            event_arguments = segment.get("event_arguments", {})
            ga4_dimensions.update(event_arguments.get("dimensions", []))
            ga4_metrics.update(event_arguments.get("metrics", []))

    serp_captures = serp.get("captures", [])
    live_captures = live.get("captures", [])
    vendor_captures = vendors.get("captures", [])
    peec_channels = {
        row["channel_id"]: row["channel_name"]
        for row in peec_rows
        if row.get("channel_id") and row.get("channel_name")
    }

    manifest = {
        "schema": "simpro-plumbing-serp-recovery-manifest/v1",
        "generated_at": datetime.now().astimezone().isoformat(),
        "target_url": TARGET_URL,
        "scope": {
            "action": "recover the existing canonical URL with a replacement article",
            "rollback": False,
            "new_url": False,
            "cms_deployment_performed": False,
            "postdeployment_validation_status": "pending",
        },
        "comparison_design": {
            "deployment_boundary": baseline["deployment_boundary"],
            "windows": baseline["comparison_windows"],
            "method": (
                "The 48 inclusive days beginning on the verified July 16, 2026 "
                "deployment boundary are compared with the immediately preceding 48 "
                "inclusive days. The boundary is operational Sheet evidence, not a "
                "public publication claim."
            ),
            "immutable_input_files": baseline["source_files"],
        },
        "source_lanes": {
            "gsc": {
                "claim_scope": "Google Web Search clicks, impressions, CTR, position, and visible query rows",
                "tool": "Google Search Console API using configured OAuth credentials",
                "site_url": "sc-domain:simprogroup.com",
                "search_type": "web",
                "data_state": "final",
                "page_filter": TARGET_URL,
                "date_range": {"start": "2026-05-29", "end": "2026-09-01"},
                "daily_dimensions": ["date"],
                "query_dimensions": ["query"],
                "row_limit": 25000,
                "raw_daily": _file_record(PACKAGE / "raw" / "gsc-daily.json"),
                "frozen_query_source": next(
                    item for item in baseline["source_files"] if item["path"].endswith("raw/sources/gsc.json")
                ),
                "derived_rows": {
                    "daily": evidence["artifacts"]["gsc_daily_rows"],
                    "daily_matched": evidence["artifacts"]["gsc_daily_matched_rows"],
                    "query_detail": evidence["artifacts"]["gsc_query_detail_rows"],
                    "query_clusters": evidence["artifacts"]["gsc_query_cluster_rows"],
                },
            },
            "ga4": {
                "claim_scope": "site sessions, users, views, engagement, bounce, time, key events, and event density",
                "tool": "official Google Analytics Data API through analytics_mcp reporting client",
                "property": ga4_raw["property"],
                "host_filter": ga4_raw["host"],
                "page_path_filters": ga4_raw["page_paths"],
                "filter_match": "case-insensitive exact",
                "segments": {
                    "channel": "sessionPrimaryChannelGroup",
                    "source_medium": "sessionSourceMedium",
                    "device": "deviceCategory",
                    "country": "country",
                    "new_returning": "newVsReturning",
                },
                "dimensions_used": sorted(ga4_dimensions),
                "metrics_used": sorted(ga4_metrics),
                "raw": _file_record(PACKAGE / "raw" / "ga4-segments.json"),
                "derived_rows": evidence["artifacts"]["ga4_segment_rows"],
                "source_error_rows": evidence["artifacts"]["ga4_source_error_rows"],
                "event_density_rule": "scroll and click event counts divided by sessions; not unique-user rates",
            },
            "peec": {
                "claim_scope": "monitored AI retrieval and citation activity only",
                "tool": corrected_manifest["source_tools"]["peec"]["tool"],
                "project_id": corrected_manifest["source_tools"]["peec"]["project_id"],
                "channels": dict(sorted(peec_channels.items())),
                "url_filter": corrected_manifest["source_tools"]["peec"]["url_filter"],
                "frozen_source": next(
                    item for item in baseline["source_files"] if item["path"].endswith("raw/sources/peec.json")
                ),
                "derived_rows": evidence["artifacts"]["peec_channel_period_rows"],
                "empty_row_rule": "0 retrievals and 0 citations with source_status recorded",
            },
            "publish_metadata": {
                "tool": corrected_manifest["source_tools"]["publish_metadata"]["tool"],
                "spreadsheet_id": corrected_manifest["source_tools"]["publish_metadata"]["spreadsheet_id"],
                "range": corrected_manifest["source_tools"]["publish_metadata"]["range"],
                "match": corrected_manifest["source_tools"]["publish_metadata"]["match"],
                "primary_field": corrected_manifest["source_tools"]["publish_metadata"]["primary_field"],
                "deployment_row": baseline["deployment_boundary"]["source_row"],
                "public_date_decision": publication["decision"],
                "evidence": _file_record(PACKAGE / "publication-date-evidence.json"),
            },
            "google_serp": {
                "claim_scope": "rendered US result order and visible SERP features at capture time",
                "tool": "Google Chrome through Playwright CLI",
                "captured_at": serp["captured_at"],
                "queries": [capture["query"] for capture in serp_captures],
                "market_parameters": serp["market_parameters"],
                "capture_count": len(serp_captures),
                "all_http_200": all(capture.get("http_status") == 200 for capture in serp_captures),
                "all_ai_overview_present": all(capture.get("ai_overview_present") for capture in serp_captures),
                "signed_in_states": [capture.get("signed_in_indicator") for capture in serp_captures],
                "authentication_requirement_status": "not_met_signed_out_capture",
                "authentication_note": (
                    "The persistent browser displayed Sign in for every capture. The evidence remains "
                    "a signed-out US sample and is not represented as an authenticated Google view."
                ),
                "raw": _file_record(PACKAGE / "raw" / "google-serp" / "google-serp-captures.json"),
            },
            "live_page": {
                "claim_scope": "current public HTTP, metadata, content, schema, and render defects",
                "tool": "Google Chrome through Playwright CLI",
                "captured_at": live["captured_at"],
                "viewports": [capture["viewport"] for capture in live_captures],
                "capture_count": len(live_captures),
                "all_http_200": all(capture.get("http_status") == 200 for capture in live_captures),
                "raw": _file_record(PACKAGE / "raw" / "live-page" / "live-page-captures.json"),
            },
            "vendor_pages": {
                "claim_scope": "official vendor positioning, workflow coverage, and public pricing route",
                "tool": "Google Chrome through Playwright CLI",
                "captured_at": vendors["captured_at"],
                "capture_count": len(vendor_captures),
                "http_status_counts": dict(
                    sorted(Counter(str(capture.get("http_status")) for capture in vendor_captures).items())
                ),
                "decision_counts": dict(
                    sorted(Counter(str(capture.get("decision")) for capture in vendor_captures).items())
                ),
                "raw": _file_record(
                    PACKAGE / "raw" / "vendor-sources" / "official-vendor-page-captures.json"
                ),
                "limitation": vendors["note"],
            },
            "answersocrates": {
                "claim_scope": "PAA question provenance",
                "query": paa["query"],
                "collection_date": paa["collection_date"],
                "runtime": paa["collection_runtime"],
                "source_export": paa["source_export"],
                "paa_question_count": paa["paa_question_count"],
                "artifact_receipt_hash": paa["artifact_receipt_hash"],
                "source_evidence": _file_record(PACKAGE / "answersocrates-source-evidence.json"),
            },
            "simpro_context": {
                "claim_scope": "brand voice, ICP, plumbing context, and competitive framing",
                "connector_sequence": [
                    "vault_status",
                    "vault_describe",
                    "vault_search",
                    "vault_read",
                    "vault_build_context",
                    "vault_validate_context",
                ],
                "selected_resource_ids": context["selected_resource_ids"],
                "revisions": context["revisions"],
                "validation": context["validation"],
                "context_pack": _file_record(PACKAGE / "context-pack.json"),
                "context_receipt": _file_record(PACKAGE / "context-receipt.json"),
            },
        },
        "normalization_rules": {
            "url": "lowercase scheme and host; strip query, fragment, and trailing slash; require canonical /blog/ URL",
            "gsc_ga4_no_matching_row": "preserve blanks in detailed source-bound outputs",
            "peec_no_matching_row": "record 0 retrievals and 0 citations with source_status",
            "query_clusters": "mutually exclusive first matching primary cluster; preserve all rule matches in detail",
            "position": "GSC impression-weighted position for cluster summaries",
            "ctr": "clicks divided by impressions; report percentage points for absolute change",
            "engagement": "GA4 source definitions; bounce rate is the complement of engagement rate",
            "comparison_dates": "inclusive day counts",
        },
        "row_evidence": row_evidence,
        "content_and_proof": {
            "article": _file_record(ARTICLE),
            "validation_sidecar": _file_record(SIDECAR),
            "customer_proof_selection": {
                "outcome": proof["selection_outcome"],
                "roles": [
                    {"role": row["role"], "selected_id": row["selected_id"], "outcome": row["selection_outcome"]}
                    for row in proof["roles"]
                ],
                "evidence": _file_record(PACKAGE / "customer-proof-selector-evidence.json"),
            },
            "fred_authority": {
                "selected": "none",
                "evidence": _file_record(PACKAGE / "fred-authority-selection.txt"),
            },
        },
        "replacement_validation": {
            "static_render": {
                "renderer": static_render["renderer"],
                "summary": static_render["summary"],
                "article_sha256": static_render["article_sha256"],
                "evidence": _file_record(
                    PACKAGE / "raw" / "replacement-render" / "static-validation.json"
                ),
            },
            "browser_render": {
                "playwright_cli_version": browser_render["playwright_cli_version"],
                "viewports": browser_render["viewports"],
                "summary": browser_render["summary"],
                "evidence": _file_record(
                    PACKAGE / "raw" / "replacement-render" / "browser-validation.json"
                ),
            },
            "quality_gates": {
                "summary": quality["summary"],
                "predeployment_status": quality["predeployment_status"],
                "evidence": _file_record(PACKAGE / "quality-gate-report.json"),
            },
            "publish_readiness_preflight": {
                "phase": readiness["phase"],
                "passed": readiness["passed"],
                "blockers": [
                    blocker
                    for gate in readiness.get("gates", [])
                    for blocker in gate.get("blockers", [])
                ],
                "evidence": _file_record(PACKAGE / "readiness-preflight.json"),
            },
        },
        "missing_or_blocked": [
            {
                "status": "cms_deployment_not_performed",
                "impact": "The live canonical still contains the pre-remediation article.",
            },
            {
                "status": "date_modified_unavailable",
                "impact": "No actual remediation date exists; dateModified is intentionally omitted.",
            },
            {
                "status": "postdeployment_live_validation_pending",
                "impact": "Live canonical, indexability, render, leakage, author, FAQ, and date checks must be rerun after deployment.",
            },
            {
                "status": "authenticated_google_serp_capture_unavailable",
                "impact": "SERP evidence is signed out and must not be described as an authenticated account view.",
            },
        ],
        "limitations": [
            "GSC query rows do not attribute zero-click behavior to AI Overviews, featured snippets, or another SERP feature.",
            "GA4 engagement changes do not establish that copy or publishing defects caused user behavior.",
            "The current Organic Search engagement sample contains only 10 sessions.",
            "Peec proves monitored retrieval and citation activity, not site traffic, leads, revenue, or conversion paths.",
            "The before-and-after design is observational and does not isolate algorithm, SERP, seasonality, channel-mix, or content effects.",
            "The original public date has no immutable archive snapshot; its evidence and limitation are preserved in publication-date-evidence.json.",
            "The local preview validates the replacement artifact, not CMS-specific rendering after deployment.",
        ],
        "artifact_inventory": _package_inventory(),
    }
    OUTPUT.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=True, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(
        json.dumps(
            {
                "manifest": str(OUTPUT),
                "artifact_count": len(manifest["artifact_inventory"]),
                "csv_row_counts": {
                    name: record["row_count"] for name, record in row_evidence.items()
                },
                "cms_deployment_performed": manifest["scope"]["cms_deployment_performed"],
                "serp_authentication_status": manifest["source_lanes"]["google_serp"]["authentication_requirement_status"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
