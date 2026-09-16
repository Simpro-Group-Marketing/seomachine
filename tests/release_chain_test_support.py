from __future__ import annotations

import hashlib
import json
from pathlib import Path

from data_sources.modules.blog_assembly.common import (
    file_sha256,
    normalized_text_sha256,
)
from data_sources.modules.blog_assembly_stage_receipt import (
    build_stage_receipt,
    load_stage_receipt,
    write_stage_evidence,
    write_stage_receipt,
)
from data_sources.modules.readiness.persistence_api import (
    readiness_stage_receipt_path,
)


def write_optimized_tail_receipts(
    tmp_path: Path,
    *,
    article: Path,
    sidecar: Path,
    prior_preflight: Path,
) -> tuple[Path, Path, Path]:
    article_hash = file_sha256(article)
    readiness_receipt = load_stage_receipt(
        readiness_stage_receipt_path(prior_preflight),
        workspace_root=tmp_path,
    )
    optimization = build_stage_receipt(
        run_id="run-123",
        stage="optimization",
        tool_name="optimize-command",
        tool_version="1",
        started_at="2026-01-15T12:01:10Z",
        completed_at="2026-01-15T12:02:00Z",
        mutation=True,
        input_artifact_hashes={
            "article": readiness_receipt["output_artifact_hashes"]["article"],
        },
        output_artifact_hashes={"article": article_hash},
        previous_receipt_hash=readiness_receipt["receipt_hash"],
        workspace_root=tmp_path,
    )
    optimization_path = tmp_path / "research" / "stage-optimization.json"
    write_stage_receipt(
        optimization_path,
        optimization,
        workspace_root=tmp_path,
    )

    scrub_path = tmp_path / "research" / "stage-post-optimization-scrub.json"
    scrub_statistics = {
        "ai_phrases_replaced": 0,
        "emdashes_replaced": 0,
        "format_control_removed": 0,
    }
    scrub_evidence = {
        "scrub_statistics": _logical_evidence_sha256(scrub_statistics),
    }
    _, scrub_evidence_hash = write_stage_evidence(
        scrub_path,
        evidence_hashes=scrub_evidence,
        payload={"statistics": scrub_statistics, "would_change": False},
    )
    scrub = build_stage_receipt(
        run_id="run-123",
        stage="post_optimization_scrub",
        tool_name="content_scrubber",
        tool_version="1.0.0",
        started_at="2026-01-15T12:03:00Z",
        completed_at="2026-01-15T12:04:00Z",
        mutation=False,
        input_artifact_hashes={"article": article_hash},
        output_artifact_hashes={
            "article": article_hash,
            "stage_evidence": scrub_evidence_hash,
        },
        evidence_hashes=scrub_evidence,
        previous_receipt_hash=optimization["receipt_hash"],
        workspace_root=tmp_path,
    )
    write_stage_receipt(scrub_path, scrub, workspace_root=tmp_path)

    binding_path = tmp_path / "research" / "stage-post-optimization-binding.json"
    reason = "The optimized article has no connector-sensitive content."
    binding_payload = {
        "article_sha256": article_hash,
        "reason": reason,
        "schema": "seomachine-context-binding-not-applicable/v1",
        "status": "not_applicable",
        "validation_sidecar_sha256": file_sha256(sidecar),
    }
    binding_evidence = {
        "context_binding": _logical_evidence_sha256(binding_payload),
        "not_applicable_reason": normalized_text_sha256(
            reason, field="not_applicable_reason"
        ),
    }
    _, binding_evidence_hash = write_stage_evidence(
        binding_path,
        evidence_hashes=binding_evidence,
        payload=binding_payload,
    )
    binding = build_stage_receipt(
        run_id="run-123",
        stage="post_optimization_context_binding",
        tool_name="context_binding_generator",
        tool_version="1.0.0",
        started_at="2026-01-15T12:05:00Z",
        completed_at="2026-01-15T12:06:00Z",
        mutation=False,
        input_artifact_hashes={
            "article": article_hash,
            "validation_sidecar": file_sha256(sidecar),
        },
        output_artifact_hashes={
            "article": article_hash,
            "validation_sidecar": file_sha256(sidecar),
            "stage_evidence": binding_evidence_hash,
        },
        evidence_hashes=binding_evidence,
        previous_receipt_hash=scrub["receipt_hash"],
        workspace_root=tmp_path,
    )
    write_stage_receipt(binding_path, binding, workspace_root=tmp_path)
    return optimization_path, scrub_path, binding_path


def _logical_evidence_sha256(payload: dict[str, object]) -> str:
    encoded = json.dumps(
        payload, ensure_ascii=True, separators=(",", ":"), sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def rewrite_stage_receipt_evidence(
    receipt_path: Path,
    *,
    evidence_hashes: dict[str, str],
    payload: dict[str, object],
    workspace_root: Path,
    previous_receipt_hash: str | None = None,
) -> dict[str, object]:
    receipt = load_stage_receipt(receipt_path, workspace_root=workspace_root)
    _, artifact_hash = write_stage_evidence(
        receipt_path,
        evidence_hashes=evidence_hashes,
        payload=payload,
    )
    replacement = build_stage_receipt(
        run_id=receipt["run_id"],
        stage=receipt["stage"],
        tool_name=receipt["tool"]["name"],
        tool_version=receipt["tool"]["version"],
        started_at=receipt["started_at"],
        completed_at=receipt["completed_at"],
        mutation=receipt["mutation"],
        input_artifact_hashes=receipt["input_artifact_hashes"],
        output_artifact_hashes={
            **receipt["output_artifact_hashes"],
            "stage_evidence": artifact_hash,
        },
        evidence_hashes=evidence_hashes,
        previous_receipt_hash=(
            receipt["previous_receipt_hash"]
            if previous_receipt_hash is None
            else previous_receipt_hash
        ),
        workspace_root=workspace_root,
    )
    write_stage_receipt(receipt_path, replacement, workspace_root=workspace_root)
    return replacement
