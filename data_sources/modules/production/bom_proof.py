"""Proof resolution for the production BOM: text is copied from approved sources, never typed."""

from __future__ import annotations

import copy
import json
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

from data_sources.modules.production.layout import Layout
from data_sources.modules.vault_claim_receipts import (
    ApprovedClaim,
    ValidatedClaimSet,
    VaultClaimReceiptError,
)

NONVAULT_INDEX = Path("config") / "nonvault-customer-proof-index.json"
ClaimLoader = Callable[[Path, Path], ValidatedClaimSet]


def _spec_keep(item: Mapping[str, Any]) -> dict[str, Any]:
    return {key: item[key] for key in ("id", "claim_id", "kind", "priority")}


def _connector_item(item: Mapping[str, Any], claim: ApprovedClaim) -> dict[str, Any]:
    evidence = claim.evidence
    customer = evidence.get("customer", "") if isinstance(evidence, Mapping) else ""
    return {
        **_spec_keep(item),
        "text": claim.assertion,
        "use_mode": claim.use_mode,
        "claim_type": claim.claim_type,
        "url": claim.public_url,
        "receipt_revision": claim.receipt_revision,
        "customer": customer,
    }


def resolve_connector_proof(
    proof: list[Mapping[str, Any]], layout: Layout, claim_loader: ClaimLoader
) -> list[dict[str, Any]]:
    """Resolve spec proof items against the receipt-approved claim set."""
    try:
        claim_set = claim_loader(layout.context_pack, layout.context_receipt)
    except VaultClaimReceiptError as error:
        raise ValueError(f"vault claim set could not be validated: {error}") from error
    if claim_set.blocker:
        raise ValueError(f"vault claim set is blocked: {claim_set.blocker}")
    claims = {claim.claim_id: claim for claim in claim_set.approved_claims()}
    missing = [item["claim_id"] for item in proof if item["claim_id"] not in claims]
    if missing:
        raise ValueError(
            "proof claim_id is not an approved claim in the validated context: " + ", ".join(missing)
        )
    return [_connector_item(item, claims[item["claim_id"]]) for item in proof]


def _load_nonvault_rows(root: Path) -> dict[str, Mapping[str, Any]]:
    path = root / NONVAULT_INDEX
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise ValueError(f"nonvault proof index cannot be read: {path}: {error}") from error
    rows = payload.get("proof") if isinstance(payload, Mapping) else None
    if not isinstance(rows, list):
        raise ValueError(f"nonvault proof index {path} has no proof list")
    return {
        row["proof_id"]: row
        for row in rows
        if isinstance(row, Mapping)
        and row.get("approval_status") == "approved"
        and row.get("public_copy_allowed") is True
        and isinstance(row.get("proof_id"), str)
    }


def _nonconnector_item(item: Mapping[str, Any], row: Mapping[str, Any]) -> dict[str, Any]:
    quotes = [
        copy.deepcopy(quote)
        for quote in row.get("approved_quotes") or []
        if isinstance(quote, Mapping) and quote.get("status") == "approved"
    ]
    return {
        **_spec_keep(item),
        "text": row.get("evidence", ""),
        "customer": row.get("customer", ""),
        "url": row.get("public_url", ""),
        "restrictions": copy.deepcopy(row.get("restrictions") or []),
        "approved_quotes": quotes,
        "approved_metrics": copy.deepcopy(row.get("approved_metrics") or []),
    }


def resolve_nonconnector_proof(proof: list[Mapping[str, Any]], root: Path) -> list[dict[str, Any]]:
    """Resolve spec proof items against approved, public-copy-allowed nonvault rows."""
    if not proof:
        return []
    rows = _load_nonvault_rows(root)
    missing = [item["claim_id"] for item in proof if item["claim_id"] not in rows]
    if missing:
        raise ValueError(
            "proof claim_id is not an approved nonvault row with public_copy_allowed: " + ", ".join(missing)
        )
    return [_nonconnector_item(item, rows[item["claim_id"]]) for item in proof]
