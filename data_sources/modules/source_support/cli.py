"""Cli responsibilities."""
from .common import Optional, Sequence, argparse, json, should_fail, summarize_findings
from .orchestration import check_file


def _main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Check source evidence supports high-risk claims.")
    parser.add_argument("path", help="Markdown file to check")
    parser.add_argument(
        "--fail-on",
        choices=["error", "warning", "none"],
        default="error",
        help="Finding severity that should produce a nonzero exit code.",
    )
    parser.add_argument(
        "--proof-sidecar",
        help="Optional validation sidecar containing Source Map or Proof Pack rows.",
    )
    args = parser.parse_args(argv)

    findings = check_file(args.path, fail_on=args.fail_on, proof_sidecar=args.proof_sidecar)
    payload = {
        "path": args.path,
        "fail_on": args.fail_on,
        "summary": summarize_findings(findings),
        "findings": findings,
    }
    print(json.dumps(payload, indent=2))
    return 1 if should_fail(findings, fail_on=args.fail_on) else 0


def main(argv: Optional[Sequence[str]] = None) -> int:
    return _main(argv)


__all__ = ["_main", "main"]


if __name__ == "__main__":
    raise SystemExit(main())
