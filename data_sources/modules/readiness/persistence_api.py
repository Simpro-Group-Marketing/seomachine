"""Publish-readiness persistence api responsibilities."""
# ruff: noqa: F403, F405

from .common import *  # noqa: F403


def readiness_stage_receipt_path(output_path: str | Path) -> Path:
    """Return the deterministic detached receipt path for a readiness output."""
    output = Path(output_path)
    return output.with_name(f"{output.stem}-stage-receipt.json")


def _receipt_context(
    result: Mapping[str, Any],
    *,
    workspace_root: Path,
) -> tuple[str, bool, list[Mapping[str, Any]], str | None, str | None]:
    bom_path = result.get("assembly_bom")
    if not isinstance(bom_path, str) or not bom_path:
        return "", False, [], None, None
    try:
        bom = load_json_object_snapshot(bom_path, field="assembly BOM").payload
    except ValueError as error:
        raise ValueError(f"readiness BOM is unavailable: {error}") from error
    workflow = bom.get("workflow") if isinstance(bom, Mapping) else None
    assembly_date = (
        str(bom.get("assembly_date"))
        if isinstance(bom, Mapping) and isinstance(bom.get("assembly_date"), str)
        else None
    )
    if assembly_date is None:
        raise ValueError("readiness BOM requires a canonical assembly_date")
    run_id = canonical_article_run_id(
        str(result.get("file") or ""),
        workspace_root=workspace_root,
        assembly_date=assembly_date,
    )
    rows = workflow.get("stage_receipts") if isinstance(workflow, Mapping) else None
    if not isinstance(rows, list) or not rows:
        return "", False, [], assembly_date, run_id
    if any(not isinstance(row, Mapping) for row in rows):
        raise ValueError("readiness BOM contains an invalid stage receipt chain")
    receipts = list(rows)
    run_ids = {str(row.get("run_id") or "").strip() for row in receipts}
    run_ids.discard("")
    if len(run_ids) == 1:
        run_id = next(iter(run_ids))
    previous_hash = str(receipts[-1].get("receipt_hash") or "")
    optimized = any(row.get("stage") in {
        "optimization", "post_optimization_scrub", "post_optimization_context_binding"
    } for row in receipts)
    return previous_hash, optimized, receipts, assembly_date, run_id


def _readiness_receipt_stage(result: Mapping[str, Any], optimized: bool) -> str:
    if result.get("phase") == "final":
        return "final_readiness_attestation"
    return "final_preflight_readiness" if optimized else "preflight_readiness"


def _validate_built_receipt_chain(
    receipt: Mapping[str, Any],
    prior_receipts: Sequence[Mapping[str, Any]],
    *,
    expected_run_id: str | None,
    assembly_date: str | None,
) -> None:
    if not prior_receipts:
        return
    if expected_run_id is None or assembly_date is None:
        raise ValueError("readiness stage receipt requires canonical workflow identity")
    findings = check_receipt_chain(
        [*prior_receipts, receipt],
        expected_run_id=expected_run_id,
        assembly_date=assembly_date,
    )
    if findings:
        rules = ", ".join(sorted({str(finding["rule_id"]) for finding in findings}))
        raise ValueError(f"readiness stage receipt chain is invalid: {rules}")


def write_readiness_result(
    output_path: str | Path,
    result: Mapping[str, Any],
    *,
    receipt_path: str | Path | None = None,
    workspace_root: str | Path | None = None,
) -> Path | None:
    """Write the result and, when passed, its non-circular stage receipt."""
    root = _result_workspace_root(result, workspace_root)
    output = _resolve_workspace_input(
        output_path,
        workspace_root=root,
        field="readiness output",
    )
    destination = (
        _resolve_workspace_input(
            receipt_path,
            workspace_root=root,
            field="readiness receipt",
        )
        if receipt_path is not None
        else readiness_stage_receipt_path(output)
    )
    _reject_output_input_collision(output, result, workspace_root=root)
    if result.get("passed") is not True:
        atomic_write_json(output, result)
        return None
    validate_passed_readiness_result(result, workspace_root=root)
    input_rows = result.get("input_hashes")
    input_hashes = {
        str(label): str(row.get("sha256"))
        for label, row in input_rows.items()
        if isinstance(row, Mapping) and isinstance(row.get("sha256"), str)
    }
    article_hash = input_hashes.get("article")
    if not article_hash:
        raise ValueError("passed readiness result requires the article input hash")
    previous_hash, optimized, prior_receipts, bom_assembly_date, expected_chain_run_id = (
        _receipt_context(result, workspace_root=root)
    )
    stage = _readiness_receipt_stage(result, optimized)
    if _same_path(destination, output):
        raise ValueError("readiness receipt cannot overwrite readiness output")
    _reject_output_input_collision(
        destination,
        result,
        output_label="readiness receipt",
        workspace_root=root,
    )
    output_digest = hashlib.sha256(canonical_json_bytes(result)).hexdigest()
    receipt = build_stage_receipt(
        run_id=str(result.get("run_id") or ""),
        stage=stage,
        tool_name="publish_readiness",
        tool_version="1.0.0",
        started_at=str(result.get("started_at") or ""),
        completed_at=str(result.get("completed_at") or ""),
        mutation=False,
        input_artifact_hashes=input_hashes,
        output_artifact_hashes={
            "article": article_hash,
            "readiness_output": output_digest,
        },
        evidence_hashes={
            label: digest
            for label, digest in input_hashes.items()
            if label not in {"article", "assembly_bom"}
        },
        previous_receipt_hash=previous_hash,
    )
    _validate_built_receipt_chain(
        receipt,
        prior_receipts,
        expected_run_id=expected_chain_run_id,
        assembly_date=bom_assembly_date,
    )
    _validate_actual_readiness_execution(result, workspace_root=root)
    return persist_result_pair(
        output,
        result,
        destination,
        receipt,
        receipt_writer=write_stage_receipt,
    )


__all__ = ['readiness_stage_receipt_path', 'write_readiness_result']
