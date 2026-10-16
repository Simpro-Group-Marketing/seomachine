from __future__ import annotations

from pathlib import Path

from data_sources.modules.readiness import api as readiness_api
from data_sources.modules.readiness import snapshot_gates
from data_sources.modules.readiness.inputs import ReadinessInputs


def test_early_blocked_result_is_resealed_and_hash_bound(tmp_path: Path) -> None:
    article = tmp_path / "article.md"
    article.write_text(
        "---\nartifact_type: unsupported\n---\n# Article\n",
        encoding="utf-8",
    )

    result = readiness_api.run_publish_readiness(
        article,
        workspace_root=tmp_path,
    )

    assert result["passed"] is False
    assert result["score_threshold"] == 75
    assert result["input_seal"] == {"status": "verified"}
    assert result["input_hashes"]["article"]["path"] == "article.md"
    assert len(result["input_hashes"]["article"]["sha256"]) == 64


def test_source_registry_state_is_loaded_from_captured_bytes(tmp_path: Path) -> None:
    registry = tmp_path / "registry.json"
    registry.write_text('{"schema":"registry"}\n', encoding="utf-8")
    inputs = ReadinessInputs.capture(
        {"source_decision_registry": registry},
        workspace_root=tmp_path,
    )
    received: list[object] = []

    class RecordingSession:
        def git_registry_state(self, path, loader):
            source = loader()
            received.extend([path, source])
            return "verified-state"

    state = snapshot_gates.source_registry_state(RecordingSession(), inputs)

    assert state is not None
    assert state() == "verified-state"
    assert received[0] == registry
    assert received[1].data == registry.read_bytes()
    assert received[1].payload == {"schema": "registry"}
