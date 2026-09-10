from __future__ import annotations

import json
from pathlib import Path

import pytest

from data_sources.modules.readiness.telemetry import ReadinessTelemetry


def test_telemetry_records_stages_counters_and_atomic_output(tmp_path: Path):
    telemetry = ReadinessTelemetry(run_id="run-1", phase="preflight")
    telemetry.increment("full_readiness_executions")
    telemetry.increment("unique_file_reads", 2)
    with telemetry.stage("context_binding"):
        telemetry.increment("connector_operations")
    telemetry.finish("passed")

    output = tmp_path / "release-telemetry.json"
    telemetry.write(output)
    payload = json.loads(output.read_text(encoding="utf-8"))

    assert payload["schema"] == "simpro-readiness-telemetry/v1"
    assert payload["run_id"] == "run-1"
    assert payload["phase"] == "preflight"
    assert payload["outcome"] == "passed"
    assert payload["elapsed_ms"] >= 0
    assert payload["counters"]["full_readiness_executions"] == 1
    assert payload["counters"]["unique_file_reads"] == 2
    assert payload["stages"][0]["name"] == "context_binding"
    assert payload["stages"][0]["elapsed_ms"] >= 0
    assert not list(tmp_path.glob("*.tmp"))


def test_telemetry_rejects_unknown_counters_and_sensitive_values(tmp_path: Path):
    telemetry = ReadinessTelemetry(run_id="run-1", phase="final")
    with pytest.raises(ValueError, match="unknown telemetry counter"):
        telemetry.increment("article_text")

    telemetry.finish("blocked")
    payload = telemetry.to_dict()
    serialized = json.dumps(payload)
    assert "proof_content" not in serialized
    assert "claims" not in serialized


def test_telemetry_cannot_finish_twice():
    telemetry = ReadinessTelemetry(run_id="run-1", phase="preflight")
    telemetry.finish("passed")
    with pytest.raises(ValueError, match="already finished"):
        telemetry.finish("passed")


def test_stage_exception_persists_operational_telemetry(tmp_path: Path):
    output = tmp_path / "release-telemetry.json"
    telemetry = ReadinessTelemetry(
        run_id="run-1",
        phase="release",
        failure_output=output,
    )

    with pytest.raises(OSError, match="boundary failed"):
        with telemetry.stage("preflight_readiness"):
            raise OSError("boundary failed")

    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["outcome"] == "operational_error"
    assert payload["stages"] == [
        {
            "name": "preflight_readiness",
            "elapsed_ms": payload["stages"][0]["elapsed_ms"],
            "outcome": "error",
            "counters": {},
        }
    ]
