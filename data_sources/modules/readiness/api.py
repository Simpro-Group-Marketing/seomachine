"""Publish-readiness api responsibilities."""
from pathlib import Path
from typing import Any, Mapping

from .adapters import _gate_from_findings
from .common import (
    READINESS_RESULT_SCHEMA,
    ReadinessResult,
    ReadinessTelemetry,
    ValidatedClaimSet,
    VaultClaimReceiptError,
    _ExecutedReadinessResult,
    load_validated_claim_set,
)
from .finalization import build_final_attestation
from .dependencies import DEFAULT_READINESS_DEPENDENCIES, ReadinessDependencies
from .orchestrator import run_in_session
from .result_validation import (
    _validate_actual_readiness_execution,
    validate_passed_readiness_result,
)
from .workspace_bindings import (
    _readiness_run_id,
    _resolve_optional_workspace_input,
    _resolve_workspace_input,
    _result_workspace_root,
)


def run_publish_readiness(
    file_path: str | Path,
    *,
    proof_sidecar: str | Path | None = None,
    context_request: str | Path | None = None,
    context_pack: str | Path | None = None,
    context_receipt: str | Path | None = None,
    assembly_bom: str | Path | None = None,
    vault_root: str | Path | None = None,
    ai_profile: str = "simpro-web",
    phase: str = "preflight",
    workspace_root: str | Path | None = None,
    artifact_kind: str | None = None,
    run_id: str | None = None,
    telemetry: ReadinessTelemetry | None = None,
    dependencies: ReadinessDependencies = DEFAULT_READINESS_DEPENDENCIES,
) -> ReadinessResult:
    """Run the complete gate stack inside one trusted workspace boundary."""
    if phase not in {"preflight", "final"}:
        raise ValueError("phase must be preflight or final")
    root = Path(workspace_root or Path.cwd()).resolve()
    article_path = _resolve_workspace_input(file_path, workspace_root=root, field="file")
    proof_path = _resolve_optional_workspace_input(
        proof_sidecar,
        workspace_root=root,
        field="proof_sidecar",
    )
    request_path = _resolve_optional_workspace_input(
        context_request,
        workspace_root=root,
        field="context_request",
    )
    pack_path = _resolve_optional_workspace_input(
        context_pack,
        workspace_root=root,
        field="context_pack",
    )
    receipt_path = _resolve_optional_workspace_input(
        context_receipt,
        workspace_root=root,
        field="context_receipt",
    )
    bom_path = _resolve_optional_workspace_input(
        assembly_bom,
        workspace_root=root,
        field="assembly_bom",
    )
    raw = _run_publish_readiness_session(
        article_path,
        proof_sidecar=proof_path,
        context_request=request_path,
        context_pack=pack_path,
        context_receipt=receipt_path,
        assembly_bom=bom_path,
        vault_root=vault_root,
        ai_profile=ai_profile,
        phase=phase,
        workspace_root=root,
        artifact_kind=artifact_kind,
        run_id=run_id,
        telemetry=telemetry,
        dependencies=dependencies,
    )
    return _ExecutedReadinessResult(raw, workspace_root=root)

def build_final_readiness_attestation(
    preflight_result: Mapping[str, Any],
    *,
    final_bom: str | Path | None = None,
    run_id: str | None = None,
    workspace_root: str | Path | None = None,
    telemetry: ReadinessTelemetry | None = None,
) -> ReadinessResult:
    """Bind an authenticated full preflight to one validated final BOM."""
    root = _result_workspace_root(preflight_result, workspace_root)
    final_bom_path = (
        _resolve_workspace_input(
            final_bom,
            workspace_root=root,
            field="final_bom",
        )
        if final_bom is not None
        else None
    )
    return build_final_attestation(
        preflight_result,
        final_bom_path=final_bom_path,
        workspace_root=root,
        validate_execution=_validate_actual_readiness_execution,
        validate_result=validate_passed_readiness_result,
        executed_result_factory=_ExecutedReadinessResult,
        readiness_run_id=_readiness_run_id,
        run_id=run_id,
        telemetry=telemetry,
    )

def _run_publish_readiness_session(
    file_path: str | Path,
    *,
    proof_sidecar: str | Path | None = None,
    context_request: str | Path | None = None,
    context_pack: str | Path | None = None,
    context_receipt: str | Path | None = None,
    assembly_bom: str | Path | None = None,
    vault_root: str | Path | None = None,
    ai_profile: str = "simpro-web",
    phase: str = "preflight",
    workspace_root: str | Path,
    artifact_kind: str | None = None,
    run_id: str | None = None,
    telemetry: ReadinessTelemetry | None = None,
    dependencies: ReadinessDependencies = DEFAULT_READINESS_DEPENDENCIES,
) -> ReadinessResult:
    """Create one immutable input/session boundary around the gate stack."""
    try:
        from ..publish_readiness_core import _run_publish_readiness as readiness_runner
    except ImportError:  # pragma: no cover - direct script compatibility.
        from publish_readiness_core import _run_publish_readiness as readiness_runner
    source_decision_registry = _optional_workspace_artifact(
        workspace_root,
        "context/source-classification-decisions.json",
    )
    customer_proof_index = _optional_workspace_artifact(
        workspace_root,
        "context/customer-proof-index.json",
    )
    customer_proof_usage_ledger = _optional_workspace_artifact(
        workspace_root,
        "context/customer-proof-usage-ledger.json",
    )
    runner_kwargs = {
        "file_path": file_path,
        "proof_sidecar": proof_sidecar,
        "context_request": context_request,
        "context_pack": context_pack,
        "context_receipt": context_receipt,
        "assembly_bom": assembly_bom,
        "vault_root": vault_root,
        "ai_profile": ai_profile,
        "phase": phase,
        "workspace_root": workspace_root,
        "artifact_kind": artifact_kind,
        "run_id": run_id,
    }
    return run_in_session(
        input_paths={
            "article": file_path,
            "validation_sidecar": proof_sidecar,
            "context_request": context_request,
            "context_pack": context_pack,
            "context_receipt": context_receipt,
            "assembly_bom": assembly_bom,
            "source_decision_registry": source_decision_registry,
            "customer_proof_index": customer_proof_index,
            "customer_proof_usage_ledger": customer_proof_usage_ledger,
        },
        workspace_root=workspace_root,
        runner=readiness_runner,
        runner_kwargs=runner_kwargs,
        blocked_result=lambda error: _input_capture_blocked_result(
            error=error,
            file_path=file_path,
            proof_sidecar=proof_sidecar,
            context_request=context_request,
            context_pack=context_pack,
            context_receipt=context_receipt,
            assembly_bom=assembly_bom,
            phase=phase,
        ),
        connector_factory=lambda: dependencies.connector_factory(vault_root=vault_root),
        claim_loader=lambda client: _load_session_claims(
            context_pack,
            context_receipt,
            vault_root=vault_root,
            client=client,
            loader=dependencies.claim_set_loader,
        ),
        telemetry=telemetry,
    )


def _optional_workspace_artifact(
    workspace_root: str | Path,
    relative_path: str,
) -> Path | None:
    """Return an existing fixed workspace input for authoritative capture."""
    root = Path(workspace_root).resolve()
    candidate = (root / relative_path).resolve(strict=False)
    return candidate if candidate.is_file() else None

def _load_session_claims(
    context_pack: str | Path | None,
    context_receipt: str | Path | None,
    *,
    vault_root: str | Path | None,
    client: Any,
    loader: Any = load_validated_claim_set,
) -> ValidatedClaimSet:
    try:
        return loader(
            context_pack,
            context_receipt,
            vault_root=vault_root,
            client=client,
        )
    except (VaultClaimReceiptError, OSError, ValueError, TypeError) as error:
        return ValidatedClaimSet(blocker=str(error))

def _input_capture_blocked_result(
    *,
    error: ValueError,
    file_path: str | Path,
    proof_sidecar: str | Path | None,
    context_request: str | Path | None,
    context_pack: str | Path | None,
    context_receipt: str | Path | None,
    assembly_bom: str | Path | None,
    phase: str,
) -> ReadinessResult:
    invalid_article_utf8 = str(error).startswith(
        "readiness input article must use valid UTF-8"
    )
    gate_name = "frontmatter_metadata" if invalid_article_utf8 else "input_seal"
    gate_title = "Frontmatter Metadata" if invalid_article_utf8 else "Input Seal"
    rule_id = "frontmatter_invalid" if invalid_article_utf8 else "readiness_input_snapshot_invalid"
    gate = _gate_from_findings(
        gate_name,
        gate_title,
        [{
            "rule_id": rule_id,
            "severity": "error",
            "line": 1,
            "column": 1,
            "message": str(error),
            "suggestion": "Provide unchanged, bounded inputs inside the trusted workspace.",
        }],
    )
    return {
        "schema": READINESS_RESULT_SCHEMA,
        "phase": phase,
        "verification_scope": "source_artifact",
        "file": str(file_path),
        "proof_sidecar": str(proof_sidecar) if proof_sidecar is not None else None,
        "context_request": str(context_request) if context_request is not None else None,
        "context_pack": str(context_pack) if context_pack is not None else None,
        "context_receipt": str(context_receipt) if context_receipt is not None else None,
        "assembly_bom": str(assembly_bom) if assembly_bom is not None else None,
        "passed": False,
        "artifact_kind": None,
        "gates": [gate],
        "score": None,
        "score_threshold": 85,
        "aeo_geo": {"score": None, "threshold": 90, "passed": False},
        "priority_fixes": [{"dimension": gate_name, "issue": str(error)}],
    }


__all__ = ['_input_capture_blocked_result', '_load_session_claims', '_run_publish_readiness_session', 'build_final_readiness_attestation', 'run_publish_readiness']
