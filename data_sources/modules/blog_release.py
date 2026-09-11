"""Atomic wrapper for the existing proof-governed blog release sequence."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Sequence

try:
    from . import (
        blog_assembly_bom,
        blog_assembly_stage_receipt,
        blog_creation_preflight,
        publish_readiness,
    )
    from .blog_assembly_contract import atomic_write_json, validate_sha256
    from .artifact_runtime.release_invocation import (
        ReleaseInvocationError,
        validate_release_invocation,
    )
    from .readiness.telemetry import ReadinessTelemetry
except ImportError:  # pragma: no cover - supports direct script execution.
    import blog_assembly_bom
    import blog_assembly_stage_receipt
    import blog_creation_preflight
    import publish_readiness
    from blog_assembly_contract import atomic_write_json, validate_sha256
    from artifact_runtime.release_invocation import (
        ReleaseInvocationError,
        validate_release_invocation,
    )
    from readiness.telemetry import ReadinessTelemetry


class ReleasePolicyError(RuntimeError):
    pass


@dataclass(frozen=True)
class ReleaseResult:
    exit_code: int
    output_dir: Path
    phase: str
    message: str
    recovery_artifact: Path | None = None


def run_blog_release(
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
    destination = _new_output_dir(output_dir, workspace_root=root)
    release_stage_receipts = tuple(stage_receipts)
    if all(str(receipt) != str(scrub_receipt) for receipt in release_stage_receipts):
        release_stage_receipts = (scrub_receipt, *release_stage_receipts)

    paths = _release_paths(destination)
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
        recovery_artifact = _begin_optimization_run(
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
            workspace_root=root,
            telemetry=telemetry,
        )
    with telemetry.stage("final_persistence"):
        publish_readiness.write_readiness_result(
            paths["final_readiness"],
            final,
            receipt_path=paths["final_readiness_stage_receipt"],
            workspace_root=root,
        )
    if final.get("passed") is not True:
        return finish(
            ReleaseResult(1, destination, "final_readiness", "final readiness blocked release")
        )
    return finish(
        ReleaseResult(0, destination, "final_readiness", "final readiness passed")
    )


def _release_paths(output_dir: Path) -> dict[str, Path]:
    return {
        "pre_bom_report": output_dir / "pre-bom-report.json",
        "provisional_bom": output_dir / "provisional-bom.json",
        "preflight_readiness": output_dir / "preflight-readiness.json",
        "preflight_readiness_stage_receipt": output_dir / "preflight-readiness-stage-receipt.json",
        "optimization_state": output_dir / "optimization-state.json",
        "optimization_recovery": output_dir / "optimization-recovery.json",
        "optimization_stage_receipt": output_dir / "optimization-stage-receipt.json",
        "final_bom": output_dir / "final-bom.json",
        "final_readiness": output_dir / "final-readiness.json",
        "final_readiness_stage_receipt": output_dir / "final-readiness-stage-receipt.json",
        "release_telemetry": output_dir / "release-telemetry.json",
    }


def _new_output_dir(path: str | Path, *, workspace_root: Path) -> Path:
    if not isinstance(path, (str, Path)) or not str(path).strip():
        raise ReleaseInvocationError("output_dir is required")
    candidate = Path(path)
    if not candidate.is_absolute():
        candidate = workspace_root / candidate
    resolved = candidate.resolve(strict=False)
    try:
        resolved.relative_to(workspace_root)
    except ValueError as error:
        raise ReleaseInvocationError("output_dir must stay inside the workspace") from error
    if resolved.exists():
        raise ReleaseInvocationError("output_dir must not already exist")
    resolved.mkdir(parents=True)
    return resolved


def _begin_optimization_run(
    *,
    article: str | Path,
    run_id: str,
    paths: dict[str, Path],
    preflight: dict[str, object],
    preflight_receipt_path: Path | None,
    workspace_root: Path,
) -> Path:
    optimization_state: str | None = None
    optimization_stage_receipt: str | None = None
    preflight_stage_receipt: str | None = None
    native_edit_status = "not_started"
    recovery_steps = [
        "Run /optimize against the article using the initial readiness output.",
        "Write a simpro-optimizer-output/v1 artifact with inspected scores, failed gates or blocker, aeo_geo checks, priority fixes, and the edit or no-op decision.",
        "Rerun /scrub and Context Binding after article or sidecar changes.",
    ]
    if preflight_receipt_path is not None:
        preflight_receipt = _read_json_object(
            preflight_receipt_path,
            "preflight_readiness_stage_receipt",
        )
        try:
            previous_receipt_hash = validate_sha256(
                preflight_receipt.get("receipt_hash"),
                field="preflight_readiness_stage_receipt.receipt_hash",
            )
        except ValueError as error:
            raise ReleasePolicyError(
                "preflight readiness receipt is missing a valid receipt_hash; "
                "cannot begin /optimize recovery"
            ) from error

        blog_assembly_stage_receipt.begin_native_edit(
            article_path=article,
            state_path=paths["optimization_state"],
            run_id=run_id,
            stage="optimization",
            tool_name="optimize-command",
            tool_version="1",
            input_artifacts={
                "preflight_readiness": paths["preflight_readiness"],
                "preflight_readiness_receipt": preflight_receipt_path,
            },
            previous_receipt_hash=previous_receipt_hash,
        )
        native_edit_status = "started"
        preflight_stage_receipt = _workspace_path(
            preflight_receipt_path,
            workspace_root=workspace_root,
        )
        optimization_state = _workspace_path(
            paths["optimization_state"],
            workspace_root=workspace_root,
        )
        optimization_stage_receipt = _workspace_path(
            paths["optimization_stage_receipt"],
            workspace_root=workspace_root,
        )
        recovery_steps.extend(
            [
                "Finish the optimization stage receipt if article bytes changed.",
                "Rerun the release wrapper with --optimizer-output and --prior-preflight-readiness.",
            ]
        )
    else:
        recovery_steps.extend(
            [
                "Resolve the preflight blocker, then rerun /scrub and Context Binding when needed.",
                "Rerun the release wrapper to produce the required passed initial scorecard before final release.",
            ]
        )
    recovery = {
        "schema": "simpro-blog-optimization-recovery/v1",
        "status": "started",
        "reason": "Optimizer evidence was not supplied to the release wrapper.",
        "preflight_passed": preflight.get("passed") is True,
        "native_edit_status": native_edit_status,
        "preflight_readiness": _workspace_path(
            paths["preflight_readiness"],
            workspace_root=workspace_root,
        ),
        "preflight_readiness_stage_receipt": preflight_stage_receipt,
        "optimization_state": optimization_state,
        "optimization_stage_receipt": optimization_stage_receipt,
        "required_next_steps": recovery_steps,
    }
    atomic_write_json(paths["optimization_recovery"], recovery)
    return paths["optimization_recovery"]


def _read_json_object(path: str | Path, label: str) -> dict[str, object]:
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise ReleasePolicyError(f"{label} is unreadable: {error}") from error
    if not isinstance(value, dict):
        raise ReleasePolicyError(f"{label} must be a JSON object")
    return value


def _workspace_path(path: str | Path, *, workspace_root: Path) -> str:
    resolved = Path(path).resolve(strict=False)
    try:
        return resolved.relative_to(workspace_root).as_posix()
    except ValueError:
        return resolved.as_posix()


def main(argv: Sequence[str] | None = None) -> int:
    try:
        from .readiness.release_cli import run_release_cli
    except ImportError:  # pragma: no cover - supports direct script execution.
        from readiness.release_cli import run_release_cli
    return run_release_cli(
        argv,
        runner=run_blog_release,
        invocation_error=ReleaseInvocationError,
    )


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
