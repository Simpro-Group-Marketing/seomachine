"""Connector-bound customer-proof selection orchestration."""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Dict, List, Optional, Sequence

from ..proof_usage import count_customer_proof_usage
from .connector_inputs import (
    _claim_binding_for_candidate,
    _has_inventory_bound_claim,
    _load_json,
    _load_receipt_claims,
)
from .contracts import (
    DEFAULT_INDEX_PATH,
    DEFAULT_LEDGER_PATH,
    NO_BOUND_CUSTOMER_PROOF_MESSAGE,
    NO_FIT_CUSTOMER_PROOF_OUTCOME,
    NO_FIT_CUSTOMER_PROOF_REASON,
    SLATE_ROLES,
    CustomerProofDataError,
    FindingDict,
    _SelectorInputSnapshot,
)
from .ranking import (
    _is_review_story_eligible,
    _matches_proof_role,
    _relevance_score,
    _score_candidate,
    _selection_reason,
    _source_intent_score,
    _tokens,
    _use_modes_for_role,
    _used_in_article,
)
from .slate import _format_rejected_candidates, _parse_roles, _slate_selector_command


def select_customer_proofs(
    topic: str,
    *,
    index_path: str | Path = DEFAULT_INDEX_PATH,
    ledger_path: str | Path = DEFAULT_LEDGER_PATH,
    context_pack: str | Path | None = None,
    context_receipt: str | Path | None = None,
    article_slug: str = "",
    title: str = "",
    objective: str = "",
    require_eeat_story: bool = False,
    proof_role: str = "any",
    limit: int = 8,
    reference_date: Optional[date] = None,
    _input_snapshot: Optional[_SelectorInputSnapshot] = None,
) -> List[FindingDict]:
    """Return ranked customer proof candidates for a topic."""
    reference = reference_date or date.today()
    if _input_snapshot is None:
        index = _load_json(index_path, "customer proof index")
        ledger = _load_json(ledger_path, "customer proof ledger")
        receipt_claims = _load_receipt_claims(context_pack, context_receipt)
    else:
        index = _input_snapshot.index
        ledger = _input_snapshot.ledger
        receipt_claims = _input_snapshot.receipt_claims
    proof_rows = [
        candidate
        for candidate in index.get("proof", [])
        if isinstance(candidate, dict)
        and str(candidate.get("proof_id") or "").strip()
        and str(candidate.get("public_url") or "")
        .strip()
        .startswith(("http://", "https://"))
    ]
    if not proof_rows:
        raise CustomerProofDataError(
            "Customer proof index has no usable public customer proof inventory rows."
        )
    inventory_ids = {str(candidate["proof_id"]).strip() for candidate in proof_rows}
    approved_claims = receipt_claims.approved_claims()
    if not _has_inventory_bound_claim(
        proof_rows,
        inventory_ids=inventory_ids,
        approved_claims=approved_claims,
    ):
        raise CustomerProofDataError(
            "Customer proof context receipt has no approved claims bound to the "
            "customer proof inventory by selector ID or exact public URL; rebuild "
            "the vault-owned selector bindings and context artifacts."
        )
    search_text = " ".join(part for part in (topic, title, objective) if part)
    topic_tokens = _tokens(search_text)

    scored = []
    for candidate in proof_rows:
        if not isinstance(candidate, dict):
            continue
        if require_eeat_story and not _is_review_story_eligible(candidate):
            continue
        use_modes = _use_modes_for_role(proof_role)
        claim_binding = _claim_binding_for_candidate(
            candidate,
            proof_rows=proof_rows,
            receipt_claims=receipt_claims,
            approved_claims=approved_claims,
            use_modes=use_modes,
        )
        if claim_binding is None:
            continue
        approved_claim = claim_binding.claim
        binding_source = claim_binding.binding_source
        if not _matches_proof_role(candidate, proof_role, approved_claim=approved_claim):
            continue
        result = dict(candidate)
        result.update(
            count_customer_proof_usage(
                ledger,
                proof_id=str(candidate.get("proof_id", "")),
                source_url=str(candidate.get("public_url", "")),
                customer=str(candidate.get("customer", "")),
                reference_date=reference,
            )
        )
        result["relevance_score"] = _relevance_score(topic_tokens, candidate)
        result["source_intent_score"] = _source_intent_score(search_text, candidate)
        result["proof_role"] = proof_role
        result["review_story_eligible"] = _is_review_story_eligible(candidate)
        result["claim_id"] = approved_claim.claim_id
        result["binding_source"] = binding_source
        result["approval_source"] = approved_claim.approval_source
        result["context_receipt_revision"] = approved_claim.receipt_revision
        result["score"] = _score_candidate(result)
        result["overused"] = bool(result.get("overused", False))
        result["selection_reason"] = _selection_reason(result)
        scored.append(result)

    if article_slug:
        scored = [
            candidate
            for candidate in scored
            if not _used_in_article(candidate, ledger.get("uses", []), article_slug)
        ] or scored

    scored.sort(
        key=lambda item: (
            item.get("score", 0),
            item.get("relevance_score", 0),
            -item.get("recent_uses_90d", 0),
            str(item.get("proof_id", "")),
        ),
        reverse=True,
    )
    return scored[: max(limit, 0)]


def build_customer_proof_slate(
    topic: str,
    *,
    index_path: str | Path = DEFAULT_INDEX_PATH,
    ledger_path: str | Path = DEFAULT_LEDGER_PATH,
    context_pack: str | Path | None = None,
    context_receipt: str | Path | None = None,
    article_slug: str = "",
    title: str = "",
    objective: str = "",
    require_eeat_story: bool = False,
    roles: Sequence[str] = ("metric", "quote", "theme"),
    limit: int = 8,
    selected_overrides: Optional[Dict[str, str]] = None,
    rejected_overrides: Optional[Dict[str, Dict[str, str]]] = None,
    allow_no_proof: bool = False,
    reference_date: Optional[date] = None,
    _role_evidence: Optional[List[FindingDict]] = None,
    _input_snapshot: Optional[_SelectorInputSnapshot] = None,
) -> str:
    """Return a sidecar-ready Customer Proof Slate block."""
    selected = selected_overrides or {}
    rejected = rejected_overrides or {}
    normalized_roles = _parse_roles(
        ",".join(roles) if not isinstance(roles, str) else roles
    )
    if allow_no_proof and set(normalized_roles) != SLATE_ROLES:
        raise CustomerProofDataError(
            "No-proof customer proof evidence requires metric, quote, theme, "
            "and experience_story roles."
        )
    command = _slate_selector_command(
        topic,
        title=title,
        objective=objective,
        context_pack=context_pack,
        context_receipt=context_receipt,
        require_eeat_story=require_eeat_story,
        roles=normalized_roles,
        limit=limit,
        allow_no_proof=allow_no_proof,
    )
    lines = [
        "Customer Proof Slate",
        f"- Selector command: {command}",
        f"- Context receipt: {context_receipt or 'not supplied'}",
        "- Approval source: connector_claim_result",
    ]
    no_fit_roles: set[str] = set()
    for role in normalized_roles:
        no_fit_reason = ""
        results = select_customer_proofs(
            topic,
            index_path=index_path,
            ledger_path=ledger_path,
            context_pack=context_pack,
            context_receipt=context_receipt,
            article_slug=article_slug,
            title=title,
            objective=objective,
            require_eeat_story=require_eeat_story and role == "experience_story",
            proof_role=role,
            limit=limit,
            reference_date=reference_date,
            _input_snapshot=_input_snapshot,
        )
        if allow_no_proof and not results:
            no_fit_reason = NO_FIT_CUSTOMER_PROOF_REASON
            no_fit_roles.add(role)
        top_candidates = [
            str(result.get("proof_id", ""))
            for result in results
            if result.get("proof_id")
        ]
        claim_ids = [
            str(result.get("claim_id", ""))
            for result in results
            if result.get("claim_id")
        ]
        receipt_revision = next(
            (
                str(result.get("context_receipt_revision", ""))
                for result in results
                if result.get("context_receipt_revision")
            ),
            "not available",
        )
        selected_override = str(selected.get(role) or "").strip()
        if (
            selected_override
            and selected_override.casefold() != "none"
            and selected_override not in top_candidates
        ):
            raise CustomerProofDataError(
                "Selected customer proof ID is not in the verified "
                f"{role} candidate slate: {selected_override}"
            )
        selected_id = selected_override or (
            top_candidates[0] if top_candidates else "none"
        )
        rejected_text = _format_rejected_candidates(rejected.get(role, {}))
        lines.append(
            "- Role: "
            f"{role} | Top candidates: [{', '.join(top_candidates) if top_candidates else 'none'}] "
            f"| Selected: [{selected_id}] | Claim IDs: [{', '.join(claim_ids) if claim_ids else 'none'}] "
            f"| Receipt revision: {receipt_revision} | Rejected stronger candidates: [{rejected_text}]"
        )
        if no_fit_reason:
            lines.append(f"  - No-fit reason: {no_fit_reason}")
        if _role_evidence is not None:
            row = {
                "role": role,
                "candidate_ids": top_candidates,
                "claim_ids": claim_ids,
                "receipt_revision": receipt_revision,
                "selected_id": selected_id,
            }
            if no_fit_reason:
                row["selection_outcome"] = NO_FIT_CUSTOMER_PROOF_OUTCOME
                row["no_fit_reason"] = no_fit_reason
            _role_evidence.append(row)
    if no_fit_roles and no_fit_roles == set(normalized_roles):
        lines.insert(4, f"- Selection outcome: {NO_FIT_CUSTOMER_PROOF_OUTCOME}")
    return "\n".join(lines)


def _is_no_bound_customer_proof_error(error: CustomerProofDataError) -> bool:
    return NO_BOUND_CUSTOMER_PROOF_MESSAGE in str(error)


__all__ = [
    'select_customer_proofs',
    'build_customer_proof_slate',
    '_is_no_bound_customer_proof_error'
]
