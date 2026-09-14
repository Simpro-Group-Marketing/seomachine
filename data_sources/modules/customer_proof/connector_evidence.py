"""Validate connector-bound customer-proof selector evidence."""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any, Mapping

from .contracts import CustomerProofDataError
from .evidence_common import (
    artifacts_unchanged,
    limit_value,
    overrides_valid,
    string_inputs_valid,
    verified_artifact_paths,
)
from .selection import select_customer_proofs


CONNECTOR_EVIDENCE_SCHEMA = "simpro-customer-proof-selector-evidence/v1"
CONNECTOR_ROLES = {"experience_story", "metric", "quote", "theme"}


def verify_connector_selector_evidence(
    evidence: dict[str, Any],
) -> dict[str, dict[str, Any]] | None:
    try:
        prepared = _connector_inputs(evidence)
        if prepared is None:
            return None
        inputs, roles, recorded_roles, artifact_paths, limit, reference_date = prepared
        if evidence.get("selection_outcome") == "no_fit_customer_proof":
            verified = _verify_no_fit_roles(inputs, roles, recorded_roles)
        else:
            verified = _verify_selected_roles(
                inputs,
                roles,
                recorded_roles,
                artifact_paths,
                limit,
                reference_date,
            )
        if verified is None or not artifacts_unchanged(evidence, artifact_paths):
            return None
        return verified
    except (CustomerProofDataError, KeyError, OSError, TypeError, ValueError):
        return None


def _connector_inputs(
    evidence: Mapping[str, Any],
) -> tuple[dict[str, Any], list[str], list[Any], dict[str, Path], int, date] | None:
    inputs = evidence.get("inputs")
    recorded_roles = evidence.get("roles")
    if not isinstance(inputs, dict) or not isinstance(recorded_roles, list):
        return None
    paths = verified_artifact_paths(evidence, ("index", "ledger", "context_pack", "context_receipt"))
    if paths is None or not _connector_input_shape(inputs, recorded_roles):
        return None
    limit = limit_value(inputs)
    reference_date = date.fromisoformat(str(inputs["reference_date"]))
    if limit is None or reference_date != date.today():
        return None
    roles = inputs["roles"]
    return inputs, roles, recorded_roles, paths, limit, reference_date


def _connector_input_shape(inputs: Mapping[str, Any], recorded_roles: list[Any]) -> bool:
    roles = inputs.get("roles")
    strings = ("topic", "title", "objective", "article_slug", "reference_date")
    return bool(
        string_inputs_valid(inputs, strings)
        and isinstance(roles, list)
        and roles
        and all(role in CONNECTOR_ROLES for role in roles)
        and len(set(roles)) == len(roles)
        and "experience_story" in roles
        and inputs.get("require_eeat_story") is True
        and overrides_valid(inputs)
        and len(recorded_roles) == len(roles)
    )


def _verify_no_fit_roles(
    inputs: Mapping[str, Any],
    roles: list[str],
    recorded_roles: list[Any],
) -> dict[str, dict[str, Any]] | None:
    if inputs.get("allow_no_proof") is not True or set(roles) != CONNECTOR_ROLES:
        return None
    verified: dict[str, dict[str, Any]] = {}
    rejected = inputs.get("rejected_overrides", {})
    for role, recorded in zip(roles, recorded_roles):
        row = _verified_no_fit_role(role, recorded, rejected.get(role, {}))
        if row is None:
            return None
        verified[role] = row
    return verified


def _verified_no_fit_role(
    role: str,
    recorded: object,
    role_rejections: object,
) -> dict[str, Any] | None:
    if not isinstance(recorded, dict) or recorded.get("role") != role or not isinstance(role_rejections, dict):
        return None
    no_fit_reason = str(recorded.get("no_fit_reason") or "")
    valid = (
        recorded.get("selection_outcome") == "no_fit_customer_proof"
        and recorded.get("candidate_ids") == []
        and recorded.get("claim_ids") == []
        and str(recorded.get("selected_id", "")).casefold() == "none"
        and "public copy must omit customer proof" in no_fit_reason.casefold()
    )
    if not valid:
        return None
    return {
        "candidate_ids": [],
        "claim_ids": [],
        "selected_id": "none",
        "selected_candidate": None,
        "no_fit_reason": no_fit_reason,
        "rejected_overrides": {str(key): str(value) for key, value in role_rejections.items()},
    }


def _verify_selected_roles(
    inputs: Mapping[str, Any],
    roles: list[str],
    recorded_roles: list[Any],
    paths: Mapping[str, Path],
    limit: int,
    reference_date: date,
) -> dict[str, dict[str, Any]] | None:
    verified: dict[str, dict[str, Any]] = {}
    for role, recorded in zip(roles, recorded_roles):
        row = _verify_selected_role(inputs, role, recorded, paths, limit, reference_date)
        if row is None:
            return None
        verified[role] = row
    return verified


def _verify_selected_role(
    inputs: Mapping[str, Any],
    role: str,
    recorded: object,
    paths: Mapping[str, Path],
    limit: int,
    reference_date: date,
) -> dict[str, Any] | None:
    if not isinstance(recorded, dict) or recorded.get("role") != role:
        return None
    results = select_customer_proofs(
        str(inputs["topic"]),
        index_path=paths["index"],
        ledger_path=paths["ledger"],
        context_pack=paths["context_pack"],
        context_receipt=paths["context_receipt"],
        article_slug=str(inputs["article_slug"]),
        title=str(inputs["title"]),
        objective=str(inputs["objective"]),
        require_eeat_story=role == "experience_story",
        proof_role=role,
        limit=limit,
        reference_date=reference_date,
    )
    candidate_ids = [str(result["proof_id"]) for result in results if result.get("proof_id")]
    claim_ids = [str(result["claim_id"]) for result in results if result.get("claim_id")]
    selected_id = str(inputs.get("selected_overrides", {}).get(role) or (candidate_ids[0] if candidate_ids else "none"))
    if not _recorded_selection_matches(recorded, candidate_ids, claim_ids, selected_id):
        return None
    role_rejections = inputs.get("rejected_overrides", {}).get(role, {})
    if not isinstance(role_rejections, dict):
        return None
    selected = next((result for result in results if str(result.get("proof_id", "")) == selected_id), None)
    return {
        "candidate_ids": candidate_ids,
        "claim_ids": claim_ids,
        "selected_id": selected_id,
        "selected_candidate": experience_candidate_binding(selected) if role == "experience_story" and selected else None,
        "rejected_overrides": {str(key): str(value) for key, value in role_rejections.items()},
    }


def _recorded_selection_matches(
    recorded: Mapping[str, Any],
    candidate_ids: list[str],
    claim_ids: list[str],
    selected_id: str,
) -> bool:
    return bool(
        recorded.get("candidate_ids") == candidate_ids
        and recorded.get("claim_ids") == claim_ids
        and str(recorded.get("selected_id")) == selected_id
    )


def experience_candidate_binding(candidate: Mapping[str, Any]) -> dict[str, str]:
    story = candidate.get("review_story")
    if not isinstance(story, dict):
        story = {}
    identity = str(story.get("identity_display") or story.get("person_name") or story.get("business_name") or candidate.get("customer") or "").strip()
    public_url = str(story.get("public_url") or candidate.get("public_url") or "").strip()
    story_text = str(story.get("workflow_story") or candidate.get("evidence") or " ".join(str(value) for value in candidate.get("themes", []) or [])).strip()
    return {
        "proof_id": str(candidate.get("proof_id", "")).strip(),
        "claim_id": str(candidate.get("claim_id", "")).strip(),
        "identity": identity,
        "public_url": public_url,
        "story": story_text,
    }


__all__ = ["CONNECTOR_EVIDENCE_SCHEMA", "experience_candidate_binding", "verify_connector_selector_evidence"]
