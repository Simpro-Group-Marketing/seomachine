"""Session-level fixture for the offline release benchmark harness."""

from __future__ import annotations

import json
import socket
import sys
import time
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Sequence


FIXTURE_URL = "https://benchmark.example/source"
FIXTURE_BODY = b"<html><body>benchmark evidence</body></html>"


def prepare_fixture(runtime_root: Path) -> None:
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


def run_session_fixture(
    runtime_root: Path,
    *,
    benchmark_counters: Sequence[str],
    benchmark_gauges: Sequence[str],
    scoring_modules: Sequence[str],
) -> dict[str, Any]:
    scoring_before = {name for name in scoring_modules if name in sys.modules}
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
        "counters": {name: counters[name] for name in benchmark_counters},
        "gauges": {name: payload["gauges"].get(name) for name in benchmark_gauges},
        "scoring_imports": sorted(
            name
            for name in scoring_modules
            if name in sys.modules and name not in scoring_before
        ),
        "exit_phase": "session_complete",
        "exit_code": 0,
        "final_authorization_result": None,
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
    return [
        (
            socket.AF_INET,
            socket.SOCK_STREAM,
            socket.IPPROTO_TCP,
            "",
            ("93.184.216.34", port),
        )
    ]


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


def _run_bounded_text_process(*args: Any, **kwargs: Any) -> Any:
    from data_sources.modules.artifact_runtime.subprocesses import (
        run_bounded_text_process,
    )

    return run_bounded_text_process(*args, **kwargs)
