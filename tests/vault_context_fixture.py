"""Connector-faithful context pack fixtures for proof workflow tests."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any, Iterable, Mapping

from data_sources.modules.vault_claim_receipts import load_validated_claim_set


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _sha256_json(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def write_connector_context_fixture(
    root: Path,
    evidence_rows: Iterable[Mapping[str, Any]],
) -> tuple[Path, Path]:
    request = {
        "task": "Validate proof selector fixture claims.",
        "scope": {
            "artifact_type": "blog",
            "brand": "Simpro",
            "title": "Proof selector fixture",
            "objective": "Exercise receipt-bound proof selection.",
            "audience": "field service leaders",
            "region": "US",
            "intended_public_use_modes": [
                "authority_support",
                "exact_quote",
                "public_metric",
                "public_paraphrase",
            ],
        },
    }
    revisions = {
        "content_revision": "content-1",
        "contract_revision": "contract-1",
        "inventory_revision": "inventory-1",
        "manifest_revision": "manifest-1",
        "claim_registry_revision": "claims-1",
        "approval_policy_revision": "policy-1",
    }
    normalized_evidence: list[dict[str, Any]] = []
    decisions: list[dict[str, Any]] = []
    for source in evidence_rows:
        claim_id = str(source.get("claim_id") or "").strip()
        if not claim_id:
            continue
        original_hash = str(source.get("source_hash") or "")
        source_hash = (
            original_hash
            if re.fullmatch(r"[0-9a-f]{64}", original_hash)
            else hashlib.sha256(original_hash.encode("utf-8")).hexdigest()
        )
        brand_value = source.get("brand_scope")
        if isinstance(brand_value, list):
            brand_scope = str(brand_value[0]) if brand_value else ""
        else:
            brand_scope = str(brand_value or "")
        use_mode = str(source.get("use_mode") or "").strip()
        resource_id = f"res-{hashlib.sha256(claim_id.encode('utf-8')).hexdigest()[:32]}"
        evidence = {
            "claim_id": claim_id,
            "assertion": str(source.get("assertion") or claim_id),
            "claim_type": str(
                source.get("claim_type") or "test-connector-approved-claim"
            ),
            "authority_resource_id": resource_id,
            "evidence_anchor": f"fixture#{claim_id}",
            "public_url": str(source.get("public_url") or ""),
            "source_hash": source_hash,
            "support_resource_ids": [resource_id],
            "support_resource_hashes": {resource_id: source_hash},
            "use_mode": use_mode,
            "brand_scope": brand_scope,
            "authority_date": "2026-08-10",
        }
        selector_id = str(source.get("selector_id") or "").strip()
        if selector_id:
            evidence["selector_id"] = selector_id
        normalized_evidence.append(evidence)
        decisions.append(
            {
                "claim_id": claim_id,
                "query": "proof selector fixture",
                "approved": True,
                "use_mode": use_mode,
                "brand_scope": brand_scope,
                "authority_date": "2026-08-10",
            }
        )
    pack = {
        "schema": "simpro-product-context-pack/v2",
        "revisions": revisions,
        "claim_registry_revision": "claims-1",
        "sections": {
            "Task and Scope": {
                "request": request,
                "task": request["task"],
                "scope": request["scope"],
                "task_satisfaction": "satisfied",
            },
            "Discovery Trace": {
                "entries": [],
                "selected_resource_ids": [],
                "selected_resource_purposes": {},
            },
            "Retrieved Guidance": [],
            "Approved Claim Evidence": normalized_evidence,
            "Constraints and Unresolved Gaps": {
                "constraints": [],
                "unresolved_gaps": [],
            },
            "Selected Resource Inventory": [],
        },
    }
    receipt = {
        "schema": "simpro-context-receipt/v1",
        "request_sha256": _sha256_json(request),
        "pack_sha256": _sha256_json(pack),
        "revisions": revisions,
        "claim_registry_revision": "claims-1",
        "resources": [],
        "resource_purposes": {},
        "claim_decisions": decisions,
        "search_queries": ["proof selector fixture"],
        "discovery_trace": [],
        "constraints": [],
        "unresolved_gaps": [],
        "task_satisfaction": "satisfied",
        "validation_time": "2026-08-10T12:00:00Z",
        "errors": [],
    }
    receipt["receipt_sha256"] = _sha256_json(receipt)
    pack_path = root / "context-pack.json"
    receipt_path = root / "context-receipt.json"
    pack_path.write_text(json.dumps(pack, indent=2), encoding="utf-8")
    receipt_path.write_text(json.dumps(receipt, indent=2), encoding="utf-8")
    return pack_path, receipt_path


class AcceptingContextClient:
    """Test double for the connector's already-covered live validator boundary."""

    def validate_context(self, request, pack, receipt):
        return {"valid": True, "errors": []}


def load_validated_claim_set_for_unit_test(
    context_pack,
    context_receipt,
    *,
    vault_root=None,
    client=None,
):
    """Validate canonical fixtures without crossing the live connector boundary."""
    return load_validated_claim_set(
        context_pack,
        context_receipt,
        vault_root=vault_root,
        client=AcceptingContextClient(),
    )
