"""
Customer Proof Selector

Ranks curated customer proof by topic fit, copy boundary, and reuse history.
This module helps writers choose the most relevant proof instead of defaulting
to whichever case study is easiest to cite.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from contextlib import contextmanager, nullcontext
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any, Dict, Iterable, Iterator, List, Mapping, Optional, Sequence
from urllib.parse import urlsplit, urlunsplit

try:
    from .blog_assembly_contract import validate_governance_output_path
    from .proof_usage import count_customer_proof_usage, usage_matches_candidate
    from .vault_claim_receipts import (
        VaultClaimReceiptError,
        load_validated_claim_set,
    )
except ImportError:  # pragma: no cover - supports direct script execution.
    from blog_assembly_contract import validate_governance_output_path
    from proof_usage import count_customer_proof_usage, usage_matches_candidate
    from vault_claim_receipts import VaultClaimReceiptError, load_validated_claim_set


DEFAULT_INDEX_PATH = Path("context/customer-proof-index.json")
DEFAULT_LEDGER_PATH = Path("context/customer-proof-usage-ledger.json")

FindingDict = Dict[str, Any]
SLATE_ROLES = {"experience_story", "metric", "quote", "theme"}
CUSTOMER_PROOF_USE_MODES = {"public_metric", "exact_quote", "public_paraphrase"}
NO_FIT_CUSTOMER_PROOF_OUTCOME = "no_fit_customer_proof"
CUSTOMER_PROOF_CANDIDATES_AVAILABLE_OUTCOME = "customer_proof_candidates_available"
NO_FIT_CUSTOMER_PROOF_REASON = (
    "No customer proof selected because the selector evaluated the current "
    "connector-bound proof inventory and found no article-relevant approved "
    "customer proof for this role; public copy must omit customer proof, named "
    "customer claims, review stories, exact quotes, testimonials, and customer "
    "metrics for the unsupported role."
)
NO_BOUND_CUSTOMER_PROOF_MESSAGE = (
    "no approved claims bound to the customer proof inventory"
)


class CustomerProofDataError(RuntimeError):
    """Raised when receipt-backed customer proof cannot be verified."""


@dataclass(frozen=True)
class _ApprovedClaimBinding:
    claim: Any
    binding_source: str


@dataclass(frozen=True)
class _ArtifactSnapshot:
    label: str
    path: Path
    content: bytes
    sha256: str
    json_object: FindingDict | None = None

    def evidence_record(self) -> FindingDict:
        return {"path": str(self.path), "sha256": self.sha256}


@dataclass(frozen=True)
class _SelectorInputSnapshot:
    artifacts: Mapping[str, _ArtifactSnapshot]
    index: FindingDict
    ledger: FindingDict
    context_pack_path: Path
    context_receipt_path: Path
    receipt_claims: Any


SOURCE_TYPE_WEIGHT = {
    "quote_matrix": 18,
    "reference": 17,
    "customer_story": 16,
    "review_site": 12,
    "case_study": 10,
}

SOURCE_INTENT_BONUS = 18
RECENT_USE_SCORE_PENALTY = 20
HISTORICAL_USE_SCORE_PENALTY = 2

SOURCE_INTENT_PATTERNS = {
    "review_site": (
        "review",
        "reviews",
        "reviewer",
        "review story",
        "review site",
        "g2",
        "capterra",
        "google review",
        "software advice",
        "softwareadvice",
    ),
    "quote_matrix": ("quote matrix",),
    "reference": ("reference", "references"),
    "customer_story": ("customer story", "customer stories"),
    "case_study": ("case study", "case studies"),
}

APPROVAL_WEIGHT = {
    "approved": 24,
    "ready": 18,
    "candidate": 8,
    "blocked": -8,
    "rejected": -20,
}

STOPWORDS = {
    "about",
    "after",
    "and",
    "are",
    "best",
    "business",
    "businesses",
    "for",
    "from",
    "guide",
    "into",
    "job",
    "jobs",
    "software",
    "that",
    "the",
    "this",
    "with",
    "your",
}


def select_customer_proofs(
    topic: str,
    *,
    index_path: str | Path = DEFAULT_INDEX_PATH,
    ledger_path: str | Path = DEFAULT_LEDGER_PATH,
    context_pack: str | Path | None = None,
    context_receipt: str | Path | None = None,
    article_slug: str = "",
    title: str = "",
    objective: str = "",
    require_eeat_story: bool = False,
    proof_role: str = "any",
    limit: int = 8,
    reference_date: Optional[date] = None,
    _input_snapshot: Optional[_SelectorInputSnapshot] = None,
) -> List[FindingDict]:
    """Return ranked customer proof candidates for a topic."""
    reference = reference_date or date.today()
    if _input_snapshot is None:
        index = _load_json(index_path, "customer proof index")
        ledger = _load_json(ledger_path, "customer proof ledger")
        receipt_claims = _load_receipt_claims(context_pack, context_receipt)
    else:
        index = _input_snapshot.index
        ledger = _input_snapshot.ledger
        receipt_claims = _input_snapshot.receipt_claims
    proof_rows = [
        candidate
        for candidate in index.get("proof", [])
        if isinstance(candidate, dict)
        and str(candidate.get("proof_id") or "").strip()
        and str(candidate.get("public_url") or "")
        .strip()
        .startswith(("http://", "https://"))
    ]
    if not proof_rows:
        raise CustomerProofDataError(
            "Customer proof index has no usable public customer proof inventory rows."
        )
    inventory_ids = {str(candidate["proof_id"]).strip() for candidate in proof_rows}
    approved_claims = receipt_claims.approved_claims()
    if not _has_inventory_bound_claim(
        proof_rows,
        inventory_ids=inventory_ids,
        approved_claims=approved_claims,
    ):
        raise CustomerProofDataError(
            "Customer proof context receipt has no approved claims bound to the "
            "customer proof inventory by selector ID or exact public URL; rebuild "
            "the vault-owned selector bindings and context artifacts."
        )
    search_text = " ".join(part for part in (topic, title, objective) if part)
    topic_tokens = _tokens(search_text)

    scored = []
    for candidate in proof_rows:
        if not isinstance(candidate, dict):
            continue
        if require_eeat_story and not _is_review_story_eligible(candidate):
            continue
        use_modes = _use_modes_for_role(proof_role)
        claim_binding = _claim_binding_for_candidate(
            candidate,
            proof_rows=proof_rows,
            receipt_claims=receipt_claims,
            approved_claims=approved_claims,
            use_modes=use_modes,
        )
        if claim_binding is None:
            continue
        approved_claim = claim_binding.claim
        binding_source = claim_binding.binding_source
        if not _matches_proof_role(candidate, proof_role, approved_claim=approved_claim):
            continue
        result = dict(candidate)
        result.update(
            count_customer_proof_usage(
                ledger,
                proof_id=str(candidate.get("proof_id", "")),
                source_url=str(candidate.get("public_url", "")),
                customer=str(candidate.get("customer", "")),
                reference_date=reference,
            )
        )
        result["relevance_score"] = _relevance_score(topic_tokens, candidate)
        result["source_intent_score"] = _source_intent_score(search_text, candidate)
        result["proof_role"] = proof_role
        result["review_story_eligible"] = _is_review_story_eligible(candidate)
        result["claim_id"] = approved_claim.claim_id
        result["binding_source"] = binding_source
        result["approval_source"] = approved_claim.approval_source
        result["context_receipt_revision"] = approved_claim.receipt_revision
        result["score"] = _score_candidate(result)
        result["overused"] = bool(result.get("overused", False))
        result["selection_reason"] = _selection_reason(result)
        scored.append(result)

    if article_slug:
        scored = [
            candidate
            for candidate in scored
            if not _used_in_article(candidate, ledger.get("uses", []), article_slug)
        ] or scored

    scored.sort(
        key=lambda item: (
            item.get("score", 0),
            item.get("relevance_score", 0),
            -item.get("recent_uses_90d", 0),
            str(item.get("proof_id", "")),
        ),
        reverse=True,
    )
    return scored[: max(limit, 0)]


def build_customer_proof_slate(
    topic: str,
    *,
    index_path: str | Path = DEFAULT_INDEX_PATH,
    ledger_path: str | Path = DEFAULT_LEDGER_PATH,
    context_pack: str | Path | None = None,
    context_receipt: str | Path | None = None,
    article_slug: str = "",
    title: str = "",
    objective: str = "",
    require_eeat_story: bool = False,
    roles: Sequence[str] = ("metric", "quote", "theme"),
    limit: int = 8,
    selected_overrides: Optional[Dict[str, str]] = None,
    rejected_overrides: Optional[Dict[str, Dict[str, str]]] = None,
    allow_no_proof: bool = False,
    reference_date: Optional[date] = None,
    _role_evidence: Optional[List[FindingDict]] = None,
    _input_snapshot: Optional[_SelectorInputSnapshot] = None,
) -> str:
    """Return a sidecar-ready Customer Proof Slate block."""
    selected = selected_overrides or {}
    rejected = rejected_overrides or {}
    normalized_roles = _parse_roles(
        ",".join(roles) if not isinstance(roles, str) else roles
    )
    if allow_no_proof and set(normalized_roles) != SLATE_ROLES:
        raise CustomerProofDataError(
            "No-proof customer proof evidence requires metric, quote, theme, "
            "and experience_story roles."
        )
    command = _slate_selector_command(
        topic,
        title=title,
        objective=objective,
        context_pack=context_pack,
        context_receipt=context_receipt,
        require_eeat_story=require_eeat_story,
        roles=normalized_roles,
        limit=limit,
        allow_no_proof=allow_no_proof,
    )
    lines = [
        "Customer Proof Slate",
        f"- Selector command: {command}",
        f"- Context receipt: {context_receipt or 'not supplied'}",
        "- Approval source: connector_claim_result",
    ]
    no_fit_roles: set[str] = set()
    for role in normalized_roles:
        no_fit_reason = ""
        results = select_customer_proofs(
            topic,
            index_path=index_path,
            ledger_path=ledger_path,
            context_pack=context_pack,
            context_receipt=context_receipt,
            article_slug=article_slug,
            title=title,
            objective=objective,
            require_eeat_story=require_eeat_story and role == "experience_story",
            proof_role=role,
            limit=limit,
            reference_date=reference_date,
            _input_snapshot=_input_snapshot,
        )
        if allow_no_proof and not results:
            no_fit_reason = NO_FIT_CUSTOMER_PROOF_REASON
            no_fit_roles.add(role)
        top_candidates = [
            str(result.get("proof_id", ""))
            for result in results
            if result.get("proof_id")
        ]
        claim_ids = [
            str(result.get("claim_id", ""))
            for result in results
            if result.get("claim_id")
        ]
        receipt_revision = next(
            (
                str(result.get("context_receipt_revision", ""))
                for result in results
                if result.get("context_receipt_revision")
            ),
            "not available",
        )
        selected_override = str(selected.get(role) or "").strip()
        if (
            selected_override
            and selected_override.casefold() != "none"
            and selected_override not in top_candidates
        ):
            raise CustomerProofDataError(
                "Selected customer proof ID is not in the verified "
                f"{role} candidate slate: {selected_override}"
            )
        selected_id = selected_override or (
            top_candidates[0] if top_candidates else "none"
        )
        rejected_text = _format_rejected_candidates(rejected.get(role, {}))
        lines.append(
            "- Role: "
            f"{role} | Top candidates: [{', '.join(top_candidates) if top_candidates else 'none'}] "
            f"| Selected: [{selected_id}] | Claim IDs: [{', '.join(claim_ids) if claim_ids else 'none'}] "
            f"| Receipt revision: {receipt_revision} | Rejected stronger candidates: [{rejected_text}]"
        )
        if no_fit_reason:
            lines.append(f"  - No-fit reason: {no_fit_reason}")
        if _role_evidence is not None:
            row = {
                "role": role,
                "candidate_ids": top_candidates,
                "claim_ids": claim_ids,
                "receipt_revision": receipt_revision,
                "selected_id": selected_id,
            }
            if no_fit_reason:
                row["selection_outcome"] = NO_FIT_CUSTOMER_PROOF_OUTCOME
                row["no_fit_reason"] = no_fit_reason
            _role_evidence.append(row)
    if no_fit_roles and no_fit_roles == set(normalized_roles):
        lines.insert(4, f"- Selection outcome: {NO_FIT_CUSTOMER_PROOF_OUTCOME}")
    return "\n".join(lines)


def _is_no_bound_customer_proof_error(error: CustomerProofDataError) -> bool:
    return NO_BOUND_CUSTOMER_PROOF_MESSAGE in str(error)


def _parse_roles(raw_roles: str) -> List[str]:
    roles = [role.strip().lower() for role in raw_roles.split(",") if role.strip()]
    if not roles:
        roles = ["metric", "quote", "theme"]
    invalid = [role for role in roles if role not in SLATE_ROLES]
    if invalid:
        raise ValueError(f"Unsupported slate role: {', '.join(invalid)}")
    return roles


def _parse_selected_overrides(values: Sequence[str]) -> Dict[str, str]:
    overrides: Dict[str, str] = {}
    for value in values:
        role, proof_id = _split_role_assignment(value)
        overrides[role] = proof_id
    return overrides


def _parse_rejected_overrides(values: Sequence[str]) -> Dict[str, Dict[str, str]]:
    overrides: Dict[str, Dict[str, str]] = {}
    for value in values:
        role, rejected = _split_role_assignment(value)
        proof_id, separator, reason = rejected.partition(":")
        if not separator or not proof_id.strip() or not reason.strip():
            raise ValueError("--reject values must use role=proof_id:reason")
        overrides.setdefault(role, {})[proof_id.strip()] = reason.strip()
    return overrides


def _split_role_assignment(value: str) -> tuple[str, str]:
    role, separator, assigned = value.partition("=")
    role = role.strip().lower()
    assigned = assigned.strip()
    if not separator or role not in SLATE_ROLES or not assigned:
        raise ValueError(f"Expected role=proof_id for override, got: {value}")
    return role, assigned


def _format_rejected_candidates(rejected: Dict[str, str]) -> str:
    if not rejected:
        return "none"
    return ", ".join(f"{proof_id}: {reason}" for proof_id, reason in rejected.items())


def _slate_selector_command(
    topic: str,
    *,
    title: str,
    objective: str,
    context_pack: str | Path | None,
    context_receipt: str | Path | None,
    require_eeat_story: bool,
    roles: Sequence[str],
    limit: int,
    allow_no_proof: bool = False,
) -> str:
    parts = [
        "python",
        "data_sources/modules/customer_proof_selector.py",
        _quote_command_value(topic),
    ]
    if title:
        parts.extend(["--title", _quote_command_value(title)])
    if objective:
        parts.extend(["--objective", _quote_command_value(objective)])
    if context_pack:
        parts.extend(["--context-pack", _quote_command_value(str(context_pack))])
    if context_receipt:
        parts.extend(["--context-receipt", _quote_command_value(str(context_receipt))])
    if require_eeat_story:
        parts.append("--require-eeat-story")
    if allow_no_proof:
        parts.append("--allow-no-proof")
    parts.extend(["--slate", "--roles", ",".join(roles), "--limit", str(limit)])
    return " ".join(parts)


def _quote_command_value(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def _capture_artifact(
    path_value: str | Path | None,
    label: str,
    *,
    parse_json_object: bool = False,
) -> _ArtifactSnapshot:
    if path_value is None or not str(path_value).strip():
        raise CustomerProofDataError(f"{label} is required for selector evidence")
    path = Path(path_value).expanduser().resolve()
    try:
        if not path.exists():
            raise CustomerProofDataError(f"{label} is unavailable: {path}")
        if not path.is_file():
            raise CustomerProofDataError(f"{label} is not a regular file: {path}")
        content = path.read_bytes()
    except CustomerProofDataError:
        raise
    except OSError as exc:
        raise CustomerProofDataError(f"{label} is unreadable: {path}: {exc}") from exc

    json_object = None
    if parse_json_object:
        try:
            decoded = content.decode("utf-8-sig")
            parsed = json.loads(decoded)
        except (UnicodeError, json.JSONDecodeError) as exc:
            raise CustomerProofDataError(
                f"{label} is invalid JSON: {path}: {exc}"
            ) from exc
        if not isinstance(parsed, dict):
            raise CustomerProofDataError(f"{label} is invalid JSON object: {path}")
        json_object = parsed
    return _ArtifactSnapshot(
        label=label,
        path=path,
        content=content,
        sha256=hashlib.sha256(content).hexdigest(),
        json_object=json_object,
    )


def _load_json(path: str | Path, label: str) -> FindingDict:
    snapshot = _capture_artifact(path, label, parse_json_object=True)
    if snapshot.json_object is None:  # pragma: no cover - constructor invariant.
        raise CustomerProofDataError(f"{label} is invalid JSON object: {snapshot.path}")
    return snapshot.json_object


def _load_receipt_claims(
    context_pack: str | Path | None,
    context_receipt: str | Path | None,
) -> Any:
    try:
        receipt_claims = load_validated_claim_set(context_pack, context_receipt)
    except VaultClaimReceiptError as exc:
        raise CustomerProofDataError(
            f"Customer proof context receipt is invalid: {exc}"
        ) from exc
    if not receipt_claims.available:
        raise CustomerProofDataError(
            f"Customer proof context receipt is unavailable: {receipt_claims.blocker}"
        )
    return receipt_claims


def _normalize_public_url(value: Any) -> str:
    url = str(value or "").strip()
    if not url.startswith(("http://", "https://")):
        return ""
    parsed = urlsplit(url)
    if not parsed.scheme or not parsed.netloc:
        return ""
    path = parsed.path.rstrip("/")
    return urlunsplit(
        (
            parsed.scheme.lower(),
            parsed.netloc.lower(),
            path,
            parsed.query,
            "",
        )
    )


def _inventory_url_map(proof_rows: Iterable[FindingDict]) -> dict[str, list[str]]:
    url_map: dict[str, list[str]] = {}
    for candidate in proof_rows:
        proof_id = str(candidate.get("proof_id") or "").strip()
        normalized = _normalize_public_url(candidate.get("public_url"))
        if not proof_id or not normalized:
            continue
        url_map.setdefault(normalized, []).append(proof_id)
    return url_map


def _public_url_binding(
    candidate: FindingDict,
    *,
    proof_rows: Iterable[FindingDict],
    approved_claims: Sequence[Any],
    use_modes: set[str],
) -> _ApprovedClaimBinding | None:
    normalized_url = _normalize_public_url(candidate.get("public_url"))
    if not normalized_url:
        return None
    inventory_matches = sorted(set(_inventory_url_map(proof_rows).get(normalized_url, [])))
    if len(inventory_matches) > 1:
        raise CustomerProofDataError(
            "Customer proof public URL binding is ambiguous for "
            f"{normalized_url}: {', '.join(inventory_matches)}"
        )
    matches = [
        claim
        for claim in approved_claims
        if not str(getattr(claim, "selector_id", "") or "").strip()
        and str(getattr(claim, "use_mode", "") or "") in use_modes
        and _normalize_public_url(getattr(claim, "public_url", "")) == normalized_url
    ]
    if len(matches) > 1:
        claim_ids = ", ".join(sorted(str(claim.claim_id) for claim in matches))
        raise CustomerProofDataError(
            "Customer proof approved claim public URL binding is ambiguous for "
            f"{normalized_url}: {claim_ids}"
        )
    if not matches:
        return None
    return _ApprovedClaimBinding(
        claim=matches[0],
        binding_source="public_url_exact_match",
    )


def _claim_binding_for_candidate(
    candidate: FindingDict,
    *,
    proof_rows: Iterable[FindingDict],
    receipt_claims: Any,
    approved_claims: Sequence[Any],
    use_modes: set[str],
) -> _ApprovedClaimBinding | None:
    approved_claim = receipt_claims.require_selector_claim(
        str(candidate.get("proof_id", "")),
        use_modes=use_modes,
        public_url=str(candidate.get("public_url", "")),
    )
    if approved_claim is not None:
        return _ApprovedClaimBinding(
            claim=approved_claim,
            binding_source="selector_id",
        )
    return _public_url_binding(
        candidate,
        proof_rows=proof_rows,
        approved_claims=approved_claims,
        use_modes=use_modes,
    )


def _has_inventory_bound_claim(
    proof_rows: Iterable[FindingDict],
    *,
    inventory_ids: set[str],
    approved_claims: Sequence[Any],
) -> bool:
    receipt_selector_ids = {
        str(getattr(claim, "selector_id", "") or "").strip()
        for claim in approved_claims
        if str(getattr(claim, "selector_id", "") or "").strip()
    }
    if inventory_ids.intersection(receipt_selector_ids):
        return True
    url_map = _inventory_url_map(proof_rows)
    for claim in approved_claims:
        if str(getattr(claim, "selector_id", "") or "").strip():
            continue
        if str(getattr(claim, "use_mode", "") or "") not in CUSTOMER_PROOF_USE_MODES:
            continue
        normalized_url = _normalize_public_url(getattr(claim, "public_url", ""))
        if not normalized_url or normalized_url not in url_map:
            continue
        inventory_matches = sorted(set(url_map[normalized_url]))
        if len(inventory_matches) > 1:
            raise CustomerProofDataError(
                "Customer proof public URL binding is ambiguous for "
                f"{normalized_url}: {', '.join(inventory_matches)}"
            )
        return True
    return False


@contextmanager
def _selector_input_snapshot(
    *,
    index_path: str | Path,
    ledger_path: str | Path,
    context_pack: str | Path | None,
    context_receipt: str | Path | None,
) -> Iterator[_SelectorInputSnapshot]:
    artifacts = {
        "index": _capture_artifact(
            index_path,
            "customer proof index",
            parse_json_object=True,
        ),
        "ledger": _capture_artifact(
            ledger_path,
            "customer proof ledger",
            parse_json_object=True,
        ),
        "context_pack": _capture_artifact(context_pack, "context pack"),
        "context_receipt": _capture_artifact(context_receipt, "context receipt"),
    }
    changed_input = _selector_artifacts_unchanged(artifacts)
    if changed_input is not None:
        raise CustomerProofDataError(
            f"Selector evidence input changed during snapshot: {changed_input}"
        )

    with TemporaryDirectory(prefix="simpro-customer-proof-") as temp_dir:
        snapshot_root = Path(temp_dir)
        snapshot_pack = snapshot_root / "context-pack.json"
        snapshot_receipt = snapshot_root / "context-receipt.json"
        snapshot_pack.write_bytes(artifacts["context_pack"].content)
        snapshot_receipt.write_bytes(artifacts["context_receipt"].content)
        receipt_claims = _load_receipt_claims(snapshot_pack, snapshot_receipt)
        index = artifacts["index"].json_object
        ledger = artifacts["ledger"].json_object
        if index is None or ledger is None:  # pragma: no cover - capture invariant.
            raise CustomerProofDataError("Selector JSON snapshot is unavailable")
        yield _SelectorInputSnapshot(
            artifacts=artifacts,
            index=index,
            ledger=ledger,
            context_pack_path=snapshot_pack,
            context_receipt_path=snapshot_receipt,
            receipt_claims=receipt_claims,
        )


def _relevance_score(topic_tokens: set[str], candidate: FindingDict) -> int:
    if not topic_tokens:
        return 0
    candidate_tokens = _tokens(_candidate_text(candidate))
    overlap = topic_tokens.intersection(candidate_tokens)
    phrase_bonus = 0
    text = _normalize_space(_candidate_text(candidate).lower())
    topic = _normalize_space(" ".join(sorted(topic_tokens)))
    if "quote to cash" in text or "quote-to-cash" in text:
        phrase_bonus += 8
    if "small trade" in text or "small trades" in text:
        phrase_bonus += 6
    if (
        "quoting" in topic_tokens
        and "invoicing" in topic_tokens
        and {"quoting", "invoicing"}.issubset(candidate_tokens)
    ):
        phrase_bonus += 10
    if topic and topic in text:
        phrase_bonus += 5
    return len(overlap) * 10 + phrase_bonus


def _score_candidate(candidate: FindingDict) -> int:
    approval = str(candidate.get("approval_status", "")).strip().lower()
    source_type = str(candidate.get("source_type", "")).strip().lower()
    public_copy_allowed = bool(candidate.get("public_copy_allowed", False))
    score = int(candidate.get("relevance_score", 0))
    score += APPROVAL_WEIGHT.get(approval, 0)
    score += SOURCE_TYPE_WEIGHT.get(source_type, 0)
    if public_copy_allowed:
        score += 8
    score += int(candidate.get("source_intent_score", 0))
    score -= int(candidate.get("recent_uses_90d", 0)) * RECENT_USE_SCORE_PENALTY
    score -= (
        max(
            int(candidate.get("total_uses", 0))
            - int(candidate.get("recent_uses_90d", 0)),
            0,
        )
        * HISTORICAL_USE_SCORE_PENALTY
    )
    return score


def _used_in_article(
    candidate: FindingDict, uses: Iterable[FindingDict], article_slug: str
) -> bool:
    for usage in uses:
        if str(usage.get("article_slug", "")) != article_slug:
            continue
        if usage_matches_candidate(candidate, usage):
            return True
    return False


def _selection_reason(candidate: FindingDict) -> str:
    parts = [
        f"relevance={candidate.get('relevance_score', 0)}",
        f"source_intent={candidate.get('source_intent_score', 0)}",
        f"source_type={candidate.get('source_type', '')}",
        f"status={candidate.get('approval_status', '')}",
        f"recent_uses_90d={candidate.get('recent_uses_90d', 0)}",
    ]
    if candidate.get("review_story_eligible"):
        parts.append("review_story_eligible=true")
    if candidate.get("overused"):
        parts.append("overused=true")
    return "; ".join(parts)


def _candidate_text(candidate: FindingDict) -> str:
    values: List[str] = []
    for key in (
        "proof_id",
        "customer",
        "source_type",
        "industry",
        "region",
        "company_size",
        "workflow_fit",
        "themes",
        "evidence",
        "restrictions",
    ):
        values.extend(_flatten(candidate.get(key)))
    for row_key in ("approved_quotes", "approved_metrics"):
        for row in candidate.get(row_key, []) or []:
            values.extend(_flatten(row))
    values.extend(_flatten(candidate.get("review_story")))
    return " ".join(values)


def _matches_proof_role(
    candidate: FindingDict,
    proof_role: str,
    *,
    approved_claim: Any | None = None,
) -> bool:
    role = str(proof_role or "any").strip().lower()
    if role == "any":
        return True
    approved_mode = str(getattr(approved_claim, "use_mode", "") or "").strip()
    if role == "experience_story":
        source_type = str(candidate.get("source_type", "")).strip().lower()
        if _is_review_story_eligible(candidate):
            return True
        return source_type in {"case_study", "customer_story", "reference"} and bool(
            candidate.get("public_copy_allowed", False)
        )
    if role == "metric":
        if approved_mode == "public_metric":
            return True
        return bool(candidate.get("approved_metrics") or [])
    if role == "quote":
        if approved_mode == "exact_quote":
            return True
        for row in candidate.get("approved_quotes", []) or []:
            if (
                isinstance(row, dict)
                and str(row.get("status", "")).strip().lower() == "approved"
            ):
                return True
            if isinstance(row, str) and "status: approved" in row.lower():
                return True
        return False
    if role == "theme":
        return bool(
            candidate.get("themes")
            or candidate.get("evidence")
            or candidate.get("workflow_fit")
        )
    return True


def _use_modes_for_role(proof_role: str) -> set[str]:
    role = str(proof_role or "any").strip().lower()
    if role == "metric":
        return {"public_metric"}
    if role == "quote":
        return {"exact_quote"}
    if role in {"theme", "experience_story"}:
        return {"public_paraphrase"}
    return {"public_metric", "exact_quote", "public_paraphrase"}


def _is_review_story_eligible(candidate: FindingDict) -> bool:
    story = candidate.get("review_story") or {}
    if not isinstance(story, dict):
        return False
    if story.get("story_allowed") is not True:
        return False
    identity_type = str(story.get("identity_type", "")).strip().lower()
    if identity_type not in {"person", "business", "person_and_business"}:
        return False
    identity = (
        str(story.get("identity_display", "")).strip()
        or str(story.get("person_name", "")).strip()
        or str(story.get("business_name", "")).strip()
    )
    if not identity:
        return False
    public_url = str(
        story.get("public_url") or candidate.get("public_url") or ""
    ).strip()
    return public_url.startswith(("http://", "https://"))


def _source_intent_score(topic: str, candidate: FindingDict) -> int:
    source_type = str(candidate.get("source_type", "")).strip().lower()
    patterns = SOURCE_INTENT_PATTERNS.get(source_type, ())
    if not patterns:
        return 0
    normalized_topic = _normalize_space(_normalize_text(topic))
    raw_topic = topic.lower()
    for pattern in patterns:
        normalized_pattern = _normalize_space(_normalize_text(pattern))
        if pattern in raw_topic or normalized_pattern in normalized_topic:
            return SOURCE_INTENT_BONUS
    return 0


def _flatten(value: Any) -> List[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        return [str(item) for pair in value.items() for item in pair]
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        flattened: List[str] = []
        for item in value:
            flattened.extend(_flatten(item))
        return flattened
    return [str(value)]


def _tokens(text: str) -> set[str]:
    normalized = _normalize_text(text.replace("-", " "))
    tokens = set()
    for token in re.findall(r"[a-z0-9]+", normalized):
        if len(token) < 3 or token in STOPWORDS:
            continue
        if token == "quotes":
            token = "quoting"
        if token in {"invoice", "invoices"}:
            token = "invoicing"
        tokens.add(token)
    return tokens


def _normalize_text(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()


def _normalize_space(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _selector_artifacts_unchanged(
    artifacts: Mapping[str, _ArtifactSnapshot],
) -> Optional[Path]:
    for artifact in artifacts.values():
        try:
            current_content = artifact.path.read_bytes()
        except OSError:
            return artifact.path
        if current_content != artifact.content:
            return artifact.path
    return None


def _raise_if_selector_inputs_changed(
    artifacts: Mapping[str, _ArtifactSnapshot],
) -> None:
    changed_input = _selector_artifacts_unchanged(artifacts)
    if changed_input is not None:
        raise CustomerProofDataError(
            f"Selector evidence input changed during selection: {changed_input}"
        )


def _paths_alias(left: Path, right: Path) -> bool:
    """Return whether two paths name the same file, including hard links."""
    try:
        left_normalized = os.path.normcase(str(left.resolve(strict=False)))
        right_normalized = os.path.normcase(str(right.resolve(strict=False)))
    except OSError:
        left_normalized = os.path.normcase(os.path.abspath(str(left)))
        right_normalized = os.path.normcase(os.path.abspath(str(right)))
    if left_normalized == right_normalized:
        return True
    try:
        return left.exists() and right.exists() and os.path.samefile(left, right)
    except OSError:
        return False


def _validate_evidence_output_paths(
    output: Path,
    temporary_output: Path,
    artifacts: Mapping[str, _ArtifactSnapshot],
) -> None:
    validate_governance_output_path(output)
    validate_governance_output_path(temporary_output)
    for candidate in (output, temporary_output):
        for artifact in artifacts.values():
            if _paths_alias(candidate, artifact.path):
                raise CustomerProofDataError(
                    "Selector evidence output aliases selector input: "
                    f"{candidate} -> {artifact.path}"
                )


def _write_selector_evidence(
    output_path: str | Path,
    *,
    topic: str,
    title: str,
    objective: str,
    article_slug: str,
    roles: Sequence[str],
    require_eeat_story: bool,
    limit: int,
    reference_date: date,
    selected_overrides: Mapping[str, str],
    rejected_overrides: Mapping[str, Mapping[str, str]],
    allow_no_proof: bool,
    role_evidence: Sequence[FindingDict],
    input_snapshot: _SelectorInputSnapshot,
) -> tuple[str, str]:
    artifacts = input_snapshot.artifacts
    selection_outcome = _selector_evidence_outcome(role_evidence)
    evidence = {
        "schema": "simpro-customer-proof-selector-evidence/v1",
        "selection_outcome": selection_outcome,
        "inputs": {
            "topic": topic,
            "title": title,
            "objective": objective,
            "article_slug": article_slug,
            "roles": list(roles),
            "require_eeat_story": require_eeat_story,
            "allow_no_proof": allow_no_proof,
            "limit": limit,
            "reference_date": reference_date.isoformat(),
            "selected_overrides": dict(selected_overrides),
            "rejected_overrides": {
                role: dict(rows) for role, rows in rejected_overrides.items()
            },
        },
        "artifacts": {
            name: artifact.evidence_record() for name, artifact in artifacts.items()
        },
        "roles": list(role_evidence),
    }
    output = Path(output_path).expanduser()
    temporary_output = output.with_name(f"{output.name}.tmp")
    _validate_evidence_output_paths(output, temporary_output, artifacts)
    output.parent.mkdir(parents=True, exist_ok=True)
    payload = (
        json.dumps(evidence, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")
    published = False
    original_output = output.read_bytes() if output.is_file() else None
    _raise_if_selector_inputs_changed(artifacts)
    try:
        temporary_output.write_bytes(payload)
        _raise_if_selector_inputs_changed(artifacts)
        temporary_output.replace(output)
        published = True
        _raise_if_selector_inputs_changed(artifacts)
    except Exception:
        temporary_output.unlink(missing_ok=True)
        if published:
            if original_output is None:
                output.unlink(missing_ok=True)
            else:
                temporary_output.write_bytes(original_output)
                temporary_output.replace(output)
        raise
    return str(output), hashlib.sha256(payload).hexdigest()


def _selector_evidence_outcome(role_evidence: Sequence[FindingDict]) -> str:
    if role_evidence and all(
        row.get("selection_outcome") == NO_FIT_CUSTOMER_PROOF_OUTCOME
        and str(row.get("selected_id") or "").casefold() == "none"
        and not row.get("candidate_ids")
        and not row.get("claim_ids")
        for row in role_evidence
    ):
        return NO_FIT_CUSTOMER_PROOF_OUTCOME
    return CUSTOMER_PROOF_CANDIDATES_AVAILABLE_OUTCOME


def _main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Rank customer proof candidates for a topic."
    )
    parser.add_argument("topic", help="Topic or keyword to rank proof against.")
    parser.add_argument(
        "--index",
        default=str(DEFAULT_INDEX_PATH),
        help="Customer proof index JSON path.",
    )
    parser.add_argument(
        "--ledger",
        default=str(DEFAULT_LEDGER_PATH),
        help="Customer proof usage ledger JSON path.",
    )
    parser.add_argument(
        "--context-pack", help="simpro-product-context-pack/v2 JSON path."
    )
    parser.add_argument(
        "--context-receipt", help="simpro-context-receipt/v1 JSON path."
    )
    parser.add_argument(
        "--article-slug",
        default="",
        help="Optional current article slug to avoid same-article repeats.",
    )
    parser.add_argument(
        "--title", default="", help="Optional article title for proof fit scoring."
    )
    parser.add_argument(
        "--objective",
        default="",
        help="Optional content objective for proof fit scoring.",
    )
    parser.add_argument(
        "--require-eeat-story",
        action="store_true",
        help="Only return review-story rows with a real identity and public review URL.",
    )
    parser.add_argument(
        "--proof-role",
        choices=["experience_story", "metric", "quote", "theme", "any"],
        default="any",
        help="Desired proof role for this selection pass.",
    )
    parser.add_argument(
        "--limit", type=int, default=8, help="Maximum number of candidates to return."
    )
    parser.add_argument(
        "--slate",
        action="store_true",
        help="Print a sidecar-ready Customer Proof Slate block instead of JSON.",
    )
    parser.add_argument(
        "--roles",
        default="metric,quote,theme",
        help="Comma-separated proof roles to include when --slate is used.",
    )
    parser.add_argument(
        "--selected",
        action="append",
        default=[],
        help="Override selected proof for a slate role, e.g. metric=proof_id. Repeatable.",
    )
    parser.add_argument(
        "--reject",
        action="append",
        default=[],
        help="Document a rejected stronger candidate, e.g. metric=proof_id:section-specific reason. Repeatable.",
    )
    parser.add_argument(
        "--evidence-output",
        help="Write a hash-bound JSON record of selector inputs and verified candidates.",
    )
    parser.add_argument(
        "--allow-no-proof",
        action="store_true",
        help=(
            "Allow a full four-role slate to emit no-fit evidence when the "
            "current connector context has no bound customer proof candidates."
        ),
    )
    args = parser.parse_args(argv)
    if args.evidence_output and not args.slate:
        parser.error("--evidence-output requires --slate")
    if args.allow_no_proof and not args.evidence_output:
        parser.error("--allow-no-proof requires --evidence-output")

    try:
        if args.slate:
            try:
                roles = _parse_roles(args.roles)
                selected_overrides = _parse_selected_overrides(args.selected)
                rejected_overrides = _parse_rejected_overrides(args.reject)
            except ValueError as exc:
                parser.error(str(exc))
            if args.allow_no_proof and set(roles) != SLATE_ROLES:
                parser.error(
                    "--allow-no-proof requires --roles metric,quote,theme,experience_story"
                )
            reference_date = date.today()
            snapshot_context = (
                _selector_input_snapshot(
                    index_path=args.index,
                    ledger_path=args.ledger,
                    context_pack=args.context_pack,
                    context_receipt=args.context_receipt,
                )
                if args.evidence_output
                else nullcontext(None)
            )
            with snapshot_context as input_snapshot:
                role_evidence: List[FindingDict] = []
                slate = build_customer_proof_slate(
                    args.topic,
                    index_path=args.index,
                    ledger_path=args.ledger,
                    context_pack=args.context_pack,
                    context_receipt=args.context_receipt,
                    article_slug=args.article_slug,
                    title=args.title,
                    objective=args.objective,
                    require_eeat_story=args.require_eeat_story,
                    roles=roles,
                    limit=args.limit,
                    selected_overrides=selected_overrides,
                    rejected_overrides=rejected_overrides,
                    allow_no_proof=args.allow_no_proof,
                    reference_date=reference_date,
                    _role_evidence=role_evidence,
                    _input_snapshot=input_snapshot,
                )
                if args.evidence_output:
                    if input_snapshot is None:  # pragma: no cover - context invariant.
                        raise CustomerProofDataError(
                            "Selector evidence input snapshot is unavailable"
                        )
                    evidence_path, evidence_hash = _write_selector_evidence(
                        args.evidence_output,
                        topic=args.topic,
                        title=args.title,
                        objective=args.objective,
                        article_slug=args.article_slug,
                        roles=roles,
                        require_eeat_story=args.require_eeat_story,
                        limit=args.limit,
                        reference_date=reference_date,
                        selected_overrides=selected_overrides,
                        rejected_overrides=rejected_overrides,
                        allow_no_proof=args.allow_no_proof,
                        role_evidence=role_evidence,
                        input_snapshot=input_snapshot,
                    )
                    slate_lines = slate.splitlines()
                    slate_lines.insert(
                        2,
                        f"- Selector evidence: {evidence_path} | SHA-256: {evidence_hash}",
                    )
                    slate = "\n".join(slate_lines)
            print(slate)
        else:
            results = select_customer_proofs(
                args.topic,
                index_path=args.index,
                ledger_path=args.ledger,
                context_pack=args.context_pack,
                context_receipt=args.context_receipt,
                article_slug=args.article_slug,
                title=args.title,
                objective=args.objective,
                require_eeat_story=args.require_eeat_story,
                proof_role=args.proof_role,
                limit=args.limit,
            )
            print(json.dumps({"topic": args.topic, "results": results}, indent=2))
    except CustomerProofDataError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(_main())
