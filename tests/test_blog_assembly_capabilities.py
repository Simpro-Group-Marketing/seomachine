from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from data_sources.modules.blog_assembly_capabilities import (
    CapabilityRegistryError,
    expected_agent_ids,
    infer_route,
    resolve_execution_evidence,
    validate_execution_evidence,
)


ROOT = Path(__file__).resolve().parents[1]


ROUTE_AGENTS = {
    "article-command": (
        "content-analyzer",
        "seo-optimizer",
        "meta-creator",
        "internal-linker",
        "keyword-mapper",
    ),
    "write-command": (
        "content-analyzer",
        "seo-optimizer",
        "meta-creator",
        "internal-linker",
        "keyword-mapper",
    ),
    "rewrite-command": (
        "seo-optimizer",
        "meta-creator",
        "internal-linker",
        "keyword-mapper",
    ),
}


def _receipt(stage: str, tool: str, version: str = "1") -> dict[str, object]:
    return {"stage": stage, "tool": {"name": tool, "version": version}}


def _outputs(tmp_path: Path, agents: tuple[str, ...]) -> dict[str, Path]:
    output_dir = tmp_path / "research" / "agent-outputs"
    output_dir.mkdir(parents=True)
    result: dict[str, Path] = {}
    for agent_id in agents:
        path = output_dir / f"{agent_id}-scheduling-guide-2026-08-12.md"
        path.write_text(f"# {agent_id} diagnostics\n", encoding="utf-8")
        result[agent_id] = path
    return result


@pytest.mark.parametrize(("route", "agents"), ROUTE_AGENTS.items())
def test_registry_infers_only_current_draft_routes_and_exact_agents(
    route: str,
    agents: tuple[str, ...],
):
    receipts = [_receipt("draft", route)]

    assert infer_route(receipts) == route
    assert expected_agent_ids(receipts) == agents


def test_registry_rejects_unknown_route_and_wrong_command_version():
    with pytest.raises(CapabilityRegistryError, match="draft receipt tool identity"):
        infer_route([_receipt("draft", "external-writer")])
    with pytest.raises(CapabilityRegistryError, match="version 1"):
        infer_route([_receipt("draft", "article-command", "2")])


def test_registry_adds_optimize_agents_as_one_deduplicated_union():
    receipts = [
        _receipt("draft", "rewrite-command"),
        _receipt("optimization", "optimize-command"),
    ]

    assert expected_agent_ids(receipts) == (
        "seo-optimizer",
        "meta-creator",
        "internal-linker",
        "keyword-mapper",
        "content-analyzer",
    )


def test_registry_resolves_definitions_internally_and_requires_exact_outputs(
    tmp_path: Path,
):
    for source in (ROOT / ".claude" / "commands", ROOT / ".claude" / "agents"):
        destination = tmp_path / source.relative_to(ROOT)
        destination.mkdir(parents=True, exist_ok=True)
        for path in source.glob("*.md"):
            (destination / path.name).write_bytes(path.read_bytes())
    receipts = [_receipt("draft", "rewrite-command")]
    outputs = _outputs(tmp_path, ROUTE_AGENTS["rewrite-command"])

    evidence = resolve_execution_evidence(
        receipts,
        agent_output_paths=outputs,
        workspace_root=tmp_path,
    )

    assert set(evidence) == {
        "command_definition.rewrite-command",
        *(f"agent_definition.{agent_id}" for agent_id in ROUTE_AGENTS["rewrite-command"]),
        *(f"agent_output.{agent_id}" for agent_id in ROUTE_AGENTS["rewrite-command"]),
    }
    command_row = evidence["command_definition.rewrite-command"]
    assert command_row == {
        "path": ".claude/commands/rewrite.md",
        "sha256": hashlib.sha256(
            (tmp_path / ".claude" / "commands" / "rewrite.md").read_bytes()
        ).hexdigest(),
    }
    assert validate_execution_evidence(
        evidence,
        receipts=receipts,
        workspace_root=tmp_path,
    ) == []

    with pytest.raises(CapabilityRegistryError, match="agent output IDs"):
        resolve_execution_evidence(
            receipts,
            agent_output_paths={
                **outputs,
                "external-reviewer": tmp_path / "outside.md",
            },
            workspace_root=tmp_path,
        )


def test_registry_rejects_stale_invented_external_and_conditional_skill_rows(
    tmp_path: Path,
):
    for source in (ROOT / ".claude" / "commands", ROOT / ".claude" / "agents"):
        destination = tmp_path / source.relative_to(ROOT)
        destination.mkdir(parents=True, exist_ok=True)
        for path in source.glob("*.md"):
            (destination / path.name).write_bytes(path.read_bytes())
    receipts = [_receipt("draft", "rewrite-command")]
    evidence = resolve_execution_evidence(
        receipts,
        agent_output_paths=_outputs(tmp_path, ROUTE_AGENTS["rewrite-command"]),
        workspace_root=tmp_path,
    )

    stale = {key: dict(value) for key, value in evidence.items()}
    stale["command_definition.rewrite-command"]["sha256"] = "0" * 64
    assert "capability_definition_stale" in {
        code for code, _ in validate_execution_evidence(stale, receipts=receipts, workspace_root=tmp_path)
    }

    invented = {**evidence, "agent_definition.external-reviewer": dict(next(iter(evidence.values())))}
    assert "capability_evidence_keys_invalid" in {
        code for code, _ in validate_execution_evidence(invented, receipts=receipts, workspace_root=tmp_path)
    }

    conditional_skill = {**evidence, "skill_definition.blog-review": dict(next(iter(evidence.values())))}
    assert "capability_evidence_keys_invalid" in {
        code
        for code, _ in validate_execution_evidence(
            conditional_skill,
            receipts=receipts,
            workspace_root=tmp_path,
        )
    }

    external = {key: dict(value) for key, value in evidence.items()}
    external["agent_output.seo-optimizer"] = {
        "path": "../external.md",
        "sha256": "0" * 64,
    }
    assert "capability_artifact_invalid" in {
        code for code, _ in validate_execution_evidence(external, receipts=receipts, workspace_root=tmp_path)
    }
