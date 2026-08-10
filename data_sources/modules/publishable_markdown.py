"""Shared parsing and snapshot helpers for publishable Markdown artifacts."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Mapping
from urllib.parse import urlparse

try:
    from .frontmatter import (
        FrontmatterError,
        normalize_key as normalize_frontmatter_key,
        split_frontmatter,
    )
except ImportError:  # pragma: no cover - supports direct script execution.
    from frontmatter import (
        FrontmatterError,
        normalize_key as normalize_frontmatter_key,
        split_frontmatter,
    )


H1_RE = re.compile(r"^#\s+(.+?)\s*$", re.MULTILINE)
LEGACY_FIELD_RE = re.compile(r"^\*\*(?P<key>[^*]+)\*\*:\s*(?P<value>.*?)\s*$")
LEGACY_METADATA_KEYS = frozenset(
    {
        "author",
        "category",
        "conversion_goal",
        "external_links",
        "internal_links",
        "last_updated",
        "meta_description",
        "meta_title",
        "original_url",
        "page_type",
        "primary_keyword",
        "rewrite_date",
        "secondary_keywords",
        "tags",
        "target_keyword",
        "target_url",
        "url_slug",
        "word_count",
    }
)


@dataclass(frozen=True)
class FileSnapshot:
    """Immutable hash state for one supplied publish-readiness input."""

    label: str
    path: Path
    sha256: str | None


@dataclass(frozen=True)
class PublishableMarkdown:
    """An immutable read of one Markdown artifact."""

    path: Path
    raw: str
    sha256: str
    metadata: Dict[str, Any]
    h1: str
    body: str

    def scalar(self, *keys: str) -> str:
        """Return the first non-empty metadata value as a scalar string."""
        for key in keys:
            value = self.metadata.get(normalize_key(key))
            if isinstance(value, list):
                if value:
                    return ", ".join(value)
            elif value is not None and str(value).strip():
                return str(value).strip()
        return ""

    def values(self, *keys: str) -> list[str]:
        """Return the first non-empty metadata value as a string list."""
        for key in keys:
            value = self.metadata.get(normalize_key(key))
            if isinstance(value, list):
                normalized = [str(item).strip() for item in value if str(item).strip()]
                if normalized:
                    return normalized
            elif value is not None and str(value).strip():
                return [item.strip() for item in str(value).split(",") if item.strip()]
        return []


def read_publishable_markdown(path: str | Path) -> PublishableMarkdown:
    """Read and parse one artifact into an immutable snapshot."""
    source = Path(path)
    raw_bytes = source.read_bytes()
    try:
        raw = raw_bytes.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise FrontmatterError(
            f"Publishable Markdown is not valid UTF-8: {source}."
        ) from exc
    metadata, body = _split_frontmatter(raw)
    metadata, body = _merge_legacy_metadata(metadata, body)
    h1_match = H1_RE.search(body)
    h1 = h1_match.group(1).strip() if h1_match else ""
    if h1_match:
        body = body[: h1_match.start()] + body[h1_match.end() :]
    body = body.strip()
    return PublishableMarkdown(
        path=source,
        raw=raw,
        sha256=hashlib.sha256(raw_bytes).hexdigest(),
        metadata=metadata,
        h1=h1,
        body=body,
    )


def capture_file_snapshots(
    inputs: Mapping[str, str | Path | None],
) -> dict[str, FileSnapshot]:
    """Hash every supplied readiness input without silently skipping missing files."""
    snapshots: dict[str, FileSnapshot] = {}
    for label, value in inputs.items():
        if value is None:
            continue
        path = Path(value)
        try:
            raw = path.read_bytes()
        except FileNotFoundError:
            digest = None
        else:
            digest = hashlib.sha256(raw).hexdigest()
        snapshots[label] = FileSnapshot(label=label, path=path, sha256=digest)
    return snapshots


def ensure_same_file_snapshots(
    before: Mapping[str, FileSnapshot],
    after: Mapping[str, FileSnapshot],
) -> None:
    """Reject missing, replaced, or modified publish-readiness inputs."""
    if set(before) != set(after):
        raise ValueError("publish inputs changed during readiness")
    for label in sorted(before):
        expected = before[label]
        current = after[label]
        if expected.path != current.path or expected.sha256 is None or current.sha256 is None:
            raise ValueError(f"publish input is unavailable: {label} ({expected.path})")
        if expected.sha256 != current.sha256:
            raise ValueError(f"publish inputs changed: {label} ({expected.path})")

def ensure_same_snapshot(before: PublishableMarkdown, after: PublishableMarkdown) -> None:
    """Reject a source artifact changed while its readiness checks ran."""
    if before.sha256 != after.sha256:
        raise ValueError(
            f"Publishable Markdown changed during readiness: {before.path}"
        )


def metadata_path_tail(value: str) -> str:
    """Return the final URL/path segment from a metadata value."""
    candidate = value.strip()
    if not candidate:
        return ""
    parsed = urlparse(candidate)
    path = parsed.path or candidate
    return path.rstrip("/").replace("\\", "/").split("/")[-1]


def normalize_key(value: str) -> str:
    """Normalize legacy and canonical metadata field names."""
    return normalize_frontmatter_key(value)


def _split_frontmatter(raw: str) -> tuple[Dict[str, Any], str]:
    metadata, body, _ = split_frontmatter(raw)
    return metadata, body


def _parse_scalar(value: str) -> str:
    candidate = value.strip()
    if len(candidate) >= 2 and candidate[0] == candidate[-1] == '"':
        try:
            parsed = json.loads(candidate)
        except json.JSONDecodeError:
            return candidate[1:-1]
        return str(parsed)
    if len(candidate) >= 2 and candidate[0] == candidate[-1] == "'":
        return candidate[1:-1].replace("''", "'")
    return candidate


def _merge_legacy_metadata(
    metadata: Dict[str, Any],
    body: str,
) -> tuple[Dict[str, Any], str]:
    """Promote only a contiguous legacy metadata block in the document preamble."""
    lines = body.splitlines()
    cursor = 0
    while cursor < len(lines) and not lines[cursor].strip():
        cursor += 1

    if cursor < len(lines) and H1_RE.fullmatch(lines[cursor]):
        cursor += 1
        while cursor < len(lines) and not lines[cursor].strip():
            cursor += 1

    first_metadata_line = cursor
    merged = dict(metadata)
    while cursor < len(lines):
        match = LEGACY_FIELD_RE.match(lines[cursor])
        if not match:
            break
        key = normalize_key(match.group("key"))
        if key not in LEGACY_METADATA_KEYS:
            break
        merged.setdefault(key, _parse_scalar(match.group("value")))
        cursor += 1

    if cursor == first_metadata_line:
        return merged, body
    retained_lines = lines[:first_metadata_line] + lines[cursor:]
    return merged, "\n".join(retained_lines)