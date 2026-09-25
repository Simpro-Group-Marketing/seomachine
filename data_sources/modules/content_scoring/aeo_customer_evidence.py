"""Focused aeo customer evidence scoring."""

from __future__ import annotations

from .aeo_text import _normalize_key
from .aeo_text import _normalize_text
from .aeo_text import _normalize_url
from .aeo_text import _paragraph_has_url_and_identity
from .aeo_text import _plain_text
from .aeo_text import _story_tokens
from collections.abc import Mapping
from data_sources.modules.customer_proof.evidence import verify_selector_evidence_roles
from typing import Any
from typing import Dict
from typing import Optional
import re

def _has_sidecar_experience_proof(proof_sidecar_content: Optional[str]) -> bool:
    if not proof_sidecar_content:
        return False

    in_block = False
    for line in proof_sidecar_content.splitlines():
        stripped = line.strip()
        if re.match(r"^(?:#{1,6}\s+)?E-E-A-T Proof Map:?\s*$", stripped, re.IGNORECASE):
            in_block = True
            continue
        if not in_block:
            continue
        if stripped.startswith("```"):
            continue
        if re.match(
            r"^(?:#{1,6}\s+)?(?:PAA/FAQ Provenance|Metric Proof Pack|Source Map|"
            r"Customer Proof Pack|FAQ Proof Map|Structured data plan|Review Story Selection|"
            r"Review Site Theme Selection|Fred Voccola Authority Selection)\s*$",
            stripped,
            re.IGNORECASE,
        ):
            break

        match = re.match(r"^[-*+]\s*Experience proof:\s*(.+)$", stripped, re.IGNORECASE)
        if (
            match
            and re.search(r"https?://", match.group(1))
            and _has_approved_experience_proof_status(match.group(1))
        ):
            proof_description = match.group(1)
            if _is_explicit_first_hand_evidence(proof_description):
                return True

    return False

def _is_explicit_first_hand_evidence(proof_description: str) -> bool:
    proof_type_match = re.search(
        r"(?:^|\|)\s*Proof type:\s*([^|]+)",
        proof_description,
        re.IGNORECASE,
    )
    evidence_match = re.search(
        r"(?:^|\|)\s*Evidence:\s*([^|]+)",
        proof_description,
        re.IGNORECASE,
    )
    if proof_type_match and evidence_match and evidence_match.group(1).strip():
        proof_type = _normalize_text(proof_type_match.group(1))
        return proof_type in {
            "first hand experience",
            "first hand evidence",
            "identity backed experience",
            "identity backed story",
            "identity backed account",
            "identity backed review",
            "identity backed evidence",
            "first party workflow experience",
            "first party workflow evidence",
        }

    return (
        re.search(
            r"\bThe rewrite uses first[- ]party ClockShark workflow evidence from\s+"
            r"https?://(?:www\.)?clockshark\.com/(?:blog|tour|industries)/",
            proof_description,
            re.IGNORECASE,
        )
        is not None
    )

def _has_approved_experience_proof_status(proof_description: str) -> bool:
    status_match = re.search(
        r"(?:^|\|)\s*Status:\s*([^|]+)",
        proof_description,
        re.IGNORECASE,
    )
    if not status_match:
        return False

    status = _normalize_text(status_match.group(1))
    return status in {
        "approved",
        "approved for public use",
        "verified",
        "verified for public use",
    }

def _verified_selector_roles(
    proof_sidecar_content: str,
    proof_sidecar_path: Optional[str],
) -> Optional[Dict[str, Dict[str, Any]]]:
    return verify_selector_evidence_roles(
        proof_sidecar_content,
        proof_sidecar_path,
    )

def _validated_customer_experience_binding(
    content: str,
    proof_sidecar_content: Optional[str],
    proof_sidecar_path: Optional[str],
) -> Optional[Dict[str, str]]:
    if not proof_sidecar_content or not proof_sidecar_path:
        return None
    verified_roles = _verified_selector_roles(
        proof_sidecar_content,
        proof_sidecar_path,
    )
    if not verified_roles:
        return None
    selected = _selected_experience_fields(verified_roles)
    if selected is None:
        return None
    mining = _extract_selected_customer_proof_mining(proof_sidecar_content)
    if mining is None or not _mining_matches_selection(mining, selected):
        return None
    if not _visible_story_mapping(
        content,
        selected["public_url"],
        selected["identity"],
        selected["story"],
    ):
        return None
    return {
        key: selected[key]
        for key in ("proof_id", "claim_id", "identity", "public_url")
        if selected.get(key)
    }


def _selected_experience_fields(
    verified_roles: Mapping[str, object],
) -> Optional[Dict[str, str]]:
    experience_role = verified_roles.get("experience_story")
    if not isinstance(experience_role, Mapping):
        return None
    selected = experience_role.get("selected_candidate")
    if not isinstance(selected, Mapping):
        return None
    fields = {
        key: str(selected.get(key, "")).strip()
        for key in ("proof_id", "claim_id", "identity", "public_url", "story")
    }
    required_fields = ("proof_id", "identity", "public_url", "story")
    return fields if all(fields[key] for key in required_fields) else None


def _mining_matches_selection(
    mining: Mapping[str, str],
    selected: Mapping[str, str],
) -> bool:
    proof = _parse_mined_proof(str(mining.get("proof", "")))
    usable_story = str(mining.get("usable_pov/story_found", "")).strip()
    final_use = str(mining.get("final_use_in_copy", "")).strip()
    return (
        str(proof.get("proof_id", "")).strip() == selected["proof_id"]
        and _normalize_url(str(proof.get("url", "")))
        == _normalize_url(selected["public_url"])
        and str(mining.get("status", "")).strip().casefold() == "approved"
        and _is_substantive_experience_text(usable_story)
        and _is_substantive_experience_text(final_use)
        and bool(re.search(r"\b(?:experience|pov|story)\b", final_use, re.IGNORECASE))
    )

def _extract_selected_customer_proof_mining(
    proof_sidecar_content: str,
) -> Optional[Dict[str, str]]:
    in_block = False
    fields: Dict[str, str] = {}
    for line in proof_sidecar_content.splitlines():
        stripped = line.strip()
        if re.match(
            r"^(?:#{1,6}\s+)?Selected Customer Proof Mining:?\s*$",
            stripped,
            re.IGNORECASE,
        ):
            in_block = True
            continue
        if not in_block:
            continue
        if stripped.startswith("```") or re.match(r"^#{1,6}\s+", stripped):
            break
        match = re.match(r"^[-*+]\s*([^:]+):\s*(.+?)\s*$", stripped)
        if match:
            fields[_normalize_key(match.group(1))] = match.group(2).strip()
    return fields or None

def _parse_mined_proof(value: str) -> Dict[str, str]:
    parts = [part.strip() for part in value.split("|")]
    parsed = {"proof_id": parts[0] if parts else ""}
    for part in parts[1:]:
        if ":" not in part:
            continue
        key, item_value = part.split(":", 1)
        parsed[_normalize_key(key)] = item_value.strip()
    return parsed

def _is_substantive_experience_text(value: str) -> bool:
    normalized = _normalize_text(value)
    if not normalized or normalized in {
        "none",
        "none found",
        "not used",
        "not applicable",
        "n a",
    }:
        return False
    return len(re.findall(r"[a-z0-9]+", normalized)) >= 4

def _visible_story_mapping(
    content: str,
    public_url: str,
    identity: str,
    story: str,
) -> bool:
    normalized_url = _normalize_url(public_url)
    normalized_identity = _normalize_text(identity)
    story_tokens = _story_tokens(story)
    if not normalized_url or not normalized_identity or len(story_tokens) < 2:
        return False
    for paragraph in re.split(r"\n\s*\n", content):
        if normalized_url not in _normalize_url(paragraph):
            continue
        if normalized_identity not in _normalize_text(paragraph):
            continue
        if len(story_tokens.intersection(_story_tokens(paragraph))) >= 2:
            return True
    return False

def _has_review_site_theme(body: str) -> bool:
    text = _plain_text(body).lower()
    review_surfaces = (
        "g2",
        "capterra",
        "software advice",
        "getapp",
        "trustradius",
        "gartner",
        "trustpilot",
        "app store",
        "google reviews",
    )
    review_terms = (
        "review",
        "reviews",
        "review-site",
        "review site",
        "customer feedback",
        "customer themes",
        "voc",
    )
    return any(surface in text for surface in review_surfaces) and any(
        term in text for term in review_terms
    )

def _has_valid_review_story_selection(
    content: str, proof_sidecar_content: Optional[str]
) -> bool:
    if not proof_sidecar_content:
        return False
    selected = _extract_review_story_selected_line(proof_sidecar_content)
    if not selected:
        return False
    identity = selected.get("identity", "")
    url = selected.get("url", "")
    status = selected.get("status", "").lower()
    use = selected.get("use", "").lower()
    if not identity or not url.startswith(("http://", "https://")):
        return False
    if status != "approved":
        return False
    if "e-e-a-t experience story" not in use:
        return False
    return _paragraph_has_url_and_identity(content, url, identity)

def _extract_review_story_selected_line(content: str) -> Dict[str, str]:
    in_block = False
    for line in content.splitlines():
        stripped = line.strip()
        if re.match(
            r"^(?:#{1,6}\s+)?Review Story Selection:?\s*$", stripped, re.IGNORECASE
        ):
            in_block = True
            continue
        if not in_block:
            continue
        if stripped.startswith("```"):
            break
        if re.match(
            r"^(?:#{1,6}\s+)?(?:PAA/FAQ Provenance|Metric Proof Pack|Source Map|"
            r"Customer Proof Pack|E-E-A-T Proof Map|FAQ Proof Map|Structured data plan|Fred Voccola Authority Selection)\s*$",
            stripped,
            re.IGNORECASE,
        ):
            break
        match = re.match(
            r"^\s*[-*+]\s*Selected story:\s*(.+?)\s*$", line, re.IGNORECASE
        )
        if not match:
            continue
        parts = [part.strip() for part in match.group(1).split("|")]
        selected = {"proof_id": parts[0] if parts else ""}
        for part in parts[1:]:
            if ":" not in part:
                continue
            key, value = part.split(":", 1)
            selected[_normalize_key(key).replace(" ", "_")] = value.strip()
        return selected
    return {}


__all__ = [
    "_has_sidecar_experience_proof",
    "_is_explicit_first_hand_evidence",
    "_has_approved_experience_proof_status",
    "_verified_selector_roles",
    "_validated_customer_experience_binding",
    "_extract_selected_customer_proof_mining",
    "_parse_mined_proof",
    "_is_substantive_experience_text",
    "_visible_story_mapping",
    "_has_review_site_theme",
    "_has_valid_review_story_selection",
    "_extract_review_story_selected_line",
]
