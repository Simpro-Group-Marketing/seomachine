"""Atomic wrapper for the existing proof-governed blog release sequence."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

try:
    from . import blog_assembly_bom, blog_creation_preflight, publish_readiness
    from .blog_assembly_contract import atomic_write_json
except ImportError:  # pragma: no cover - supports direct script execution.
    import blog_assembly_bom
    import blog_creation_preflight
    import publish_readiness
    from blog_assembly_contract import atomic_write_json


class ReleaseInvocationError(ValueError):
    """The release wrapper was called with invalid or unsafe arguments."""


class ReleasePolicyError(RuntimeError):
    """A policy, evidence, score, or readiness gate blocked release."""


@dataclass(frozen=True)
class ReleaseResult:
    exit_code: int
    output_dir: Path
    phase: str
    message: str


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
    workspace_root: str | Path | None = None,
    vault_root: str | Path | None = None,
) -> ReleaseResult:
    """Run preflight, provisional BOM, readiness, final BOM, and final readiness."""
    root = Path(workspace_root or Path.cwd()).resolve()
    destination = _new_output_dir(output_dir, workspace_root=root)
    _require_file(article, "article")
    _require_file(proof_sidecar, "proof_sidecar")
    _require_file(editorial_plan, "editorial_plan")
    _require_file(plan_review, "plan_review")
    _require_file(article_review, "article_review")
    _require_file(keyword_decision, "keyword_decision")
    _require_file(scrub_receipt, "scrub_receipt")
    _require_file(serp_evidence, "serp_evidence")
    if not stage_receipts:
        raise ReleaseInvocationError("at least one stage receipt is required")
    for index, receipt in enumerate(stage_receipts):
        _require_file(receipt, f"stage_receipts[{index}]")
    for label, value in (
        ("context_request", context_request),
        ("context_pack", context_pack),
        ("context_receipt", context_receipt),
        ("customer_proof_evidence", customer_proof_evidence),
        ("fred_authority_evidence", fred_authority_evidence),
        ("paa_artifact", paa_artifact),
        ("content_brief", content_brief),
        ("user_paa_csv", user_paa_csv),
        ("answersocrates_blocker", answersocrates_blocker),
    ):
        if value is not None:
            _require_file(value, label)
    if not isinstance(run_id, str) or not run_id.strip():
        raise ReleaseInvocationError("run_id is required")
    if workflow_mode not in {"new", "rewrite"}:
        raise ReleaseInvocationError("workflow_mode must be new or rewrite")
    release_stage_receipts = tuple(stage_receipts)
    if all(str(receipt) != str(scrub_receipt) for receipt in release_stage_receipts):
        release_stage_receipts = (scrub_receipt, *release_stage_receipts)

    paths = _release_paths(destination)
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
        return ReleaseResult(1, destination, "pre_bom", "pre-BOM report blocked release")

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
        workspace_root=root,
        vault_root=vault_root,
    )
    atomic_write_json(paths["provisional_bom"], provisional)

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
    )
    publish_readiness.write_readiness_result(
        paths["preflight_readiness"],
        preflight,
        receipt_path=paths["preflight_readiness_stage_receipt"],
        workspace_root=root,
    )
    if preflight.get("passed") is not True:
        return ReleaseResult(1, destination, "preflight_readiness", "preflight readiness blocked release")

    final_bom = blog_assembly_bom.finalize_blog_assembly_bom(
        bom_path=paths["provisional_bom"],
        preflight_readiness_path=paths["preflight_readiness"],
        workspace_root=root,
        vault_root=vault_root,
    )
    atomic_write_json(paths["final_bom"], final_bom)

    final = publish_readiness.run_publish_readiness(
        article,
        proof_sidecar=proof_sidecar,
        context_request=context_request,
        context_pack=context_pack,
        context_receipt=context_receipt,
        assembly_bom=paths["final_bom"],
        phase="final",
        workspace_root=root,
        vault_root=vault_root,
    )
    publish_readiness.write_readiness_result(
        paths["final_readiness"],
        final,
        receipt_path=paths["final_readiness_stage_receipt"],
        workspace_root=root,
    )
    if final.get("passed") is not True:
        return ReleaseResult(1, destination, "final_readiness", "final readiness blocked release")
    return ReleaseResult(0, destination, "final_readiness", "final readiness passed")


def _release_paths(output_dir: Path) -> dict[str, Path]:
    return {
        "pre_bom_report": output_dir / "pre-bom-report.json",
        "provisional_bom": output_dir / "provisional-bom.json",
        "preflight_readiness": output_dir / "preflight-readiness.json",
        "preflight_readiness_stage_receipt": output_dir / "preflight-readiness-stage-receipt.json",
        "final_bom": output_dir / "final-bom.json",
        "final_readiness": output_dir / "final-readiness.json",
        "final_readiness_stage_receipt": output_dir / "final-readiness-stage-receipt.json",
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


def _require_file(path: str | Path, label: str) -> None:
    if not isinstance(path, (str, Path)) or not str(path).strip():
        raise ReleaseInvocationError(f"{label} path is required")
    if not Path(path).is_file():
        raise ReleaseInvocationError(f"{label} is unreadable: {path}")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the atomic Simpro blog release wrapper.")
    parser.add_argument("article")
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--proof-sidecar", required=True)
    parser.add_argument("--editorial-plan", required=True)
    parser.add_argument("--plan-review", required=True)
    parser.add_argument("--article-review", required=True)
    parser.add_argument("--keyword-decision", required=True)
    parser.add_argument("--scrub-receipt", required=True)
    parser.add_argument("--serp-evidence", required=True)
    parser.add_argument("--stage-receipt", action="append", required=True, dest="stage_receipts")
    parser.add_argument("--workflow-mode", choices=("new", "rewrite"), required=True)
    parser.add_argument("--assembly-date", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--context-request")
    parser.add_argument("--context-pack")
    parser.add_argument("--context-receipt")
    parser.add_argument("--customer-proof-evidence")
    parser.add_argument("--fred-authority-evidence")
    parser.add_argument("--paa-artifact")
    parser.add_argument("--content-brief")
    parser.add_argument("--user-paa-csv")
    parser.add_argument("--answersocrates-blocker")
    parser.add_argument("--workspace-root", default=str(Path.cwd()))
    parser.add_argument("--vault-root")
    parser.add_argument("--json", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        result = run_blog_release(
            article=args.article,
            run_id=args.run_id,
            proof_sidecar=args.proof_sidecar,
            editorial_plan=args.editorial_plan,
            plan_review=args.plan_review,
            article_review=args.article_review,
            keyword_decision=args.keyword_decision,
            scrub_receipt=args.scrub_receipt,
            serp_evidence=args.serp_evidence,
            stage_receipts=args.stage_receipts,
            workflow_mode=args.workflow_mode,
            assembly_date=args.assembly_date,
            output_dir=args.output_dir,
            context_request=args.context_request,
            context_pack=args.context_pack,
            context_receipt=args.context_receipt,
            customer_proof_evidence=args.customer_proof_evidence,
            fred_authority_evidence=args.fred_authority_evidence,
            paa_artifact=args.paa_artifact,
            content_brief=args.content_brief,
            user_paa_csv=args.user_paa_csv,
            answersocrates_blocker=args.answersocrates_blocker,
            workspace_root=args.workspace_root,
            vault_root=args.vault_root,
        )
    except ReleaseInvocationError as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    except (OSError, UnicodeError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    except (ValueError, RuntimeError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps({"exit_code": result.exit_code, "phase": result.phase, "message": result.message, "output_dir": str(result.output_dir)}, indent=2))
    else:
        print(f"{result.phase}: {result.message}")
        print(f"output_dir: {result.output_dir}")
    return result.exit_code


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main(sys.argv[1:]))
