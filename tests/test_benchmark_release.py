from __future__ import annotations

from pathlib import Path

from tools import benchmark_release


def test_benchmark_records_distinct_cold_and_warm_samples(
    tmp_path: Path,
    monkeypatch,
) -> None:
    (tmp_path / "pytest.ini").write_text("[pytest]\n", encoding="utf-8")
    calls: list[Path] = []
    preparations: list[Path] = []

    def fake_run_once(repository: Path, *, node: str, runtime_root: Path):
        del repository, node
        phase_value = 1 if len(calls) % 2 == 0 else 2
        calls.append(runtime_root)
        return {
            "wall_ms": float(len(calls)),
            "child_elapsed_ms": float(len(calls)) - 0.5,
            "fixture_elapsed_ms": 1.0,
            "peak_rss_bytes": 100,
            "counters": {
                name: phase_value for name in benchmark_release.BENCHMARK_COUNTERS
            },
            "gauges": {
                name: phase_value for name in benchmark_release.BENCHMARK_GAUGES
            },
            "scoring_imports": [] if phase_value == 1 else ["textstat"],
            "exit_phase": "session_complete",
            "exit_code": 0,
            "final_authorization_result": None,
        }

    monkeypatch.setattr(benchmark_release, "_run_once", fake_run_once)
    monkeypatch.setattr(
        benchmark_release,
        "_prepare_fixture",
        lambda runtime_root: preparations.append(runtime_root),
    )
    monkeypatch.setattr(benchmark_release, "_commit", lambda repository: "a" * 40)
    monkeypatch.setattr(benchmark_release, "_is_dirty", lambda repository: True)

    result = benchmark_release.run_benchmark(
        tmp_path,
        samples=2,
        nodes=(benchmark_release.DEFAULT_NODE,),
    )

    assert result["schema"] == "simpro-offline-release-benchmark/v3"
    assert result["repository_dirty"] is True
    assert result["fixture"] == "multi-scenario-release-suite/v1"
    assert result["harness_sha256"]
    scenario = result["scenarios"][benchmark_release.DEFAULT_NODE]
    assert scenario["summary"]["exit_phase"] == "session_complete"
    assert len(result["samples"]) == 2
    assert set(result["samples"][0]) == {"cold", "warm"}
    assert scenario["summary"]["median_cold_wall_ms"] == 4.0
    assert scenario["summary"]["median_warm_wall_ms"] == 5.0
    assert scenario["summary"]["median_peak_rss_bytes"] == 100
    assert scenario["summary"]["median_cold_pre_fixture_ms"] == 2.5
    assert scenario["summary"]["median_warm_pre_fixture_ms"] == 3.5
    assert scenario["summary"]["median_cold_process_overhead_ms"] == 0.5
    assert scenario["summary"]["median_warm_process_overhead_ms"] == 0.5
    assert result["boundary_counters"]["cold"]["unique_file_reads"] == 1
    assert result["boundary_counters"]["warm"]["unique_file_reads"] == 2
    assert result["scoring_imports"] == {"cold": [], "warm": ["textstat"]}
    assert len(calls) == 6
    assert preparations == [calls[0], calls[2], calls[4]]
    assert calls[0] == calls[1]
    assert calls[2] == calls[3]
    assert calls[4] == calls[5]
    assert len({calls[0], calls[2], calls[4]}) == 3
