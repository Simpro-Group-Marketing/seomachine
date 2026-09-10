"""Publish-readiness workspace bindings responsibilities."""
# ruff: noqa: F403, F405

from .common import *  # noqa: F403


def _same_path(left: str | Path, right: str | Path) -> bool:
    return os.path.normcase(str(Path(left).resolve())) == os.path.normcase(
        str(Path(right).resolve())
    )

def _readiness_run_id(assembly_bom: str | None, article_hash: str) -> str:
    if assembly_bom:
        try:
            bom = load_json_object_snapshot(
                assembly_bom, field="assembly BOM"
            ).payload
        except ValueError:
            bom = None
        workflow = bom.get("workflow") if isinstance(bom, Mapping) else None
        receipts = workflow.get("stage_receipts") if isinstance(workflow, Mapping) else None
        if isinstance(receipts, list) and receipts and isinstance(receipts[0], Mapping):
            run_id = receipts[0].get("run_id")
            if isinstance(run_id, str) and run_id.strip():
                return run_id.strip()
    return f"readiness-{article_hash[:16]}"

def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

def _resolve_workspace_input(
    value: str | Path,
    *,
    workspace_root: str | Path,
    field: str,
) -> Path:
    """Resolve one caller path without allowing a BOM to widen the trust root."""
    root = Path(workspace_root).resolve()
    raw = Path(value)
    candidate = raw.resolve() if raw.is_absolute() else (root / raw).resolve()
    try:
        common = Path(os.path.commonpath((str(root), str(candidate))))
    except ValueError as error:
        raise ValueError(f"{field} must remain inside workspace_root") from error
    if os.path.normcase(str(common)) != os.path.normcase(str(root)):
        raise ValueError(f"{field} must remain inside workspace_root")
    return candidate

def _resolve_optional_workspace_input(
    value: str | Path | None,
    *,
    workspace_root: str | Path,
    field: str,
) -> Path | None:
    if value is None:
        return None
    return _resolve_workspace_input(value, workspace_root=workspace_root, field=field)

def _result_workspace_root(
    result: Mapping[str, Any],
    workspace_root: str | Path | None,
) -> Path:
    if workspace_root is not None:
        root = Path(workspace_root).resolve()
    elif isinstance(result, _ExecutedReadinessResult):
        root = result._workspace_root
    else:
        root = Path.cwd().resolve()
    if (
        isinstance(result, _ExecutedReadinessResult)
        and os.path.normcase(str(root))
        != os.path.normcase(str(result._workspace_root))
    ):
        raise ValueError("readiness result workspace_root does not match its execution")
    return root

def _verify_result_inputs_unchanged(
    result: Mapping[str, Any],
    *,
    workspace_root: str | Path,
) -> None:
    """Reject persistence of a pass after any attested input changed."""
    if result.get("input_seal") != {"status": "verified"}:
        raise ValueError("passed readiness result requires a verified input seal")
    rows = result.get("input_hashes")
    if not isinstance(rows, Mapping) or not rows:
        raise ValueError("passed readiness result requires input_hashes")
    root = Path(workspace_root).resolve()
    for label, row in rows.items():
        if not isinstance(row, Mapping) or set(row) != {"path", "sha256"}:
            raise ValueError(f"readiness input {label} must contain only path and sha256")
        digest = validate_sha256(row.get("sha256"), field=f"input_hashes.{label}.sha256")
        stored = row.get("path")
        if not isinstance(stored, str) or not stored:
            raise ValueError(f"input_hashes.{label}.path must be a non-empty string")
        candidate = resolve_artifact(stored, workspace_root=root)
        if not candidate.is_file() or file_sha256(candidate) != digest:
            raise ValueError(f"readiness input {label} changed after gate execution")
    if result.get("phase") == "final":
        assembly_row = rows.get("assembly_bom")
        if (
            not isinstance(assembly_row, Mapping)
            or result.get("final_bom_sha256") != assembly_row.get("sha256")
        ):
            raise ValueError("final readiness must bind the exact final BOM hash")

def _reject_output_input_collision(
    output_path: str | Path,
    result: Mapping[str, Any],
    *,
    output_label: str = "readiness output",
    workspace_root: str | Path,
) -> None:
    root = Path(workspace_root).resolve()
    destination = os.path.normcase(str(Path(output_path).resolve()))
    _reject_direct_collision(destination, result, output_label=output_label, root=root)
    _reject_bom_collision(destination, result, output_label=output_label, root=root)
    _reject_inventory_collision(destination, result, output_label=output_label, root=root)


def _reject_direct_collision(
    destination: str,
    result: Mapping[str, Any],
    *,
    output_label: str,
    root: Path,
) -> None:
    direct_inputs = {
        "article": result.get("file"),
        "validation_sidecar": result.get("proof_sidecar"),
        "context_request": result.get("context_request"),
        "context_pack": result.get("context_pack"),
        "context_receipt": result.get("context_receipt"),
        "assembly_bom": result.get("assembly_bom"),
    }
    for label, value in direct_inputs.items():
        if isinstance(value, str) and value:
            resolved = _resolve_workspace_input(
                value,
                workspace_root=root,
                field=label,
            )
            if destination == os.path.normcase(str(resolved)):
                raise ValueError(f"{output_label} cannot overwrite input {label}")


def _reject_bom_collision(
    destination: str,
    result: Mapping[str, Any],
    *,
    output_label: str,
    root: Path,
) -> None:
    bom_value = result.get("assembly_bom")
    if not isinstance(bom_value, str) or not bom_value:
        return
    try:
        bom = load_json_object_snapshot(bom_value, field="assembly BOM").payload
        artifacts = bom.get("artifacts") if isinstance(bom, Mapping) else None
        if not isinstance(artifacts, Mapping):
            raise ValueError("assembly BOM artifacts must be an object")
        nested_rows = artifact_inventory_snapshots(artifacts)
        nested_rows.update(_historical_preflight_input_snapshots(bom))
        for label, row in nested_rows.items():
            resolved = resolve_artifact(row["path"], workspace_root=root)
            if destination == os.path.normcase(str(resolved)):
                raise ValueError(f"{output_label} cannot overwrite input {label}")
    except ValueError as error:
        raise ValueError(
            f"{output_label} cannot safely inspect its bound assembly BOM: {error}"
        ) from error


def _reject_inventory_collision(
    destination: str,
    result: Mapping[str, Any],
    *,
    output_label: str,
    root: Path,
) -> None:
    rows = result.get("input_hashes")
    if not isinstance(rows, Mapping):
        return
    for label, row in rows.items():
        if not isinstance(row, Mapping) or not isinstance(row.get("path"), str):
            continue
        stored = str(row["path"])
        try:
            resolved = resolve_artifact(stored, workspace_root=root)
        except ValueError:
            continue
        if destination == os.path.normcase(str(resolved)):
            raise ValueError(f"{output_label} cannot overwrite input {label}")

def _readiness_input_hashes(
    inputs: Dict[str, str | Path | None],
    *,
    workspace_root: str | Path,
) -> Dict[str, Dict[str, str]]:
    snapshots: Dict[str, Dict[str, str]] = {}
    for label, value in inputs.items():
        if value is None:
            continue
        path = _resolve_workspace_input(
            value,
            workspace_root=workspace_root,
            field=f"readiness input {label}",
        )
        if path.is_file():
            snapshots[label] = canonical_artifact(
                path,
                workspace_root=workspace_root,
            )
    return snapshots

def _complete_readiness_input_hashes(
    *,
    article: str | Path,
    validation_sidecar: str | Path | None,
    context_request: str | Path | None,
    context_pack: str | Path | None,
    context_receipt: str | Path | None,
    assembly_bom: str | Path | None,
    workspace_root: str | Path,
) -> Dict[str, Dict[str, str]]:
    return _capture_readiness_inputs(
        article=article,
        validation_sidecar=validation_sidecar,
        context_request=context_request,
        context_pack=context_pack,
        context_receipt=context_receipt,
        assembly_bom=assembly_bom,
        workspace_root=workspace_root,
    ).hash_inventory()

def _capture_readiness_inputs(
    *,
    article: str | Path,
    validation_sidecar: str | Path | None,
    context_request: str | Path | None,
    context_pack: str | Path | None,
    context_receipt: str | Path | None,
    assembly_bom: str | Path | None,
    workspace_root: str | Path,
    telemetry: ReadinessTelemetry | None = None,
) -> ReadinessInputs:
    return ReadinessInputs.capture(
        {
            "article": article,
            "validation_sidecar": validation_sidecar,
            "context_request": context_request,
            "context_pack": context_pack,
            "context_receipt": context_receipt,
            "assembly_bom": assembly_bom,
        },
        workspace_root=workspace_root,
        telemetry=telemetry,
    )

def _captured_proof_content(
    inputs: ReadinessInputs | None,
    *,
    proof_sidecar_path: str | None,
) -> str | None:
    if proof_sidecar_path is None:
        return None
    if inputs is not None and inputs.optional_snapshot("validation_sidecar") is not None:
        return inputs.text("validation_sidecar")
    return Path(proof_sidecar_path).read_text(encoding="utf-8")

def _optional_result_path(result: Mapping[str, Any], key: str) -> str | None:
    value = result.get(key)
    return value if isinstance(value, str) else None

def _historical_preflight_input_snapshots(
    bom: Mapping[str, Any],
) -> Dict[str, Dict[str, str]]:
    """Return the immutable inputs sealed by a final BOM's preflight run."""
    record = bom.get("preflight")
    if record is None:
        return {}
    if not isinstance(record, Mapping):
        raise ValueError("assembly BOM preflight record must be an object")
    inputs = record.get("input_hashes")
    if not isinstance(inputs, Mapping) or not inputs:
        raise ValueError("assembly BOM preflight input_hashes must be an object")
    snapshots: Dict[str, Dict[str, str]] = {}
    for label, row in sorted(inputs.items(), key=lambda item: str(item[0])):
        if not isinstance(label, str) or not label:
            raise ValueError("assembly BOM preflight input labels must be non-empty strings")
        if not isinstance(row, Mapping) or set(row) != {"path", "sha256"}:
            raise ValueError(
                f"assembly BOM preflight input {label} must contain path and sha256"
            )
        path = row.get("path")
        if not isinstance(path, str) or not path:
            raise ValueError(
                f"assembly BOM preflight input {label}.path must be a non-empty string"
            )
        digest = validate_sha256(
            row.get("sha256"),
            field=f"preflight.input_hashes.{label}.sha256",
        )
        snapshots[f"historical_preflight.{label}"] = {
            "path": path,
            "sha256": digest,
        }
    return snapshots


__all__ = ['_capture_readiness_inputs', '_captured_proof_content', '_complete_readiness_input_hashes', '_historical_preflight_input_snapshots', '_optional_result_path', '_readiness_input_hashes', '_readiness_run_id', '_reject_output_input_collision', '_resolve_optional_workspace_input', '_resolve_workspace_input', '_result_workspace_root', '_same_path', '_utc_now', '_verify_result_inputs_unchanged']
