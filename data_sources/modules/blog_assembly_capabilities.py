"""Closed repository capability registry for blog assembly provenance.

This module attests only local repository identity and byte integrity. It does
not prove model authorship, execution quality, or external truth.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Mapping, Sequence

try:
    from .blog_assembly_contract import canonical_artifact, verify_artifact
except ImportError:  # pragma: no cover - supports direct script execution.
    from blog_assembly_contract import canonical_artifact, verify_artifact


COMMAND_VERSION = "1"
OPTIMIZE_COMMAND_ID = "optimize-command"
OPTIMIZE_AGENT_IDS = (
    "content-analyzer",
    "seo-optimizer",
    "meta-creator",
    "internal-linker",
    "keyword-mapper",
)
CONDITIONAL_SKILL_IDS: tuple[str, ...] = ()
EXECUTION_EVIDENCE_PREFIXES = (
    "command_definition.",
    "agent_definition.",
    "agent_output.",
    "skill_definition.",
)


@dataclass(frozen=True, slots=True)
class RouteCapability:
    command_id: str
    command_path: str
    agent_ids: tuple[str, ...]


ROUTES = {
    "write-command": RouteCapability(
        command_id="write-command",
        command_path=".claude/commands/write.md",
        agent_ids=(
            "content-analyzer",
            "seo-optimizer",
            "meta-creator",
            "internal-linker",
            "keyword-mapper",
        ),
    ),
    "rewrite-command": RouteCapability(
        command_id="rewrite-command",
        command_path=".claude/commands/rewrite.md",
        agent_ids=(
            "seo-optimizer",
            "meta-creator",
            "internal-linker",
            "keyword-mapper",
        ),
    ),
}
COMMAND_PATHS = {
    **{route.command_id: route.command_path for route in ROUTES.values()},
    OPTIMIZE_COMMAND_ID: ".claude/commands/optimize.md",
}
AGENT_PATHS = {
    agent_id: f".claude/agents/{agent_id}.md"
    for agent_id in OPTIMIZE_AGENT_IDS
}


class CapabilityRegistryError(ValueError):
    """Repository execution evidence violates the closed registry."""


def infer_route(receipts: Sequence[Mapping[str, Any]]) -> str:
    """Infer one route exclusively from its draft receipt tool identity."""
    draft_receipts = [
        receipt for receipt in receipts
        if isinstance(receipt, Mapping) and receipt.get("stage") == "draft"
    ]
    if len(draft_receipts) != 1:
        raise CapabilityRegistryError(
            "receipt chain must contain exactly one draft receipt tool identity"
        )
    tool = draft_receipts[0].get("tool")
    if not isinstance(tool, Mapping) or set(tool) != {"name", "version"}:
        raise CapabilityRegistryError("draft receipt tool identity is invalid")
    command_id = tool.get("name")
    if command_id not in ROUTES:
        raise CapabilityRegistryError("draft receipt tool identity is not a registered route")
    if tool.get("version") != COMMAND_VERSION:
        raise CapabilityRegistryError("draft command must use version 1")
    return str(command_id)


def is_optimized(receipts: Sequence[Mapping[str, Any]]) -> bool:
    """Validate and return whether the chain includes optimize-command."""
    optimization_receipts = [
        receipt for receipt in receipts
        if isinstance(receipt, Mapping) and receipt.get("stage") == "optimization"
    ]
    if len(optimization_receipts) > 1:
        raise CapabilityRegistryError("receipt chain contains duplicate optimization stages")
    if not optimization_receipts:
        return False
    tool = optimization_receipts[0].get("tool")
    if (
        not isinstance(tool, Mapping)
        or set(tool) != {"name", "version"}
        or tool.get("name") != OPTIMIZE_COMMAND_ID
    ):
        raise CapabilityRegistryError(
            "optimization receipt tool identity must be optimize-command"
        )
    if tool.get("version") != COMMAND_VERSION:
        raise CapabilityRegistryError("optimize command must use version 1")
    return True


def expected_agent_ids(receipts: Sequence[Mapping[str, Any]]) -> tuple[str, ...]:
    """Return the ordered, deduplicated union invoked by this exact route."""
    route = ROUTES[infer_route(receipts)]
    agents = list(route.agent_ids)
    if is_optimized(receipts):
        agents.extend(
            agent_id for agent_id in OPTIMIZE_AGENT_IDS if agent_id not in agents
        )
    return tuple(agents)


def expected_execution_evidence_keys(
    receipts: Sequence[Mapping[str, Any]],
) -> tuple[str, ...]:
    """Return the sole allowed execution evidence key inventory."""
    route_id = infer_route(receipts)
    command_ids = [route_id]
    if is_optimized(receipts):
        command_ids.append(OPTIMIZE_COMMAND_ID)
    return (
        *(f"command_definition.{command_id}" for command_id in command_ids),
        *(f"agent_definition.{agent_id}" for agent_id in expected_agent_ids(receipts)),
        *(f"agent_output.{agent_id}" for agent_id in expected_agent_ids(receipts)),
        *(f"skill_definition.{skill_id}" for skill_id in CONDITIONAL_SKILL_IDS),
    )


def resolve_execution_evidence(
    receipts: Sequence[Mapping[str, Any]],
    *,
    agent_output_paths: Mapping[str, str | Path],
    workspace_root: str | Path,
) -> dict[str, dict[str, str]]:
    """Resolve definition rows internally and bind exact agent output artifacts."""
    root = Path(workspace_root).resolve()
    route_id = infer_route(receipts)
    optimized = is_optimized(receipts)
    agent_ids = expected_agent_ids(receipts)
    supplied_ids = set(agent_output_paths)
    expected_ids = set(agent_ids)
    if supplied_ids != expected_ids:
        missing = sorted(expected_ids - supplied_ids)
        extra = sorted(supplied_ids - expected_ids)
        details = []
        if missing:
            details.append("missing " + ", ".join(missing))
        if extra:
            details.append("extra " + ", ".join(extra))
        raise CapabilityRegistryError(
            "agent output IDs must match the invoked registry set exactly"
            + (": " + "; ".join(details) if details else "")
        )

    evidence = resolve_definition_evidence(receipts, workspace_root=root)
    for agent_id in agent_ids:
        row = canonical_artifact(
            agent_output_paths[agent_id],
            workspace_root=root,
        )
        if not _is_agent_output_path(row["path"], agent_id):
            raise CapabilityRegistryError(
                f"agent output {agent_id} must use research/agent-outputs/{agent_id}-*.md"
            )
        evidence[f"agent_output.{agent_id}"] = row
    return evidence


def resolve_definition_evidence(
    receipts: Sequence[Mapping[str, Any]],
    *,
    workspace_root: str | Path,
) -> dict[str, dict[str, str]]:
    """Resolve only invoked command and agent definitions from registry state."""
    root = Path(workspace_root).resolve()
    route_id = infer_route(receipts)
    command_ids = [route_id]
    if is_optimized(receipts):
        command_ids.append(OPTIMIZE_COMMAND_ID)
    evidence: dict[str, dict[str, str]] = {}
    for command_id in command_ids:
        evidence[f"command_definition.{command_id}"] = _definition_artifact(
            COMMAND_PATHS[command_id],
            workspace_root=root,
        )
    for agent_id in expected_agent_ids(receipts):
        evidence[f"agent_definition.{agent_id}"] = _definition_artifact(
            AGENT_PATHS[agent_id],
            workspace_root=root,
        )
    return evidence


def resolve_mutation_definition_evidence(
    *,
    stage: str,
    tool_name: str,
    tool_version: str,
    workspace_root: str | Path,
) -> dict[str, dict[str, str]]:
    """Resolve definitions available at one mutation boundary without caller IDs."""
    tool_receipt = {
        "stage": stage,
        "tool": {"name": tool_name, "version": tool_version},
    }
    if stage == "draft":
        return resolve_definition_evidence(
            [tool_receipt],
            workspace_root=workspace_root,
        )
    if stage != "optimization" or not is_optimized([tool_receipt]):
        raise CapabilityRegistryError("mutation stage is not a registered capability")
    root = Path(workspace_root).resolve()
    evidence = {
        f"command_definition.{OPTIMIZE_COMMAND_ID}": _definition_artifact(
            COMMAND_PATHS[OPTIMIZE_COMMAND_ID],
            workspace_root=root,
        )
    }
    for agent_id in OPTIMIZE_AGENT_IDS:
        evidence[f"agent_definition.{agent_id}"] = _definition_artifact(
            AGENT_PATHS[agent_id],
            workspace_root=root,
        )
    return evidence


def resolve_optimization_agent_outputs(
    agent_output_paths: Mapping[str, str | Path],
    *,
    workspace_root: str | Path,
) -> dict[str, dict[str, str]]:
    """Resolve the exact optimize-command output set at mutation close."""
    supplied_ids = set(agent_output_paths)
    expected_ids = set(OPTIMIZE_AGENT_IDS)
    if supplied_ids != expected_ids:
        raise CapabilityRegistryError(
            "optimization agent output IDs must match the registry exactly"
        )
    root = Path(workspace_root).resolve()
    evidence: dict[str, dict[str, str]] = {}
    for agent_id in OPTIMIZE_AGENT_IDS:
        row = canonical_artifact(
            agent_output_paths[agent_id],
            workspace_root=root,
        )
        if not _is_agent_output_path(row["path"], agent_id):
            raise CapabilityRegistryError(
                f"agent output {agent_id} must use "
                f"research/agent-outputs/{agent_id}-*.md"
            )
        evidence[f"agent_output.{agent_id}"] = row
    return evidence


def validate_execution_evidence(
    evidence: Any,
    *,
    receipts: Sequence[Mapping[str, Any]],
    workspace_root: str | Path,
) -> list[tuple[str, str]]:
    """Validate exact IDs, categories, canonical paths, and current bytes."""
    try:
        route_id = infer_route(receipts)
        optimized = is_optimized(receipts)
        agent_ids = expected_agent_ids(receipts)
        expected_keys = set(expected_execution_evidence_keys(receipts))
    except CapabilityRegistryError as error:
        return [("capability_route_invalid", str(error))]
    if not isinstance(evidence, Mapping):
        return [("capability_evidence_invalid", "execution_evidence must be an object")]
    if set(evidence) != expected_keys:
        return [(
            "capability_evidence_keys_invalid",
            "execution_evidence keys must exactly match registered invoked capabilities",
        )]

    root = Path(workspace_root).resolve()
    errors: list[tuple[str, str]] = []
    command_ids = [route_id, *( [OPTIMIZE_COMMAND_ID] if optimized else [])]
    for command_id in command_ids:
        label = f"command_definition.{command_id}"
        _validate_definition_row(
            evidence.get(label),
            expected_path=COMMAND_PATHS[command_id],
            label=label,
            root=root,
            errors=errors,
        )
    for agent_id in agent_ids:
        label = f"agent_definition.{agent_id}"
        _validate_definition_row(
            evidence.get(label),
            expected_path=AGENT_PATHS[agent_id],
            label=label,
            root=root,
            errors=errors,
        )
        output_label = f"agent_output.{agent_id}"
        row = evidence.get(output_label)
        try:
            path = verify_artifact(
                row,
                workspace_root=root,
                field=f"artifacts.execution_evidence.{output_label}",
            )
            relative = path.relative_to(root).as_posix()
            if not _is_agent_output_path(relative, agent_id):
                raise ValueError("agent output path is not the canonical agent convention")
        except ValueError as error:
            errors.append(("capability_artifact_invalid", f"{output_label}: {error}"))
    return errors


def receipt_definition_hashes(
    receipts: Sequence[Mapping[str, Any]],
    *,
    stage: str,
    execution_evidence: Mapping[str, Mapping[str, str]],
) -> dict[str, str]:
    """Return the exact definition/output hashes required on one mutation receipt."""
    route_id = infer_route(receipts)
    if stage == "draft":
        labels = [
            f"command_definition.{route_id}",
            *(f"agent_definition.{agent_id}" for agent_id in ROUTES[route_id].agent_ids),
        ]
    elif stage == "optimization":
        if not is_optimized(receipts):
            raise CapabilityRegistryError("optimization definition hashes require optimization")
        agents = expected_agent_ids(receipts)
        labels = [
            f"command_definition.{OPTIMIZE_COMMAND_ID}",
            *(f"agent_definition.{agent_id}" for agent_id in agents),
            *(f"agent_output.{agent_id}" for agent_id in agents),
        ]
    else:
        raise CapabilityRegistryError("definition hashes are supported only for mutation stages")
    result: dict[str, str] = {}
    for label in labels:
        row = execution_evidence.get(label)
        if not isinstance(row, Mapping) or not isinstance(row.get("sha256"), str):
            raise CapabilityRegistryError(f"execution evidence is missing {label}")
        result[label] = str(row["sha256"])
    return result


def _definition_artifact(
    stored_path: str,
    *,
    workspace_root: Path,
) -> dict[str, str]:
    path = workspace_root.joinpath(*PurePosixPath(stored_path).parts)
    try:
        return canonical_artifact(path, workspace_root=workspace_root)
    except ValueError as error:
        raise CapabilityRegistryError(
            f"registered repository definition is unavailable: {stored_path}"
        ) from error


def _validate_definition_row(
    row: Any,
    *,
    expected_path: str,
    label: str,
    root: Path,
    errors: list[tuple[str, str]],
) -> None:
    try:
        current = _definition_artifact(expected_path, workspace_root=root)
    except CapabilityRegistryError as error:
        errors.append(("capability_definition_missing", str(error)))
        return
    if not isinstance(row, Mapping) or set(row) != {"path", "sha256"}:
        errors.append(("capability_definition_invalid", f"{label} must contain path and sha256"))
        return
    if row.get("path") != current["path"]:
        errors.append(("capability_definition_path_invalid", f"{label} uses the wrong canonical path"))
    if row.get("sha256") != current["sha256"]:
        errors.append(("capability_definition_stale", f"{label} does not match current repository bytes"))


def _is_agent_output_path(path: str, agent_id: str) -> bool:
    pure = PurePosixPath(path)
    return (
        len(pure.parts) == 3
        and pure.parts[:2] == ("research", "agent-outputs")
        and pure.suffix == ".md"
        and pure.name.startswith(f"{agent_id}-")
        and len(pure.stem) > len(agent_id) + 1
    )
