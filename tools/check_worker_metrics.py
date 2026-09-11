"""Validate and summarize content-free pytest worker metrics."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence


METRIC_SCHEMA = "simpro-test-worker-metrics/v1"
SUMMARY_SCHEMA = "simpro-test-worker-metrics-summary/v1"


def metric_errors(
    records: Iterable[Mapping[str, object]],
    *,
    expected_workers: int,
    max_peak_rss_bytes: int | None = None,
) -> list[str]:
    """Return deterministic worker-count, replacement, and RSS errors."""
    rows = list(records)
    errors = _record_errors(rows)
    workers = [row.get("worker_id") for row in rows if isinstance(row.get("worker_id"), str)]
    counts = Counter(workers)
    if len(counts) != expected_workers:
        errors.append(f"expected {expected_workers} unique workers; found {len(counts)}")
    for worker, count in sorted(counts.items()):
        if count > 1:
            errors.append(f"worker {worker} was replaced during the run")
    if max_peak_rss_bytes is not None:
        for row in rows:
            worker = row.get("worker_id")
            peak = row.get("peak_rss_bytes")
            if peak is None:
                errors.append(f"worker {worker} did not report peak RSS")
            elif isinstance(peak, int) and peak > max_peak_rss_bytes:
                errors.append(f"worker {worker} exceeded the peak RSS limit")
    return sorted(set(errors))


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
        if not isinstance(row.get("worker_id"), str) or not row.get("worker_id"):
            errors.append(f"{label} has an invalid worker ID")
        process_id = row.get("process_id")
        if isinstance(process_id, bool) or not isinstance(process_id, int) or process_id < 1:
            errors.append(f"{label} has an invalid process ID")
        elif process_id in process_ids:
            errors.append(f"{label} repeats process ID {process_id}")
        else:
            process_ids.add(process_id)
    return errors


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
    parser.add_argument("--max-peak-rss-mib", type=int)
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
