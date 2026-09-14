"""CLI for customer-proof diversity validation."""

from __future__ import annotations

import argparse
import json
from typing import Optional, Sequence

from ..guard_common import should_fail, summarize_findings
from .diversity import check_file
from .diversity_contracts import DEFAULT_INDEX_PATH, DEFAULT_LEDGER_PATH


def _main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Check customer proof selection and reuse governance."
    )
    parser.add_argument("path", help="Markdown file to check")
    parser.add_argument(
        "--fail-on",
        choices=["error", "warning", "none"],
        default="error",
        help="Finding severity that should produce a nonzero exit code.",
    )
    parser.add_argument(
        "--proof-sidecar",
        help="Optional validation sidecar containing Customer Proof Pack rows.",
    )
    parser.add_argument(
        "--ledger",
        default=str(DEFAULT_LEDGER_PATH),
        help="Customer proof usage ledger JSON path.",
    )
    parser.add_argument(
        "--proof-index",
        default=str(DEFAULT_INDEX_PATH),
        help="Customer proof index JSON path.",
    )
    parser.add_argument(
        "--context-pack",
        help="simpro-product-context-pack/v2 JSON path for receipt-backed comparison.",
    )
    parser.add_argument(
        "--context-receipt",
        help="simpro-context-receipt/v1 JSON path for receipt-backed comparison.",
    )
    args = parser.parse_args(argv)

    findings = check_file(
        args.path,
        fail_on=args.fail_on,
        proof_sidecar=args.proof_sidecar,
        ledger_path=args.ledger,
        proof_index_path=args.proof_index,
        context_pack=args.context_pack,
        context_receipt=args.context_receipt,
    )
    payload = {
        "path": args.path,
        "fail_on": args.fail_on,
        "summary": summarize_findings(findings),
        "findings": findings,
    }
    print(json.dumps(payload, indent=2))
    return 1 if should_fail(findings, fail_on=args.fail_on) else 0


__all__ = [
    '_main'
]
