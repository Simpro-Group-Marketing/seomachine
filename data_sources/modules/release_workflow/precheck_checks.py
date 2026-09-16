"""Small validation and artifact helpers for blog release prechecks."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping, Sequence

try:
    from .. import optimizer_evidence
    from ..artifact_runtime.release_invocation import ReleaseInvocationError
except ImportError:  # pragma: no cover - supports direct script execution.
    import optimizer_evidence
    from artifact_runtime.release_invocation import ReleaseInvocationError


def validate_optimizer_outputs(
    optimizer_outputs: Sequence[str | Path],
    *,
    article: str | Path,
    editorial_plan: str | Path,
    proof_sidecar: str | Path,
    prior_preflight_readiness: str | Path | None,
    workspace_root: Path,
) -> None:
    try:
        optimizer_evidence.validate_optimizer_outputs(
            optimizer_outputs,
            article=article,
            editorial_plan=editorial_plan,
            proof_sidecar=proof_sidecar,
            prior_preflight_readiness=prior_preflight_readiness,
            workspace_root=workspace_root,
        )
    except optimizer_evidence.OptimizerEvidenceError as error:
        raise ReleaseInvocationError(str(error)) from error


def provisional_findings(provisional: object) -> list[dict[str, str]]:
    findings: list[dict[str, str]] = []
    if not isinstance(provisional, Mapping):
        return [_blocker("provisional_bom_invalid", "Provisional BOM must be an object.")]
    if provisional.get("schema") != "simpro-blog-assembly-bom/v2":
        findings.append(
            _blocker(
                "provisional_bom_schema_invalid",
                "Provisional BOM must use simpro-blog-assembly-bom/v2.",
            )
        )
    if provisional.get("lifecycle_state") != "provisional":
        findings.append(
            _blocker(
                "provisional_bom_lifecycle_invalid",
                "Provisional BOM lifecycle_state must be provisional.",
            )
        )
    return findings


def pre_bom_for_release(pre_bom: Mapping[str, Any], *, output: str | Path) -> dict[str, Any]:
    payload = dict(pre_bom)
    artifact_paths = payload.get("artifact_paths")
    if isinstance(artifact_paths, Mapping):
        payload["artifact_paths"] = {**artifact_paths, "output": str(Path(output).resolve())}
    return payload


def _blocker(rule_id: str, message: str) -> dict[str, str]:
    return {"rule_id": rule_id, "message": message}


__all__ = [
    "pre_bom_for_release",
    "provisional_findings",
    "validate_optimizer_outputs",
]
