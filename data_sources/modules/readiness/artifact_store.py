"""Instrumented, run-scoped artifact snapshots and derived-view caches."""

from __future__ import annotations

import hashlib
import threading
from collections.abc import Callable, Mapping
from pathlib import Path
from types import MappingProxyType
from typing import Any

from ..artifact_runtime.limits import (
    ARTIFACT_STORE_MAX_BYTES,
    JSON_MAX_BYTES,
    TEXT_MAX_BYTES,
)
from ..blog_assembly_contract import artifact_inventory_snapshots, load_json_text
from ..publishable_markdown import parse_publishable_markdown
from .artifact_io import (
    read_bounded as _read_bounded,
    resolve_input as _resolve_input,
    resolve_workspace_root as _resolve_workspace_root,
    stream_sha256 as _stream_sha256,
)
from .artifact_views import (
    ArtifactBytesView,
    ArtifactJsonView,
    ArtifactMarkdownView,
    ArtifactTextView,
    FileIdentity,
    freeze_mapping,
    thaw_value,
)
from .input_spec import ReadinessInputSpec
from .telemetry import ReadinessTelemetry

BoundedReader = Callable[..., bytes]
HashReader = Callable[[Path], str]


class _ArtifactRecord:
    """One exact source snapshot plus lazily derived immutable views."""

    __slots__ = (
        "bytes_view",
        "identity",
        "json_view",
        "lock",
        "markdown_view",
        "telemetry",
        "text_view",
    )

    def __init__(
        self,
        *,
        bytes_view: ArtifactBytesView,
        identity: FileIdentity,
        telemetry: ReadinessTelemetry | None,
    ) -> None:
        self.bytes_view = bytes_view
        self.identity = identity
        self.telemetry = telemetry
        self.text_view: ArtifactTextView | None = None
        self.json_view: ArtifactJsonView | None = None
        self.markdown_view: ArtifactMarkdownView | None = None
        self.lock = threading.RLock()

    def text(self, field: str) -> ArtifactTextView:
        with self.lock:
            is_json = self.bytes_view.path.suffix.casefold() == ".json"
            if self.text_view is None:
                try:
                    decoded = self.bytes_view.content.decode("utf-8", errors="strict")
                except UnicodeDecodeError as error:
                    raise ValueError(
                        f"readiness input {field} must use valid UTF-8: {error}"
                    ) from error
                view = ArtifactTextView(
                    path=self.bytes_view.path,
                    relative_path=self.bytes_view.relative_path,
                    sha256=self.bytes_view.sha256,
                    text=decoded,
                )
                if not is_json:
                    self.text_view = view
                return view
            return self.text_view

    def json(self, field: str) -> ArtifactJsonView:
        with self.lock:
            if self.json_view is None:
                parsed = load_json_text(self.text(field).text, field=field)
                if not isinstance(parsed, dict):
                    raise ValueError(f"readiness input {field} must be a JSON object")
                self.json_view = ArtifactJsonView(
                    path=self.bytes_view.path,
                    relative_path=self.bytes_view.relative_path,
                    sha256=self.bytes_view.sha256,
                    payload=freeze_mapping(parsed),
                )
                _increment(self.telemetry, "json_parses")
            return self.json_view

    def markdown(self, field: str) -> ArtifactMarkdownView:
        with self.lock:
            if self.markdown_view is None:
                document = parse_publishable_markdown(
                    self.bytes_view.path,
                    self.text(field).text,
                    sha256=self.bytes_view.sha256,
                )
                self.markdown_view = ArtifactMarkdownView.from_document(
                    document,
                    relative_path=self.bytes_view.relative_path,
                )
                _increment(self.telemetry, "markdown_parses")
            return self.markdown_view


class InstrumentedArtifactStore:
    """Capture artifacts once and share hash-bound views for one workflow."""

    __slots__ = ("_by_label", "_by_path", "_telemetry", "_workspace_root")

    def __init__(
        self,
        *,
        workspace_root: Path,
        by_label: Mapping[str, _ArtifactRecord],
        by_path: Mapping[Path, _ArtifactRecord],
        telemetry: ReadinessTelemetry | None,
    ) -> None:
        self._workspace_root = workspace_root
        self._by_label = MappingProxyType(dict(by_label))
        self._by_path = MappingProxyType(dict(by_path))
        self._telemetry = telemetry

    @classmethod
    def capture(
        cls,
        inputs: Mapping[str, str | Path | None] | ReadinessInputSpec,
        *,
        workspace_root: str | Path,
        telemetry: ReadinessTelemetry | None = None,
        reader: BoundedReader | None = None,
        aggregate_budget_bytes: int = ARTIFACT_STORE_MAX_BYTES,
    ) -> "InstrumentedArtifactStore":
        root = _resolve_workspace_root(workspace_root)
        spec = (
            inputs
            if isinstance(inputs, ReadinessInputSpec)
            else ReadinessInputSpec.from_mapping(inputs, workspace_root=root)
        )
        if spec.workspace_root != root:
            raise ValueError("readiness input spec workspace_root does not match capture")
        builder = _StoreBuilder(
            root,
            telemetry,
            reader or _read_bounded,
            aggregate_budget_bytes,
        )
        builder.bind_spec(spec)
        if spec.expand_bom_inventory:
            builder.bind_bom_inventory()
        store = builder.build()
        if telemetry is not None:
            telemetry.set_gauge("artifact_store_source_bytes", store.total_bytes)
        return store

    @property
    def workspace_root(self) -> Path:
        return self._workspace_root

    @property
    def unique_file_count(self) -> int:
        return len(self._by_path)

    @property
    def total_bytes(self) -> int:
        return sum(record.bytes_view.byte_count for record in self._by_path.values())

    @property
    def labels(self) -> tuple[str, ...]:
        return tuple(sorted(self._by_label))

    def bytes_view(self, label: str) -> ArtifactBytesView:
        return self._record(label).bytes_view

    def text_view(self, label: str) -> ArtifactTextView:
        return self._record(label).text(label)

    def json_view(self, label: str) -> ArtifactJsonView:
        return self._record(label).json(label)

    def markdown_view(self, label: str) -> ArtifactMarkdownView:
        return self._record(label).markdown(label)

    def file_identity(self, label: str) -> FileIdentity:
        return self._record(label).identity

    def bytes(self, label: str) -> bytes:
        return self.bytes_view(label).content

    def text(self, label: str) -> str:
        return self.text_view(label).text

    def json_object(self, label: str) -> Mapping[str, Any]:
        return self.json_view(label).payload

    def hash_inventory(self) -> dict[str, dict[str, str]]:
        return {
            label: {
                "path": self._by_label[label].bytes_view.relative_path,
                "sha256": self._by_label[label].bytes_view.sha256,
            }
            for label in sorted(key for key in self._by_label if not key.startswith("prior_preflight."))
        }

    def release_inventory(self) -> dict[str, dict[str, str | int]]:
        return {
            label: {
                "path": self._by_label[label].bytes_view.relative_path,
                "sha256": self._by_label[label].bytes_view.sha256,
                "bytes": self._by_label[label].bytes_view.byte_count,
            }
            for label in sorted(key for key in self._by_label if not key.startswith("prior_preflight."))
        }

    def reseal(
        self,
        *,
        hash_reader: HashReader | None = None,
    ) -> dict[str, dict[str, str | int]]:
        """Stream every unique artifact once and verify identity plus digest."""
        _increment(self._telemetry, "final_reseals")
        digest_reader = hash_reader or _stream_sha256
        records = sorted(
            self._by_path.items(),
            key=lambda item: item[1].bytes_view.relative_path,
        )
        for path, record in records:
            self._reseal_record(path, record, digest_reader)
        return self.release_inventory()

    def _record(self, label: str) -> _ArtifactRecord:
        try:
            return self._by_label[label]
        except KeyError as error:
            raise KeyError(f"unknown readiness input: {label}") from error

    def _reseal_record(
        self,
        path: Path,
        record: _ArtifactRecord,
        digest_reader: HashReader,
    ) -> None:
        try:
            before = FileIdentity.from_path(path)
            if before != record.identity:
                raise ValueError("identity changed")
            current = digest_reader(path)
            _increment(self._telemetry, "final_rehashes")
            after = FileIdentity.from_path(path)
        except (OSError, ValueError) as error:
            raise _changed_error(record, error) from error
        if after != before or current != record.bytes_view.sha256:
            raise _changed_error(record)


class _StoreBuilder:
    """Mutable construction scope hidden behind the immutable store."""

    __slots__ = (
        "aggregate_budget_bytes",
        "by_label",
        "by_path",
        "reader",
        "root",
        "source_bytes",
        "telemetry",
    )

    def __init__(
        self,
        root: Path,
        telemetry: ReadinessTelemetry | None,
        reader: BoundedReader,
        aggregate_budget_bytes: int,
    ) -> None:
        self.root = root
        self.telemetry = telemetry
        self.reader = reader
        if (
            isinstance(aggregate_budget_bytes, bool)
            or not isinstance(aggregate_budget_bytes, int)
            or aggregate_budget_bytes < 1
        ):
            raise ValueError("artifact aggregate budget must be a positive integer")
        self.aggregate_budget_bytes = aggregate_budget_bytes
        self.by_label: dict[str, _ArtifactRecord] = {}
        self.by_path: dict[Path, _ArtifactRecord] = {}
        self.source_bytes = 0

    def bind_spec(self, spec: ReadinessInputSpec) -> None:
        for binding in spec.bindings:
            self.bind(
                binding.label,
                binding.path,
                expected_sha256=binding.expected_sha256,
                expected_bytes=binding.expected_bytes,
            )

    def bind_bom_inventory(self) -> None:
        record = self.by_label.get("assembly_bom")
        if record is None:
            return
        payload = record.json("assembly_bom").payload
        artifacts = payload.get("artifacts")
        if not isinstance(artifacts, Mapping):
            raise ValueError("assembly_bom artifacts must be an object")
        snapshots = artifact_inventory_snapshots(thaw_value(artifacts))
        for label in sorted(snapshots):
            row = snapshots[label]
            self.bind(label, row["path"], expected_sha256=row["sha256"])
        self._bind_machine_reviews(payload.get("machine_reviews"))
        self._bind_serp_raw_capture()
        self._bind_paa_raw_capture()
        self._bind_historical(payload.get("preflight"), prefix="historical_preflight")
        prior = self.by_label.get("prior_preflight_readiness")
        if prior is not None:
            prior_inputs = prior.json("prior_preflight_readiness").payload.get("input_hashes")
            if isinstance(prior_inputs, Mapping):
                self._bind_historical_row("assembly_bom", prior_inputs.get("assembly_bom"), prefix="prior_preflight")

    def bind(
        self,
        label: str,
        raw_path: str | Path,
        *,
        expected_sha256: str | None = None,
        expected_bytes: int | None = None,
    ) -> None:
        _validate_label(label)
        path = _resolve_input(raw_path, workspace_root=self.root, field=label)
        record = self.by_path.get(path)
        if record is None:
            try:
                projected = self.source_bytes + path.stat().st_size
            except OSError as error:
                raise ValueError(f"readiness input {label} is unreadable: {error}") from error
            if projected > self.aggregate_budget_bytes:
                raise ValueError("artifact aggregate byte budget exceeded")
            record = _capture_record(
                path,
                workspace_root=self.root,
                field=label,
                telemetry=self.telemetry,
                reader=self.reader,
            )
            self.by_path[path] = record
            self.source_bytes = projected
            if self.telemetry is not None:
                self.telemetry.set_gauge("artifact_store_source_bytes", projected)
                self.telemetry.observe_peak(
                    "peak_artifact_store_source_bytes", projected
                )
        if expected_sha256 is not None and record.bytes_view.sha256 != expected_sha256:
            raise ValueError(
                f"readiness input {label} does not match its declared SHA-256"
            )
        if expected_bytes is not None and record.bytes_view.byte_count != expected_bytes:
            raise ValueError(
                f"readiness input {label} does not match its declared byte count"
            )
        previous = self.by_label.get(label)
        if previous is not None and previous.bytes_view.path != path:
            raise ValueError(f"duplicate readiness input label: {label}")
        self.by_label[label] = record

    def build(self) -> InstrumentedArtifactStore:
        return InstrumentedArtifactStore(
            workspace_root=self.root,
            by_label=self.by_label,
            by_path=self.by_path,
            telemetry=self.telemetry,
        )

    def _bind_historical(self, preflight: Any, *, prefix: str) -> None:
        if preflight is None:
            return
        if not isinstance(preflight, Mapping):
            raise ValueError("assembly_bom preflight must be an object")
        historical = preflight.get("input_hashes")
        if not isinstance(historical, Mapping) or not historical:
            raise ValueError("assembly_bom preflight input_hashes must be an object")
        for label in sorted(historical, key=str):
            self._bind_historical_row(label, historical[label], prefix=prefix)

    def _bind_serp_raw_capture(self) -> None:
        record = self.by_label.get("serp_evidence")
        if record is None:
            return
        raw_capture = record.json("serp_evidence").payload.get("raw_capture")
        if not isinstance(raw_capture, Mapping):
            return
        raw_path = raw_capture.get("path")
        sha256 = raw_capture.get("sha256")
        if isinstance(raw_path, str) and isinstance(sha256, str):
            self.bind("serp_raw_capture", raw_path, expected_sha256=sha256)

    def _bind_paa_raw_capture(self) -> None:
        record = self.by_label.get("paa_artifact")
        if record is None:
            return
        raw_capture = record.json("paa_artifact").payload.get("raw_capture")
        if not isinstance(raw_capture, Mapping):
            return
        raw_path = raw_capture.get("path")
        sha256 = raw_capture.get("sha256")
        if isinstance(raw_path, str) and isinstance(sha256, str):
            self.bind("paa_raw_capture", raw_path, expected_sha256=sha256)

    def _bind_machine_reviews(self, reviews: Any) -> None:
        if reviews is None:
            return
        if not isinstance(reviews, Mapping):
            raise ValueError("assembly_bom machine_reviews must be an object")
        for phase in sorted(reviews, key=str):
            row = reviews[phase]
            if not isinstance(row, Mapping) or set(row) != {"path", "sha256"}:
                raise ValueError(
                    f"assembly_bom machine_reviews.{phase} must contain path and sha256"
                )
            self.bind(
                f"machine_reviews.{phase}",
                str(row["path"]),
                expected_sha256=str(row["sha256"]),
            )

    def _bind_historical_row(self, label: Any, row: Any, *, prefix: str) -> None:
        if not isinstance(label, str) or not isinstance(row, Mapping):
            raise ValueError("assembly_bom preflight input hashes are invalid")
        if set(row) != {"path", "sha256"}:
            raise ValueError(
                f"assembly_bom preflight input {label} must contain path and sha256"
            )
        self.bind(
            f"{prefix}.{label}",
            str(row["path"]),
            expected_sha256=str(row["sha256"]),
        )


def _capture_record(
    path: Path,
    *,
    workspace_root: Path,
    field: str,
    telemetry: ReadinessTelemetry | None,
    reader: BoundedReader,
) -> _ArtifactRecord:
    max_bytes = JSON_MAX_BYTES if path.suffix.casefold() == ".json" else TEXT_MAX_BYTES
    try:
        before = FileIdentity.from_path(path)
        data = reader(path, max_bytes=max_bytes, field=field)
        after = FileIdentity.from_path(path)
    except OSError as error:
        raise ValueError(f"readiness input {field} is unreadable: {error}") from error
    if before != after or len(data) != after.byte_count:
        raise ValueError(f"readiness input {field} changed while it was captured")
    view = ArtifactBytesView(
        path=path,
        relative_path=path.relative_to(workspace_root).as_posix(),
        sha256=hashlib.sha256(data).hexdigest(),
        content=bytes(data),
    )
    _record_capture(telemetry, view.byte_count)
    return _ArtifactRecord(bytes_view=view, identity=after, telemetry=telemetry)


def _record_capture(telemetry: ReadinessTelemetry | None, byte_count: int) -> None:
    _increment(telemetry, "unique_file_reads")
    _increment(telemetry, "bytes_read", byte_count)
    _increment(telemetry, "file_hashes")
    _increment(telemetry, "byte_snapshots")


def _increment(
    telemetry: ReadinessTelemetry | None,
    counter: str,
    amount: int = 1,
) -> None:
    if telemetry is not None:
        telemetry.increment(counter, amount)


def _changed_error(record: _ArtifactRecord, cause: object | None = None) -> ValueError:
    detail = (
        f": {cause}"
        if cause is not None and str(cause) != "identity changed"
        else ""
    )
    return ValueError(
        "readiness input changed during readiness: "
        f"{record.bytes_view.relative_path}{detail}"
    )


def _validate_label(label: object) -> None:
    if not isinstance(label, str) or not label.strip():
        raise ValueError("readiness input labels must be non-empty strings")


__all__ = ["InstrumentedArtifactStore"]
