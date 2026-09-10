"""Cli responsibilities."""
# ruff: noqa: F403, F405

from .common import *  # noqa: F403


def main(argv: Sequence[str] | None = None) -> int:
    """CLI for strict provisional build and passed-preflight finalization."""
    parser = argparse.ArgumentParser(description="Build or finalize a blog assembly BOM.")
    subparsers = parser.add_subparsers(dest="command", required=True)
    build = subparsers.add_parser("build", help="Build a provisional BOM.")
    build.add_argument("article_path")
    build.add_argument("--validation-sidecar", required=True)
    build.add_argument("--editorial-plan", required=True)
    build.add_argument("--keyword-decision", required=True)
    build.add_argument("--serp-evidence", required=True)
    build.add_argument("--plan-review")
    build.add_argument("--article-review")
    build.add_argument("--paa-artifact")
    build.add_argument("--content-brief")
    build.add_argument("--user-paa-csv")
    build.add_argument("--answersocrates-blocker")
    build.add_argument("--context-request")
    build.add_argument("--context-pack")
    build.add_argument("--context-receipt")
    build.add_argument("--customer-proof-selector-evidence")
    build.add_argument("--fred-authority-evidence")
    build.add_argument("--hindsight-strategy-evidence")
    build.add_argument("--agent-output", action="append", default=[])
    build.add_argument("--optimizer-output", action="append", default=[])
    build.add_argument("--prior-preflight-readiness")
    build.add_argument("--expected-review-run-id")
    build.add_argument("--stage-receipt", action="append", required=True)
    build.add_argument("--workflow-mode", choices=sorted(WORKFLOW_MODES), required=True)
    build.add_argument("--assembly-date", required=True)
    build.add_argument("--workspace-root", default=str(Path.cwd()))
    build.add_argument("--vault-root")
    build.add_argument("--output", required=True)

    finalize = subparsers.add_parser("finalize", help="Seal a passed preflight.")
    finalize.add_argument("--bom", required=True)
    finalize.add_argument("--preflight-readiness", required=True)
    finalize.add_argument("--workspace-root", default=str(Path.cwd()))
    finalize.add_argument("--vault-root")
    finalize.add_argument("--output", required=True)
    args = parser.parse_args(argv)

    try:
        if args.command == "build":
            bom = build_blog_assembly_bom_from_files(
                article_path=args.article_path,
                validation_sidecar_path=args.validation_sidecar,
                editorial_plan_path=args.editorial_plan,
                keyword_decision_path=args.keyword_decision,
                serp_evidence_path=args.serp_evidence,
                plan_review_path=args.plan_review,
                article_review_path=args.article_review,
                paa_artifact_path=args.paa_artifact,
                content_brief_path=args.content_brief,
                user_paa_csv_path=args.user_paa_csv,
                answersocrates_blocker_path=args.answersocrates_blocker,
                context_request_path=args.context_request,
                context_pack_path=args.context_pack,
                context_receipt_path=args.context_receipt,
                customer_proof_selector_evidence_path=args.customer_proof_selector_evidence,
                fred_authority_evidence_path=args.fred_authority_evidence,
                hindsight_strategy_evidence_path=args.hindsight_strategy_evidence,
                agent_output_paths=_label_paths(args.agent_output),
                optimizer_output_paths=args.optimizer_output,
                prior_preflight_readiness_path=args.prior_preflight_readiness,
                expected_review_run_id=args.expected_review_run_id,
                stage_receipt_paths=args.stage_receipt,
                workflow_mode=args.workflow_mode,
                assembly_date=args.assembly_date,
                workspace_root=args.workspace_root,
                vault_root=args.vault_root,
            )
        else:
            bom = finalize_blog_assembly_bom(
                bom_path=args.bom,
                preflight_readiness_path=args.preflight_readiness,
                workspace_root=args.workspace_root,
                vault_root=args.vault_root,
            )
        _reject_bom_output_collision(
            args.output,
            bom,
            workspace_root=args.workspace_root,
        )
        write_blog_assembly_bom(args.output, bom)
    except (OSError, UnicodeError, ValueError) as error:
        parser.error(str(error))
    return 0

def _bom_output_identity(path: str | Path, *, root: Path) -> str:
    candidate = Path(path)
    if not candidate.is_absolute():
        candidate = root / candidate
    resolved = candidate.resolve(strict=False)
    root_identity = os.path.normcase(str(root))
    resolved_identity = os.path.normcase(str(resolved))
    try:
        common = os.path.commonpath((root_identity, resolved_identity))
    except ValueError as error:
        raise ValueError("BOM output must stay inside the workspace") from error
    if common != root_identity:
        raise ValueError("BOM output must stay inside the workspace")
    return resolved_identity


def _reject_bom_output_collision(
    output_path: str | Path,
    bom: Mapping[str, Any],
    *,
    workspace_root: str | Path,
) -> None:
    """Prevent a BOM write from destroying any artifact it attests."""
    root = Path(workspace_root).resolve()
    destination = _bom_output_identity(output_path, root=root)
    artifacts = _required_mapping(bom.get("artifacts"), "bom.artifacts")
    for label, row in artifact_inventory_snapshots(artifacts).items():
        candidate = resolve_artifact(row["path"], workspace_root=workspace_root)
        if destination == os.path.normcase(str(candidate)):
            raise ValueError(f"BOM output cannot overwrite artifact {label}")
    for readiness_label in ("prior_preflight_readiness", "preflight_readiness"):
        readiness_row = artifacts.get(readiness_label)
        if not isinstance(readiness_row, Mapping):
            continue
        readiness_path = verify_artifact(
            readiness_row,
            workspace_root=workspace_root,
            field=f"artifacts.{readiness_label}",
        )
        readiness = _read_json_object(readiness_path, readiness_label)
        inputs = _required_mapping(
            readiness.get("input_hashes"),
            f"{readiness_label}.input_hashes",
        )
        for label, row in inputs.items():
            input_row = _required_mapping(
                row,
                f"{readiness_label}.input_hashes.{label}",
            )
            candidate = resolve_artifact(
                input_row.get("path"),
                workspace_root=workspace_root,
            )
            candidate_identity = os.path.normcase(str(candidate))
            if destination != candidate_identity:
                continue
            raise ValueError(
                f"BOM output cannot overwrite {readiness_label} input {label}"
            )


__all__ = ['_reject_bom_output_collision', 'main']
