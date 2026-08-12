from __future__ import annotations

import hashlib
import json
import os
from datetime import date
from pathlib import Path

import pytest

from data_sources.modules.blog_assembly_contract import (
    artifact_inventory_snapshots,
    atomic_write_json,
    canonical_artifact,
    expected_blog_gate_inventory,
    order_blog_gate_results,
    resolve_artifact,
    validate_current_assembly_date,
    validate_sha256,
)
from data_sources.modules import blog_assembly_contract


def test_canonical_artifact_stores_workspace_relative_posix_path_and_hash(tmp_path: Path):
    artifact = tmp_path / "research" / "evidence.json"
    artifact.parent.mkdir()
    artifact.write_text('{"ok": true}\n', encoding="utf-8")

    row = canonical_artifact(artifact, workspace_root=tmp_path)

    assert row == {
        "path": "research/evidence.json",
        "sha256": hashlib.sha256(artifact.read_bytes()).hexdigest(),
    }


def test_execution_evidence_flattens_exact_labels_without_container_prefix():
    digest = "a" * 64
    artifacts = {
        "article": {"path": "drafts/article.md", "sha256": digest},
        "execution_evidence": {
            "command_definition.write-command": {
                "path": ".claude/commands/write.md",
                "sha256": "b" * 64,
            },
            "agent_output.seo-optimizer": {
                "path": "research/agent-outputs/seo-optimizer-topic-2026-08-12.md",
                "sha256": "c" * 64,
            },
        },
    }

    assert artifact_inventory_snapshots(artifacts) == {
        "article": artifacts["article"],
        "command_definition.write-command": artifacts["execution_evidence"][
            "command_definition.write-command"
        ],
        "agent_output.seo-optimizer": artifacts["execution_evidence"][
            "agent_output.seo-optimizer"
        ],
    }


def test_execution_evidence_rejects_duplicate_flattened_labels():
    row = {"path": "drafts/article.md", "sha256": "a" * 64}

    with pytest.raises(ValueError, match="duplicate artifact snapshot label"):
        artifact_inventory_snapshots(
            {
                "agent_output.seo-optimizer": row,
                "execution_evidence": {"agent_output.seo-optimizer": row},
            }
        )


def test_canonical_artifact_rejects_workspace_escape(tmp_path: Path):
    outside = tmp_path.parent / "outside.json"
    outside.write_text("{}", encoding="utf-8")
    try:
        with pytest.raises(ValueError, match="outside workspace"):
            canonical_artifact(outside, workspace_root=tmp_path)
    finally:
        outside.unlink(missing_ok=True)


@pytest.mark.parametrize(
    "stored",
    [
        "../secret.json",
        "/absolute/path.json",
        "C:/absolute/path.json",
        "C:drive-relative.json",
        "\\\\server\\share\\a.json",
        "//server/share/a.json",
    ],
)
def test_resolve_artifact_rejects_non_relative_stored_path(tmp_path: Path, stored: str):
    with pytest.raises(ValueError, match="workspace-relative POSIX"):
        resolve_artifact(stored, workspace_root=tmp_path)


@pytest.mark.parametrize(
    "stored",
    [
        " research/evidence.json",
        "research/evidence.json ",
        "research/evidence file.json",
        "research/\tevidence.json",
        "research//evidence.json",
        "research/./evidence.json",
        "research/sub/../evidence.json",
    ],
)
def test_resolve_artifact_rejects_noncanonical_path_spelling(
    tmp_path: Path,
    stored: str,
):
    with pytest.raises(ValueError, match="canonical workspace-relative POSIX"):
        resolve_artifact(stored, workspace_root=tmp_path)


def test_resolve_artifact_rejects_case_mismatched_existing_identity(tmp_path: Path):
    artifact = tmp_path / "research" / "Evidence.json"
    artifact.parent.mkdir()
    artifact.write_text("{}", encoding="utf-8")
    if os.path.normcase("Evidence.json") != os.path.normcase("evidence.json"):
        pytest.skip("Case-sensitive filesystem identities are already distinct.")

    with pytest.raises(ValueError, match="canonical workspace-relative POSIX"):
        resolve_artifact("research/evidence.json", workspace_root=tmp_path)


def test_canonical_artifact_rejects_noncanonical_existing_filename(tmp_path: Path):
    artifact = tmp_path / "research" / "evidence file.json"
    artifact.parent.mkdir()
    artifact.write_text("{}", encoding="utf-8")

    with pytest.raises(ValueError, match="not canonical"):
        canonical_artifact(artifact, workspace_root=tmp_path)


def test_validate_sha256_requires_lowercase_64_character_digest():
    assert validate_sha256("a" * 64) == "a" * 64
    with pytest.raises(ValueError, match="lowercase SHA-256"):
        validate_sha256("A" * 64)


def test_current_assembly_date_validation_is_utc_bound_and_patchable(monkeypatch):
    monkeypatch.setattr(
        blog_assembly_contract,
        "current_utc_date",
        lambda: date(2026, 8, 11),
    )

    assert validate_current_assembly_date("2026-08-11") == date(2026, 8, 11)
    with pytest.raises(ValueError, match="current UTC date"):
        validate_current_assembly_date("2026-08-10")
    with pytest.raises(ValueError, match="current UTC date"):
        validate_current_assembly_date("2026-08-12")


def test_atomic_write_json_replaces_destination_without_temp_leak(tmp_path: Path):
    destination = tmp_path / "bom.json"
    destination.write_text('{"old": true}\n', encoding="utf-8")

    atomic_write_json(destination, {"new": True})

    assert json.loads(destination.read_text(encoding="utf-8")) == {"new": True}
    assert [path.name for path in tmp_path.iterdir()] == ["bom.json"]


def test_atomic_write_json_preserves_destination_and_cleans_temp_on_replace_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    destination = tmp_path / "bom.json"
    destination.write_text('{"old": true}\n', encoding="utf-8")

    def fail_replace(source, target):
        raise OSError("replace failed")

    monkeypatch.setattr(os, "replace", fail_replace)

    with pytest.raises(OSError, match="replace failed"):
        atomic_write_json(destination, {"new": True})

    assert json.loads(destination.read_text(encoding="utf-8")) == {"old": True}
    assert [path.name for path in tmp_path.iterdir()] == ["bom.json"]


def test_expected_gate_inventory_is_conditional_without_losing_gate_order():
    minimal = expected_blog_gate_inventory(
        visible_faq=False,
        connector_required=False,
    )
    complete = expected_blog_gate_inventory(
        visible_faq=True,
        connector_required=True,
    )

    assert "faq_answer_quality" not in minimal
    assert "faq_proof" not in minimal
    assert "vault_brand_language" not in minimal
    assert "named_feature_status" not in minimal
    assert "fred_authority" not in minimal
    assert complete.index("faq_answer_quality") < complete.index("paa_provenance")
    assert complete.index("vault_brand_language") < complete.index("fred_authority")
    assert complete[-2:] == ["content_scorer", "input_seal"]


def test_shared_gate_descriptors_order_executor_results_and_inventory():
    expected = expected_blog_gate_inventory(
        visible_faq=False,
        connector_required=False,
    )
    shuffled = [{"name": name} for name in reversed(expected)]

    ordered = order_blog_gate_results(
        shuffled,
        visible_faq=False,
        connector_required=False,
    )

    assert [row["name"] for row in ordered] == expected
