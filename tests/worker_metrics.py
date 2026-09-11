"""Content-free pytest worker metrics."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path


SCHEMA = "simpro-test-worker-metrics/v1"


def write_worker_metrics(
    output_dir: str | Path,
    *,
    worker_id: str,
    elapsed_ms: float,
    collected: int,
    executed: int = 0,
    exit_status: int,
    peak_rss_bytes: int | None,
) -> Path:
    """Atomically persist one worker's numeric session metrics."""
    process_id = os.getpid()
    destination = Path(output_dir) / f"{worker_id}-{process_id}.json"
    destination.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema": SCHEMA,
        "worker_id": worker_id,
        "elapsed_ms": round(max(0.0, elapsed_ms), 3),
        "collected": int(collected),
        "executed": int(executed),
        "exit_status": int(exit_status),
        "peak_rss_bytes": peak_rss_bytes,
        "process_id": process_id,
    }
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
            json.dump(payload, handle, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, destination)
        temporary = None
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    return destination


def process_peak_rss_bytes() -> int | None:
    """Return dependency-free peak RSS where the standard library exposes it."""
    if os.name == "nt":
        return _windows_peak_rss_bytes()
    try:
        import resource
    except ImportError:
        return None
    peak = int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    if os.name == "posix" and not sys_platform_is_macos():
        return peak * 1024
    return peak


def _windows_peak_rss_bytes() -> int | None:
    import ctypes
    from ctypes import wintypes

    class _ProcessMemoryCounters(ctypes.Structure):
        _fields_ = (
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
        )

    counters = _ProcessMemoryCounters()
    counters.cb = ctypes.sizeof(counters)
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    psapi = ctypes.WinDLL("psapi", use_last_error=True)
    get_current_process = kernel32.GetCurrentProcess
    get_current_process.argtypes = ()
    get_current_process.restype = wintypes.HANDLE
    get_process_memory_info = psapi.GetProcessMemoryInfo
    get_process_memory_info.argtypes = (
        wintypes.HANDLE,
        ctypes.POINTER(_ProcessMemoryCounters),
        wintypes.DWORD,
    )
    get_process_memory_info.restype = wintypes.BOOL
    success = get_process_memory_info(
        get_current_process(),
        ctypes.byref(counters),
        counters.cb,
    )
    return int(counters.PeakWorkingSetSize) if success else None


def sys_platform_is_macos() -> bool:
    import sys

    return sys.platform == "darwin"
