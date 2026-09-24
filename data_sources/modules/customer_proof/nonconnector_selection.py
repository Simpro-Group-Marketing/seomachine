"""Select public proof for nonconnector brand workflows."""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any

from .nonconnector_contracts import (
    SUPPORTED_BRAND_HOSTS,
    SUPPORTED_ROLES,
    NonVaultProofDataError,
)
from .nonconnector_eligibility import (
    _brand_key,
    _eligible_source,
    _recent_uses,
    _relevance_score,
    _source_weight,
    _supports_role,
    _tokens,
)
from .nonconnector_inputs import _read_json


def select_nonvault_customer_proofs(
    topic: str,
    *,
    brand: str,
    index_path: str | Path = "context/customer-proof-index.json",
    ledger_path: str | Path = "context/customer-proof-usage-ledger.json",
    title: str = "",
    objective: str = "",
    article_slug: str = "",
    proof_role: str = "theme",
    require_eeat_story: bool = False,
    limit: int = 10,
    reference_date: date | None = None,
) -> list[dict[str, Any]]:
    """Return approved, brand-owned proof candidates for one nonconnector brand."""
    del article_slug
    if proof_role not in SUPPORTED_ROLES:
        raise NonVaultProofDataError(f"unsupported proof role: {proof_role}")
    if isinstance(limit, bool) or not isinstance(limit, int) or not 0 <= limit <= 100:
        raise NonVaultProofDataError("limit must be an integer from 0 to 100")
    brand_key = _brand_key(brand)
    expected_host = SUPPORTED_BRAND_HOSTS[brand_key]
    index = _read_json(index_path, "customer proof index")
    ledger = _read_json(ledger_path, "customer proof usage ledger")
    query_tokens = _tokens(" ".join((topic, title, objective)))
    reference = reference_date or date.today()

    ranked: list[dict[str, Any]] = []
    for source in index.get("proof", []):
        if not isinstance(source, dict):
            continue
        if not _eligible_source(source, expected_host=expected_host, brand_key=brand_key):
            continue
        if not _supports_role(source, proof_role, require_eeat_story=require_eeat_story):
            continue
        candidate = dict(source)
        candidate["proof_role"] = proof_role
        candidate["relevance_score"] = _relevance_score(query_tokens, source)
        candidate["recent_uses_90d"] = _recent_uses(
            ledger,
            proof_id=str(source.get("proof_id") or ""),
            reference_date=reference,
        )
        candidate["score"] = (
            candidate["relevance_score"]
            + _source_weight(str(source.get("source_type") or ""))
            - candidate["recent_uses_90d"] * 20
        )
        ranked.append(candidate)

    ranked.sort(
        key=lambda row: (
            -int(row.get("score", 0)),
            str(row.get("proof_id") or ""),
        )
    )
    return ranked[:limit]


__all__ = [
    'select_nonvault_customer_proofs'
]
