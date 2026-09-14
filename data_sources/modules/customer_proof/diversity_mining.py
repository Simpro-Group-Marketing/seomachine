"""Validate selector evidence and selected proof mining."""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional, Sequence

from ..guard_common import Finding
from .diversity_common import _finding, _has_customer_quote_claim, _normalize_key, _normalize_space
from .diversity_contracts import EMPTY_SELECTION_VALUES, NONE_RESULT_RE
from .diversity_parsing import _first_field_value
from .evidence import verify_selector_evidence_roles


def _selector_evidence_findings(
    slate: Dict[str, object],
    proof_sidecar_content: str,
    proof_sidecar_path: str | Path,
) -> List[Finding]:
    verified = verify_selector_evidence_roles(
        proof_sidecar_content,
        str(proof_sidecar_path),
    )
    if not verified:
        return [
            _finding(
                "customer_proof_selector_evidence_unverified",
                int(slate["line"]),
                "Customer Proof Slate is not bound to current, hash-verified selector evidence.",
                (
                    "Rerun customer_proof_selector.py with --evidence-output and keep the "
                    "generated Selector evidence path and SHA-256 line in the validation sidecar."
                ),
            )
        ]

    roles = slate.get("roles", {})
    if not isinstance(roles, dict):
        roles = {}
    findings: List[Finding] = []
    if set(roles) != set(verified):
        findings.append(
            _finding(
                "customer_proof_selector_evidence_slate_mismatch",
                int(slate["line"]),
                "Customer Proof Slate roles do not match the verified selector evidence roles.",
                "Use the complete generated slate from the hash-bound selector run.",
            )
        )

    for role in sorted(set(roles).intersection(verified)):
        details = roles[role]
        expected = verified[role]
        if not isinstance(details, dict):
            continue
        expected_selected_id = str(expected.get("selected_id", "")).strip()
        expected_selected = (
            []
            if expected_selected_id.casefold() in EMPTY_SELECTION_VALUES
            else [expected_selected_id]
        )
        actual_candidates = [str(value) for value in details.get("top_candidates", [])]
        actual_selected = [str(value) for value in details.get("selected", [])]
        actual_rejected = {
            str(candidate): str(reason)
            for candidate, reason in dict(details.get("rejected", {})).items()
        }
        expected_candidates = [
            str(value) for value in expected.get("candidate_ids", [])
        ]
        expected_rejected = {
            str(candidate): str(reason)
            for candidate, reason in dict(
                expected.get("rejected_overrides", {})
            ).items()
        }
        if (
            actual_candidates != expected_candidates
            or actual_selected != expected_selected
            or actual_rejected != expected_rejected
        ):
            findings.append(
                _finding(
                    "customer_proof_selector_evidence_slate_mismatch",
                    int(details.get("line", slate["line"])),
                    f"Customer Proof Slate {role} row differs from verified selector evidence.",
                    "Use the generated candidates, selection, and rejection reasons without alteration.",
                    match=role,
                )
            )
    return findings


def _proof_mining_findings(
    content: str,
    pack: Dict[str, object],
    mining: Optional[Dict[str, object]],
    *,
    all_customer_proof_urls: Sequence[str],
) -> List[Finding]:
    if not all_customer_proof_urls and not _has_customer_quote_claim(content):
        return []
    if mining is None:
        return [
            _finding(
                "selected_customer_proof_mining_missing",
                int(pack["line"]),
                "Customer proof appears, but no Selected Customer Proof Mining block was found.",
                (
                    "Read the selected public proof URL before drafting and add Selected Customer "
                    "Proof Mining with quote, metric, POV/story, workflow-theme, recommended-use, "
                    "final-use, exclusion, and approved status details."
                ),
            )
        ]

    findings: List[Finding] = []
    for required_key in (
        "checked for",
        "recommended use",
        "final use in copy",
        "status",
    ):
        if not _first_field_value(mining, required_key):
            findings.append(
                _finding(
                    "selected_customer_proof_mining_required_field_missing",
                    int(mining["line"]),
                    f"Selected Customer Proof Mining is missing required field: {required_key}.",
                    "Add Checked for, Recommended use, Final use in copy, and Status: approved.",
                    match=required_key,
                )
            )

    status = _first_field_value(mining, "status")
    if status and "approved" not in status.lower():
        findings.append(
            _finding(
                "selected_customer_proof_mining_status_not_approved",
                int(mining["line"]),
                "Selected Customer Proof Mining status is not approved.",
                "Set Status: approved only after the selected source was mined for quotes, metrics, POV/story, and themes.",
                match=status,
            )
        )

    if _pack_declares_none_used(pack, "approved quotes") and not _first_field_value(
        mining, "usable quotes found"
    ):
        findings.append(
            _finding(
                "selected_customer_proof_mining_quote_result_missing",
                int(mining["line"]),
                "Customer Proof Pack says approved quotes are none used, but mining does not document usable quote results.",
                "Add Usable quotes found with approved rows, none found, or a rejected quote reason.",
            )
        )

    if _pack_declares_none_used(pack, "approved metrics") and not _first_field_value(
        mining, "usable metrics found"
    ):
        findings.append(
            _finding(
                "selected_customer_proof_mining_metric_result_missing",
                int(mining["line"]),
                "Customer Proof Pack says approved metrics are none used, but mining does not document usable metric results.",
                "Add Usable metrics found with approved rows, none found, or a rejected metric reason.",
            )
        )

    findings.extend(_omitted_usable_mined_proof_findings(mining))
    return findings


def _pack_declares_none_used(pack: Dict[str, object], key: str) -> bool:
    normalized_key = _normalize_key(key)
    for field in pack.get("fields", []):
        if str(field.get("key", "")) != normalized_key:
            continue
        value = _normalize_space(str(field.get("value", "")))
        if not value:
            return False
        return "none" in value and "used" in value or bool(NONE_RESULT_RE.match(value))
    return False


def _omitted_usable_mined_proof_findings(mining: Dict[str, object]) -> List[Finding]:
    findings: List[Finding] = []
    final_use = _first_field_value(mining, "final use in copy")
    excluded_proof = _first_field_value(mining, "excluded proof")
    checks = [
        (
            "quote",
            _first_field_value(mining, "usable quotes found"),
            ("quote", "exact quote", "testimonial"),
        ),
        (
            "POV/story",
            _first_field_value(mining, "usable pov/story found"),
            ("pov", "story", "experience"),
        ),
    ]
    for proof_type, value, final_use_terms in checks:
        if not _mining_value_indicates_usable_proof(value):
            continue
        if any(term in final_use.lower() for term in final_use_terms):
            continue
        if _has_specific_excluded_proof_reason(excluded_proof, proof_type):
            continue
        findings.append(
            _finding(
                "selected_customer_proof_mining_usable_proof_omitted",
                int(mining["line"]),
                f"Selected Customer Proof Mining found usable {proof_type} evidence, but final copy omits it without a section-specific reason.",
                (
                    "Use the mined proof if it improves the article objective, or document why it was excluded "
                    "for this section."
                ),
                severity="warning",
                match=proof_type,
            )
        )
    return findings


def _mining_value_indicates_usable_proof(value: str) -> bool:
    normalized = _normalize_space(value)
    if not normalized or NONE_RESULT_RE.match(normalized):
        return False
    if (
        "none found" in normalized
        or "no usable" in normalized
        or "not found" in normalized
    ):
        return False
    return True


def _has_specific_excluded_proof_reason(value: str, proof_type: str) -> bool:
    normalized = _normalize_space(value)
    if not normalized or NONE_RESULT_RE.match(normalized):
        return False
    if (
        proof_type.lower().split("/", 1)[0] not in normalized
        and "proof" not in normalized
    ):
        return False
    reason_signals = (
        "because",
        "current",
        "section",
        "omitted",
        "excluded",
        "does not",
        "not relevant",
    )
    return len(normalized.split()) >= 8 and any(
        signal in normalized for signal in reason_signals
    )


__all__ = [
    '_selector_evidence_findings',
    '_proof_mining_findings',
    '_pack_declares_none_used',
    '_omitted_usable_mined_proof_findings',
    '_mining_value_indicates_usable_proof',
    '_has_specific_excluded_proof_reason'
]
