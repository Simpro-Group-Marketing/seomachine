from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

import pytest

from data_sources.modules.blog_assembly_contract import (
    atomic_write_json,
    canonical_artifact,
    resolve_artifact,
    validate_governance_output_path,
    validate_sha256,
)


@pytest.mark.parametrize(
    "public_directory",
    ["drafts", "rewrites", "published", "review-required"],
)
def test_governance_outputs_cannot_target_public_article_directories(
    tmp_path: Path,
    public_directory: str,
):
    destination = tmp_path / public_directory / "receipt.json"

    with pytest.raises(ValueError, match="public article director"):
        validate_governance_output_path(destination)
    with pytest.raises(ValueError, match="public article director"):
        atomic_write_json(destination, {"governance": True})

    assert not destination.exists()


def test_governance_outputs_cannot_overwrite_an_input(tmp_path: Path):
    article = tmp_path / "article.md"
    article.write_text("# Article\n", encoding="utf-8")

    with pytest.raises(ValueError, match="cannot overwrite input"):
        validate_governance_output_path(article, inputs={"article": article})


def test_canonical_artifact_stores_workspace_relative_posix_path_and_hash(tmp_path: Path):
    artifact = tmp_path / "research" / "evidence.json"
    artifact.parent.mkdir()
    artifact.write_text('{"ok": true}\n', encoding="utf-8")

    row = canonical_artifact(artifact, workspace_root=tmp_path)

    assert row == {
        "path": "research/evidence.json",
        "sha256": hashlib.sha256(artifact.read_bytes()).hexdigest(),
    }


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

