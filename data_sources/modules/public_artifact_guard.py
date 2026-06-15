"""
Public Artifact Guard

Blocks internal validation/proof appendices from public blog copy artifacts.
Proof maps belong in validation sidecars, not in the publishable draft body.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import List, Optional, Sequence

try:
    from .guard_common import Finding, make_finding, should_fail, summarize_findings
except ImportError:  # pragma: no cover - supports direct script execution.
    from guard_common import Finding, make_finding, should_fail, summarize_findings


BANNED_HEADINGS = (
    "Editorial Validation Appendix",
    "PAA/FAQ Provenance",
    "Metric Proof Pack",
    "Source Map",
    "Customer Proof Pack",
    "E-E-A-T Proof Map",
    "FAQ Proof Map",
    "Structured data plan",
)


def check_content(content: str) -> List[Finding]:
    """Return findings for internal validation headings in public copy."""
    findings: List[Finding] = []
    patterns = [
        (
            heading,
            re.compile(
                rf"^\s*(?:#{{1,6}}\s+)?{re.escape(heading)}\s*:?\s*$",
                re.IGNORECASE,
            ),
        )
        for heading in BANNED_HEADINGS
    ]

    for line_number, line in enumerate(content.splitlines(), start=1):
        stripped = line.strip()
        for heading, pattern in patterns:
            if pattern.match(stripped):
                findings.append(
                    make_finding(
                        "internal_validation_artifact",
                        "error",
                        line_number,
                        match=stripped,
                        message=(
                            f"Public article copy contains internal validation heading: {heading}."
                        ),
                        suggestion=(
                            "Move proof infrastructure to "
                            "research/validation-[topic-slug]-[YYYY-MM-DD].md "
                            "and run proof gates with --proof-sidecar."
                        ),
                    )
                )
                break

    return findings


def check_file(path: str | Path, fail_on: str = "error") -> List[Finding]:
    """Check a markdown file for internal validation artifacts."""
    if fail_on not in {"error", "warning", "none"}:
        raise ValueError("fail_on must be one of: error, warning, none")
    return check_content(Path(path).read_text(encoding="utf-8"))


def _main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Check public copy artifacts for internal validation headings."
    )
    parser.add_argument("path", help="Markdown file to check")
    parser.add_argument(
        "--fail-on",
        choices=["error", "warning", "none"],
        default="error",
        help="Finding severity that should produce a nonzero exit code.",
    )
    args = parser.parse_args(argv)

    findings = check_file(args.path, fail_on=args.fail_on)
    payload = {
        "path": args.path,
        "fail_on": args.fail_on,
        "summary": summarize_findings(findings),
        "findings": findings,
    }
    print(json.dumps(payload, indent=2))
    return 1 if should_fail(findings, fail_on=args.fail_on) else 0


if __name__ == "__main__":
    sys.exit(_main())
