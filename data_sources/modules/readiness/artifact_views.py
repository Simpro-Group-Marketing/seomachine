"""Immutable representations derived from one captured artifact."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Any, Mapping

from ..publishable_markdown import PublishableMarkdown, normalize_key


@dataclass(frozen=True, slots=True)
class FileIdentity:
    """Filesystem identity used to detect replacement and in-flight mutation."""

    device: int
    inode: int
    byte_count: int
    modified_ns: int
    changed_ns: int

    @classmethod
    def from_path(cls, path: Path) -> "FileIdentity":
        stat = path.stat()
        return cls(
            device=int(stat.st_dev),
            inode=int(stat.st_ino),
            byte_count=int(stat.st_size),
            modified_ns=int(stat.st_mtime_ns),
            changed_ns=int(stat.st_ctime_ns),
        )

    def as_tuple(self) -> tuple[int, int, int, int, int]:
        return (
            self.device,
            self.inode,
            self.byte_count,
            self.modified_ns,
            self.changed_ns,
        )


@dataclass(frozen=True, slots=True)
class ArtifactBytesView:
    """Exact source bytes and their canonical capture metadata."""

    path: Path
    relative_path: str
    sha256: str
    content: bytes

    @property
    def byte_count(self) -> int:
        return len(self.content)


@dataclass(frozen=True, slots=True)
class ArtifactTextView:
    """Strict UTF-8 text decoded from an exact byte snapshot."""

    path: Path
    relative_path: str
    sha256: str
    text: str


@dataclass(frozen=True, slots=True)
class ArtifactJsonView:
    """Deeply immutable strict JSON object."""

    path: Path
    relative_path: str
    sha256: str
    payload: Mapping[str, Any]


@dataclass(frozen=True, slots=True)
class ArtifactMarkdownView:
    """Deeply immutable publishable-Markdown parse."""

    path: Path
    relative_path: str
    sha256: str
    raw: str
    metadata: Mapping[str, Any]
    h1: str
    body: str

    @classmethod
    def from_document(
        cls,
        document: PublishableMarkdown,
        *,
        relative_path: str,
    ) -> "ArtifactMarkdownView":
        return cls(
            path=document.path,
            relative_path=relative_path,
            sha256=document.sha256,
            raw=document.raw,
            metadata=freeze_mapping(document.metadata),
            h1=document.h1,
            body=document.body,
        )

    def scalar(self, *keys: str) -> str:
        """Return the first non-empty metadata value as a scalar string."""
        for key in keys:
            value = self.metadata.get(normalize_key(key))
            if isinstance(value, (list, tuple)):
                if value:
                    return ", ".join(str(item) for item in value)
            elif value is not None and str(value).strip():
                return str(value).strip()
        return ""

    def values(self, *keys: str) -> list[str]:
        """Return the first non-empty metadata value as a detached string list."""
        for key in keys:
            value = self.metadata.get(normalize_key(key))
            if isinstance(value, (list, tuple)):
                normalized = [str(item).strip() for item in value if str(item).strip()]
                if normalized:
                    return normalized
            elif value is not None and str(value).strip():
                return [item.strip() for item in str(value).split(",") if item.strip()]
        return []


def freeze_value(value: Any) -> Any:
    """Recursively detach mutable containers from a loader-owned result."""
    if isinstance(value, Mapping):
        return MappingProxyType(
            {str(key): freeze_value(item) for key, item in value.items()}
        )
    if isinstance(value, (list, tuple)):
        return tuple(freeze_value(item) for item in value)
    if isinstance(value, (set, frozenset)):
        return frozenset(freeze_value(item) for item in value)
    return value


def freeze_mapping(value: Mapping[str, Any]) -> Mapping[str, Any]:
    """Return a deeply immutable mapping with detached storage."""
    frozen = freeze_value(value)
    if not isinstance(frozen, Mapping):  # pragma: no cover - type contract defense.
        raise TypeError("value must be a mapping")
    return frozen


def thaw_value(value: Any) -> Any:
    """Restore JSON-compatible mutable containers for strict validators."""
    if isinstance(value, Mapping):
        return {key: thaw_value(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [thaw_value(item) for item in value]
    if isinstance(value, frozenset):
        return [thaw_value(item) for item in sorted(value, key=repr)]
    return value


__all__ = [
    "ArtifactBytesView",
    "ArtifactJsonView",
    "ArtifactMarkdownView",
    "ArtifactTextView",
    "FileIdentity",
    "freeze_mapping",
    "freeze_value",
    "thaw_value",
]
