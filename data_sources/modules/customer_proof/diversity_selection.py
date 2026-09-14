"""Validate customer-proof pack selection decisions."""

from __future__ import annotations

from typing import Dict, List, Optional, Sequence

from ..guard_common import Finding
from .diversity_common import _finding, _first_quote_line, _has_customer_quote_claim, _normalize_space
from .diversity_contracts import BLOCKED_OR_EMPTY_RE, NON_CASE_STUDY_KEYS


def _missing_pack_findings(
    content: str,
    article_case_study_urls: Sequence[str],
) -> List[Finding]:
    if not article_case_study_urls and not _has_customer_quote_claim(content):
        return []
    return [
        _finding(
            "customer_proof_pack_missing",
            1,
            "Customer proof appears in public copy, but no Customer Proof Pack was found.",
            (
                "Add a Customer Proof Pack to the validation sidecar with proof candidates, "
                "non-case-study search evidence, selected proof, and claims excluded."
            ),
        )
    ]


def _pack_selection_findings(
    content: str,
    pack: Dict[str, object],
    decision: Optional[Dict[str, object]],
    *,
    all_case_study_urls: Sequence[str],
    all_customer_proof_urls: Sequence[str],
) -> List[Finding]:
    findings: List[Finding] = []
    if all_customer_proof_urls and decision is None:
        findings.append(
            _finding(
                "customer_proof_selection_decision_missing",
                pack["line"],
                "Customer proof appears, but no Customer Proof Selection Decision block was found.",
                (
                    "Add Customer Proof Selection Decision to the validation sidecar with selector command, "
                    "selected proof IDs, rejected stronger candidates, and final use in copy."
                ),
            )
        )

    if all_case_study_urls and not _has_non_case_study_attempt(pack):
        findings.append(
            _finding(
                "customer_proof_non_case_study_attempt_missing",
                pack["line"],
                "Customer Proof Pack uses case-study proof without a documented Quote Matrix, Reference, Customer Story, or review-site search attempt.",
                (
                    "Add Quote Matrix candidates, Reference candidates, Customer Stories candidates, "
                    "or review-site experience evidence with the search result, blocker, or approval status."
                ),
            )
        )

    if _has_customer_quote_claim(content) and not _has_approved_quote(pack):
        findings.append(
            _finding(
                "customer_quote_requires_approved_quote",
                _first_quote_line(content),
                "Exact quote or testimonial wording appears in public copy without an approved Customer Proof Pack quote row.",
                (
                    "Add an Approved quote row with customer or reviewer identity, source type, "
                    "URL or source ref, Evidence, Status: approved, and intended Use."
                ),
            )
        )
    return findings


def _has_non_case_study_attempt(pack: Dict[str, object]) -> bool:
    for field in pack.get("fields", []):
        key = str(field.get("key", ""))
        value = str(field.get("value", "")).strip()
        if key not in NON_CASE_STUDY_KEYS:
            continue
        if _is_documented_attempt(value):
            return True
    return False


def _is_documented_attempt(value: str) -> bool:
    normalized = _normalize_space(value)
    if not normalized or BLOCKED_OR_EMPTY_RE.match(normalized):
        return False
    if "none collected" in normalized or "not collected" in normalized:
        return False
    return True


def _has_reuse_reason(pack: Dict[str, object]) -> bool:
    for field in pack.get("fields", []):
        key = str(field.get("key", ""))
        value = str(field.get("value", "")).strip()
        if key == "reuse reason" and value:
            return True
    return False


def _has_approved_quote(pack: Dict[str, object]) -> bool:
    for field in pack.get("fields", []):
        key = str(field.get("key", ""))
        value = str(field.get("value", ""))
        if key == "approved quote" and "status: approved" in value.lower():
            return True
    return False


__all__ = [
    '_missing_pack_findings',
    '_pack_selection_findings',
    '_has_non_case_study_attempt',
    '_is_documented_attempt',
    '_has_reuse_reason',
    '_has_approved_quote'
]
