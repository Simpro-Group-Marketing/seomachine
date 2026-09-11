"""Deadline-bounded process-tree execution with disk-backed output spooling."""

from __future__ import annotations

import math
import subprocess
import tempfile
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO, Mapping, Sequence

from .limits import SUBPROCESS_MAX_OUTPUT_BYTES, SUBPROCESS_SPOOL_THRESHOLD_BYTES
from .paths import spool_path
from .process_tree import ProcessTreeController, create_process_tree_controller


READ_CHUNK_BYTES = 64 * 1024
TERMINATE_GRACE_SECONDS = 1.0
SOFT_TERMINATE_SECONDS = 0.2


class SubprocessOutputLimitError(RuntimeError):
    """Raised when a child emits more output than the configured hard limit."""


class ProcessCleanupError(RuntimeError):
    """Raised when a process tree or collector cannot be conclusively stopped."""


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

    def __enter__(self) -> "BoundedCompletedProcess":
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
        self.failure: BaseException | None = None
        self.thread = threading.Thread(target=self._collect, daemon=True)

    def _collect(self) -> None:
        try:
            while chunk := self.source.read(READ_CHUNK_BYTES):
                self.byte_count += len(chunk)
                if self.byte_count <= self.max_output_bytes:
                    self.handle.write(chunk)
                else:
                    self.overflow.set()
        except BaseException as error:
            self.failure = error
        finally:
            try:
                self.source.close()
            except OSError:
                pass

    def start(self) -> None:
        self.thread.start()

    def join(self, timeout: float) -> bool:
        self.thread.join(max(0.0, timeout))
        return not self.thread.is_alive()

    def captured(self, *, encoding: str) -> CapturedStream:
        self.handle.flush()
        return CapturedStream(self.handle, self.byte_count, encoding=encoding)

    def close_source(self) -> None:
        try:
            self.source.close()
        except OSError:
            pass

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
    """Run a complete child tree and capture both streams within hard limits."""
    command = _validate_arguments(
        args,
        timeout=timeout,
        spool_threshold_bytes=spool_threshold_bytes,
        max_output_bytes=max_output_bytes,
    )
    resolved_spool_dir = Path(spool_dir) if spool_dir is not None else spool_path()
    resolved_spool_dir.mkdir(parents=True, exist_ok=True)
    deadline = time.monotonic() + timeout
    controller = create_process_tree_controller()
    process: subprocess.Popen[bytes] | None = None
    collectors: tuple[_StreamCollector, _StreamCollector] = ()
    try:
        process = subprocess.Popen(
            command,
            cwd=cwd,
            env=dict(env) if env is not None else None,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=False,
            **controller.popen_options(),
        )
        controller.attach(process)
        if process.stdout is None or process.stderr is None:  # pragma: no cover
            raise ProcessCleanupError("subprocess pipes were not created")
        collectors = _start_collectors(
            process,
            spool_threshold_bytes=spool_threshold_bytes,
            max_output_bytes=max_output_bytes,
            spool_dir=resolved_spool_dir,
        )
        _wait_for_completion(
            process,
            collectors,
            deadline=deadline,
            timeout=timeout,
            args=command,
            max_output_bytes=max_output_bytes,
        )
        result = BoundedCompletedProcess(
            args=command,
            returncode=int(process.returncode),
            stdout=collectors[0].captured(encoding=encoding),
            stderr=collectors[1].captured(encoding=encoding),
        )
        controller.close()
        return result
    except BaseException as original:
        cleanup_error = _cleanup(
            process,
            collectors,
            controller=controller,
            deadline=max(deadline, time.monotonic()) + TERMINATE_GRACE_SECONDS,
        )
        for collector in collectors:
            collector.close()
        if cleanup_error is not None:
            raise ProcessCleanupError(cleanup_error) from original
        raise


def _start_collectors(
    process: subprocess.Popen[bytes],
    *,
    spool_threshold_bytes: int,
    max_output_bytes: int,
    spool_dir: Path,
) -> tuple[_StreamCollector, _StreamCollector]:
    assert process.stdout is not None and process.stderr is not None
    collectors = tuple(
        _StreamCollector(
            source,
            name=name,
            spool_threshold_bytes=spool_threshold_bytes,
            max_output_bytes=max_output_bytes,
            spool_dir=spool_dir,
        )
        for source, name in ((process.stdout, "stdout"), (process.stderr, "stderr"))
    )
    for collector in collectors:
        collector.start()
    return collectors  # type: ignore[return-value]


def _wait_for_completion(
    process: subprocess.Popen[bytes],
    collectors: tuple[_StreamCollector, _StreamCollector],
    *,
    deadline: float,
    timeout: float,
    args: tuple[str, ...],
    max_output_bytes: int,
) -> None:
    while process.poll() is None:
        _raise_collector_problem(collectors, max_output_bytes=max_output_bytes)
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise subprocess.TimeoutExpired(args, timeout)
        time.sleep(min(0.01, remaining))
    for collector in collectors:
        remaining = deadline - time.monotonic()
        if remaining <= 0 or not collector.join(remaining):
            raise subprocess.TimeoutExpired(args, timeout)
    _raise_collector_problem(collectors, max_output_bytes=max_output_bytes)


def _raise_collector_problem(
    collectors: tuple[_StreamCollector, _StreamCollector],
    *,
    max_output_bytes: int,
) -> None:
    overflow = next((item for item in collectors if item.overflow.is_set()), None)
    if overflow is not None:
        raise SubprocessOutputLimitError(
            f"{overflow.name} exceeded {max_output_bytes} bytes"
        )
    failure = next((item for item in collectors if item.failure is not None), None)
    if failure is not None:
        raise RuntimeError(f"{failure.name} collector failed") from failure.failure


def _cleanup(
    process: subprocess.Popen[bytes] | None,
    collectors: tuple[_StreamCollector, _StreamCollector],
    *,
    controller: ProcessTreeController,
    deadline: float,
) -> str | None:
    errors: list[str] = []
    if process is not None:
        errors.extend(_terminate_process(process, controller=controller, deadline=deadline))
    for collector in collectors:
        remaining = deadline - time.monotonic()
        if remaining <= 0 or not collector.join(remaining):
            collector.close_source()
    for collector in collectors:
        remaining = deadline - time.monotonic()
        if collector.thread.is_alive() and (
            remaining <= 0 or not collector.join(remaining)
        ):
            errors.append(f"{collector.name} collector did not exit")
    try:
        controller.close()
    except Exception as error:
        errors.append(f"process controller close failed: {error}")
    return "; ".join(errors) if errors else None


def _terminate_process(
    process: subprocess.Popen[bytes],
    *,
    controller: ProcessTreeController,
    deadline: float,
) -> list[str]:
    errors: list[str] = []
    try:
        controller.terminate(process)
    except Exception as error:
        errors.append(f"tree termination failed: {error}")
    _wait_direct_child(process, min(deadline, time.monotonic() + SOFT_TERMINATE_SECONDS))
    try:
        controller.kill(process)
    except Exception as error:
        errors.append(f"tree kill failed: {error}")
    _wait_direct_child(process, deadline)
    if process.poll() is None:
        try:
            process.kill()
            process.wait(timeout=max(0.01, deadline - time.monotonic()))
        except Exception as error:
            errors.append(f"direct child cleanup failed: {error}")
    return errors


def _wait_direct_child(process: subprocess.Popen[bytes], deadline: float) -> None:
    if process.poll() is not None:
        return
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        return
    try:
        process.wait(timeout=remaining)
    except subprocess.TimeoutExpired:
        return


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
    if not math.isfinite(timeout) or timeout <= 0:
        raise ValueError("timeout must be finite and positive")
    if spool_threshold_bytes < 1 or max_output_bytes < spool_threshold_bytes:
        raise ValueError("output limits are invalid")
    return command
