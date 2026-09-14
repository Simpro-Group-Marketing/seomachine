"""Validate customer-proof slate completeness and story decisions."""

from __future__ import annotations

import re
from typing import Dict, List, Optional, Sequence

from ..guard_common import Finding
from .diversity_common import _blank_fenced_code, _finding, _has_customer_quote_claim, _normalize_space
from .diversity_contracts import NONE_RESULT_RE, REQUIRED_SLATE_ROLES, REVIEW_PROOF_HEADING_RE
from .diversity_parsing import _first_field_value, _selected_proof_ids, _slate_selected_ids


def _slate_findings(
    content: str,
    proof_source: str,
    slate: Optional[Dict[str, object]],
    decision: Optional[Dict[str, object]],
    *,
    all_customer_proof_urls: Sequence[str],
) -> List[Finding]:
    if not all_customer_proof_urls and not _has_customer_quote_claim(content):
        return []
    if slate is None:
        return [
            _finding(
                "customer_proof_slate_missing",
                1,
                "Customer proof appears, but no Customer Proof Slate was found.",
                (
                    "Add Customer Proof Slate to the validation sidecar with selector-backed "
                    "metric, quote, and theme role rows before drafting."
                ),
            )
        ]

    findings: List[Finding] = []
    roles = slate.get("roles", {})
    if not isinstance(roles, dict):
        roles = {}

    if not _first_field_value(slate, "selector command"):
        findings.append(
            _finding(
                "customer_proof_slate_selector_command_missing",
                int(slate["line"]),
                "Customer Proof Slate is missing a selector command.",
                "Add the customer_proof_selector.py command used to build the proof slate.",
            )
        )

    for role in REQUIRED_SLATE_ROLES:
        if role not in roles:
            findings.append(
                _finding(
                    "customer_proof_slate_role_missing",
                    int(slate["line"]),
                    f"Customer Proof Slate is missing the required {role} role row.",
                    "Add Role rows for metric, quote, theme, and experience_story when review-derived copy appears.",
                    match=role,
                )
            )

    if "experience_story" not in roles:
        findings.append(
            _finding(
                "customer_proof_slate_experience_story_missing",
                int(slate["line"]),
                "Customer proof appears without an experience_story Customer Proof Slate role.",
                (
                    "Run or consult the selector with --require-eeat-story and add an "
                    "experience_story role row. Select a proof-backed story only when it "
                    "improves the article objective; otherwise use Selected: [none] with "
                    "section-specific rejection reasons."
                ),
            )
        )
    else:
        findings.extend(
            _experience_story_consideration_findings(roles["experience_story"])
        )

    selected_ids = _selected_proof_ids(decision)
    slate_selected_ids = _slate_selected_ids(roles)
    for proof_id in selected_ids:
        if proof_id not in slate_selected_ids:
            findings.append(
                _finding(
                    "customer_proof_selected_not_in_slate",
                    int(decision["line"]) if decision else int(slate["line"]),
                    "Customer Proof Selection Decision selected proof that is not selected in Customer Proof Slate.",
                    "Add the proof ID to the matching slate Role selected list or choose a selected slate candidate.",
                    match=proof_id,
                )
            )

    findings.extend(_stronger_slate_candidate_findings(slate))
    return findings


def _stronger_slate_candidate_findings(slate: Dict[str, object]) -> List[Finding]:
    roles = slate.get("roles", {})
    if not isinstance(roles, dict):
        return []
    findings: List[Finding] = []
    for role, details in roles.items():
        if not isinstance(details, dict):
            continue
        top_candidates = [
            str(candidate) for candidate in details.get("top_candidates", [])
        ]
        selected = {str(candidate) for candidate in details.get("selected", [])}
        rejected = details.get("rejected", {})
        rejected_ids = set(rejected.keys()) if isinstance(rejected, dict) else set()
        if not top_candidates or not selected:
            continue
        unverified_selected = sorted(selected.difference(top_candidates))
        for proof_id in unverified_selected:
            findings.append(
                _finding(
                    "customer_proof_slate_selected_not_in_top_candidates",
                    int(details.get("line", slate["line"])),
                    (
                        "Customer Proof Slate selected a proof that is not in the "
                        f"receipt-verified {role} candidate list: {proof_id}."
                    ),
                    (
                        "Choose a proof from Top candidates or rerun the receipt-backed "
                        "selector so the proof is verified before selection."
                    ),
                    match=proof_id,
                )
            )
        selected_indexes = [
            index
            for index, candidate in enumerate(top_candidates)
            if candidate in selected
        ]
        if not selected_indexes:
            continue
        first_selected_index = min(selected_indexes)
        for candidate in top_candidates[:first_selected_index]:
            if candidate in selected or candidate in rejected_ids:
                continue
            findings.append(
                _finding(
                    "customer_proof_stronger_slate_candidate_available",
                    int(details.get("line", slate["line"])),
                    (
                        "Customer Proof Slate selected a lower-ranked proof while a stronger "
                        f"{role} candidate is documented: {candidate}."
                    ),
                    (
                        "Use the stronger candidate or add it to Rejected stronger candidates "
                        "with a section-specific reason."
                    ),
                    severity="warning",
                    match=candidate,
                )
            )
    return findings


def _experience_story_consideration_findings(
    role_details: Dict[str, object],
) -> List[Finding]:
    selected = {str(candidate) for candidate in role_details.get("selected", [])}
    if selected:
        return []

    top_candidates = [
        str(candidate) for candidate in role_details.get("top_candidates", [])
    ]
    if not top_candidates:
        reason = _normalize_space(str(role_details.get("reason", "")))
        if (
            "no customer proof selected" in reason
            and "no approved claims" in reason
        ) or (
            "selector returned no" in reason
            and "experience_story" in reason
        ):
            return []
        return [
            _finding(
                "customer_proof_slate_experience_story_candidates_missing",
                int(role_details.get("line", 1)),
                "experience_story slate row has no story candidates.",
                (
                    "Run or consult the selector with --require-eeat-story and list the "
                    "strongest identity-backed story candidates, even when none are used."
                ),
            )
        ]

    rejected = role_details.get("rejected", {})
    if not isinstance(rejected, dict):
        rejected = {}

    for candidate, reason in rejected.items():
        if candidate in top_candidates and _has_section_specific_story_rejection_reason(
            str(reason)
        ):
            return []

    return [
        _finding(
            "customer_proof_slate_experience_story_rejection_missing",
            int(role_details.get("line", 1)),
            (
                "experience_story slate row selected no story but did not give a "
                "section-specific rejection reason for a ranked story candidate."
            ),
            (
                "Use the proof-backed story if it improves the article objective, or "
                "add at least one ranked candidate to Rejected stronger candidates with "
                "a concrete section-specific reason."
            ),
            match=top_candidates[0],
        )
    ]


def _has_section_specific_story_rejection_reason(reason: str) -> bool:
    normalized = _normalize_space(reason)
    if not normalized or NONE_RESULT_RE.match(normalized):
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


def _needs_experience_story_slate_role(content: str, proof_source: str) -> bool:
    if REVIEW_PROOF_HEADING_RE.search(proof_source):
        return True
    review_signal = re.search(
        r"(?:capterra\.com|g2\.com/products/simpro/reviews|review-derived|reviewer)",
        _blank_fenced_code(content),
        flags=re.IGNORECASE,
    )
    return bool(review_signal)


__all__ = [
    '_slate_findings',
    '_stronger_slate_candidate_findings',
    '_experience_story_consideration_findings',
    '_has_section_specific_story_rejection_reason',
    '_needs_experience_story_slate_role'
]
