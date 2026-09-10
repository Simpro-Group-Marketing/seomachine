"""Classification responsibilities."""
# ruff: noqa: F403, F405

from .common import *  # noqa: F403


def _load_classification_payload(
    proof: ProofEntry,
    candidate: ClaimCandidate,
    base_path: Path,
) -> tuple[dict | None, Path | None, Optional[Finding]]:
    if not proof.classification_artifact or not proof.classification_hash:
        return None, None, _finding(
            "source_classification_artifact_missing", candidate,
            "General claim Source class must be bound to a registry-emitted classification artifact.",
            "Add Classification artifact and Classification hash from a source_registry_export record.", proof,
        )
    path = _resolve_local_artifact(
        proof.classification_artifact, base_path, JSON_ARTIFACT_EXTENSION_RE
    )
    if path is None:
        return None, None, _finding(
            "source_classification_artifact_missing", candidate,
            "The declared source-classification artifact is missing or is not JSON.",
            "Use an existing registry-emitted JSON classification artifact.", proof,
        )
    if not SHA256_RE.fullmatch(proof.classification_hash):
        return None, None, _finding(
            "source_classification_hash_invalid", candidate,
            "Classification hash must be a 64-character lowercase SHA-256.",
            "Record the exact SHA-256 of the classification artifact.", proof,
        )
    try:
        snapshot = load_json_object_snapshot(path, field="source classification artifact")
    except ValueError:
        snapshot = None
    if snapshot is None or snapshot.sha256 != proof.classification_hash:
        return None, None, _finding(
            "source_classification_hash_mismatch", candidate,
            "The source-classification artifact hash does not match the Source Map binding.",
            "Regenerate the classification binding from the unchanged registry artifact.", proof,
        )
    payload = snapshot.payload
    if not isinstance(payload, dict):
        return None, None, _finding(
            "source_classification_artifact_invalid", candidate,
            "The source-classification artifact does not satisfy simpro-source-classification/v1.",
            "Regenerate it with source_registry_export; do not hand-label the source class.", proof,
        )
    return payload, path, None


def _validate_source_classification(
    proof: ProofEntry,
    candidate: ClaimCandidate,
    base_path: Path,
) -> Optional[Finding]:
    payload, classification_path, finding = _load_classification_payload(
        proof, candidate, base_path
    )
    if finding is not None:
        return finding
    assert payload is not None and classification_path is not None
    if not verify_mapping_attestation(
        payload,
        purpose=SOURCE_CLASSIFICATION_ATTESTATION_PURPOSE,
        workspace_root=_attestation_workspace_root(base_path),
    ):
        return _finding(
            "source_classification_execution_attestation_invalid",
            candidate,
            "The source-classification artifact lacks a valid workspace execution attestation.",
            "Regenerate it with write_source_classification_artifact in this workspace.",
            proof,
        )
    if not _is_strict_classification_payload(payload):
        return _finding(
            "source_classification_artifact_invalid",
            candidate,
            "The source-classification artifact does not satisfy simpro-source-classification/v1.",
            "Regenerate it with source_registry_export; do not hand-label the source class.",
            proof,
        )
    if payload["source_url"] != proof.url or payload["source_class"] != proof.source_class:
        return _finding(
            "source_classification_mismatch",
            candidate,
            "The declared Source class or URL does not match the registry classification artifact.",
            "Use the registry-declared class for this exact URL.",
            proof,
        )
    hostname = (urlsplit(proof.url).hostname or "").lower()
    publisher = payload["publisher"]
    if publisher["hostname"].lower() != hostname:
        return _finding(
            "source_classification_hostname_mismatch",
            candidate,
            "The registry classification hostname does not match the cited URL.",
            "Regenerate classification metadata for the exact cited URL.",
            proof,
        )
    relationship = publisher["relationship"]
    if relationship not in SOURCE_CLASS_RELATIONSHIPS[proof.source_class]:
        return _finding(
            "source_classification_relationship_mismatch",
            candidate,
            "The publisher relationship cannot support the declared Source class.",
            "Use the registry-declared ownership or competitor relationship.",
            proof,
        )
    if (hostname == "simprogroup.com" or hostname.endswith(".simprogroup.com")) and proof.source_class != "owned_product":
        return _finding(
            "source_classification_owned_domain_mismatch",
            candidate,
            "A Simpro-owned hostname cannot be classified as an independent or competitor source.",
            "Use Source class: owned_product for Simpro-owned product facts.",
            proof,
        )
    decision_finding = _validate_classification_decision(
        payload,
        classification_path=classification_path,
        base_path=base_path,
    )
    if decision_finding is not None:
        return _finding(
            decision_finding,
            candidate,
            "The source classification no longer matches its approved repository decision.",
            "Regenerate classification from the current approved decision registry.",
            proof,
        )
    return None

def validate_source_classification_binding(
    *,
    source_url: str,
    source_class: str,
    classification_artifact: str,
    classification_hash: str,
    base_path: str | Path,
) -> str | None:
    """Return the strict classification rule ID for another proof guard.

    This reuses the same repository-decision, Git HEAD, hash, and local
    execution-attestation checks as Source Map validation without trusting a
    second sidecar classification surface.
    """
    candidate = ClaimCandidate(
        text="classification binding",
        line=1,
        numeric_tokens=[],
        normalized_tokens=frozenset(),
        customer_names=frozenset(),
        has_case_study_link=False,
        requires_approved_quote=False,
        claim_type="factual",
    )
    proof = ProofEntry(
        kind="claim",
        claim="classification binding",
        url=source_url,
        evidence="classification binding",
        status="approved",
        line=1,
        section="faq proof map",
        source_class=source_class,
        claim_type="factual",
        evidence_relation="directly_supports",
        classification_artifact=classification_artifact,
        classification_hash=classification_hash,
    )
    finding = _validate_source_classification(proof, candidate, Path(base_path))
    return str(finding["rule_id"]) if finding is not None else None

def _validate_classification_decision(
    payload: dict,
    *,
    classification_path: Path,
    base_path: Path,
) -> str | None:
    registry = payload.get("registry")
    if not isinstance(registry, dict) or registry.get("authority_mode") != "repository_decision":
        return "source_classification_authority_unsupported"
    workspace_root = _attestation_workspace_root(base_path)
    try:
        decision_path = resolve_artifact(
            registry.get("decision_path"),
            workspace_root=workspace_root,
        )
        snapshot = load_json_object_snapshot(
            decision_path,
            field="source classification decision registry",
        )
    except ValueError:
        return "source_classification_decision_missing"
    if snapshot.sha256 != registry.get("decision_sha256"):
        return "source_classification_decision_tampered"
    if registry.get("decision_path") != SOURCE_DECISIONS_PATH:
        return "source_classification_authority_unsupported"
    try:
        _require_registry_matches_committed_head(
            snapshot,
            workspace_root=workspace_root,
        )
    except ValueError:
        return "source_classification_decision_tampered"
    decision_registry = snapshot.payload
    if (
        set(decision_registry) != {"schema", "revision", "decisions"}
        or decision_registry.get("schema") != SOURCE_DECISIONS_SCHEMA
        or decision_registry.get("revision") != registry.get("revision")
        or not isinstance(decision_registry.get("decisions"), list)
    ):
        return "source_classification_decision_revision_mismatch"
    matches = [
        row for row in decision_registry["decisions"]
        if isinstance(row, dict) and row.get("decision_id") == registry.get("record_id")
    ]
    if len(matches) != 1 or set(matches[0]) != SOURCE_DECISION_FIELDS:
        return "source_classification_decision_missing"
    decision = matches[0]
    expected = {
        "status": "approved",
        "source_url": payload.get("source_url"),
        "hostname": payload.get("publisher", {}).get("hostname"),
        "source_class": payload.get("source_class"),
        "publisher_relationship": payload.get("publisher", {}).get("relationship"),
    }
    if any(decision.get(key) != value for key, value in expected.items()):
        return "source_classification_decision_mismatch"
    return None

def _require_registry_matches_committed_head(
    snapshot: object,
    *,
    workspace_root: str | Path,
) -> None:
    """Require canonical registry bytes to equal the Git-tracked HEAD blob."""
    root = Path(workspace_root).resolve()
    path = getattr(snapshot, "path", None)
    data = getattr(snapshot, "data", None)
    if not isinstance(path, Path) or not isinstance(data, bytes):
        raise ValueError("source decision registry snapshot is invalid")
    expected_path = (root / SOURCE_DECISIONS_PATH).resolve()
    if path != expected_path:
        raise ValueError(
            f"source classification decisions must use {SOURCE_DECISIONS_PATH}"
        )
    try:
        top = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "--show-toplevel"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            timeout=10,
        )
        blob = subprocess.run(
            ["git", "-C", str(root), "show", f"HEAD:{SOURCE_DECISIONS_PATH}"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError) as error:
        raise ValueError(
            "source classification registry must match its committed HEAD blob"
        ) from error
    try:
        top_path = Path(top.stdout.decode("utf-8").strip()).resolve()
    except (UnicodeDecodeError, OSError):
        top_path = Path()
    if top.returncode != 0 or top_path != root or blob.returncode != 0 or blob.stdout != data:
        raise ValueError(
            "source classification registry must match its committed HEAD blob"
        )


__all__ = [
    "_validate_source_classification", "validate_source_classification_binding",
    "_validate_classification_decision", "_require_registry_matches_committed_head",
]
