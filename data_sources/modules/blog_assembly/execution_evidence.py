"""Execution-evidence resolution for provisional BOM construction."""
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

from .common import blog_assembly_capabilities, canonical_artifact, verify_artifact
from .contracts import _read_json_object, _required_mapping


NORMAL_CHAIN_REQUIRED = "normal_chain_required"
EVIDENCE_READY = "evidence_ready"


@dataclass(frozen=True, slots=True)
class StaleExecutionArtifact:
    """A copied agent output that no longer identifies the current artifact."""

    label: str
    path: str
    copied_path: str
    copied_sha256: str
    current_sha256: str


@dataclass(frozen=True, slots=True)
class ExecutionEvidenceResolution:
    """Evidence or a decision requiring the normal execution chain."""

    decision: str
    evidence: Mapping[str, Mapping[str, str]] | None
    stale_artifact: StaleExecutionArtifact | None = None

    @property
    def normal_chain_required(self) -> bool:
        return self.decision == NORMAL_CHAIN_REQUIRED


def _execution_evidence_from_prior_preflight(
    prior_preflight_readiness_path: str | Path | None,
    *,
    workspace_root: Path,
) -> dict[str, dict[str, str]]:
    if prior_preflight_readiness_path is None:
        raise blog_assembly_capabilities.CapabilityRegistryError(
            "optimized-tail workflow requires prior preflight readiness evidence"
        )
    try:
        readiness = _read_json_object(
            prior_preflight_readiness_path,
            "prior_preflight_readiness",
        )
        inputs = _required_mapping(
            readiness.get("input_hashes"),
            "prior_preflight_readiness.input_hashes",
        )
        prior_bom_row = _required_mapping(
            inputs.get("assembly_bom"),
            "prior_preflight_readiness.input_hashes.assembly_bom",
        )
        prior_bom_path = verify_artifact(
            prior_bom_row,
            workspace_root=workspace_root,
            field="prior_preflight_readiness.input_hashes.assembly_bom",
        )
        prior_bom = _read_json_object(prior_bom_path, "prior_preflight_bom")
        prior_artifacts = _required_mapping(
            prior_bom.get("artifacts"),
            "prior_preflight_bom.artifacts",
        )
        evidence = _required_mapping(
            prior_artifacts.get("execution_evidence"),
            "prior_preflight_bom.artifacts.execution_evidence",
        )
        copied: dict[str, dict[str, str]] = {}
        for label, row in evidence.items():
            if not isinstance(label, str):
                raise ValueError("execution evidence labels must be strings")
            copied[label] = dict(
                _required_mapping(
                    row,
                    f"prior_preflight_bom.artifacts.execution_evidence.{label}",
                )
            )
        return copied
    except ValueError as error:
        raise blog_assembly_capabilities.CapabilityRegistryError(str(error)) from error


def _stale_agent_output(
    copied: Mapping[str, Mapping[str, str]],
    agent_output_paths: Mapping[str, str | Path],
    *,
    workspace_root: Path,
) -> StaleExecutionArtifact | None:
    for label, copied_row in copied.items():
        if not label.startswith("agent_output."):
            continue
        agent_id = label.removeprefix("agent_output.")
        if agent_id not in agent_output_paths:
            continue
        current_row = canonical_artifact(
            agent_output_paths[agent_id],
            workspace_root=workspace_root,
        )
        if current_row == copied_row:
            continue
        return StaleExecutionArtifact(
            label=label,
            path=current_row["path"],
            copied_path=str(copied_row.get("path") or ""),
            copied_sha256=str(copied_row.get("sha256") or ""),
            current_sha256=current_row["sha256"],
        )
    return None


def resolve_execution_evidence(
    stage_receipts: Sequence[Mapping[str, Any]],
    *,
    prior_preflight_readiness_path: str | Path | None,
    agent_output_paths: Mapping[str, str | Path],
    workspace_root: Path,
) -> ExecutionEvidenceResolution:
    """Resolve current evidence or require a normal chain for stale copied rows."""
    stages = tuple(str(receipt.get("stage") or "") for receipt in stage_receipts)
    optimized_tail = stages == (
        "post_optimization_scrub",
        "post_optimization_context_binding",
    )
    if not optimized_tail:
        evidence = blog_assembly_capabilities.resolve_execution_evidence(
            stage_receipts,
            agent_output_paths=agent_output_paths,
            workspace_root=workspace_root,
        )
        return ExecutionEvidenceResolution(EVIDENCE_READY, evidence)

    copied = _execution_evidence_from_prior_preflight(
        prior_preflight_readiness_path,
        workspace_root=workspace_root,
    )
    stale_artifact = _stale_agent_output(
        copied,
        agent_output_paths,
        workspace_root=workspace_root,
    )
    if stale_artifact is not None:
        return ExecutionEvidenceResolution(
            NORMAL_CHAIN_REQUIRED,
            None,
            stale_artifact,
        )
    return ExecutionEvidenceResolution(EVIDENCE_READY, copied)


__all__ = [
    "EVIDENCE_READY",
    "NORMAL_CHAIN_REQUIRED",
    "ExecutionEvidenceResolution",
    "StaleExecutionArtifact",
    "_execution_evidence_from_prior_preflight",
    "resolve_execution_evidence",
]
