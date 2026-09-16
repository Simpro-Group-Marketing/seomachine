"""Implementation for the proof-governed blog release sequence."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Mapping, Sequence

try:
    from . import (
        blog_creation_preflight,
        optimizer_evidence,
        release_authorization,
    )
    from .blog_assembly_contract import atomic_write_json, validate_sha256
    from .blog_assembly import construction as blog_assembly_construction
    from .blog_assembly import finalization as blog_assembly_finalization
    from .artifact_runtime.release_invocation import (
        ReleaseInvocationError,
        ReleaseResult,
        validate_release_invocation,
    )
    from .release_workflow.optimization import (
        ReleasePolicyError,
        begin_optimization_run,
    )
    from .release_workflow.paths import blog_release_paths, new_output_dir
    from .readiness import api as readiness_api
    from .readiness import persistence_api as readiness_persistence_api
    from .readiness.telemetry import ReadinessTelemetry
except ImportError:  # pragma: no cover - supports direct script execution.
    import blog_creation_preflight
    import optimizer_evidence
    import release_authorization
    from blog_assembly_contract import atomic_write_json, validate_sha256
    import blog_assembly.construction as blog_assembly_construction
    import blog_assembly.finalization as blog_assembly_finalization
    from artifact_runtime.release_invocation import (
        ReleaseInvocationError,
        ReleaseResult,
        validate_release_invocation,
    )
    from release_workflow.optimization import (
        ReleasePolicyError,
        begin_optimization_run,
    )
    from release_workflow.paths import blog_release_paths, new_output_dir
    import readiness.api as readiness_api
    import readiness.persistence_api as readiness_persistence_api
    from readiness.telemetry import ReadinessTelemetry

blog_assembly_bom = SimpleNamespace(
    build_blog_assembly_bom_from_files=(
        blog_assembly_construction.build_blog_assembly_bom_from_files
    ),
    finalize_blog_assembly_bom=blog_assembly_finalization.finalize_blog_assembly_bom,
)
publish_readiness = SimpleNamespace(
    build_final_readiness_attestation=readiness_api.build_final_readiness_attestation,
    run_publish_readiness=readiness_api.run_publish_readiness,
    write_readiness_result=readiness_persistence_api.write_readiness_result,
)


def _run_blog_release(
    *,
    article: str | Path,
    run_id: str,
    proof_sidecar: str | Path,
    editorial_plan: str | Path,
    plan_review: str | Path,
    article_review: str | Path,
    keyword_decision: str | Path,
    scrub_receipt: str | Path,
    serp_evidence: str | Path,
    plan_fulfillment: str | Path,
    commercial_pillar_index: str | Path,
    stage_receipts: Sequence[str | Path],
    workflow_mode: str,
    assembly_date: str,
    output_dir: str | Path,
    context_request: str | Path | None = None,
    context_pack: str | Path | None = None,
    context_receipt: str | Path | None = None,
    customer_proof_evidence: str | Path | None = None,
    fred_authority_evidence: str | Path | None = None,
    paa_artifact: str | Path | None = None,
    content_brief: str | Path | None = None,
    user_paa_csv: str | Path | None = None,
    answersocrates_blocker: str | Path | None = None,
    optimizer_outputs: Sequence[str | Path] | None = None,
    prior_preflight_readiness: str | Path | None = None,
    agent_output_paths: Mapping[str, str | Path] | None = None,
    workspace_root: str | Path | None = None,
    vault_root: str | Path | None = None,
) -> ReleaseResult:
    """Run the governed release sequence with mandatory optimization evidence."""
    root = Path(workspace_root or Path.cwd()).resolve()
    optimizer_outputs = tuple(optimizer_outputs or ())
    normalized_agent_output_paths = dict(agent_output_paths or {})
    optimized_release = validate_release_invocation(
        required_files={
            "article": article,
            "proof_sidecar": proof_sidecar,
            "editorial_plan": editorial_plan,
            "plan_review": plan_review,
            "article_review": article_review,
            "keyword_decision": keyword_decision,
            "scrub_receipt": scrub_receipt,
            "serp_evidence": serp_evidence,
            "plan_fulfillment": plan_fulfillment,
            "commercial_pillar_index": commercial_pillar_index,
        },
        optional_files={
            "context_request": context_request,
            "context_pack": context_pack,
            "context_receipt": context_receipt,
            "customer_proof_evidence": customer_proof_evidence,
            "fred_authority_evidence": fred_authority_evidence,
            "paa_artifact": paa_artifact,
            "content_brief": content_brief,
            "user_paa_csv": user_paa_csv,
            "answersocrates_blocker": answersocrates_blocker,
        },
        stage_receipts=stage_receipts,
        optimizer_outputs=optimizer_outputs,
        prior_preflight_readiness=prior_preflight_readiness,
        agent_output_paths=normalized_agent_output_paths,
        run_id=run_id,
        workflow_mode=workflow_mode,
        workspace_root=root,
    )
    if optimized_release:
        try:
            optimizer_evidence.validate_optimizer_outputs(
                optimizer_outputs,
                article=article,
                editorial_plan=editorial_plan,
                proof_sidecar=proof_sidecar,
                prior_preflight_readiness=prior_preflight_readiness,
                workspace_root=root,
            )
        except optimizer_evidence.OptimizerEvidenceError as error:
            raise ReleaseInvocationError(str(error)) from error
    destination = new_output_dir(output_dir, workspace_root=root)
    release_stage_receipts = tuple(stage_receipts)
    if all(str(receipt) != str(scrub_receipt) for receipt in release_stage_receipts):
        release_stage_receipts = (scrub_receipt, *release_stage_receipts)

    paths = blog_release_paths(destination)
    telemetry = ReadinessTelemetry(
        run_id=run_id,
        phase="release",
        failure_output=paths["release_telemetry"],
    )

    def finish(result: ReleaseResult) -> ReleaseResult:
        telemetry.finish("passed" if result.exit_code == 0 else "blocked")
        telemetry.write(paths["release_telemetry"])
        return result

    with telemetry.stage("pre_bom"):
        pre_bom = blog_creation_preflight.build_preflight_report(
            article,
            proof_sidecar=proof_sidecar,
            context_request=context_request,
            context_pack=context_pack,
            context_receipt=context_receipt,
            keyword_decision=keyword_decision,
            assembly_date=assembly_date,
            output=paths["pre_bom_report"],
            scrub_receipt=scrub_receipt,
            customer_proof_evidence=customer_proof_evidence,
            fred_authority_evidence=fred_authority_evidence,
            editorial_plan=editorial_plan,
            serp_evidence=serp_evidence,
            stage_receipts=release_stage_receipts,
            paa_artifact=paa_artifact,
            content_brief=content_brief,
            user_paa_csv=user_paa_csv,
            answersocrates_blocker=answersocrates_blocker,
            workspace_root=root,
        )
        atomic_write_json(paths["pre_bom_report"], pre_bom)
    if pre_bom.get("ready_for_bom") is not True:
        return finish(
            ReleaseResult(1, destination, "pre_bom", "pre-BOM report blocked release")
        )

    with telemetry.stage("provisional_bom"):
        provisional = blog_assembly_bom.build_blog_assembly_bom_from_files(
            article_path=article,
            validation_sidecar_path=proof_sidecar,
            editorial_plan_path=editorial_plan,
            keyword_decision_path=keyword_decision,
            serp_evidence_path=serp_evidence,
            plan_fulfillment_path=plan_fulfillment,
            commercial_pillar_index_path=commercial_pillar_index,
            plan_review_path=plan_review,
            article_review_path=article_review,
            expected_review_run_id=run_id,
            stage_receipt_paths=release_stage_receipts,
            workflow_mode=workflow_mode,
            assembly_date=assembly_date,
            paa_artifact_path=paa_artifact,
            content_brief_path=content_brief,
            user_paa_csv_path=user_paa_csv,
            answersocrates_blocker_path=answersocrates_blocker,
            context_request_path=context_request,
            context_pack_path=context_pack,
            context_receipt_path=context_receipt,
            customer_proof_selector_evidence_path=customer_proof_evidence,
            fred_authority_evidence_path=fred_authority_evidence,
            agent_output_paths=normalized_agent_output_paths,
            optimizer_output_paths=optimizer_outputs,
            prior_preflight_readiness_path=prior_preflight_readiness,
            workspace_root=root,
            vault_root=vault_root,
        )
        atomic_write_json(paths["provisional_bom"], provisional)

    telemetry.increment("full_readiness_executions")
    with telemetry.stage("preflight_readiness"):
        preflight = publish_readiness.run_publish_readiness(
            article,
            proof_sidecar=proof_sidecar,
            context_request=context_request,
            context_pack=context_pack,
            context_receipt=context_receipt,
            assembly_bom=paths["provisional_bom"],
            phase="preflight",
            run_id=run_id,
            workspace_root=root,
            vault_root=vault_root,
            telemetry=telemetry,
        )
    telemetry.increment("gate_invocations", len(preflight.get("gates", [])))
    with telemetry.stage("preflight_persistence"):
        preflight_receipt_path = publish_readiness.write_readiness_result(
            paths["preflight_readiness"],
            preflight,
            receipt_path=paths["preflight_readiness_stage_receipt"],
            workspace_root=root,
        )
    if not optimized_release:
        recovery_artifact = begin_optimization_run(
            article=article,
            run_id=run_id,
            paths=paths,
            preflight=preflight,
            preflight_receipt_path=preflight_receipt_path,
            workspace_root=root,
        )
        if preflight.get("passed") is not True:
            return finish(ReleaseResult(
                0,
                destination,
                "optimization_started",
                "initial preflight readiness blocked; /optimize run started from blocker report",
                recovery_artifact=recovery_artifact,
            ))
        return finish(ReleaseResult(
            0,
            destination,
            "optimization_started",
            "initial preflight readiness completed; /optimize run started before final release",
            recovery_artifact=recovery_artifact,
        ))
    if preflight.get("passed") is not True:
        return finish(
            ReleaseResult(
                1,
                destination,
                "preflight_readiness",
                "preflight readiness blocked release",
            )
        )

    with telemetry.stage("bom_finalization"):
        final_bom = blog_assembly_bom.finalize_blog_assembly_bom(
            bom_path=paths["provisional_bom"],
            preflight_readiness_path=paths["preflight_readiness"],
            workspace_root=root,
            vault_root=vault_root,
        )
        atomic_write_json(paths["final_bom"], final_bom)

    with telemetry.stage("final_attestation"):
        final = publish_readiness.build_final_readiness_attestation(
            preflight,
            final_bom=paths["final_bom"],
            run_id=run_id,
            workspace_root=root,
            telemetry=telemetry,
            vault_root=vault_root,
        )
        final = release_authorization.prepare_final_release_result(
            final,
            release_manifest_path=paths["release_manifest"],
            previous_receipt_hash=_final_chain_head(final_bom),
            workspace_root=root,
        )
    with telemetry.stage("final_persistence"):
        publish_readiness.write_readiness_result(
            paths["final_readiness"],
            final,
            receipt_path=paths["final_readiness_stage_receipt"],
            workspace_root=root,
        )
        release_authorization.load_publish_authorization(
            final_readiness_path=paths["final_readiness"],
            final_receipt_path=paths["final_readiness_stage_receipt"],
            release_manifest_path=paths["release_manifest"],
            workspace_root=root,
        )
    if final.get("passed") is not True:
        return finish(
            ReleaseResult(1, destination, "final_readiness", "final readiness blocked release")
        )
    return finish(
        ReleaseResult(0, destination, "final_readiness", "final readiness passed")
    )


def _final_chain_head(final_bom: Mapping[str, object]) -> str:
    workflow = final_bom.get("workflow")
    receipts = workflow.get("stage_receipts") if isinstance(workflow, Mapping) else None
    if not isinstance(receipts, list) or not receipts:
        return ""
    last = receipts[-1]
    if not isinstance(last, Mapping):
        raise ReleasePolicyError("final BOM stage receipt chain is invalid")
    try:
        return validate_sha256(last.get("receipt_hash"), field="receipt_hash")
    except ValueError as error:
        raise ReleasePolicyError("final BOM stage receipt chain head is invalid") from error

__all__ = [
    "ReleaseInvocationError",
    "ReleasePolicyError",
    "ReleaseResult",
    "_run_blog_release",
    "blog_assembly_bom",
    "blog_creation_preflight",
    "publish_readiness",
    "release_authorization",
]
