"""Content-free pytest worker metrics."""

from __future__ import annotations

import json
import os
import re
import tempfile
from pathlib import Path

from data_sources.modules.resource_metrics import process_peak_rss_bytes


SCHEMA = "simpro-test-worker-metrics/v2"
_IDENTITY_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}")


def write_worker_metrics(
    output_dir: str | Path,
    *,
    run_id: str,
    worker_id: str,
    elapsed_ms: float,
    collected: int,
    executed: int = 0,
    exit_status: int,
    peak_rss_bytes: int | None,
) -> Path:
    """Atomically persist one worker's numeric session metrics."""
    _validate_identity(run_id, field_name="run_id")
    _validate_identity(worker_id, field_name="worker_id")
    process_id = os.getpid()
    destination = Path(output_dir) / f"{run_id}-{worker_id}-{process_id}.json"
    destination.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema": SCHEMA,
        "run_id": run_id,
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
def _validate_identity(value: str, *, field_name: str) -> None:
    if not isinstance(value, str) or _IDENTITY_PATTERN.fullmatch(value) is None:
        raise ValueError(f"{field_name} must be a safe non-empty identifier")
