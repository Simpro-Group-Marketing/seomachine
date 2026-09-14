"""Measure the deterministic offline optimized-release characterization path."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import statistics
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Sequence

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

SCHEMA = "simpro-offline-release-benchmark/v3"
DEFAULT_NODE = "isolated-validation-session/v2"
BLOG_RELEASE_NODE = "optimized-blog-release/v1"
LANDING_RELEASE_NODE = "landing-page-release/v1"
ALL_NODES = (DEFAULT_NODE, BLOG_RELEASE_NODE, LANDING_RELEASE_NODE)
MARKER = "__SIMPRO_BENCHMARK_RESULT__="
SCORING_MODULES = (
    "data_sources.modules.content_scorer",
    "data_sources.modules.readability_scorer",
    "textstat",
)
BENCHMARK_COUNTERS = (
    "unique_file_reads",
    "bytes_read",
    "file_hashes",
    "byte_snapshots",
    "markdown_parses",
    "json_parses",
    "git_state_loads",
    "connector_clients",
    "connector_operations",
    "connector_result_cache_hits",
    "connector_result_cache_misses",
    "normalized_source_parses",
    "normalized_source_cache_hits",
    "http_requests",
    "http_unique_requests",
    "http_deduplicated_occurrences",
    "http_response_bytes",
    "cache_hits",
    "cache_misses",
    "final_reseals",
    "final_rehashes",
    "http_dns_resolutions",
)
BENCHMARK_GAUGES = (
    "artifact_store_source_bytes",
    "peak_artifact_store_source_bytes",
    "connector_result_cache_bytes",
    "peak_connector_result_cache_bytes",
    "normalized_source_bytes",
    "peak_normalized_source_bytes",
    "http_memo_bytes",
    "peak_http_memo_bytes",
    "current_http_reserved_bytes",
    "peak_http_reserved_bytes",
    "process_peak_rss_bytes",
)
def run_benchmark(
    repository: Path,
    *,
    samples: int = 10,
    node: str = "all",
    nodes: Sequence[str] | None = None,
    authoritative: bool = False,
) -> dict[str, Any]:
    if samples < 1:
        raise ValueError("samples must be positive")
    repo = repository.resolve()
    if not (repo / "pytest.ini").is_file():
        raise ValueError(f"benchmark repository is invalid: {repo}")
    dirty = _is_dirty(repo)
    if authoritative and dirty:
        raise RuntimeError("authoritative benchmark generation requires a clean worktree")
    selected_nodes = _selected_nodes(node=node, nodes=nodes)
    scenario_reports = {
        selected: _run_scenario(repo, samples=samples, node=selected)
        for selected in selected_nodes
    }
    default_report = scenario_reports[selected_nodes[0]]
    return {
        "schema": SCHEMA,
        "repository_commit": _commit(repo),
        "repository_dirty": dirty,
        "authoritative": authoritative,
        "harness_sha256": _file_sha256(Path(__file__)),
        "fixture": "multi-scenario-release-suite/v1",
        "environment": {
            "python": sys.version.split()[0],
            "platform": sys.platform,
            "process_peak_rss_available": any(
                report["summary"]["median_peak_rss_bytes"] is not None
                for report in scenario_reports.values()
            ),
        },
        "scenarios": scenario_reports,
        "summary": {
            "sample_count": samples,
            "scenario_count": len(scenario_reports),
            "scenarios": {
                name: report["summary"]
                for name, report in scenario_reports.items()
            },
        },
        "warmup": default_report["warmup"],
        "samples": default_report["samples"],
        "boundary_counters": default_report["boundary_counters"],
        "scoring_imports": default_report["scoring_imports"],
    }


def _selected_nodes(
    *,
    node: str,
    nodes: Sequence[str] | None,
) -> tuple[str, ...]:
    raw_nodes = tuple(nodes) if nodes is not None else (ALL_NODES if node == "all" else (node,))
    if not raw_nodes:
        raise ValueError("at least one benchmark scenario is required")
    unknown = sorted(set(raw_nodes) - set(ALL_NODES))
    if unknown:
        raise ValueError(f"unknown benchmark scenario: {', '.join(unknown)}")
    return raw_nodes


def _run_scenario(
    repository: Path,
    *,
    samples: int,
    node: str,
) -> dict[str, Any]:
    observed = []
    for _ in range(samples + 1):
        with tempfile.TemporaryDirectory(prefix="simpro-release-benchmark-") as raw_root:
            runtime_root = Path(raw_root)
            _prepare_fixture(runtime_root)
            observed.append({
                "cold": _run_once(repository, node=node, runtime_root=runtime_root),
                "warm": _run_once(repository, node=node, runtime_root=runtime_root),
            })
    warmup, measured = observed[0], observed[1:]
    cold_wall = [row["cold"]["wall_ms"] for row in measured]
    warm_wall = [row["warm"]["wall_ms"] for row in measured]
    rss_values = [
        execution["peak_rss_bytes"]
        for row in measured
        for execution in (row["cold"], row["warm"])
        if execution["peak_rss_bytes"]
    ]
    return {
        "node": node,
        "warmup": warmup,
        "samples": measured,
        "summary": {
            "sample_count": samples,
            "median_cold_wall_ms": round(statistics.median(cold_wall), 3),
            "median_warm_wall_ms": round(statistics.median(warm_wall), 3),
            "median_cold_fixture_elapsed_ms": _median_phase(
                measured, "cold", "fixture_elapsed_ms"
            ),
            "median_warm_fixture_elapsed_ms": _median_phase(
                measured, "warm", "fixture_elapsed_ms"
            ),
            "median_cold_pre_fixture_ms": _median_difference(
                measured, "cold", "child_elapsed_ms", "fixture_elapsed_ms"
            ),
            "median_warm_pre_fixture_ms": _median_difference(
                measured, "warm", "child_elapsed_ms", "fixture_elapsed_ms"
            ),
            "median_cold_process_overhead_ms": _median_difference(
                measured, "cold", "wall_ms", "child_elapsed_ms"
            ),
            "median_warm_process_overhead_ms": _median_difference(
                measured, "warm", "wall_ms", "child_elapsed_ms"
            ),
            "median_peak_rss_bytes": (
                int(statistics.median(rss_values)) if rss_values else None
            ),
            "exit_phase": _deterministic_phase(measured, "warm", "exit_phase"),
            "final_authorization_result": _deterministic_phase(
                measured, "warm", "final_authorization_result"
            ),
        },
        "boundary_counters": {
            phase: _deterministic_phase(measured, phase, "counters")
            for phase in ("cold", "warm")
        },
        "gauges": {
            phase: _numeric_mapping_summary(measured, phase, "gauges")
            for phase in ("cold", "warm")
        },
        "scoring_imports": {
            phase: _deterministic_phase(measured, phase, "scoring_imports")
            for phase in ("cold", "warm")
        },
    }


def _run_bounded_text_process(*args: Any, **kwargs: Any) -> Any:
    """Import process control only in the parent benchmark process."""
    from data_sources.modules.artifact_runtime.subprocesses import (
        run_bounded_text_process,
    )

    return run_bounded_text_process(*args, **kwargs)


def _run_once(
    repository: Path,
    *,
    node: str,
    runtime_root: Path,
) -> dict[str, Any]:
    child = (
        "import json,time;"
        "from pathlib import Path;"
        "from tools import benchmark_release as benchmark;"
        "started=time.perf_counter_ns();"
        f"result=benchmark._run_fixture(Path({str(runtime_root)!r}), node={node!r});"
        "result['child_elapsed_ms']=round((time.perf_counter_ns()-started)/1e6,3);"
        "print('" + MARKER + "'+json.dumps(result,sort_keys=True))"
    )
    started = time.perf_counter_ns()
    environment = dict(os.environ)
    environment["SEOMACHINE_RUNTIME_ROOT"] = str(runtime_root)
    completed = _run_bounded_text_process(
        [sys.executable, "-c", child],
        cwd=repository,
        env=environment,
        timeout=300,
        max_output_bytes=8 * 1024 * 1024,
        measure_peak_rss=True,
    )
    peak_rss = completed.peak_rss_bytes
    stdout = completed.stdout
    wall_ms = round((time.perf_counter_ns() - started) / 1_000_000, 3)
    if completed.returncode != 0:
        details = completed.stderr or stdout
        raise RuntimeError(f"benchmark fixture failed ({completed.returncode}):\n{details}")
    child_result = _marker_payload(stdout)
    return {
        "wall_ms": wall_ms,
        "fixture_elapsed_ms": child_result["fixture_elapsed_ms"],
        "child_elapsed_ms": child_result["child_elapsed_ms"],
        "peak_rss_bytes": peak_rss,
        "counters": child_result["counters"],
        "gauges": child_result["gauges"],
        "scoring_imports": child_result["scoring_imports"],
        "exit_phase": child_result.get("exit_phase"),
        "exit_code": child_result.get("exit_code"),
        "final_authorization_result": child_result.get("final_authorization_result"),
    }


def _prepare_fixture(runtime_root: Path) -> None:
    from tools.benchmark_release_session import prepare_fixture

    prepare_fixture(runtime_root)


def _run_fixture(runtime_root: Path, *, node: str = DEFAULT_NODE) -> dict[str, Any]:
    if node == BLOG_RELEASE_NODE:
        from tools.benchmark_release_fixtures import run_blog_release_fixture

        return _normalized_fixture_result(run_blog_release_fixture(runtime_root))
    if node == LANDING_RELEASE_NODE:
        from tools.benchmark_release_fixtures import run_landing_release_fixture

        return _normalized_fixture_result(run_landing_release_fixture(runtime_root))
    if node != DEFAULT_NODE:
        raise ValueError(f"unknown benchmark fixture: {node}")
    from tools.benchmark_release_session import run_session_fixture

    return run_session_fixture(
        runtime_root,
        benchmark_counters=BENCHMARK_COUNTERS,
        benchmark_gauges=BENCHMARK_GAUGES,
        scoring_modules=SCORING_MODULES,
    )


def _normalized_fixture_result(result: dict[str, Any]) -> dict[str, Any]:
    counters = dict(result.get("counters") or {})
    gauges = dict(result.get("gauges") or {})
    result["counters"] = {name: counters.get(name, 0) for name in BENCHMARK_COUNTERS}
    result["gauges"] = {name: gauges.get(name) for name in BENCHMARK_GAUGES}
    result.setdefault("scoring_imports", [])
    result.setdefault("exit_phase", None)
    result.setdefault("exit_code", None)
    result.setdefault("final_authorization_result", None)
    return result


def _median_phase(rows: list[dict[str, Any]], phase: str, field: str) -> float:
    return round(statistics.median(row[phase][field] for row in rows), 3)


def _median_difference(
    rows: list[dict[str, Any]],
    phase: str,
    minuend: str,
    subtrahend: str,
) -> float:
    return round(
        statistics.median(
            row[phase][minuend] - row[phase][subtrahend] for row in rows
        ),
        3,
    )


def _deterministic_phase(
    rows: list[dict[str, Any]],
    phase: str,
    field: str,
) -> Any:
    values = [row[phase][field] for row in rows]
    first = values[0]
    if any(value != first for value in values[1:]):
        raise RuntimeError(f"benchmark {phase} {field} observations are not deterministic")
    return first


def _numeric_mapping_summary(
    rows: list[dict[str, Any]],
    phase: str,
    field: str,
) -> dict[str, dict[str, float | int | None]]:
    mappings = [row[phase][field] for row in rows]
    keys = sorted({key for mapping in mappings for key in mapping})
    summary: dict[str, dict[str, float | int | None]] = {}
    for key in keys:
        values = [mapping.get(key) for mapping in mappings]
        numeric = [value for value in values if isinstance(value, (int, float))]
        if len(numeric) != len(values):
            summary[key] = {"minimum": None, "median": None, "maximum": None}
            continue
        summary[key] = {
            "minimum": min(numeric),
            "median": round(statistics.median(numeric), 3),
            "maximum": max(numeric),
        }
    return summary


def _marker_payload(stdout: str) -> dict[str, Any]:
    rows = [line[len(MARKER) :] for line in stdout.splitlines() if line.startswith(MARKER)]
    if len(rows) != 1:
        raise RuntimeError(f"benchmark fixture did not emit one result marker:\n{stdout}")
    value = json.loads(rows[0])
    if not isinstance(value, dict):
        raise RuntimeError("benchmark fixture result is invalid")
    return value


def _commit(repository: Path) -> str:
    completed = _run_bounded_text_process(
        ["git", "rev-parse", "HEAD"],
        cwd=repository,
        timeout=30,
        max_output_bytes=1024 * 1024,
    )
    if completed.returncode != 0:
        raise RuntimeError(completed.stderr.strip() or "git rev-parse failed")
    return completed.stdout.strip()


def _file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _is_dirty(repository: Path) -> bool:
    completed = _run_bounded_text_process(
        ["git", "status", "--porcelain"],
        cwd=repository,
        timeout=30,
        max_output_bytes=1024 * 1024,
    )
    if completed.returncode != 0:
        raise RuntimeError(completed.stderr.strip() or "git status failed")
    return bool(completed.stdout.strip())


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
    parser.add_argument("--node", default="all")
    parser.add_argument(
        "--scenario",
        action="append",
        choices=ALL_NODES,
        help="Run one scenario; repeat to select multiple. Defaults to all scenarios.",
    )
    parser.add_argument(
        "--authoritative",
        action="store_true",
        help="Require a clean repository and mark the output as authoritative.",
    )
    args = parser.parse_args(argv)
    result = run_benchmark(
        args.repository,
        samples=args.samples,
        node=args.node,
        nodes=args.scenario,
        authoritative=args.authoritative,
    )
    _atomic_write(args.output, result)
    print(json.dumps(result["summary"], sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
