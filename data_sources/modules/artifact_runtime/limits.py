"""Shared byte and encoding limits for workflow artifacts."""

from __future__ import annotations

from pathlib import Path


MIB = 1024 * 1024
ARTICLE_MAX_BYTES = MIB
SIDECAR_MAX_BYTES = MIB
TEXT_MAX_BYTES = MIB
JSON_MAX_BYTES = 8 * MIB
SUBPROCESS_SPOOL_THRESHOLD_BYTES = MIB
SUBPROCESS_MAX_OUTPUT_BYTES = 32 * MIB


def validate_text_artifact(
    path: str | Path,
    *,
    label: str,
    workspace_root: str | Path,
    max_bytes: int,
) -> Path:
    """Validate one bounded UTF-8 file and return its canonical path."""
    if not isinstance(path, (str, Path)) or not str(path).strip():
        raise ValueError(f"{label} path is required")
    if not isinstance(max_bytes, int) or isinstance(max_bytes, bool) or max_bytes < 1:
        raise ValueError("max_bytes must be a positive integer")
    root = Path(workspace_root).resolve()
    candidate = Path(path)
    if not candidate.is_absolute():
        candidate = root / candidate
    try:
        resolved = candidate.resolve(strict=True)
        resolved.relative_to(root)
    except FileNotFoundError as error:
        raise ValueError(f"{label} is unreadable: {path}") from error
    except ValueError as error:
        raise ValueError(f"{label} must stay inside the workspace") from error
    if not resolved.is_file():
        raise ValueError(f"{label} is unreadable: {path}")
    with resolved.open("rb") as handle:
        content = handle.read(max_bytes + 1)
    if len(content) > max_bytes:
        raise ValueError(f"{label} exceeds {max_bytes} bytes")
    try:
        content.decode("utf-8")
    except UnicodeDecodeError as error:
        raise ValueError(f"{label} must contain valid UTF-8") from error
    return resolved
