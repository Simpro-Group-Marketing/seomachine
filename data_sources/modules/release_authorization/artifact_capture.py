"""Alias-aware physical capture for final release-manifest inputs."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

from ..readiness.artifact_store import InstrumentedArtifactStore
from ..readiness.input_spec import ReadinessInputSpec
from .contracts import SealedArtifact


def capture_manifest_inputs(
    value: Any,
    *,
    root: Path,
) -> dict[str, SealedArtifact]:
    """Capture each physical input once while preserving all logical labels."""
    if not isinstance(value, Mapping):
        raise ValueError("release manifest inputs must be an object")
    spec = ReadinessInputSpec.from_release_inventory(value, workspace_root=root)
    store = InstrumentedArtifactStore.capture(spec, workspace_root=root)
    artifacts: dict[str, SealedArtifact] = {}
    for label in store.labels:
        view = store.bytes_view(label)
        if view.path.suffix.casefold() == ".json":
            store.json_object(label)
        else:
            store.text(label)
        artifacts[label] = SealedArtifact(
            label=label,
            path=view.path,
            relative_path=view.relative_path,
            data=view.content,
            sha256=view.sha256,
            byte_count=view.byte_count,
            file_identity=store.file_identity(label).as_tuple(),
        )
    return artifacts


__all__ = ["capture_manifest_inputs"]
