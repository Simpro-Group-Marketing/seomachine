"""Strict one-read loader for persisted final-release authorization bundles."""

from __future__ import annotations

import hashlib
import re
from collections.abc import Mapping
from pathlib import Path, PurePosixPath
from typing import Any

from ..artifact_runtime.limits import JSON_MAX_BYTES, TEXT_MAX_BYTES
from ..blog_assembly_contract import ArtifactSnapshot, load_json_object_snapshot
from ..blog_assembly_stage_receipt import check_stage_receipt
from ..context_binding_guard import require_artifact_kind
from ..readiness.contracts import PASSED_RESULT_FIELDS, READINESS_TOOL
from .contracts import (
    FINAL_READINESS_SCHEMA,
    RELEASE_MANIFEST_SCHEMA,
    PublishAuthorization,
    SealedArtifact,
    freeze_artifacts,
)


_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_MANIFEST_FIELDS = frozenset(
    {"schema", "artifact_kind", "run_id", "created_at", "inputs", "previous_receipt_hash"}
)
_INPUT_FIELDS = frozenset({"path", "sha256", "bytes"})
_RELEASE_RESULT_FIELDS = frozenset(
    {*PASSED_RESULT_FIELDS, "release_manifest", "release_manifest_sha256"}
)


def load_publish_authorization(
    *,
    final_readiness_path: str | Path,
    final_receipt_path: str | Path,
    release_manifest_path: str | Path,
    workspace_root: str | Path,
) -> PublishAuthorization:
    """Load and authenticate one complete final release bundle."""
    root = _workspace_root(workspace_root)
    manifest_path = _bundle_path(release_manifest_path, root=root, label="release manifest")
    readiness_path = _bundle_path(final_readiness_path, root=root, label="readiness output")
    receipt_path = _bundle_path(final_receipt_path, root=root, label="readiness receipt")
    if len({manifest_path, readiness_path, receipt_path}) != 3:
        raise ValueError("release bundle outputs must use distinct paths")

    manifest_snapshot, manifest_identity = _load_bundle_snapshot(
        manifest_path, field="release manifest"
    )
    readiness_snapshot, readiness_identity = _load_bundle_snapshot(
        readiness_path, field="final readiness"
    )
    receipt_snapshot, receipt_identity = _load_bundle_snapshot(
        receipt_path, field="final readiness receipt"
    )
    manifest = manifest_snapshot.payload
    result = readiness_snapshot.payload
    receipt = receipt_snapshot.payload

    _validate_manifest_envelope(manifest)
    artifact_kind, run_id = _validate_result_envelope(result)
    if manifest["artifact_kind"] != artifact_kind or manifest["run_id"] != run_id:
        raise ValueError("release manifest identity does not match final readiness")
    if result["release_manifest_sha256"] != manifest_snapshot.sha256:
        raise ValueError("final readiness release manifest digest does not match")
    if _bundle_path(result["release_manifest"], root=root, label="release manifest") != manifest_path:
        raise ValueError("final readiness release manifest path does not match")

    artifacts = _capture_manifest_inputs(manifest["inputs"], root=root)
    if any(path in {item.path for item in artifacts.values()} for path in (
        manifest_path, readiness_path, receipt_path,
    )):
        raise ValueError("release bundle output collides with a declared input")
    _validate_result_inventory(result, artifacts)
    _validate_result_paths(result, artifacts, root=root)
    _validate_article_identity(result, artifacts, root=root)
    _validate_bom(result, artifacts, artifact_kind=artifact_kind)
    _validate_receipt(
        receipt,
        result=result,
        manifest=manifest,
        artifacts=artifacts,
        readiness_snapshot=readiness_snapshot,
        manifest_snapshot=manifest_snapshot,
        workspace_root=root,
    )
    return PublishAuthorization(
        workspace_root=root,
        run_id=run_id,
        artifact_kind=artifact_kind,
        artifacts=freeze_artifacts(artifacts),
        manifest_path=manifest_path,
        manifest_sha256=manifest_snapshot.sha256,
        manifest_identity=manifest_identity,
        readiness_path=readiness_path,
        readiness_sha256=readiness_snapshot.sha256,
        readiness_identity=readiness_identity,
        receipt_path=receipt_path,
        receipt_sha256=receipt_snapshot.sha256,
        receipt_identity=receipt_identity,
    )


def _validate_manifest_envelope(manifest: Mapping[str, Any]) -> None:
    if set(manifest) != _MANIFEST_FIELDS:
        raise ValueError("release manifest has an invalid field set")
    if manifest.get("schema") != RELEASE_MANIFEST_SCHEMA:
        raise ValueError(f"release manifest must use {RELEASE_MANIFEST_SCHEMA}")
    if manifest.get("artifact_kind") not in {"blog", "landing_page"}:
        raise ValueError("release manifest artifact_kind is invalid")
    if not isinstance(manifest.get("run_id"), str) or not manifest["run_id"].strip():
        raise ValueError("release manifest run_id is required")
    if not isinstance(manifest.get("created_at"), str) or not manifest["created_at"].endswith("Z"):
        raise ValueError("release manifest created_at must be UTC")
    previous = manifest.get("previous_receipt_hash")
    if not isinstance(previous, str) or (previous and not _SHA256_RE.fullmatch(previous)):
        raise ValueError("release manifest previous_receipt_hash is invalid")
    if not isinstance(manifest.get("inputs"), Mapping) or "article" not in manifest["inputs"]:
        raise ValueError("release manifest requires an article input inventory")


def _validate_result_envelope(result: Mapping[str, Any]) -> tuple[str, str]:
    if result.get("schema") != FINAL_READINESS_SCHEMA:
        raise ValueError("publish authorization requires final readiness schema v2")
    kind = result.get("artifact_kind")
    if set(result) != _result_fields(kind):
        raise ValueError("final readiness result has an invalid field set")
    if result.get("tool") != READINESS_TOOL or result.get("verification_scope") != "source_artifact":
        raise ValueError("final readiness result identity is invalid")
    if result.get("phase") != "final" or result.get("passed") is not True:
        raise ValueError("publish authorization requires passed final readiness")
    if kind not in {"blog", "landing_page"}:
        raise ValueError("final readiness artifact_kind is invalid")
    run_id = result.get("run_id")
    if not isinstance(run_id, str) or not run_id.strip():
        raise ValueError("final readiness run_id is required")
    if result.get("input_seal") != {"status": "verified"}:
        raise ValueError("final readiness input seal is not verified")
    _validate_gate_inventory(result)
    return kind, run_id


def _result_fields(kind: Any) -> set[str]:
    fields = set(_RELEASE_RESULT_FIELDS)
    if kind == "blog":
        fields.add("final_bom_sha256")
    return fields


def _validate_gate_inventory(result: Mapping[str, Any]) -> None:
    gates = result.get("gates")
    inventory = result.get("gate_inventory")
    if not isinstance(gates, list) or not gates or not isinstance(inventory, list):
        raise ValueError("final readiness gate inventory is invalid")
    names = [gate.get("name") for gate in gates if isinstance(gate, Mapping)]
    if names != inventory or any(gate.get("passed") is not True for gate in gates):
        raise ValueError("final readiness contains an incomplete gate")


def _capture_manifest_inputs(value: Any, *, root: Path) -> dict[str, SealedArtifact]:
    if not isinstance(value, Mapping):
        raise ValueError("release manifest inputs must be an object")
    artifacts: dict[str, SealedArtifact] = {}
    for label, row in value.items():
        if not isinstance(label, str) or not label or not isinstance(row, Mapping):
            raise ValueError("release manifest contains an invalid input row")
        if set(row) != _INPUT_FIELDS:
            raise ValueError(f"release manifest input {label} has an invalid field set")
        path = _input_path(row.get("path"), root=root, label=label)
        expected_hash = row.get("sha256")
        expected_bytes = row.get("bytes")
        if not isinstance(expected_hash, str) or not _SHA256_RE.fullmatch(expected_hash):
            raise ValueError(f"release manifest input {label} sha256 is invalid")
        if isinstance(expected_bytes, bool) or not isinstance(expected_bytes, int) or expected_bytes < 0:
            raise ValueError(f"release manifest input {label} byte count is invalid")
        limit = JSON_MAX_BYTES if path.suffix.casefold() == ".json" else TEXT_MAX_BYTES
        snapshot, identity = _read_input(path, limit=limit, label=label)
        if any(item.path == path for item in artifacts.values()):
            raise ValueError("release manifest input paths must be distinct")
        if snapshot.sha256 != expected_hash or len(snapshot.data) != expected_bytes:
            raise ValueError(f"release manifest input {label} does not match current bytes")
        artifacts[label] = SealedArtifact(
            label=label,
            path=path,
            relative_path=str(row["path"]),
            data=snapshot.data,
            sha256=snapshot.sha256,
            byte_count=len(snapshot.data),
            file_identity=identity,
        )
    return artifacts


def _validate_result_inventory(result: Mapping[str, Any], artifacts: Mapping[str, SealedArtifact]) -> None:
    rows = result.get("input_hashes")
    if not isinstance(rows, Mapping) or set(rows) != set(artifacts):
        raise ValueError("final readiness input inventory does not match release manifest")
    expected = {
        label: {"path": item.relative_path, "sha256": item.sha256}
        for label, item in artifacts.items()
    }
    if rows != expected:
        raise ValueError("final readiness input inventory does not match release manifest")


def _validate_result_paths(
    result: Mapping[str, Any],
    artifacts: Mapping[str, SealedArtifact],
    *,
    root: Path,
) -> None:
    for field, label in (
        ("proof_sidecar", "validation_sidecar"),
        ("context_request", "context_request"),
        ("context_pack", "context_pack"),
        ("context_receipt", "context_receipt"),
        ("assembly_bom", "assembly_bom"),
    ):
        artifact = artifacts.get(label)
        value = result.get(field)
        if artifact is None:
            if value is not None:
                raise ValueError(f"final readiness {field} lacks a manifest input")
        elif _bundle_path(value, root=root, label=field) != artifact.path:
            raise ValueError(f"final readiness {field} path does not match release manifest")


def _validate_article_identity(
    result: Mapping[str, Any],
    artifacts: Mapping[str, SealedArtifact],
    *,
    root: Path,
) -> None:
    article = artifacts["article"]
    if _bundle_path(result.get("file"), root=root, label="final readiness article") != article.path:
        raise ValueError("final readiness article path does not match release manifest")
    try:
        kind = require_artifact_kind(article.data.decode("utf-8"), article_path=article.path)
    except (UnicodeDecodeError, ValueError) as error:
        raise ValueError(f"release article identity is invalid: {error}") from error
    if kind != result.get("artifact_kind"):
        raise ValueError("release article artifact_kind does not match final readiness")


def _validate_bom(
    result: Mapping[str, Any],
    artifacts: Mapping[str, SealedArtifact],
    *,
    artifact_kind: str,
) -> None:
    bom = artifacts.get("assembly_bom")
    if artifact_kind == "blog":
        if bom is None or result.get("assembly_bom") is None:
            raise ValueError("final blog authorization requires a final BOM")
        if result.get("final_bom_sha256") != bom.sha256:
            raise ValueError("final blog BOM digest does not match")
    elif bom is not None or result.get("assembly_bom") is not None:
        raise ValueError("landing-page authorization must not contain a blog BOM")


def _validate_receipt(
    receipt: Mapping[str, Any],
    *,
    result: Mapping[str, Any],
    manifest: Mapping[str, Any],
    artifacts: Mapping[str, SealedArtifact],
    readiness_snapshot: ArtifactSnapshot,
    manifest_snapshot: ArtifactSnapshot,
    workspace_root: Path,
) -> None:
    findings = check_stage_receipt(
        receipt,
        expected_stage="final_readiness_attestation",
        expected_tool_name="publish_readiness",
        expected_tool_version="1.0.0",
        workspace_root=workspace_root,
    )
    if findings:
        rules = ", ".join(sorted({str(row["rule_id"]) for row in findings}))
        raise ValueError(f"final readiness receipt is invalid: {rules}")
    if receipt.get("run_id") != result["run_id"]:
        raise ValueError("final readiness receipt run_id does not match")
    if any(receipt.get(field) != result.get(field) for field in ("started_at", "completed_at")):
        raise ValueError("final readiness receipt timestamps do not match")
    if receipt.get("previous_receipt_hash") != manifest["previous_receipt_hash"]:
        raise ValueError("final readiness receipt chain head does not match")
    inputs = {label: item.sha256 for label, item in artifacts.items()}
    if receipt.get("input_artifact_hashes") != inputs:
        raise ValueError("final readiness receipt inputs do not match release manifest")
    outputs = receipt.get("output_artifact_hashes")
    expected_outputs = {
        "article": artifacts["article"].sha256,
        "readiness_output": readiness_snapshot.sha256,
        "release_manifest": manifest_snapshot.sha256,
    }
    if outputs != expected_outputs:
        raise ValueError("final readiness receipt does not bind the readiness output and manifest")


def _workspace_root(value: str | Path) -> Path:
    if not isinstance(value, (str, Path)) or not str(value).strip():
        raise ValueError("workspace_root is required")
    try:
        root = Path(value).resolve(strict=True)
    except OSError as error:
        raise ValueError(f"workspace_root is unavailable: {error}") from error
    if not root.is_dir():
        raise ValueError("workspace_root must be a directory")
    return root


def _bundle_path(value: Any, *, root: Path, label: str) -> Path:
    if not isinstance(value, (str, Path)) or not str(value).strip():
        raise ValueError(f"{label} path is required")
    candidate = Path(value)
    if not candidate.is_absolute():
        candidate = root / candidate
    try:
        resolved = candidate.resolve(strict=True)
        resolved.relative_to(root)
    except (OSError, ValueError) as error:
        raise ValueError(f"{label} must be a file inside the workspace") from error
    if not resolved.is_file():
        raise ValueError(f"{label} must be a file inside the workspace")
    return resolved


def _input_path(value: Any, *, root: Path, label: str) -> Path:
    if not isinstance(value, str) or not value:
        raise ValueError(f"release manifest input {label} path is invalid")
    pure = PurePosixPath(value)
    if pure.is_absolute() or "\\" in value or any(part in {"", ".", ".."} for part in pure.parts):
        raise ValueError(f"release manifest input {label} path is invalid")
    return _bundle_path(root.joinpath(*pure.parts), root=root, label=f"release input {label}")


def _read_input(
    path: Path,
    *,
    limit: int,
    label: str,
) -> tuple[ArtifactSnapshot, tuple[int, int, int, int, int]]:
    before = _file_identity(path)
    if path.suffix.casefold() == ".json":
        snapshot = load_json_object_snapshot(
            path, field=f"release input {label}", max_bytes=limit
        )
    else:
        try:
            with path.open("rb") as handle:
                data = handle.read(limit + 1)
        except OSError as error:
            raise ValueError(f"release input {label} is unreadable: {error}") from error
        if len(data) > limit:
            raise ValueError(f"release input {label} exceeds {limit} bytes")
        try:
            data.decode("utf-8")
        except UnicodeDecodeError as error:
            raise ValueError(f"release input {label} must use valid UTF-8") from error
        snapshot = ArtifactSnapshot(
            path=path,
            data=data,
            sha256=hashlib.sha256(data).hexdigest(),
            payload={},
        )
    after = _file_identity(path)
    if before != after:
        raise ValueError(f"release input {label} changed while it was read")
    return snapshot, after


def _load_bundle_snapshot(
    path: Path,
    *,
    field: str,
) -> tuple[ArtifactSnapshot, tuple[int, int, int, int, int]]:
    before = _file_identity(path)
    snapshot = load_json_object_snapshot(path, field=field)
    after = _file_identity(path)
    if before != after:
        raise ValueError(f"{field} changed while it was read")
    return snapshot, after


def _file_identity(path: Path) -> tuple[int, int, int, int, int]:
    stat = path.stat()
    return (stat.st_dev, stat.st_ino, stat.st_size, stat.st_mtime_ns, stat.st_ctime_ns)
