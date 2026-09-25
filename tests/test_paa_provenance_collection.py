"""Focused process-boundary tests for PAA collection dependencies."""

from __future__ import annotations

import json
import subprocess
from datetime import datetime, timezone

from data_sources.modules.paa_provenance.cli import _main
from data_sources.modules.paa_provenance.dependencies import PaaDependencies


FAQ_QUESTIONS = (
    "What is the best way to schedule HVAC technicians?",
    "Should HVAC scheduling connect to invoicing?",
)


def test_record_ignores_navigation_login_text_when_valid_paa_is_observed(tmp_path):
    collection_date = datetime.now(timezone.utc).date().isoformat()
    exact_stdout = json.dumps(
        {
            "page_url": "https://answersocrates.com/",
            "page_title": "People Also Ask Extractor",
            "body_text": "Sign in Navigation People Also Ask",
            "blocker_observations": [],
            "sections": [
                {"heading": "People Also Ask", "items": list(FAQ_QUESTIONS)},
            ],
        }
    )

    def completed(command, **kwargs):
        stdout = exact_stdout if "run-code" in command else ""
        return subprocess.CompletedProcess(command, 0, stdout=stdout, stderr="")

    raw_path = tmp_path / "research" / "answersocrates-raw.json"
    output_path = tmp_path / "research" / "paa.json"
    dependencies = PaaDependencies(lambda: "npx", completed)
    exit_code = _main(
        [
            "record",
            "--query",
            "hvac technician scheduling",
            "--collection-date",
            collection_date,
            "--run-id",
            "agency-run-navigation",
            "--raw-capture-output",
            str(raw_path),
            "--workspace-root",
            str(tmp_path),
            "--output",
            str(output_path),
        ],
        dependencies=dependencies,
    )
    capture = json.loads(raw_path.read_text(encoding="utf-8"))
    artifact = json.loads(output_path.read_text(encoding="utf-8"))

    assert exit_code == 0
    assert capture["raw_response"]["stdout"] == exact_stdout
    assert artifact["status"] == "collected"
    assert artifact["blocker"] is None
    assert artifact["eligible_questions"] == list(FAQ_QUESTIONS)
