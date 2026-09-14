"""Portable current and peak resident-memory measurements."""

from __future__ import annotations

import ctypes
import os
import subprocess
import time
from ctypes import wintypes
from functools import lru_cache
from typing import Any


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


PROCESS_QUERY_INFORMATION = 0x0400
PROCESS_VM_READ = 0x0010


def process_peak_rss_bytes() -> int | None:
    """Return peak resident bytes where the platform exposes the measurement."""
    if os.name == "nt":
        try:
            api = _windows_api()
            return _windows_info(api, api.GetCurrentProcess())[0]
        except (AttributeError, OSError, TypeError, ValueError):
            return None
    try:
        import resource

        value = int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
        return value if os.uname().sysname == "Darwin" else value * 1024
    except (AttributeError, ImportError, OSError, TypeError, ValueError):
        return None


def process_rss_bytes(process_id: int) -> int | None:
    """Return current resident bytes for one process when available."""
    if isinstance(process_id, bool) or not isinstance(process_id, int) or process_id < 1:
        raise ValueError("process_id must be a positive integer")
    if os.name == "nt":
        try:
            api = _windows_api()
            handle = api.OpenProcess(
                PROCESS_QUERY_INFORMATION | PROCESS_VM_READ,
                False,
                process_id,
            )
            if not handle:
                return None
            try:
                return _windows_info(api, handle)[1]
            finally:
                api.CloseHandle(handle)
        except (AttributeError, OSError, TypeError, ValueError):
            return None
    try:
        with open(f"/proc/{process_id}/status", encoding="ascii") as status:
            for line in status:
                if line.startswith("VmRSS:"):
                    return int(line.split()[1]) * 1024
    except (OSError, IndexError, ValueError):
        return None
    return None


def wait_with_peak_rss(
    process: subprocess.Popen[Any],
    *,
    poll_interval_seconds: float = 0.005,
) -> int | None:
    """Wait for a child and return its maximum observed resident bytes."""
    if os.name != "nt":
        process.wait()
        return None
    peak = 0
    try:
        while process.poll() is None:
            current = process_rss_bytes(process.pid)
            if current is not None:
                peak = max(peak, current)
            time.sleep(poll_interval_seconds)
        process.wait()
        current = process_rss_bytes(process.pid)
        if current is not None:
            peak = max(peak, current)
    except (OSError, TypeError, ValueError):
        process.wait()
        return peak or None
    return peak or None


@lru_cache(maxsize=1)
def _windows_api() -> Any:
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    psapi = ctypes.WinDLL("psapi", use_last_error=True)
    open_process = kernel32.OpenProcess
    open_process.argtypes = (wintypes.DWORD, wintypes.BOOL, wintypes.DWORD)
    open_process.restype = wintypes.HANDLE
    close_handle = kernel32.CloseHandle
    close_handle.argtypes = (wintypes.HANDLE,)
    close_handle.restype = wintypes.BOOL
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
    return type(
        "_WindowsApi",
        (),
        {
            "OpenProcess": open_process,
            "CloseHandle": close_handle,
            "GetCurrentProcess": get_current_process,
            "GetProcessMemoryInfo": get_process_memory_info,
        },
    )()


def _windows_info(api: Any, handle: Any) -> tuple[int, int]:
    counters = _ProcessMemoryCounters()
    counters.cb = ctypes.sizeof(counters)
    succeeded = api.GetProcessMemoryInfo(
        handle,
        ctypes.byref(counters),
        counters.cb,
    )
    if not succeeded:
        raise OSError("GetProcessMemoryInfo failed")
    return int(counters.PeakWorkingSetSize), int(counters.WorkingSetSize)


__all__ = ["process_peak_rss_bytes", "process_rss_bytes", "wait_with_peak_rss"]
