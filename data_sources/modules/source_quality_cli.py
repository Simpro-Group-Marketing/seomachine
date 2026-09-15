"""Command-line entry point for source-quality validation."""

from __future__ import annotations

import argparse
import json
from typing import Callable, Optional, Sequence

try:
    from .guard_common import Finding, should_fail, summarize_findings
except ImportError:  # pragma: no cover - direct script execution.
    from guard_common import Finding, should_fail, summarize_findings


def main(
    argv: Optional[Sequence[str]],
    *,
    check_file: Callable[..., list[Finding]],
) -> int:
    parser = argparse.ArgumentParser(
        description="Validate Source Map quality and lifecycle scheduling."
    )
    parser.add_argument("path")
    parser.add_argument("--proof-sidecar", required=True)
    parser.add_argument(
        "--fail-on", choices=["error", "warning", "none"], default="error"
    )
    args = parser.parse_args(argv)
    findings = check_file(
        args.path,
        proof_sidecar=args.proof_sidecar,
        fail_on=args.fail_on,
    )
    payload = {
        "path": args.path,
        "summary": summarize_findings(findings),
        "findings": findings,
    }
    print(json.dumps(payload, indent=2))
    return 1 if should_fail(findings, fail_on=args.fail_on) else 0
