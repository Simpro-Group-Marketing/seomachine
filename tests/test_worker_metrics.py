from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from types import SimpleNamespace

from tests import conftest as suite_config
from tests.worker_metrics import process_peak_rss_bytes, write_worker_metrics


def test_worker_metrics_are_atomic_and_content_free(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setattr("tests.worker_metrics.os.getpid", lambda: 4321)
    destination = write_worker_metrics(
        tmp_path,
        worker_id="gw2",
        elapsed_ms=12.5,
        collected=40,
        executed=11,
        exit_status=0,
        peak_rss_bytes=1234,
    )

    payload = json.loads(destination.read_text(encoding="utf-8"))
    assert destination.name == "gw2-4321.json"
    assert payload == {
        "schema": "simpro-test-worker-metrics/v1",
        "worker_id": "gw2",
        "elapsed_ms": 12.5,
        "collected": 40,
        "executed": 11,
        "exit_status": 0,
        "peak_rss_bytes": 1234,
        "process_id": 4321,
    }
    assert not list(tmp_path.glob("*.tmp"))


def test_peak_rss_is_available_on_supported_workers() -> None:
    peak = process_peak_rss_bytes()

    if os.name in {"nt", "posix"}:
        assert isinstance(peak, int)
        assert peak > 0


def test_default_basetemp_is_short_and_process_scoped() -> None:
    config = SimpleNamespace(option=SimpleNamespace(basetemp=None))

    suite_config.pytest_configure(config)
    destination = Path(config.option.basetemp)

    assert destination.parent == Path(tempfile.gettempdir())
    assert destination.name.startswith("sm-pytest-")
    assert not destination.is_relative_to(Path(__file__).resolve().parents[1])
