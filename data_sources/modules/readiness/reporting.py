"""Publish-readiness reporting responsibilities."""
# ruff: noqa: F403, F405

from .common import *  # noqa: F403


def format_text_report(result: ReadinessResult) -> str:
    """Return a human-readable publish-readiness report."""
    lines = [
        "PUBLISH READINESS",
        "=" * 50,
        f"File: {result['file']}",
        f"Proof sidecar: {result.get('proof_sidecar') or 'auto/default'}",
        f"Context request: {result.get('context_request') or 'not required/provided'}",
        f"Context pack: {result.get('context_pack') or 'not required/provided'}",
        f"Context receipt: {result.get('context_receipt') or 'not required/provided'}",
        f"Assembly BOM: {result.get('assembly_bom') or 'not required/provided'}",
        f"Overall: {'PASS' if result['passed'] else 'FAIL'}",
        "",
        "Gates:",
    ]

    for gate in result["gates"]:
        status = "PASS" if gate["passed"] else "FAIL"
        lines.append(
            f"  {status:4} {gate['label']:<28} "
            f"errors={gate['errors']} warnings={gate['warnings']}"
        )
        for blocker in gate.get("blockers", [])[:3]:
            lines.append(f"       - {blocker}")

    scorecard = result.get("scorecard")
    content_gate = _scorecard_gate(scorecard, "content_quality")
    seo_gate = _scorecard_gate(scorecard, "seo_quality")
    aeo_gate = _scorecard_gate(scorecard, "aeo_geo")

    content_score = content_gate.get("score", result.get("score"))
    content_threshold = content_gate.get("threshold", result.get("score_threshold", 85))
    content_passed = bool(
        content_gate.get(
            "passed",
            content_score is not None and content_score >= content_threshold,
        )
    )
    seo_score = seo_gate.get("score")
    seo_threshold = seo_gate.get("threshold", 90)
    seo_target = seo_gate.get("target", SEO_TARGET_SCORE)
    seo_passed = bool(seo_gate.get("passed", False))
    seo_target_met = seo_gate.get("target_met")
    seo_target_status = seo_gate.get("target_status")
    seo_critical_issue_count = seo_gate.get("critical_issue_count")
    aeo_geo = result.get("aeo_geo", {})
    if not isinstance(aeo_geo, Mapping):
        aeo_geo = {}
    aeo_geo_score = aeo_gate.get("score", aeo_geo.get("score"))
    aeo_geo_threshold = aeo_gate.get("threshold", aeo_geo.get("threshold", 90))
    aeo_geo_passed = bool(aeo_gate.get("passed", aeo_geo.get("passed", False)))

    lines.extend(
        [
            "",
            _score_report_line(
                "Content score",
                content_score,
                content_threshold,
                content_passed,
            ),
            _seo_score_report_line(
                "SEO score",
                seo_score,
                seo_threshold,
                seo_target,
                seo_passed,
                target_met=seo_target_met,
                target_status=seo_target_status,
            ),
        ]
    )
    if isinstance(seo_critical_issue_count, int) and not isinstance(
        seo_critical_issue_count,
        bool,
    ) and seo_critical_issue_count > 0:
        lines.append(f"SEO critical issues: {seo_critical_issue_count}")
    lines.append(
        _score_report_line(
            "AEO/GEO score",
            aeo_geo_score,
            aeo_geo_threshold,
            aeo_geo_passed,
        )
    )
    priority_fixes = result.get("priority_fixes", [])
    if priority_fixes:
        lines.append("")
        lines.append("Priority fixes:")
        for index, fix in enumerate(priority_fixes[:5], start=1):
            issue = fix.get("issue", "Unknown issue")
            dimension = fix.get("dimension", "unknown")
            lines.append(f"  {index}. [{dimension}] {issue}")

    lines.append("=" * 50)
    return "\n".join(lines)

def _readiness_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the publish-readiness gate stack.")
    parser.add_argument("file_path", help="Path to the draft or rewrite markdown file.")
    parser.add_argument(
        "--proof-sidecar",
        help="Validation sidecar containing proof maps and proof packs.",
    )
    parser.add_argument(
        "--profile",
        default="simpro-web",
        help="AI copy linter profile. Defaults to simpro-web.",
    )
    parser.add_argument("--context-request", help="Current Simpro context request JSON.")
    parser.add_argument("--context-pack", help="Current Simpro v2 context pack JSON.")
    parser.add_argument("--context-receipt", help="Current Simpro context receipt JSON.")
    parser.add_argument("--assembly-bom", help="Current blog assembly BOM JSON.")
    parser.add_argument(
        "--phase",
        choices=("preflight", "final"),
        default="preflight",
        help="Validate a provisional BOM for preflight or a final BOM for attestation.",
    )
    parser.add_argument(
        "--output",
        help="Atomically persist the machine-readable readiness result JSON.",
    )
    parser.add_argument(
        "--stage-receipt-output",
        help="Optional receipt path; defaults beside --output for passed runs.",
    )
    parser.add_argument(
        "--telemetry-output",
        help="Optional content-free readiness telemetry JSON output.",
    )
    parser.add_argument("--vault-root", help="Configured Simpro vault root override.")
    parser.add_argument(
        "--workspace-root",
        default=str(Path.cwd()),
        help="Trusted repository root used to resolve and contain all readiness artifacts.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print machine-readable JSON instead of the text report.",
    )
    return parser


def _validate_cli_args(parser: argparse.ArgumentParser, args: argparse.Namespace) -> None:
    if args.stage_receipt_output and not args.output:
        parser.error("--stage-receipt-output requires --output")
    if args.assembly_bom and not args.output:
        parser.error("--output is required when --assembly-bom is supplied")
    if args.phase == "preflight" and args.stage_receipt_output:
        parser.error(
            "preflight receipts use the deterministic --output companion path; "
            "--stage-receipt-output is allowed only for final attestation"
        )
    if args.telemetry_output:
        try:
            _reject_telemetry_output_collision(args)
        except ValueError as error:
            parser.error(str(error))


def _cli_telemetry(
    parser: argparse.ArgumentParser,
    args: argparse.Namespace,
) -> ReadinessTelemetry | None:
    if not args.telemetry_output:
        return None
    try:
        telemetry = ReadinessTelemetry(
            run_id=_readiness_run_id(args.assembly_bom, file_sha256(args.file_path)),
            phase=args.phase,
        )
        telemetry.increment("full_readiness_executions")
        return telemetry
    except (OSError, UnicodeError, ValueError) as error:
        parser.error(str(error))


def _execute_cli_readiness(
    args: argparse.Namespace,
    telemetry: ReadinessTelemetry | None,
) -> ReadinessResult:
    kwargs = {
        "proof_sidecar": args.proof_sidecar,
        "context_request": args.context_request,
        "context_pack": args.context_pack,
        "context_receipt": args.context_receipt,
        "assembly_bom": args.assembly_bom,
        "vault_root": args.vault_root,
        "ai_profile": args.profile,
        "phase": args.phase,
        "workspace_root": args.workspace_root,
    }
    if telemetry is None:
        return run_publish_readiness(args.file_path, **kwargs)
    with telemetry.stage("publish_readiness"):
        return run_publish_readiness(args.file_path, telemetry=telemetry, **kwargs)


def _write_cli_telemetry(
    args: argparse.Namespace,
    telemetry: ReadinessTelemetry,
) -> None:
    telemetry.write(_resolve_workspace_input(
        args.telemetry_output,
        workspace_root=args.workspace_root,
        field="telemetry output",
    ))


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = _readiness_parser()
    args = parser.parse_args(argv)
    _validate_cli_args(parser, args)
    telemetry = _cli_telemetry(parser, args)

    try:
        result = _execute_cli_readiness(args, telemetry)
        if telemetry is not None:
            telemetry.increment("gate_invocations", len(result.get("gates", [])))
        if args.output:
            write_readiness_result(
                args.output,
                result,
                receipt_path=args.stage_receipt_output,
                workspace_root=args.workspace_root,
            )
    except (OSError, UnicodeError, ValueError) as error:
        if telemetry is not None:
            telemetry.finish("operational_error")
            try:
                _write_cli_telemetry(args, telemetry)
            except (OSError, UnicodeError, ValueError) as telemetry_error:
                parser.error(f"{error}; telemetry write failed: {telemetry_error}")
        parser.error(str(error))
    if telemetry is not None:
        telemetry.finish("passed" if result.get("passed") is True else "blocked")
        try:
            _write_cli_telemetry(args, telemetry)
        except (OSError, UnicodeError, ValueError) as error:
            parser.error(str(error))
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(format_text_report(result))
    return 0 if result["passed"] else 1


__all__ = ['format_text_report', 'main']
