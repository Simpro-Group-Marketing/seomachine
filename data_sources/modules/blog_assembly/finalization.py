"""Finalization responsibilities."""
# ruff: noqa: F403, F405

from .common import *  # noqa: F403


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
            f"bom.schema must be {BOM_SCHEMA_V1}, {BOM_SCHEMA_V2}, or {BOM_SCHEMA_V3}"
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
    try:
        from .. import publish_readiness
    except ImportError:  # pragma: no cover - supports direct script execution.
        import publish_readiness
    publish_readiness.validate_passed_readiness_result(
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
    try:
        from .. import blog_assembly_bom_guard
    except ImportError:  # pragma: no cover - supports direct script execution.
        import blog_assembly_bom_guard

    artifacts = _required_mapping(bom.get("artifacts"), "bom.artifacts")

    def bound_path(label: str, *, required: bool = False) -> Path | None:
        row = artifacts.get(label)
        if row is None and not required:
            return None
        mapping = _required_mapping(row, f"bom.artifacts.{label}")
        return resolve_artifact(mapping.get("path"), workspace_root=workspace_root)

    findings = blog_assembly_bom_guard.check_bom(
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
    try:
        from .. import blog_assembly_bom_guard
    except ImportError:  # pragma: no cover - supports direct script execution.
        import blog_assembly_bom_guard

    artifacts = _required_mapping(bom.get("artifacts"), "bom.artifacts")

    def bound_path(label: str, *, required: bool = False) -> Path | None:
        row = artifacts.get(label)
        if row is None and not required:
            return None
        mapping = _required_mapping(row, f"bom.artifacts.{label}")
        return resolve_artifact(mapping.get("path"), workspace_root=workspace_root)

    findings = blog_assembly_bom_guard.check_bom(
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

def _readiness_input_digests(readiness: Mapping[str, Any]) -> dict[str, str]:
    rows = _required_mapping(
        readiness.get("input_hashes"), "preflight_readiness.input_hashes"
    )
    digests: dict[str, str] = {}
    for label, row in rows.items():
        if not isinstance(label, str) or not label.strip():
            raise ValueError("preflight readiness input labels must be non-empty strings")
        input_row = _required_mapping(
            row, f"preflight_readiness.input_hashes.{label}"
        )
        digests[label] = validate_sha256(
            input_row.get("sha256"),
            field=f"preflight_readiness.input_hashes.{label}.sha256",
        )
    return digests


def _receipt_chain_run_id(
    receipts: Sequence[Mapping[str, Any]],
    *,
    article_path: str | Path,
    workspace_root: str | Path,
    assembly_date: str | date,
) -> str:
    run_ids = {str(row.get("run_id") or "").strip() for row in receipts}
    run_ids.discard("")
    if len(run_ids) == 1:
        return next(iter(run_ids))
    return canonical_article_run_id(
        article_path, workspace_root=workspace_root, assembly_date=assembly_date
    )


def _validate_receipt_readiness_bindings(
    receipt: Mapping[str, Any],
    readiness: Mapping[str, Any],
    *,
    readiness_path: Path,
    article_sha256: str,
) -> None:
    outputs = receipt.get("output_artifact_hashes")
    if not isinstance(outputs, Mapping) or outputs.get("readiness_output") != file_sha256(readiness_path):
        raise ValueError("preflight stage receipt does not bind the readiness output")
    expected_inputs = _readiness_input_digests(readiness)
    if receipt.get("input_artifact_hashes") != expected_inputs:
        raise ValueError("preflight stage receipt input hashes do not match readiness")
    expected_evidence = {
        label: digest for label, digest in expected_inputs.items()
        if label not in {"article", "assembly_bom"}
    }
    if receipt.get("evidence_hashes") != expected_evidence:
        raise ValueError("preflight stage receipt evidence hashes do not match readiness")
    identity_matches = all(
        receipt.get(field) == readiness.get(field)
        for field in ("run_id", "started_at", "completed_at")
    )
    if not identity_matches:
        raise ValueError("preflight stage receipt run identity does not match readiness")
    if outputs.get("article") != article_sha256:
        raise ValueError("preflight stage receipt does not bind the final article")


def validate_preflight_stage_receipt_binding(
    receipt: Mapping[str, Any],
    *,
    prior_receipts: Sequence[Mapping[str, Any]],
    readiness_path: str | Path,
    article_sha256: Any,
    article_path: str | Path,
    workspace_root: str | Path,
    assembly_date: str | date,
) -> None:
    """Validate one readiness receipt against its exact run, inputs, and outputs."""
    try:
        from ..blog_assembly_stage_receipt import check_receipt_chain, check_stage_receipt
    except ImportError:  # pragma: no cover - supports direct script execution.
        from blog_assembly_stage_receipt import check_receipt_chain, check_stage_receipt
    if not isinstance(prior_receipts, (list, tuple)) or any(
        not isinstance(row, Mapping) for row in prior_receipts
    ):
        raise ValueError("prior_receipts must be a list of receipt objects")
    final_article_sha256 = validate_sha256(
        article_sha256,
        field="article_sha256",
    )
    optimized = any(
        isinstance(row, Mapping)
        and row.get("stage")
        in {
            "optimization",
            "post_optimization_scrub",
            "post_optimization_context_binding",
        }
        for row in prior_receipts
    )
    expected_stage = "final_preflight_readiness" if optimized else "preflight_readiness"
    findings = check_stage_receipt(
        receipt,
        expected_stage=expected_stage,
        expected_tool_name="publish_readiness",
        expected_tool_version="1.0.0",
    )
    expected_run_id = _receipt_chain_run_id(
        [*prior_receipts, receipt],
        article_path=article_path,
        workspace_root=workspace_root,
        assembly_date=assembly_date,
    )
    findings.extend(
        check_receipt_chain(
            [*prior_receipts, receipt],
            expected_run_id=expected_run_id,
            assembly_date=assembly_date,
        )
    )
    if findings:
        raise ValueError(
            "preflight stage receipt is invalid: "
            + ", ".join(sorted({str(finding["rule_id"]) for finding in findings}))
        )
    readiness_file = Path(readiness_path)
    readiness = _read_json_object(readiness_file, "preflight_readiness")
    _validate_receipt_readiness_bindings(
        receipt,
        readiness,
        readiness_path=readiness_file,
        article_sha256=final_article_sha256,
    )

def write_blog_assembly_bom(path: str | Path, bom: Mapping[str, Any]) -> None:
    """Persist a deterministic BOM atomically."""
    atomic_write_json(path, bom)


__all__ = ['_readiness_receipt_path', '_validate_final_bom_guard', '_validate_persisted_readiness_contract', '_validate_preflight_stage_receipt', '_validate_provisional_bom_guard', 'build_blog_assembly_bom', 'finalize_blog_assembly_bom', 'validate_preflight_stage_receipt_binding', 'write_blog_assembly_bom']
