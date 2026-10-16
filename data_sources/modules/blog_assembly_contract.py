"""Shared strict helpers for blog assembly artifacts and deterministic JSON."""

from __future__ import annotations

import hashlib
import math
import os
import re
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any, Mapping

try:
    from .bounded_io import canonical_json_bytes as _canonical_json_bytes
    from .bounded_io import canonical_json_sha256 as _canonical_json_sha256
    from .bounded_io import parse_json as _parse_json
    from .bounded_io import stream_sha256 as _stream_sha256
    from .bounded_io import atomic_write_canonical_json as _atomic_write_canonical_json
    from .blog_sidecar_bindings import FRED_SELECTION_SECTION_RE as FRED_SELECTION_SECTION_RE
    from .blog_sidecar_bindings import SELECTOR_EVIDENCE_LINE_RE as SELECTOR_EVIDENCE_LINE_RE
except ImportError:  # pragma: no cover - supports direct script execution.
    from bounded_io import canonical_json_bytes as _canonical_json_bytes
    from bounded_io import canonical_json_sha256 as _canonical_json_sha256
    from bounded_io import parse_json as _parse_json
    from bounded_io import stream_sha256 as _stream_sha256
    from bounded_io import atomic_write_canonical_json as _atomic_write_canonical_json
    from blog_sidecar_bindings import FRED_SELECTION_SECTION_RE as FRED_SELECTION_SECTION_RE
    from blog_sidecar_bindings import SELECTOR_EVIDENCE_LINE_RE as SELECTOR_EVIDENCE_LINE_RE


SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
WINDOWS_DRIVE_RE = re.compile(r"^[A-Za-z]:")
PUBLIC_ARTICLE_DIRECTORIES = frozenset(
    {"drafts", "rewrites", "published", "review-required"}
)
DEFAULT_JSON_MAX_BYTES = 8 * 1024 * 1024


@dataclass(frozen=True, slots=True)
class ArtifactSnapshot:
    """One immutable read used for both a file digest and strict parsing."""

    path: Path
    data: bytes
    sha256: str
    payload: dict[str, Any]


def load_json_object_snapshot(
    path: str | Path,
    *,
    field: str,
    max_bytes: int = DEFAULT_JSON_MAX_BYTES,
) -> ArtifactSnapshot:
    """Read one bounded control-plane JSON object once and parse those exact bytes."""
    if not is_json_number(max_bytes) or not isinstance(max_bytes, int) or max_bytes <= 0:
        raise ValueError("max_bytes must be a positive integer")
    source = Path(path)
    try:
        with source.open("rb") as handle:
            data = handle.read(max_bytes + 1)
    except OSError as error:
        raise ValueError(f"{field} must be a readable JSON object: {error}") from error
    if len(data) > max_bytes:
        raise ValueError(f"{field} exceeds {max_bytes} bytes")
    try:
        text = data.decode("utf-8", errors="strict")
    except UnicodeDecodeError as error:
        raise ValueError(f"{field} must use valid UTF-8: {error}") from error
    payload = load_json_text(text, field=field)
    if not isinstance(payload, dict):
        raise ValueError(f"{field} must be a JSON object")
    return ArtifactSnapshot(
        path=source.resolve(),
        data=data,
        sha256=hashlib.sha256(data).hexdigest(),
        payload=payload,
    )


def load_json_text(text: str, *, field: str) -> Any:
    """Parse strict JSON already embedded in an immutable text artifact."""
    return _parse_json(text, field=field)


def is_json_number(value: Any) -> bool:
    """Return whether a value is a finite JSON number, explicitly excluding bool."""
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and (not isinstance(value, float) or math.isfinite(value))
    )


def current_utc_date() -> date:
    """Return today's date in UTC through a patchable workflow clock."""
    test_override = os.environ.get("SEOMACHINE_TEST_CURRENT_UTC_DATE")
    if test_override:
        return date.fromisoformat(test_override)
    return datetime.now(timezone.utc).date()


def file_sha256(path: str | Path) -> str:
    """Return the SHA-256 digest of the exact bytes on disk."""
    return _stream_sha256(path)


def canonical_json_bytes(payload: Mapping[str, Any]) -> bytes:
    """Serialize one JSON object exactly as the durable artifact writer does."""
    return _canonical_json_bytes(payload)


def canonical_json_sha256(payload: Mapping[str, Any]) -> str:
    """Return the SHA-256 digest of canonical durable JSON bytes."""
    return _canonical_json_sha256(payload)


def validate_sha256(value: Any, *, field: str = "sha256") -> str:
    """Return a valid canonical digest or raise a field-specific error."""
    if not isinstance(value, str) or not SHA256_RE.fullmatch(value):
        raise ValueError(f"{field} must be a 64-character lowercase SHA-256 digest")
    return value


def validate_governance_output_path(
    path: str | Path,
    *,
    inputs: Mapping[str, str | Path] | None = None,
) -> Path:
    """Keep Python-authored governance artifacts out of public article trees."""
    if not isinstance(path, (str, Path)) or not str(path).strip():
        raise ValueError("governance output path must be non-empty")
    destination = Path(path).resolve(strict=False)
    protected_parts = {
        part.casefold()
        for part in destination.parts
        if part.casefold() in PUBLIC_ARTICLE_DIRECTORIES
    }
    if protected_parts:
        names = ", ".join(sorted(protected_parts))
        raise ValueError(
            f"governance output cannot target a public article directory: {names}"
        )
    destination_identity = os.path.normcase(str(destination))
    for label, input_path in (inputs or {}).items():
        input_identity = os.path.normcase(str(Path(input_path).resolve(strict=False)))
        if destination_identity == input_identity:
            raise ValueError(f"governance output cannot overwrite input {label}")
    return destination


def canonical_artifact(
    path: str | Path,
    *,
    workspace_root: str | Path,
) -> dict[str, str]:
    """Snapshot one existing file with a workspace-relative POSIX identity."""
    root = Path(workspace_root).resolve()
    candidate = Path(path).resolve()
    if not candidate.is_file():
        raise ValueError(f"artifact is unavailable: {path}")
    if not _within(candidate, root):
        raise ValueError(f"artifact is outside workspace: {path}")
    relative = candidate.relative_to(root).as_posix()
    try:
        resolve_artifact(relative, workspace_root=root)
    except ValueError as error:
        raise ValueError(f"artifact path is not canonical: {path}") from error
    data = candidate.read_bytes()
    return canonical_artifact_identity(
        candidate,
        sha256=hashlib.sha256(data).hexdigest(),
        workspace_root=root,
    )


def canonical_snapshot_artifact(
    snapshot: ArtifactSnapshot,
    *,
    workspace_root: str | Path,
) -> dict[str, str]:
    """Create a BOM row from the exact immutable bytes that were parsed."""
    return canonical_artifact_identity(
        snapshot.path,
        sha256=snapshot.sha256,
        workspace_root=workspace_root,
    )


def canonical_artifact_identity(
    path: str | Path,
    *,
    sha256: str,
    workspace_root: str | Path,
) -> dict[str, str]:
    """Bind a previously observed digest to one canonical workspace path."""
    root = Path(workspace_root).resolve()
    candidate = Path(path).resolve()
    if not candidate.is_file() or not _within(candidate, root):
        raise ValueError(f"artifact is unavailable or outside workspace: {path}")
    relative = candidate.relative_to(root).as_posix()
    resolve_artifact(relative, workspace_root=root)
    return {
        "path": relative,
        "sha256": validate_sha256(sha256, field="artifact.sha256"),
    }


def resolve_artifact(
    stored_path: Any,
    *,
    workspace_root: str | Path,
) -> Path:
    """Resolve a declared workspace-relative POSIX path without allowing escape."""
    if not isinstance(stored_path, str) or not stored_path.strip():
        raise ValueError("artifact path must be a non-empty workspace-relative POSIX path")
    value = stored_path
    pure = PurePosixPath(value)
    raw_parts = value.split("/")
    if (
        value != value.strip()
        or any(character.isspace() for character in value)
        or "\\" in value
        or pure.is_absolute()
        or WINDOWS_DRIVE_RE.match(value)
        or value.startswith("//")
        or any(part in {"", ".", ".."} for part in raw_parts)
    ):
        raise ValueError("artifact path must be a canonical workspace-relative POSIX path")
    root = Path(workspace_root).resolve()
    if not _uses_existing_path_spelling(root, raw_parts):
        raise ValueError("artifact path must be a canonical workspace-relative POSIX path")
    candidate = root.joinpath(*pure.parts).resolve()
    if not _within(candidate, root):
        raise ValueError("artifact path resolves outside workspace")
    return candidate


def _uses_existing_path_spelling(root: Path, parts: list[str]) -> bool:
    """Reject case aliases when the filesystem resolves them to another name."""
    current = root
    for part in parts:
        try:
            entries = tuple(current.iterdir())
        except OSError:
            return True
        exact = next((entry for entry in entries if entry.name == part), None)
        if exact is not None:
            current = exact
            continue
        alias = next(
            (
                entry
                for entry in entries
                if os.path.normcase(entry.name) == os.path.normcase(part)
            ),
            None,
        )
        if alias is not None:
            return False
        return True
    return True


def verify_artifact(
    row: Any,
    *,
    workspace_root: str | Path,
    field: str,
) -> Path:
    """Validate one strict path/hash object against the current file bytes."""
    if not isinstance(row, Mapping):
        raise ValueError(f"{field} must be a path/hash object")
    expected = validate_sha256(row.get("sha256"), field=f"{field}.sha256")
    path = resolve_artifact(row.get("path"), workspace_root=workspace_root)
    if not path.is_file():
        raise ValueError(f"{field}.path is unavailable")
    if file_sha256(path) != expected:
        raise ValueError(f"{field}.sha256 does not match current file contents")
    return path


def atomic_write_json(path: str | Path, payload: Mapping[str, Any]) -> None:
    """Persist deterministic JSON atomically and durably in the target directory."""
    destination = validate_governance_output_path(path)
    _atomic_write_canonical_json(
        destination,
        payload,
        max_bytes=DEFAULT_JSON_MAX_BYTES,
        field="governance JSON",
    )


def _within(candidate: Path, root: Path) -> bool:
    candidate_identity = os.path.normcase(str(candidate))
    root_identity = os.path.normcase(str(root))
    try:
        return os.path.commonpath((candidate_identity, root_identity)) == root_identity
    except ValueError:
        return False
