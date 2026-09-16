from __future__ import annotations

import json
from pathlib import Path

import pytest

from data_sources.modules import blog_release
from data_sources.modules.artifact_runtime.release_invocation import ReleaseResult
from data_sources.modules.readiness import release_cli
from tests.test_blog_release import _inputs, _optimizer_v2, _run, _touch
from tests.release_test_support import mock_final_authorization


def _mock_passed_precheck(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        blog_release.blog_creation_preflight,
        "build_preflight_report",
        lambda *args, **kwargs: {
            "schema": "simpro-blog-creation-preflight/v1",
            "ready_for_bom": True,
            "blockers": [],
        },
    )
    monkeypatch.setattr(
        blog_release.blog_assembly_bom,
        "build_blog_assembly_bom_from_files",
        lambda **kwargs: {
            "schema": "simpro-blog-assembly-bom/v2",
            "lifecycle_state": "provisional",
            "artifacts": {},
            "workflow": {"stage_receipts": []},
        },
    )


def _mock_final_release(monkeypatch: pytest.MonkeyPatch) -> None:
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
    mock_final_authorization(monkeypatch, blog_release)


def test_precheck_only_writes_report_without_release_output_dir(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    _mock_passed_precheck(monkeypatch)
    precheck_output = tmp_path / "research" / "prechecks" / "run-1.json"

    result = _run(
        tmp_path,
        precheck_only=True,
        precheck_output=precheck_output,
    )

    assert result.exit_code == 0
    assert result.phase == "precheck"
    assert precheck_output.is_file()
    payload = json.loads(precheck_output.read_text(encoding="utf-8"))
    assert payload["schema"] == "simpro-blog-release-precheck/v1"
    assert payload["passed"] is True
    assert payload["output_dir_created"] is False
    assert not (tmp_path / "research" / "releases" / "run").exists()


def test_stale_optimizer_writes_precheck_and_error_without_output_dir(
    tmp_path: Path,
):
    inputs = _inputs(tmp_path)
    optimizer, _, prior_readiness = _optimizer_v2(tmp_path, inputs)
    article = inputs["article"]
    assert isinstance(article, Path)
    article.write_text(article.read_text(encoding="utf-8") + "Changed.\n", encoding="utf-8")
    precheck_output = tmp_path / "research" / "prechecks" / "stale.json"

    with pytest.raises(blog_release.ReleaseInvocationError, match="optimizer_output_stale"):
        _run(
            tmp_path,
            inputs=inputs,
            optimizer_outputs=[optimizer],
            prior_preflight_readiness=prior_readiness,
            precheck_output=precheck_output,
        )

    payload = json.loads(precheck_output.read_text(encoding="utf-8"))
    assert payload["passed"] is False
    assert payload["phase"] == "optimizer_evidence"
    assert "optimizer_output_stale" in payload["message"]
    assert (tmp_path / "research" / "release-errors" / "run-1.json").is_file()
    assert not (tmp_path / "research" / "releases" / "run").exists()


def test_pre_bom_failure_writes_precheck_and_error_without_output_dir(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr(
        blog_release.blog_creation_preflight,
        "build_preflight_report",
        lambda *args, **kwargs: {
            "schema": "simpro-blog-creation-preflight/v1",
            "ready_for_bom": False,
            "blockers": [{"rule_id": "blocked"}],
        },
    )
    precheck_output = tmp_path / "research" / "prechecks" / "pre-bom.json"

    result = _run(tmp_path, precheck_output=precheck_output)

    assert result.exit_code == 1
    assert result.phase == "pre_bom"
    payload = json.loads(precheck_output.read_text(encoding="utf-8"))
    assert payload["passed"] is False
    assert payload["pre_bom"]["ready_for_bom"] is False
    assert payload["blockers"] == [{"rule_id": "blocked"}]
    assert (tmp_path / "research" / "release-errors" / "run-1.json").is_file()
    assert not (tmp_path / "research" / "releases" / "run").exists()


@pytest.mark.parametrize("failure_mode", ["exception", "invalid"])
def test_provisional_bom_failure_writes_precheck_without_output_dir(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    failure_mode: str,
):
    monkeypatch.setattr(
        blog_release.blog_creation_preflight,
        "build_preflight_report",
        lambda *args, **kwargs: {
            "schema": "simpro-blog-creation-preflight/v1",
            "ready_for_bom": True,
            "blockers": [],
        },
    )
    if failure_mode == "exception":
        monkeypatch.setattr(
            blog_release.blog_assembly_bom,
            "build_blog_assembly_bom_from_files",
            lambda **kwargs: (_ for _ in ()).throw(ValueError("bom broke")),
        )
    else:
        monkeypatch.setattr(
            blog_release.blog_assembly_bom,
            "build_blog_assembly_bom_from_files",
            lambda **kwargs: {"schema": "wrong", "lifecycle_state": "draft"},
        )
    precheck_output = tmp_path / "research" / "prechecks" / f"{failure_mode}.json"

    if failure_mode == "exception":
        with pytest.raises(ValueError, match="bom broke"):
            _run(tmp_path, precheck_output=precheck_output)
    else:
        result = _run(tmp_path, precheck_output=precheck_output)
        assert result.exit_code == 1
        assert result.phase == "provisional_bom"

    payload = json.loads(precheck_output.read_text(encoding="utf-8"))
    assert payload["passed"] is False
    assert payload["phase"] == "provisional_bom"
    assert (tmp_path / "research" / "release-errors" / "run-1.json").is_file()
    assert not (tmp_path / "research" / "releases" / "run").exists()


def test_normal_release_creates_output_dir_after_prechecks_pass(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    output_dir = tmp_path / "research" / "releases" / "run"
    monkeypatch.setattr(
        blog_release.blog_creation_preflight,
        "build_preflight_report",
        lambda *args, **kwargs: {
            "schema": "simpro-blog-creation-preflight/v1",
            "ready_for_bom": True,
            "blockers": [],
        },
    )

    def provisional(**kwargs):
        assert not output_dir.exists()
        return {
            "schema": "simpro-blog-assembly-bom/v2",
            "lifecycle_state": "provisional",
            "artifacts": {},
            "workflow": {"stage_receipts": []},
        }

    monkeypatch.setattr(
        blog_release.blog_assembly_bom,
        "build_blog_assembly_bom_from_files",
        provisional,
    )
    _mock_final_release(monkeypatch)
    inputs = _inputs(tmp_path)
    optimizer, _, prior_readiness = _optimizer_v2(tmp_path, inputs)

    result = _run(
        tmp_path,
        inputs=inputs,
        optimizer_outputs=[optimizer],
        prior_preflight_readiness=prior_readiness,
        precheck_output=tmp_path / "research" / "prechecks" / "passed.json",
    )

    assert result.exit_code == 0
    assert output_dir.is_dir()
    assert (output_dir / "pre-bom-report.json").is_file()
    assert (output_dir / "provisional-bom.json").is_file()


def test_release_cli_forwards_precheck_flags(tmp_path: Path):
    observed = {}
    args = [
        "rewrites/article.md",
        "--run-id",
        "run-1",
        "--proof-sidecar",
        "research/sidecar.md",
        "--editorial-plan",
        "research/plan.json",
        "--plan-fulfillment",
        "research/fulfillment.json",
        "--commercial-pillar-index",
        "context/commercial-pillar-index.json",
        "--plan-review",
        "research/plan-review.json",
        "--article-review",
        "research/article-review.json",
        "--keyword-decision",
        "research/keyword.json",
        "--scrub-receipt",
        "research/scrub.json",
        "--serp-evidence",
        "research/serp.json",
        "--stage-receipt",
        "research/stage.json",
        "--workflow-mode",
        "rewrite",
        "--assembly-date",
        "2026-08-26",
        "--output-dir",
        "research/releases/run",
        "--precheck-only",
        "--precheck-output",
        "research/prechecks/run-1.json",
        "--workspace-root",
        str(tmp_path),
    ]

    def runner(**kwargs):
        observed.update(kwargs)
        return ReleaseResult(0, tmp_path / "research" / "releases" / "run", "precheck", "ok")

    assert release_cli.run_release_cli(
        args,
        runner=runner,
        invocation_error=blog_release.ReleaseInvocationError,
    ) == 0
    assert observed["precheck_only"] is True
    assert observed["precheck_output"] == "research/prechecks/run-1.json"


def test_precheck_output_inside_output_dir_is_rejected_without_writes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    _mock_passed_precheck(monkeypatch)
    precheck_output = tmp_path / "research" / "releases" / "run" / "precheck.json"

    with pytest.raises(blog_release.ReleaseInvocationError, match="precheck_output"):
        _run(
            tmp_path,
            precheck_only=True,
            precheck_output=precheck_output,
        )

    assert not precheck_output.exists()
    assert not (tmp_path / "research" / "releases" / "run").exists()


def test_precheck_output_cannot_overwrite_release_input(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    _mock_passed_precheck(monkeypatch)
    inputs = _inputs(tmp_path)
    proof_sidecar = inputs["proof_sidecar"]
    assert isinstance(proof_sidecar, Path)
    original = proof_sidecar.read_bytes()

    with pytest.raises(blog_release.ReleaseInvocationError, match="precheck_output"):
        _run(
            tmp_path,
            inputs=inputs,
            precheck_only=True,
            precheck_output=proof_sidecar,
        )

    assert proof_sidecar.read_bytes() == original
    assert not (tmp_path / "research" / "releases" / "run").exists()


def test_existing_passed_precheck_is_overwritten_by_exception_report(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    precheck_output = tmp_path / "research" / "prechecks" / "run-1.json"
    _mock_passed_precheck(monkeypatch)
    assert _run(
        tmp_path,
        precheck_only=True,
        precheck_output=precheck_output,
    ).exit_code == 0
    assert json.loads(precheck_output.read_text(encoding="utf-8"))["passed"] is True
    monkeypatch.setattr(
        blog_release.blog_assembly_bom,
        "build_blog_assembly_bom_from_files",
        lambda **kwargs: (_ for _ in ()).throw(ValueError("current failure")),
    )

    with pytest.raises(ValueError, match="current failure"):
        _run(
            tmp_path,
            precheck_output=precheck_output,
        )

    payload = json.loads(precheck_output.read_text(encoding="utf-8"))
    assert payload["passed"] is False
    assert payload["phase"] == "provisional_bom"
    assert payload["exception_type"] == "ValueError"
    assert payload["message"] == "current failure"


def test_release_pre_bom_output_path_is_repaired_after_precheck(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    def preflight(*args, **kwargs):
        return {
            "schema": "simpro-blog-creation-preflight/v1",
            "ready_for_bom": True,
            "blockers": [],
            "artifact_paths": {"output": str(Path(kwargs["output"]).resolve())},
        }

    monkeypatch.setattr(
        blog_release.blog_creation_preflight,
        "build_preflight_report",
        preflight,
    )
    monkeypatch.setattr(
        blog_release.blog_assembly_bom,
        "build_blog_assembly_bom_from_files",
        lambda **kwargs: {
            "schema": "simpro-blog-assembly-bom/v2",
            "lifecycle_state": "provisional",
            "artifacts": {},
            "workflow": {"stage_receipts": []},
        },
    )
    _mock_final_release(monkeypatch)
    inputs = _inputs(tmp_path)
    optimizer, _, prior_readiness = _optimizer_v2(tmp_path, inputs)

    result = _run(
        tmp_path,
        inputs=inputs,
        optimizer_outputs=[optimizer],
        prior_preflight_readiness=prior_readiness,
        precheck_output=tmp_path / "research" / "prechecks" / "run-1.json",
    )

    release_pre_bom = json.loads(
        (result.output_dir / "pre-bom-report.json").read_text(encoding="utf-8")
    )
    assert Path(release_pre_bom["artifact_paths"]["output"]) == (
        result.output_dir / "pre-bom-report.json"
    )
