from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

import pytest

from data_sources.modules.readiness.artifact_store import InstrumentedArtifactStore
from data_sources.modules.readiness.telemetry import ReadinessTelemetry


def _write(path: Path, content: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def test_store_reads_once_and_caches_immutable_views(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    article = _write(
        tmp_path / "drafts" / "article.md",
        "---\ntags:\n  - operations\n---\n\n# Article\n\nBody.\n",
    )
    control = _write(tmp_path / "research" / "control.json", '{"rows":[1]}\n')
    reads: list[Path] = []

    from data_sources.modules.readiness import artifact_store as store_module

    original = store_module._read_bounded

    def counted(path: Path, *, max_bytes: int, field: str) -> bytes:
        reads.append(path)
        return original(path, max_bytes=max_bytes, field=field)

    monkeypatch.setattr(store_module, "_read_bounded", counted)
    telemetry = ReadinessTelemetry(run_id="store-1", phase="preflight")
    store = InstrumentedArtifactStore.capture(
        {
            "article": article,
            "article_alias": article,
            "control": control,
        },
        workspace_root=tmp_path,
        telemetry=telemetry,
    )

    assert reads == [article.resolve(), control.resolve()]
    assert store.bytes("article") == article.read_bytes()
    assert store.bytes_view("article") is store.bytes_view("article_alias")
    assert store.text_view("article") is store.text_view("article_alias")
    assert store.json_view("control") is store.json_view("control")
    assert store.markdown_view("article") is store.markdown_view("article_alias")
    assert store.markdown_view("article").h1 == "Article"
    assert store.json_object("control")["rows"] == (1,)
    with pytest.raises(TypeError):
        store.json_object("control")["rows"] = (2,)
    with pytest.raises(TypeError):
        store.markdown_view("article").metadata["tags"] = ("changed",)

    telemetry.finish("passed")
    counters = telemetry.to_dict()["counters"]
    assert counters["byte_snapshots"] == 2
    assert counters["json_parses"] == 1
    assert counters["markdown_parses"] == 1
    assert telemetry.to_dict()["gauges"]["artifact_store_source_bytes"] == (
        len(article.read_bytes()) + len(control.read_bytes())
    )


def test_store_expands_bom_and_returns_deterministic_inventories(tmp_path: Path):
    article = _write(tmp_path / "drafts" / "article.md", "# Article\n")
    sidecar = _write(tmp_path / "research" / "validation.md", "# Validation\n")
    bom = {
        "artifacts": {
            "validation_sidecar": {
                "path": "research/validation.md",
                "sha256": hashlib.sha256(sidecar.read_bytes()).hexdigest(),
            },
            "article": {
                "path": "drafts/article.md",
                "sha256": hashlib.sha256(article.read_bytes()).hexdigest(),
            },
        }
    }
    bom_path = tmp_path / "research" / "bom.json"
    bom_path.write_text(json.dumps(bom), encoding="utf-8")

    store = InstrumentedArtifactStore.capture(
        {"z_alias": sidecar, "assembly_bom": bom_path},
        workspace_root=tmp_path,
    )

    inventory = store.hash_inventory()
    assert list(inventory) == sorted(inventory)
    assert inventory["article"]["path"] == "drafts/article.md"
    assert inventory["validation_sidecar"]["path"] == "research/validation.md"
    assert store.unique_file_count == 3


def test_store_expands_serp_raw_capture_bound_by_bom_evidence(tmp_path: Path):
    raw_capture = _write(
        tmp_path / "research" / "serp-raw.json",
        '{"schema":"simpro-serp-raw-capture/v1"}\n',
    )
    raw_digest = hashlib.sha256(raw_capture.read_bytes()).hexdigest()
    serp_evidence = _write(
        tmp_path / "research" / "serp-evidence.json",
        json.dumps(
            {
                "schema": "simpro-serp-evidence/v1",
                "raw_capture": {
                    "path": "research/serp-raw.json",
                    "sha256": raw_digest,
                },
            }
        ),
    )
    bom_path = tmp_path / "research" / "bom.json"
    bom_path.write_text(
        json.dumps(
            {
                "artifacts": {
                    "serp_evidence": {
                        "path": "research/serp-evidence.json",
                        "sha256": hashlib.sha256(
                            serp_evidence.read_bytes()
                        ).hexdigest(),
                    }
                }
            }
        ),
        encoding="utf-8",
    )

    store = InstrumentedArtifactStore.capture(
        {"assembly_bom": bom_path},
        workspace_root=tmp_path,
    )

    assert store.json_object("serp_raw_capture")["schema"] == (
        "simpro-serp-raw-capture/v1"
    )
    assert store.hash_inventory()["serp_raw_capture"] == {
        "path": "research/serp-raw.json",
        "sha256": raw_digest,
    }


def test_store_rejects_mismatched_serp_raw_capture_hash(tmp_path: Path):
    _write(tmp_path / "research" / "serp-raw.json", "{}\n")
    serp_evidence = _write(
        tmp_path / "research" / "serp-evidence.json",
        json.dumps(
            {
                "raw_capture": {
                    "path": "research/serp-raw.json",
                    "sha256": "0" * 64,
                }
            }
        ),
    )
    bom_path = tmp_path / "research" / "bom.json"
    bom_path.write_text(
        json.dumps(
            {
                "artifacts": {
                    "serp_evidence": {
                        "path": "research/serp-evidence.json",
                        "sha256": hashlib.sha256(
                            serp_evidence.read_bytes()
                        ).hexdigest(),
                    }
                }
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="serp_raw_capture.*SHA-256"):
        InstrumentedArtifactStore.capture(
            {"assembly_bom": bom_path},
            workspace_root=tmp_path,
        )


def test_reseal_streams_once_and_detects_same_content_replacement(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    article = _write(tmp_path / "article.md", "same bytes\n")
    telemetry = ReadinessTelemetry(run_id="reseal-1", phase="final")
    store = InstrumentedArtifactStore.capture(
        {"article": article, "duplicate": article},
        workspace_root=tmp_path,
        telemetry=telemetry,
    )
    calls: list[Path] = []

    from data_sources.modules.readiness import artifact_store as store_module

    original = store_module._stream_sha256

    def counted(path: Path) -> str:
        calls.append(path)
        return original(path)

    monkeypatch.setattr(store_module, "_stream_sha256", counted)
    sealed = store.reseal()
    assert calls == [article.resolve()]
    assert sealed == store.release_inventory()
    telemetry.finish("passed")
    counters = telemetry.to_dict()["counters"]
    assert counters["final_reseals"] == 1
    assert counters["final_rehashes"] == 1

    replacement = _write(tmp_path / "replacement.md", "same bytes\n")
    os.replace(replacement, article)
    with pytest.raises(ValueError, match="changed during readiness"):
        store.reseal()


def test_text_and_json_views_reject_wrong_content_types(tmp_path: Path):
    binary = tmp_path / "binary.bin"
    binary.write_bytes(b"\xff")
    scalar = _write(tmp_path / "scalar.json", "[1, 2]\n")
    store = InstrumentedArtifactStore.capture(
        {"binary": binary, "scalar": scalar},
        workspace_root=tmp_path,
    )

    assert store.bytes("binary") == b"\xff"
    with pytest.raises(ValueError, match="valid UTF-8"):
        store.text("binary")
    with pytest.raises(ValueError, match="JSON object"):
        store.json_object("scalar")


def test_reseal_rejects_in_place_change_and_restore(tmp_path: Path):
    article = _write(tmp_path / "article.md", "original\n")
    store = InstrumentedArtifactStore.capture(
        {"article": article},
        workspace_root=tmp_path,
    )

    article.write_text("changed!\n", encoding="utf-8")
    article.write_text("original\n", encoding="utf-8")

    with pytest.raises(ValueError, match="changed during readiness"):
        store.reseal()


def test_store_rejects_duplicate_json_keys_and_workspace_escape(tmp_path: Path):
    duplicate = _write(tmp_path / "duplicate.json", '{"same":1,"same":2}\n')
    duplicate_store = InstrumentedArtifactStore.capture(
        {"control": duplicate},
        workspace_root=tmp_path,
    )
    with pytest.raises(ValueError, match="duplicate"):
        duplicate_store.json_object("control")

    outside = _write(tmp_path.parent / "outside-readiness.md", "# Outside\n")
    with pytest.raises(ValueError, match="outside workspace"):
        InstrumentedArtifactStore.capture(
            {"article": outside},
            workspace_root=tmp_path,
        )


def test_store_rejects_direct_and_bom_label_conflict(tmp_path: Path):
    direct = _write(tmp_path / "direct.md", "# Direct\n")
    declared = _write(tmp_path / "declared.md", "# Declared\n")
    bom_path = tmp_path / "bom.json"
    bom_path.write_text(
        json.dumps(
            {
                "artifacts": {
                    "article": {
                        "path": "declared.md",
                        "sha256": hashlib.sha256(declared.read_bytes()).hexdigest(),
                    }
                }
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="duplicate readiness input label"):
        InstrumentedArtifactStore.capture(
            {"article": direct, "assembly_bom": bom_path},
            workspace_root=tmp_path,
        )


def test_markdown_parse_failure_is_cached_at_the_store_boundary(tmp_path: Path):
    malformed = _write(tmp_path / "article.md", "---\ninvalid: [\n---\n# Article\n")
    store = InstrumentedArtifactStore.capture(
        {"article": malformed},
        workspace_root=tmp_path,
    )

    with pytest.raises(ValueError):
        store.markdown_view("article")
