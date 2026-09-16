"""Decide whether a blog release needs the normal chain or optimized tail."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

from .. import blog_assembly_capabilities, machine_review, optimizer_evidence
from ..blog_assembly.execution_evidence import resolve_execution_evidence


NORMAL_CHAIN_REQUIRED = "normal_chain_required"
OPTIMIZED_TAIL_ALLOWED = "optimized_tail_allowed"
DRAFT_READY_NOT_RELEASE_READY = "draft_ready_not_release_ready"
REVIEW_COLLECTED = "review_collected"
REVIEW_PHASES = frozenset({"plan", "article"})
OPTIMIZED_TAIL_STAGES = (
    "post_optimization_scrub",
    "post_optimization_context_binding",
)


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
    machine_review_collection_statuses: Mapping[str, str],
    optimizer_output_paths: Sequence[str | Path],
    prior_preflight_readiness_path: str | Path | None,
    stage_receipts: Sequence[Mapping[str, Any]],
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
        collection_statuses=machine_review_collection_statuses,
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

    stages = tuple(str(receipt.get("stage") or "") for receipt in stage_receipts)
    if stages != OPTIMIZED_TAIL_STAGES:
        return ReleaseChainDecision(
            NORMAL_CHAIN_REQUIRED,
            "optimized_tail_receipts_invalid",
            "Optimized-tail authorization requires the current scrub and context-binding receipts.",
            blockers=stages,
        )

    try:
        optimizer_evidence.validate_optimizer_outputs(
            optimizer_output_paths,
            article=article_path,
            editorial_plan=editorial_plan_path,
            proof_sidecar=proof_sidecar_path,
            prior_preflight_readiness=prior_preflight_readiness_path,
            workspace_root=workspace_root,
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
            workspace_root=Path(workspace_root).resolve(),
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
    collection_statuses: Mapping[str, str],
    run_id: str,
) -> ReleaseChainDecision | None:
    observed_phases = set(collection_statuses)
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
    incomplete = tuple(
        phase
        for phase in sorted(REVIEW_PHASES)
        if collection_statuses[phase] != REVIEW_COLLECTED
    )
    if incomplete:
        return ReleaseChainDecision(
            DRAFT_READY_NOT_RELEASE_READY,
            "machine_review_collection_incomplete",
            "Every machine-review collection must have review_collected status.",
            blockers=incomplete,
        )

    findings = []
    for phase in sorted(REVIEW_PHASES):
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


__all__ = [
    "DRAFT_READY_NOT_RELEASE_READY",
    "NORMAL_CHAIN_REQUIRED",
    "OPTIMIZED_TAIL_ALLOWED",
    "ReleaseChainDecision",
    "decide_release_chain",
]
