"""Pre-output-directory checks for governed blog releases."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

try:
    from ..artifact_runtime.release_invocation import (
        ReleaseInvocationError,
        validate_release_invocation,
    )
    from ..blog_assembly_contract import atomic_write_json
    from . import precheck_checks, precheck_paths
    from .paths import workspace_path
except ImportError:  # pragma: no cover - supports direct script execution.
    from artifact_runtime.release_invocation import (
        ReleaseInvocationError,
        validate_release_invocation,
    )
    from blog_assembly_contract import atomic_write_json
    import release_workflow.precheck_checks as precheck_checks
    import release_workflow.precheck_paths as precheck_paths
    from release_workflow.paths import workspace_path

SCHEMA = "simpro-blog-release-precheck/v1"


@dataclass(frozen=True)
class BlogReleasePrecheckResult:
    passed: bool
    phase: str
    message: str
    output_dir: Path
    optimized_release: bool
    release_stage_receipts: tuple[str | Path, ...]
    pre_bom: Mapping[str, Any] | None = None
    provisional_bom: Mapping[str, Any] | None = None
    report_path: Path | None = None


def run_blog_release_precheck(
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
    context_request: str | Path | None,
    context_pack: str | Path | None,
    context_receipt: str | Path | None,
    customer_proof_evidence: str | Path | None,
    fred_authority_evidence: str | Path | None,
    paa_artifact: str | Path | None,
    content_brief: str | Path | None,
    user_paa_csv: str | Path | None,
    answersocrates_blocker: str | Path | None,
    optimizer_outputs: Sequence[str | Path],
    prior_preflight_readiness: str | Path | None,
    agent_output_paths: Mapping[str, str | Path],
    workspace_root: str | Path,
    vault_root: str | Path | None,
    precheck_output: str | Path | None,
    preflight_builder: Callable[..., Mapping[str, Any]],
    provisional_builder: Callable[..., Mapping[str, Any]],
) -> BlogReleasePrecheckResult:
    root = Path(workspace_root).resolve()
    report_path = precheck_paths.resolve_precheck_output(
        precheck_output,
        workspace_root=root,
    )
    required_files = {
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
    }
    optional_files = {
        "context_request": context_request,
        "context_pack": context_pack,
        "context_receipt": context_receipt,
        "customer_proof_evidence": customer_proof_evidence,
        "fred_authority_evidence": fred_authority_evidence,
        "paa_artifact": paa_artifact,
        "content_brief": content_brief,
        "user_paa_csv": user_paa_csv,
        "answersocrates_blocker": answersocrates_blocker,
    }
    try:
        planned_dir = precheck_paths.validate_precheck_output_target(
            report_path,
            output_dir=output_dir,
            workspace_root=root,
            required_files=required_files,
            optional_files=optional_files,
            stage_receipts=stage_receipts,
            optimizer_outputs=optimizer_outputs,
            prior_preflight_readiness=prior_preflight_readiness,
            agent_output_paths=agent_output_paths,
        )
    except ReleaseInvocationError as error:
        planned_dir = precheck_paths.safe_output_dir(output_dir, workspace_root=root)
        if not str(error).startswith("precheck_output"):
            _write_failure_report(
                report_path,
                run_id=run_id,
                output_dir=planned_dir,
                phase="invocation",
                message=str(error),
                blockers=[_blocker("invocation", str(error))],
                workspace_root=root,
            )
        raise
    release_stage_receipts = _release_stage_receipts(stage_receipts, scrub_receipt)
    try:
        optimized_release = validate_release_invocation(
            required_files=required_files,
            optional_files=optional_files,
            stage_receipts=stage_receipts,
            optimizer_outputs=optimizer_outputs,
            prior_preflight_readiness=prior_preflight_readiness,
            agent_output_paths=agent_output_paths,
            run_id=run_id,
            workflow_mode=workflow_mode,
            workspace_root=root,
        )
        if optimized_release:
            precheck_checks.validate_optimizer_outputs(
                optimizer_outputs,
                article=article,
                editorial_plan=editorial_plan,
                proof_sidecar=proof_sidecar,
                prior_preflight_readiness=prior_preflight_readiness,
                workspace_root=root,
            )
    except ReleaseInvocationError as error:
        _write_failure_report(
            report_path,
            run_id=run_id,
            output_dir=planned_dir,
            phase=_invocation_phase(error),
            message=str(error),
            blockers=[_blocker(_invocation_phase(error), str(error))],
            workspace_root=root,
        )
        raise

    try:
        pre_bom = preflight_builder(
            article,
            proof_sidecar=proof_sidecar,
            context_request=context_request,
            context_pack=context_pack,
            context_receipt=context_receipt,
            keyword_decision=keyword_decision,
            assembly_date=assembly_date,
            output=report_path,
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
    except Exception as error:
        write_exception_report(
            error,
            run_id=run_id,
            workspace_root=root,
            output_dir=planned_dir,
            precheck_output=report_path,
            phase="pre_bom",
        )
        raise
    if pre_bom.get("ready_for_bom") is not True:
        result = BlogReleasePrecheckResult(
            False,
            "pre_bom",
            "pre-BOM report blocked release",
            planned_dir,
            optimized_release,
            release_stage_receipts,
            pre_bom=pre_bom,
            report_path=report_path,
        )
        _write_result_report(result, run_id=run_id, workspace_root=root)
        return result

    try:
        provisional = provisional_builder(
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
            agent_output_paths=agent_output_paths,
            optimizer_output_paths=optimizer_outputs,
            prior_preflight_readiness_path=prior_preflight_readiness,
            workspace_root=root,
            vault_root=vault_root,
        )
    except Exception as error:
        write_exception_report(
            error,
            run_id=run_id,
            workspace_root=root,
            output_dir=planned_dir,
            precheck_output=report_path,
            phase="provisional_bom",
        )
        raise

    provisional_findings = precheck_checks.provisional_findings(provisional)
    if provisional_findings:
        result = BlogReleasePrecheckResult(
            False,
            "provisional_bom",
            "provisional BOM blocked release",
            planned_dir,
            optimized_release,
            release_stage_receipts,
            pre_bom=pre_bom,
            provisional_bom=provisional,
            report_path=report_path,
        )
        _write_result_report(
            result,
            run_id=run_id,
            workspace_root=root,
            provisional_findings=provisional_findings,
        )
        return result

    result = BlogReleasePrecheckResult(
        True,
        "precheck",
        "release prechecks passed",
        planned_dir,
        optimized_release,
        release_stage_receipts,
        pre_bom=pre_bom,
        provisional_bom=provisional,
        report_path=report_path,
    )
    _write_result_report(result, run_id=run_id, workspace_root=root)
    return result


def write_exception_report(
    error: BaseException,
    *,
    run_id: object,
    workspace_root: str | Path,
    output_dir: str | Path | None,
    precheck_output: str | Path | None,
    phase: str,
) -> Path | None:
    root = Path(workspace_root).resolve(strict=False)
    report_path = precheck_paths.resolve_precheck_output(
        precheck_output,
        workspace_root=root,
    )
    if report_path is None:
        return report_path
    output = precheck_paths.safe_output_dir(output_dir, workspace_root=root)
    payload = _payload(
        run_id=run_id,
        passed=False,
        phase=phase,
        message=str(error),
        output_dir=output,
        workspace_root=root,
        blockers=[_blocker(phase, str(error))],
    )
    payload["exception_type"] = type(error).__name__
    atomic_write_json(report_path, payload)
    return report_path


def _write_result_report(
    result: BlogReleasePrecheckResult,
    *,
    run_id: object,
    workspace_root: Path,
    provisional_findings: Sequence[Mapping[str, Any]] | None = None,
) -> None:
    if result.report_path is None:
        return
    payload = _payload(
        run_id=run_id,
        passed=result.passed,
        phase=result.phase,
        message=result.message,
        output_dir=result.output_dir,
        workspace_root=workspace_root,
        blockers=_blockers_from_pre_bom(result.pre_bom),
    )
    payload["optimized_release"] = result.optimized_release
    if result.pre_bom is not None:
        payload["pre_bom"] = {
            "ready_for_bom": result.pre_bom.get("ready_for_bom"),
            "blockers": list(result.pre_bom.get("blockers") or []),
            "warnings": list(result.pre_bom.get("warnings") or []),
        }
    if provisional_findings is not None:
        payload["provisional_bom"] = {
            "valid": False,
            "findings": list(provisional_findings),
        }
    elif result.provisional_bom is not None:
        payload["provisional_bom"] = {"valid": True, "findings": []}
    atomic_write_json(result.report_path, payload)


def _write_failure_report(
    report_path: Path | None,
    *,
    run_id: object,
    output_dir: Path,
    phase: str,
    message: str,
    blockers: Sequence[Mapping[str, Any]],
    workspace_root: Path,
) -> None:
    if report_path is None:
        return
    atomic_write_json(
        report_path,
        _payload(
            run_id=run_id,
            passed=False,
            phase=phase,
            message=message,
            output_dir=output_dir,
            workspace_root=workspace_root,
            blockers=blockers,
        ),
    )


def _payload(
    *,
    run_id: object,
    passed: bool,
    phase: str,
    message: str,
    output_dir: Path,
    workspace_root: Path,
    blockers: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "run_id": _run_id(run_id),
        "passed": passed,
        "phase": phase,
        "message": message,
        "output_dir_created": False,
        "paths": {
            "planned_output_dir": workspace_path(output_dir, workspace_root=workspace_root),
        },
        "blockers": list(blockers),
    }


def _blockers_from_pre_bom(pre_bom: Mapping[str, Any] | None) -> list[Mapping[str, Any]]:
    if pre_bom is None:
        return []
    blockers = pre_bom.get("blockers")
    return list(blockers) if isinstance(blockers, list) else []


def _blocker(rule_id: str, message: str) -> dict[str, str]:
    return {"rule_id": rule_id, "message": message}


def _invocation_phase(error: ReleaseInvocationError) -> str:
    return "optimizer_evidence" if "optimizer_output_" in str(error) else "invocation"


def _release_stage_receipts(
    stage_receipts: Sequence[str | Path],
    scrub_receipt: str | Path,
) -> tuple[str | Path, ...]:
    receipts = tuple(stage_receipts)
    if all(str(receipt) != str(scrub_receipt) for receipt in receipts):
        return (scrub_receipt, *receipts)
    return receipts


def _run_id(value: object) -> str:
    if isinstance(value, str) and value.strip():
        return value.strip()
    return "missing-run-id"


__all__ = [
    "BlogReleasePrecheckResult",
    "SCHEMA",
    "run_blog_release_precheck",
    "write_exception_report",
]
