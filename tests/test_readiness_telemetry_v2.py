from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor

from data_sources.modules.readiness.telemetry import ReadinessTelemetry


def test_telemetry_v2_updates_counters_safely_from_worker_threads() -> None:
    telemetry = ReadinessTelemetry(run_id="run-threaded", phase="preflight")

    def record_requests() -> None:
        for _ in range(1_000):
            telemetry.increment("http_requests")

    with telemetry.stage("gate.url_validator"):
        with ThreadPoolExecutor(max_workers=8) as executor:
            list(executor.map(lambda _: record_requests(), range(8)))

    telemetry.finish("passed")
    payload = telemetry.to_dict()

    assert payload["schema"] == "simpro-readiness-telemetry/v3"
    assert payload["counters"]["http_requests"] == 8_000
    assert payload["stages"][0]["counters"]["http_requests"] == 8_000


def test_telemetry_v2_tracks_current_and_peak_content_free_gauges() -> None:
    telemetry = ReadinessTelemetry(run_id="run-gauges", phase="final")

    telemetry.set_gauge("current_http_requests", 3)
    telemetry.observe_peak("peak_http_requests", 3)
    telemetry.set_gauge("current_http_requests", 1)
    telemetry.observe_peak("peak_http_requests", 1)
    telemetry.set_gauge("artifact_store_source_bytes", 1_024)
    telemetry.finish("passed")

    payload = telemetry.to_dict()
    assert payload["gauges"]["current_http_requests"] == 1
    assert payload["gauges"]["peak_http_requests"] == 3
    assert payload["gauges"]["artifact_store_source_bytes"] == 1_024
    assert "article" not in json.dumps(payload)


def test_telemetry_v2_accepts_all_p1_content_free_counters() -> None:
    telemetry = ReadinessTelemetry(run_id="run-counters", phase="release")
    names = (
        "byte_snapshots",
        "markdown_parses",
        "json_parses",
        "git_state_loads",
        "connector_result_cache_hits",
        "connector_result_cache_misses",
        "normalized_source_parses",
        "normalized_source_cache_hits",
        "http_unique_requests",
        "http_deduplicated_occurrences",
        "final_reseals",
    )
    for name in names:
        telemetry.increment(name)
    telemetry.finish("passed")

    assert all(telemetry.to_dict()["counters"][name] == 1 for name in names)


def test_http_observer_events_update_counters_and_balanced_gauges() -> None:
    telemetry = ReadinessTelemetry(run_id="run-http", phase="preflight")
    observe = telemetry.http_observer

    observe("requests", 1)
    observe("cache_hits", 1)
    observe("cache_misses", 1)
    observe("response_bytes", 512)
    observe("deduplicated_requests", 2)
    observe("in_flight_requests_delta", 1)
    observe("reserved_bytes_delta", 4_096)
    observe("retained_bytes_delta", 512)
    observe("in_flight_requests_delta", -1)
    observe("reserved_bytes_delta", -4_096)
    observe("retained_bytes_delta", -512)
    telemetry.finish("passed")

    payload = telemetry.to_dict()
    assert payload["counters"]["http_requests"] == 1
    assert payload["counters"]["http_unique_requests"] == 1
    assert payload["counters"]["http_response_bytes"] == 512
    assert payload["counters"]["http_deduplicated_occurrences"] == 2
    assert payload["gauges"]["current_http_requests"] == 0
    assert payload["gauges"]["peak_http_requests"] == 1
    assert payload["gauges"]["current_http_reserved_bytes"] == 0
    assert payload["gauges"]["peak_http_reserved_bytes"] == 4_096
    assert payload["gauges"]["retained_http_response_bytes"] == 0
