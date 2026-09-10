"""Measure the deterministic offline optimized-release characterization path."""

from __future__ import annotations

import argparse
import ctypes
import json
import os
import statistics
import subprocess
import sys
import tempfile
import time
from ctypes import wintypes
from pathlib import Path
from typing import Any, Sequence


SCHEMA = "simpro-offline-release-benchmark/v1"
DEFAULT_NODE = (
    "tests/test_blog_release.py::"
    "test_blog_release_finalizes_only_with_optimizer_evidence"
)
MARKER = "__SIMPRO_BENCHMARK_RESULT__="
SCORING_MODULES = (
    "data_sources.modules.content_scorer",
    "data_sources.modules.readability_scorer",
    "textstat",
)


def run_benchmark(
    repository: Path,
    *,
    samples: int = 10,
    node: str = DEFAULT_NODE,
) -> dict[str, Any]:
    if samples < 1:
        raise ValueError("samples must be positive")
    repo = repository.resolve()
    if not (repo / "pytest.ini").is_file():
        raise ValueError(f"benchmark repository is invalid: {repo}")
    observed = [_run_once(repo, node=node) for _ in range(samples + 1)]
    warmup, measured = observed[0], observed[1:]
    wall_values = [row["wall_ms"] for row in measured]
    rss_values = [row["peak_rss_bytes"] for row in measured if row["peak_rss_bytes"]]
    return {
        "schema": SCHEMA,
        "repository_commit": _commit(repo),
        "fixture": node,
        "environment": {
            "python": sys.version.split()[0],
            "platform": sys.platform,
            "process_peak_rss_available": bool(rss_values),
        },
        "warmup": warmup,
        "samples": measured,
        "summary": {
            "sample_count": samples,
            "median_wall_ms": round(statistics.median(wall_values), 3),
            "median_peak_rss_bytes": (
                int(statistics.median(rss_values)) if rss_values else None
            ),
        },
        "boundary_counters": {
            "full_readiness_executions": 1,
            "connector_state_parses": 0,
            "connector_final_seals": 0,
            "http_operations": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "reason": "The deterministic characterization test replaces external boundaries.",
        },
    }


def _run_once(repository: Path, *, node: str) -> dict[str, Any]:
    child = (
        "import json,pytest,sys,time;"
        "started=time.perf_counter_ns();"
        f"code=pytest.main([{node!r},'-q']);"
        f"names={SCORING_MODULES!r};"
        "print('" + MARKER + "'+json.dumps({"
        "'pytest_exit':code,'elapsed_ms':round((time.perf_counter_ns()-started)/1e6,3),"
        "'scoring_imports':[name for name in names if name in sys.modules]}));"
        "raise SystemExit(code)"
    )
    started = time.perf_counter_ns()
    process = subprocess.Popen(
        [sys.executable, "-c", child],
        cwd=repository,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    peak_rss = _wait_with_peak_rss(process)
    stdout = process.stdout.read() if process.stdout is not None else ""
    wall_ms = round((time.perf_counter_ns() - started) / 1_000_000, 3)
    if process.returncode != 0:
        raise RuntimeError(f"benchmark fixture failed ({process.returncode}):\n{stdout}")
    child_result = _marker_payload(stdout)
    return {
        "wall_ms": wall_ms,
        "fixture_elapsed_ms": child_result["elapsed_ms"],
        "peak_rss_bytes": peak_rss,
        "scoring_imports": child_result["scoring_imports"],
    }


def _wait_with_peak_rss(process: subprocess.Popen[str]) -> int | None:
    if os.name != "nt":
        process.wait()
        return None
    handle = ctypes.windll.kernel32.OpenProcess(0x0400 | 0x0010, False, process.pid)
    if not handle:
        process.wait()
        return None
    peak = 0
    try:
        while process.poll() is None:
            peak = max(peak, _windows_peak_working_set(handle))
            time.sleep(0.005)
        peak = max(peak, _windows_peak_working_set(handle))
    finally:
        ctypes.windll.kernel32.CloseHandle(handle)
    return peak or None


def _windows_peak_working_set(handle: int) -> int:
    class Counters(ctypes.Structure):
        _fields_ = [
            ("cb", wintypes.DWORD),
            ("PageFaultCount", wintypes.DWORD),
            ("PeakWorkingSetSize", ctypes.c_size_t),
            ("WorkingSetSize", ctypes.c_size_t),
            ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
            ("QuotaPagedPoolUsage", ctypes.c_size_t),
            ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
            ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
            ("PagefileUsage", ctypes.c_size_t),
            ("PeakPagefileUsage", ctypes.c_size_t),
        ]

    counters = Counters()
    counters.cb = ctypes.sizeof(counters)
    if not ctypes.windll.psapi.GetProcessMemoryInfo(
        handle, ctypes.byref(counters), counters.cb
    ):
        return 0
    return int(counters.PeakWorkingSetSize)


def _marker_payload(stdout: str) -> dict[str, Any]:
    rows = [line[len(MARKER) :] for line in stdout.splitlines() if line.startswith(MARKER)]
    if len(rows) != 1:
        raise RuntimeError(f"benchmark fixture did not emit one result marker:\n{stdout}")
    value = json.loads(rows[0])
    if not isinstance(value, dict):
        raise RuntimeError("benchmark fixture result is invalid")
    return value


def _commit(repository: Path) -> str:
    completed = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repository,
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


def _atomic_write(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    content = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="\n",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            temporary = Path(handle.name)
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository", type=Path, default=Path.cwd())
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--samples", type=int, default=10)
    parser.add_argument("--node", default=DEFAULT_NODE)
    args = parser.parse_args(argv)
    result = run_benchmark(args.repository, samples=args.samples, node=args.node)
    _atomic_write(args.output, result)
    print(json.dumps(result["summary"], sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
