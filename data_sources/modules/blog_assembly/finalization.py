"""Finalization responsibilities."""
import copy
from datetime import date
from pathlib import Path
from typing import Any, Mapping, Sequence

from .common import (
    BOM_SCHEMA_V1,
    BOM_SCHEMA_V2,
    BOM_SCHEMA_V3,
    BOM_SCHEMA_V4,
    atomic_write_json,
    canonical_article_run_id,
    canonical_artifact,
    canonical_json_sha256,
    file_sha256,
    load_json_object_snapshot,
    resolve_artifact,
    validate_sha256,
)
from .construction import build_blog_assembly_bom_from_files
from .contracts import _is_supported_bom_schema, _read_json_object, _required_mapping
from .preflight import _validate_passed_preflight, _verify_bom_artifacts_unchanged
from .preflight_receipts import validate_preflight_stage_receipt_binding
from ..blog_bom_validation.api import check_bom
from ..readiness.result_validation import validate_passed_readiness_result


def build_blog_assembly_bom(**kwargs: Any) -> dict[str, Any]:
    """Compatibility public name for the strict file-backed builder."""
    return build_blog_assembly_bom_from_files(**kwargs)

def finalize_blog_assembly_bom(
    *,
    bom_path: str | Path,
    preflight_readiness_path: str | Path,
    workspace_root: str | Path | None = None,
    vault_root: str | Path | None = None,
) -> dict[str, Any]:
    """Seal a passed preflight into a final BOM without self-reference."""
    root = Path(workspace_root or Path.cwd()).resolve()
    bom_snapshot = load_json_object_snapshot(bom_path, field="bom")
    bom = bom_snapshot.payload
    if not _is_supported_bom_schema(bom.get("schema")):
        raise ValueError(
            f"bom.schema must be {BOM_SCHEMA_V1}, {BOM_SCHEMA_V2}, {BOM_SCHEMA_V3}, or {BOM_SCHEMA_V4}"
        )
    if bom.get("lifecycle_state") != "provisional":
        raise ValueError("only a provisional BOM can be finalized")
    if bom_snapshot.sha256 != canonical_json_sha256(bom):
        raise ValueError(
            "provisional BOM bytes are not the canonical deterministic serialization"
        )
    _validate_provisional_bom_guard(bom, workspace_root=root, vault_root=vault_root)
    readiness = _read_json_object(preflight_readiness_path, "preflight_readiness")
    _validate_passed_preflight(
        readiness,
        bom,
        bom_path=Path(bom_path),
        workspace_root=root,
    )
    _validate_persisted_readiness_contract(readiness, workspace_root=root)
    _verify_bom_artifacts_unchanged(bom, root)
    receipt_path = _readiness_receipt_path(preflight_readiness_path)
    preflight_receipt = _read_json_object(receipt_path, "preflight_stage_receipt")
    _validate_preflight_stage_receipt(
        preflight_receipt,
        bom=bom,
        readiness_path=Path(preflight_readiness_path),
        workspace_root=root,
    )
    final_bom = copy.deepcopy(bom)
    readiness_artifact = canonical_artifact(
        preflight_readiness_path,
        workspace_root=root,
    )
    final_bom["lifecycle_state"] = "final"
    final_bom["artifacts"]["preflight_readiness"] = readiness_artifact
    final_bom["artifacts"]["stage_receipts"].append(
        canonical_artifact(receipt_path, workspace_root=root)
    )
    final_bom["workflow"]["stage_receipts"].append(preflight_receipt)
    final_bom["preflight"] = {
        "path": readiness_artifact["path"],
        "sha256": readiness_artifact["sha256"],
        "tool": copy.deepcopy(readiness["tool"]),
        "verification_scope": "source_artifact",
        "gate_inventory": list(readiness["gate_inventory"]),
        "input_hashes": copy.deepcopy(readiness["input_hashes"]),
    }
    _validate_final_bom_guard(final_bom, workspace_root=root, vault_root=vault_root)
    return final_bom

def _validate_persisted_readiness_contract(
    readiness: Mapping[str, Any],
    *,
    workspace_root: Path,
) -> None:
    validate_passed_readiness_result(
        readiness,
        workspace_root=workspace_root,
    )

def _validate_provisional_bom_guard(
    bom: Mapping[str, Any],
    *,
    workspace_root: Path,
    vault_root: str | Path | None = None,
) -> None:
    """Run the same complete BOM guard used by preflight before sealing."""
    artifacts = _required_mapping(bom.get("artifacts"), "bom.artifacts")

    def bound_path(label: str, *, required: bool = False) -> Path | None:
        row = artifacts.get(label)
        if row is None and not required:
            return None
        mapping = _required_mapping(row, f"bom.artifacts.{label}")
        return resolve_artifact(mapping.get("path"), workspace_root=workspace_root)

    findings = check_bom(
        bom,
        article_path=bound_path("article", required=True),
        validation_sidecar_path=bound_path("validation_sidecar", required=True),
        context_request_path=bound_path("context_request"),
        context_pack_path=bound_path("context_pack"),
        context_receipt_path=bound_path("context_receipt"),
        workspace_root=workspace_root,
        vault_root=vault_root,
        expected_lifecycle_state="provisional",
    )
    if findings:
        rules = ", ".join(
            sorted({str(finding.get("rule_id")) for finding in findings})
        )
        raise ValueError(f"provisional BOM is invalid: {rules}")

def _validate_final_bom_guard(
    bom: Mapping[str, Any],
    *,
    workspace_root: Path,
    vault_root: str | Path | None = None,
) -> None:
    """Reject a final object that would fail the same guard after persistence."""
    artifacts = _required_mapping(bom.get("artifacts"), "bom.artifacts")

    def bound_path(label: str, *, required: bool = False) -> Path | None:
        row = artifacts.get(label)
        if row is None and not required:
            return None
        mapping = _required_mapping(row, f"bom.artifacts.{label}")
        return resolve_artifact(mapping.get("path"), workspace_root=workspace_root)

    findings = check_bom(
        bom,
        article_path=bound_path("article", required=True),
        validation_sidecar_path=bound_path("validation_sidecar", required=True),
        context_request_path=bound_path("context_request"),
        context_pack_path=bound_path("context_pack"),
        context_receipt_path=bound_path("context_receipt"),
        workspace_root=workspace_root,
        vault_root=vault_root,
        expected_lifecycle_state="final",
    )
    if findings:
        rules = ", ".join(
            sorted({str(finding.get("rule_id")) for finding in findings})
        )
        raise ValueError(f"constructed final BOM is invalid: {rules}")

def _readiness_receipt_path(readiness_path: str | Path) -> Path:
    source = Path(readiness_path)
    return source.with_name(f"{source.stem}-stage-receipt.json")

def _validate_preflight_stage_receipt(
    receipt: Mapping[str, Any],
    *,
    bom: Mapping[str, Any],
    readiness_path: Path,
    workspace_root: Path,
) -> None:
    workflow = _required_mapping(bom.get("workflow"), "bom.workflow")
    prior = workflow.get("stage_receipts")
    if not isinstance(prior, list):
        raise ValueError("bom.workflow.stage_receipts must be a list")
    artifacts = _required_mapping(bom.get("artifacts"), "bom.artifacts")
    article = _required_mapping(artifacts.get("article"), "bom.artifacts.article")
    article_path = resolve_artifact(
        article.get("path"),
        workspace_root=workspace_root,
    )
    validate_preflight_stage_receipt_binding(
        receipt,
        prior_receipts=prior,
        readiness_path=readiness_path,
        article_sha256=article.get("sha256"),
        article_path=article_path,
        workspace_root=workspace_root,
        assembly_date=bom.get("assembly_date"),
    )

def write_blog_assembly_bom(path: str | Path, bom: Mapping[str, Any]) -> None:
    """Persist a deterministic BOM atomically."""
    atomic_write_json(path, bom)


__all__ = ['_readiness_receipt_path', '_validate_final_bom_guard', '_validate_persisted_readiness_contract', '_validate_preflight_stage_receipt', '_validate_provisional_bom_guard', 'build_blog_assembly_bom', 'finalize_blog_assembly_bom', 'validate_preflight_stage_receipt_binding', 'write_blog_assembly_bom']
