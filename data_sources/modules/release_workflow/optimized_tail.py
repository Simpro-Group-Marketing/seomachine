"""Optimized-tail receipt validation for release-chain decisions."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping, Sequence

from ..blog_assembly.common import (
    canonical_artifact,
    file_sha256,
    load_json_object_snapshot,
    normalized_text_sha256,
)
from ..blog_assembly.preflight import _resolvable_receipt_evidence_hashes
from ..blog_assembly_stage_receipt import (
    check_receipt_chain,
    load_stage_receipt,
    stage_evidence_path,
)


OPTIMIZED_TAIL_STAGES = ("post_optimization_scrub", "post_optimization_context_binding")
NOT_APPLICABLE_BINDING_SCHEMA = "seomachine-context-binding-not-applicable/v1"


def load_optimized_tail_receipts(
    paths: Sequence[str | Path], *, article_path: str | Path,
    proof_sidecar_path: str | Path, prior_preflight_readiness_path: str | Path | None,
    prior_preflight_receipt: Mapping[str, Any], run_id: str, workspace_root: Path,
) -> list[Mapping[str, Any]]:
    loaded, receipts = _tail_receipts_by_stage(paths, workspace_root=workspace_root)
    predecessor = _tail_predecessor(
        loaded,
        prior_preflight_receipt=prior_preflight_receipt,
    )
    _validate_receipt_link(predecessor, receipts[0])
    evidence_rows = []
    for receipt_path, receipt in zip(paths[-len(OPTIMIZED_TAIL_STAGES):], receipts):
        evidence_rows.append(_validate_tail_stage_evidence(
            receipt_path, receipt=receipt, workspace_root=workspace_root,
        ))
    if prior_preflight_readiness_path is None:
        raise ValueError("optimized-tail workflow requires prior preflight readiness evidence")
    resolvable_evidence_hashes = _resolvable_receipt_evidence_hashes(
        receipts,
        artifacts={
            "prior_preflight_readiness": canonical_artifact(
                prior_preflight_readiness_path,
                workspace_root=workspace_root,
            ),
            "stage_evidence": evidence_rows,
        },
        workspace_root=workspace_root,
    )
    _validate_tail_receipt_chain(
        receipts,
        run_id=run_id,
        resolvable_evidence_hashes=resolvable_evidence_hashes,
        workspace_root=workspace_root,
    )
    _validate_tail_article_binding(receipts, article_path=article_path)
    _validate_tail_sidecar_binding(receipts, proof_sidecar_path=proof_sidecar_path)
    return receipts


def _tail_receipts_by_stage(
    paths: Sequence[str | Path],
    *,
    workspace_root: Path,
) -> tuple[list[Mapping[str, Any]], list[Mapping[str, Any]]]:
    if len(paths) not in {len(OPTIMIZED_TAIL_STAGES), len(OPTIMIZED_TAIL_STAGES) + 1}:
        raise ValueError("optimized-tail authorization requires current scrub and context-binding "
                         "receipts plus an optimization receipt when article bytes changed")
    loaded = [load_stage_receipt(path, workspace_root=workspace_root) for path in paths]
    receipts = loaded[-len(OPTIMIZED_TAIL_STAGES):]
    stages = tuple(str(receipt.get("stage") or "") for receipt in receipts)
    if stages != OPTIMIZED_TAIL_STAGES:
        raise ValueError("optimized-tail receipt stages are out of order")
    return loaded, receipts


def _tail_predecessor(
    loaded: Sequence[Mapping[str, Any]],
    *,
    prior_preflight_receipt: Mapping[str, Any],
) -> Mapping[str, Any]:
    if len(loaded) == len(OPTIMIZED_TAIL_STAGES):
        return prior_preflight_receipt
    predecessor = loaded[0]
    if predecessor.get("stage") != "optimization":
        raise ValueError("optimized-tail predecessor must be an optimization receipt")
    _validate_receipt_link(prior_preflight_receipt, predecessor)
    return predecessor


def _validate_tail_receipt_chain(
    receipts: Sequence[Mapping[str, Any]],
    *,
    run_id: str,
    resolvable_evidence_hashes: Mapping[str, str],
    workspace_root: Path,
) -> None:
    findings = check_receipt_chain(
        receipts,
        expected_run_id=run_id,
        resolvable_evidence_hashes=resolvable_evidence_hashes,
        workspace_root=workspace_root,
    )
    if findings:
        rules = ", ".join(sorted({str(row["rule_id"]) for row in findings}))
        raise ValueError(f"optimized-tail receipt chain is invalid: {rules}")


def _validate_tail_article_binding(
    receipts: Sequence[Mapping[str, Any]],
    *,
    article_path: str | Path,
) -> None:
    article_sha256 = file_sha256(article_path)
    for receipt in receipts:
        if (receipt["input_artifact_hashes"].get("article") != article_sha256
                or receipt["output_artifact_hashes"].get("article") != article_sha256):
            raise ValueError("optimized-tail receipts do not bind the current article")


def _validate_tail_sidecar_binding(
    receipts: Sequence[Mapping[str, Any]],
    *,
    proof_sidecar_path: str | Path,
) -> None:
    if "scrub_statistics" not in receipts[0]["evidence_hashes"]:
        raise ValueError("post-optimization scrub receipt lacks scrub statistics")
    if (receipts[1]["output_artifact_hashes"].get("validation_sidecar")
            != file_sha256(proof_sidecar_path)
            or "context_binding" not in receipts[1]["evidence_hashes"]):
        raise ValueError("post-optimization context receipt does not bind the current sidecar")


def _validate_tail_stage_evidence(
    receipt_path: str | Path, *, receipt: Mapping[str, Any], workspace_root: Path,
) -> Mapping[str, str]:
    stage = str(receipt.get("stage") or "")
    evidence_path = stage_evidence_path(receipt_path)
    evidence_row = canonical_artifact(evidence_path, workspace_root=workspace_root)
    outputs = receipt.get("output_artifact_hashes")
    if not isinstance(outputs, Mapping) or outputs.get("stage_evidence") != evidence_row["sha256"]:
        raise ValueError(f"{stage} receipt does not bind its stage evidence artifact")
    manifest = load_json_object_snapshot(
        evidence_path, field=f"{stage} stage evidence",
    ).payload
    declared = manifest.get("evidence_hashes")
    if declared != receipt.get("evidence_hashes"):
        raise ValueError(f"{stage} receipt evidence hashes do not match its artifact")
    payload = manifest.get("payload")
    if not isinstance(payload, Mapping):
        raise ValueError(f"{stage} evidence payload is invalid")
    expected = _expected_tail_evidence(stage, payload)
    if declared != expected:
        raise ValueError(f"{stage} logical evidence hashes do not match its payload")
    return evidence_row


def _expected_tail_evidence(stage: str, payload: Mapping[str, Any]) -> dict[str, str]:
    if stage == "post_optimization_scrub":
        statistics = payload.get("statistics")
        if (set(payload) != {"statistics", "would_change"}
                or not isinstance(statistics, Mapping)
                or payload.get("would_change") is not False):
            raise ValueError("post-optimization scrub evidence payload is invalid")
        return {"scrub_statistics": _logical_evidence_sha256(statistics)}
    expected = {"context_binding": _logical_evidence_sha256(payload)}
    if payload.get("schema") == NOT_APPLICABLE_BINDING_SCHEMA:
        required = {"article_sha256", "reason", "schema", "status", "validation_sidecar_sha256"}
        if set(payload) != required or payload.get("status") != "not_applicable":
            raise ValueError("post-optimization context evidence payload is invalid")
        expected["not_applicable_reason"] = normalized_text_sha256(
            payload.get("reason"), field="not_applicable_reason",
        )
    elif (set(payload) != {"binding", "claim_use_map"}
          or not isinstance(payload.get("binding"), Mapping)
          or not isinstance(payload.get("claim_use_map"), list)):
        raise ValueError("post-optimization context evidence payload is invalid")
    return expected


def _logical_evidence_sha256(payload: Mapping[str, Any]) -> str:
    encoded = json.dumps(
        dict(payload), ensure_ascii=True, separators=(",", ":"), sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _validate_receipt_link(predecessor: Mapping[str, Any], receipt: Mapping[str, Any]) -> None:
    if receipt.get("previous_receipt_hash") != predecessor.get("receipt_hash"):
        raise ValueError("optimized-tail receipt predecessor hash is not verified")
    if receipt.get("run_id") != predecessor.get("run_id"):
        raise ValueError("optimized-tail receipt predecessor run_id does not match")
    predecessor_outputs = predecessor.get("output_artifact_hashes")
    receipt_inputs = receipt.get("input_artifact_hashes")
    if (
        not isinstance(predecessor_outputs, Mapping)
        or not isinstance(receipt_inputs, Mapping)
        or receipt_inputs.get("article") != predecessor_outputs.get("article")
    ):
        raise ValueError("optimized-tail receipt predecessor article hash is not continuous")
    predecessor_completed = datetime.fromisoformat(str(predecessor.get("completed_at")).replace("Z", "+00:00"))
    receipt_started = datetime.fromisoformat(str(receipt.get("started_at")).replace("Z", "+00:00"))
    if receipt_started <= predecessor_completed:
        raise ValueError("optimized-tail receipt predecessor timestamps are not monotonic")


__all__ = ["load_optimized_tail_receipts"]
