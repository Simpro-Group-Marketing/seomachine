"""Creation of one hash-bound final release manifest and readiness result."""

from __future__ import annotations

import hashlib
import hmac
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from ..blog_assembly_contract import canonical_json_bytes, validate_sha256
from ..readiness.contracts import (
    FINAL_READINESS_RESULT_SCHEMA,
    ExecutedReadinessResult,
    sign_readiness_execution,
)
from ..readiness.inputs import ReadinessInputs
from ..readiness.result_validation import validate_passed_readiness_result
from .contracts import RELEASE_MANIFEST_SCHEMA


def prepare_final_release_result(
    result: Mapping[str, Any],
    *,
    release_manifest_path: str | Path,
    previous_receipt_hash: str,
    workspace_root: str | Path,
) -> ExecutedReadinessResult:
    """Persist a no-clobber manifest and return its authenticated v2 result."""
    root = _workspace_root(workspace_root)
    _validate_executed_result(result, root=root)
    if result.get("phase") != "final" or result.get("passed") is not True:
        raise ValueError("release manifest requires passed final readiness")
    previous = str(previous_receipt_hash or "")
    if previous:
        validate_sha256(previous, field="previous_receipt_hash")
    paths = _result_input_paths(result)
    inputs = ReadinessInputs.capture(paths, workspace_root=root)
    if inputs.hash_inventory() != result.get("input_hashes"):
        raise ValueError("final readiness inputs changed before release manifest creation")
    destination = _new_manifest_path(release_manifest_path, root=root)
    manifest = {
        "schema": RELEASE_MANIFEST_SCHEMA,
        "artifact_kind": result["artifact_kind"],
        "run_id": result["run_id"],
        "created_at": _utc_now(),
        "inputs": inputs.release_inventory(),
        "previous_receipt_hash": previous,
    }
    manifest_bytes = canonical_json_bytes(manifest)
    _write_new_file(destination, manifest_bytes)
    upgraded = dict(result)
    upgraded.update(
        {
            "schema": FINAL_READINESS_RESULT_SCHEMA,
            "release_manifest": destination.relative_to(root).as_posix(),
            "release_manifest_sha256": hashlib.sha256(manifest_bytes).hexdigest(),
        }
    )
    executed = ExecutedReadinessResult(upgraded, workspace_root=root)
    validate_passed_readiness_result(executed, workspace_root=root)
    return executed


def _validate_executed_result(result: Mapping[str, Any], *, root: Path) -> None:
    if not isinstance(result, ExecutedReadinessResult):
        raise ValueError("release manifest requires an actual readiness execution")
    if result._workspace_root != root:
        raise ValueError("readiness execution workspace_root changed")
    expected = sign_readiness_execution(result)
    if not hmac.compare_digest(result._execution_signature, expected):
        raise ValueError("readiness result changed after execution")
    validate_passed_readiness_result(result, workspace_root=root)


def _result_input_paths(result: Mapping[str, Any]) -> dict[str, str]:
    rows = result.get("input_hashes")
    if not isinstance(rows, Mapping) or not rows:
        raise ValueError("final readiness requires a complete input inventory")
    paths: dict[str, str] = {}
    for label, row in rows.items():
        if not isinstance(label, str) or not isinstance(row, Mapping):
            raise ValueError("final readiness input inventory is invalid")
        path = row.get("path")
        if not isinstance(path, str) or not path:
            raise ValueError(f"final readiness input {label} path is invalid")
        paths[label] = path
    return paths


def _workspace_root(value: str | Path) -> Path:
    try:
        root = Path(value).resolve(strict=True)
    except OSError as error:
        raise ValueError(f"workspace_root is unavailable: {error}") from error
    if not root.is_dir():
        raise ValueError("workspace_root must be a directory")
    return root


def _new_manifest_path(value: str | Path, *, root: Path) -> Path:
    path = Path(value)
    if not path.is_absolute():
        path = root / path
    resolved = path.resolve(strict=False)
    try:
        resolved.relative_to(root)
    except ValueError as error:
        raise ValueError("release manifest must stay inside the workspace") from error
    if resolved.exists():
        raise ValueError("release manifest output must not already exist")
    return resolved


def _write_new_file(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            temporary = Path(handle.name)
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        try:
            os.link(temporary, path)
        except FileExistsError as error:
            raise ValueError("release manifest output already exists") from error
        temporary.unlink()
        temporary = None
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
