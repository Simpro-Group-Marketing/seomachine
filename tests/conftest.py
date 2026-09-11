"""Worker-safe runtime isolation and optional test-process metrics."""

from __future__ import annotations

import os
import tempfile
import time
from pathlib import Path

import pytest

from tests.worker_metrics import process_peak_rss_bytes, write_worker_metrics


ROOT = Path(__file__).resolve().parents[1]
_SESSION_STARTED_NS = 0
_TESTS_EXECUTED = 0


def pytest_configure(config: pytest.Config) -> None:
    if config.option.basetemp is None:
        parent = Path(tempfile.gettempdir())
        config.option.basetemp = str(parent / f"sm-pytest-{os.getpid()}")


def pytest_sessionstart(session: pytest.Session) -> None:
    global _SESSION_STARTED_NS
    _SESSION_STARTED_NS = time.perf_counter_ns()


def pytest_sessionfinish(session: pytest.Session, exitstatus: int) -> None:
    output = os.getenv("SEOMACHINE_WORKER_METRICS_DIR")
    if not output:
        return
    if getattr(session.config.option, "numprocesses", 0) and not hasattr(
        session.config,
        "workerinput",
    ):
        return
    worker_id = _worker_id(session.config)
    elapsed_ms = (time.perf_counter_ns() - _SESSION_STARTED_NS) / 1_000_000
    write_worker_metrics(
        output,
        worker_id=worker_id,
        elapsed_ms=elapsed_ms,
        collected=session.testscollected,
        executed=_TESTS_EXECUTED,
        exit_status=exitstatus,
        peak_rss_bytes=process_peak_rss_bytes(),
    )


def pytest_runtest_logreport(report: pytest.TestReport) -> None:
    global _TESTS_EXECUTED
    if report.when == "call":
        _TESTS_EXECUTED += 1


@pytest.fixture(scope="session", autouse=True)
def isolated_runtime_root(
    request: pytest.FixtureRequest,
    tmp_path_factory: pytest.TempPathFactory,
):
    """Keep caches and spools distinct across pytest worker processes."""
    runtime = tmp_path_factory.getbasetemp() / "runtime" / _worker_id(request.config)
    runtime.mkdir(parents=True, exist_ok=True)
    previous = os.environ.get("SEOMACHINE_RUNTIME_ROOT")
    os.environ["SEOMACHINE_RUNTIME_ROOT"] = str(runtime)
    try:
        yield runtime
    finally:
        if previous is None:
            os.environ.pop("SEOMACHINE_RUNTIME_ROOT", None)
        else:
            os.environ["SEOMACHINE_RUNTIME_ROOT"] = previous


def _worker_id(config: pytest.Config) -> str:
    worker_input = getattr(config, "workerinput", None)
    if isinstance(worker_input, dict):
        value = worker_input.get("workerid")
        if isinstance(value, str) and value:
            return value
    return "controller"
