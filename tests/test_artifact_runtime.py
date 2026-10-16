from __future__ import annotations

import sys
import os
import subprocess
import time
from pathlib import Path

import pytest

from data_sources.modules.artifact_runtime.limits import SUBPROCESS_MAX_INPUT_BYTES
from data_sources.modules.artifact_runtime.paths import cache_path, spool_path
from data_sources.modules.artifact_runtime.subprocesses import (
    ProcessCleanupError,
    SubprocessOutputLimitError,
    run_bounded_process,
    run_bounded_text_process,
)
from data_sources.modules.bounded_io import (
    JsonOutputLimitError,
    bounded_canonical_json_bytes,
)


def test_bounded_process_keeps_small_output_in_memory() -> None:
    with run_bounded_process(
        [sys.executable, "-c", "import sys;sys.stdout.write('ok');sys.stderr.write('note')"],
        timeout=10,
        spool_threshold_bytes=128,
        max_output_bytes=1024,
    ) as completed:
        assert completed.returncode == 0
        assert completed.stdout.read_text() == "ok"
        assert completed.stderr.read_text() == "note"
        assert completed.stdout.spooled_to_disk is False
        assert completed.stderr.spooled_to_disk is False


def test_bounded_canonical_json_stops_at_declared_limit() -> None:
    assert bounded_canonical_json_bytes({"ok": True}, max_bytes=32) == (
        b'{\n  "ok": true\n}\n'
    )
    with pytest.raises(JsonOutputLimitError, match="exceeds 8 bytes"):
        bounded_canonical_json_bytes({"value": "x" * 100}, max_bytes=8)


def test_bounded_text_process_materializes_and_closes_streams() -> None:
    completed = run_bounded_text_process(
        [sys.executable, "-c", "import sys;print('ok');print('note', file=sys.stderr)"],
        timeout=5,
        max_output_bytes=1024,
    )

    assert completed.returncode == 0
    assert completed.stdout.splitlines() == ["ok"]
    assert completed.stderr.splitlines() == ["note"]


def test_bounded_process_supplies_bounded_stdin_bytes(tmp_path: Path) -> None:
    payload = b"bounded input\x00with binary bytes"

    with run_bounded_process(
        [sys.executable, "-c", "import sys;sys.stdout.buffer.write(sys.stdin.buffer.read())"],
        timeout=10,
        input_bytes=payload,
        spool_threshold_bytes=128,
        max_output_bytes=1024,
        spool_dir=tmp_path,
    ) as completed:
        assert completed.returncode == 0
        assert completed.stdout.read_bytes() == payload

    assert list(tmp_path.iterdir()) == []


def test_bounded_process_rejects_oversized_stdin_bytes(tmp_path: Path) -> None:
    with pytest.raises(
        ValueError,
        match=f"input_bytes exceeds {SUBPROCESS_MAX_INPUT_BYTES} bytes",
    ):
        run_bounded_process(
            [sys.executable, "-c", "pass"],
            timeout=10,
            input_bytes=b"x" * (SUBPROCESS_MAX_INPUT_BYTES + 1),
            spool_threshold_bytes=128,
            max_output_bytes=1024,
            spool_dir=tmp_path,
        )

    assert list(tmp_path.iterdir()) == []


def test_bounded_process_spools_large_output_without_losing_bytes() -> None:
    payload_size = 4096
    with run_bounded_process(
        [sys.executable, "-c", f"import sys;sys.stdout.write('x'*{payload_size})"],
        timeout=10,
        spool_threshold_bytes=128,
        max_output_bytes=8192,
    ) as completed:
        assert completed.stdout.byte_count == payload_size
        assert completed.stdout.spooled_to_disk is True
        assert completed.stdout.read_text() == "x" * payload_size


def test_bounded_process_fails_instead_of_truncating_oversized_output() -> None:
    with pytest.raises(SubprocessOutputLimitError, match="stdout exceeded 1024 bytes"):
        run_bounded_process(
            [sys.executable, "-c", "import sys;sys.stdout.write('x'*4096)"],
            timeout=10,
            spool_threshold_bytes=128,
            max_output_bytes=1024,
        )


def test_runtime_paths_use_injected_worker_root(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runtime = tmp_path / "worker-gw1"
    monkeypatch.setenv("SEOMACHINE_RUNTIME_ROOT", str(runtime))

    assert cache_path("public_http", "v1") == runtime / "cache" / "public_http" / "v1"
    assert spool_path() == runtime / "spool" / "v1"


def test_bounded_process_timeout_includes_cleanup_budget() -> None:
    started = time.monotonic()

    with pytest.raises(subprocess.TimeoutExpired):
        run_bounded_process(
            [sys.executable, "-c", "import time; time.sleep(30)"],
            timeout=0.2,
            spool_threshold_bytes=128,
            max_output_bytes=1024,
        )

    assert time.monotonic() - started < 2.5


def test_process_cleanup_error_is_a_stable_runtime_error() -> None:
    assert issubclass(ProcessCleanupError, RuntimeError)


def test_timeout_terminates_grandchild_holding_inherited_pipes(tmp_path: Path) -> None:
    pid_path = tmp_path / "grandchild.pid"
    script = (
        "import pathlib,subprocess,sys,time;"
        "child=subprocess.Popen([sys.executable,'-c','import time;time.sleep(30)']);"
        "pathlib.Path(sys.argv[1]).write_text(str(child.pid),encoding='utf-8');"
        "time.sleep(30)"
    )

    with pytest.raises(subprocess.TimeoutExpired):
        run_bounded_process(
            [sys.executable, "-c", script, str(pid_path)],
            timeout=0.5,
            spool_threshold_bytes=128,
            max_output_bytes=1024,
            spool_dir=tmp_path / "spool",
        )

    grandchild_pid = int(pid_path.read_text(encoding="utf-8"))
    time.sleep(0.05)
    with pytest.raises(OSError):
        os.kill(grandchild_pid, 0)
    assert list((tmp_path / "spool").iterdir()) == []
