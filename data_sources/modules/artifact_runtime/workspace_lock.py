"""Shared cross-process locking for context objects and retention mutations."""

from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from filelock import FileLock, Timeout


LOCK_TIMEOUT_SECONDS = 30.0


@contextmanager
def artifact_workspace_lock(
    workspace_root: str | Path,
    *,
    timeout: float = LOCK_TIMEOUT_SECONDS,
) -> Iterator[None]:
    """Serialize writes that can change context-object reachability."""
    root = Path(workspace_root).resolve(strict=True)
    if not root.is_dir():
        raise ValueError("workspace_root must be an existing directory")
    lock_path = root / ".seomachine" / "locks" / "artifact-retention.lock"
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    lock = FileLock(str(lock_path), timeout=timeout)
    try:
        with lock:
            yield
    except Timeout as error:
        raise RuntimeError("artifact workspace lock acquisition timed out") from error
