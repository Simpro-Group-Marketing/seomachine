"""Capture Receipts responsibilities."""
# ruff: noqa: F403, F405

from .common import *  # noqa: F403


def _capture_receipt_payload(
    proof: ProofEntry,
    candidate: ClaimCandidate,
    base_path: Path,
) -> tuple[dict | None, Path | None, Optional[Finding]]:
    if not proof.capture_receipt or not proof.capture_receipt_hash:
        return None, None, _finding(
            "source_capture_receipt_missing", candidate,
            "A local fallback is not evidence unless a tool-emitted capture receipt binds it to the cited source.",
            "Capture or extract the source with source_support_capture and bind its receipt and SHA-256.", proof,
        )
    receipt_path = _resolve_local_artifact(
        proof.capture_receipt, base_path, JSON_ARTIFACT_EXTENSION_RE
    )
    if receipt_path is None:
        return None, None, _finding(
            "source_capture_receipt_missing", candidate,
            "The declared source-capture receipt is missing or is not JSON.",
            "Use the JSON receipt emitted for this exact captured source.", proof,
        )
    if not SHA256_RE.fullmatch(proof.capture_receipt_hash):
        return None, None, _finding(
            "source_capture_receipt_hash_invalid", candidate,
            "Capture receipt hash must be a 64-character lowercase SHA-256.",
            "Record the exact SHA-256 of the capture receipt.", proof,
        )
    if _sha256_file(receipt_path) != proof.capture_receipt_hash:
        return None, None, _finding(
            "source_capture_receipt_hash_mismatch", candidate,
            "The capture receipt hash does not match its Source Map binding.",
            "Regenerate the receipt binding from the unchanged capture output.", proof,
        )
    payload = _read_json_object(receipt_path)
    if payload is None:
        return None, None, _finding(
            "source_capture_receipt_invalid", candidate,
            "The capture receipt does not satisfy simpro-source-capture-receipt/v1.",
            "Regenerate the capture and receipt with source_support_capture.", proof,
        )
    return payload, receipt_path, None


def _validate_capture_receipt(
    proof: ProofEntry,
    candidate: ClaimCandidate,
    base_path: Path,
    *,
    expected_method: str,
) -> Optional[Finding]:
    payload, receipt_path, finding = _capture_receipt_payload(proof, candidate, base_path)
    if finding is not None:
        return finding
    assert payload is not None and receipt_path is not None
    if not verify_mapping_attestation(
        payload,
        purpose=SOURCE_CAPTURE_ATTESTATION_PURPOSE,
        workspace_root=_attestation_workspace_root(base_path),
    ):
        return _finding(
            "source_capture_execution_attestation_invalid",
            candidate,
            "The source-capture receipt lacks a valid workspace execution attestation.",
            "Regenerate it with write_source_capture_receipt in this workspace.",
            proof,
        )
    artifact_path = _resolve_local_artifact(
        proof.artifact,
        base_path,
        LOCAL_ARTIFACT_EXTENSION_RE,
    )
    if artifact_path is None or not _is_strict_capture_payload(payload):
        return _finding(
            "source_capture_receipt_invalid",
            candidate,
            "The capture receipt does not satisfy simpro-source-capture-receipt/v1.",
            "Regenerate the capture and receipt with source_support_capture.",
            proof,
        )
    artifact = payload["artifact"]
    extraction = payload["extraction"]
    if payload["source_url"] != proof.url or artifact["path"] != proof.artifact:
        return _finding(
            "source_capture_binding_mismatch",
            candidate,
            "The capture receipt does not bind the cited URL and declared local artifact.",
            "Use the receipt emitted for this exact URL and artifact path.",
            proof,
        )
    artifact_hash = _sha256_file(artifact_path)
    if artifact_hash != artifact["sha256"] or artifact_hash != extraction["output_sha256"]:
        return _finding(
            "source_capture_artifact_hash_mismatch",
            candidate,
            "The local source artifact changed after capture or extraction.",
            "Recapture the source and regenerate the receipt before using the evidence.",
            proof,
        )
    if extraction["input_sha256"] != payload["source_content_sha256"]:
        return _finding(
            "source_capture_input_hash_mismatch",
            candidate,
            "The extraction input hash does not match the captured source-content hash.",
            "Regenerate the tool-emitted capture receipt.",
            proof,
        )
    if extraction["method"] != expected_method:
        return _finding(
            "source_capture_method_mismatch",
            candidate,
            "The capture extraction method does not fit the cited source type.",
            f"Use extraction method {expected_method} for this source.",
            proof,
        )
    return None


__all__ = ["_validate_capture_receipt"]
