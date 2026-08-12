"""Opaque, process-local reuse of findings from one sealed readiness run."""

from __future__ import annotations

import hashlib
import hmac
import os
from pathlib import Path
from typing import Any, Mapping, Sequence

try:
    from .blog_assembly_contract import (
        canonical_json_bytes,
        file_sha256,
        resolve_artifact,
        validate_sha256,
    )
except ImportError:  # pragma: no cover - supports direct script execution.
    from blog_assembly_contract import (
        canonical_json_bytes,
        file_sha256,
        resolve_artifact,
        validate_sha256,
    )


_ISSUER_TOKEN = object()
_SIGNING_KEY = os.urandom(32)


class ReadinessGateContext:
    """Non-serializable capability binding reused findings to exact run inputs."""

    __slots__ = (
        "_article_sha256",
        "_findings",
        "_input_hashes",
        "_proof_sidecar_sha256",
        "_signature",
        "_workspace_root",
    )

    def __init__(
        self,
        *,
        token: object,
        findings: Mapping[str, tuple[dict[str, Any], ...]],
        article_sha256: str,
        proof_sidecar_sha256: str,
        input_hashes: Mapping[str, dict[str, str]],
        workspace_root: Path,
    ) -> None:
        if token is not _ISSUER_TOKEN:
            raise TypeError("ReadinessGateContext can only be issued by publish readiness")
        self._findings = dict(findings)
        self._article_sha256 = article_sha256
        self._proof_sidecar_sha256 = proof_sidecar_sha256
        self._input_hashes = dict(input_hashes)
        self._workspace_root = workspace_root.resolve()
        self._signature = _sign(self._payload())

    def _payload(self) -> dict[str, Any]:
        return {
            "article_sha256": self._article_sha256,
            "proof_sidecar_sha256": self._proof_sidecar_sha256,
            "input_hashes": self._input_hashes,
            "findings": {
                gate: list(rows)
                for gate, rows in sorted(self._findings.items())
            },
            "workspace_root": str(self._workspace_root),
        }

    def _findings_for(
        self,
        gate_name: str,
        *,
        article_content: str,
        proof_sidecar_content: str | None,
    ) -> list[dict[str, Any]] | None:
        if not hmac.compare_digest(self._signature, _sign(self._payload())):
            return None
        if _text_sha256(article_content) != self._article_sha256:
            return None
        if _optional_text_sha256(proof_sidecar_content) != self._proof_sidecar_sha256:
            return None
        if not _inputs_unchanged(self._input_hashes, self._workspace_root):
            return None
        rows = self._findings.get(gate_name)
        if rows is None:
            return None
        return [dict(row) for row in rows]


def _issue_readiness_gate_context(
    findings_by_gate: Mapping[str, Sequence[Mapping[str, Any]]],
    *,
    article_content: str,
    proof_sidecar_content: str | None,
    input_hashes: Mapping[str, Mapping[str, str]],
    workspace_root: str | Path,
) -> ReadinessGateContext:
    """Issue one capability after publish readiness has validated all inputs."""
    findings: dict[str, tuple[dict[str, Any], ...]] = {}
    for gate_name, raw_rows in findings_by_gate.items():
        if not isinstance(gate_name, str) or not gate_name:
            raise ValueError("readiness context gate names must be non-empty strings")
        if isinstance(raw_rows, (str, bytes)) or not isinstance(raw_rows, Sequence):
            raise ValueError(f"readiness context findings for {gate_name} must be a sequence")
        rows: list[dict[str, Any]] = []
        for index, row in enumerate(raw_rows):
            if not isinstance(row, Mapping):
                raise ValueError(
                    f"readiness context finding {gate_name}[{index}] must be an object"
                )
            rows.append(dict(row))
        findings[gate_name] = tuple(rows)

    snapshots: dict[str, dict[str, str]] = {}
    for label, raw_row in input_hashes.items():
        if not isinstance(label, str) or not label or not isinstance(raw_row, Mapping):
            raise ValueError("readiness context input hashes are invalid")
        if set(raw_row) != {"path", "sha256"}:
            raise ValueError(f"readiness context input {label} must contain path and sha256")
        path = raw_row.get("path")
        if not isinstance(path, str) or not path:
            raise ValueError(f"readiness context input {label}.path is invalid")
        snapshots[label] = {
            "path": path,
            "sha256": validate_sha256(
                raw_row.get("sha256"),
                field=f"readiness_context.{label}.sha256",
            ),
        }

    return ReadinessGateContext(
        token=_ISSUER_TOKEN,
        findings=findings,
        article_sha256=_text_sha256(article_content),
        proof_sidecar_sha256=_optional_text_sha256(proof_sidecar_content),
        input_hashes=snapshots,
        workspace_root=Path(workspace_root),
    )


def trusted_readiness_findings(
    context: object,
    gate_name: str,
    *,
    article_content: str,
    proof_sidecar_content: str | None,
) -> list[dict[str, Any]] | None:
    """Return bound findings only for a valid opaque readiness capability."""
    if not isinstance(context, ReadinessGateContext):
        return None
    return context._findings_for(
        gate_name,
        article_content=article_content,
        proof_sidecar_content=proof_sidecar_content,
    )


def _inputs_unchanged(
    rows: Mapping[str, Mapping[str, str]],
    workspace_root: Path,
) -> bool:
    try:
        for row in rows.values():
            path = resolve_artifact(row["path"], workspace_root=workspace_root)
            if not path.is_file() or file_sha256(path) != row["sha256"]:
                return False
    except (KeyError, OSError, ValueError):
        return False
    return True


def _text_sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _optional_text_sha256(value: str | None) -> str:
    marker = {"present": value is not None, "value": value or ""}
    return hashlib.sha256(canonical_json_bytes(marker)).hexdigest()


def _sign(payload: Mapping[str, Any]) -> str:
    return hmac.new(_SIGNING_KEY, canonical_json_bytes(payload), hashlib.sha256).hexdigest()
