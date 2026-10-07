"""Atomic checkpoint store so an interrupted context build resumes without repeating work."""

from __future__ import annotations

import hashlib
import shutil
from pathlib import Path
from typing import Any

try:
    from ..bounded_io import atomic_write_canonical_json, parse_json_object, read_bounded
    from .spec import ContextBuildSpec
except ImportError:  # pragma: no cover - supports direct script execution.
    from bounded_io import atomic_write_canonical_json, parse_json_object, read_bounded
    from context_build.spec import ContextBuildSpec

CHECKPOINT_ROOT = Path(".seomachine") / "context-build"
MANIFEST_SCHEMA = "simpro-context-build-checkpoint-manifest/v1"
CHECKPOINT_MAX_BYTES = 16 * 1024 * 1024
MANIFEST_MAX_BYTES = 64 * 1024
RESUME_CHANGED_MESSAGE = "spec changed since the saved checkpoints; rerun without --resume"


class ContextBuildResumeError(ValueError):
    """Raised when saved checkpoints cannot be safely resumed."""


class CheckpointStore:
    """Per-spec checkpoint directory under .seomachine/context-build/<slug>/<date>/."""

    def __init__(self, workspace_root: Path, spec: ContextBuildSpec, *, resume: bool) -> None:
        self._directory = Path(workspace_root) / CHECKPOINT_ROOT / spec.slug / spec.date
        self._manifest = self._directory / "manifest.json"
        self._digest = spec.digest
        if not resume:
            shutil.rmtree(self._directory, ignore_errors=True)
        if resume and self._manifest.exists():
            self._verify_resume()
        elif resume and self._directory.exists() and any(self._directory.iterdir()):
            raise ContextBuildResumeError("checkpoint manifest is missing; rerun without --resume")
        else:
            self._write_manifest()

    def _verify_resume(self) -> None:
        try:
            stored = parse_json_object(
                read_bounded(self._manifest, max_bytes=MANIFEST_MAX_BYTES, field="checkpoint manifest"),
                field="checkpoint manifest",
            )
        except ValueError as error:
            raise ContextBuildResumeError(f"checkpoint manifest is unreadable: {error}") from error
        if stored.get("spec_digest") != self._digest:
            raise ContextBuildResumeError(RESUME_CHANGED_MESSAGE)

    def _write_manifest(self) -> None:
        atomic_write_canonical_json(
            self._manifest,
            {"schema": MANIFEST_SCHEMA, "spec_digest": self._digest},
            max_bytes=MANIFEST_MAX_BYTES,
            field="checkpoint manifest",
        )

    def _path(self, key: str) -> Path:
        return self._directory / f"{hashlib.sha256(key.encode('utf-8')).hexdigest()}.json"

    def get(self, key: str) -> Any | None:
        """Return the saved value for key, or None when no checkpoint exists."""
        path = self._path(key)
        if not path.exists():
            return None
        try:
            payload = parse_json_object(
                read_bounded(path, max_bytes=CHECKPOINT_MAX_BYTES, field=f"checkpoint {key}"),
                field=f"checkpoint {key}",
            )
        except ValueError as error:
            raise ContextBuildResumeError(f"checkpoint {key} is unreadable: {error}") from error
        if payload.get("key") != key:
            raise ContextBuildResumeError(f"checkpoint {key} does not match its stored key")
        return payload.get("value")

    def put(self, key: str, value: Any) -> None:
        """Atomically save value under key."""
        atomic_write_canonical_json(
            self._path(key),
            {"key": key, "value": value},
            max_bytes=CHECKPOINT_MAX_BYTES,
            field=f"checkpoint {key}",
        )
