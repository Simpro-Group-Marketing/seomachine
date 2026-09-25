"""Decide whether a blog release needs the normal chain or optimized tail."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

from .. import (
    blog_assembly_capabilities,
    machine_review,
    optimizer_evidence,
)
from ..blog_assembly.common import (
    canonical_artifact,
    load_json_object_snapshot,
    verify_artifact,
)
from ..blog_assembly.execution_evidence import resolve_execution_evidence
from ..blog_assembly.stage_receipts import _validate_prior_preflight_readiness
from ..blog_assembly_stage_receipt import load_stage_receipt
from .collection_reports import check_collection_report
from .optimized_tail import load_optimized_tail_receipts
from ..readiness.persistence_api import readiness_stage_receipt_path


NORMAL_CHAIN_REQUIRED = "normal_chain_required"
OPTIMIZED_TAIL_ALLOWED = "optimized_tail_allowed"
DRAFT_READY_NOT_RELEASE_READY = "draft_ready_not_release_ready"
REVIEW_PHASES = frozenset({"plan", "article"})


@dataclass(frozen=True, slots=True)
class ReleaseChainDecision:
    """One stable release-chain decision and its machine-readable rationale."""

    decision: str
    code: str
    reason: str
    blockers: tuple[str, ...] = ()


def decide_release_chain(
    *,
    article_path: str | Path,
    editorial_plan_path: str | Path,
    proof_sidecar_path: str | Path,
    machine_review_paths: Mapping[str, str | Path],
    machine_review_collection_report_paths: Mapping[str, str | Path],
    optimizer_output_paths: Sequence[str | Path],
    prior_preflight_readiness_path: str | Path | None,
    stage_receipt_paths: Sequence[str | Path],
    agent_output_paths: Mapping[str, str | Path],
    run_id: str,
    workspace_root: str | Path,
) -> ReleaseChainDecision:
    """Compose current evidence validators into a release-chain decision."""
    review_decision = _machine_review_decision(
        article_path=article_path,
        editorial_plan_path=editorial_plan_path,
        proof_sidecar_path=proof_sidecar_path,
        machine_review_paths=machine_review_paths,
        collection_report_paths=machine_review_collection_report_paths,
        run_id=run_id,
    )
    if review_decision is not None:
        return review_decision

    has_optimizer = bool(optimizer_output_paths)
    has_prior_preflight = prior_preflight_readiness_path is not None
    if not has_optimizer and not has_prior_preflight:
        return ReleaseChainDecision(
            NORMAL_CHAIN_REQUIRED,
            "optimized_tail_evidence_absent",
            "No optimizer output or prior preflight was supplied; run the normal chain.",
        )
    if has_optimizer != has_prior_preflight:
        return ReleaseChainDecision(
            NORMAL_CHAIN_REQUIRED,
            "optimized_tail_evidence_incomplete",
            "Optimizer output and prior preflight evidence must be supplied together.",
        )

    root = Path(workspace_root).resolve()
    try:
        prior_preflight_receipt = _validate_prior_preflight(
            prior_preflight_readiness_path,
            run_id=run_id,
            workspace_root=root,
        )
        stage_receipts = load_optimized_tail_receipts(
            stage_receipt_paths,
            article_path=article_path,
            proof_sidecar_path=proof_sidecar_path,
            prior_preflight_readiness_path=prior_preflight_readiness_path,
            prior_preflight_receipt=prior_preflight_receipt,
            run_id=run_id,
            workspace_root=root,
        )
    except (OSError, TypeError, ValueError) as error:
        return ReleaseChainDecision(
            NORMAL_CHAIN_REQUIRED,
            "optimized_tail_receipts_invalid",
            f"Optimized-tail receipt or prior-preflight evidence is invalid: {error}",
            blockers=("optimized_tail_receipts_invalid",),
        )

    try:
        optimizer_evidence.validate_optimizer_outputs(
            optimizer_output_paths,
            article=article_path,
            editorial_plan=editorial_plan_path,
            proof_sidecar=proof_sidecar_path,
            prior_preflight_readiness=prior_preflight_readiness_path,
            workspace_root=root,
        )
    except optimizer_evidence.OptimizerEvidenceError as error:
        return ReleaseChainDecision(
            NORMAL_CHAIN_REQUIRED,
            error.code,
            str(error),
            blockers=(error.code,),
        )

    try:
        execution = resolve_execution_evidence(
            stage_receipts,
            prior_preflight_readiness_path=prior_preflight_readiness_path,
            agent_output_paths=agent_output_paths,
            workspace_root=root,
        )
    except blog_assembly_capabilities.CapabilityRegistryError as error:
        return ReleaseChainDecision(
            NORMAL_CHAIN_REQUIRED,
            "execution_evidence_invalid",
            str(error),
            blockers=("execution_evidence_invalid",),
        )
    if execution.normal_chain_required:
        stale = execution.stale_artifact
        blocker = stale.label if stale is not None else "execution_evidence"
        return ReleaseChainDecision(
            NORMAL_CHAIN_REQUIRED,
            "execution_evidence_stale",
            f"Copied execution evidence is stale for {blocker}; run the normal chain.",
            blockers=(blocker,),
        )

    return ReleaseChainDecision(
        OPTIMIZED_TAIL_ALLOWED,
        "optimized_tail_evidence_valid",
        "Optimizer, prior-preflight, execution, and machine-review evidence are current.",
    )


def _machine_review_decision(
    *,
    article_path: str | Path,
    editorial_plan_path: str | Path,
    proof_sidecar_path: str | Path,
    machine_review_paths: Mapping[str, str | Path],
    collection_report_paths: Mapping[str, str | Path],
    run_id: str,
) -> ReleaseChainDecision | None:
    observed_phases = set(collection_report_paths)
    observed_review_phases = set(machine_review_paths)
    if observed_phases != REVIEW_PHASES or observed_review_phases != REVIEW_PHASES:
        mismatches = tuple(
            sorted(
                {
                    *(f"collection_status.{phase}" for phase in REVIEW_PHASES ^ observed_phases),
                    *(f"review_artifact.{phase}" for phase in REVIEW_PHASES ^ observed_review_phases),
                }
            )
        )
        return ReleaseChainDecision(
            DRAFT_READY_NOT_RELEASE_READY,
            "machine_review_collection_mismatch",
            "Machine-review collection statuses and artifacts must cover plan and article.",
            blockers=mismatches,
        )
    findings = []
    for phase in sorted(REVIEW_PHASES):
        report_findings = check_collection_report(
            collection_report_paths[phase],
            review_path=machine_review_paths[phase],
            editorial_plan_path=editorial_plan_path,
            article_path=article_path,
            proof_sidecar_path=proof_sidecar_path,
            expected_run_id=run_id,
            expected_phase=phase,
        )
        if report_findings:
            code = (
                "machine_review_collection_incomplete"
                if report_findings == ["machine_review_collection_incomplete"]
                else "machine_review_collection_invalid"
            )
            return ReleaseChainDecision(
                DRAFT_READY_NOT_RELEASE_READY,
                code,
                "Machine-review collection reports must be complete and bind the current review artifacts.",
                blockers=tuple(report_findings),
            )
        findings.extend(
            machine_review.check_machine_review_file(
                machine_review_paths[phase],
                proof_sidecar_path=proof_sidecar_path,
                editorial_plan_path=editorial_plan_path,
                article_path=article_path,
                expected_run_id=run_id,
                expected_phase=phase,
            )
        )
    findings.extend(
        machine_review.check_machine_review_pair(
            machine_review_paths["plan"],
            machine_review_paths["article"],
            expected_run_id=run_id,
        )
    )
    if findings:
        blockers = tuple(
            sorted(
                {
                    str(finding.get("rule_id") or "machine_review_invalid")
                    for finding in findings
                }
            )
        )
        return ReleaseChainDecision(
            DRAFT_READY_NOT_RELEASE_READY,
            "machine_review_invalid",
            "Machine reviews do not match the current release inputs.",
            blockers=blockers,
        )
    return None


def _validate_prior_preflight(
    path: str | Path | None, *, run_id: str, workspace_root: Path,
) -> Mapping[str, Any]:
    if path is None:
        raise ValueError("optimized-tail workflow requires prior preflight readiness evidence")
    canonical_artifact(path, workspace_root=workspace_root)
    readiness = load_json_object_snapshot(path, field="prior preflight readiness").payload
    inputs = readiness.get("input_hashes")
    if not isinstance(inputs, Mapping):
        raise ValueError("prior preflight readiness input hashes are invalid")
    bom_row = inputs.get("assembly_bom")
    if not isinstance(bom_row, Mapping):
        raise ValueError("prior preflight readiness lacks its assembly BOM binding")
    bom_path = verify_artifact(
        bom_row,
        workspace_root=workspace_root,
        field="prior_preflight_readiness.input_hashes.assembly_bom",
    )
    prior_bom = load_json_object_snapshot(
        bom_path,
        field="prior preflight BOM",
    ).payload
    schema_policy = prior_bom.get("schema_policy")
    connector_binding = prior_bom.get("connector_binding")
    if not isinstance(schema_policy, Mapping) or not isinstance(connector_binding, Mapping):
        raise ValueError("prior preflight BOM policy bindings are invalid")
    receipt = load_stage_receipt(readiness_stage_receipt_path(path), workspace_root=workspace_root)
    if receipt.get("stage") != "preflight_readiness":
        raise ValueError("prior preflight readiness receipt stage is invalid")
    validated = _validate_prior_preflight_readiness(
        path,
        receipt=receipt,
        visible_faq=schema_policy.get("visible_faq") is True,
        connector_required=connector_binding.get("status") == "required",
        workspace_root=workspace_root,
    )
    if validated.get("run_id") != run_id:
        raise ValueError("prior preflight readiness run_id does not match the release run")
    return receipt


__all__ = [
    "DRAFT_READY_NOT_RELEASE_READY",
    "NORMAL_CHAIN_REQUIRED",
    "OPTIMIZED_TAIL_ALLOWED",
    "ReleaseChainDecision",
    "decide_release_chain",
]
