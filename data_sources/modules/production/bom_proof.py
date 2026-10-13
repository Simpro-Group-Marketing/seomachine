"""Proof resolution for the production BOM: text is copied from approved sources, never typed."""

from __future__ import annotations

import copy
import json
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

from data_sources.modules.customer_proof.contracts import CUSTOMER_PROOF_USE_MODES, SLATE_ROLES
from data_sources.modules.customer_proof.nonconnector_contracts import SUPPORTED_BRAND_HOSTS
from data_sources.modules.customer_proof.nonconnector_eligibility import (
    NonVaultProofDataError,
    _brand_key,
    _eligible_source,
)
from data_sources.modules.production.bom import BuildEnvironmentError
from data_sources.modules.production.layout import Layout
from data_sources.modules.vault_claim_receipts import (
    ApprovedClaim,
    ValidatedClaimSet,
    VaultClaimReceiptError,
)

NONVAULT_INDEX = Path("config") / "nonvault-customer-proof-index.json"
ClaimLoader = Callable[[Path, Path], ValidatedClaimSet]
# Mirrors customer_proof/ranking.py:_use_modes_for_role.
_ROLE_USE_MODE = {
    "metric": "public_metric",
    "quote": "exact_quote",
    "theme": "public_paraphrase",
    "experience_story": "public_paraphrase",
}


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


def _kind_error(item: Mapping[str, Any]) -> str:
    if item["kind"] not in SLATE_ROLES:
        return f"proof {item['id']} kind must be one of {sorted(SLATE_ROLES)}, found: {item['kind']!r}"
    return ""


def _use_mode_error(item: Mapping[str, Any], claim: ApprovedClaim) -> str:
    expected = _ROLE_USE_MODE[item["kind"]]
    if claim.use_mode not in CUSTOMER_PROOF_USE_MODES or claim.use_mode != expected:
        return (
            f"proof {item['id']} use_mode {claim.use_mode!r} of claim {claim.claim_id} "
            f"does not fit kind {item['kind']} (needs {expected})"
        )
    return ""


def _load_claims(layout: Layout, claim_loader: ClaimLoader) -> dict[str, ApprovedClaim]:
    try:
        claim_set = claim_loader(layout.context_pack, layout.context_receipt)
    except VaultClaimReceiptError as error:
        raise BuildEnvironmentError(f"vault claim set could not be validated: {error}") from error
    if claim_set.blocker:
        raise ValueError(f"vault claim set is blocked: {claim_set.blocker}")
    return {claim.claim_id: claim for claim in claim_set.approved_claims()}


def resolve_connector_proof(
    proof: list[Mapping[str, Any]], layout: Layout, claim_loader: ClaimLoader
) -> list[dict[str, Any]]:
    """Resolve spec proof items against the receipt-approved claim set."""
    claims = _load_claims(layout, claim_loader)
    errors = []
    for item in proof:
        claim = claims.get(item["claim_id"])
        if claim is None:
            errors.append(f"proof claim_id is not an approved claim in the validated context: {item['claim_id']}")
            continue
        error = _kind_error(item) or _use_mode_error(item, claim)
        if error:
            errors.append(error)
    if errors:
        raise ValueError("\n".join(errors))
    return [_connector_item(item, claims[item["claim_id"]]) for item in proof]


def _load_nonvault_rows(root: Path) -> list[Mapping[str, Any]]:
    path = root / NONVAULT_INDEX
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise BuildEnvironmentError(f"nonvault proof index cannot be read: {path}: {error}") from error
    rows = payload.get("proof") if isinstance(payload, Mapping) else None
    if not isinstance(rows, list):
        raise BuildEnvironmentError(f"nonvault proof index {path} has no proof list")
    return [row for row in rows if isinstance(row, Mapping)]


def _region_error(row: Mapping[str, Any], market: str) -> str:
    regions = {str(region).strip().casefold() for region in row.get("region") or []}
    if regions and market.strip().casefold() not in regions and "global" not in regions:
        return f"proof row {row.get('proof_id')} region {sorted(regions)} does not cover market {market}"
    return ""


def _role_error(item: Mapping[str, Any], row: Mapping[str, Any]) -> str:
    kind = item["kind"]
    if kind not in SLATE_ROLES:
        return _kind_error(item)
    needs = {
        "metric": bool(row.get("approved_metrics")),
        "quote": any(q.get("status") == "approved" for q in row.get("approved_quotes") or [] if isinstance(q, Mapping)),
        "experience_story": isinstance(row.get("review_story"), Mapping)
        and row["review_story"].get("story_allowed") is True,
        "theme": True,
    }
    if needs[kind]:
        return ""
    return f"proof {item['id']} kind {kind} is not supported by row {row.get('proof_id')} (no approved evidence for that role)"


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


def _scoped_rows(root: Path, brand: str) -> dict[str, Mapping[str, Any]]:
    try:
        key = _brand_key(brand)
    except NonVaultProofDataError as error:
        raise ValueError(str(error)) from error
    host = SUPPORTED_BRAND_HOSTS[key]
    return {
        row["proof_id"]: row
        for row in _load_nonvault_rows(root)
        if isinstance(row.get("proof_id"), str) and _eligible_source(row, expected_host=host, brand_key=key)
    }


def resolve_nonconnector_proof(
    proof: list[Mapping[str, Any]], root: Path, brand: str, market: str
) -> list[dict[str, Any]]:
    """Resolve spec proof items against approved, brand-scoped, market-scoped nonvault rows."""
    if not proof:
        return []
    rows = _scoped_rows(root, brand)
    errors = []
    for item in proof:
        row = rows.get(item["claim_id"])
        if row is None:
            errors.append(
                f"proof claim_id {item['claim_id']} is not an approved, public-copy-allowed {brand} nonvault row"
            )
            continue
        error = _region_error(row, market) or _role_error(item, row)
        if error:
            errors.append(error)
    if errors:
        raise ValueError("\n".join(errors))
    return [_nonconnector_item(item, rows[item["claim_id"]]) for item in proof]
