"""Snapshot and validate connector-bound customer-proof inputs."""

from __future__ import annotations

import hashlib
import json
import os
from contextlib import contextmanager
from functools import lru_cache
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any, Iterable, Iterator, Mapping, Optional, Sequence
from urllib.parse import urlsplit, urlunsplit

from ..blog_assembly_contract import validate_governance_output_path
from ..vault_claim_receipts import VaultClaimReceiptError, load_validated_claim_set
from .contracts import (
    CUSTOMER_PROOF_USE_MODES,
    CustomerProofDataError,
    FindingDict,
    _ApprovedClaimBinding,
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
    matches = [
        claim
        for claim in approved_claims
        if not str(getattr(claim, "selector_id", "") or "").strip()
        and str(getattr(claim, "use_mode", "") or "") in use_modes
        and _normalize_public_url(getattr(claim, "public_url", "")) == normalized_url
    ]
    if not matches:
        return None
    inventory_matches = sorted(set(_inventory_url_map(proof_rows).get(normalized_url, [])))
    if len(inventory_matches) > 1:
        raise CustomerProofDataError(
            "Customer proof public URL binding is ambiguous for "
            f"{normalized_url}: {', '.join(inventory_matches)}"
        )
    if len(matches) > 1:
        claim_ids = ", ".join(sorted(str(claim.claim_id) for claim in matches))
        raise CustomerProofDataError(
            "Customer proof approved claim public URL binding is ambiguous for "
            f"{normalized_url}: {claim_ids}"
        )
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
    '_inventory_url_map',
    '_public_url_binding',
    '_claim_binding_for_candidate',
    '_has_inventory_bound_claim',
    '_selector_input_snapshot',
    '_selector_artifacts_unchanged',
    '_raise_if_selector_inputs_changed',
    '_paths_alias',
    '_validate_evidence_output_paths'
]
