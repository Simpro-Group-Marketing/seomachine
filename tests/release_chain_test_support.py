from __future__ import annotations

from pathlib import Path

from data_sources.modules.blog_assembly.common import (
    canonical_json_sha256,
    file_sha256,
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
        "scrub_statistics": canonical_json_sha256(scrub_statistics),
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
    binding_payload = {
        "article_sha256": article_hash,
        "status": "generated",
        "validation_sidecar_sha256": file_sha256(sidecar),
    }
    binding_evidence = {
        "context_binding": canonical_json_sha256(binding_payload),
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
