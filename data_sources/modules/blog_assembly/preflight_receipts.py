"""Preflight readiness stage-receipt binding checks."""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any, Mapping, Sequence

from ..blog_assembly_stage_receipt import check_receipt_chain, check_stage_receipt
from .common import canonical_article_run_id, file_sha256, validate_sha256
from .contracts import _read_json_object, _required_mapping


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
    readiness_sha256: str,
    article_sha256: str,
) -> None:
    outputs = receipt.get("output_artifact_hashes")
    if not isinstance(outputs, Mapping) or outputs.get("readiness_output") != readiness_sha256:
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
    readiness_payload: Mapping[str, Any] | None = None,
    readiness_sha256: str | None = None,
) -> None:
    """Validate one readiness receipt against its exact run, inputs, and outputs."""
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
        workspace_root=workspace_root,
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
            workspace_root=workspace_root,
        )
    )
    if findings:
        raise ValueError(
            "preflight stage receipt is invalid: "
            + ", ".join(sorted({str(finding["rule_id"]) for finding in findings}))
        )
    readiness_file = Path(readiness_path)
    readiness = (
        readiness_payload
        if readiness_payload is not None
        else _read_json_object(readiness_file, "preflight_readiness")
    )
    observed_sha256 = (
        validate_sha256(readiness_sha256, field="readiness_sha256")
        if readiness_sha256 is not None
        else file_sha256(readiness_file)
    )
    _validate_receipt_readiness_bindings(
        receipt,
        readiness,
        readiness_sha256=observed_sha256,
        article_sha256=final_article_sha256,
    )


__all__ = ["validate_preflight_stage_receipt_binding"]
