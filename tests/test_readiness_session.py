from __future__ import annotations

from pathlib import Path
from contextlib import contextmanager

import pytest

from data_sources.modules.readiness.inputs import ReadinessInputs
from data_sources.modules.readiness.session import ValidationSession
from data_sources.modules.readiness.telemetry import ReadinessTelemetry
from data_sources.modules import readiness_gate_context


def test_session_creates_connector_and_claim_set_once(tmp_path: Path):
    article = tmp_path / "article.md"
    article.write_text("# Article\n", encoding="utf-8")
    inputs = ReadinessInputs.capture({"article": article}, workspace_root=tmp_path)
    created: list[object] = []
    claims_loaded: list[object] = []

    class Client:
        def close(self) -> None:
            created.append("closed")

    def factory() -> Client:
        client = Client()
        created.append(client)
        return client

    def claim_loader(client: Client) -> object:
        claims_loaded.append(client)
        return {"claim-1": {"approved": True}}

    with ValidationSession(
        inputs,
        connector_factory=factory,
        claim_loader=claim_loader,
    ) as session:
        assert session.connector() is session.connector()
        assert session.validated_claim_set() is session.validated_claim_set()

    assert len([item for item in created if isinstance(item, Client)]) == 1
    assert claims_loaded == [created[0]]
    assert created[-1] == "closed"


@pytest.mark.parametrize("raises", [False, True])
def test_session_owns_one_connector_workflow_snapshot(
    tmp_path: Path,
    raises: bool,
):
    article = tmp_path / "article.md"
    article.write_text("# Article\n", encoding="utf-8")
    inputs = ReadinessInputs.capture({"article": article}, workspace_root=tmp_path)
    events: list[str] = []

    class Client:
        @contextmanager
        def workflow_snapshot(self):
            events.append("snapshot_enter")
            try:
                yield self
            finally:
                events.append("snapshot_exit")

        def close(self) -> None:
            events.append("close")

    with pytest.raises(RuntimeError) if raises else _does_not_raise():
        with ValidationSession(inputs, connector_factory=Client) as session:
            assert session.connector() is session.connector()
            if raises:
                raise RuntimeError("gate failed")

    assert events == ["snapshot_enter", "snapshot_exit", "close"]


@contextmanager
def _does_not_raise():
    yield


def test_session_findings_are_copied_and_bound_to_one_session(tmp_path: Path):
    article = tmp_path / "article.md"
    article.write_text("# Article\n", encoding="utf-8")
    inputs = ReadinessInputs.capture({"article": article}, workspace_root=tmp_path)

    with ValidationSession(inputs) as session:
        session.record_findings("gate", [{"rule_id": "warning"}])
        first = session.findings("gate")
        assert first == [{"rule_id": "warning"}]
        first[0]["rule_id"] = "changed"
        assert session.findings("gate") == [{"rule_id": "warning"}]

    other = ValidationSession(inputs)
    assert other.findings("gate") is None


def test_session_creates_and_closes_one_public_transport(tmp_path: Path):
    article = tmp_path / "article.md"
    article.write_text("# Article\n", encoding="utf-8")
    inputs = ReadinessInputs.capture({"article": article}, workspace_root=tmp_path)
    events: list[str] = []

    class Transport:
        counters = {"requests": 3, "cache_hits": 2, "cache_misses": 1}

        def close(self) -> None:
            events.append("closed")

    telemetry = ReadinessTelemetry(run_id="run-1", phase="preflight")
    with ValidationSession(
        inputs, transport_factory=Transport, telemetry=telemetry
    ) as session:
        assert session.transport() is session.transport()

    assert events == ["closed"]
    telemetry.finish("passed")
    counters = telemetry.to_dict()["counters"]
    assert counters["http_requests"] == 3
    assert counters["cache_hits"] == 2
    assert counters["cache_misses"] == 1


def test_trusted_findings_do_not_rehash_files_during_lookup(
    tmp_path: Path,
    monkeypatch,
):
    article = tmp_path / "article.md"
    article.write_text("# Article\n", encoding="utf-8")
    inputs = ReadinessInputs.capture({"article": article}, workspace_root=tmp_path)
    context = readiness_gate_context._issue_readiness_gate_context(
        {"gate": [{"rule_id": "cached"}]},
        article_content="# Article\n",
        proof_sidecar_content=None,
        input_hashes=inputs.hash_inventory(),
        workspace_root=tmp_path,
    )

    monkeypatch.setattr(
        Path,
        "open",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("lookup reopened an input")
        ),
    )
    assert readiness_gate_context.trusted_readiness_findings(
        context,
        "gate",
        article_content="# Article\n",
        proof_sidecar_content=None,
    ) == [{"rule_id": "cached"}]
    assert readiness_gate_context.trusted_readiness_findings(
        context,
        "gate",
        article_content="# Changed\n",
        proof_sidecar_content=None,
    ) is None
