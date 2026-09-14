from __future__ import annotations

import hashlib
from pathlib import Path
from types import SimpleNamespace

from data_sources.modules import publish_readiness
from data_sources.modules.readiness import api as readiness_api
from data_sources.modules.readiness import finalization, pipeline_tail, runtime_policy
from data_sources.modules.readiness import snapshot_gates
from data_sources.modules.readiness.inputs import ReadinessInputs
from data_sources.modules.url_validator import UrlValidationSummary


def test_runtime_policy_uses_the_captured_bom_payload(tmp_path: Path) -> None:
    bom = tmp_path / "bom.json"
    bom.write_text(
        '{"artifacts":{},"paa_policy":{},"faq_policy":{"status":"ready"},'
        '"schema_policy":{"visible_faq":true},"assembly_date":"2026-09-11",'
        '"workflow":{}}\n',
        encoding="utf-8",
    )
    inputs = ReadinessInputs.capture(
        {"assembly_bom": bom},
        workspace_root=tmp_path,
    )
    bom.write_text(
        '{"artifacts":{},"paa_policy":{},"faq_policy":{"status":"changed"},'
        '"schema_policy":{"visible_faq":false}}\n',
        encoding="utf-8",
    )

    policy = runtime_policy._bom_runtime_policy(
        str(bom),
        workspace_root=tmp_path,
        inputs=inputs,
    )

    assert policy["visible_faq"] is True
    assert policy["faq_policy_status"] == "ready"
    assert policy["assembly_date"] == "2026-09-11"


def test_pipeline_uses_content_apis_for_public_article_gates(
    tmp_path: Path,
    monkeypatch,
) -> None:
    article_path = tmp_path / "article.md"
    article_content = "---\nartifact_type: landing_page\n---\n# Captured\n"
    article_path.write_text(article_content, encoding="utf-8")
    inputs = ReadinessInputs.capture({"article": article_path}, workspace_root=tmp_path)
    captured_content = inputs.text("article")
    calls: list[tuple[str, str]] = []

    monkeypatch.setattr(pipeline_tail, "ARTICLE_GATES", ())
    monkeypatch.setattr(
        pipeline_tail.public_artifact_guard,
        "check_file",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("file API used")),
    )
    monkeypatch.setattr(
        pipeline_tail.public_artifact_guard,
        "check_content",
        lambda content, **kwargs: calls.append(("public", content)) or [],
    )
    monkeypatch.setattr(
        pipeline_tail.ai_copy_linter,
        "lint_file",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("file API used")),
    )
    monkeypatch.setattr(
        pipeline_tail.ai_copy_linter,
        "lint_content",
        lambda content, **kwargs: calls.append(("linter", content)) or [],
    )
    monkeypatch.setattr(
        pipeline_tail.public_research_link_guard,
        "check_file",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("file API used")),
    )
    monkeypatch.setattr(
        pipeline_tail.public_research_link_guard,
        "check_content",
        lambda content, **kwargs: calls.append(("research", content)) or [],
    )
    monkeypatch.setattr(
        pipeline_tail,
        "validate_content_urls",
        lambda content, **kwargs: calls.append(("urls", content))
        or UrlValidationSummary([]),
        raising=False,
    )
    monkeypatch.setattr(
        pipeline_tail.chrome_review_evidence,
        "apply_chrome_review_evidence_fallbacks",
        lambda summary, **kwargs: summary,
    )
    monkeypatch.setattr(
        pipeline_tail,
        "_score_content",
        lambda *args, **kwargs: {
            "passed": True,
            "content_quality_score": 100,
            "threshold": 75,
            "aeo_geo": {"passed": True, "not_applicable": True},
        },
    )

    result = pipeline_tail._run_remaining_gates(
        run_started_at="2026-09-11T00:00:00Z",
        article_path=article_path,
        article=SimpleNamespace(sha256=inputs.snapshot("article").sha256),
        article_content=captured_content,
        proof_sidecar_path=None,
        context_request_path=None,
        context_pack_path=None,
        context_receipt_path=None,
        assembly_bom_path=None,
        vault_root=None,
        ai_profile="simpro-web",
        phase="preflight",
        workspace_root=tmp_path,
        readiness_root=tmp_path,
        artifact_kind="landing_page",
        score_threshold=75,
        gates=[],
        runtime_policy={"visible_faq": False, "paa_kwargs": {}},
        session=None,
        sealed_inputs=inputs,
        sealed_input_hashes=inputs.hash_inventory(),
        input_capture_error=None,
        telemetry=None,
        run_id="snapshot-run",
    )

    assert result["input_seal"] == {"status": "verified"}
    assert calls == [
        ("public", captured_content),
        ("linter", captured_content),
        ("urls", captured_content),
        ("research", captured_content),
    ]


def test_early_blocked_result_is_resealed_and_hash_bound(tmp_path: Path) -> None:
    article = tmp_path / "article.md"
    article.write_text(
        "---\nartifact_type: unsupported\n---\n# Article\n",
        encoding="utf-8",
    )

    result = publish_readiness.run_publish_readiness(
        article,
        workspace_root=tmp_path,
    )

    assert result["passed"] is False
    assert result["input_seal"] == {"status": "verified"}
    assert result["input_hashes"]["article"]["path"] == "article.md"
    assert len(result["input_hashes"]["article"]["sha256"]) == 64


def test_optional_workspace_artifact_is_discovered_without_fallback(
    tmp_path: Path,
) -> None:
    expected = tmp_path / "context" / "registry.json"
    expected.parent.mkdir()
    expected.write_text("{}\n", encoding="utf-8")

    assert readiness_api._optional_workspace_artifact(
        tmp_path,
        "context/registry.json",
    ) == expected.resolve()
    assert readiness_api._optional_workspace_artifact(
        tmp_path,
        "context/missing.json",
    ) is None


def test_eeat_gate_uses_every_captured_evidence_payload(
    tmp_path: Path,
    monkeypatch,
) -> None:
    paths = {
        "article": tmp_path / "article.md",
        "validation_sidecar": tmp_path / "validation.md",
        "editorial_plan": tmp_path / "plan.json",
        "customer_proof_selector_evidence": tmp_path / "customer.json",
        "fred_authority_evidence": tmp_path / "fred.md",
    }
    paths["article"].write_text("# Captured\n", encoding="utf-8")
    paths["validation_sidecar"].write_text("proof", encoding="utf-8")
    paths["editorial_plan"].write_text('{"status":"ready"}', encoding="utf-8")
    paths["customer_proof_selector_evidence"].write_text(
        '{"status":"ready"}', encoding="utf-8"
    )
    paths["fred_authority_evidence"].write_text("fred", encoding="utf-8")
    inputs = ReadinessInputs.capture(paths, workspace_root=tmp_path)
    received: dict[str, object] = {}
    guard = SimpleNamespace(
        check_file=lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("file API used")
        ),
        check_content=lambda content, **kwargs: received.update(
            {"content": content, **kwargs}
        )
        or [],
    )
    gate_inputs = pipeline_tail.ContentGateInputs(
        article_content=inputs.text("article"),
        proof_content=inputs.text("validation_sidecar"),
        article_path=paths["article"],
        proof_sidecar_path=str(paths["validation_sidecar"]),
        context_pack_path=None,
        context_receipt_path=None,
        vault_root=None,
        runtime_policy={},
        captured=inputs,
        validated_claim_set=None,
        transport=None,
    )

    findings = pipeline_tail._execute_article_gate(
        "eeat_strength",
        guard,
        article_path=paths["article"],
        content_gate_inputs=gate_inputs,
        runtime_policy={},
        guard_kwargs={},
        telemetry=None,
    )

    assert findings == []
    assert received == {
        "content": inputs.text("article"),
        "proof_content": "proof",
        "editorial_plan": {"status": "ready"},
        "customer_proof_evidence": {"status": "ready"},
        "fred_authority_content": "fred",
    }


def test_final_attestation_owns_a_validation_session_through_reseal(
    tmp_path: Path,
    monkeypatch,
) -> None:
    article = tmp_path / "article.md"
    sidecar = tmp_path / "validation.md"
    final_bom = tmp_path / "final-bom.json"
    registry = tmp_path / "registry.json"
    article.write_text("# Article\n", encoding="utf-8")
    sidecar.write_text("proof\n", encoding="utf-8")
    final_bom.write_text(
        '{"lifecycle_state":"final","artifacts":{}}\n',
        encoding="utf-8",
    )
    registry.write_text('{"schema":"registry"}\n', encoding="utf-8")
    events: list[str] = []

    class RecordingSession:
        def __init__(self, inputs: ReadinessInputs) -> None:
            self.inputs = inputs

        @classmethod
        def capture(cls, paths, **kwargs):
            events.append("capture")
            return cls(
                ReadinessInputs.capture(
                    paths,
                    workspace_root=kwargs["workspace_root"],
                    telemetry=kwargs.get("telemetry"),
                )
            )

        def __enter__(self):
            events.append("enter")
            return self

        def __exit__(self, *args):
            events.append("exit")

    monkeypatch.setattr(finalization, "ValidationSession", RecordingSession, raising=False)
    result = finalization.build_final_attestation(
        {
            "phase": "preflight",
            "artifact_kind": "blog",
            "file": str(article),
            "proof_sidecar": str(sidecar),
            "input_hashes": {
                "source_decision_registry": {
                    "path": "registry.json",
                    "sha256": hashlib.sha256(registry.read_bytes()).hexdigest(),
                }
            },
        },
        final_bom_path=final_bom,
        workspace_root=tmp_path,
        validate_execution=lambda *args, **kwargs: None,
        validate_result=lambda *args, **kwargs: None,
        executed_result_factory=lambda value, **kwargs: value,
        readiness_run_id=lambda bom, article_hash: f"{bom}:{article_hash}",
    )

    assert result["input_seal"] == {"status": "verified"}
    assert "source_decision_registry" in result["input_hashes"]
    assert events == ["capture", "enter", "exit"]


def test_source_registry_state_is_loaded_from_captured_bytes(tmp_path: Path) -> None:
    registry = tmp_path / "registry.json"
    registry.write_text('{"schema":"registry"}\n', encoding="utf-8")
    inputs = ReadinessInputs.capture(
        {"source_decision_registry": registry},
        workspace_root=tmp_path,
    )
    received: list[object] = []

    class RecordingSession:
        def git_registry_state(self, path, loader):
            source = loader()
            received.extend([path, source])
            return "verified-state"

    state = snapshot_gates.source_registry_state(RecordingSession(), inputs)

    assert state is not None
    assert state() == "verified-state"
    assert received[0] == registry
    assert received[1].data == registry.read_bytes()
    assert received[1].payload == {"schema": "registry"}
