"""Focused aeo no fit scoring."""

from __future__ import annotations

from .aeo_customer_evidence import _verified_selector_roles
from .aeo_text import _normalize_text
from .aeo_text import _word_count
from pathlib import Path
from typing import Dict
from typing import FrozenSet
from typing import List
from typing import Optional
from typing import Tuple
import json
import re

def _has_documented_no_fit_experience_boundary(
    proof_sidecar_content: Optional[str],
    *,
    proof_sidecar_path: Optional[str] = None,
) -> bool:
    if not proof_sidecar_content:
        return False
    verified_roles = _verified_selector_roles(
        proof_sidecar_content,
        proof_sidecar_path,
    )
    if not verified_roles or "experience_story" not in verified_roles:
        return False
    verified_story = verified_roles["experience_story"]
    if str(verified_story.get("selected_id", "")).casefold() != "none":
        return False
    expected_candidates = [
        str(candidate).casefold()
        for candidate in verified_story.get("candidate_ids", [])
    ]
    expected_rejections = {
        str(candidate).casefold(): str(reason)
        for candidate, reason in verified_story.get("rejected_overrides", {}).items()
    }
    has_substantive_decision = _has_substantive_no_fit_decision(
        _section_lines(proof_sidecar_content, "E-E-A-T Proof Map")
    )
    has_verified_rejections = _has_verified_slate_rejections(
        _section_lines(proof_sidecar_content, "Customer Proof Slate"),
        expected_candidates,
        expected_rejections,
    )
    if not expected_candidates and not expected_rejections:
        no_fit_reason = str(verified_story.get("no_fit_reason", ""))
        normalized_no_fit = _normalize_text(no_fit_reason)
        has_verified_rejections = has_verified_rejections or (
            _word_count(no_fit_reason) >= 8
            and "no customer proof selected" in normalized_no_fit
            and "public copy must omit" in normalized_no_fit
        )

    return has_substantive_decision and has_verified_rejections


def _section_lines(content: str, title: str) -> List[str]:
    title_pattern = re.compile(
        rf"^(?:#{{1,6}}\s+)?{re.escape(title)}:?\s*$",
        re.IGNORECASE,
    )
    lines: List[str] = []
    active = False
    for line in content.splitlines():
        stripped = line.strip()
        if title_pattern.match(stripped):
            active = True
            continue
        if active and (
            stripped.startswith(chr(96) * 3)
            or re.match(r"^#{1,6}\s+", stripped)
        ):
            break
        if active:
            lines.append(stripped)
    return lines


def _has_substantive_no_fit_decision(lines: List[str]) -> bool:
    pattern = re.compile(
        r"^[-*+]\s*First-hand evidence decision:\s*"
        r"Selected:\s*\[none\]\s*(.*)$",
        re.IGNORECASE,
    )
    signals = (
        "because", "does not", "did not", "cannot", "no approved",
        "no relevant", "not relevant", "objective", "article", "section",
        "omitted", "excluded", "substantiat", "rather than",
    )
    for line in lines:
        match = pattern.match(line)
        if match:
            reason = match.group(1).lstrip(" .:|-\t")
            return _word_count(reason) >= 8 and any(
                signal in _normalize_text(reason) for signal in signals
            )
    return False


def _has_verified_slate_rejections(
    lines: List[str],
    expected_candidates: List[str],
    expected_rejections: Dict[str, str],
) -> bool:
    for line in lines:
        parsed = _parse_experience_slate(line)
        if parsed is None or parsed[0] != expected_candidates:
            continue
        rejections = parsed[1]
        empty_slate = not expected_candidates and not expected_rejections
        if rejections != expected_rejections and not (
            empty_slate and set(rejections) == {"none"}
        ):
            continue
        return _rejections_are_substantive(rejections, expected_candidates)
    return False


def _parse_experience_slate(
    line: str,
) -> Optional[Tuple[List[str], Dict[str, str]]]:
    if not re.match(r"^[-*+]\s*Role:\s*experience_story\b", line, re.IGNORECASE):
        return None
    if not re.search(r"\|\s*Selected:\s*\[none\]", line, re.IGNORECASE):
        return None
    candidates_match = re.search(
        r"\|\s*Top candidates:\s*\[([^\]]*)\]", line, re.IGNORECASE
    )
    rejected_match = re.search(
        r"\|\s*Rejected stronger candidates:\s*\[([^\]]*)\]", line, re.IGNORECASE
    )
    if not candidates_match or not rejected_match:
        return None
    raw_candidates = [
        value.strip().strip("\"'").casefold()
        for value in candidates_match.group(1).split(",")
        if value.strip()
    ]
    candidates = [] if raw_candidates == ["none"] else raw_candidates
    rejections = _parse_rejections(rejected_match.group(1))
    return None if rejections is None else (candidates, rejections)


def _parse_rejections(value: str) -> Optional[Dict[str, str]]:
    parsed: Dict[str, str] = {}
    for raw_rejection in value.split(","):
        candidate, separator, reason = raw_rejection.partition(":")
        key = candidate.strip().strip("\"'").casefold()
        reason = reason.strip()
        if not separator or not key or not reason:
            return None
        parsed[key] = reason
    return parsed


def _rejections_are_substantive(
    rejections: Dict[str, str],
    expected_candidates: List[str],
) -> bool:
    if expected_candidates:
        return set(rejections) == set(expected_candidates) and all(
            _has_section_specific_story_rejection_reason(reason)
            for reason in rejections.values()
        )
    empty_reason = rejections.get("none", "")
    return (
        set(rejections) == {"none"}
        and "no eligible candidate exists" in _normalize_text(empty_reason)
        and _has_section_specific_story_rejection_reason(empty_reason)
    )

def _customer_proof_ids() -> FrozenSet[str]:
    """Load approved, public, story-eligible proof IDs; fail closed on error."""
    index_path = (
        Path(__file__).resolve().parents[2] / "context" / "customer-proof-index.json"
    )
    try:
        payload = json.loads(index_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return frozenset()

    proof_rows = payload.get("proof")
    if not isinstance(proof_rows, list):
        return frozenset()
    eligible_ids = set()
    for row in proof_rows:
        if not isinstance(row, dict):
            continue
        review_story = row.get("review_story")
        if not isinstance(review_story, dict):
            continue
        proof_id = str(row.get("proof_id", "")).strip().lower()
        if (
            proof_id
            and str(row.get("approval_status", "")).strip().lower() == "approved"
            and row.get("public_copy_allowed") is True
            and review_story.get("story_allowed") is True
        ):
            eligible_ids.add(proof_id)
    return frozenset(eligible_ids)

def _has_section_specific_story_rejection_reason(reason: str) -> bool:
    normalized = re.sub(r"\s+", " ", reason.strip().lower())
    if not normalized or normalized in {"none", "n/a", "na"}:
        return False
    reason_signals = (
        "because",
        "section",
        "article",
        "objective",
        "omitted",
        "not used",
        "instead",
        "while",
    )
    return len(normalized.split()) >= 8 and any(
        signal in normalized for signal in reason_signals
    )


__all__ = [
    "_has_documented_no_fit_experience_boundary",
    "_customer_proof_ids",
    "_has_section_specific_story_rejection_reason",
]
