from __future__ import annotations

import copy
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from data_sources.modules.context_build.checkpoints import ContextBuildResumeError
from data_sources.modules.context_build.runner import (
    ContextBuildError,
    run_context_build,
)
from data_sources.modules.context_build.spec import load_spec

NOW = datetime(2026, 10, 7, 12, 0, tzinfo=timezone.utc)


class FakeVaultClient:
    def __init__(self, *, fail_on_build: int | None = None, valid: bool = True) -> None:
        self.calls: list[str] = []
        self.build_count = 0
        self.fail_on_build = fail_on_build
        self.valid = valid
        self.build_inputs: list[dict] = []

    def status(self):
        self.calls.append("status")
        return {"status": "ready", "revisions": {"manifest_revision": "m1"}}

    def describe(self):
        self.calls.append("describe")
        return {"schema": "fake"}

    def search(self, query, *, limit=20):
        self.calls.append(f"search:{query}")
        return [{"resource_id": "res-a"}, {"resource_id": "res-b"}]

    def expand(self, resource_id, *, relation_types=None, purpose="guidance"):
        self.calls.append(f"expand:{resource_id}")
        return []

    def read(self, resource_id, *, purpose="guidance", heading=None, max_chars=None):
        self.calls.append(f"read:{resource_id}")
        return {"resource_id": resource_id, "content": "text"}

    def claims(self, query, *, use_mode, brand_scope, limit=20):
        self.calls.append(f"claims:{query}")
        return [{"claim_id": "claim-1", "public_url": "https://example.com/1"}]

    def build_context(self, build_input):
        self.build_count += 1
        self.build_inputs.append(build_input)
        if self.fail_on_build == self.build_count:
            raise RuntimeError("killed mid-build")
        ids = [row["claim_id"] for row in build_input["claim_requests"]]
        return {
            "pack": {"claims": ids, "build": self.build_count},
            "receipt": {"pack_sha256": f"p{self.build_count}", "receipt_sha256": f"r{self.build_count}"},
        }

    def validate_context(self, request, pack, receipt):
        self.calls.append("validate")
        return {"valid": self.valid, "errors": []}


class FreshOnlyClient(FakeVaultClient):
    """Accepts only packs it built itself, like a connector rejecting stale saved packs."""

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._built: list[dict] = []

    def build_context(self, build_input):
        output = super().build_context(build_input)
        self._built.append(output["pack"])
        return output

    def validate_context(self, request, pack, receipt):
        self.calls.append("validate")
        return {"valid": any(pack is built for built in self._built), "errors": []}


def _payload():
    stages = [
        {
            "id": f"stage{n}",
            "pack": f"research/context-pack-demo-{n}.json",
            "receipt": f"research/context-receipt-demo-{n}.json",
            "claim_requests": [
                {"claim_id": f"claim-{n}", "query": "q", "use_mode": "exact_quote", "brand_scope": "Simpro"}
            ],
        }
        for n in (1, 2, 3)
    ]
    return {
        "schema": "simpro-context-build-spec/v1",
        "slug": "demo",
        "date": "2026-10-07",
        "request": {"schema": "simpro-context-request/v1", "task": "t", "scope": {"title": "Demo"}},
        "outputs": {
            "request": "research/context-request-demo.json",
            "trace": "research/context-refresh-demo-2026-10-07.json",
            "claim_lookup": "research/claim-lookup-demo-2026-10-07.json",
        },
        "discovery": {
            "search_queries": ["q1", "q2"],
            "resource_purposes": {"res-a": "guidance", "res-b": "context"},
            "expand_resource_ids": ["res-a"],
        },
        "constraints": ["c1"],
        "claim_lookups": [
            {"brand_scope": "Simpro", "query": "lookup", "use_mode": "exact_quote", "limit": 50},
        ],
        "stages": stages,
    }


def _spec(tmp_path: Path, payload=None):
    path = tmp_path / "spec.json"
    path.write_text(json.dumps(payload or _payload()), encoding="utf-8")
    return load_spec(path)


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _stage_files(root: Path):
    return [
        root / f"research/context-{kind}-demo-{n}.json"
        for n in (1, 2, 3)
        for kind in ("pack", "receipt")
    ]


def test_fresh_build_writes_every_stage_and_trace(tmp_path):
    spec = _spec(tmp_path)
    client = FakeVaultClient()

    result = run_context_build(spec, client=client, workspace_root=tmp_path, resume=False, now=NOW)

    assert client.build_count == 3
    assert [stage.action for stage in result.stages] == ["built", "built", "built"]
    assert [stage.stage_id for stage in result.stages] == ["stage1", "stage2", "stage3"]
    for path in _stage_files(tmp_path):
        assert path.is_file()
    assert (tmp_path / "research/context-request-demo.json").is_file()
    assert (tmp_path / "research/claim-lookup-demo-2026-10-07.json").is_file()
    assert (tmp_path / spec.trace_path).is_file()
    assert result.trace_path == tmp_path / spec.trace_path
    first = result.stages[0]
    assert first.pack_sha256 == _sha(tmp_path / "research/context-pack-demo-1.json")
    assert first.receipt_sha256 == _sha(tmp_path / "research/context-receipt-demo-1.json")


def test_outputs_use_reference_serialization(tmp_path):
    spec = _spec(tmp_path)
    run_context_build(spec, client=FakeVaultClient(), workspace_root=tmp_path, resume=False, now=NOW)

    pack_bytes = (tmp_path / "research/context-pack-demo-1.json").read_bytes()
    assert pack_bytes == (json.dumps({"claims": ["claim-1"], "build": 1}, indent=2, ensure_ascii=False) + "\n").encode()
    assert b"\r\n" not in pack_bytes
    request_bytes = (tmp_path / "research/context-request-demo.json").read_bytes()
    assert request_bytes == (json.dumps(spec.request, indent=2, ensure_ascii=False) + "\n").encode()


def test_build_input_carries_spec_values(tmp_path):
    spec = _spec(tmp_path)
    client = FakeVaultClient()
    run_context_build(spec, client=client, workspace_root=tmp_path, resume=False, now=NOW)

    first = client.build_inputs[0]
    assert set(first) == {
        "request", "search_queries", "resource_ids", "resource_purposes",
        "constraints", "task_satisfaction", "unresolved_gaps", "claim_requests",
    }
    assert first["task_satisfaction"] == "satisfied"
    assert first["unresolved_gaps"] == []
    assert first["resource_ids"] == ["res-a", "res-b"]
    assert first["claim_requests"][0]["claim_id"] == "claim-1"


def test_claim_lookup_artifact_shape(tmp_path):
    spec = _spec(tmp_path)
    run_context_build(spec, client=FakeVaultClient(), workspace_root=tmp_path, resume=False, now=NOW)

    artifact = json.loads((tmp_path / spec.claim_lookup_path).read_text(encoding="utf-8"))
    assert artifact["schema"] == "simpro-customer-proof-claim-lookup/v1"
    assert artifact["source"] == "SimproVaultClient.claims"
    assert artifact["article_slug"] == "demo"
    assert artifact["generated_at"] == NOW.isoformat()
    [lookup] = artifact["lookups"]
    assert lookup["source"] == "SimproVaultClient.claims"
    assert lookup["status"] == "complete"
    assert lookup["truncated"] is False
    assert lookup["result_count"] == 1
    assert lookup["claim_ids"] == ["claim-1"]
    assert lookup["query"] == "lookup"
    assert lookup["limit"] == 50


def test_resume_after_crash_reuses_finished_stages(tmp_path):
    spec = _spec(tmp_path)
    with pytest.raises(RuntimeError, match="killed mid-build"):
        run_context_build(spec, client=FakeVaultClient(fail_on_build=3), workspace_root=tmp_path,
                          resume=False, now=NOW)
    files = _stage_files(tmp_path)
    assert all(path.is_file() for path in files[:4])
    assert not files[4].exists() and not files[5].exists()
    before = [_sha(path) for path in files[:4]]

    client = FakeVaultClient()
    result = run_context_build(spec, client=client, workspace_root=tmp_path, resume=True, now=NOW)

    assert [stage.action for stage in result.stages] == ["reused", "reused", "built"]
    assert client.build_count == 1
    assert [_sha(path) for path in files[:4]] == before


def test_resume_skips_completed_discovery_calls(tmp_path):
    spec = _spec(tmp_path)
    run_context_build(spec, client=FakeVaultClient(), workspace_root=tmp_path, resume=False, now=NOW)

    client = FakeVaultClient()
    run_context_build(spec, client=client, workspace_root=tmp_path, resume=True, now=NOW)

    assert not [call for call in client.calls if call.startswith(("search:", "read:", "expand:", "claims:"))]
    assert "status" not in client.calls and "describe" not in client.calls


def test_resume_rebuilds_when_saved_pack_no_longer_validates(tmp_path):
    spec = _spec(tmp_path)
    run_context_build(spec, client=FakeVaultClient(), workspace_root=tmp_path, resume=False, now=NOW)

    client = FreshOnlyClient()
    result = run_context_build(spec, client=client, workspace_root=tmp_path, resume=True, now=NOW)

    assert client.build_count == 3
    assert [stage.action for stage in result.stages] == ["built", "built", "built"]


def test_resume_refuses_changed_request(tmp_path):
    spec = _spec(tmp_path)
    run_context_build(spec, client=FakeVaultClient(), workspace_root=tmp_path, resume=False, now=NOW)

    changed = copy.deepcopy(_payload())
    changed["request"]["scope"]["title"] = "Changed"
    with pytest.raises(ContextBuildResumeError):
        run_context_build(_spec(tmp_path, changed), client=FakeVaultClient(), workspace_root=tmp_path,
                          resume=True, now=NOW)


def test_resume_refuses_request_file_edited_on_disk(tmp_path):
    spec = _spec(tmp_path)
    run_context_build(spec, client=FakeVaultClient(), workspace_root=tmp_path, resume=False, now=NOW)
    request_file = tmp_path / spec.request_path
    request_file.write_text('{"edited": true}\n', encoding="utf-8")

    with pytest.raises(ContextBuildResumeError, match="request changed"):
        run_context_build(spec, client=FakeVaultClient(), workspace_root=tmp_path, resume=True, now=NOW)
    assert request_file.read_text(encoding="utf-8") == '{"edited": true}\n'


def test_rediscovery_failure_raises(tmp_path):
    payload = _payload()
    payload["discovery"]["resource_purposes"]["res-missing"] = "guidance"
    with pytest.raises(ContextBuildError, match="res-missing"):
        run_context_build(_spec(tmp_path, payload), client=FakeVaultClient(), workspace_root=tmp_path,
                          resume=False, now=NOW)


def test_status_not_ready_raises(tmp_path):
    class NotReady(FakeVaultClient):
        def status(self):
            return {"status": "degraded"}

    with pytest.raises(ContextBuildError, match="degraded"):
        run_context_build(_spec(tmp_path), client=NotReady(), workspace_root=tmp_path, resume=False, now=NOW)


def test_fresh_build_with_invalid_validation_writes_nothing(tmp_path):
    spec = _spec(tmp_path)
    with pytest.raises(ContextBuildError, match="stage1"):
        run_context_build(spec, client=FakeVaultClient(valid=False), workspace_root=tmp_path,
                          resume=False, now=NOW)
    assert not any(path.exists() for path in _stage_files(tmp_path))
    assert not (tmp_path / spec.trace_path).exists()


def test_claim_lookup_missing_brand_scope_raises(tmp_path):
    payload = _payload()
    del payload["claim_lookups"][0]["brand_scope"]
    with pytest.raises(ContextBuildError, match="brand_scope"):
        run_context_build(_spec(tmp_path, payload), client=FakeVaultClient(), workspace_root=tmp_path,
                          resume=False, now=NOW)


def test_cli_reports_spec_error_as_json(tmp_path, capsys):
    from data_sources.modules.context_build.cli import main

    bad = tmp_path / "bad.json"
    bad.write_text("{}", encoding="utf-8")

    assert main([str(bad)]) == 1
    output = json.loads(capsys.readouterr().out)
    assert output["ok"] is False
    assert output["error"]["code"] == "ContextBuildSpecError"
    assert "recovery_hint" in output


def test_cli_success_prints_stage_outcomes(tmp_path, capsys, monkeypatch):
    from data_sources.modules.context_build import cli

    spec_path = tmp_path / "spec.json"
    spec_path.write_text(json.dumps(_payload()), encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(cli, "SimproVaultClient", FakeVaultClient)

    assert cli.main([str(spec_path)]) == 0
    output = json.loads(capsys.readouterr().out)
    assert output["ok"] is True
    assert [row["action"] for row in output["result"]["stages"]] == ["built", "built", "built"]
    assert output["result"]["trace"].endswith("research/context-refresh-demo-2026-10-07.json")
