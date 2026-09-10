from __future__ import annotations

import json
from pathlib import Path

import pytest

from data_sources.modules import blog_release


def _touch(path: Path, payload: str = "{}\n") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(payload, encoding="utf-8")
    return path


def _inputs(tmp_path: Path) -> dict[str, object]:
    return {
        "article": _touch(tmp_path / "rewrites" / "article.md", "---\nartifact_type: blog\n---\n# Article\n"),
        "proof_sidecar": _touch(tmp_path / "research" / "sidecar.md"),
        "editorial_plan": _touch(tmp_path / "research" / "plan.json"),
        "plan_review": _touch(tmp_path / "research" / "plan-review.json"),
        "article_review": _touch(tmp_path / "research" / "article-review.json"),
        "keyword_decision": _touch(tmp_path / "research" / "keyword.json"),
        "scrub_receipt": _touch(tmp_path / "research" / "scrub.json"),
        "serp_evidence": _touch(tmp_path / "research" / "serp.json"),
        "stage_receipts": [_touch(tmp_path / "research" / "stage.json")],
    }


def _run(tmp_path: Path, **kwargs):
    return blog_release.run_blog_release(run_id="run-1", workflow_mode="rewrite", assembly_date="2026-08-26", output_dir=tmp_path / "research" / "releases" / "run", workspace_root=tmp_path, **_inputs(tmp_path), **kwargs)


def test_blog_release_rejects_reused_output_directory(tmp_path: Path):
    (tmp_path / "research" / "releases" / "run").mkdir(parents=True)
    with pytest.raises(blog_release.ReleaseInvocationError):
        _run(tmp_path)


def test_blog_release_persists_telemetry_when_a_stage_raises(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr(
        blog_release.blog_creation_preflight,
        "build_preflight_report",
        lambda *args, **kwargs: (_ for _ in ()).throw(OSError("boundary failed")),
    )

    with pytest.raises(OSError, match="boundary failed"):
        _run(tmp_path)

    payload = json.loads(
        (tmp_path / "research" / "releases" / "run" / "release-telemetry.json").read_text(
            encoding="utf-8"
        )
    )
    assert payload["outcome"] == "operational_error"
    assert payload["stages"][0]["name"] == "pre_bom"
    assert payload["stages"][0]["outcome"] == "error"


def test_blog_release_writes_fixed_artifacts_for_blocker_and_initial_scorecard(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr(blog_release.blog_creation_preflight, "build_preflight_report", lambda *a, **k: {"schema": "simpro-blog-creation-preflight/v1", "ready_for_bom": False, "blockers": [{"rule_id": "blocked"}]})
    blocked = _run(tmp_path)
    assert blocked.exit_code == 1 and (blocked.output_dir / "pre-bom-report.json").is_file()
    blocked_telemetry = json.loads(
        (blocked.output_dir / "release-telemetry.json").read_text(encoding="utf-8")
    )
    assert blocked_telemetry["schema"] == "simpro-readiness-telemetry/v1"
    assert blocked_telemetry["outcome"] == "blocked"
    assert not (blocked.output_dir / "provisional-bom.json").exists()

    tmp2 = tmp_path / "initial_scorecard"
    monkeypatch.setattr(blog_release.blog_creation_preflight, "build_preflight_report", lambda *a, **k: {"schema": "simpro-blog-creation-preflight/v1", "ready_for_bom": True, "blockers": []})
    monkeypatch.setattr(blog_release.blog_assembly_bom, "build_blog_assembly_bom_from_files", lambda **k: {"schema": "simpro-blog-assembly-bom/v2", "lifecycle_state": "provisional", "artifacts": {}, "workflow": {"stage_receipts": []}})
    monkeypatch.setattr(blog_release.blog_assembly_bom, "finalize_blog_assembly_bom", lambda **k: pytest.fail("initial scorecard run must not finalize"))
    monkeypatch.setattr(blog_release.publish_readiness, "run_publish_readiness", lambda *a, **k: {"schema": "simpro-publish-readiness-result/v1", "passed": True, "phase": k["phase"]})
    monkeypatch.setattr(blog_release.publish_readiness, "write_readiness_result", lambda output, result, **k: (_touch(Path(output), json.dumps(result)), _touch(Path(k["receipt_path"]), '{"receipt_hash":"' + ("a" * 64) + '"}\n'))[1])
    passed = _run(tmp2)
    assert passed.exit_code == 0
    assert passed.phase == "optimization_started"
    assert passed.recovery_artifact == passed.output_dir / "optimization-recovery.json"
    assert sorted(p.name for p in passed.output_dir.iterdir()) == [
        "optimization-recovery.json",
        "optimization-state.json",
        "pre-bom-report.json",
        "preflight-readiness-stage-receipt.json",
        "preflight-readiness.json",
        "provisional-bom.json",
        "release-telemetry.json",
    ]
    recovery = json.loads((passed.output_dir / "optimization-recovery.json").read_text(encoding="utf-8"))
    assert recovery["schema"] == "simpro-blog-optimization-recovery/v1"
    assert recovery["status"] == "started"
    assert recovery["preflight_passed"] is True
    assert recovery["native_edit_status"] == "started"
    assert recovery["optimization_state"] == "research/releases/run/optimization-state.json"


def test_blog_release_starts_optimization_from_preflight_blocker(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr(blog_release.blog_creation_preflight, "build_preflight_report", lambda *a, **k: {"schema": "simpro-blog-creation-preflight/v1", "ready_for_bom": True, "blockers": []})
    monkeypatch.setattr(blog_release.blog_assembly_bom, "build_blog_assembly_bom_from_files", lambda **k: {"schema": "simpro-blog-assembly-bom/v2", "lifecycle_state": "provisional", "artifacts": {}, "workflow": {"stage_receipts": []}})
    monkeypatch.setattr(blog_release.blog_assembly_bom, "finalize_blog_assembly_bom", lambda **k: pytest.fail("blocked initial scorecard run must not finalize"))
    monkeypatch.setattr(blog_release.publish_readiness, "run_publish_readiness", lambda *a, **k: {"schema": "simpro-publish-readiness-result/v1", "passed": False, "phase": k["phase"], "gates": [{"name": "context_binding", "passed": False}]})
    monkeypatch.setattr(blog_release.publish_readiness, "write_readiness_result", lambda output, result, **k: (_touch(Path(output), json.dumps(result)), None)[1])

    result = _run(tmp_path)

    assert result.exit_code == 0
    assert result.phase == "optimization_started"
    assert result.recovery_artifact == result.output_dir / "optimization-recovery.json"
    recovery = json.loads(result.recovery_artifact.read_text(encoding="utf-8"))
    assert recovery["preflight_passed"] is False
    assert recovery["native_edit_status"] == "not_started"
    assert recovery["optimization_state"] is None
    assert not (result.output_dir / "optimization-state.json").exists()
    assert "Run /optimize" in recovery["required_next_steps"][0]


def test_blog_release_finalizes_only_with_optimizer_evidence(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    optimizer = _touch(tmp_path / "research" / "optimizer-output.json")
    prior_readiness = _touch(tmp_path / "research" / "prior-preflight-readiness.json")
    observed = {}

    monkeypatch.setattr(blog_release.blog_creation_preflight, "build_preflight_report", lambda *a, **k: {"schema": "simpro-blog-creation-preflight/v1", "ready_for_bom": True, "blockers": []})

    def provisional(**kwargs):
        observed["optimizer_output_paths"] = kwargs["optimizer_output_paths"]
        observed["prior_preflight_readiness_path"] = kwargs["prior_preflight_readiness_path"]
        return {"schema": "simpro-blog-assembly-bom/v2", "lifecycle_state": "provisional", "artifacts": {}, "workflow": {"stage_receipts": []}}

    monkeypatch.setattr(blog_release.blog_assembly_bom, "build_blog_assembly_bom_from_files", provisional)
    monkeypatch.setattr(blog_release.blog_assembly_bom, "finalize_blog_assembly_bom", lambda **k: {"schema": "simpro-blog-assembly-bom/v2", "lifecycle_state": "final", "artifacts": {}, "workflow": {"stage_receipts": []}})
    readiness_calls = []

    def readiness(*args, **kwargs):
        readiness_calls.append(kwargs["phase"])
        return {
            "schema": "simpro-publish-readiness-result/v1",
            "passed": True,
            "phase": kwargs["phase"],
        }

    monkeypatch.setattr(blog_release.publish_readiness, "run_publish_readiness", readiness)
    monkeypatch.setattr(
        blog_release.publish_readiness,
        "build_final_readiness_attestation",
        lambda preflight, **kwargs: {
            **preflight,
            "phase": "final",
            "final_bom_sha256": "a" * 64,
        },
    )
    monkeypatch.setattr(blog_release.publish_readiness, "write_readiness_result", lambda output, result, **k: (_touch(Path(output), json.dumps(result)), _touch(Path(k["receipt_path"]), '{"receipt": true}\n')))

    passed = _run(
        tmp_path,
        optimizer_outputs=[optimizer],
        prior_preflight_readiness=prior_readiness,
    )

    assert passed.exit_code == 0
    assert sorted(p.name for p in passed.output_dir.iterdir()) == ["final-bom.json", "final-readiness-stage-receipt.json", "final-readiness.json", "pre-bom-report.json", "preflight-readiness-stage-receipt.json", "preflight-readiness.json", "provisional-bom.json", "release-telemetry.json"]
    assert readiness_calls == ["preflight"]
    telemetry = json.loads(
        (passed.output_dir / "release-telemetry.json").read_text(encoding="utf-8")
    )
    assert telemetry["counters"]["full_readiness_executions"] == 1
    assert [stage["name"] for stage in telemetry["stages"]] == [
        "pre_bom",
        "provisional_bom",
        "preflight_readiness",
        "preflight_persistence",
        "bom_finalization",
        "final_attestation",
        "final_persistence",
    ]
    assert observed == {
        "optimizer_output_paths": (optimizer,),
        "prior_preflight_readiness_path": prior_readiness,
    }


def test_blog_release_rejects_partial_optimizer_evidence(tmp_path: Path):
    optimizer = _touch(tmp_path / "research" / "optimizer-output.json")
    prior_readiness = _touch(tmp_path / "research" / "prior-preflight-readiness.json")

    with pytest.raises(blog_release.ReleaseInvocationError, match="optimized release requires both"):
        _run(tmp_path, optimizer_outputs=[optimizer])

    with pytest.raises(blog_release.ReleaseInvocationError, match="optimized release requires both"):
        _run(tmp_path, prior_preflight_readiness=prior_readiness)


def test_blog_release_forwards_nonvault_customer_proof_evidence(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    evidence = _touch(
        tmp_path / "research" / "nonvault-proof.json",
        '{"schema":"simpro-nonvault-customer-proof-selector-evidence/v1"}\n',
    )
    observed = {}

    def preflight(*args, **kwargs):
        observed["preflight"] = kwargs["customer_proof_evidence"]
        return {
            "schema": "simpro-blog-creation-preflight/v1",
            "ready_for_bom": True,
            "blockers": [],
        }

    def provisional(**kwargs):
        observed["bom"] = kwargs["customer_proof_selector_evidence_path"]
        return {
            "schema": "simpro-blog-assembly-bom/v2",
            "lifecycle_state": "provisional",
            "artifacts": {},
            "workflow": {"stage_receipts": []},
        }

    monkeypatch.setattr(blog_release.blog_creation_preflight, "build_preflight_report", preflight)
    monkeypatch.setattr(blog_release.blog_assembly_bom, "build_blog_assembly_bom_from_files", provisional)
    monkeypatch.setattr(
        blog_release.blog_assembly_bom,
        "finalize_blog_assembly_bom",
        lambda **kwargs: {
            "schema": "simpro-blog-assembly-bom/v2",
            "lifecycle_state": "final",
            "artifacts": {},
            "workflow": {"stage_receipts": []},
        },
    )
    monkeypatch.setattr(
        blog_release.publish_readiness,
        "run_publish_readiness",
        lambda *args, **kwargs: {
            "schema": "simpro-publish-readiness-result/v1",
            "passed": True,
            "phase": kwargs["phase"],
        },
    )
    monkeypatch.setattr(
        blog_release.publish_readiness,
        "build_final_readiness_attestation",
        lambda preflight, **kwargs: {
            **preflight,
            "phase": "final",
            "final_bom_sha256": "a" * 64,
        },
    )
    monkeypatch.setattr(
        blog_release.publish_readiness,
        "write_readiness_result",
        lambda output, result, **kwargs: (
            _touch(Path(output), json.dumps(result)),
            _touch(Path(kwargs["receipt_path"]), '{"receipt": true}\n'),
        ),
    )

    optimizer = _touch(tmp_path / "research" / "optimizer-output.json")
    prior_readiness = _touch(tmp_path / "research" / "prior-preflight-readiness.json")

    result = _run(
        tmp_path,
        customer_proof_evidence=evidence,
        optimizer_outputs=[optimizer],
        prior_preflight_readiness=prior_readiness,
    )

    assert result.exit_code == 0
    assert observed == {"preflight": evidence, "bom": evidence}


def test_blog_release_cli_exit_codes_distinguish_policy_from_operational_failure(monkeypatch: pytest.MonkeyPatch):
    args = ["rewrites/article.md", "--run-id", "run-1", "--proof-sidecar", "research/sidecar.md", "--editorial-plan", "research/plan.json", "--plan-review", "research/plan-review.json", "--article-review", "research/article-review.json", "--keyword-decision", "research/keyword.json", "--scrub-receipt", "research/scrub.json", "--serp-evidence", "research/serp.json", "--stage-receipt", "research/stage.json", "--workflow-mode", "rewrite", "--assembly-date", "2026-08-26", "--output-dir", "research/releases/run"]
    monkeypatch.setattr(blog_release, "run_blog_release", lambda **k: (_ for _ in ()).throw(ValueError("policy blocker")))
    assert blog_release.main(args) == 1
    monkeypatch.setattr(blog_release, "run_blog_release", lambda **k: (_ for _ in ()).throw(OSError("disk write failed")))
    assert blog_release.main(args) == 2
