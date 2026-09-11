"""Immutable contracts for a verified final release bundle."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Any, Callable, Mapping, TypeVar

from ..artifact_runtime.limits import JSON_MAX_BYTES, TEXT_MAX_BYTES


RELEASE_MANIFEST_SCHEMA = "simpro-release-manifest/v1"
FINAL_READINESS_SCHEMA = "simpro-publish-readiness-result/v2"
_T = TypeVar("_T")


@dataclass(frozen=True, slots=True)
class SealedArtifact:
    """One exact bounded artifact from the authorized release inventory."""

    label: str
    path: Path
    relative_path: str
    data: bytes
    sha256: str
    byte_count: int
    file_identity: tuple[int, int, int, int, int]


@dataclass(frozen=True, slots=True)
class PublishAuthorization:
    """A verified final bundle that can reseal inputs before one mutation."""

    workspace_root: Path
    run_id: str
    artifact_kind: str
    artifacts: Mapping[str, SealedArtifact]
    manifest_path: Path
    manifest_sha256: str
    manifest_identity: tuple[int, int, int, int, int]
    readiness_path: Path
    readiness_sha256: str
    readiness_identity: tuple[int, int, int, int, int]
    receipt_path: Path
    receipt_sha256: str
    receipt_identity: tuple[int, int, int, int, int]

    def with_final_input_seal(
        self,
        callback: Callable[[bytes, Mapping[str, str]], _T],
    ) -> _T:
        """Reseal every authorized file, then synchronously invoke ``callback``."""
        if not callable(callback):
            raise TypeError("mutation_callback must be callable")
        _verify_file(
            self.manifest_path, self.manifest_sha256, self.manifest_identity,
            JSON_MAX_BYTES, "release manifest",
        )
        _verify_file(
            self.readiness_path, self.readiness_sha256, self.readiness_identity,
            JSON_MAX_BYTES, "readiness output",
        )
        _verify_file(
            self.receipt_path, self.receipt_sha256, self.receipt_identity,
            JSON_MAX_BYTES, "readiness receipt",
        )
        current: dict[str, str] = {}
        verified_paths: dict[Path, bytes] = {}
        for label, artifact in self.artifacts.items():
            limit = JSON_MAX_BYTES if artifact.path.suffix.casefold() == ".json" else TEXT_MAX_BYTES
            data = verified_paths.get(artifact.path)
            if data is None:
                data = _verify_file(
                    artifact.path,
                    artifact.sha256,
                    artifact.file_identity,
                    limit,
                    label,
                )
                verified_paths[artifact.path] = data
            if len(data) != artifact.byte_count:
                raise ValueError(f"authorized input {label} byte count changed")
            current[label] = artifact.sha256
        article = self.artifacts.get("article")
        if article is None:
            raise ValueError("release authorization is missing the article")
        return callback(article.data, MappingProxyType(current))


def _verify_file(
    path: Path,
    expected: str,
    identity: tuple[int, int, int, int, int],
    limit: int,
    label: str,
) -> bytes:
    try:
        before = _file_identity(path)
        with path.open("rb") as handle:
            data = handle.read(limit + 1)
        after = _file_identity(path)
    except OSError as error:
        raise ValueError(f"authorized {label} is unreadable: {error}") from error
    if len(data) > limit:
        raise ValueError(f"authorized {label} exceeds {limit} bytes")
    if before != identity or after != identity:
        raise ValueError(f"authorized {label} changed since authorization")
    if not hashlib.sha256(data).hexdigest() == expected:
        raise ValueError(f"authorized {label} sha256 changed")
    return data


def _file_identity(path: Path) -> tuple[int, int, int, int, int]:
    stat = path.stat()
    return (stat.st_dev, stat.st_ino, stat.st_size, stat.st_mtime_ns, stat.st_ctime_ns)


def freeze_artifacts(
    artifacts: Mapping[str, SealedArtifact],
) -> Mapping[str, SealedArtifact]:
    return MappingProxyType(dict(artifacts))
