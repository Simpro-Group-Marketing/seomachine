from __future__ import annotations

import subprocess
from datetime import datetime
from pathlib import Path

import pytest

from scripts import research_priorities_comprehensive as priorities
from scripts import research_serp_analysis as serp


def _artifact_writer(path: Path, calls: list[str], name: str):
    def run():
        calls.append(name)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"# {name}\n", encoding="utf-8")

    return run


def test_research_orchestrator_runs_modules_and_binds_completed_status_to_artifacts(
    tmp_path,
):
    calls = []
    run_date = datetime(2026, 8, 10)
    runners = {}
    for name, spec in priorities.RESEARCH_MODULES.items():
        artifact = tmp_path / spec["artifact"].format(date="2026-08-10")
        runners[name] = _artifact_writer(artifact, calls, name)

    results = priorities.run_research_modules(
        output_dir=tmp_path,
        now=run_date,
        module_runners=runners,
        include_competitor_gaps=True,
        print_fn=lambda *args, **kwargs: None,
    )

    assert calls == list(priorities.RESEARCH_MODULES)
    assert all(row["status"] == "completed" for row in results.values())
    assert all(Path(row["artifact"]).is_file() for row in results.values())


def test_research_orchestrator_fails_lane_when_runner_does_not_write_artifact(tmp_path):
    results = priorities.run_research_modules(
        output_dir=tmp_path,
        now=datetime(2026, 8, 10),
        module_runners={"quick_wins": lambda: None},
        module_names=["quick_wins"],
        print_fn=lambda *args, **kwargs: None,
    )

    assert results["quick_wins"]["status"] == "failed"
    assert "artifact" in results["quick_wins"]["error"].lower()


def test_roadmap_contains_only_evidence_bound_completed_artifacts(tmp_path):
    artifact = tmp_path / "quick-wins-2026-08-10.md"
    artifact.write_text("# verified report\n", encoding="utf-8")
    results = {
        "quick_wins": {"status": "completed", "artifact": str(artifact)},
        "trending": {"status": "failed", "error": "source unavailable"},
        "competitor_gaps": {"status": "skipped"},
    }

    roadmap = priorities.generate_unified_roadmap(
        results,
        now=datetime(2026, 8, 10),
    )

    assert roadmap["completed_artifacts"] == [str(artifact)]
    assert roadmap["actions"] == [
        {
            "source": "Quick Wins",
            "artifact": str(artifact),
            "action": "Review the verified Quick Wins report and select supported priorities.",
        }
    ]
    assert "Trending" not in str(roadmap["actions"])
    assert "Competitor Gaps" not in str(roadmap["actions"])


def test_playwright_subprocesses_are_bounded_and_timeout_is_reported(monkeypatch, tmp_path):
    calls = []

    def fake_run(command, **kwargs):
        calls.append((command, kwargs))
        if "run-code" in command:
            raise subprocess.TimeoutExpired(command, kwargs["timeout"])
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

    monkeypatch.setattr(serp, "find_npx_executable", lambda: "npx.cmd")
    monkeypatch.setattr(serp.subprocess, "run", fake_run)
    monkeypatch.setattr(serp.tempfile, "tempdir", str(tmp_path))

    with pytest.raises(RuntimeError, match="timed out"):
        serp.run_playwright_cli_serp_capture("field service scheduling")

    assert len(calls) == 3
    assert all(call_kwargs.get("timeout", 0) > 0 for _, call_kwargs in calls)
    assert "close" in calls[-1][0]


def test_playwright_open_timeout_has_stable_runtime_error(monkeypatch):
    def fake_run(command, **kwargs):
        raise subprocess.TimeoutExpired(command, kwargs["timeout"])

    monkeypatch.setattr(serp, "find_npx_executable", lambda: "npx")
    monkeypatch.setattr(serp.subprocess, "run", fake_run)

    with pytest.raises(RuntimeError, match="open timed out"):
        serp.run_playwright_cli_serp_capture("field service scheduling")
