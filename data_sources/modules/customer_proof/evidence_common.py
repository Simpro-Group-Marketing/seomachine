"""Shared filesystem and shape validation for selector evidence."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any, Mapping, Sequence


MAX_SELECTOR_EVIDENCE_BYTES = 1024 * 1024
SHA256_RE = re.compile(r"[0-9a-f]{64}")


def selector_evidence_path(raw_path: str, proof_sidecar_path: str) -> Path | None:
    candidate = Path(raw_path).expanduser()
    if candidate.is_absolute():
        return candidate.resolve()
    sidecar = Path(proof_sidecar_path).resolve()
    candidates = (
        Path.cwd() / candidate,
        sidecar.parent / candidate,
        sidecar.parent.parent / candidate,
    )
    return next((path.resolve() for path in candidates if path.is_file()), None)


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_selector_evidence(
    proof_sidecar_content: str,
    proof_sidecar_path: str | None,
) -> dict[str, Any] | None:
    if not proof_sidecar_path:
        return None
    sidecar_path = Path(proof_sidecar_path).resolve()
    if not _sidecar_matches(sidecar_path, proof_sidecar_content):
        return None
    match = re.search(
        r"(?im)^[-*+]\s*Selector evidence:\s*(.+?)\s*\|\s*"
        r"SHA-256:\s*([0-9a-f]{64})\s*$",
        proof_sidecar_content,
    )
    if match is None:
        return None
    evidence_path = selector_evidence_path(match.group(1).strip().strip("\"'"), str(sidecar_path))
    if evidence_path is None:
        return None
    return _read_hashed_json(evidence_path, match.group(2))


def _sidecar_matches(path: Path, expected_content: str) -> bool:
    try:
        return path.is_file() and path.read_text(encoding="utf-8") == expected_content
    except (OSError, UnicodeError):
        return False


def _read_hashed_json(path: Path, expected_sha256: str) -> dict[str, Any] | None:
    try:
        if not path.is_file() or path.stat().st_size > MAX_SELECTOR_EVIDENCE_BYTES:
            return None
        payload = path.read_bytes()
        if hashlib.sha256(payload).hexdigest() != expected_sha256:
            return None
        parsed = json.loads(payload)
        return parsed if isinstance(parsed, dict) else None
    except (json.JSONDecodeError, OSError, TypeError, UnicodeError):
        return None


def verified_artifact_paths(
    evidence: Mapping[str, Any],
    required_names: Sequence[str],
) -> dict[str, Path] | None:
    artifacts = evidence.get("artifacts")
    if not isinstance(artifacts, dict) or set(artifacts) != set(required_names):
        return None
    resolved: dict[str, Path] = {}
    for name in required_names:
        path = _verified_artifact_path(artifacts.get(name))
        if path is None:
            return None
        resolved[name] = path
    return resolved


def _verified_artifact_path(record: object) -> Path | None:
    if not isinstance(record, dict):
        return None
    path = Path(str(record.get("path", ""))).expanduser()
    digest = str(record.get("sha256", ""))
    if not path.is_absolute() or SHA256_RE.fullmatch(digest) is None or not path.is_file():
        return None
    return path.resolve() if file_sha256(path) == digest else None


def artifacts_unchanged(
    evidence: Mapping[str, Any],
    artifact_paths: Mapping[str, Path],
) -> bool:
    artifacts = evidence.get("artifacts")
    if not isinstance(artifacts, dict):
        return False
    return all(
        file_sha256(path) == str(artifacts[name].get("sha256", ""))
        for name, path in artifact_paths.items()
    )


def string_inputs_valid(inputs: Mapping[str, Any], names: Sequence[str]) -> bool:
    return all(isinstance(inputs.get(name), str) for name in names)


def limit_value(inputs: Mapping[str, Any]) -> int | None:
    value = inputs.get("limit")
    if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= 100:
        return None
    return value


def overrides_valid(inputs: Mapping[str, Any]) -> bool:
    selected = inputs.get("selected_overrides", {})
    rejected = inputs.get("rejected_overrides", {})
    if not isinstance(selected, dict) or not isinstance(rejected, dict):
        return False
    selected_valid = all(isinstance(role, str) and isinstance(value, str) for role, value in selected.items())
    rejected_valid = all(
        isinstance(role, str)
        and isinstance(rows, dict)
        and all(isinstance(candidate, str) and isinstance(reason, str) for candidate, reason in rows.items())
        for role, rows in rejected.items()
    )
    return selected_valid and rejected_valid


__all__ = [
    "MAX_SELECTOR_EVIDENCE_BYTES",
    "artifacts_unchanged",
    "file_sha256",
    "limit_value",
    "load_selector_evidence",
    "overrides_valid",
    "selector_evidence_path",
    "string_inputs_valid",
    "verified_artifact_paths",
]
