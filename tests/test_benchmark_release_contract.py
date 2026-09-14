from __future__ import annotations

from pathlib import Path

from tools import benchmark_release


def test_authoritative_benchmark_refuses_dirty_repository(
    tmp_path: Path,
    monkeypatch,
) -> None:
    (tmp_path / "pytest.ini").write_text("[pytest]\n", encoding="utf-8")
    monkeypatch.setattr(benchmark_release, "_is_dirty", lambda repository: True)

    try:
        benchmark_release.run_benchmark(
            tmp_path,
            samples=1,
            nodes=(benchmark_release.DEFAULT_NODE,),
            authoritative=True,
        )
    except RuntimeError as error:
        assert "clean worktree" in str(error)
    else:
        raise AssertionError("authoritative dirty repository should fail")


def test_benchmark_summarizes_variable_gauges(tmp_path: Path, monkeypatch) -> None:
    (tmp_path / "pytest.ini").write_text("[pytest]\n", encoding="utf-8")
    calls = 0

    def fake_run_once(repository: Path, *, node: str, runtime_root: Path):
        nonlocal calls
        del repository, node, runtime_root
        calls += 1
        return {
            "wall_ms": 1.0,
            "child_elapsed_ms": 1.0,
            "fixture_elapsed_ms": 1.0,
            "peak_rss_bytes": 100 + calls,
            "counters": {name: 1 for name in benchmark_release.BENCHMARK_COUNTERS},
            "gauges": {name: calls for name in benchmark_release.BENCHMARK_GAUGES},
            "scoring_imports": [],
            "exit_phase": "session_complete",
            "exit_code": 0,
            "final_authorization_result": None,
        }

    monkeypatch.setattr(benchmark_release, "_run_once", fake_run_once)
    monkeypatch.setattr(benchmark_release, "_prepare_fixture", lambda runtime_root: None)
    monkeypatch.setattr(benchmark_release, "_commit", lambda repository: "a" * 40)
    monkeypatch.setattr(benchmark_release, "_is_dirty", lambda repository: False)

    result = benchmark_release.run_benchmark(
        tmp_path,
        samples=2,
        nodes=(benchmark_release.DEFAULT_NODE,),
    )

    gauge = benchmark_release.BENCHMARK_GAUGES[0]
    cold = result["scenarios"][benchmark_release.DEFAULT_NODE]["gauges"]["cold"][gauge]
    warm = result["scenarios"][benchmark_release.DEFAULT_NODE]["gauges"]["warm"][gauge]
    assert cold == {"minimum": 3, "median": 4.0, "maximum": 5}
    assert warm == {"minimum": 4, "median": 5.0, "maximum": 6}


def test_isolated_fixture_observes_real_session_boundaries(tmp_path: Path) -> None:
    benchmark_release._prepare_fixture(tmp_path)

    cold = benchmark_release._run_fixture(tmp_path, node=benchmark_release.DEFAULT_NODE)
    warm = benchmark_release._run_fixture(tmp_path, node=benchmark_release.DEFAULT_NODE)

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
