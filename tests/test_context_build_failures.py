"""Context build failure reporting: stages not rebuilt, malformed results, and write errors."""
from __future__ import annotations

import json

import pytest

from data_sources.modules.context_build.checkpoints import CheckpointStore, ContextBuildResumeError
from data_sources.modules.context_build.runner import ContextBuildError, run_context_build
from data_sources.modules.simpro_vault_client import VaultClientError
from tests.test_context_build_runner import (
    NOW,
    FakeVaultClient,
    FreshOnlyClient,
    _payload,
    _spec,
    _stage_files,
)


def _stage_ids_not_rebuilt(error: BaseException) -> list[str]:
    return list(error.stages_not_rebuilt)


def test_failure_names_stages_not_built_and_keeps_files(tmp_path):
    spec = _spec(tmp_path)
    run_context_build(spec, client=FakeVaultClient(), workspace_root=tmp_path, resume=False, now=NOW)
    before = {path: path.read_bytes() for path in _stage_files(tmp_path)}

    class RejectsSecondStage(FakeVaultClient):
        def validate_context(self, request, pack, receipt):
            return {"valid": self.build_count != 2, "errors": []}

    with pytest.raises(ContextBuildError, match="stage2") as caught:
        run_context_build(spec, client=RejectsSecondStage(), workspace_root=tmp_path, resume=False, now=NOW)
    assert _stage_ids_not_rebuilt(caught.value) == ["stage2", "stage3"]
    assert {path: path.read_bytes() for path in _stage_files(tmp_path)} == before


def test_early_failure_names_every_stage_not_rebuilt(tmp_path):
    class NotReady(FakeVaultClient):
        def status(self):
            return {"status": "degraded"}

    with pytest.raises(ContextBuildError) as caught:
        run_context_build(_spec(tmp_path), client=NotReady(), workspace_root=tmp_path, resume=False, now=NOW)
    assert _stage_ids_not_rebuilt(caught.value) == ["stage1", "stage2", "stage3"]


def test_reused_stages_are_not_listed_as_not_rebuilt(tmp_path):
    spec = _spec(tmp_path)
    with pytest.raises(RuntimeError, match="killed"):
        run_context_build(spec, client=FakeVaultClient(fail_on_build=3), workspace_root=tmp_path,
                          resume=False, now=NOW)

    class VaultDown(FreshOnlyClient):
        def validate_context(self, request, pack, receipt):
            return {"valid": True, "errors": []}

        def build_context(self, build_input):
            raise VaultClientError("vault_down", "vault went away", "retry")

    with pytest.raises(VaultClientError) as caught:
        run_context_build(spec, client=VaultDown(), workspace_root=tmp_path, resume=True, now=NOW)
    assert _stage_ids_not_rebuilt(caught.value) == ["stage3"]


def test_cli_error_json_lists_stages_not_rebuilt(tmp_path, capsys, monkeypatch):
    from data_sources.modules.context_build import cli

    spec_path = tmp_path / "spec.json"
    spec_path.write_text(json.dumps(_payload()), encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(cli, "SimproVaultClient", lambda: FakeVaultClient(valid=False))

    assert cli.main([str(spec_path)]) == 1
    output = json.loads(capsys.readouterr().out)
    assert output["ok"] is False
    assert output["stages_not_rebuilt"] == ["stage1", "stage2", "stage3"]
    assert "stale" in output["recovery_hint"]


def test_cli_spec_error_has_no_stage_list(tmp_path, capsys):
    from data_sources.modules.context_build.cli import main

    bad = tmp_path / "bad.json"
    bad.write_text("{}", encoding="utf-8")
    assert main([str(bad)]) == 1
    assert "stages_not_rebuilt" not in json.loads(capsys.readouterr().out)


@pytest.mark.parametrize("result", [{}, {"pack": {}}, {"receipt": {}}, None])
def test_malformed_build_result_raises_context_build_error(tmp_path, result):
    class Malformed(FakeVaultClient):
        def build_context(self, build_input):
            return result

    with pytest.raises(ContextBuildError, match="stage1 build_context result"):
        run_context_build(_spec(tmp_path), client=Malformed(), workspace_root=tmp_path, resume=False, now=NOW)


def test_write_failure_raises_context_build_error(tmp_path, monkeypatch):
    from data_sources.modules.context_build import runner

    def fail(path, chunks, **kwargs):
        raise OSError("disk full")

    monkeypatch.setattr(runner, "atomic_write_bytes", fail)
    with pytest.raises(ContextBuildError, match="disk full") as caught:
        run_context_build(_spec(tmp_path), client=FakeVaultClient(), workspace_root=tmp_path,
                          resume=False, now=NOW)
    assert _stage_ids_not_rebuilt(caught.value) == ["stage1", "stage2", "stage3"]


def test_trace_write_failure_raises_context_build_error(tmp_path, monkeypatch):
    from data_sources.modules.context_build import runner

    def fail(*args, **kwargs):
        raise OSError("read-only filesystem")

    monkeypatch.setattr(runner, "write_context_trace", fail)
    with pytest.raises(ContextBuildError, match="read-only filesystem"):
        run_context_build(_spec(tmp_path), client=FakeVaultClient(), workspace_root=tmp_path,
                          resume=False, now=NOW)


def test_checkpoint_write_failure_raises_resume_error(tmp_path, monkeypatch):
    from data_sources.modules.context_build import checkpoints

    def fail(*args, **kwargs):
        raise OSError("no space left")

    monkeypatch.setattr(checkpoints, "atomic_write_canonical_json", fail)
    with pytest.raises(ContextBuildResumeError, match="no space left"):
        CheckpointStore(tmp_path, _spec(tmp_path), resume=False)


def test_cli_reports_malformed_build_result_as_json(tmp_path, capsys, monkeypatch):
    from data_sources.modules.context_build import cli

    class Malformed(FakeVaultClient):
        def build_context(self, build_input):
            return {}

    spec_path = tmp_path / "spec.json"
    spec_path.write_text(json.dumps(_payload()), encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(cli, "SimproVaultClient", Malformed)

    assert cli.main([str(spec_path)]) == 1
    output = json.loads(capsys.readouterr().out)
    assert output["error"]["code"] == "ContextBuildError"
    assert "build_context result" in output["error"]["message"]


class StaleSavedClient(FreshOnlyClient):
    """Raises like the real connector (code pack_stale) for saved packs it did not build itself."""

    def __init__(self, *, stale_claims=None, code="pack_stale", **kwargs) -> None:
        super().__init__(**kwargs)
        self.stale_claims = stale_claims
        self.code = code

    def validate_context(self, request, pack, receipt):
        self.calls.append("validate")
        if any(pack is built for built in self._built):
            return {"valid": True, "errors": []}
        if self.stale_claims is None or pack.get("claims") in self.stale_claims:
            raise VaultClientError(self.code, "Receipt validation time is stale", "Rebuild and revalidate.")
        return {"valid": True, "errors": []}


def test_resume_rebuilds_every_stage_whose_receipt_is_stale(tmp_path):
    spec = _spec(tmp_path)
    run_context_build(spec, client=FakeVaultClient(), workspace_root=tmp_path, resume=False, now=NOW)

    client = StaleSavedClient()
    result = run_context_build(spec, client=client, workspace_root=tmp_path, resume=True, now=NOW)

    assert [stage.action for stage in result.stages] == ["built", "built", "built"]
    assert client.build_count == 3


def test_resume_rebuilds_only_the_stale_stage(tmp_path):
    spec = _spec(tmp_path)
    run_context_build(spec, client=FakeVaultClient(), workspace_root=tmp_path, resume=False, now=NOW)

    client = StaleSavedClient(stale_claims=[["claim-1"]])
    result = run_context_build(spec, client=client, workspace_root=tmp_path, resume=True, now=NOW)

    assert [stage.action for stage in result.stages] == ["built", "reused", "reused"]
    assert client.build_count == 1


def test_resume_still_fails_closed_on_other_vault_errors(tmp_path):
    spec = _spec(tmp_path)
    run_context_build(spec, client=FakeVaultClient(), workspace_root=tmp_path, resume=False, now=NOW)

    with pytest.raises(VaultClientError) as caught:
        run_context_build(spec, client=StaleSavedClient(code="pack_tampered"), workspace_root=tmp_path,
                          resume=True, now=NOW)
    assert caught.value.code == "pack_tampered"
    assert _stage_ids_not_rebuilt(caught.value) == ["stage1", "stage2", "stage3"]
