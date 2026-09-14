"""Measure the deterministic offline optimized-release characterization path."""

from __future__ import annotations

import argparse
import json
import os
import socket
import statistics
import sys
import tempfile
import time
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Sequence

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

SCHEMA = "simpro-offline-release-benchmark/v2"
DEFAULT_NODE = "isolated-validation-session/v2"
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
)
FIXTURE_URL = "https://benchmark.example/source"
FIXTURE_BODY = b"<html><body>benchmark evidence</body></html>"


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
    observed = []
    for _ in range(samples + 1):
        with tempfile.TemporaryDirectory(prefix="simpro-release-benchmark-") as raw_root:
            runtime_root = Path(raw_root)
            _prepare_fixture(runtime_root)
            observed.append({
                "cold": _run_once(repo, node=node, runtime_root=runtime_root),
                "warm": _run_once(repo, node=node, runtime_root=runtime_root),
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
        "schema": SCHEMA,
        "repository_commit": _commit(repo),
        "repository_dirty": _is_dirty(repo),
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
        },
        "boundary_counters": {
            phase: _deterministic_phase(measured, phase, "counters")
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
        f"result=benchmark._run_fixture(Path({str(runtime_root)!r}));"
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
        "scoring_imports": child_result["scoring_imports"],
    }


def _prepare_fixture(runtime_root: Path) -> None:
    workspace = runtime_root / "fixture"
    workspace.mkdir(parents=True, exist_ok=True)
    article = workspace / "article.md"
    registry = workspace / "context" / "registry.json"
    registry.parent.mkdir(parents=True, exist_ok=True)
    article.write_bytes(b"# Benchmark article\n\nBounded fixture content.\n")
    registry.write_bytes(
        (
            json.dumps({"revision": "benchmark-v2", "records": []}, sort_keys=True)
            + "\n"
        ).encode("utf-8")
    )
    _run_git(workspace, "init", "-q")
    _run_git(workspace, "config", "user.email", "benchmark@example.invalid")
    _run_git(workspace, "config", "user.name", "Benchmark Fixture")
    _run_git(workspace, "add", "article.md", "context/registry.json")
    _run_git(workspace, "commit", "-qm", "benchmark fixture")


def _run_fixture(runtime_root: Path) -> dict[str, Any]:
    scoring_before = {name for name in SCORING_MODULES if name in sys.modules}
    from data_sources.modules.public_http import (
        PublicHttpTransport,
        SOURCE_VISIBLE_TEXT_POLICY,
    )
    from data_sources.modules.readiness.session import ValidationSession
    from data_sources.modules.readiness.telemetry import ReadinessTelemetry

    workspace = runtime_root / "fixture"
    article = workspace / "article.md"
    registry = workspace / "context" / "registry.json"
    telemetry = ReadinessTelemetry(run_id="offline-benchmark", phase="final")
    started = time.perf_counter_ns()

    def transport_factory() -> PublicHttpTransport:
        return PublicHttpTransport(
            cache_dir=runtime_root / "http-cache",
            requester=_fixture_requester,
            resolver=_fixture_resolver,
            observer=telemetry.http_observer,
        )

    with ValidationSession.capture(
        {"article": article, "registry": registry},
        workspace_root=workspace,
        connector_factory=_BenchmarkConnector,
        claim_loader=lambda connector: connector.claims(),
        transport_factory=transport_factory,
        telemetry=telemetry,
    ) as session:
        session.artifacts.markdown_view("article")
        registry_view = session.artifacts.json_view("registry")
        bytes_view = session.artifacts.bytes_view("registry")
        snapshot = SimpleNamespace(
            path=registry_view.path,
            data=bytes_view.content,
            sha256=registry_view.sha256,
            payload=registry_view.payload,
        )
        session.git_registry_state(registry, lambda: snapshot)
        session.git_registry_state(registry, lambda: snapshot)
        session.validated_claim_set()
        session.validated_claim_set()
        session.connector_result("search", {"query": "benchmark"}, lambda: {"id": 1})
        session.connector_result("search", {"query": "benchmark"}, lambda: {"id": 2})
        transport = session.transport()
        responses = transport.request_many(
            "GET",
            [FIXTURE_URL, FIXTURE_URL],
            policy=SOURCE_VISIBLE_TEXT_POLICY,
        )
        session.normalized_source(FIXTURE_URL, lambda: responses[0].text)
        session.normalized_source(FIXTURE_URL, lambda: "unreachable")
        transport.request("GET", FIXTURE_URL, policy=SOURCE_VISIBLE_TEXT_POLICY)
        session.artifacts.reseal()
    telemetry.finish("passed")
    elapsed_ms = round((time.perf_counter_ns() - started) / 1_000_000, 3)
    payload = telemetry.to_dict()
    counters = payload["counters"]
    return {
        "fixture_elapsed_ms": elapsed_ms,
        "counters": {name: counters[name] for name in BENCHMARK_COUNTERS},
        "scoring_imports": sorted(
            name
            for name in SCORING_MODULES
            if name in sys.modules and name not in scoring_before
        ),
    }


class _BenchmarkConnector:
    def workflow_snapshot(self) -> "_BenchmarkConnector":
        return self

    def __enter__(self) -> "_BenchmarkConnector":
        return self

    def __exit__(self, *args: object) -> None:
        del args

    def claims(self) -> tuple[str, ...]:
        return ("benchmark-claim",)

    def close(self) -> None:
        return None


def _fixture_resolver(host: str, port: int, **kwargs: object) -> list[tuple[object, ...]]:
    del host, kwargs
    return [(socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", ("93.184.216.34", port))]


def _fixture_requester(session: object, method: str, url: str, **kwargs: object):
    del session, method, kwargs
    import requests

    response = requests.Response()
    response.status_code = 200
    response.url = url
    response.headers["Content-Type"] = "text/html; charset=utf-8"
    response._content = FIXTURE_BODY
    response._content_consumed = True
    return response


def _run_git(repository: Path, *arguments: str) -> None:
    completed = _run_bounded_text_process(
        ["git", "-C", str(repository), *arguments],
        timeout=30,
        max_output_bytes=1024 * 1024,
    )
    if completed.returncode != 0:
        raise RuntimeError(completed.stderr.strip() or "git command failed")


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
    parser.add_argument("--node", default=DEFAULT_NODE)
    args = parser.parse_args(argv)
    result = run_benchmark(args.repository, samples=args.samples, node=args.node)
    _atomic_write(args.output, result)
    print(json.dumps(result["summary"], sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
