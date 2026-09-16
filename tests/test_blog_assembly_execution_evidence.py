from __future__ import annotations

import json
from pathlib import Path

import pytest

from data_sources.modules.blog_assembly.common import canonical_artifact
from data_sources.modules.blog_assembly.construction_support import (
    resolve_construction_execution_evidence,
)
from data_sources.modules.blog_assembly.execution_evidence import (
    NORMAL_CHAIN_REQUIRED,
    resolve_execution_evidence,
)


OPTIMIZED_TAIL_RECEIPTS = (
    {"stage": "post_optimization_scrub"},
    {"stage": "post_optimization_context_binding"},
)


def _write_json(path: Path, value: object) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
    return path


def _prior_preflight_fixture(
    tmp_path: Path,
) -> tuple[Path, Path, dict[str, dict[str, str]]]:
    agent_output = tmp_path / "research" / "agent-outputs" / "content-analyzer-run.md"
    agent_output.parent.mkdir(parents=True)
    agent_output.write_text("# Current diagnostics\n", encoding="utf-8")
    evidence = {
        "command_definition.write-command": {
            "path": ".claude/commands/write.md",
            "sha256": "a" * 64,
        },
        "agent_output.content-analyzer": canonical_artifact(
            agent_output,
            workspace_root=tmp_path,
        ),
    }
    prior_bom = _write_json(
        tmp_path / "research" / "prior-bom.json",
        {"artifacts": {"execution_evidence": evidence}},
    )
    readiness = _write_json(
        tmp_path / "research" / "prior-readiness.json",
        {
            "input_hashes": {
                "assembly_bom": canonical_artifact(
                    prior_bom,
                    workspace_root=tmp_path,
                )
            }
        },
    )
    return readiness, agent_output, evidence


def test_optimized_tail_copies_fresh_agent_output_evidence(tmp_path: Path):
    readiness, agent_output, copied_evidence = _prior_preflight_fixture(tmp_path)

    evidence = resolve_construction_execution_evidence(
        OPTIMIZED_TAIL_RECEIPTS,
        prior_preflight_readiness_path=readiness,
        agent_output_paths={"content-analyzer": agent_output},
        workspace_root=tmp_path,
    )

    assert evidence == copied_evidence


def test_optimized_tail_requires_normal_chain_for_stale_agent_output(tmp_path: Path):
    readiness, agent_output, copied_evidence = _prior_preflight_fixture(tmp_path)
    agent_output.write_text("# Mutated diagnostics\n", encoding="utf-8")

    result = resolve_execution_evidence(
        OPTIMIZED_TAIL_RECEIPTS,
        prior_preflight_readiness_path=readiness,
        agent_output_paths={"content-analyzer": agent_output},
        workspace_root=tmp_path,
    )

    assert result.decision == NORMAL_CHAIN_REQUIRED
    assert result.evidence is None
    assert result.stale_artifact is not None
    assert result.stale_artifact.label == "agent_output.content-analyzer"
    assert result.stale_artifact.path == copied_evidence[
        "agent_output.content-analyzer"
    ]["path"]
    with pytest.raises(
        ValueError,
        match=r"normal_chain_required.*agent_output\.content-analyzer",
    ):
        resolve_construction_execution_evidence(
            OPTIMIZED_TAIL_RECEIPTS,
            prior_preflight_readiness_path=readiness,
            agent_output_paths={"content-analyzer": agent_output},
            workspace_root=tmp_path,
        )
