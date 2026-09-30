"""Connector-bound customer-proof selection orchestration."""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence

from ..proof_usage import count_customer_proof_usage
from .connector_inputs import (
    _load_json,
    _load_receipt_claims,
    _require_complete_claim_searches,
)
from .contracts import (
    DEFAULT_LEDGER_PATH,
    LEGACY_INDEX_ERROR,
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
    index_path: str | Path | None = None,
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
    claim_lookup_evidence: Optional[Mapping[str, Any]] = None,
    _input_snapshot: Optional[_SelectorInputSnapshot] = None,
) -> List[FindingDict]:
    """Return ranked vault-approved customer proof claims for a topic."""
    if index_path is not None:
        raise CustomerProofDataError(LEGACY_INDEX_ERROR)
    reference = reference_date or date.today()
    if _input_snapshot is None:
        ledger = _load_json(ledger_path, "customer proof ledger")
        receipt_claims = _load_receipt_claims(context_pack, context_receipt)
        receipt_payload = _load_json(context_receipt, "context receipt")
    else:
        ledger = _input_snapshot.ledger
        receipt_claims = _input_snapshot.receipt_claims
        receipt_payload = _input_snapshot.context_receipt
        claim_lookup_evidence = _input_snapshot.claim_lookup
    use_modes = _use_modes_for_role(proof_role)
    _require_complete_claim_searches(
        receipt_payload,
        sorted(use_modes),
        claim_lookup=claim_lookup_evidence,
    )
    proof_rows = [
        _candidate_from_claim(claim)
        for claim in receipt_claims.approved_claims()
        if str(getattr(claim, "use_mode", "") or "") in use_modes
    ]
    search_text = " ".join(part for part in (topic, title, objective) if part)
    topic_tokens = _tokens(search_text)

    scored = []
    for candidate in proof_rows:
        if not isinstance(candidate, dict):
            continue
        if require_eeat_story and not _is_review_story_eligible(candidate):
            continue
        if not _matches_proof_role(candidate, proof_role):
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
        result["binding_source"] = "claim_id"
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
    index_path: str | Path | None = None,
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
    claim_lookup_evidence: Optional[Mapping[str, Any]] = None,
    _role_evidence: Optional[List[FindingDict]] = None,
    _input_snapshot: Optional[_SelectorInputSnapshot] = None,
) -> str:
    """Return a sidecar-ready Customer Proof Slate block."""
    if index_path is not None:
        raise CustomerProofDataError(LEGACY_INDEX_ERROR)
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
            claim_lookup_evidence=claim_lookup_evidence,
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
    return "no approved customer proof claims" in str(error)


def _candidate_from_claim(claim: Any) -> FindingDict:
    evidence = getattr(claim, "evidence", None)
    evidence_row = dict(evidence) if isinstance(evidence, Mapping) else {}
    claim_id = str(getattr(claim, "claim_id", "") or "").strip()
    public_url = str(getattr(claim, "public_url", "") or "").strip()
    use_mode = str(getattr(claim, "use_mode", "") or "").strip()
    assertion = str(getattr(claim, "assertion", "") or "").strip()
    identity = _first_text(
        evidence_row,
        (
            "identity",
            "identity_display",
            "customer",
            "customer_name",
            "business_name",
            "person_name",
            "attribution",
            "source_title",
            "title",
        ),
    )
    story = _first_text(
        evidence_row,
        (
            "story",
            "workflow_story",
            "experience_story",
            "paraphrase_evidence",
            "evidence",
            "assertion",
        ),
    ) or assertion
    source_type = _source_type_for_claim(evidence_row, public_url, use_mode)
    topics = _string_values(
        evidence_row,
        (
            "topics",
            "topic",
            "entities",
            "industry",
            "industries",
            "region",
            "source_collection",
            "proof_type",
            "claim_type",
        ),
    )
    candidate: FindingDict = {
        "proof_id": claim_id,
        "candidate_id": claim_id,
        "claim_id": claim_id,
        "selector_id": str(getattr(claim, "selector_id", "") or "").strip(),
        "customer": identity or _customer_from_url(public_url),
        "source_type": source_type,
        "industry": topics,
        "region": _string_values(evidence_row, ("region", "regions", "market")),
        "workflow_fit": topics,
        "themes": _string_values(evidence_row, ("themes", "topics", "entities")),
        "evidence": assertion,
        "restrictions": _string_values(evidence_row, ("use_boundaries", "restrictions")),
        "public_url": public_url,
        "approval_status": "approved",
        "public_copy_allowed": bool(public_url.startswith(("http://", "https://"))),
        "use_mode": use_mode,
        "claim_type": str(getattr(claim, "claim_type", "") or "").strip(),
        "authority_resource_id": str(
            getattr(claim, "authority_resource_id", "") or ""
        ).strip(),
        "source_hash": str(getattr(claim, "source_hash", "") or "").strip(),
        "brand_scope": list(getattr(claim, "brand_scope", ()) or ()),
        "approval_source": str(getattr(claim, "approval_source", "") or "").strip(),
        "context_receipt_revision": str(
            getattr(claim, "receipt_revision", "") or ""
        ).strip(),
        "evidence_anchor": str(getattr(claim, "evidence_anchor", "") or "").strip(),
        "approved_metrics": [],
        "approved_quotes": [],
        "review_story": {"story_allowed": False},
    }
    if use_mode == "public_metric":
        candidate["approved_metrics"] = [
            {
                "claim": assertion,
                "status": "approved",
                "url": public_url,
                "claim_id": claim_id,
            }
        ]
    if use_mode == "exact_quote":
        candidate["approved_quotes"] = [
            {
                "quote": assertion,
                "status": "approved",
                "url": public_url,
                "claim_id": claim_id,
            }
        ]
    if use_mode == "public_paraphrase" and identity and public_url.startswith(
        ("http://", "https://")
    ):
        candidate["review_story"] = {
            "story_allowed": True,
            "identity_type": _identity_type(evidence_row),
            "identity_display": identity,
            "business_name": _first_text(evidence_row, ("business_name", "customer")),
            "person_name": _first_text(evidence_row, ("person_name",)),
            "public_url": public_url,
            "workflow_story": story,
            "verification_status": "vault-approved-claim",
        }
    return candidate


def _source_type_for_claim(
    evidence: Mapping[str, Any],
    public_url: str,
    use_mode: str,
) -> str:
    raw = " ".join(
        value.casefold()
        for value in _string_values(
            evidence,
            (
                "source_type",
                "proof_type",
                "source_collection",
                "claim_type",
                "authority_resource_id",
            ),
        )
    )
    url = public_url.casefold()
    if "review" in raw or any(
        host in url for host in ("g2.com", "capterra.", "softwareadvice.")
    ):
        return "review_site"
    if "quote" in raw or use_mode == "exact_quote":
        return "quote_matrix"
    if "reference" in raw:
        return "reference"
    if "customer story" in raw or "customer_story" in raw or "/customers/" in url:
        return "customer_story"
    if "case" in raw or "/case-studies/" in url or "/resources/case-study-" in url:
        return "case_study"
    if use_mode == "public_metric":
        return "quote_matrix"
    return "customer_story"


def _identity_type(evidence: Mapping[str, Any]) -> str:
    raw = str(evidence.get("identity_type") or "").strip().casefold()
    if raw in {"person", "business", "person_and_business"}:
        return raw
    if _first_text(evidence, ("person_name",)):
        return "person"
    return "business"


def _first_text(evidence: Mapping[str, Any], keys: Sequence[str]) -> str:
    for key in keys:
        value = evidence.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
        if isinstance(value, Mapping):
            nested = _first_text(value, ("name", "display", "title", "text"))
            if nested:
                return nested
    metadata = evidence.get("source_metadata")
    if isinstance(metadata, Mapping):
        return _first_text(metadata, keys)
    return ""


def _string_values(evidence: Mapping[str, Any], keys: Sequence[str]) -> list[str]:
    values: list[str] = []
    for key in keys:
        values.extend(_flatten_value(evidence.get(key)))
    metadata = evidence.get("source_metadata")
    if isinstance(metadata, Mapping):
        for key in keys:
            values.extend(_flatten_value(metadata.get(key)))
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        normalized = value.strip()
        if normalized and normalized.casefold() not in seen:
            seen.add(normalized.casefold())
            result.append(normalized)
    return result


def _flatten_value(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, Mapping):
        flattened: list[str] = []
        for item in value.values():
            flattened.extend(_flatten_value(item))
        return flattened
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        flattened = []
        for item in value:
            flattened.extend(_flatten_value(item))
        return flattened
    return [str(value)]


def _customer_from_url(public_url: str) -> str:
    slug = public_url.rstrip("/").rsplit("/", 1)[-1].replace("-", " ")
    return slug.strip().title() if slug else ""


__all__ = [
    "select_customer_proofs",
    "build_customer_proof_slate",
    "_is_no_bound_customer_proof_error",
    "_candidate_from_claim",
]
