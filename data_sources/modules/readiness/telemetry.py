"""Content-free performance telemetry for governed readiness runs."""

from __future__ import annotations

import json
import os
import tempfile
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator


TELEMETRY_SCHEMA = "simpro-readiness-telemetry/v1"
COUNTERS = (
    "full_readiness_executions",
    "gate_invocations",
    "unique_file_reads",
    "bytes_read",
    "file_hashes",
    "final_rehashes",
    "connector_clients",
    "connector_operations",
    "http_requests",
    "cache_hits",
    "cache_misses",
)
OUTCOMES = frozenset({"passed", "blocked", "operational_error"})


class ReadinessTelemetry:
    """Accumulate numeric observations without retaining proof-sensitive data."""

    __slots__ = (
        "_completed_at",
        "_counters",
        "_finished_ns",
        "_failure_output",
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
        self._failure_output = Path(failure_output) if failure_output is not None else None
        self._started_at = _utc_now()
        self._started_ns = time.perf_counter_ns()
        self._completed_at: str | None = None
        self._finished_ns: int | None = None
        self._outcome: str | None = None
        self._counters = {name: 0 for name in COUNTERS}
        self._stages: list[dict[str, object]] = []

    def increment(self, counter: str, amount: int = 1) -> None:
        if counter not in self._counters:
            raise ValueError(f"unknown telemetry counter: {counter}")
        if not isinstance(amount, int) or isinstance(amount, bool) or amount < 0:
            raise ValueError("telemetry counter amount must be a non-negative integer")
        self._counters[counter] += amount

    @contextmanager
    def stage(self, name: str) -> Iterator[None]:
        if not isinstance(name, str) or not name.strip():
            raise ValueError("telemetry stage name is required")
        started = time.perf_counter_ns()
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
        if self._outcome is not None:
            raise ValueError("telemetry is already finished")
        if outcome not in OUTCOMES:
            raise ValueError("telemetry outcome is invalid")
        self._outcome = outcome
        self._finished_ns = time.perf_counter_ns()
        self._completed_at = _utc_now()

    def to_dict(self) -> dict[str, object]:
        if self._outcome is None or self._finished_ns is None or self._completed_at is None:
            raise ValueError("telemetry must be finished before serialization")
        return {
            "schema": TELEMETRY_SCHEMA,
            "run_id": self._run_id,
            "phase": self._phase,
            "outcome": self._outcome,
            "started_at": self._started_at,
            "completed_at": self._completed_at,
            "elapsed_ms": _milliseconds(self._finished_ns - self._started_ns),
            "process_peak_rss_bytes": _peak_rss_bytes(),
            "counters": dict(self._counters),
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


def _peak_rss_bytes() -> int | None:
    """Return a no-dependency process peak where Python exposes one safely."""
    if os.name == "nt":
        return None
    try:
        import resource

        value = int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    except (ImportError, OSError, TypeError, ValueError):
        return None
    return value if os.uname().sysname == "Darwin" else value * 1024
