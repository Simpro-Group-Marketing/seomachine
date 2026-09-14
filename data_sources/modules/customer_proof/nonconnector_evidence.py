"""Validate nonconnector customer-proof selector evidence."""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any, Mapping

from .evidence_common import (
    artifacts_unchanged,
    limit_value,
    string_inputs_valid,
    verified_artifact_paths,
)
from .nonconnector_contracts import NonVaultProofDataError
from .nonconnector_selection import select_nonvault_customer_proofs


NONCONNECTOR_ROLES = {"metric", "quote", "theme", "experience_story"}


def verify_nonconnector_selector_evidence(
    evidence: dict[str, Any],
) -> dict[str, dict[str, Any]] | None:
    try:
        prepared = _nonconnector_inputs(evidence)
        if prepared is None:
            return None
        inputs, roles, recorded_roles, paths, limit, reference_date = prepared
        verified: dict[str, dict[str, Any]] = {}
        for role, recorded in zip(roles, recorded_roles):
            row = _verified_role(inputs, role, recorded, paths, limit, reference_date)
            if row is None:
                return None
            verified[role] = row
        return verified if artifacts_unchanged(evidence, paths) else None
    except (NonVaultProofDataError, KeyError, OSError, TypeError, ValueError):
        return None


def _nonconnector_inputs(
    evidence: Mapping[str, Any],
) -> tuple[dict[str, Any], list[str], list[Any], dict[str, Path], int, date] | None:
    inputs = evidence.get("inputs")
    recorded_roles = evidence.get("roles")
    if not isinstance(inputs, dict) or not isinstance(recorded_roles, list):
        return None
    paths = verified_artifact_paths(evidence, ("index", "ledger"))
    roles = inputs.get("roles")
    strings = ("brand", "topic", "title", "objective", "article_slug", "reference_date")
    limit = limit_value(inputs)
    if not _input_shape_valid(inputs, roles, recorded_roles, strings) or paths is None or limit is None:
        return None
    return inputs, roles, recorded_roles, paths, limit, date.fromisoformat(str(inputs["reference_date"]))


def _input_shape_valid(
    inputs: Mapping[str, Any],
    roles: object,
    recorded_roles: list[Any],
    string_names: tuple[str, ...],
) -> bool:
    return bool(
        string_inputs_valid(inputs, string_names)
        and isinstance(roles, list)
        and set(roles) == NONCONNECTOR_ROLES
        and len(roles) == 4
        and inputs.get("require_eeat_story") is True
        and isinstance(inputs.get("selected_overrides", {}), dict)
        and isinstance(inputs.get("rejected_overrides", {}), dict)
        and len(recorded_roles) == len(roles)
    )


def _verified_role(
    inputs: Mapping[str, Any],
    role: str,
    recorded: object,
    paths: Mapping[str, Path],
    limit: int,
    reference_date: date,
) -> dict[str, Any] | None:
    if not isinstance(recorded, dict) or recorded.get("role") != role:
        return None
    results = select_nonvault_customer_proofs(
        str(inputs["topic"]),
        brand=str(inputs["brand"]),
        index_path=paths["index"],
        ledger_path=paths["ledger"],
        title=str(inputs["title"]),
        objective=str(inputs["objective"]),
        article_slug=str(inputs["article_slug"]),
        proof_role=role,
        require_eeat_story=role == "experience_story",
        limit=limit,
        reference_date=reference_date,
    )
    candidate_ids = [str(result["proof_id"]) for result in results if result.get("proof_id")]
    selected_id = str(inputs.get("selected_overrides", {}).get(role) or "none")
    selected = next((result for result in results if str(result.get("proof_id", "")) == selected_id), None)
    expected_binding = nonvault_experience_candidate_binding(selected) if role == "experience_story" and selected else None
    role_rejections = inputs.get("rejected_overrides", {}).get(role, {})
    if not isinstance(role_rejections, dict) or not _recorded_role_matches(recorded, candidate_ids, selected_id, expected_binding, role_rejections):
        return None
    return {
        "candidate_ids": candidate_ids,
        "claim_ids": [],
        "selected_id": selected_id,
        "selected_candidate": expected_binding,
        "rejected_overrides": {str(key): str(value) for key, value in role_rejections.items()},
    }


def _recorded_role_matches(
    recorded: Mapping[str, Any],
    candidate_ids: list[str],
    selected_id: str,
    expected_binding: dict[str, str] | None,
    rejected: Mapping[str, Any],
) -> bool:
    return bool(
        recorded.get("candidate_ids") == candidate_ids
        and str(recorded.get("selected_id")) == selected_id
        and recorded.get("selected_candidate") == expected_binding
        and recorded.get("rejected_overrides") == rejected
    )


def nonvault_experience_candidate_binding(candidate: Mapping[str, Any]) -> dict[str, str]:
    story = candidate.get("review_story")
    if not isinstance(story, dict):
        story = {}
    return {
        "proof_id": str(candidate.get("proof_id", "")).strip(),
        "identity": str(story.get("identity_display") or story.get("business_name") or story.get("person_name") or candidate.get("customer") or "").strip(),
        "public_url": str(story.get("public_url") or candidate.get("public_url") or "").strip(),
        "story": str(story.get("workflow_story") or candidate.get("evidence") or "").strip(),
    }


__all__ = ["nonvault_experience_candidate_binding", "verify_nonconnector_selector_evidence"]
