from __future__ import annotations

from pathlib import Path

from data_sources.modules.readiness.inputs import ReadinessInputs
from data_sources.modules.readiness.session import ValidationSession
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
