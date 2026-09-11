"""Bounded immutable snapshots for one publish-readiness execution."""

from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Any, Mapping

from ..blog_assembly_contract import artifact_inventory_snapshots, load_json_text
from ..artifact_runtime.limits import JSON_MAX_BYTES, TEXT_MAX_BYTES
from .telemetry import ReadinessTelemetry

HASH_CHUNK_BYTES = 1024 * 1024


@dataclass(frozen=True, slots=True)
class InputSnapshot:
    """One exact file read shared by every label that references the path."""

    path: Path
    relative_path: str
    sha256: str
    byte_count: int
    text: str | None
    json_payload: Mapping[str, Any] | None


class ReadinessInputs:
    """Immutable artifact inventory captured once and resealed once."""

    __slots__ = ("_by_label", "_by_path", "_telemetry", "_workspace_root")

    def __init__(
        self,
        *,
        workspace_root: Path,
        by_label: Mapping[str, InputSnapshot],
        by_path: Mapping[Path, InputSnapshot],
        telemetry: ReadinessTelemetry | None,
    ) -> None:
        self._workspace_root = workspace_root
        self._by_label = MappingProxyType(dict(by_label))
        self._by_path = MappingProxyType(dict(by_path))
        self._telemetry = telemetry

    @classmethod
    def capture(
        cls,
        inputs: Mapping[str, str | Path | None],
        *,
        workspace_root: str | Path,
        telemetry: ReadinessTelemetry | None = None,
    ) -> "ReadinessInputs":
        root = _resolve_workspace_root(workspace_root)
        builder = _CaptureBuilder(root, telemetry)
        builder.bind_direct(inputs)
        builder.bind_bom_inventory()
        return builder.build()

    @property
    def workspace_root(self) -> Path:
        return self._workspace_root

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

    def text(self, label: str) -> str:
        value = self.snapshot(label).text
        if value is None:
            raise ValueError(f"readiness input {label} is parsed JSON, not text")
        return value

    def json_object(self, label: str) -> Mapping[str, Any]:
        snapshot = self.snapshot(label)
        if snapshot.json_payload is None:
            raise ValueError(f"readiness input {label} is not a JSON object")
        return snapshot.json_payload

    def hash_inventory(self) -> dict[str, dict[str, str]]:
        return {
            label: {
                "path": snapshot.relative_path,
                "sha256": snapshot.sha256,
            }
            for label, snapshot in self._by_label.items()
        }

    def release_inventory(self) -> dict[str, dict[str, str | int]]:
        """Return path, exact digest, and byte count for release authorization."""
        return {
            label: {
                "path": snapshot.relative_path,
                "sha256": snapshot.sha256,
                "bytes": snapshot.byte_count,
            }
            for label, snapshot in self._by_label.items()
        }

    def reseal(self) -> None:
        """Hash each unique bound path once and reject any mutation."""
        for path, snapshot in self._by_path.items():
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


class _CaptureBuilder:
    """Mutable construction scope that never escapes a captured inventory."""

    __slots__ = ("by_label", "by_path", "root", "telemetry")

    def __init__(self, root: Path, telemetry: ReadinessTelemetry | None) -> None:
        self.root = root
        self.telemetry = telemetry
        self.by_label: dict[str, InputSnapshot] = {}
        self.by_path: dict[Path, InputSnapshot] = {}

    def bind_direct(self, inputs: Mapping[str, str | Path | None]) -> None:
        for label, raw_path in inputs.items():
            if raw_path is not None:
                self.bind(label, raw_path)

    def bind_bom_inventory(self) -> None:
        bom_snapshot = self.by_label.get("assembly_bom")
        if bom_snapshot is None:
            return
        payload = bom_snapshot.json_payload
        if payload is None:
            raise ValueError("assembly_bom must be a JSON object")
        artifacts = payload.get("artifacts")
        if not isinstance(artifacts, Mapping):
            raise ValueError("assembly_bom artifacts must be an object")
        for label, row in artifact_inventory_snapshots(_thaw_json(artifacts)).items():
            self.bind(label, row["path"], expected_sha256=row["sha256"])
        self._bind_historical(payload.get("preflight"))

    def bind(
        self,
        label: str,
        raw_path: str | Path,
        *,
        expected_sha256: str | None = None,
    ) -> None:
        if not isinstance(label, str) or not label.strip():
            raise ValueError("readiness input labels must be non-empty strings")
        path = _resolve_input(raw_path, workspace_root=self.root, field=label)
        snapshot = self.by_path.get(path)
        if snapshot is None:
            snapshot = _capture_path(path, workspace_root=self.root, field=label)
            self.by_path[path] = snapshot
            self._record_capture(snapshot)
        if expected_sha256 is not None and snapshot.sha256 != expected_sha256:
            raise ValueError(f"readiness input {label} does not match its declared SHA-256")
        previous = self.by_label.get(label)
        if previous is not None and previous.path != snapshot.path:
            raise ValueError(f"duplicate readiness input label: {label}")
        self.by_label[label] = snapshot

    def build(self) -> ReadinessInputs:
        return ReadinessInputs(
            workspace_root=self.root,
            by_label=self.by_label,
            by_path=self.by_path,
            telemetry=self.telemetry,
        )

    def _bind_historical(self, preflight: Any) -> None:
        if preflight is None:
            return
        if not isinstance(preflight, Mapping):
            raise ValueError("assembly_bom preflight must be an object")
        historical = preflight.get("input_hashes")
        if not isinstance(historical, Mapping) or not historical:
            raise ValueError("assembly_bom preflight input_hashes must be an object")
        for label, row in historical.items():
            self._bind_historical_row(label, row)

    def _bind_historical_row(self, label: Any, row: Any) -> None:
        if not isinstance(label, str) or not isinstance(row, Mapping):
            raise ValueError("assembly_bom preflight input hashes are invalid")
        if set(row) != {"path", "sha256"}:
            raise ValueError(
                f"assembly_bom preflight input {label} must contain path and sha256"
            )
        self.bind(
            f"historical_preflight.{label}",
            str(row["path"]),
            expected_sha256=str(row["sha256"]),
        )

    def _record_capture(self, snapshot: InputSnapshot) -> None:
        if self.telemetry is None:
            return
        self.telemetry.increment("unique_file_reads")
        self.telemetry.increment("bytes_read", snapshot.byte_count)
        self.telemetry.increment("file_hashes")


def _capture_path(path: Path, *, workspace_root: Path, field: str) -> InputSnapshot:
    max_bytes = JSON_MAX_BYTES if path.suffix.casefold() == ".json" else TEXT_MAX_BYTES
    data = _read_bounded(path, max_bytes=max_bytes, field=field)
    try:
        text = data.decode("utf-8", errors="strict")
    except UnicodeDecodeError as error:
        raise ValueError(f"readiness input {field} must use valid UTF-8: {error}") from error
    payload: Mapping[str, Any] | None = None
    retained_text: str | None = text
    if path.suffix.casefold() == ".json":
        parsed = load_json_text(text, field=field)
        if not isinstance(parsed, dict):
            raise ValueError(f"readiness input {field} must be a JSON object")
        payload = _freeze_json(parsed)
        retained_text = None
    return InputSnapshot(
        path=path,
        relative_path=path.relative_to(workspace_root).as_posix(),
        sha256=hashlib.sha256(data).hexdigest(),
        byte_count=len(data),
        text=retained_text,
        json_payload=payload,
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


def _freeze_json(value: Any) -> Any:
    if isinstance(value, dict):
        return MappingProxyType({key: _freeze_json(item) for key, item in value.items()})
    if isinstance(value, list):
        return tuple(_freeze_json(item) for item in value)
    return value


def _thaw_json(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {key: _thaw_json(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_thaw_json(item) for item in value]
    return value


def _resolve_workspace_root(value: str | Path) -> Path:
    try:
        root = Path(value).resolve(strict=True)
    except OSError as error:
        raise ValueError(f"workspace_root is unavailable: {error}") from error
    if not root.is_dir():
        raise ValueError("workspace_root must be a directory")
    return root


def _resolve_input(value: str | Path, *, workspace_root: Path, field: str) -> Path:
    if not isinstance(value, (str, Path)) or not str(value).strip():
        raise ValueError(f"readiness input {field} path is required")
    candidate = Path(value)
    if not candidate.is_absolute():
        candidate = workspace_root / candidate
    try:
        candidate = candidate.resolve(strict=True)
    except OSError as error:
        raise ValueError(f"readiness input {field} is unavailable: {error}") from error
    try:
        common = os.path.commonpath((str(workspace_root), str(candidate)))
    except ValueError as error:
        raise ValueError(f"readiness input {field} is outside workspace") from error
    if os.path.normcase(common) != os.path.normcase(str(workspace_root)):
        raise ValueError(f"readiness input {field} is outside workspace")
    if not candidate.is_file():
        raise ValueError(f"readiness input {field} must be a file")
    return candidate
