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
            "scoring_imports": [] if phase_value == 1 else ["textstat"],
        }

    monkeypatch.setattr(benchmark_release, "_run_once", fake_run_once)
    monkeypatch.setattr(
        benchmark_release,
        "_prepare_fixture",
        lambda runtime_root: preparations.append(runtime_root),
    )
    monkeypatch.setattr(benchmark_release, "_commit", lambda repository: "a" * 40)
    monkeypatch.setattr(benchmark_release, "_is_dirty", lambda repository: True)

    result = benchmark_release.run_benchmark(tmp_path, samples=2, node="test_node")

    assert result["schema"] == "simpro-offline-release-benchmark/v2"
    assert result["repository_dirty"] is True
    assert len(result["samples"]) == 2
    assert set(result["samples"][0]) == {"cold", "warm"}
    assert result["summary"]["median_cold_wall_ms"] == 4.0
    assert result["summary"]["median_warm_wall_ms"] == 5.0
    assert result["summary"]["median_peak_rss_bytes"] == 100
    assert result["summary"]["median_cold_pre_fixture_ms"] == 2.5
    assert result["summary"]["median_warm_pre_fixture_ms"] == 3.5
    assert result["summary"]["median_cold_process_overhead_ms"] == 0.5
    assert result["summary"]["median_warm_process_overhead_ms"] == 0.5
    assert result["boundary_counters"]["cold"]["unique_file_reads"] == 1
    assert result["boundary_counters"]["warm"]["unique_file_reads"] == 2
    assert result["scoring_imports"] == {"cold": [], "warm": ["textstat"]}
    assert len(calls) == 6
    assert preparations == [calls[0], calls[2], calls[4]]
    assert calls[0] == calls[1]
    assert calls[2] == calls[3]
    assert calls[4] == calls[5]
    assert len({calls[0], calls[2], calls[4]}) == 3


def test_isolated_fixture_observes_real_session_boundaries(tmp_path: Path) -> None:
    benchmark_release._prepare_fixture(tmp_path)

    cold = benchmark_release._run_fixture(tmp_path)
    warm = benchmark_release._run_fixture(tmp_path)

    for result in (cold, warm):
        counters = result["counters"]
        assert counters["unique_file_reads"] == 2
        assert counters["file_hashes"] == 2
        assert counters["byte_snapshots"] == 2
        assert counters["markdown_parses"] == 1
        assert counters["json_parses"] == 1
        assert counters["git_state_loads"] == 1
        assert counters["connector_clients"] == 1
        assert counters["connector_operations"] == 2
        assert counters["connector_result_cache_misses"] == 1
        assert counters["connector_result_cache_hits"] == 1
        assert counters["normalized_source_parses"] == 1
        assert counters["normalized_source_cache_hits"] == 1
        assert counters["http_deduplicated_occurrences"] == 1
        assert counters["final_reseals"] == 1
        assert counters["final_rehashes"] == 2
        assert result["scoring_imports"] == []

    assert cold["counters"]["http_requests"] == 1
    assert cold["counters"]["cache_misses"] == 1
    assert cold["counters"]["cache_hits"] == 1
    assert warm["counters"]["http_requests"] in {0, 1}
    assert warm["counters"]["cache_misses"] == warm["counters"]["http_requests"]
    assert warm["counters"]["cache_hits"] == 2 - warm["counters"]["http_requests"]
