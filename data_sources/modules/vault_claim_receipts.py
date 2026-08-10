"""Validate Simpro context-pack receipts for public proof eligibility."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Optional

try:
    from .simpro_vault_client import SimproVaultClient, VaultClientError
except ImportError:  # pragma: no cover - supports direct script execution.
    from simpro_vault_client import SimproVaultClient, VaultClientError


PACK_SCHEMA = "simpro-product-context-pack/v2"
RECEIPT_SCHEMA = "simpro-context-receipt/v1"
APPROVAL_SOURCE = "connector_claim_result"
SIMPRO_SCOPE = "Simpro"


class VaultClaimReceiptError(RuntimeError):
    """Raised when a context pack and receipt cannot approve public proof."""


@dataclass(frozen=True)
class ApprovedClaim:
    claim_id: str
    selector_id: str
    assertion: str
    use_mode: str
    brand_scope: tuple[str, ...]
    source_hash: str
    public_url: str
    approval_source: str
    receipt_revision: str
    claim_type: str = ""
    authority_resource_id: str = ""
    evidence_anchor: str = ""


class ValidatedClaimSet:
    """Receipt-approved public claim lookup for selectors and guards."""

    def __init__(
        self,
        claims: Iterable[ApprovedClaim] = (),
        *,
        blocker: str = "",
        receipt_revision: str = "",
    ) -> None:
        self._claims = list(claims)
        self.blocker = blocker
        self.receipt_revision = receipt_revision

    @property
    def available(self) -> bool:
        return not self.blocker

    def claim_ids(self) -> list[str]:
        return [claim.claim_id for claim in self._claims]

    def approved_claims(self) -> tuple[ApprovedClaim, ...]:
        """Return immutable receipt-approved claim records for semantic selectors."""
        return tuple(self._claims)

    def require_selector_claim(
        self,
        selector_id: str,
        *,
        use_modes: set[str],
        public_url: str = "",
        source_hash: str = "",
    ) -> Optional[ApprovedClaim]:
        selector = str(selector_id or "").strip()
        expected_url = str(public_url or "").strip()
        expected_hash = str(source_hash or "").strip()
        for claim in self._claims:
            if claim.selector_id != selector:
                continue
            if claim.use_mode not in use_modes:
                continue
            if expected_url and claim.public_url != expected_url:
                continue
            if expected_hash and claim.source_hash != expected_hash:
                continue
            return claim
        return None


def load_validated_claim_set(
    context_pack_path: str | Path | None,
    context_receipt_path: str | Path | None,
    *,
    vault_root: str | Path | None = None,
    client: Any = None,
) -> ValidatedClaimSet:
    """Load and validate a file-based context pack plus receipt."""
    if not context_pack_path or not context_receipt_path:
        return ValidatedClaimSet(
            blocker="context pack and receipt are required for public proof eligibility"
        )

    pack = _load_json_object(Path(context_pack_path), "context pack")
    receipt = _load_json_object(Path(context_receipt_path), "context receipt")
    _validate_pack_and_receipt(pack, receipt)
    request = _context_request(pack)
    try:
        validator = client or SimproVaultClient(vault_root=vault_root)
        validation = validator.validate_context(request, pack, receipt)
    except (VaultClientError, OSError, ValueError) as error:
        raise VaultClaimReceiptError(
            f"live connector could not validate context: {error}"
        ) from error
    if (
        not isinstance(validation, dict)
        or validation.get("valid") is not True
        or validation.get("errors")
    ):
        raise VaultClaimReceiptError("live connector rejected the context pack and receipt")
    receipt_revision = _receipt_revision(receipt)
    evidence_rows = _section_list(pack, "Approved Claim Evidence")
    evidence_by_claim_id: dict[str, dict[str, Any]] = {}
    for item in evidence_rows:
        claim_id = str(item.get("claim_id") or "").strip()
        if not claim_id:
            raise VaultClaimReceiptError("approved claim evidence requires claim_id")
        if claim_id in evidence_by_claim_id:
            raise VaultClaimReceiptError(f"approved claim evidence is duplicated: {claim_id}")
        evidence_by_claim_id[claim_id] = item
    claims = []
    for decision in _list_field(receipt, "claim_decisions"):
        claim_id = str(decision.get("claim_id") or "").strip()
        evidence = evidence_by_claim_id.get(claim_id)
        if evidence is None:
            raise VaultClaimReceiptError(f"claim decision has no pack evidence: {claim_id}")
        claims.append(_approved_claim_from_records(evidence, decision, receipt_revision))
    if {claim.claim_id for claim in claims} != set(evidence_by_claim_id):
        raise VaultClaimReceiptError("pack claim evidence and receipt decisions differ")
    return ValidatedClaimSet(claims, receipt_revision=receipt_revision)


def _load_json_object(path: Path, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise VaultClaimReceiptError(f"{label} is unreadable: {path}") from error
    if not isinstance(value, dict):
        raise VaultClaimReceiptError(f"{label} must be a JSON object: {path}")
    return value


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _sha256_json(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _list_field(value: dict[str, Any], field: str) -> list[dict[str, Any]]:
    items = value.get(field)
    if not isinstance(items, list):
        raise VaultClaimReceiptError(f"{field} must be a list")
    if not all(isinstance(item, dict) for item in items):
        raise VaultClaimReceiptError(f"{field} must contain only objects")
    return items


def _validate_pack_and_receipt(pack: dict[str, Any], receipt: dict[str, Any]) -> None:
    if pack.get("schema") != PACK_SCHEMA:
        raise VaultClaimReceiptError("context pack schema is unsupported")
    if receipt.get("schema") != RECEIPT_SCHEMA:
        raise VaultClaimReceiptError("context receipt schema is unsupported")
    request = _context_request(pack)
    if receipt.get("request_sha256") != _sha256_json(request):
        raise VaultClaimReceiptError("context receipt request hash does not match")
    if receipt.get("pack_sha256") != _sha256_json(pack):
        raise VaultClaimReceiptError("context receipt pack hash does not match")
    pack_revisions = pack.get("revisions")
    receipt_revisions = receipt.get("revisions")
    if not isinstance(pack_revisions, dict) or not isinstance(receipt_revisions, dict):
        raise VaultClaimReceiptError("context pack and receipt revisions are required")
    if pack_revisions != receipt_revisions:
        raise VaultClaimReceiptError("context receipt revisions do not match pack revisions")
    if pack.get("claim_registry_revision") != receipt.get("claim_registry_revision"):
        raise VaultClaimReceiptError("context claim registry revisions do not match")
    if pack.get("claim_registry_revision") != pack_revisions.get("claim_registry_revision"):
        raise VaultClaimReceiptError("context claim registry revision is inconsistent")
    receipt_hash = str(receipt.get("receipt_sha256") or "").strip()
    unsigned_receipt = {key: value for key, value in receipt.items() if key != "receipt_sha256"}
    if not receipt_hash or receipt_hash != _sha256_json(unsigned_receipt):
        raise VaultClaimReceiptError("context receipt self-hash does not match")
    _section_list(pack, "Approved Claim Evidence")
    _list_field(receipt, "claim_decisions")


def _context_request(pack: dict[str, Any]) -> dict[str, Any]:
    sections = pack.get("sections")
    task_scope = sections.get("Task and Scope") if isinstance(sections, dict) else None
    if not isinstance(task_scope, dict):
        raise VaultClaimReceiptError("context pack Task and Scope section is missing")
    task = task_scope.get("task")
    scope = task_scope.get("scope")
    if not isinstance(task, str) or not task.strip() or not isinstance(scope, dict):
        raise VaultClaimReceiptError("context pack request is missing")
    embedded_request = task_scope.get("request")
    if embedded_request is None:
        return {"task": task, "scope": scope}
    if not isinstance(embedded_request, dict):
        raise VaultClaimReceiptError("context pack embedded request must be an object")
    if embedded_request.get("task") != task or embedded_request.get("scope") != scope:
        raise VaultClaimReceiptError(
            "context pack embedded request does not match Task and Scope"
        )
    return dict(embedded_request)


def _section_list(pack: dict[str, Any], section: str) -> list[dict[str, Any]]:
    sections = pack.get("sections")
    if not isinstance(sections, dict):
        raise VaultClaimReceiptError("context pack sections are missing")
    items = sections.get(section)
    if not isinstance(items, list):
        raise VaultClaimReceiptError(f"{section} must be a list")
    if not all(isinstance(item, dict) for item in items):
        raise VaultClaimReceiptError(f"{section} must contain only objects")
    return items


def _approved_claim_from_records(
    evidence: dict[str, Any],
    decision: dict[str, Any],
    receipt_revision: str,
) -> ApprovedClaim:
    claim_id = _same_required_string(evidence, decision, "claim_id")
    claim_type = str(evidence.get("claim_type") or "").strip()
    selector_id = str(
        evidence.get("selector_id")
        or _derived_selector_id(claim_id, claim_type)
    ).strip()
    assertion = str(evidence.get("assertion") or "").strip()
    if not assertion:
        raise VaultClaimReceiptError("approved claim requires assertion")
    use_mode = _same_use_mode(evidence, decision)
    source_hash = str(evidence.get("source_hash") or "").strip()
    if not re.fullmatch(r"[0-9a-f]{64}", source_hash):
        raise VaultClaimReceiptError("approved claim requires a valid source_hash")
    public_url = str(evidence.get("public_url") or "").strip()
    if not public_url.startswith(("http://", "https://")):
        raise VaultClaimReceiptError("approved claim requires a public URL")
    if source_hash not in {
        str(item).strip()
        for item in (evidence.get("support_resource_hashes") or {}).values()
    }:
        raise VaultClaimReceiptError("approved claim source hash is not in support hashes")
    brand_scope = _same_scope(evidence, decision)
    if brand_scope != [SIMPRO_SCOPE]:
        raise VaultClaimReceiptError(
            "approved claim requires explicit Simpro scope and no other brands"
        )
    if decision.get("approved") is not True:
        raise VaultClaimReceiptError(f"claim decision is not approved: {claim_id}")
    return ApprovedClaim(
        claim_id=claim_id,
        selector_id=selector_id,
        assertion=assertion,
        use_mode=use_mode,
        brand_scope=tuple(brand_scope),
        source_hash=source_hash,
        public_url=public_url,
        approval_source=APPROVAL_SOURCE,
        receipt_revision=receipt_revision,
        claim_type=claim_type,
        authority_resource_id=str(evidence.get("authority_resource_id") or "").strip(),
        evidence_anchor=str(evidence.get("evidence_anchor") or "").strip(),
    )


def _derived_selector_id(claim_id: str, claim_type: str) -> str:
    """Derive only protocol-declared selector IDs from strict claim families."""
    patterns = {
        "fred-authority-joined-v2": r"claim-fred-(FVMI-[A-Za-z0-9._-]+)",
        "lightning-public-product-context-v2": r"claim-lightning-(LCUR-[A-Za-z0-9._-]+)",
    }
    pattern = patterns.get(claim_type)
    if not pattern:
        return ""
    match = re.fullmatch(pattern, claim_id)
    return match.group(1) if match else ""


def _same_required_string(
    evidence: dict[str, Any],
    decision: dict[str, Any],
    field: str,
) -> str:
    evidence_value = str(evidence.get(field) or "").strip()
    decision_value = str(decision.get(field) or "").strip()
    if not evidence_value or not decision_value:
        raise VaultClaimReceiptError(f"approved claim requires {field}")
    if evidence_value != decision_value:
        raise VaultClaimReceiptError(f"claim decision {field} does not match pack evidence")
    return evidence_value


def _same_use_mode(evidence: dict[str, Any], decision: dict[str, Any]) -> str:
    evidence_mode = str(evidence.get("use_mode") or "").strip()
    decision_mode = str(
        decision.get("requested_use_mode") or decision.get("use_mode") or ""
    ).strip()
    if not evidence_mode or not decision_mode:
        raise VaultClaimReceiptError("approved claim requires use mode")
    if evidence_mode != decision_mode:
        raise VaultClaimReceiptError("claim decision use mode does not match pack evidence")
    return evidence_mode


def _same_scope(evidence: dict[str, Any], decision: dict[str, Any]) -> list[str]:
    evidence_scope = _string_list(evidence.get("brand_scope"))
    decision_scope = _string_list(decision.get("brand_scope"))
    if evidence_scope != decision_scope:
        raise VaultClaimReceiptError("claim decision brand scope does not match pack evidence")
    return evidence_scope


def _string_list(value: Any) -> list[str]:
    if isinstance(value, str):
        items = [value]
    elif isinstance(value, list):
        items = value
    else:
        raise VaultClaimReceiptError("brand scope must be a string list")
    normalized = [str(item).strip() for item in items if str(item).strip()]
    if not normalized:
        raise VaultClaimReceiptError("approved claim requires explicit Simpro scope")
    return normalized


def _receipt_revision(receipt: dict[str, Any]) -> str:
    declared = str(receipt.get("receipt_sha256") or "").strip()
    return declared or _sha256_json(receipt)
