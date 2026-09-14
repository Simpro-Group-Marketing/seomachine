from __future__ import annotations

import hashlib
import json
import subprocess
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest

from data_sources.modules.blog_assembly_contract import load_json_object_snapshot
from data_sources.modules import source_support_guard  # noqa: F401
from data_sources.modules.readiness.session import GitRegistryState, ValidationSession
from data_sources.modules.readiness.telemetry import ReadinessTelemetry
from data_sources.modules.readiness.git_registry import capture_git_registry_state
from data_sources.modules.source_support import classification


SOURCE_URL = "https://example.com/scheduling-guidance"
REGISTRY_RELATIVE_PATH = Path("context/source-classification-decisions.json")


def _run_git(root: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", "-C", str(root), *args],
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


def _committed_registry(root: Path) -> tuple[Path, dict[str, Any]]:
    payload = {
        "schema": "simpro-source-classification-decisions/v1",
        "revision": "revision-1",
        "decisions": [
            {
                "decision_id": "source:test-record",
                "status": "approved",
                "source_url": SOURCE_URL,
                "hostname": "example.com",
                "source_class": "non_competing_expert",
                "publisher_relationship": "independent",
            }
        ],
    }
    registry = root / REGISTRY_RELATIVE_PATH
    registry.parent.mkdir(parents=True)
    registry.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
    _run_git(root, "init", "-q")
    _run_git(root, "config", "user.email", "tests@example.com")
    _run_git(root, "config", "user.name", "Tests")
    _run_git(root, "add", REGISTRY_RELATIVE_PATH.as_posix())
    _run_git(root, "commit", "-qm", "approve source decisions")
    return registry, payload


def _session(root: Path, telemetry: ReadinessTelemetry | None = None) -> ValidationSession:
    article = root / "article.md"
    article.write_text("# Article\n", encoding="utf-8")
    return ValidationSession.capture(
        {"article": article},
        workspace_root=root,
        telemetry=telemetry,
    )


def _classification_payload() -> dict[str, Any]:
    return {
        "source_url": SOURCE_URL,
        "source_class": "non_competing_expert",
        "publisher": {
            "hostname": "example.com",
            "relationship": "independent",
        },
        "registry": {
            "authority_mode": "repository_decision",
            "record_id": "source:test-record",
            "revision": "revision-1",
            "decision_path": REGISTRY_RELATIVE_PATH.as_posix(),
            "decision_sha256": "",
        },
    }


def test_session_captures_and_caches_committed_registry_state_once(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    registry, payload = _committed_registry(tmp_path)
    telemetry = ReadinessTelemetry(run_id="git-state", phase="preflight")
    loads: list[Path] = []
    commands: list[tuple[str, ...]] = []
    process_inputs: list[bytes | None] = []

    from data_sources.modules.readiness import git_registry

    original = git_registry.run_bounded_process

    def counted_process(args, **kwargs):
        commands.append(tuple(args))
        process_inputs.append(kwargs.get("input_bytes"))
        return original(args, **kwargs)

    monkeypatch.setattr(git_registry, "run_bounded_process", counted_process)

    def loader():
        loads.append(registry)
        return load_json_object_snapshot(registry, field="source decision registry")

    with _session(tmp_path, telemetry) as session:
        first = session.git_registry_state(registry, loader)
        second = session.git_registry_state(registry.parent / "." / registry.name, loader)

        assert isinstance(first, GitRegistryState)
        assert first is second
        assert first.registry_path == registry.resolve()
        assert first.repository_root == tmp_path.resolve()
        assert first.relative_path == REGISTRY_RELATIVE_PATH.as_posix()
        assert first.head == _run_git(tmp_path, "rev-parse", "--verify", "HEAD")
        assert first.registry_sha256 == hashlib.sha256(registry.read_bytes()).hexdigest()
        assert first.committed_blob_sha256 == first.registry_sha256
        assert first.byte_count == len(registry.read_bytes())
        assert first.payload["revision"] == payload["revision"]
        with pytest.raises(TypeError):
            first.payload["revision"] = "changed"

    assert loads == [registry]
    assert [command[3] for command in commands] == ["cat-file"]
    assert commands[0][4:] == (
        "--batch-command",
        "-z",
    )
    assert process_inputs == [
        b"info HEAD\0contents HEAD:context/source-classification-decisions.json\0"
    ]
    telemetry.finish("passed")
    assert telemetry.to_dict()["counters"]["git_state_loads"] == 1


def test_session_does_not_cache_registry_that_differs_from_head(tmp_path: Path):
    registry, _ = _committed_registry(tmp_path)
    original = registry.read_bytes()
    loads: list[str] = []

    def loader():
        loads.append("load")
        return load_json_object_snapshot(registry, field="source decision registry")

    with _session(tmp_path) as session:
        registry.write_bytes(original + b"\n")
        with pytest.raises(ValueError, match="committed HEAD blob"):
            session.git_registry_state(registry, loader)
        registry.write_bytes(original)
        state = session.git_registry_state(registry, loader)

    assert state.registry_sha256 == hashlib.sha256(original).hexdigest()
    assert loads == ["load", "load"]


def test_registry_state_rejects_nested_workspace_in_parent_repository(
    tmp_path: Path,
) -> None:
    registry, _ = _committed_registry(tmp_path)
    nested = tmp_path / "nested"
    nested.mkdir()
    nested_registry = nested / "registry.json"
    nested_registry.write_bytes(registry.read_bytes())
    _run_git(tmp_path, "add", "nested/registry.json")
    _run_git(tmp_path, "commit", "-qm", "add nested registry")

    snapshot = load_json_object_snapshot(
        nested_registry,
        field="source decision registry",
    )
    with pytest.raises(ValueError, match="committed HEAD blob"):
        capture_git_registry_state(snapshot, workspace_root=nested)


def test_classification_accepts_cached_state_without_loading_or_verifying_again(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    registry, _ = _committed_registry(tmp_path)
    with _session(tmp_path) as session:
        state = session.git_registry_state(
            registry,
            lambda: load_json_object_snapshot(registry, field="source decision registry"),
        )
        payload = _classification_payload()
        payload["registry"]["decision_sha256"] = state.registry_sha256
        monkeypatch.setattr(
            classification,
            "load_json_object_snapshot",
            lambda *args, **kwargs: (_ for _ in ()).throw(
                AssertionError("classification reopened the cached registry")
            ),
        )
        verifier_calls: list[object] = []

        result = classification._validate_classification_decision(
            payload,
            classification_path=tmp_path / "source-classification.json",
            base_path=tmp_path,
            registry_state=lambda: state,
            registry_verifier=lambda *args, **kwargs: verifier_calls.append(args),
        )

    assert result is None
    assert verifier_calls == []


def test_classification_accepts_supplied_snapshot_and_verifier(tmp_path: Path):
    registry, _ = _committed_registry(tmp_path)
    snapshot = load_json_object_snapshot(registry, field="source decision registry")
    payload = _classification_payload()
    payload["registry"]["decision_sha256"] = snapshot.sha256
    calls: list[tuple[object, Path]] = []

    def verifier(value: object, *, workspace_root: str | Path) -> None:
        calls.append((value, Path(workspace_root)))

    result = classification._validate_classification_decision(
        payload,
        classification_path=tmp_path / "source-classification.json",
        base_path=tmp_path,
        registry_snapshot=snapshot,
        registry_verifier=verifier,
    )

    assert result is None
    assert calls == [(snapshot, tmp_path.resolve())]


def test_classification_rejects_mismatched_cached_registry_state(tmp_path: Path):
    registry, _ = _committed_registry(tmp_path)
    with _session(tmp_path) as session:
        state = session.git_registry_state(
            registry,
            lambda: load_json_object_snapshot(registry, field="source decision registry"),
        )
        payload = _classification_payload()
        payload["registry"]["decision_sha256"] = state.registry_sha256
        mismatched = replace(state, relative_path="context/other-registry.json")

        result = classification._validate_classification_decision(
            payload,
            classification_path=tmp_path / "source-classification.json",
            base_path=tmp_path,
            registry_state=mismatched,
        )

    assert result == "source_classification_decision_tampered"


def test_check_content_threads_cached_registry_state_to_classification(
    tmp_path: Path,
):
    registry, _ = _committed_registry(tmp_path)
    artifact = tmp_path / "source-classification.json"
    source_support_guard.write_source_classification_artifact(
        artifact,
        source_url=SOURCE_URL,
        decision_id="source:test-record",
        decision_path=registry,
        workspace_root=tmp_path,
    )
    artifact_hash = hashlib.sha256(artifact.read_bytes()).hexdigest()
    claim = "Field service leaders should review capacity before dispatch."
    content = f"""---
Source Map:
- Claim: {claim} | Claim type: recommendation | Source class: non_competing_expert | Evidence relation: directly_supports | Classification artifact: {artifact.name} | Classification hash: {artifact_hash} | URL: {SOURCE_URL} | Evidence: "{claim}" | Status: approved
---

# Scheduling guide

{claim}
"""
    with _session(tmp_path) as session:
        state = session.git_registry_state(
            registry,
            lambda: load_json_object_snapshot(registry, field="source decision registry"),
        )
        def unexpected_registry_verifier(*args, **kwargs):
            raise AssertionError("cached state must bypass Git verification")

        findings = source_support_guard.check_content(
            content,
            base_path=tmp_path,
            fetcher=lambda url: claim,
            registry_state=state,
            registry_verifier=unexpected_registry_verifier,
        )

    assert findings == []
