"""Read and hash nonconnector customer-proof inputs."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .nonconnector_contracts import NonVaultProofDataError


def _read_json(path: str | Path, label: str) -> dict[str, Any]:
    candidate = Path(path)
    if not candidate.is_file():
        raise NonVaultProofDataError(f"{label} is unavailable: {candidate}")
    payload = json.loads(candidate.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise NonVaultProofDataError(f"{label} must be a JSON object")
    return payload


def _file_sha256(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


__all__ = [
    '_read_json',
    '_file_sha256'
]
