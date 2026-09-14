"""Validate and summarize content-free pytest worker metrics."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence


METRIC_SCHEMA = "simpro-test-worker-metrics/v2"
SUMMARY_SCHEMA = "simpro-test-worker-metrics-summary/v1"
DEFAULT_MAX_PEAK_RSS_BYTES = 96 * 1024 * 1024


def metric_errors(
    records: Iterable[Mapping[str, object]],
    *,
    expected_workers: int,
    expected_run_id: str,
    max_peak_rss_bytes: int | None = None,
) -> list[str]:
    """Return deterministic worker-count, replacement, and RSS errors."""
    if (
        isinstance(expected_workers, bool)
        or not isinstance(expected_workers, int)
        or expected_workers < 1
    ):
        raise ValueError("expected_workers must be a positive integer")
    if not isinstance(expected_run_id, str) or not expected_run_id:
        raise ValueError("expected_run_id must be non-empty")
    if max_peak_rss_bytes is not None and (
        isinstance(max_peak_rss_bytes, bool)
        or not isinstance(max_peak_rss_bytes, int)
        or max_peak_rss_bytes < 1
    ):
        raise ValueError("max_peak_rss_bytes must be a positive integer")
    rows = list(records)
    errors = _record_errors(rows)
    current = [row for row in rows if row.get("run_id") == expected_run_id]
    stale_count = len(rows) - len(current)
    if stale_count:
        errors.append(f"{stale_count} metric records belong to another run")
    if not current:
        errors.append(f"no metrics found for run {expected_run_id}")
    errors.extend(_worker_set_errors(current, expected_workers=expected_workers))
    errors.extend(_execution_errors(current))
    if max_peak_rss_bytes is not None:
        errors.extend(_rss_errors(current, maximum=max_peak_rss_bytes))
    return sorted(set(errors))


def _worker_set_errors(
    records: list[Mapping[str, object]],
    *,
    expected_workers: int,
) -> list[str]:
    workers = [
        row.get("worker_id")
        for row in records
        if isinstance(row.get("worker_id"), str)
    ]
    counts = Counter(workers)
    errors: list[str] = []
    if len(counts) != expected_workers:
        errors.append(f"expected {expected_workers} unique workers; found {len(counts)}")
    expected_ids = {f"gw{index}" for index in range(expected_workers)}
    actual_ids = set(counts)
    if missing := sorted(expected_ids - actual_ids):
        errors.append(f"missing expected worker IDs: {', '.join(missing)}")
    if unexpected := sorted(actual_ids - expected_ids):
        errors.append(f"unexpected worker IDs: {', '.join(unexpected)}")
    for worker, count in sorted(counts.items()):
        if count > 1:
            errors.append(f"worker {worker} was replaced during the run")
    return errors


def _execution_errors(records: list[Mapping[str, object]]) -> list[str]:
    errors: list[str] = []
    for row in records:
        worker = row.get("worker_id")
        executed = row.get("executed")
        if isinstance(executed, int) and not isinstance(executed, bool) and executed == 0:
            errors.append(f"worker {worker} executed no tests")
        exit_status = row.get("exit_status")
        if isinstance(exit_status, int) and exit_status != 0:
            errors.append(f"worker {worker} exited with status {exit_status}")
    return errors


def _rss_errors(
    records: list[Mapping[str, object]],
    *,
    maximum: int,
) -> list[str]:
    errors: list[str] = []
    for row in records:
        worker = row.get("worker_id")
        peak = row.get("peak_rss_bytes")
        if peak is None:
            errors.append(f"worker {worker} did not report peak RSS")
        elif isinstance(peak, int) and peak > maximum:
            errors.append(f"worker {worker} exceeded the peak RSS limit")
    return errors


def summarize_metrics(records: Iterable[Mapping[str, object]]) -> dict[str, object]:
    """Build a content-free numeric summary for one pytest run."""
    rows = list(records)
    peaks = [int(row["peak_rss_bytes"]) for row in rows if isinstance(row.get("peak_rss_bytes"), int)]
    workers = {str(row.get("worker_id")) for row in rows}
    return {
        "schema": SUMMARY_SCHEMA,
        "worker_count": len(workers),
        "process_count": len(rows),
        "executed": sum(int(row.get("executed", 0)) for row in rows),
        "maximum_peak_rss_bytes": max(peaks) if peaks else None,
        "total_peak_rss_bytes": sum(peaks) if peaks else None,
    }


def _record_errors(records: list[Mapping[str, object]]) -> list[str]:
    errors: list[str] = []
    process_ids: set[int] = set()
    for index, row in enumerate(records):
        label = f"record {index + 1}"
        if row.get("schema") != METRIC_SCHEMA:
            errors.append(f"{label} has an invalid schema")
        if not isinstance(row.get("run_id"), str) or not row.get("run_id"):
            errors.append(f"{label} has an invalid run ID")
        if not isinstance(row.get("worker_id"), str) or not row.get("worker_id"):
            errors.append(f"{label} has an invalid worker ID")
        _append_numeric_error(errors, row, label=label, field="elapsed_ms", integer=False)
        _append_numeric_error(errors, row, label=label, field="collected", integer=True)
        _append_numeric_error(errors, row, label=label, field="executed", integer=True)
        _append_numeric_error(errors, row, label=label, field="exit_status", integer=True)
        peak = row.get("peak_rss_bytes")
        if peak is not None and (
            isinstance(peak, bool) or not isinstance(peak, int) or peak < 1
        ):
            errors.append(f"{label} has invalid peak_rss_bytes")
        process_id = row.get("process_id")
        if isinstance(process_id, bool) or not isinstance(process_id, int) or process_id < 1:
            errors.append(f"{label} has an invalid process ID")
        elif process_id in process_ids:
            errors.append(f"{label} repeats process ID {process_id}")
        else:
            process_ids.add(process_id)
    return errors


def _append_numeric_error(
    errors: list[str],
    row: Mapping[str, object],
    *,
    label: str,
    field: str,
    integer: bool,
) -> None:
    value = row.get(field)
    numeric_type = int if integer else (int, float)
    if isinstance(value, bool) or not isinstance(value, numeric_type) or value < 0:
        errors.append(f"{label} has invalid {field}")


def _load_records(directory: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for path in sorted(directory.glob("*.json")):
        value = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(value, dict):
            raise ValueError(f"worker metric must be an object: {path}")
        records.append(value)
    return records


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("metrics_dir", type=Path)
    parser.add_argument("--expected-workers", type=int, default=4)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--max-peak-rss-mib", type=int, default=96)
    args = parser.parse_args(argv)
    try:
        records = _load_records(args.metrics_dir)
        maximum = (
            args.max_peak_rss_mib * 1024 * 1024
            if args.max_peak_rss_mib is not None
            else None
        )
        errors = metric_errors(
            records,
            expected_workers=args.expected_workers,
            expected_run_id=args.run_id,
            max_peak_rss_bytes=maximum,
        )
        print(json.dumps(summarize_metrics(records), indent=2, sort_keys=True))
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as error:
        print(f"worker metrics check failed: {error}", file=sys.stderr)
        return 2
    for error in errors:
        print(error, file=sys.stderr)
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
