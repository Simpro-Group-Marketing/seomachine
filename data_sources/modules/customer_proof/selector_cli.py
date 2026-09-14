"""CLI for connector-bound customer-proof selection."""

from __future__ import annotations

import argparse
import json
import sys
from contextlib import nullcontext
from datetime import date
from typing import List, Optional, Sequence

from .connector_inputs import _selector_input_snapshot
from .contracts import (
    DEFAULT_INDEX_PATH,
    DEFAULT_LEDGER_PATH,
    SLATE_ROLES,
    CustomerProofDataError,
    FindingDict,
)
from .selection import build_customer_proof_slate, select_customer_proofs
from .slate import (
    _parse_rejected_overrides,
    _parse_roles,
    _parse_selected_overrides,
    _write_selector_evidence,
)


def _main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Rank customer proof candidates for a topic."
    )
    parser.add_argument("topic", help="Topic or keyword to rank proof against.")
    parser.add_argument(
        "--index",
        default=str(DEFAULT_INDEX_PATH),
        help="Customer proof index JSON path.",
    )
    parser.add_argument(
        "--ledger",
        default=str(DEFAULT_LEDGER_PATH),
        help="Customer proof usage ledger JSON path.",
    )
    parser.add_argument(
        "--context-pack", help="simpro-product-context-pack/v2 JSON path."
    )
    parser.add_argument(
        "--context-receipt", help="simpro-context-receipt/v1 JSON path."
    )
    parser.add_argument(
        "--article-slug",
        default="",
        help="Optional current article slug to avoid same-article repeats.",
    )
    parser.add_argument(
        "--title", default="", help="Optional article title for proof fit scoring."
    )
    parser.add_argument(
        "--objective",
        default="",
        help="Optional content objective for proof fit scoring.",
    )
    parser.add_argument(
        "--require-eeat-story",
        action="store_true",
        help="Only return review-story rows with a real identity and public review URL.",
    )
    parser.add_argument(
        "--proof-role",
        choices=["experience_story", "metric", "quote", "theme", "any"],
        default="any",
        help="Desired proof role for this selection pass.",
    )
    parser.add_argument(
        "--limit", type=int, default=8, help="Maximum number of candidates to return."
    )
    parser.add_argument(
        "--slate",
        action="store_true",
        help="Print a sidecar-ready Customer Proof Slate block instead of JSON.",
    )
    parser.add_argument(
        "--roles",
        default="metric,quote,theme",
        help="Comma-separated proof roles to include when --slate is used.",
    )
    parser.add_argument(
        "--selected",
        action="append",
        default=[],
        help="Override selected proof for a slate role, e.g. metric=proof_id. Repeatable.",
    )
    parser.add_argument(
        "--reject",
        action="append",
        default=[],
        help="Document a rejected stronger candidate, e.g. metric=proof_id:section-specific reason. Repeatable.",
    )
    parser.add_argument(
        "--evidence-output",
        help="Write a hash-bound JSON record of selector inputs and verified candidates.",
    )
    parser.add_argument(
        "--allow-no-proof",
        action="store_true",
        help=(
            "Allow a full four-role slate to emit no-fit evidence when the "
            "current connector context has no bound customer proof candidates."
        ),
    )
    args = parser.parse_args(argv)
    if args.evidence_output and not args.slate:
        parser.error("--evidence-output requires --slate")
    if args.allow_no_proof and not args.evidence_output:
        parser.error("--allow-no-proof requires --evidence-output")

    try:
        if args.slate:
            try:
                roles = _parse_roles(args.roles)
                selected_overrides = _parse_selected_overrides(args.selected)
                rejected_overrides = _parse_rejected_overrides(args.reject)
            except ValueError as exc:
                parser.error(str(exc))
            if args.allow_no_proof and set(roles) != SLATE_ROLES:
                parser.error(
                    "--allow-no-proof requires --roles metric,quote,theme,experience_story"
                )
            reference_date = date.today()
            snapshot_context = (
                _selector_input_snapshot(
                    index_path=args.index,
                    ledger_path=args.ledger,
                    context_pack=args.context_pack,
                    context_receipt=args.context_receipt,
                )
                if args.evidence_output
                else nullcontext(None)
            )
            with snapshot_context as input_snapshot:
                role_evidence: List[FindingDict] = []
                slate = build_customer_proof_slate(
                    args.topic,
                    index_path=args.index,
                    ledger_path=args.ledger,
                    context_pack=args.context_pack,
                    context_receipt=args.context_receipt,
                    article_slug=args.article_slug,
                    title=args.title,
                    objective=args.objective,
                    require_eeat_story=args.require_eeat_story,
                    roles=roles,
                    limit=args.limit,
                    selected_overrides=selected_overrides,
                    rejected_overrides=rejected_overrides,
                    allow_no_proof=args.allow_no_proof,
                    reference_date=reference_date,
                    _role_evidence=role_evidence,
                    _input_snapshot=input_snapshot,
                )
                if args.evidence_output:
                    if input_snapshot is None:  # pragma: no cover - context invariant.
                        raise CustomerProofDataError(
                            "Selector evidence input snapshot is unavailable"
                        )
                    evidence_path, evidence_hash = _write_selector_evidence(
                        args.evidence_output,
                        topic=args.topic,
                        title=args.title,
                        objective=args.objective,
                        article_slug=args.article_slug,
                        roles=roles,
                        require_eeat_story=args.require_eeat_story,
                        limit=args.limit,
                        reference_date=reference_date,
                        selected_overrides=selected_overrides,
                        rejected_overrides=rejected_overrides,
                        allow_no_proof=args.allow_no_proof,
                        role_evidence=role_evidence,
                        input_snapshot=input_snapshot,
                    )
                    slate_lines = slate.splitlines()
                    slate_lines.insert(
                        2,
                        f"- Selector evidence: {evidence_path} | SHA-256: {evidence_hash}",
                    )
                    slate = "\n".join(slate_lines)
            print(slate)
        else:
            results = select_customer_proofs(
                args.topic,
                index_path=args.index,
                ledger_path=args.ledger,
                context_pack=args.context_pack,
                context_receipt=args.context_receipt,
                article_slug=args.article_slug,
                title=args.title,
                objective=args.objective,
                require_eeat_story=args.require_eeat_story,
                proof_role=args.proof_role,
                limit=args.limit,
            )
            print(json.dumps({"topic": args.topic, "results": results}, indent=2))
    except CustomerProofDataError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    return 0


__all__ = [
    '_main'
]
