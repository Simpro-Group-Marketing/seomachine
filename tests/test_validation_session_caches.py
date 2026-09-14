from __future__ import annotations

from pathlib import Path

import pytest

from data_sources.modules.readiness.session import ValidationSession
from data_sources.modules.readiness.telemetry import ReadinessTelemetry
from data_sources.modules.vault_claim_receipts import ValidatedClaimSet


def test_session_capture_owns_artifacts_and_compatibility_inputs(tmp_path: Path):
    article = tmp_path / "article.md"
    article.write_text("# Article\n", encoding="utf-8")

    with ValidationSession.capture(
        {"article": article},
        workspace_root=tmp_path,
    ) as session:
        assert session.artifacts is session.inputs.artifacts
        assert session.artifacts.text("article") == session.inputs.text("article")
        assert session.artifacts.markdown_view("article").h1 == "Article"


def test_session_caches_connector_results_by_canonical_request(tmp_path: Path):
    article = tmp_path / "article.md"
    article.write_text("# Article\n", encoding="utf-8")
    calls: list[str] = []
    telemetry = ReadinessTelemetry(run_id="run-cache", phase="preflight")

    with ValidationSession.capture(
        {"article": article},
        workspace_root=tmp_path,
        telemetry=telemetry,
    ) as session:
        first = session.connector_result(
            "search",
            {"query": "topic", "roles": ["voice", "product"]},
            lambda: calls.append("connector") or {"resource_id": "one"},
        )
        second = session.connector_result(
            "search",
            {"roles": ["voice", "product"], "query": "topic"},
            lambda: calls.append("duplicate") or {},
        )
        source_first = session.normalized_source(
            "https://example.com/source",
            lambda: calls.append("source") or {"title": "Evidence"},
        )
        source_second = session.normalized_source(
            " https://example.com/source ",
            lambda: calls.append("source duplicate") or {},
        )

        assert first is second
        assert source_first is source_second
        with pytest.raises(TypeError):
            first["resource_id"] = "changed"

    assert calls == ["connector", "source"]
    telemetry.finish("passed")
    counters = telemetry.to_dict()["counters"]
    assert counters["connector_result_cache_misses"] == 1
    assert counters["connector_result_cache_hits"] == 1
    assert counters["connector_operations"] == 1
    assert counters["normalized_source_parses"] == 1
    assert counters["normalized_source_cache_hits"] == 1




def test_normalized_source_cache_enforces_session_memory_budget(tmp_path: Path):
    article = tmp_path / "article.md"
    article.write_text("# Article\n", encoding="utf-8")
    telemetry = ReadinessTelemetry(run_id="run-budget", phase="preflight")

    with ValidationSession.capture(
        {"article": article},
        workspace_root=tmp_path,
        telemetry=telemetry,
        network_material_budget_bytes=4,
    ) as session:
        session.normalized_source("one", lambda: "four")
        with pytest.raises(ValueError, match="network material budget"):
            session.normalized_source("two", lambda: "x")

    telemetry.finish("blocked")
    assert telemetry.to_dict()["gauges"]["normalized_source_bytes"] == 0


def test_git_registry_state_rejects_paths_outside_workspace(tmp_path: Path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    article = workspace / "article.md"
    article.write_text("# Article\n", encoding="utf-8")
    outside = tmp_path / "outside.json"
    outside.write_text("{}\n", encoding="utf-8")

    with ValidationSession.capture(
        {"article": article},
        workspace_root=workspace,
    ) as session:
        with pytest.raises(ValueError, match="outside workspace"):
            session.git_registry_state(outside, lambda: {})


def test_session_never_memoizes_connector_or_source_exceptions(tmp_path: Path):
    article = tmp_path / "article.md"
    article.write_text("# Article\n", encoding="utf-8")
    connector_calls = 0
    source_calls = 0

    def connector_failure() -> object:
        nonlocal connector_calls
        connector_calls += 1
        raise RuntimeError("connector failed")

    def source_failure() -> str:
        nonlocal source_calls
        source_calls += 1
        raise RuntimeError("source failed")

    with ValidationSession.capture(
        {"article": article},
        workspace_root=tmp_path,
    ) as session:
        for _ in range(2):
            with pytest.raises(RuntimeError, match="connector failed"):
                session.connector_result("search", {"query": "same"}, connector_failure)
            with pytest.raises(RuntimeError, match="source failed"):
                session.normalized_source("same-source", source_failure)

    assert connector_calls == 2
    assert source_calls == 2


def test_validated_claim_set_exposes_immutable_state_and_defensive_ids() -> None:
    claims = ValidatedClaimSet(blocker="blocked", receipt_revision="revision-1")

    with pytest.raises(AttributeError):
        claims.blocker = "changed"
    with pytest.raises(AttributeError):
        claims.receipt_revision = "changed"
    detached = claims.claim_ids()
    detached.append("invented")
    assert claims.claim_ids() == []
