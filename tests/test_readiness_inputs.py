from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from data_sources.modules.readiness.inputs import ReadinessInputs
from data_sources.modules.readiness.telemetry import ReadinessTelemetry


def _write(path: Path, content: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def test_capture_reads_duplicate_paths_once(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    article = _write(
        tmp_path / "drafts" / "article.md",
        "---\nartifact_type: blog\n---\n\n# Article\n\nBody.\n",
    )
    sidecar = _write(tmp_path / "research" / "validation.md", "# Validation\n")
    observed: list[Path] = []

    from data_sources.modules.readiness import inputs as inputs_module

    original = inputs_module._read_bounded

    def counted(path: Path, *, max_bytes: int, field: str) -> bytes:
        observed.append(path.resolve())
        return original(path, max_bytes=max_bytes, field=field)

    monkeypatch.setattr(inputs_module, "_read_bounded", counted)
    captured = ReadinessInputs.capture(
        {
            "article": article,
            "validation_sidecar": sidecar,
            "duplicate_sidecar": sidecar,
        },
        workspace_root=tmp_path,
    )

    assert observed.count(article.resolve()) == 1
    assert observed.count(sidecar.resolve()) == 1
    assert captured.snapshot("validation_sidecar") is captured.snapshot("duplicate_sidecar")
    assert captured.text("article").startswith("---")
    assert captured.hash_inventory()["article"] == {
        "path": "drafts/article.md",
        "sha256": hashlib.sha256(article.read_bytes()).hexdigest(),
    }


def test_capture_expands_bom_inventory_without_rereading_direct_inputs(tmp_path: Path):
    article = _write(tmp_path / "drafts" / "article.md", "# Article\n")
    sidecar = _write(tmp_path / "research" / "validation.md", "# Validation\n")
    bom = {
        "artifacts": {
            "article": {
                "path": "drafts/article.md",
                "sha256": hashlib.sha256(article.read_bytes()).hexdigest(),
            },
            "validation_sidecar": {
                "path": "research/validation.md",
                "sha256": hashlib.sha256(sidecar.read_bytes()).hexdigest(),
            },
        }
    }
    bom_path = tmp_path / "research" / "bom.json"
    bom_path.write_text(json.dumps(bom), encoding="utf-8")

    captured = ReadinessInputs.capture(
        {
            "article": article,
            "validation_sidecar": sidecar,
            "assembly_bom": bom_path,
        },
        workspace_root=tmp_path,
    )

    inventory = captured.hash_inventory()
    assert inventory["article"]["sha256"] == bom["artifacts"]["article"]["sha256"]
    assert inventory["validation_sidecar"]["sha256"] == (
        bom["artifacts"]["validation_sidecar"]["sha256"]
    )
    assert inventory["assembly_bom"]["path"] == "research/bom.json"


def test_capture_rejects_oversized_text_and_invalid_utf8(tmp_path: Path):
    oversized = tmp_path / "oversized.md"
    oversized.write_bytes(b"x" * (1024 * 1024 + 1))
    with pytest.raises(ValueError, match="exceeds 1048576 bytes"):
        ReadinessInputs.capture({"article": oversized}, workspace_root=tmp_path)

    invalid = tmp_path / "invalid.md"
    invalid.write_bytes(b"\xff")
    with pytest.raises(ValueError, match="valid UTF-8"):
        ReadinessInputs.capture({"article": invalid}, workspace_root=tmp_path)


def test_reseal_hashes_each_unique_file_once_and_detects_change(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    article = _write(tmp_path / "article.md", "before\n")
    captured = ReadinessInputs.capture(
        {"article": article, "duplicate": article},
        workspace_root=tmp_path,
    )
    from data_sources.modules.readiness import inputs as inputs_module

    calls: list[Path] = []
    original = inputs_module._stream_sha256

    def counted(path: Path) -> str:
        calls.append(path.resolve())
        return original(path)

    monkeypatch.setattr(inputs_module, "_stream_sha256", counted)
    captured.reseal()
    assert calls == [article.resolve()]

    article.write_text("after\n", encoding="utf-8")
    with pytest.raises(ValueError, match="changed during readiness"):
        captured.reseal()


def test_json_payload_is_deeply_immutable(tmp_path: Path):
    source = _write(tmp_path / "control.json", '{"nested":{"items":["one"]}}\n')
    captured = ReadinessInputs.capture({"control": source}, workspace_root=tmp_path)
    payload = captured.json_object("control")
    assert captured.snapshot("control").text is None

    with pytest.raises(TypeError):
        payload["nested"]["items"][0] = "changed"


def test_capture_and_reseal_report_exact_io_counters(tmp_path: Path):
    first = _write(tmp_path / "first.md", "first\n")
    second = _write(tmp_path / "second.json", '{"value":2}\n')
    telemetry = ReadinessTelemetry(run_id="run-1", phase="preflight")

    captured = ReadinessInputs.capture(
        {"first": first, "duplicate": first, "second": second},
        workspace_root=tmp_path,
        telemetry=telemetry,
    )
    captured.reseal()
    telemetry.finish("passed")

    counters = telemetry.to_dict()["counters"]
    assert counters["unique_file_reads"] == 2
    assert counters["bytes_read"] == len(first.read_bytes()) + len(second.read_bytes())
    assert counters["file_hashes"] == 2
    assert counters["final_rehashes"] == 2
