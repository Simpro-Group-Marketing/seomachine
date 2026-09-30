"""Snapshot and validate connector-bound customer-proof inputs."""

from __future__ import annotations

import hashlib
import json
import os
from contextlib import contextmanager
from functools import lru_cache
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any, Iterator, Mapping, Optional, Sequence
from urllib.parse import urlsplit, urlunsplit

from ..blog_assembly_contract import validate_governance_output_path
from ..vault_claim_receipts import VaultClaimReceiptError, load_validated_claim_set
from .contracts import (
    CustomerProofDataError,
    FindingDict,
    _ArtifactSnapshot,
    _SelectorInputSnapshot,
)


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
    if not context_pack or not context_receipt:
        pack_path = str(context_pack or "")
        receipt_path = str(context_receipt or "")
        pack_digest = ""
        receipt_digest = ""
    else:
        resolved_pack = Path(context_pack).expanduser().resolve()
        resolved_receipt = Path(context_receipt).expanduser().resolve()
        pack_path = str(resolved_pack)
        receipt_path = str(resolved_receipt)
        try:
            pack_digest = hashlib.sha256(resolved_pack.read_bytes()).hexdigest()
            receipt_digest = hashlib.sha256(resolved_receipt.read_bytes()).hexdigest()
        except OSError as exc:
            raise CustomerProofDataError(
                f"Customer proof context artifact is unreadable: {exc}"
            ) from exc
    return _load_receipt_claims_cached(
        pack_path,
        receipt_path,
        pack_digest,
        receipt_digest,
    )


@lru_cache(maxsize=32)
def _load_receipt_claims_cached(
    context_pack: str,
    context_receipt: str,
    pack_digest: str,
    receipt_digest: str,
) -> Any:
    del pack_digest, receipt_digest
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


def _require_complete_claim_searches(
    context_receipt: Mapping[str, Any],
    use_modes: Sequence[str],
    *,
    claim_lookup: Mapping[str, Any] | None = None,
) -> None:
    required = sorted({str(mode).strip() for mode in use_modes if str(mode).strip()})
    if not required:
        return
    searches = context_receipt.get("claim_searches")
    lookup_searches = _claim_lookup_search_rows(claim_lookup)
    if not isinstance(searches, list) and not lookup_searches:
        raise CustomerProofDataError(
            "Customer proof context receipt lacks claim_searches evidence for "
            f"use modes: {', '.join(required)}"
        )
    search_rows = list(searches) if isinstance(searches, list) else []
    search_rows.extend(lookup_searches)
    for row in search_rows:
        if isinstance(row, Mapping):
            _validate_claim_search_row(
                ", ".join(sorted(_claim_search_use_modes(row))) or "unspecified",
                row,
            )
    missing = []
    for mode in required:
        matches = [
            row
            for row in search_rows
            if isinstance(row, Mapping) and mode in _claim_search_use_modes(row)
        ]
        if not matches:
            missing.append(mode)
            continue
    if missing:
        raise CustomerProofDataError(
            "Customer proof context receipt lacks task-specific claim search "
            f"evidence for use modes: {', '.join(missing)}"
        )


def _claim_lookup_search_rows(claim_lookup: Mapping[str, Any] | None) -> list[Mapping[str, Any]]:
    if not isinstance(claim_lookup, Mapping):
        return []
    if claim_lookup.get("schema") != "simpro-customer-proof-claim-lookup/v1":
        return []
    if str(claim_lookup.get("source") or "").strip() != "SimproVaultClient.claims":
        return []
    rows = claim_lookup.get("lookups")
    if not isinstance(rows, list):
        return []
    normalized: list[Mapping[str, Any]] = []
    for row in rows:
        if not isinstance(row, Mapping):
            continue
        result_count = row.get("result_count")
        if isinstance(result_count, bool) or not isinstance(result_count, int) or result_count < 0:
            continue
        normalized.append(row)
    return normalized


def _claim_search_use_modes(row: Mapping[str, Any]) -> set[str]:
    values: list[Any] = []
    for key in (
        "use_mode",
        "requested_use_mode",
        "requested_use_modes",
        "use_modes",
        "intended_public_use_mode",
    ):
        raw = row.get(key)
        if raw is None:
            continue
        if isinstance(raw, list):
            values.extend(raw)
        else:
            values.append(raw)
    return {str(value).strip() for value in values if str(value).strip()}


def _validate_claim_search_row(mode: str, row: Mapping[str, Any]) -> None:
    if row.get("truncated") is True:
        raise CustomerProofDataError(
            f"Customer proof claim search for {mode} is truncated; rerun vault claim discovery."
        )
    status = str(
        row.get("status")
        or row.get("completion_status")
        or row.get("search_status")
        or "complete"
    ).strip().casefold()
    if status in {"truncated", "incomplete", "partial", "error", "failed", "failure"}:
        raise CustomerProofDataError(
            f"Customer proof claim search for {mode} is not complete: {status}"
        )
    if row.get("complete") is False:
        raise CustomerProofDataError(
            f"Customer proof claim search for {mode} is marked incomplete."
        )


@contextmanager
def _selector_input_snapshot(
    *,
    ledger_path: str | Path,
    context_pack: str | Path | None,
    context_receipt: str | Path | None,
    claim_lookup_evidence: str | Path | None = None,
) -> Iterator[_SelectorInputSnapshot]:
    artifacts = {
        "ledger": _capture_artifact(
            ledger_path,
            "customer proof ledger",
            parse_json_object=True,
        ),
        "context_pack": _capture_artifact(context_pack, "context pack"),
        "context_receipt": _capture_artifact(
            context_receipt,
            "context receipt",
            parse_json_object=True,
        ),
    }
    if claim_lookup_evidence:
        artifacts["claim_lookup"] = _capture_artifact(
            claim_lookup_evidence,
            "customer proof claim lookup evidence",
            parse_json_object=True,
        )
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
        ledger = artifacts["ledger"].json_object
        context_receipt_json = artifacts["context_receipt"].json_object
        claim_lookup_json = (
            artifacts["claim_lookup"].json_object
            if "claim_lookup" in artifacts
            else None
        )
        if ledger is None or context_receipt_json is None:  # pragma: no cover - capture invariant.
            raise CustomerProofDataError("Selector JSON snapshot is unavailable")
        yield _SelectorInputSnapshot(
            artifacts=artifacts,
            ledger=ledger,
            context_pack_path=snapshot_pack,
            context_receipt_path=snapshot_receipt,
            receipt_claims=receipt_claims,
            context_receipt=context_receipt_json,
            claim_lookup=claim_lookup_json,
        )


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


__all__ = [
    '_capture_artifact',
    '_load_json',
    '_load_receipt_claims',
    '_load_receipt_claims_cached',
    '_normalize_public_url',
    '_require_complete_claim_searches',
    '_claim_lookup_search_rows',
    '_claim_search_use_modes',
    '_selector_input_snapshot',
    '_selector_artifacts_unchanged',
    '_raise_if_selector_inputs_changed',
    '_paths_alias',
    '_validate_evidence_output_paths'
]
