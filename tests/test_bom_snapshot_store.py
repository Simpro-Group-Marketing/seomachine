from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from data_sources.modules.readiness.inputs import ReadinessInputs
from data_sources.modules import blog_assembly_contract
from data_sources.modules.blog_assembly_bom_guard import check_bom
from tests.test_blog_assembly_bom import _build, _fixture
from tests.test_blog_assembly_bom_v4 import _upgrade_to_v4

def _write(path: Path, content: str, *, root: Path) -> dict[str, str]:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content.encode("utf-8"))
    return {
        "path": path.relative_to(root).as_posix(),
        "sha256": hashlib.sha256(content.encode("utf-8")).hexdigest(),
    }

def test_bom_expands_machine_reviews_and_nested_paa_capture_once(
    tmp_path: Path,
) -> None:
    review = tmp_path / "research" / "review.json"
    raw = tmp_path / "research" / "paa-raw.json"
    paa = tmp_path / "research" / "paa.json"
    review_row = _write(review, '{"phase":"article"}\n', root=tmp_path)
    raw_row = _write(raw, '{"schema":"raw"}\n', root=tmp_path)
    paa_row = _write(
        paa,
        json.dumps({"raw_capture": raw_row}) + "\n",
        root=tmp_path,
    )
    bom = tmp_path / "research" / "bom.json"
    bom.write_text(
        json.dumps(
            {
                "artifacts": {"paa_artifact": paa_row},
                "machine_reviews": {"article": review_row},
            }
        )
        + "\n",
        encoding="utf-8",
    )

    inputs = ReadinessInputs.capture(
        {"assembly_bom": bom},
        workspace_root=tmp_path,
    )

    assert inputs.unique_file_count == 4
    assert inputs.json_object("machine_reviews.article")["phase"] == "article"
    assert inputs.json_object("paa_raw_capture")["schema"] == "raw"

def test_row_views_never_reopen_captured_json(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = tmp_path / "record.json"
    row = _write(source, '{"schema":"captured"}\n', root=tmp_path)
    inputs = ReadinessInputs.capture({"record": source}, workspace_root=tmp_path)
    monkeypatch.setattr(
        Path,
        "read_text",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("captured JSON was reopened")
        ),
    )

    assert inputs.json_row(row, field="record")["schema"] == "captured"
    assert inputs.text_row(row, field="record") == '{"schema":"captured"}\n'

def test_row_view_rejects_an_uncaptured_or_mismatched_binding(tmp_path: Path) -> None:
    source = tmp_path / "record.json"
    row = _write(source, '{}\n', root=tmp_path)
    inputs = ReadinessInputs.capture({"record": source}, workspace_root=tmp_path)

    with pytest.raises(ValueError, match="was not captured"):
        inputs.json_row(
            {"path": "missing.json", "sha256": row["sha256"]},
            field="missing",
        )
    with pytest.raises(ValueError, match="does not match captured"):
        inputs.json_row(
            {"path": row["path"], "sha256": "0" * 64},
            field="record",
        )

def test_current_bom_gate_does_not_reopen_captured_inputs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        blog_assembly_contract,
        "current_utc_date",
        lambda: __import__("datetime").date(2026, 8, 11),
    )
    paths = _upgrade_to_v4(tmp_path)
    bom = _build(
        tmp_path,
        paths,
        plan_fulfillment_path=paths["plan_fulfillment"],
        commercial_pillar_index_path=paths["commercial_pillar_index"],
    )
    bom_path = tmp_path / "research" / "bom.json"
    bom_path.write_text(json.dumps(bom), encoding="utf-8")
    inputs = ReadinessInputs.capture(
        {
            "article": paths["article"],
            "validation_sidecar": paths["sidecar"],
            "assembly_bom": bom_path,
        },
        workspace_root=tmp_path,
    )
    captured_paths = {
        inputs.snapshot(label).path for label in inputs.hash_inventory()
    }
    original_read_text = Path.read_text
    original_read_bytes = Path.read_bytes
    def guarded_read_text(path: Path, *args, **kwargs):
        if path.resolve() in captured_paths:
            raise AssertionError("captured input was reopened with read_text")
        return original_read_text(path, *args, **kwargs)

    def guarded_read_bytes(path: Path, *args, **kwargs):
        if path.resolve() in captured_paths:
            raise AssertionError("captured input was reopened with read_bytes")
        return original_read_bytes(path, *args, **kwargs)

    monkeypatch.setattr(
        Path,
        "read_text",
        guarded_read_text,
    )
    monkeypatch.setattr(
        Path,
        "read_bytes",
        guarded_read_bytes,
    )

    findings = check_bom(
        inputs.json_row_copy(
            {
                "path": inputs.snapshot("assembly_bom").relative_path,
                "sha256": inputs.snapshot("assembly_bom").sha256,
            },
            field="assembly_bom",
        ),
        article_path=paths["article"],
        validation_sidecar_path=paths["sidecar"],
        workspace_root=tmp_path,
        expected_lifecycle_state="provisional",
        require_current_schema=True,
        captured=inputs,
    )

    assert findings == []
