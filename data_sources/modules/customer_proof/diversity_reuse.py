"""Enforce customer-proof diversity and reuse policy."""

from __future__ import annotations

import re
import shlex
from datetime import date
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence

from .. import customer_proof_snapshot
from ..guard_common import Finding
from ..proof_usage import count_customer_proof_usage
from .contracts import CustomerProofDataError
from .diversity_common import _finding, _normalize_text, _proof_id_from_url
from .diversity_parsing import _first_field_value
from .selection import select_customer_proofs


def _reuse_findings(
    customer_proof_urls: Sequence[str],
    *,
    pack: Dict[str, object],
    decision: Optional[Dict[str, object]],
    ledger: Dict[str, object],
    reference: date,
) -> tuple[List[Finding], List[Dict[str, object]]]:
    findings: List[Finding] = []
    recently_used_sources: List[Dict[str, object]] = []
    for url in customer_proof_urls:
        usage = count_customer_proof_usage(
            ledger,
            proof_id=_proof_id_from_url(url),
            source_url=url,
            reference_date=reference,
        )
        if usage["recent_uses_90d"] > 0:
            recently_used_sources.append({"url": url, "usage": usage})
            findings.append(
                _finding(
                    "customer_proof_recent_use_warning",
                    pack["line"],
                    f"Customer proof source has {usage['recent_uses_90d']} recent use(s) in the last 90 days: {url}",
                    "Prefer suitable approved zero-use proof or document the source-specific reuse decision.",
                    severity="warning",
                    match=url,
                )
            )
        reason = _source_specific_reuse_reason(url, pack, decision)
        comparison = _source_specific_zero_use_comparison(url, pack, decision)
        if usage["recent_uses_90d"] > 0 and not reason:
            findings.append(
                _finding(
                    "customer_proof_reuse_requires_source_specific_reason",
                    pack["line"],
                    f"Customer proof source has been used {usage['recent_uses_90d']} times in the last 90 days: {url}",
                    (
                        "Add a source-specific Reuse reason naming the proof ID, customer, or URL, "
                        "or choose a stronger underused proof source from customer-proof-index.json."
                    ),
                    match=url,
                )
            )
        if usage["recent_uses_90d"] > 0 and not comparison:
            findings.append(
                _finding(
                    "customer_proof_zero_use_comparison_missing",
                    pack["line"],
                    f"Recently used proof lacks an explicit comparison with suitable approved zero-use evidence: {url}",
                    (
                        "Name the suitable zero-use candidates considered and why they do not fit the same role, "
                        "or record that the selector found none for that role."
                    ),
                    match=url,
                )
            )
    return findings, recently_used_sources


def _stronger_underused_candidate_findings(
    overused_sources: Sequence[Dict[str, object]],
    *,
    pack: Dict[str, object],
    decision: Optional[Dict[str, object]],
    ledger: Dict[str, object],
    ledger_path: str | Path,
    proof_index_path: str | Path,
    context_pack: str | Path | None,
    context_receipt: str | Path | None,
    proof_index_payload: Mapping[str, Any] | None,
    validated_claim_set: object | None,
    reference: date,
) -> List[Finding]:
    index_status = customer_proof_snapshot.load_index_for_comparison(
        proof_index_path,
        proof_index_payload,
    )
    if index_status["error"]:
        return [
            _finding(
                str(index_status["rule_id"]),
                pack["line"],
                str(index_status["message"]),
                str(index_status["suggestion"]),
            )
        ]

    index = index_status["index"]
    if not isinstance(index, dict) or not index.get("proof"):
        return []

    selector_query = _selector_query(decision)
    proof_role = _selector_proof_role(decision)
    selector_snapshot = customer_proof_snapshot.selector_inputs(
        index,
        ledger,
        validated_claim_set,
    )
    try:
        if proof_index_payload is not None and selector_snapshot is None:
            raise CustomerProofDataError(
                "validated customer proof claim set is unavailable"
            )
        ranked = select_customer_proofs(
            selector_query,
            index_path=proof_index_path,
            ledger_path=ledger_path,
            context_pack=context_pack,
            context_receipt=context_receipt,
            proof_role=proof_role,
            limit=25,
            reference_date=reference,
            _input_snapshot=selector_snapshot,
        )
    except CustomerProofDataError as exc:
        return [
            _finding(
                "customer_proof_selector_context_unavailable",
                pack["line"],
                f"Receipt-backed customer proof comparison is unavailable: {exc}",
                (
                    "Provide the validated context pack and receipt, then rerun the "
                    "customer proof diversity guard."
                ),
                match=str(exc),
            )
        ]
    findings: List[Finding] = []
    for source in overused_sources:
        url = str(source.get("url", ""))
        selected = _matching_ranked_candidate(url, ranked, index)
        selected_score = int(selected.get("score", 0)) if selected else 0
        stronger = [
            candidate
            for candidate in ranked
            if _is_stronger_underused_candidate(candidate, selected_score, url)
            and not _decision_rejects_candidate(candidate, decision)
        ]
        if stronger:
            best = stronger[0]
            findings.append(
                _finding(
                    "customer_proof_stronger_underused_candidate_available",
                    pack["line"],
                    (
                        "Overused customer proof was selected while a stronger underused approved proof candidate "
                        f"is available: {best.get('proof_id')} ({best.get('customer')})."
                    ),
                    (
                        "Use the stronger underused proof or add a Rejected stronger underused candidate row "
                        "with the candidate proof ID and a section-specific rejection reason."
                    ),
                    match=f"{url} -> {best.get('proof_id')}",
                )
            )
    return findings


def _selector_query(decision: Optional[Dict[str, object]]) -> str:
    command = _first_field_value(decision, "selector command")
    if command:
        try:
            parts = shlex.split(command)
        except ValueError:
            parts = command.split()
        for index, part in enumerate(parts):
            if part.endswith("customer_proof_selector.py") and index + 1 < len(parts):
                return parts[index + 1]
        if parts:
            return " ".join(parts)
    return "customer proof selection"


def _selector_proof_role(decision: Optional[Dict[str, object]]) -> str:
    command = _first_field_value(decision, "selector command")
    if not command:
        return "any"
    try:
        parts = shlex.split(command)
    except ValueError:
        parts = command.split()
    for index, part in enumerate(parts):
        if part == "--proof-role" and index + 1 < len(parts):
            role = parts[index + 1]
            if role in {"experience_story", "metric", "quote", "theme", "any"}:
                return role
    return "any"


def _matching_ranked_candidate(
    url: str,
    ranked: Sequence[Dict[str, Any]],
    index: Dict[str, Any],
) -> Dict[str, Any]:
    slug = _proof_id_from_url(url)
    indexed = _index_candidate_for_url(url, index)
    identifiers = {slug, url}
    if indexed:
        identifiers.add(str(indexed.get("proof_id", "")))
        identifiers.add(str(indexed.get("customer", "")))
    for candidate in ranked:
        if _candidate_matches_identifiers(candidate, identifiers):
            return candidate
    return indexed or {}


def _index_candidate_for_url(url: str, index: Dict[str, Any]) -> Dict[str, Any]:
    slug = _proof_id_from_url(url)
    for candidate in index.get("proof", []):
        if not isinstance(candidate, dict):
            continue
        if str(candidate.get("public_url", "")) == url:
            return candidate
        if str(candidate.get("proof_id", "")) == slug:
            return candidate
    return {}


def _is_stronger_underused_candidate(
    candidate: Dict[str, Any], selected_score: int, selected_url: str
) -> bool:
    if str(candidate.get("public_url", "")) == selected_url:
        return False
    if str(candidate.get("proof_id", "")) == _proof_id_from_url(selected_url):
        return False
    if str(candidate.get("approval_status", "")).strip().lower() != "approved":
        return False
    if not bool(candidate.get("public_copy_allowed", False)):
        return False
    if int(candidate.get("recent_uses_90d", 0)) != 0:
        return False
    return int(candidate.get("score", 0)) >= selected_score


def _decision_rejects_candidate(
    candidate: Dict[str, Any], decision: Optional[Dict[str, object]]
) -> bool:
    if decision is None:
        return False
    identifiers = [
        str(candidate.get("proof_id", "")).strip().lower(),
        str(candidate.get("public_url", "")).strip().lower(),
        str(candidate.get("customer", "")).strip().lower(),
    ]
    for field in decision.get("fields", []):
        key = str(field.get("key", ""))
        if "rejected" not in key:
            continue
        value = str(field.get("value", "")).strip().lower()
        if not value or "none found" in value or "none" == value:
            continue
        if any(identifier and identifier in value for identifier in identifiers):
            return True
    return False


def _source_specific_reuse_reason(
    url: str,
    pack: Dict[str, object],
    decision: Optional[Dict[str, object]],
) -> str:
    identifiers = _source_identifiers(url, pack, decision)
    for block in (pack, decision):
        if block is None:
            continue
        for field in block.get("fields", []):
            key = str(field.get("key", ""))
            if key != "reuse reason":
                continue
            value = str(field.get("value", "")).strip()
            normalized_value = _normalize_text(value)
            if value and any(
                identifier and identifier in normalized_value
                for identifier in identifiers
            ):
                return value
    return ""


def _source_specific_zero_use_comparison(
    url: str,
    pack: Dict[str, object],
    decision: Optional[Dict[str, object]],
) -> str:
    """Return an explicit same-role zero-use comparison for this selection."""
    if not _source_specific_reuse_reason(url, pack, decision):
        return ""
    for block in (decision, pack):
        if block is None:
            continue
        for field in block.get("fields", []):
            key = str(field.get("key", ""))
            value = str(field.get("value", "")).strip()
            normalized = _normalize_text(value)
            if not value or not any(term in key for term in ("zero use", "zero-use", "underused")):
                continue
            if (
                ("none found" in normalized and "role" in normalized)
                or ("reason" in normalized and len(normalized.split()) >= 6)
                or ("zero use" in normalized and "role" in normalized)
            ):
                return value
    return ""


def _source_identifiers(
    url: str,
    pack: Dict[str, object],
    decision: Optional[Dict[str, object]],
) -> List[str]:
    identifiers = {
        _normalize_text(url),
        _normalize_text(_proof_id_from_url(url)),
        _normalize_text(url.rstrip("/").rsplit("/", 1)[-1].replace("-", " ")),
    }
    for block in (pack, decision):
        if block is None:
            continue
        for field in block.get("fields", []):
            value = str(field.get("value", ""))
            if url not in value:
                continue
            for segment in re.split(r"\s*\|\s*", value):
                if segment.strip().lower().startswith("customer"):
                    identifiers.add(_normalize_text(segment.split(":", 1)[-1]))
                if segment.strip().lower().startswith("customer/brand"):
                    identifiers.add(_normalize_text(segment.split(":", 1)[-1]))
                if segment.strip().lower().startswith("selected proof"):
                    identifiers.add(_normalize_text(segment.split(":", 1)[-1]))
            prefix = value.split("|", 1)[0]
            if "," in prefix:
                identifiers.add(_normalize_text(prefix.split(",", 1)[0]))
    return sorted(identifier for identifier in identifiers if identifier)


def _candidate_matches_identifiers(
    candidate: Dict[str, Any], identifiers: set[str]
) -> bool:
    candidate_identifiers = {
        str(candidate.get("proof_id", "")),
        str(candidate.get("public_url", "")),
        str(candidate.get("customer", "")),
    }
    normalized_candidate_identifiers = {
        _normalize_text(identifier)
        for identifier in candidate_identifiers
        if identifier
    }
    normalized_identifiers = {
        _normalize_text(identifier) for identifier in identifiers if identifier
    }
    return bool(normalized_candidate_identifiers.intersection(normalized_identifiers))


__all__ = [
    '_reuse_findings',
    '_stronger_underused_candidate_findings',
    '_selector_query',
    '_selector_proof_role',
    '_matching_ranked_candidate',
    '_index_candidate_for_url',
    '_is_stronger_underused_candidate',
    '_decision_rejects_candidate',
    '_source_specific_reuse_reason',
    '_source_specific_zero_use_comparison',
    '_source_identifiers',
    '_candidate_matches_identifiers'
]
