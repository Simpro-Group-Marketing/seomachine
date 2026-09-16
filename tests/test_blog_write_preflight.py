from __future__ import annotations

import json
from pathlib import Path

from data_sources.modules import blog_write_preflight


SOURCE_URL = "https://example.com/field-service-guidance"


def _write_inventory(root: Path) -> Path:
    path = root / "research" / "source-candidates.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "schema": "simpro-source-candidate-inventory/v1",
                "candidates": [{"source_url": SOURCE_URL, "decision_id": "source:missing"}],
            },
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    return path


def test_write_preflight_blocks_before_drafting_when_source_decision_is_missing(
    tmp_path: Path,
) -> None:
    inventory = _write_inventory(tmp_path)
    draft = tmp_path / "drafts" / "field-service-guide.md"
    classifications = tmp_path / "research" / "source-classifications"
    source_report = tmp_path / "research" / "source-classification-preflight.json"
    output = tmp_path / "research" / "write-preflight.json"

    exit_code = blog_write_preflight.main(
        [
            "--draft",
            str(draft),
            "--source-candidate-inventory",
            str(inventory),
            "--classification-directory",
            str(classifications),
            "--source-classification-output",
            str(source_report),
            "--output",
            str(output),
            "--workspace-root",
            str(tmp_path),
        ]
    )

    report = json.loads(output.read_text(encoding="utf-8"))
    assert exit_code == 1
    assert report["schema"] == "simpro-blog-write-preflight/v1"
    assert report["ready_for_drafting"] is False
    assert report["blockers"][0]["rule_id"] == "source_classification_decision_missing"
    assert source_report.is_file()
    assert not draft.exists()
    assert not classifications.exists()
    assert not (tmp_path / "research" / "stage-receipts" / "draft-state.json").exists()
