from __future__ import annotations

from pathlib import Path

from data_sources.modules.readiness.session import ValidationSession
from data_sources.modules.readiness.telemetry import ReadinessTelemetry


def test_session_does_not_double_count_event_reporting_transport(tmp_path: Path) -> None:
    article = tmp_path / "article.md"
    article.write_text("# Article\n", encoding="utf-8")
    telemetry = ReadinessTelemetry(run_id="run-http", phase="preflight")

    class Transport:
        reports_events = True
        counters = {"requests": 1, "cache_hits": 1, "cache_misses": 1}

        def close(self) -> None:
            return None

    with ValidationSession.capture(
        {"article": article},
        workspace_root=tmp_path,
        transport_factory=Transport,
        telemetry=telemetry,
    ) as session:
        session.transport()
        telemetry.http_observer("requests", 1)
        telemetry.http_observer("cache_hits", 1)
        telemetry.http_observer("cache_misses", 1)

    telemetry.finish("passed")
    counters = telemetry.to_dict()["counters"]
    assert counters["http_requests"] == 1
    assert counters["http_unique_requests"] == 1
    assert counters["cache_hits"] == 1
    assert counters["cache_misses"] == 1
