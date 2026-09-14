"""Best-effort peak resident-memory measurement for the current process."""

from __future__ import annotations

import os
import subprocess
import time
from typing import Any


def process_peak_rss_bytes() -> int | None:
    """Return peak resident bytes when the platform exposes the measurement."""
    if os.name == "nt":
        return _windows_peak_rss_bytes()
    try:
        import resource

        value = int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
        return value if os.uname().sysname == "Darwin" else value * 1024
    except (AttributeError, ImportError, OSError, TypeError, ValueError):
        return None


def process_rss_bytes(process_id: int) -> int | None:
    """Return the current resident bytes for one process when available."""
    if isinstance(process_id, bool) or not isinstance(process_id, int) or process_id < 1:
        raise ValueError("process_id must be a positive integer")
    if os.name == "nt":
        return _windows_process_rss_bytes(process_id)
    try:
        status = open(f"/proc/{process_id}/status", encoding="ascii")
        with status:
            for line in status:
                if line.startswith("VmRSS:"):
                    return int(line.split()[1]) * 1024
    except (OSError, IndexError, ValueError):
        return None
    return None


def _windows_process_rss_bytes(process_id: int) -> int | None:
    try:
        import ctypes

        handle = ctypes.windll.kernel32.OpenProcess(0x0400 | 0x0010, False, process_id)
        if not handle:
            return None
        try:
            return _windows_process_peak_rss(handle) or None
        finally:
            ctypes.windll.kernel32.CloseHandle(handle)
    except (AttributeError, OSError, TypeError, ValueError):
        return None


def _windows_peak_rss_bytes() -> int | None:
    try:
        import ctypes
        from ctypes import wintypes

        class ProcessMemoryCounters(ctypes.Structure):
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

        counters = ProcessMemoryCounters()
        counters.cb = ctypes.sizeof(counters)
        current_process = ctypes.windll.kernel32.GetCurrentProcess()
        succeeded = ctypes.windll.psapi.GetProcessMemoryInfo(
            current_process,
            ctypes.byref(counters),
            counters.cb,
        )
        return int(counters.PeakWorkingSetSize) if succeeded else None
    except (AttributeError, OSError, TypeError, ValueError):
        return None


def wait_with_peak_rss(
    process: subprocess.Popen[Any],
    *,
    poll_interval_seconds: float = 0.005,
) -> int | None:
    """Wait for a child and return its observed peak RSS on Windows."""
    if os.name != "nt":
        process.wait()
        return None
    try:
        import ctypes

        handle = ctypes.windll.kernel32.OpenProcess(
            0x0400 | 0x0010,
            False,
            process.pid,
        )
        if not handle:
            process.wait()
            return None
        peak = 0
        try:
            while process.poll() is None:
                peak = max(peak, _windows_process_peak_rss(handle))
                time.sleep(poll_interval_seconds)
            peak = max(peak, _windows_process_peak_rss(handle))
        finally:
            ctypes.windll.kernel32.CloseHandle(handle)
        return peak or None
    except (AttributeError, OSError, TypeError, ValueError):
        process.wait()
        return None


def _windows_process_peak_rss(handle: int) -> int:
    try:
        import ctypes
        from ctypes import wintypes

        class ProcessMemoryCounters(ctypes.Structure):
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

        counters = ProcessMemoryCounters()
        counters.cb = ctypes.sizeof(counters)
        succeeded = ctypes.windll.psapi.GetProcessMemoryInfo(
            handle,
            ctypes.byref(counters),
            counters.cb,
        )
        return int(counters.PeakWorkingSetSize) if succeeded else 0
    except (AttributeError, OSError, TypeError, ValueError):
        return 0


__all__ = ["process_peak_rss_bytes", "process_rss_bytes", "wait_with_peak_rss"]
