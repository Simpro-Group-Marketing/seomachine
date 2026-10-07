from __future__ import annotations

import json
from pathlib import Path

import pytest

from data_sources.modules.context_build.checkpoints import CheckpointStore, ContextBuildResumeError
from data_sources.modules.context_build.spec import ContextBuildSpecError, load_spec


def _spec_payload(**overrides):
    payload = {
        "schema": "simpro-context-build-spec/v1",
        "slug": "demo",
        "date": "2026-10-07",
        "request": {"schema": "simpro-context-request/v1", "task": "t", "scope": {"title": "Demo"}},
        "outputs": {"request": "research/context-request-demo.json",
                    "trace": "research/context-refresh-demo-2026-10-07.json",
                    "claim_lookup": None},
        "discovery": {"search_queries": ["q1"], "resource_purposes": {"res-a": "guidance"},
                      "expand_resource_ids": ["res-a"]},
        "constraints": ["c1"],
        "claim_lookups": [],
        "stages": [{"id": "public", "pack": "research/context-pack-demo.json",
                    "receipt": "research/context-receipt-demo.json",
                    "claim_requests": [{"claim_id": "claim-1", "query": "q", "use_mode": "exact_quote",
                                        "brand_scope": "Simpro"}]}],
    }
    payload.update(overrides)
    return payload


def _write(tmp_path: Path, payload) -> Path:
    path = tmp_path / "spec.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_valid_spec_loads(tmp_path: Path) -> None:
    spec = load_spec(_write(tmp_path, _spec_payload()))
    assert spec.slug == "demo" and spec.stages[0].stage_id == "public" and len(spec.digest) == 64


def test_example_spec_loads() -> None:
    assert load_spec(Path("config/context-build-spec.example.json")).stages


@pytest.mark.parametrize("mutate", [
    lambda p: p["discovery"].update(search_queries=[f"q{i}" for i in range(21)]),
    lambda p: p["stages"][0]["claim_requests"][0].update(extra="x"),
    lambda p: p["stages"].append(dict(p["stages"][0])),
    lambda p: p["stages"][0].update(pack="drafts/context-pack-demo.json"),
    lambda p: p["discovery"].update(expand_resource_ids=["res-missing"]),
])
def test_invalid_specs_are_rejected(tmp_path: Path, mutate) -> None:
    payload = _spec_payload()
    mutate(payload)
    with pytest.raises(ContextBuildSpecError):
        load_spec(_write(tmp_path, payload))


def test_checkpoint_round_trip_and_fresh_run_clears(tmp_path: Path) -> None:
    spec = load_spec(_write(tmp_path, _spec_payload()))
    store = CheckpointStore(tmp_path, spec, resume=False)
    store.put("search:q1", [{"resource_id": "res-a"}])
    assert CheckpointStore(tmp_path, spec, resume=True).get("search:q1") == [{"resource_id": "res-a"}]
    assert CheckpointStore(tmp_path, spec, resume=False).get("search:q1") is None


def test_resume_with_changed_spec_is_refused(tmp_path: Path) -> None:
    CheckpointStore(tmp_path, load_spec(_write(tmp_path, _spec_payload())), resume=False)
    changed = load_spec(_write(tmp_path, _spec_payload(constraints=["different"])))
    with pytest.raises(ContextBuildResumeError):
        CheckpointStore(tmp_path, changed, resume=True)
