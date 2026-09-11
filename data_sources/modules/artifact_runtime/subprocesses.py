"""Bounded subprocess execution with disk-backed output spooling."""

from __future__ import annotations

import subprocess
import tempfile
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO, Mapping, Sequence

from .limits import (
    SUBPROCESS_MAX_OUTPUT_BYTES,
    SUBPROCESS_SPOOL_THRESHOLD_BYTES,
)
from .paths import spool_path


READ_CHUNK_BYTES = 64 * 1024
TERMINATE_GRACE_SECONDS = 1.0


class SubprocessOutputLimitError(RuntimeError):
    """Raised when a child emits more output than the configured hard limit."""


class CapturedStream:
    """A seekable subprocess stream that spills from memory to a temporary file."""

    def __init__(self, handle: BinaryIO, byte_count: int, *, encoding: str) -> None:
        self._handle = handle
        self.byte_count = byte_count
        self.encoding = encoding
        self.spooled_to_disk = bool(getattr(handle, "_rolled", False))

    def read_bytes(self, *, max_bytes: int | None = None) -> bytes:
        if max_bytes is not None and self.byte_count > max_bytes:
            raise SubprocessOutputLimitError(
                f"captured stream exceeds materialization limit of {max_bytes} bytes"
            )
        self._handle.seek(0)
        return self._handle.read()

    def read_text(self, *, max_bytes: int | None = None) -> str:
        return self.read_bytes(max_bytes=max_bytes).decode(self.encoding)

    def close(self) -> None:
        self._handle.close()


@dataclass
class BoundedCompletedProcess:
    """Completed child process whose captured streams must be closed."""

    args: tuple[str, ...]
    returncode: int
    stdout: CapturedStream
    stderr: CapturedStream

    def close(self) -> None:
        self.stdout.close()
        self.stderr.close()

    def __enter__(self) -> BoundedCompletedProcess:
        return self

    def __exit__(self, *unused: object) -> None:
        self.close()


class _StreamCollector:
    def __init__(
        self,
        source: BinaryIO,
        *,
        name: str,
        spool_threshold_bytes: int,
        max_output_bytes: int,
        spool_dir: Path,
    ) -> None:
        self.source = source
        self.name = name
        self.max_output_bytes = max_output_bytes
        self.handle = tempfile.SpooledTemporaryFile(
            max_size=spool_threshold_bytes,
            mode="w+b",
            dir=spool_dir,
        )
        self.byte_count = 0
        self.overflow = threading.Event()
        self.thread = threading.Thread(target=self._collect, daemon=True)

    def _collect(self) -> None:
        try:
            while chunk := self.source.read(READ_CHUNK_BYTES):
                self.byte_count += len(chunk)
                if self.byte_count <= self.max_output_bytes:
                    self.handle.write(chunk)
                else:
                    self.overflow.set()
        finally:
            self.source.close()

    def start(self) -> None:
        self.thread.start()

    def join(self) -> None:
        self.thread.join()

    def captured(self, *, encoding: str) -> CapturedStream:
        self.handle.flush()
        return CapturedStream(self.handle, self.byte_count, encoding=encoding)

    def close(self) -> None:
        self.handle.close()


def run_bounded_process(
    args: Sequence[str],
    *,
    timeout: float,
    cwd: str | Path | None = None,
    env: Mapping[str, str] | None = None,
    encoding: str = "utf-8",
    spool_threshold_bytes: int = SUBPROCESS_SPOOL_THRESHOLD_BYTES,
    max_output_bytes: int = SUBPROCESS_MAX_OUTPUT_BYTES,
    spool_dir: str | Path | None = None,
) -> BoundedCompletedProcess:
    """Run a child without shell expansion and capture both streams within limits."""
    command = _validate_arguments(
        args,
        timeout=timeout,
        spool_threshold_bytes=spool_threshold_bytes,
        max_output_bytes=max_output_bytes,
    )
    resolved_spool_dir = Path(spool_dir) if spool_dir is not None else spool_path()
    resolved_spool_dir.mkdir(parents=True, exist_ok=True)
    process = subprocess.Popen(
        command,
        cwd=cwd,
        env=dict(env) if env is not None else None,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        shell=False,
    )
    if process.stdout is None or process.stderr is None:  # pragma: no cover
        process.kill()
        raise RuntimeError("subprocess pipes were not created")
    collectors = (
        _StreamCollector(
            process.stdout,
            name="stdout",
            spool_threshold_bytes=spool_threshold_bytes,
            max_output_bytes=max_output_bytes,
            spool_dir=resolved_spool_dir,
        ),
        _StreamCollector(
            process.stderr,
            name="stderr",
            spool_threshold_bytes=spool_threshold_bytes,
            max_output_bytes=max_output_bytes,
            spool_dir=resolved_spool_dir,
        ),
    )
    for collector in collectors:
        collector.start()
    try:
        _wait_for_process(process, collectors, timeout=timeout, args=command)
        for collector in collectors:
            collector.join()
        overflow = next((item for item in collectors if item.overflow.is_set()), None)
        if overflow is not None:
            raise SubprocessOutputLimitError(
                f"{overflow.name} exceeded {max_output_bytes} bytes"
            )
        return BoundedCompletedProcess(
            args=command,
            returncode=int(process.returncode),
            stdout=collectors[0].captured(encoding=encoding),
            stderr=collectors[1].captured(encoding=encoding),
        )
    except BaseException:
        _stop_process(process)
        for collector in collectors:
            collector.join()
            collector.close()
        raise


def _wait_for_process(
    process: subprocess.Popen[bytes],
    collectors: tuple[_StreamCollector, _StreamCollector],
    *,
    timeout: float,
    args: tuple[str, ...],
) -> None:
    deadline = time.monotonic() + timeout
    while process.poll() is None:
        if any(collector.overflow.is_set() for collector in collectors):
            _stop_process(process)
            return
        if time.monotonic() >= deadline:
            _stop_process(process)
            raise subprocess.TimeoutExpired(args, timeout)
        time.sleep(0.01)


def _stop_process(process: subprocess.Popen[bytes]) -> None:
    if process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=TERMINATE_GRACE_SECONDS)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait()


def _validate_arguments(
    args: Sequence[str],
    *,
    timeout: float,
    spool_threshold_bytes: int,
    max_output_bytes: int,
) -> tuple[str, ...]:
    command = tuple(args)
    if not command or not all(isinstance(value, str) and value for value in command):
        raise ValueError("args must contain non-empty strings")
    if timeout <= 0:
        raise ValueError("timeout must be positive")
    if spool_threshold_bytes < 1 or max_output_bytes < spool_threshold_bytes:
        raise ValueError("output limits are invalid")
    return command
