"""Persistence responsibilities."""
# ruff: noqa: F403, F405

from .common import *  # noqa: F403


def _load_decision_registry(
    decision_path: str | Path,
    *,
    workspace_root: Path,
) -> tuple[Any, dict, str]:
    snapshot = load_json_object_snapshot(
        decision_path, field="source classification decision registry"
    )
    _require_registry_matches_committed_head(snapshot, workspace_root=workspace_root)
    registry = snapshot.payload
    if set(registry) != {"schema", "revision", "decisions"}:
        raise ValueError("source classification decision registry shape is invalid")
    if registry.get("schema") != SOURCE_DECISIONS_SCHEMA:
        raise ValueError("source classification decision registry schema is invalid")
    revision = _required_emitter_text(registry.get("revision"), "decision revision")
    if not isinstance(registry.get("decisions"), list):
        raise ValueError("source classification decisions must be a list")
    return snapshot, registry, revision


def _select_approved_decision(
    decisions: Sequence[Any],
    *,
    decision_id: str,
    source_url: str,
    hostname: str,
) -> tuple[str, str]:
    matches = [
        row for row in decisions
        if isinstance(row, dict) and row.get("decision_id") == decision_id
    ]
    if len(matches) != 1 or set(matches[0]) != SOURCE_DECISION_FIELDS:
        raise ValueError("source classification decision must resolve exactly once")
    decision = matches[0]
    expected = {
        "status": "approved",
        "source_url": source_url,
        "hostname": hostname,
    }
    mismatches = {
        key for key, value in expected.items() if decision.get(key) != value
    }
    if "status" in mismatches:
        raise ValueError("source classification decision is not approved")
    if "source_url" in mismatches:
        raise ValueError("source classification decision URL does not match")
    if "hostname" in mismatches:
        raise ValueError("source classification decision hostname does not match")
    source_class = decision.get("source_class")
    relationship = decision.get("publisher_relationship")
    if source_class not in SOURCE_CLASSES:
        raise ValueError("approved decision source_class is invalid")
    if relationship not in SOURCE_CLASS_RELATIONSHIPS[source_class]:
        raise ValueError("approved decision publisher relationship is invalid")
    return source_class, relationship


def write_source_classification_artifact(
    path: str | Path,
    *,
    source_url: str,
    decision_id: str,
    decision_path: str | Path,
    workspace_root: str | Path | None = None,
) -> dict:
    """Emit classification derived from one approved repository decision row."""
    if workspace_root is None:
        raise ValueError("workspace_root is required for source classification")
    root = Path(workspace_root).resolve()
    normalized_url = _required_emitter_text(source_url, "source_url")
    hostname = (urlsplit(normalized_url).hostname or "").lower()
    if not hostname:
        raise ValueError("source_url must contain a hostname")
    normalized_decision_id = _required_emitter_text(decision_id, "decision_id")
    snapshot, registry, revision = _load_decision_registry(
        decision_path, workspace_root=root
    )
    source_class, publisher_relationship = _select_approved_decision(
        registry["decisions"],
        decision_id=normalized_decision_id,
        source_url=normalized_url,
        hostname=hostname,
    )
    decision_binding = canonical_snapshot_artifact(snapshot, workspace_root=root)
    if decision_binding["path"] != SOURCE_DECISIONS_PATH:
        raise ValueError(
            f"source classification decisions must use {SOURCE_DECISIONS_PATH}"
        )
    payload = {
        "schema": SOURCE_CLASSIFICATION_SCHEMA,
        "source_url": normalized_url,
        "source_class": source_class,
        "classified_at": _utc_timestamp_now(),
        "publisher": {
            "hostname": hostname,
            "relationship": publisher_relationship,
        },
        "registry": {
            "authority_mode": "repository_decision",
            "record_id": normalized_decision_id,
            "revision": revision,
            "decision_path": decision_binding["path"],
            "decision_sha256": decision_binding["sha256"],
        },
        "emitter": {
            "name": SOURCE_CLASSIFICATION_EMITTER,
            "version": SOURCE_CLASSIFICATION_EMITTER_VERSION,
        },
    }
    attested = attest_mapping(
        payload,
        purpose=SOURCE_CLASSIFICATION_ATTESTATION_PURPOSE,
        workspace_root=workspace_root,
    )
    if not _is_strict_classification_payload(attested):
        raise ValueError("generated source classification does not satisfy the v1 contract")
    atomic_write_json(path, attested)
    return attested


__all__ = ["write_source_classification_artifact", "write_source_capture_receipt"]

def write_source_capture_receipt(
    path: str | Path,
    *,
    source_url: str,
    source_content_path: str | Path,
    artifact_path: str | Path,
    artifact_reference: str,
    method: str,
    workspace_root: str | Path | None = None,
) -> dict:
    """Atomically emit one workspace-attested source capture receipt."""
    normalized_url = _required_emitter_text(source_url, "source_url")
    if not (urlsplit(normalized_url).hostname or ""):
        raise ValueError("source_url must contain a hostname")
    if method not in {"html_visible_text", "pdf_text"}:
        raise ValueError("method must be html_visible_text or pdf_text")

    captured_source = Path(source_content_path)
    extracted_artifact = Path(artifact_path)
    if not captured_source.is_file():
        raise ValueError("source_content_path must identify an existing file")
    if not extracted_artifact.is_file():
        raise ValueError("artifact_path must identify an existing file")

    source_content_hash = _sha256_file(captured_source)
    artifact_hash = _sha256_file(extracted_artifact)
    payload = {
        "schema": SOURCE_CAPTURE_SCHEMA,
        "source_url": normalized_url,
        "retrieved_at": _utc_timestamp_now(),
        "source_content_sha256": source_content_hash,
        "artifact": {
            "path": _required_emitter_text(
                artifact_reference,
                "artifact_reference",
            ),
            "sha256": artifact_hash,
        },
        "extraction": {
            "method": method,
            "tool_name": SOURCE_CAPTURE_EMITTER,
            "tool_version": SOURCE_CAPTURE_EMITTER_VERSION,
            "input_sha256": source_content_hash,
            "output_sha256": artifact_hash,
        },
        "emitter": {
            "name": SOURCE_CAPTURE_EMITTER,
            "version": SOURCE_CAPTURE_EMITTER_VERSION,
        },
    }
    attested = attest_mapping(
        payload,
        purpose=SOURCE_CAPTURE_ATTESTATION_PURPOSE,
        workspace_root=workspace_root,
    )
    if not _is_strict_capture_payload(attested):
        raise ValueError("generated source capture receipt does not satisfy the v1 contract")
    atomic_write_json(path, attested)
    return attested
