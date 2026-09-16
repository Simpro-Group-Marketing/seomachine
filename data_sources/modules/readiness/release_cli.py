"""CLI adapter for the atomic blog release service."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Callable, Sequence

try:
    from ..release_workflow import error_reporting
except ImportError:  # pragma: no cover - supports direct script execution.
    from release_workflow import error_reporting


def run_release_cli(
    argv: Sequence[str] | None,
    *,
    runner: Callable[..., Any],
    invocation_error: type[Exception],
) -> int:
    raw_argv = list(sys.argv[1:] if argv is None else argv)
    try:
        args = _parser().parse_args(raw_argv)
    except SystemExit as error:
        _report_cli_parse_error(raw_argv, error)
        raise
    try:
        result = runner(
            article=args.article,
            run_id=args.run_id,
            proof_sidecar=args.proof_sidecar,
            editorial_plan=args.editorial_plan,
            plan_review=args.plan_review,
            article_review=args.article_review,
            keyword_decision=args.keyword_decision,
            scrub_receipt=args.scrub_receipt,
            serp_evidence=args.serp_evidence,
            plan_fulfillment=args.plan_fulfillment,
            commercial_pillar_index=args.commercial_pillar_index,
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
            optimizer_outputs=args.optimizer_outputs,
            prior_preflight_readiness=args.prior_preflight_readiness,
            agent_output_paths=_label_paths(args.agent_outputs, invocation_error),
            workspace_root=args.workspace_root,
            vault_root=args.vault_root,
        )
    except invocation_error as error:
        _report_cli_error(args, error)
        return _error_exit(error, 2)
    except (OSError, UnicodeError) as error:
        _report_cli_error(args, error)
        return _error_exit(error, 2)
    except (ValueError, RuntimeError) as error:
        _report_cli_error(args, error)
        return _error_exit(error, 1)
    _print_result(result, as_json=args.json)
    return int(result.exit_code)


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
    parser.add_argument("--plan-fulfillment", required=True)
    parser.add_argument("--commercial-pillar-index", required=True)
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
    parser.add_argument("--optimizer-output", action="append", default=[], dest="optimizer_outputs")
    parser.add_argument("--prior-preflight-readiness")
    parser.add_argument("--agent-output", action="append", default=[], dest="agent_outputs")
    parser.add_argument("--workspace-root", default=str(Path.cwd()))
    parser.add_argument("--vault-root")
    parser.add_argument("--json", action="store_true")
    return parser


def _error_exit(error: Exception, code: int) -> int:
    print(f"error: {error}", file=sys.stderr)
    return code


def _report_cli_error(args: argparse.Namespace, error: Exception) -> None:
    if error_reporting.error_report_path(
        args.run_id,
        workspace_root=args.workspace_root,
    ).exists():
        return
    error_reporting.report_exception(
        error,
        run_id=args.run_id,
        workspace_root=args.workspace_root,
        phase="cli",
        module="release_cli",
        artifact="blog",
        output_dir=args.output_dir,
    )


def _report_cli_parse_error(argv: Sequence[str], error: SystemExit) -> None:
    context = _parse_error_context(argv)
    if context is None:
        return
    run_id, workspace_root, output_dir = context
    if error_reporting.error_report_path(run_id, workspace_root=workspace_root).exists():
        return
    error_reporting.report_exception(
        error,
        run_id=run_id,
        workspace_root=workspace_root,
        phase="cli_parse",
        module="release_cli",
        artifact="blog",
        output_dir=output_dir,
    )


def _parse_error_context(argv: Sequence[str]) -> tuple[str, str, str] | None:
    values = {
        "run_id": _option_value(argv, "--run-id"),
        "workspace_root": _option_value(argv, "--workspace-root"),
        "output_dir": _option_value(argv, "--output-dir"),
    }
    if not all(values.values()):
        return None
    return (
        values["run_id"] or "",
        values["workspace_root"] or "",
        values["output_dir"] or "",
    )


def _option_value(argv: Sequence[str], option: str) -> str | None:
    prefix = f"{option}="
    for index, value in enumerate(argv):
        if value.startswith(prefix):
            candidate = value[len(prefix) :].strip()
            return candidate or None
        if value == option and index + 1 < len(argv):
            candidate = argv[index + 1].strip()
            if candidate and not candidate.startswith("--"):
                return candidate
    return None


def _label_paths(
    values: Sequence[str],
    invocation_error: type[Exception],
) -> dict[str, Path]:
    result: dict[str, Path] = {}
    for raw_value in values:
        if "=" not in raw_value:
            raise invocation_error("agent output arguments must use id=path")
        label, raw_path = (part.strip() for part in raw_value.split("=", 1))
        if not label:
            raise invocation_error("agent output ID is required")
        if not raw_path:
            raise invocation_error(f"agent output path is required for {label}")
        result[label] = Path(raw_path)
    return result


def _print_result(result: Any, *, as_json: bool) -> None:
    if as_json:
        payload = {
            "exit_code": result.exit_code,
            "phase": result.phase,
            "message": result.message,
            "output_dir": str(result.output_dir),
        }
        if result.recovery_artifact is not None:
            payload["recovery_artifact"] = str(result.recovery_artifact)
        print(json.dumps(payload, indent=2))
        return
    print(f"{result.phase}: {result.message}")
    print(f"output_dir: {result.output_dir}")
    if result.recovery_artifact is not None:
        print(f"recovery_artifact: {result.recovery_artifact}")
