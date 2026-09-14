"""AnswerSocrates receipt and raw-capture validation."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..blog_assembly_contract import (
    canonical_json_sha256,
    load_json_object_snapshot,
    resolve_artifact,
)
from ..execution_attestation import verify_mapping_attestation
from . import snapshot_validation
from .contracts import (
    ANSWERSOCRATES_CAPTURE_CONTRACTS,
    ANSWERSOCRATES_CHROME_CONNECTOR_TOOL,
    ANSWERSOCRATES_RAW_CAPTURE_FIELDS,
    ANSWERSOCRATES_RECEIPT_ATTESTATION_PURPOSE,
    ANSWERSOCRATES_RECEIPT_SCHEMA,
    ANSWERSOCRATES_TOOL,
)


def _parse_utc_timestamp(value: object) -> datetime | None:
    if not isinstance(value, str) or not value.endswith("Z"):
        return None
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError:
        return None
    if parsed.tzinfo is None or parsed.utcoffset() != timezone.utc.utcoffset(parsed):
        return None
    return parsed


def _valid_answersocrates_receipt(value: object, *, payload: dict) -> bool:
    required_fields = {
        "schema",
        "run_id",
        "tool",
        "started_at",
        "completed_at",
        "status",
        "payload_sha256",
        "raw_capture",
        "execution_attestation",
        "receipt_hash",
    }
    if not isinstance(value, dict) or set(value) != required_fields:
        return False
    if value.get("tool") not in (
        ANSWERSOCRATES_TOOL,
        ANSWERSOCRATES_CHROME_CONNECTOR_TOOL,
    ):
        return False
    started = _parse_utc_timestamp(value.get("started_at"))
    completed = _parse_utc_timestamp(value.get("completed_at"))
    if started is None or completed is None or completed <= started:
        return False
    if not _receipt_payload_matches(value, payload):
        return False
    receipt_without_hash = dict(value)
    stored_hash = receipt_without_hash.pop("receipt_hash", None)
    hash_valid = (
        isinstance(stored_hash, str)
        and re.fullmatch("[0-9a-f]{64}", stored_hash) is not None
        and stored_hash == canonical_json_sha256(receipt_without_hash)
    )
    return hash_valid and verify_mapping_attestation(
        value,
        purpose=ANSWERSOCRATES_RECEIPT_ATTESTATION_PURPOSE,
        excluded_fields=("receipt_hash",),
    )


def _receipt_payload_matches(receipt: dict, payload: dict) -> bool:
    return bool(
        receipt.get("schema") == ANSWERSOCRATES_RECEIPT_SCHEMA
        and isinstance(receipt.get("run_id"), str)
        and str(receipt.get("run_id")).strip()
        and receipt.get("status") == payload.get("status")
        and receipt.get("payload_sha256") == canonical_json_sha256(payload)
        and receipt.get("raw_capture") == payload.get("raw_capture")
    )


def _valid_raw_capture_binding(
    binding: object,
    *,
    workspace_root: str | Path | None,
    expected_query: object,
    expected_run_id: object,
    expected_collection_date: object,
    expected_questions: object,
    expected_fragments: object,
    expected_blocker: object,
    raw_capture_snapshot: Any = None,
) -> bool:
    from .collection import _derive_answersocrates_observations

    return snapshot_validation.valid_raw_capture_binding(
        binding,
        workspace_root=workspace_root,
        expected_query=expected_query,
        expected_run_id=expected_run_id,
        expected_collection_date=expected_collection_date,
        expected_questions=expected_questions,
        expected_fragments=expected_fragments,
        expected_blocker=expected_blocker,
        raw_capture_snapshot=raw_capture_snapshot,
        capture_contracts=ANSWERSOCRATES_CAPTURE_CONTRACTS,
        raw_capture_fields=ANSWERSOCRATES_RAW_CAPTURE_FIELDS,
        resolve_artifact_fn=resolve_artifact,
        load_snapshot_fn=load_json_object_snapshot,
        verify_attestation_fn=verify_mapping_attestation,
        parse_timestamp_fn=_parse_utc_timestamp,
        derive_observations_fn=_derive_answersocrates_observations,
    )


__all__ = [
    "_parse_utc_timestamp",
    "_valid_answersocrates_receipt",
    "_valid_raw_capture_binding",
]
