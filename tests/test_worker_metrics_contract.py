from __future__ import annotations

from tools.check_worker_metrics import metric_errors, summarize_metrics


def _record(
    worker: str,
    *,
    run_id: str = "run-current",
    rss: int | None = 100,
    process_id: int = 1,
    executed: int = 5,
    exit_status: int = 0,
) -> dict[str, object]:
    return {
        "schema": "simpro-test-worker-metrics/v2",
        "run_id": run_id,
        "worker_id": worker,
        "process_id": process_id,
        "elapsed_ms": 10.0,
        "collected": 20,
        "executed": executed,
        "exit_status": exit_status,
        "peak_rss_bytes": rss,
    }


def test_worker_metric_summary_reports_peak_and_total_memory() -> None:
    records = [
        _record(f"gw{index}", rss=(index + 1) * 100, process_id=index + 1)
        for index in range(4)
    ]

    assert metric_errors(
        records,
        expected_workers=4,
        expected_run_id="run-current",
        max_peak_rss_bytes=500,
    ) == []
    assert summarize_metrics(records) == {
        "schema": "simpro-test-worker-metrics-summary/v1",
        "worker_count": 4,
        "process_count": 4,
        "executed": 20,
        "maximum_peak_rss_bytes": 400,
        "total_peak_rss_bytes": 1000,
    }


def test_worker_metric_validation_detects_replacement_missing_memory_and_ceiling() -> None:
    records = [
        _record("gw0", process_id=1),
        _record("gw0", process_id=2),
        _record("gw1", rss=None),
        _record("gw2", rss=600),
    ]

    errors = metric_errors(
        records,
        expected_workers=4,
        expected_run_id="run-current",
        max_peak_rss_bytes=500,
    )

    assert "expected 4 unique workers; found 3" in errors
    assert "worker gw0 was replaced during the run" in errors
    assert "worker gw1 did not report peak RSS" in errors
    assert "worker gw2 exceeded the peak RSS limit" in errors


def test_worker_metric_validation_requires_exact_ids_work_and_success() -> None:
    records = [
        _record("gw0", process_id=1),
        _record("gw1", process_id=2, executed=0),
        _record("gw2", process_id=3, exit_status=1),
        _record("other", process_id=4),
    ]

    errors = metric_errors(
        records,
        expected_workers=4,
        expected_run_id="run-current",
        max_peak_rss_bytes=500,
    )

    assert "missing expected worker IDs: gw3" in errors
    assert "unexpected worker IDs: other" in errors
    assert "worker gw1 executed no tests" in errors
    assert "worker gw2 exited with status 1" in errors


def test_stale_run_records_cannot_satisfy_current_worker_set() -> None:
    records = [
        _record(f"gw{index}", run_id="run-stale", process_id=index + 1)
        for index in range(4)
    ]

    errors = metric_errors(
        records,
        expected_workers=4,
        expected_run_id="run-current",
        max_peak_rss_bytes=500,
    )

    assert "no metrics found for run run-current" in errors
    assert "4 metric records belong to another run" in errors
