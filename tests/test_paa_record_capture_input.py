"""`paa_provenance record` must accept an already-collected raw capture.

The Playwright collector cannot complete a run: it drives `open`, `run-code`
and `close` as three separate processes, so the second one reports
`Browser 'default' is not open` (see
research/paa-raw-capture-digital-worker-2026-09-15.json). The chrome-connector
capture contract exists for exactly that case and is already accepted by
`build_answersocrates_artifact`, but the CLI has no way to hand it one:
`--raw-capture-output` is write-only and the collector always runs.

Without this seam every article needs a bespoke script to mint its capture
(scripts/build_subcontractors_paa_blocker.py,
scripts/build_ai_field_service_economics_browser_evidence.py).
"""

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from data_sources.modules.blog_assembly_contract import atomic_write_json
from data_sources.modules.execution_attestation import attest_mapping
from data_sources.modules.paa_provenance import collection as collection_module
from data_sources.modules.paa_provenance.cli import _record_main

CHROME_CAPTURE_SCHEMA = "simpro-answersocrates-chrome-connector-capture/v1"
QUERY = "how do i hire a subcontractor"
RUN_ID = "0f9d4c3a-7b21-4e55-9a0c-2d6e8b1f4a37"


def _write_capture(workspace_root: Path) -> tuple[Path, str]:
    """Mint the capture a Chrome-connector operator would hand the CLI."""
    completed = datetime.now(timezone.utc)
    started = completed - timedelta(seconds=45)
    collection_date = completed.strftime("%Y-%m-%d")

    # The main page is what actually carries a "People Also Ask" heading; the
    # /paa-extractor page never does.
    browser_output = {
        "page_url": "https://answersocrates.com/",
        "page_title": "AnswerSocrates",
        "body_text": "People Also Ask results for how do i hire a subcontractor.",
        "sections": [
            {
                "heading": "People Also Ask",
                "items": [
                    "How do I verify a subcontractor's insurance?",
                    "What documents should a subcontractor provide?",
                ],
            }
        ],
        "blocker_observations": [],
    }
    capture = {
        "schema": CHROME_CAPTURE_SCHEMA,
        "collector": {"name": "answersocrates_chrome_connector", "version": "1.0.0"},
        "query": QUERY,
        "run_id": RUN_ID,
        "started_at": started.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "completed_at": completed.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "page_url": "https://answersocrates.com/",
        "raw_response": {
            "stdout": json.dumps(browser_output, ensure_ascii=False),
            "stderr": "",
            "returncode": 0,
        },
    }
    capture_path = workspace_root / "raw-capture.json"
    atomic_write_json(
        capture_path,
        attest_mapping(
            capture, purpose=CHROME_CAPTURE_SCHEMA, workspace_root=workspace_root
        ),
    )
    return capture_path, collection_date


def _argv(workspace_root: Path, capture_path: Path, collection_date: str, output: Path):
    return [
        "--query",
        QUERY,
        "--collection-date",
        collection_date,
        "--run-id",
        RUN_ID,
        "--raw-capture-input",
        str(capture_path),
        "--workspace-root",
        str(workspace_root),
        "--output",
        str(output),
    ]


def test_record_builds_artifact_from_supplied_capture(tmp_path, capsys):
    capture_path, collection_date = _write_capture(tmp_path)
    output = tmp_path / "answersocrates-artifact.json"

    exit_code = _record_main(_argv(tmp_path, capture_path, collection_date, output))

    assert exit_code == 0
    artifact = json.loads(output.read_text(encoding="utf-8"))
    assert artifact["status"] == "collected"
    assert artifact["query"] == QUERY
    assert artifact["eligible_questions"] == [
        "How do I verify a subcontractor's insurance?",
        "What documents should a subcontractor provide?",
    ]
    assert artifact["run_receipt"]["receipt_hash"]

    summary = json.loads(capsys.readouterr().out)
    assert summary["status"] == "collected"


def test_supplied_capture_does_not_invoke_the_collector(tmp_path, monkeypatch):
    capture_path, collection_date = _write_capture(tmp_path)
    output = tmp_path / "answersocrates-artifact.json"

    def _fail(*args, **kwargs):
        raise AssertionError("collector ran despite an explicit raw capture input")

    monkeypatch.setattr(
        collection_module, "collect_answersocrates_raw_capture", _fail
    )

    assert _record_main(_argv(tmp_path, capture_path, collection_date, output)) == 0


def test_capture_input_and_capture_output_are_mutually_exclusive(tmp_path, capsys):
    """Collecting a capture and supplying one are opposite modes."""
    capture_path, collection_date = _write_capture(tmp_path)
    output = tmp_path / "answersocrates-artifact.json"
    argv = _argv(tmp_path, capture_path, collection_date, output) + [
        "--raw-capture-output",
        str(tmp_path / "written-capture.json"),
    ]

    with pytest.raises(SystemExit) as excinfo:
        _record_main(argv)

    assert excinfo.value.code == 2
    # Must fail on the conflict itself, not because the flag is unknown.
    assert "not allowed with" in capsys.readouterr().err


def test_neither_capture_argument_is_rejected(tmp_path, capsys):
    """One of the two modes must be chosen explicitly."""
    argv = [
        "--query",
        QUERY,
        "--collection-date",
        "2026-09-18",
        "--run-id",
        RUN_ID,
        "--workspace-root",
        str(tmp_path),
        "--output",
        str(tmp_path / "artifact.json"),
    ]

    with pytest.raises(SystemExit) as excinfo:
        _record_main(argv)

    assert excinfo.value.code == 2
    # The message must offer both modes, not demand the collector.
    stderr = capsys.readouterr().err
    assert "--raw-capture-input" in stderr and "--raw-capture-output" in stderr
