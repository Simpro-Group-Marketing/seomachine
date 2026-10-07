"""Prefilled Customer Proof Selection Decision block for the selector CLI.

Only fields the selector knows are emitted. Writers still add Reuse reason,
zero-use comparison, and Final use in copy directly under these bullets
(no blank line), because the guard reads one contiguous bullet list.
"""

from __future__ import annotations

from typing import Any, Callable, Mapping, Sequence

from .contracts import CustomerProofDataError

HEADING = "## Customer Proof Selection Decision"


def selected_proof_rows(
    role_evidence: Sequence[Mapping[str, Any]],
    lookup: Callable[[str], Sequence[Mapping[str, Any]]],
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for role_row in role_evidence:
        selected_id = str(role_row.get("selected_id") or "").strip()
        if not selected_id or selected_id.casefold() == "none":
            continue
        role = str(role_row.get("role") or "")
        match = next(
            (c for c in lookup(role) if str(c.get("proof_id")) == selected_id), None
        )
        if match is None:
            raise CustomerProofDataError(
                f"Selected {role} proof {selected_id} is missing from verified candidates"
            )
        rows.append(
            {
                "role": role,
                "proof_id": selected_id,
                "customer": str(match.get("customer") or "unknown"),
                "public_url": str(match.get("public_url") or ""),
                "claim_id": str(match.get("claim_id") or selected_id),
            }
        )
    return rows


def selection_decision_block(
    rows: Sequence[Mapping[str, str]], *, selector_command: str
) -> str:
    lines = [HEADING, "", f"- Selector command: {selector_command}"]
    for row in rows:
        lines.append(
            f"- Selected proof: {row['proof_id']} | Customer: {row['customer']} "
            f"| URL: {row['public_url']} | Role: {row['role']} | Claim ID: {row['claim_id']}"
        )
    return "\n".join(lines)


__all__ = ["HEADING", "selected_proof_rows", "selection_decision_block"]
