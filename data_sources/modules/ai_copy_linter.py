"""Compatibility facade and CLI for the split AI copy linter."""

from __future__ import annotations

import argparse
import json
import sys
from typing import Optional

try:
    from .ai_copy_lint.core import lint_content, lint_file, should_fail, summarize_findings
except ImportError:
    from ai_copy_lint.core import lint_content, lint_file, should_fail, summarize_findings


def _main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Lint content for AI copy tells.")
    parser.add_argument("path", help="Markdown or text file to lint")
    parser.add_argument("--profile", default="simpro-web", help="Lint profile")
    parser.add_argument(
        "--fail-on",
        default="error",
        choices=["error", "warning", "none"],
        help="Minimum finding severity that returns exit code 1",
    )
    args = parser.parse_args(argv)
    findings = lint_file(args.path, profile=args.profile, fail_on=args.fail_on)
    print(json.dumps({
        "path": args.path,
        "profile": args.profile,
        "fail_on": args.fail_on,
        "summary": summarize_findings(findings),
        "findings": findings,
    }, indent=2))
    return 1 if should_fail(findings, fail_on=args.fail_on) else 0


if __name__ == "__main__":
    sys.exit(_main())


__all__ = ["lint_content", "lint_file", "should_fail", "summarize_findings"]
