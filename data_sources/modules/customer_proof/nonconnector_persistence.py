"""Build and persist nonconnector selector evidence."""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any, Mapping, Sequence

from ..blog_assembly_contract import atomic_write_json, validate_governance_output_path
from .nonconnector_contracts import SCHEMA, NonVaultProofDataError
from .nonconnector_eligibility import _canonical_brand, _experience_binding
from .nonconnector_inputs import _file_sha256
from .nonconnector_selection import select_nonvault_customer_proofs


def build_nonvault_customer_proof_slate(
    *,
    selector_command: str,
    roles: Sequence[Mapping[str, Any]],
    evidence_path: str = "",
    evidence_sha256: str = "",
) -> str:
    lines = ["Customer Proof Slate", f"- Selector command: {selector_command}"]
    if evidence_path and evidence_sha256:
        lines.append(
            f"- Selector evidence: {evidence_path} | SHA-256: {evidence_sha256}"
        )
    for row in roles:
        role = str(row["role"])
        candidates = ", ".join(str(value) for value in row["candidate_ids"]) or "none"
        selected = str(row.get("selected_id") or "none")
        rejected = row.get("rejected_overrides", {})
        rejected_text = "; ".join(
            f"{candidate}: {reason}"
            for candidate, reason in sorted(dict(rejected).items())
        ) or "none"
        lines.append(
            f"- Role: {role} | Top candidates: [{candidates}] | "
            f"Selected: [{selected}] | Rejected stronger candidates: [{rejected_text}]"
        )
    return "\n".join(lines) + "\n"


def write_nonvault_selector_evidence(
    output_path: str | Path,
    *,
    topic: str,
    brand: str,
    title: str,
    objective: str,
    article_slug: str,
    roles: Sequence[str],
    require_eeat_story: bool,
    limit: int,
    reference_date: date,
    selected_overrides: Mapping[str, str],
    rejected_overrides: Mapping[str, Mapping[str, str]],
    index_path: str | Path,
    ledger_path: str | Path,
) -> tuple[Path, str, list[dict[str, Any]]]:
    index = Path(index_path).resolve()
    ledger = Path(ledger_path).resolve()
    artifacts = {
        "index": {"path": str(index), "sha256": _file_sha256(index)},
        "ledger": {"path": str(ledger), "sha256": _file_sha256(ledger)},
    }
    role_rows: list[dict[str, Any]] = []
    for role in roles:
        results = select_nonvault_customer_proofs(
            topic,
            brand=brand,
            index_path=index,
            ledger_path=ledger,
            title=title,
            objective=objective,
            article_slug=article_slug,
            proof_role=role,
            require_eeat_story=role == "experience_story" and require_eeat_story,
            limit=limit,
            reference_date=reference_date,
        )
        candidate_ids = [str(row["proof_id"]) for row in results]
        selected_id = str(selected_overrides.get(role) or "none")
        if selected_id != "none" and selected_id not in candidate_ids:
            raise NonVaultProofDataError(
                f"Selected customer proof ID is not in the verified {role} candidate slate: {selected_id}"
            )
        selected_candidate = next(
            (row for row in results if str(row.get("proof_id")) == selected_id),
            None,
        )
        role_rows.append(
            {
                "role": role,
                "candidate_ids": candidate_ids,
                "selected_id": selected_id,
                "selected_candidate": (
                    _experience_binding(selected_candidate)
                    if role == "experience_story" and selected_candidate
                    else None
                ),
                "rejected_overrides": dict(rejected_overrides.get(role, {})),
            }
        )

    payload = {
        "schema": SCHEMA,
        "selection_outcome": (
            "customer_proof_candidates_available"
            if any(row["candidate_ids"] for row in role_rows)
            else "no_fit_customer_proof"
        ),
        "inputs": {
            "brand": _canonical_brand(brand),
            "topic": topic,
            "title": title,
            "objective": objective,
            "article_slug": article_slug,
            "roles": list(roles),
            "require_eeat_story": require_eeat_story,
            "limit": limit,
            "reference_date": reference_date.isoformat(),
            "selected_overrides": dict(selected_overrides),
            "rejected_overrides": {
                role: dict(rows) for role, rows in rejected_overrides.items()
            },
        },
        "artifacts": artifacts,
        "roles": role_rows,
    }
    output = Path(output_path)
    validate_governance_output_path(output)
    atomic_write_json(output, payload)
    return output, _file_sha256(output), role_rows


__all__ = [
    'build_nonvault_customer_proof_slate',
    'write_nonvault_selector_evidence'
]
