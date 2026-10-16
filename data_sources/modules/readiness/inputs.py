"""Compatibility facade over the session-owned artifact store."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Any, Mapping

from .artifact_io import HASH_CHUNK_BYTES
from ..artifact_runtime.limits import ARTIFACT_STORE_MAX_BYTES
from .artifact_store import InstrumentedArtifactStore
from .input_spec import ReadinessInputSpec
from .telemetry import ReadinessTelemetry


@dataclass(frozen=True, slots=True)
class InputSnapshot:
    """Legacy immutable projection with lazy text and JSON compatibility views."""

    path: Path
    relative_path: str
    sha256: str
    byte_count: int
    _store: InstrumentedArtifactStore | None = None
    _label: str = ""

    @property
    def text(self) -> str | None:
        if self._store is None or self.path.suffix.casefold() == ".json":
            return None
        return self._store.text(self._label)

    @property
    def json_payload(self) -> Mapping[str, Any] | None:
        if self._store is None or self.path.suffix.casefold() != ".json":
            return None
        return self._store.json_object(self._label)


class ReadinessInputs:
    """Stable gate-facing API backed by one instrumented artifact store."""

    __slots__ = (
        "_by_label",
        "_by_path",
        "_store",
        "_telemetry",
        "_workspace_root",
    )

    def __init__(
        self,
        *,
        workspace_root: Path,
        by_label: Mapping[str, InputSnapshot],
        by_path: Mapping[Path, InputSnapshot],
        telemetry: ReadinessTelemetry | None,
        store: InstrumentedArtifactStore,
    ) -> None:
        self._workspace_root = workspace_root
        self._by_label = MappingProxyType(dict(by_label))
        self._by_path = MappingProxyType(dict(by_path))
        self._telemetry = telemetry
        self._store = store

    @classmethod
    def capture(
        cls,
        inputs: Mapping[str, str | Path | None] | ReadinessInputSpec,
        *,
        workspace_root: str | Path,
        telemetry: ReadinessTelemetry | None = None,
        aggregate_budget_bytes: int = ARTIFACT_STORE_MAX_BYTES,
    ) -> "ReadinessInputs":
        store = InstrumentedArtifactStore.capture(
            inputs,
            workspace_root=workspace_root,
            telemetry=telemetry,
            reader=_read_bounded,
            aggregate_budget_bytes=aggregate_budget_bytes,
        )
        return cls.from_store(store, telemetry=telemetry)

    @classmethod
    def from_store(
        cls,
        store: InstrumentedArtifactStore,
        *,
        telemetry: ReadinessTelemetry | None = None,
    ) -> "ReadinessInputs":
        by_path: dict[Path, InputSnapshot] = {}
        by_label: dict[str, InputSnapshot] = {}
        for label in store.labels:
            byte_view = store.bytes_view(label)
            snapshot = by_path.get(byte_view.path)
            if snapshot is None:
                snapshot = InputSnapshot(
                    path=byte_view.path,
                    relative_path=byte_view.relative_path,
                    sha256=byte_view.sha256,
                    byte_count=byte_view.byte_count,
                    _store=store,
                    _label=label,
                )
                by_path[byte_view.path] = snapshot
            by_label[label] = snapshot
        return cls(
            workspace_root=store.workspace_root,
            by_label=by_label,
            by_path=by_path,
            telemetry=telemetry,
            store=store,
        )

    @property
    def workspace_root(self) -> Path:
        return self._workspace_root

    @property
    def artifacts(self) -> InstrumentedArtifactStore:
        return self._store

    @property
    def unique_file_count(self) -> int:
        return len(self._by_path)

    @property
    def total_bytes(self) -> int:
        return sum(snapshot.byte_count for snapshot in self._by_path.values())

    def snapshot(self, label: str) -> InputSnapshot:
        try:
            return self._by_label[label]
        except KeyError as error:
            raise KeyError(f"unknown readiness input: {label}") from error

    def optional_snapshot(self, label: str) -> InputSnapshot | None:
        return self._by_label.get(label)

    def bytes(self, label: str) -> bytes:
        return self.artifacts.bytes(label)

    def text(self, label: str) -> str:
        value = self.snapshot(label).text
        if value is None:
            raise ValueError(f"readiness input {label} is parsed JSON, not text")
        return value

    def json_object(self, label: str) -> Mapping[str, Any]:
        payload = self.snapshot(label).json_payload
        if payload is None:
            raise ValueError(f"readiness input {label} is not a JSON object")
        return payload

    def hash_inventory(self) -> dict[str, dict[str, str]]:
        return self._store.hash_inventory()

    def reseal(self) -> None:
        """Re-verify every captured artifact's identity and digest."""
        self._store.reseal(hash_reader=_stream_sha256)


def _read_bounded(path: Path, *, max_bytes: int, field: str) -> bytes:
    try:
        with path.open("rb") as handle:
            data = handle.read(max_bytes + 1)
    except OSError as error:
        raise ValueError(f"readiness input {field} is unreadable: {error}") from error
    if len(data) > max_bytes:
        raise ValueError(f"readiness input {field} exceeds {max_bytes} bytes")
    return data


def _stream_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(HASH_CHUNK_BYTES):
            digest.update(chunk)
    return digest.hexdigest()


__all__ = ["InputSnapshot", "ReadinessInputs"]
