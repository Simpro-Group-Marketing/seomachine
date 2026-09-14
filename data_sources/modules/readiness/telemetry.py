"""Content-free performance telemetry for governed readiness runs."""

from __future__ import annotations

import json
import os
import tempfile
import threading
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

from ..resource_metrics import process_peak_rss_bytes


TELEMETRY_SCHEMA = "simpro-readiness-telemetry/v2"
SUPPORTED_TELEMETRY_SCHEMAS = frozenset(
    {"simpro-readiness-telemetry/v1", TELEMETRY_SCHEMA}
)
COUNTERS = (
    "full_readiness_executions",
    "gate_invocations",
    "unique_file_reads",
    "bytes_read",
    "file_hashes",
    "final_rehashes",
    "final_reseals",
    "connector_clients",
    "connector_operations",
    "http_requests",
    "cache_hits",
    "cache_misses",
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
    "http_response_bytes",
)
GAUGES = (
    "current_http_requests",
    "peak_http_requests",
    "current_http_reserved_bytes",
    "peak_http_reserved_bytes",
    "retained_http_response_bytes",
    "normalized_source_bytes",
    "artifact_store_source_bytes",
    "process_peak_rss_bytes",
    "peak_allocation_bytes",
)
OUTCOMES = frozenset({"passed", "blocked", "operational_error"})


class ReadinessTelemetry:
    """Accumulate numeric observations without retaining proof-sensitive data."""

    __slots__ = (
        "_completed_at",
        "_counters",
        "_finished_ns",
        "_failure_output",
        "_gauges",
        "_lock",
        "_outcome",
        "_phase",
        "_run_id",
        "_stages",
        "_started_at",
        "_started_ns",
    )

    def __init__(
        self,
        *,
        run_id: str,
        phase: str,
        failure_output: str | Path | None = None,
    ) -> None:
        if not isinstance(run_id, str) or not run_id.strip():
            raise ValueError("telemetry run_id is required")
        if phase not in {"preflight", "final", "release"}:
            raise ValueError("telemetry phase is invalid")
        self._run_id = run_id.strip()
        self._phase = phase
        self._failure_output = (
            Path(failure_output) if failure_output is not None else None
        )
        self._started_at = _utc_now()
        self._started_ns = time.perf_counter_ns()
        self._completed_at: str | None = None
        self._finished_ns: int | None = None
        self._outcome: str | None = None
        self._counters = {name: 0 for name in COUNTERS}
        self._gauges: dict[str, int | None] = {name: 0 for name in GAUGES}
        self._gauges["process_peak_rss_bytes"] = None
        self._gauges["peak_allocation_bytes"] = None
        self._stages: list[dict[str, object]] = []
        self._lock = threading.RLock()

    def increment(self, counter: str, amount: int = 1) -> None:
        if not isinstance(amount, int) or isinstance(amount, bool) or amount < 0:
            raise ValueError("telemetry counter amount must be a non-negative integer")
        with self._lock:
            if counter not in self._counters:
                raise ValueError(f"unknown telemetry counter: {counter}")
            self._counters[counter] += amount

    def set_gauge(self, gauge: str, value: int | None) -> None:
        """Set a content-free current measurement."""
        _validate_gauge_value(value)
        with self._lock:
            if gauge not in self._gauges:
                raise ValueError(f"unknown telemetry gauge: {gauge}")
            self._gauges[gauge] = value

    def observe_peak(self, gauge: str, value: int) -> None:
        """Retain the largest observed value for one peak gauge."""
        _validate_gauge_value(value)
        with self._lock:
            if gauge not in self._gauges or not gauge.startswith("peak_"):
                raise ValueError(f"unknown telemetry peak gauge: {gauge}")
            previous = self._gauges[gauge]
            self._gauges[gauge] = value if previous is None else max(previous, value)

    def http_observer(self, event: str, amount: int) -> None:
        """Consume content-free transport lifecycle events in real time."""
        if not isinstance(amount, int) or isinstance(amount, bool):
            raise ValueError("HTTP telemetry amount must be an integer")
        counters = {
            "requests": ("http_requests", "http_unique_requests"),
            "cache_hits": ("cache_hits",),
            "cache_misses": ("cache_misses",),
            "response_bytes": ("http_response_bytes",),
            "deduplicated_requests": ("http_deduplicated_occurrences",),
        }
        if event in counters:
            if amount < 0:
                raise ValueError("HTTP counter telemetry cannot be negative")
            for counter in counters[event]:
                self.increment(counter, amount)
            return
        gauges = {
            "in_flight_requests_delta": (
                "current_http_requests",
                "peak_http_requests",
            ),
            "reserved_bytes_delta": (
                "current_http_reserved_bytes",
                "peak_http_reserved_bytes",
            ),
            "retained_bytes_delta": ("retained_http_response_bytes", None),
        }
        try:
            current, peak = gauges[event]
        except KeyError as error:
            raise ValueError(f"unknown HTTP telemetry event: {event}") from error
        self._adjust_gauge(current, amount, peak=peak)

    def _adjust_gauge(
        self,
        gauge: str,
        amount: int,
        *,
        peak: str | None,
    ) -> None:
        with self._lock:
            previous = self._gauges[gauge]
            current = (previous or 0) + amount
            if current < 0:
                raise ValueError(f"telemetry gauge became negative: {gauge}")
            self._gauges[gauge] = current
            if peak is not None:
                prior_peak = self._gauges[peak]
                self._gauges[peak] = max(prior_peak or 0, current)

    @contextmanager
    def stage(self, name: str) -> Iterator[None]:
        if not isinstance(name, str) or not name.strip():
            raise ValueError("telemetry stage name is required")
        started = time.perf_counter_ns()
        with self._lock:
            before = dict(self._counters)
        outcome = "passed"
        failed = False
        try:
            yield
        except BaseException:
            outcome = "error"
            failed = True
            raise
        finally:
            completed = time.perf_counter_ns()
            with self._lock:
                delta = {
                    key: self._counters[key] - before[key]
                    for key in COUNTERS
                    if self._counters[key] != before[key]
                }
                self._stages.append(
                    {
                        "name": name.strip(),
                        "elapsed_ms": _milliseconds(completed - started),
                        "outcome": outcome,
                        "counters": delta,
                    }
                )
            if failed and self._failure_output is not None and self._outcome is None:
                self.finish("operational_error")
                self.write(self._failure_output)

    def finish(self, outcome: str) -> None:
        if outcome not in OUTCOMES:
            raise ValueError("telemetry outcome is invalid")
        with self._lock:
            if self._outcome is not None:
                raise ValueError("telemetry is already finished")
            self._outcome = outcome
            self._finished_ns = time.perf_counter_ns()
            self._completed_at = _utc_now()

    def to_dict(self) -> dict[str, object]:
        with self._lock:
            if (
                self._outcome is None
                or self._finished_ns is None
                or self._completed_at is None
            ):
                raise ValueError("telemetry must be finished before serialization")
            peak_rss = process_peak_rss_bytes()
            gauges = dict(self._gauges)
            gauges["process_peak_rss_bytes"] = peak_rss
            return {
                "schema": TELEMETRY_SCHEMA,
                "run_id": self._run_id,
                "phase": self._phase,
                "outcome": self._outcome,
                "started_at": self._started_at,
                "completed_at": self._completed_at,
                "elapsed_ms": _milliseconds(self._finished_ns - self._started_ns),
                "process_peak_rss_bytes": peak_rss,
                "counters": dict(self._counters),
                "gauges": gauges,
                "stages": [dict(stage) for stage in self._stages],
            }

    def write(self, path: str | Path) -> Path:
        destination = Path(path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        payload = json.dumps(
            self.to_dict(),
            ensure_ascii=True,
            indent=2,
            sort_keys=True,
            allow_nan=False,
        ) + "\n"
        temporary: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                newline="\n",
                dir=destination.parent,
                prefix=f".{destination.name}.",
                suffix=".tmp",
                delete=False,
            ) as handle:
                temporary = Path(handle.name)
                handle.write(payload)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, destination)
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
        return destination


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _milliseconds(nanoseconds: int) -> float:
    return round(max(0, nanoseconds) / 1_000_000, 3)


def _validate_gauge_value(value: int | None) -> None:
    if value is not None and (
        not isinstance(value, int) or isinstance(value, bool) or value < 0
    ):
        raise ValueError("telemetry gauge value must be a non-negative integer or null")
