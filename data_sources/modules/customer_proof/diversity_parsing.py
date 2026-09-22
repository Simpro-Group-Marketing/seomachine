"""Parse customer-proof sidecar decision blocks."""

from __future__ import annotations

import re
from typing import Dict, List, Optional

from .diversity_common import _normalize_key
from .diversity_contracts import (
    BULLET_FIELD_RE,
    CUSTOMER_PROOF_HEADING_RE,
    CUSTOMER_PROOF_SLATE_HEADING_RE,
    EMPTY_SELECTION_VALUES,
    NEXT_DECISION_HEADING_RE,
    NEXT_MINING_HEADING_RE,
    NEXT_PROOF_HEADING_RE,
    NEXT_SLATE_HEADING_RE,
    SELECTED_CUSTOMER_PROOF_MINING_HEADING_RE,
    SELECTION_DECISION_HEADING_RE,
)

# Slate writers disagree on the separator between rejected candidates: the
# nonconnector writer joins with "; " and the vault writer with ", ". Rejection
# reasons are prose and routinely contain both. Split only where a new
# "<proof-id>: " pair actually opens, anchored on the hyphenated proof-id slug,
# so punctuation inside a reason stays with that reason.
REJECTION_PAIR_SPLIT_RE = re.compile(
    r"(?:^|[,;])\s*(?=[a-z0-9]+(?:-[a-z0-9]+)+\s*:\s)"
)


def _extract_customer_proof_pack(content: str) -> Optional[Dict[str, object]]:
    return _extract_bullet_block(
        content, CUSTOMER_PROOF_HEADING_RE, NEXT_PROOF_HEADING_RE
    )


def _extract_selection_decision(content: str) -> Optional[Dict[str, object]]:
    return _extract_bullet_block(
        content, SELECTION_DECISION_HEADING_RE, NEXT_DECISION_HEADING_RE
    )


def _extract_customer_proof_slate(content: str) -> Optional[Dict[str, object]]:
    slate = _extract_bullet_block(
        content, CUSTOMER_PROOF_SLATE_HEADING_RE, NEXT_SLATE_HEADING_RE
    )
    if slate is None:
        return None
    slate["roles"] = _parse_slate_roles(slate)
    return slate


def _extract_selected_customer_proof_mining(
    content: str,
) -> Optional[Dict[str, object]]:
    return _extract_bullet_block(
        content,
        SELECTED_CUSTOMER_PROOF_MINING_HEADING_RE,
        NEXT_MINING_HEADING_RE,
    )


def _extract_bullet_block(
    content: str,
    heading_re: re.Pattern[str],
    next_heading_re: re.Pattern[str],
) -> Optional[Dict[str, object]]:
    lines = content.splitlines()
    for index, line in enumerate(lines):
        if not heading_re.match(line.strip()):
            continue
        pack_lines: List[str] = []
        fields: List[Dict[str, object]] = []
        for offset, block_line in enumerate(lines[index + 1 :], start=index + 2):
            stripped = block_line.strip()
            if stripped.startswith("```"):
                break
            if next_heading_re.match(stripped):
                break
            if (
                stripped
                and not stripped.startswith(("-", "*", "+"))
                and re.match(r"^\s*(?:#{1,6}\s+)?[A-Za-z].*$", stripped)
            ):
                break
            if not stripped:
                if pack_lines:
                    break
                continue
            pack_lines.append(block_line)
            match = BULLET_FIELD_RE.match(block_line)
            if match:
                fields.append(
                    {
                        "key": _normalize_key(match.group("key")),
                        "value": match.group("value").strip(),
                        "line": offset,
                    }
                )
        return {"line": index + 1, "lines": pack_lines, "fields": fields}
    return None


def _parse_slate_roles(slate: Dict[str, object]) -> Dict[str, Dict[str, object]]:
    roles: Dict[str, Dict[str, object]] = {}
    for field in slate.get("fields", []):
        if str(field.get("key", "")) != "role":
            continue
        value = str(field.get("value", ""))
        role, details = _parse_role_row(value)
        if role:
            details["line"] = field.get("line", slate.get("line", 1))
            roles[role] = details
    return roles


def _parse_role_row(value: str) -> tuple[str, Dict[str, object]]:
    segments = [segment.strip() for segment in value.split("|") if segment.strip()]
    if not segments:
        return "", {}
    role = _normalize_key(segments[0]).replace(" ", "_")
    details: Dict[str, object] = {
        "top_candidates": [],
        "selected": [],
        "rejected": {},
    }
    for segment in segments[1:]:
        if ":" not in segment:
            continue
        key, raw_value = segment.split(":", 1)
        normalized_key = _normalize_key(key)
        if normalized_key == "top candidates":
            details["top_candidates"] = _parse_proof_id_list(raw_value)
        elif normalized_key == "selected":
            details["selected"] = _parse_proof_id_list(raw_value)
        elif normalized_key == "rejected stronger candidates":
            details["rejected"] = _parse_rejected_candidates(raw_value)
        elif normalized_key == "reason":
            details["reason"] = raw_value.strip()
    return role, details


def _parse_proof_id_list(value: str) -> List[str]:
    cleaned = value.strip().strip("[]")
    proof_ids: List[str] = []
    for raw_item in cleaned.split(","):
        item = _clean_proof_id(raw_item)
        if (
            not item
            or item.lower() in EMPTY_SELECTION_VALUES
            or " or none" in item.lower()
        ):
            continue
        proof_ids.append(item)
    return proof_ids


def _parse_rejected_candidates(value: str) -> Dict[str, str]:
    cleaned = value.strip().strip("[]")
    rejected: Dict[str, str] = {}
    for raw_item in REJECTION_PAIR_SPLIT_RE.split(cleaned):
        item = raw_item.strip()
        if not item or item.lower() in EMPTY_SELECTION_VALUES:
            continue
        proof_id, _, reason = item.partition(":")
        clean_id = _clean_proof_id(proof_id)
        clean_reason = reason.strip()
        if clean_id and clean_reason:
            rejected[clean_id] = clean_reason
    return rejected


def _selected_proof_ids(decision: Optional[Dict[str, object]]) -> List[str]:
    if decision is None:
        return []
    proof_ids: List[str] = []
    for field in decision.get("fields", []):
        if str(field.get("key", "")) != "selected proof":
            continue
        value = str(field.get("value", ""))
        proof_id = _clean_proof_id(value.split("|", 1)[0])
        if proof_id and proof_id.lower() not in EMPTY_SELECTION_VALUES:
            proof_ids.append(proof_id)
    return proof_ids


def _slate_selected_ids(roles: Dict[str, object]) -> set[str]:
    selected: set[str] = set()
    for role_details in roles.values():
        if not isinstance(role_details, dict):
            continue
        selected.update(str(proof_id) for proof_id in role_details.get("selected", []))
    return selected


def _clean_proof_id(value: str) -> str:
    return value.strip().strip("[]").strip("`").strip()


def _first_field_value(block: Optional[Dict[str, object]], key: str) -> str:
    if block is None:
        return ""
    normalized_key = _normalize_key(key)
    for field in block.get("fields", []):
        if str(field.get("key", "")) == normalized_key:
            return str(field.get("value", "")).strip()
    return ""


__all__ = [
    '_extract_customer_proof_pack',
    '_extract_selection_decision',
    '_extract_customer_proof_slate',
    '_extract_selected_customer_proof_mining',
    '_extract_bullet_block',
    '_parse_slate_roles',
    '_parse_role_row',
    '_parse_proof_id_list',
    '_parse_rejected_candidates',
    '_selected_proof_ids',
    '_slate_selected_ids',
    '_clean_proof_id',
    '_first_field_value'
]
