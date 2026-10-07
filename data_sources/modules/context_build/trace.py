"""Compact, hash-stable summaries of vault calls for the context build trace."""

from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping

TRACE_SCHEMA = "simpro-context-build-trace/v1"
_READ_KEYS = (
    "resource_id", "title", "locator", "content_sha256", "read_purpose", "retrieval_tier",
    "authority_state", "public_claim_use", "content_truncated", "revisions",
)
_CLAIM_KEYS = (
    "claim_id", "assertion", "permitted_use_modes", "public_url", "source_collection",
    "customer_or_company", "identity", "approval_status", "source_hash",
)


def resource_ids(value: Any) -> set[str]:
    """Collect every resource_id string nested anywhere in a search or expand result."""
    found: set[str] = set()
    if isinstance(value, dict):
        rid = value.get("resource_id")
        if isinstance(rid, str):
            found.add(rid)
        for child in value.values():
            found.update(resource_ids(child))
    elif isinstance(value, list):
        for child in value:
            found.update(resource_ids(child))
    return found


def compact_search(rows: Any) -> dict[str, Any]:
    ids = [row.get("resource_id") for row in rows if isinstance(row, dict)] if isinstance(rows, list) else []
    digest = hashlib.sha256(json.dumps(rows, sort_keys=True, ensure_ascii=False).encode("utf-8"))
    return {"result_resource_ids": ids, "results_sha256": digest.hexdigest()}


def compact_expansion(rows: Any) -> dict[str, Any]:
    return compact_search([{"resource_id": rid} for rid in sorted(resource_ids(rows))])


def compact_read(read: Any) -> dict[str, Any]:
    if not isinstance(read, dict):
        return {}
    return {key: read.get(key) for key in _READ_KEYS if key in read}


def compact_claims(rows: Any) -> list[dict[str, Any]]:
    if not isinstance(rows, list):
        return []
    return [{key: row.get(key) for key in _CLAIM_KEYS if key in row} for row in rows if isinstance(row, dict)]


def compact_receipt(receipt: Mapping[str, Any]) -> dict[str, Any]:
    decisions = receipt.get("claim_decisions") or []
    return {
        "pack_sha256": receipt.get("pack_sha256"),
        "receipt_sha256": receipt.get("receipt_sha256"),
        "request_sha256": receipt.get("request_sha256"),
        "revisions": receipt.get("revisions"),
        "claim_decision_ids": [d.get("claim_id") for d in decisions if isinstance(d, dict)],
        "note": "Full pack and receipt are written to their own research files.",
    }
