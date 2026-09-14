"""Build and persist hash-bound customer-proof slate evidence."""

from __future__ import annotations

import hashlib
import json
from datetime import date
from pathlib import Path
from typing import Dict, List, Mapping, Sequence

from .connector_inputs import _raise_if_selector_inputs_changed, _validate_evidence_output_paths
from .contracts import (
    CUSTOMER_PROOF_CANDIDATES_AVAILABLE_OUTCOME,
    NO_FIT_CUSTOMER_PROOF_OUTCOME,
    FindingDict,
    SLATE_ROLES,
    _SelectorInputSnapshot,
)


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


__all__ = [
    '_parse_roles',
    '_parse_selected_overrides',
    '_parse_rejected_overrides',
    '_split_role_assignment',
    '_format_rejected_candidates',
    '_slate_selector_command',
    '_quote_command_value',
    '_write_selector_evidence',
    '_selector_evidence_outcome'
]
