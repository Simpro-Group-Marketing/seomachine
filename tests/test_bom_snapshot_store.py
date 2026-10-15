from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from data_sources.modules.readiness.inputs import ReadinessInputs

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
