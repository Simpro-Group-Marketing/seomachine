"""Shared validation for hash-bound customer proof selector evidence."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import date
from pathlib import Path
from typing import Any, Dict, Optional

try:
    from .customer_proof_selector import CustomerProofDataError, select_customer_proofs
    from .nonvault_customer_proof_selector import (
        SCHEMA as NONVAULT_SELECTOR_EVIDENCE_SCHEMA,
        NonVaultProofDataError,
        select_nonvault_customer_proofs,
    )
except ImportError:  # pragma: no cover - supports direct script execution.
    from customer_proof_selector import CustomerProofDataError, select_customer_proofs
    from nonvault_customer_proof_selector import (
        SCHEMA as NONVAULT_SELECTOR_EVIDENCE_SCHEMA,
        NonVaultProofDataError,
        select_nonvault_customer_proofs,
    )


MAX_SELECTOR_EVIDENCE_BYTES = 1024 * 1024


def _selector_evidence_path(
    raw_path: str,
    proof_sidecar_path: str,
) -> Optional[Path]:
    candidate = Path(raw_path).expanduser()
    if candidate.is_absolute():
        return candidate.resolve()
    sidecar = Path(proof_sidecar_path).resolve()
    candidates = [
        Path.cwd() / candidate,
        sidecar.parent / candidate,
        sidecar.parent.parent / candidate,
    ]
    return next((path.resolve() for path in candidates if path.is_file()), None)


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def verify_selector_evidence_roles(
    proof_sidecar_content: str,
    proof_sidecar_path: Optional[str],
) -> Optional[Dict[str, Dict[str, Any]]]:
    if not proof_sidecar_path:
        return None
    sidecar_path = Path(proof_sidecar_path).resolve()
    try:
        if not sidecar_path.is_file():
            return None
        if sidecar_path.read_text(encoding="utf-8") != proof_sidecar_content:
            return None
    except (OSError, UnicodeError):
        return None
    evidence_match = re.search(
        r"(?im)^[-*+]\s*Selector evidence:\s*(.+?)\s*\|\s*"
        r"SHA-256:\s*([0-9a-f]{64})\s*$",
        proof_sidecar_content,
    )
    if not evidence_match:
        return None
    evidence_path = _selector_evidence_path(
        evidence_match.group(1).strip().strip("\"'"),
        str(sidecar_path),
    )
    if evidence_path is None or not evidence_path.is_file():
        return None
    try:
        if evidence_path.stat().st_size > MAX_SELECTOR_EVIDENCE_BYTES:
            return None
        evidence_bytes = evidence_path.read_bytes()
        if hashlib.sha256(evidence_bytes).hexdigest() != evidence_match.group(2):
            return None
        evidence = json.loads(evidence_bytes)
        if not isinstance(evidence, dict):
            return None
        if evidence.get("schema") == NONVAULT_SELECTOR_EVIDENCE_SCHEMA:
            return _verify_nonvault_selector_evidence(evidence)
        if evidence.get("schema") != "simpro-customer-proof-selector-evidence/v1":
            return None
        inputs = evidence["inputs"]
        artifacts = evidence["artifacts"]
        recorded_roles = evidence["roles"]
        if not isinstance(inputs, dict) or not isinstance(artifacts, dict):
            return None
        required_artifacts = {
            "index",
            "ledger",
            "context_pack",
            "context_receipt",
        }
        if set(artifacts) != required_artifacts:
            return None
        artifact_paths: Dict[str, Path] = {}
        for name in sorted(required_artifacts):
            record = artifacts[name]
            if not isinstance(record, dict):
                return None
            path = Path(str(record["path"])).expanduser()
            digest = str(record["sha256"])
            if (
                not path.is_absolute()
                or not re.fullmatch(r"[0-9a-f]{64}", digest)
                or not path.is_file()
                or _file_sha256(path) != digest
            ):
                return None
            artifact_paths[name] = path.resolve()

        roles = inputs["roles"]
        string_inputs = (
            "topic",
            "title",
            "objective",
            "article_slug",
            "reference_date",
        )
        if any(not isinstance(inputs.get(name), str) for name in string_inputs):
            return None
        if (
            not isinstance(roles, list)
            or not roles
            or any(
                role not in {"experience_story", "metric", "quote", "theme"}
                for role in roles
            )
            or len(set(roles)) != len(roles)
            or "experience_story" not in roles
            or inputs.get("require_eeat_story") is not True
        ):
            return None
        limit = inputs["limit"]
        if (
            isinstance(limit, bool)
            or not isinstance(limit, int)
            or not 0 <= limit <= 100
        ):
            return None
        reference_date = date.fromisoformat(str(inputs["reference_date"]))
        if reference_date != date.today():
            return None
        selected_overrides = inputs.get("selected_overrides", {})
        rejected_overrides = inputs.get("rejected_overrides", {})
        if not isinstance(selected_overrides, dict) or not isinstance(
            rejected_overrides, dict
        ):
            return None
        if any(
            not isinstance(role, str) or not isinstance(value, str)
            for role, value in selected_overrides.items()
        ):
            return None
        if any(
            not isinstance(role, str)
            or not isinstance(rows, dict)
            or any(
                not isinstance(candidate, str) or not isinstance(reason, str)
                for candidate, reason in rows.items()
            )
            for role, rows in rejected_overrides.items()
        ):
            return None
        if not isinstance(recorded_roles, list) or len(recorded_roles) != len(roles):
            return None

        if evidence.get("selection_outcome") == "no_fit_customer_proof":
            if inputs.get("allow_no_proof") is not True:
                return None
            if set(roles) != {"metric", "quote", "theme", "experience_story"}:
                return None
            verified_no_fit: Dict[str, Dict[str, Any]] = {}
            for role, recorded in zip(roles, recorded_roles):
                if not isinstance(recorded, dict) or recorded.get("role") != role:
                    return None
                if (
                    recorded.get("selection_outcome") != "no_fit_customer_proof"
                    or recorded.get("candidate_ids") != []
                    or recorded.get("claim_ids") != []
                    or str(recorded.get("selected_id", "")).casefold() != "none"
                ):
                    return None
                no_fit_reason = str(recorded.get("no_fit_reason") or "")
                if "public copy must omit customer proof" not in no_fit_reason.casefold():
                    return None
                role_rejections = rejected_overrides.get(role, {})
                if not isinstance(role_rejections, dict):
                    return None
                verified_no_fit[role] = {
                    "candidate_ids": [],
                    "claim_ids": [],
                    "selected_id": "none",
                    "selected_candidate": None,
                    "no_fit_reason": no_fit_reason,
                    "rejected_overrides": {
                        str(candidate): str(reason)
                        for candidate, reason in role_rejections.items()
                    },
                }
            for name, path in artifact_paths.items():
                if _file_sha256(path) != str(artifacts[name]["sha256"]):
                    return None
            return verified_no_fit

        verified: Dict[str, Dict[str, Any]] = {}
        for role, recorded in zip(roles, recorded_roles):
            if not isinstance(recorded, dict) or recorded.get("role") != role:
                return None
            results = select_customer_proofs(
                str(inputs["topic"]),
                index_path=artifact_paths["index"],
                ledger_path=artifact_paths["ledger"],
                context_pack=artifact_paths["context_pack"],
                context_receipt=artifact_paths["context_receipt"],
                article_slug=str(inputs["article_slug"]),
                title=str(inputs["title"]),
                objective=str(inputs["objective"]),
                require_eeat_story=role == "experience_story",
                proof_role=role,
                limit=limit,
                reference_date=reference_date,
            )
            candidate_ids = [
                str(result["proof_id"]) for result in results if result.get("proof_id")
            ]
            claim_ids = [
                str(result["claim_id"]) for result in results if result.get("claim_id")
            ]
            selected_override = str(selected_overrides.get(role) or "").strip()
            selected_id = selected_override or (
                candidate_ids[0] if candidate_ids else "none"
            )
            if (
                recorded.get("candidate_ids") != candidate_ids
                or recorded.get("claim_ids") != claim_ids
                or str(recorded.get("selected_id")) != selected_id
            ):
                return None
            role_rejections = rejected_overrides.get(role, {})
            if not isinstance(role_rejections, dict):
                return None
            selected_candidate = next(
                (
                    result
                    for result in results
                    if str(result.get("proof_id", "")) == selected_id
                ),
                None,
            )
            verified[role] = {
                "candidate_ids": candidate_ids,
                "claim_ids": claim_ids,
                "selected_id": selected_id,
                "selected_candidate": (
                    _experience_candidate_binding(selected_candidate)
                    if role == "experience_story" and selected_candidate is not None
                    else None
                ),
                "rejected_overrides": {
                    str(candidate): str(reason)
                    for candidate, reason in role_rejections.items()
                },
            }
        for name, path in artifact_paths.items():
            if _file_sha256(path) != str(artifacts[name]["sha256"]):
                return None
        return verified
    except (
        CustomerProofDataError,
        json.JSONDecodeError,
        KeyError,
        OSError,
        TypeError,
        UnicodeError,
        ValueError,
    ):
        return None


def _verify_nonvault_selector_evidence(
    evidence: Dict[str, Any],
) -> Optional[Dict[str, Dict[str, Any]]]:
    try:
        inputs = evidence["inputs"]
        artifacts = evidence["artifacts"]
        recorded_roles = evidence["roles"]
        if not isinstance(inputs, dict) or not isinstance(artifacts, dict):
            return None
        if set(artifacts) != {"index", "ledger"}:
            return None
        artifact_paths: Dict[str, Path] = {}
        for name in ("index", "ledger"):
            record = artifacts[name]
            if not isinstance(record, dict):
                return None
            path = Path(str(record["path"])).expanduser()
            digest = str(record["sha256"])
            if (
                not path.is_absolute()
                or not re.fullmatch(r"[0-9a-f]{64}", digest)
                or not path.is_file()
                or _file_sha256(path) != digest
            ):
                return None
            artifact_paths[name] = path.resolve()

        string_inputs = (
            "brand",
            "topic",
            "title",
            "objective",
            "article_slug",
            "reference_date",
        )
        if any(not isinstance(inputs.get(name), str) for name in string_inputs):
            return None
        roles = inputs.get("roles")
        if (
            not isinstance(roles, list)
            or set(roles) != {"metric", "quote", "theme", "experience_story"}
            or len(roles) != 4
            or inputs.get("require_eeat_story") is not True
        ):
            return None
        limit = inputs.get("limit")
        if (
            isinstance(limit, bool)
            or not isinstance(limit, int)
            or not 0 <= limit <= 100
        ):
            return None
        reference_date = date.fromisoformat(str(inputs["reference_date"]))
        selected_overrides = inputs.get("selected_overrides", {})
        rejected_overrides = inputs.get("rejected_overrides", {})
        if not isinstance(selected_overrides, dict) or not isinstance(
            rejected_overrides, dict
        ):
            return None
        if not isinstance(recorded_roles, list) or len(recorded_roles) != len(roles):
            return None

        verified: Dict[str, Dict[str, Any]] = {}
        for role, recorded in zip(roles, recorded_roles):
            if not isinstance(recorded, dict) or recorded.get("role") != role:
                return None
            results = select_nonvault_customer_proofs(
                str(inputs["topic"]),
                brand=str(inputs["brand"]),
                index_path=artifact_paths["index"],
                ledger_path=artifact_paths["ledger"],
                title=str(inputs["title"]),
                objective=str(inputs["objective"]),
                article_slug=str(inputs["article_slug"]),
                proof_role=role,
                require_eeat_story=role == "experience_story",
                limit=limit,
                reference_date=reference_date,
            )
            candidate_ids = [
                str(result["proof_id"]) for result in results if result.get("proof_id")
            ]
            selected_id = str(selected_overrides.get(role) or "none")
            selected_candidate = next(
                (
                    result
                    for result in results
                    if str(result.get("proof_id", "")) == selected_id
                ),
                None,
            )
            role_rejections = rejected_overrides.get(role, {})
            if not isinstance(role_rejections, dict):
                return None
            expected_binding = (
                _nonvault_experience_candidate_binding(selected_candidate)
                if role == "experience_story" and selected_candidate is not None
                else None
            )
            if (
                recorded.get("candidate_ids") != candidate_ids
                or str(recorded.get("selected_id")) != selected_id
                or recorded.get("selected_candidate") != expected_binding
                or recorded.get("rejected_overrides") != role_rejections
            ):
                return None
            verified[role] = {
                "candidate_ids": candidate_ids,
                "claim_ids": [],
                "selected_id": selected_id,
                "selected_candidate": expected_binding,
                "rejected_overrides": {
                    str(candidate): str(reason)
                    for candidate, reason in role_rejections.items()
                },
            }
        for name, path in artifact_paths.items():
            if _file_sha256(path) != str(artifacts[name]["sha256"]):
                return None
        return verified
    except (
        NonVaultProofDataError,
        KeyError,
        OSError,
        TypeError,
        ValueError,
    ):
        return None


def _nonvault_experience_candidate_binding(
    candidate: Dict[str, Any],
) -> Dict[str, str]:
    story = candidate.get("review_story")
    if not isinstance(story, dict):
        story = {}
    return {
        "proof_id": str(candidate.get("proof_id", "")).strip(),
        "identity": str(
            story.get("identity_display")
            or story.get("business_name")
            or story.get("person_name")
            or candidate.get("customer")
            or ""
        ).strip(),
        "public_url": str(
            story.get("public_url") or candidate.get("public_url") or ""
        ).strip(),
        "story": str(
            story.get("workflow_story") or candidate.get("evidence") or ""
        ).strip(),
    }


def _experience_candidate_binding(candidate: Dict[str, Any]) -> Dict[str, str]:
    story = candidate.get("review_story")
    if not isinstance(story, dict):
        story = {}
    identity = (
        str(story.get("identity_display", "")).strip()
        or str(story.get("person_name", "")).strip()
        or str(story.get("business_name", "")).strip()
        or str(candidate.get("customer", "")).strip()
    )
    public_url = str(
        story.get("public_url") or candidate.get("public_url") or ""
    ).strip()
    story_text = str(
        story.get("workflow_story")
        or candidate.get("evidence")
        or " ".join(str(value) for value in candidate.get("themes", []) or [])
    ).strip()
    return {
        "proof_id": str(candidate.get("proof_id", "")).strip(),
        "claim_id": str(candidate.get("claim_id", "")).strip(),
        "identity": identity,
        "public_url": public_url,
        "story": story_text,
    }
