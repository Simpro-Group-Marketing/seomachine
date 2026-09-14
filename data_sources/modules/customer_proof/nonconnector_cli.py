"""CLI for nonconnector customer-proof selection."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from typing import Sequence

from .nonconnector_contracts import SUPPORTED_ROLES, NonVaultProofDataError
from .nonconnector_persistence import build_nonvault_customer_proof_slate, write_nonvault_selector_evidence
from .nonconnector_selection import select_nonvault_customer_proofs


def _main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Select public customer proof for a nonconnector brand."
    )
    parser.add_argument("topic")
    parser.add_argument(
        "--brand", required=True, choices=("AroFlo", "BigChange", "ClockShark")
    )
    parser.add_argument("--title", default="")
    parser.add_argument("--objective", default="")
    parser.add_argument("--article-slug", default="")
    parser.add_argument("--index", default="context/customer-proof-index.json")
    parser.add_argument("--ledger", default="context/customer-proof-usage-ledger.json")
    parser.add_argument("--roles", default="metric,quote,theme,experience_story")
    parser.add_argument("--require-eeat-story", action="store_true")
    parser.add_argument("--selected", action="append", default=[])
    parser.add_argument("--rejected", action="append", default=[])
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--reference-date", default=date.today().isoformat())
    parser.add_argument("--slate", action="store_true")
    parser.add_argument("--evidence-output")
    args = parser.parse_args(argv)
    try:
        roles = _parse_roles(args.roles)
        selected = _parse_selected(args.selected, roles)
        rejected = _parse_rejected(args.rejected, roles)
        reference = date.fromisoformat(args.reference_date)
        if args.evidence_output:
            output, digest, role_rows = write_nonvault_selector_evidence(
                args.evidence_output,
                topic=args.topic,
                brand=args.brand,
                title=args.title,
                objective=args.objective,
                article_slug=args.article_slug,
                roles=roles,
                require_eeat_story=args.require_eeat_story,
                limit=args.limit,
                reference_date=reference,
                selected_overrides=selected,
                rejected_overrides=rejected,
                index_path=args.index,
                ledger_path=args.ledger,
            )
        else:
            output = None
            digest = ""
            role_rows = []
            for role in roles:
                results = select_nonvault_customer_proofs(
                    args.topic,
                    brand=args.brand,
                    index_path=args.index,
                    ledger_path=args.ledger,
                    title=args.title,
                    objective=args.objective,
                    article_slug=args.article_slug,
                    proof_role=role,
                    require_eeat_story=role == "experience_story"
                    and args.require_eeat_story,
                    limit=args.limit,
                    reference_date=reference,
                )
                candidate_ids = [str(row["proof_id"]) for row in results]
                selected_id = str(selected.get(role) or "none")
                if selected_id != "none" and selected_id not in candidate_ids:
                    raise NonVaultProofDataError(
                        f"Selected customer proof ID is not in the verified {role} candidate slate: {selected_id}"
                    )
                role_rows.append(
                    {
                        "role": role,
                        "candidate_ids": candidate_ids,
                        "selected_id": selected_id,
                        "rejected_overrides": dict(rejected.get(role, {})),
                    }
                )
        if args.slate:
            command = (
                "python data_sources/modules/nonvault_customer_proof_selector.py "
                + json.dumps(args.topic)
            )
            print(
                build_nonvault_customer_proof_slate(
                    selector_command=command,
                    roles=role_rows,
                    evidence_path=str(output) if output else "",
                    evidence_sha256=digest,
                ),
                end="",
            )
        else:
            print(json.dumps(role_rows, indent=2, sort_keys=True))
        return 0
    except (NonVaultProofDataError, OSError, ValueError, json.JSONDecodeError) as exc:
        print(str(exc), file=sys.stderr)
        return 1


def _parse_roles(value: str) -> list[str]:
    roles = [role.strip() for role in value.split(",") if role.strip()]
    if (
        not roles
        or len(set(roles)) != len(roles)
        or any(role not in SUPPORTED_ROLES for role in roles)
    ):
        raise NonVaultProofDataError("roles must be unique supported proof roles")
    if "experience_story" not in roles:
        raise NonVaultProofDataError("roles must include experience_story")
    return roles


def _parse_selected(values: Sequence[str], roles: Sequence[str]) -> dict[str, str]:
    parsed: dict[str, str] = {}
    for value in values:
        role, separator, proof_id = value.partition("=")
        if not separator or role not in roles or not proof_id.strip():
            raise NonVaultProofDataError(f"invalid selected override: {value}")
        parsed[role] = proof_id.strip()
    return parsed


def _parse_rejected(
    values: Sequence[str], roles: Sequence[str]
) -> dict[str, dict[str, str]]:
    parsed: dict[str, dict[str, str]] = {}
    for value in values:
        role, separator, remainder = value.partition("=")
        proof_id, reason_separator, reason = remainder.partition(":")
        if (
            not separator
            or not reason_separator
            or role not in roles
            or not proof_id.strip()
            or not reason.strip()
        ):
            raise NonVaultProofDataError(f"invalid rejected override: {value}")
        parsed.setdefault(role, {})[proof_id.strip()] = reason.strip()
    return parsed


__all__ = [
    '_main',
    '_parse_roles',
    '_parse_selected',
    '_parse_rejected'
]
