"""Compatibility facade over the session-owned artifact store."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Any, Mapping

from .artifact_io import HASH_CHUNK_BYTES
from .artifact_store import InstrumentedArtifactStore
from .artifact_views import ArtifactMarkdownView, thaw_value
from .telemetry import ReadinessTelemetry


@dataclass(frozen=True, slots=True)
class InputSnapshot:
    """Legacy immutable projection of one stored artifact."""

    path: Path
    relative_path: str
    sha256: str
    byte_count: int
    text: str | None
    json_payload: Mapping[str, Any] | None


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
        store: InstrumentedArtifactStore | None = None,
    ) -> None:
        self._workspace_root = workspace_root
        self._by_label = MappingProxyType(dict(by_label))
        self._by_path = MappingProxyType(dict(by_path))
        self._telemetry = telemetry
        self._store = store

    @classmethod
    def capture(
        cls,
        inputs: Mapping[str, str | Path | None],
        *,
        workspace_root: str | Path,
        telemetry: ReadinessTelemetry | None = None,
    ) -> "ReadinessInputs":
        store = InstrumentedArtifactStore.capture(
            inputs,
            workspace_root=workspace_root,
            telemetry=telemetry,
            reader=_read_bounded,
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
                is_json = byte_view.path.suffix.casefold() == ".json"
                snapshot = InputSnapshot(
                    path=byte_view.path,
                    relative_path=byte_view.relative_path,
                    sha256=byte_view.sha256,
                    byte_count=byte_view.byte_count,
                    text=None if is_json else store.text(label),
                    json_payload=store.json_object(label) if is_json else None,
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
        if self._store is None:
            raise RuntimeError("legacy ReadinessInputs has no artifact store")
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

    def snapshot_row(self, row: Any, *, field: str) -> InputSnapshot:
        """Resolve a strict path/hash row to its already captured snapshot."""
        if not isinstance(row, Mapping) or set(row) != {"path", "sha256"}:
            raise ValueError(f"{field} must be a path/hash object")
        relative_path = row.get("path")
        expected_sha256 = row.get("sha256")
        if not isinstance(relative_path, str) or not relative_path:
            raise ValueError(f"{field}.path is invalid")
        matches = (
            snapshot
            for snapshot in self._by_path.values()
            if snapshot.relative_path == relative_path
        )
        snapshot = next(matches, None)
        if snapshot is None:
            raise ValueError(f"{field}.path was not captured")
        if snapshot.sha256 != expected_sha256:
            raise ValueError(f"{field}.sha256 does not match captured contents")
        return snapshot

    def json_row(self, row: Any, *, field: str) -> Mapping[str, Any]:
        """Return one deeply immutable JSON object selected by a BOM row."""
        payload = self.snapshot_row(row, field=field).json_payload
        if payload is None:
            raise ValueError(f"{field} is not a JSON object")
        return payload

    def json_row_copy(self, row: Any, *, field: str) -> dict[str, Any]:
        """Return a defensive mutable projection for legacy validators."""
        value = thaw_value(self.json_row(row, field=field))
        if not isinstance(value, dict):  # pragma: no cover - guarded above.
            raise ValueError(f"{field} is not a JSON object")
        return value

    def text_row(self, row: Any, *, field: str) -> str:
        """Return strict UTF-8 text selected by a BOM row."""
        snapshot = self.snapshot_row(row, field=field)
        value = snapshot.text
        if value is None:
            label = next(
                label
                for label, candidate in self._by_label.items()
                if candidate is snapshot
            )
            return self.artifacts.text(label)
        return value

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

    def markdown_view(self, label: str) -> ArtifactMarkdownView:
        return self.artifacts.markdown_view(label)

    def hash_inventory(self) -> dict[str, dict[str, str]]:
        if self._store is not None:
            return self._store.hash_inventory()
        return {
            label: {
                "path": self._by_label[label].relative_path,
                "sha256": self._by_label[label].sha256,
            }
            for label in sorted(self._by_label)
        }

    def release_inventory(self) -> dict[str, dict[str, str | int]]:
        if self._store is not None:
            return self._store.release_inventory()
        return {
            label: {
                "path": self._by_label[label].relative_path,
                "sha256": self._by_label[label].sha256,
                "bytes": self._by_label[label].byte_count,
            }
            for label in sorted(self._by_label)
        }

    def reseal(self) -> None:
        """Preserve the legacy no-return API while using the stronger seal."""
        if self._store is not None:
            self._store.reseal(hash_reader=_stream_sha256)
            return
        for path, snapshot in sorted(
            self._by_path.items(), key=lambda item: item[1].relative_path
        ):
            try:
                current = _stream_sha256(path)
                if self._telemetry is not None:
                    self._telemetry.increment("final_rehashes")
            except OSError as error:
                raise ValueError(
                    f"readiness input changed during readiness: {snapshot.relative_path}: {error}"
                ) from error
            if current != snapshot.sha256:
                raise ValueError(
                    f"readiness input changed during readiness: {snapshot.relative_path}"
                )


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
