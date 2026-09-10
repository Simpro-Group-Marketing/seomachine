"""Preflight responsibilities."""
# ruff: noqa: F403, F405

from .common import *  # noqa: F403


def _validate_preflight_metadata(readiness: Mapping[str, Any]) -> None:
    expected = {
        "schema": READINESS_SCHEMA,
        "phase": "preflight",
        "passed": True,
        "verification_scope": "source_artifact",
        "input_seal": {"status": "verified"},
        "artifact_kind": "blog",
    }
    messages = {
        "schema": f"preflight readiness must use {READINESS_SCHEMA}",
        "phase": "preflight readiness phase must be preflight",
        "passed": "failed preflight cannot finalize a BOM",
        "verification_scope": "preflight verification_scope must be source_artifact",
        "input_seal": "preflight readiness input seal is not verified",
        "artifact_kind": "preflight readiness artifact_kind must be blog",
    }
    for field, value in expected.items():
        if readiness.get(field) != value:
            raise ValueError(messages[field])
    tool = _required_mapping(readiness.get("tool"), "preflight_readiness.tool")
    if tool != {"name": "publish_readiness", "version": "1.0.0"}:
        raise ValueError("preflight readiness tool/version is invalid")


def _validate_preflight_gates(
    readiness: Mapping[str, Any],
    bom: Mapping[str, Any],
) -> None:
    schema_policy = _required_mapping(bom.get("schema_policy"), "bom.schema_policy")
    connector = _required_mapping(bom.get("connector_binding"), "bom.connector_binding")
    expected = expected_blog_gate_inventory(
        visible_faq=schema_policy.get("visible_faq") is True,
        connector_required=connector.get("status") == "required",
    )
    if readiness.get("gate_inventory") != expected:
        raise ValueError("preflight readiness gate inventory is not the exact expected inventory")
    gates = readiness.get("gates")
    if not isinstance(gates, list) or len(gates) != len(expected):
        raise ValueError("preflight readiness gate results are incomplete")
    for index, (gate, expected_name) in enumerate(zip(gates, expected)):
        if not isinstance(gate, Mapping):
            raise ValueError(f"preflight readiness gate result {index} must be an object")
        if gate.get("name") != expected_name or gate.get("passed") is not True:
            raise ValueError(
                f"preflight readiness gate result {expected_name} is not a passed tool result"
            )
        if gate.get("errors") != 0 or gate.get("blockers") not in ([], ()):
            raise ValueError(
                f"preflight readiness gate result {expected_name} contains blockers"
            )


def _validate_preflight_scores(readiness: Mapping[str, Any]) -> None:
    score = readiness.get("score")
    threshold = readiness.get("score_threshold")
    if not _is_number(score) or threshold != 85 or score < threshold:
        raise ValueError("preflight readiness content score did not pass 85")
    aeo_geo = _required_mapping(readiness.get("aeo_geo"), "preflight_readiness.aeo_geo")
    passed = (
        aeo_geo.get("passed") is True
        and aeo_geo.get("threshold") == 90
        and _is_number(aeo_geo.get("score"))
        and aeo_geo["score"] >= 90
    )
    if not passed:
        raise ValueError("preflight readiness AEO/GEO score did not pass 90")


def _validate_preflight_inputs(
    readiness: Mapping[str, Any],
    bom: Mapping[str, Any],
    *,
    bom_path: Path,
    workspace_root: Path,
) -> None:
    inputs = _required_mapping(readiness.get("input_hashes"), "preflight_readiness.input_hashes")
    bom_input = _required_mapping(inputs.get("assembly_bom"), "input_hashes.assembly_bom")
    expected_bom = canonical_artifact(bom_path, workspace_root=workspace_root)
    if dict(bom_input) != expected_bom:
        raise ValueError("preflight input hash mismatch: assembly_bom")
    declared = readiness.get("assembly_bom")
    if not isinstance(declared, str) or not declared:
        raise ValueError("preflight readiness assembly_bom path is missing")
    try:
        candidate = Path(declared)
        if not candidate.is_absolute():
            candidate = resolve_artifact(declared, workspace_root=workspace_root)
        identity = canonical_artifact(candidate, workspace_root=workspace_root)
    except ValueError as error:
        raise ValueError("preflight readiness assembly_bom path is invalid") from error
    if identity != expected_bom:
        raise ValueError("preflight readiness binds a different assembly BOM path")
    artifacts = _required_mapping(bom.get("artifacts"), "bom.artifacts")
    for label, expected in artifact_inventory_snapshots(artifacts).items():
        row = _required_mapping(inputs.get(label), f"input_hashes.{label}")
        if dict(row) != expected:
            raise ValueError(f"preflight input hash mismatch: {label}")


def _validate_passed_preflight(
    readiness: Mapping[str, Any],
    bom: Mapping[str, Any],
    *,
    bom_path: Path,
    workspace_root: Path,
) -> None:
    _validate_preflight_metadata(readiness)
    _validate_preflight_gates(readiness, bom)
    _validate_preflight_scores(readiness)
    _validate_preflight_inputs(
        readiness, bom, bom_path=bom_path, workspace_root=workspace_root
    )

def _verify_bom_artifacts_unchanged(bom: Mapping[str, Any], root: Path) -> None:
    artifacts = _required_mapping(bom.get("artifacts"), "bom.artifacts")
    for label, row in artifacts.items():
        if row is None:
            continue
        if label == "execution_evidence":
            if not isinstance(row, Mapping):
                raise ValueError("artifacts.execution_evidence must be an object")
            for evidence_label, item in row.items():
                verify_artifact(
                    item,
                    workspace_root=root,
                    field=f"artifacts.execution_evidence.{evidence_label}",
                )
        elif isinstance(row, list):
            for index, item in enumerate(row):
                verify_artifact(item, workspace_root=root, field=f"artifacts.{label}[{index}]")
        else:
            verify_artifact(row, workspace_root=root, field=f"artifacts.{label}")


def _add_prior_readiness_hashes(
    resolvable: set[str],
    prior_readiness: Any,
    *,
    workspace_root: Path,
) -> None:
    if not isinstance(prior_readiness, Mapping):
        return
    prior_path = verify_artifact(
        prior_readiness,
        workspace_root=workspace_root,
        field="artifacts.prior_preflight_readiness",
    )
    payload = load_json_object_snapshot(prior_path, field="prior preflight readiness").payload
    inputs = payload.get("input_hashes")
    if not isinstance(inputs, Mapping):
        return
    for label, row in inputs.items():
        if isinstance(row, Mapping):
            resolvable.add(validate_sha256(
                row.get("sha256"),
                field=f"prior_preflight_readiness.input_hashes.{label}",
            ))


def _stage_evidence_manifests(
    stage_rows: Any,
    *,
    workspace_root: Path,
) -> dict[str, Mapping[str, Any]]:
    manifests: dict[str, Mapping[str, Any]] = {}
    if not isinstance(stage_rows, list):
        return manifests
    for index, row in enumerate(stage_rows):
        path = verify_artifact(
            row, workspace_root=workspace_root,
            field=f"artifacts.stage_evidence[{index}]",
        )
        snapshot = load_json_object_snapshot(path, field=f"stage evidence {index}")
        manifest = snapshot.payload
        if manifest.get("schema") != "simpro-blog-stage-evidence/v1":
            raise ValueError("stage evidence schema is invalid")
        if set(manifest) != {"schema", "evidence_hashes", "payload"}:
            raise ValueError("stage evidence must use the exact field set")
        hashes = _required_mapping(
            manifest.get("evidence_hashes"), f"stage_evidence[{index}].evidence_hashes"
        )
        manifests[snapshot.sha256] = {
            str(label): validate_sha256(
                digest, field=f"stage_evidence[{index}].evidence_hashes.{label}"
            )
            for label, digest in hashes.items()
        }
    return manifests


def _add_receipt_evidence_hashes(
    resolvable: set[str],
    receipts: Sequence[Mapping[str, Any]],
    manifests: Mapping[str, Mapping[str, Any]],
) -> None:
    for receipt in receipts:
        outputs = _required_mapping(
            receipt.get("output_artifact_hashes"), "stage_receipt.output_artifact_hashes"
        )
        evidence = _required_mapping(
            receipt.get("evidence_hashes"), "stage_receipt.evidence_hashes"
        )
        manifest_evidence = manifests.get(str(outputs.get("stage_evidence")), {})
        for label, digest in evidence.items():
            if digest not in resolvable and manifest_evidence.get(label) == digest:
                resolvable.add(str(digest))


def _resolvable_receipt_evidence_hashes(
    receipts: Sequence[Mapping[str, Any]],
    *,
    artifacts: Mapping[str, Any],
    execution_evidence: Mapping[str, Mapping[str, str]] | None = None,
    workspace_root: Path,
) -> set[str]:
    """Resolve every receipt evidence digest to a current bound source."""
    resolvable = {
        row["sha256"]
        for row in artifact_inventory_snapshots(artifacts).values()
    }
    registered_evidence = (
        execution_evidence
        if execution_evidence is not None
        else artifacts.get("execution_evidence")
    )
    stages = tuple(str(receipt.get("stage") or "") for receipt in receipts)
    optimized_tail = stages == (
        "post_optimization_scrub",
        "post_optimization_context_binding",
    )
    if not optimized_tail:
        capability_errors = blog_assembly_capabilities.validate_execution_evidence(
            registered_evidence,
            receipts=receipts,
            workspace_root=workspace_root,
        )
        if capability_errors:
            raise ValueError(
                "repository capability definitions are invalid: "
                + ", ".join(code for code, _ in capability_errors)
            )
    _add_prior_readiness_hashes(
        resolvable,
        artifacts.get("prior_preflight_readiness"),
        workspace_root=workspace_root,
    )
    manifests = _stage_evidence_manifests(
        artifacts.get("stage_evidence"), workspace_root=workspace_root
    )
    _add_receipt_evidence_hashes(resolvable, receipts, manifests)
    return resolvable


__all__ = ['_resolvable_receipt_evidence_hashes', '_validate_passed_preflight', '_verify_bom_artifacts_unchanged']
