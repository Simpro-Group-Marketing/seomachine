from __future__ import annotations

import dataclasses
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


def _second_stage(**overrides):
    stage = {"id": "second", "pack": "research/context-pack-demo-2.json",
             "receipt": "research/context-receipt-demo-2.json", "claim_requests": []}
    stage.update(overrides)
    return stage


@pytest.mark.parametrize("mutate", [
    lambda p: p["outputs"].update(trace=p["outputs"]["request"]),
    lambda p: p["outputs"].update(claim_lookup=p["outputs"]["trace"]),
    lambda p: p["stages"][0].update(pack=p["outputs"]["request"]),
    lambda p: p["stages"][0].update(receipt=p["stages"][0]["pack"]),
    lambda p: p["stages"].append(_second_stage(pack=p["stages"][0]["pack"])),
    lambda p: p["stages"].append(_second_stage(receipt=p["stages"][0]["receipt"])),
    lambda p: p["stages"].append(_second_stage(pack=p["stages"][0]["pack"].upper().replace("RESEARCH", "research"))),
])
def test_duplicate_output_paths_are_rejected(tmp_path: Path, mutate) -> None:
    payload = _spec_payload()
    payload["outputs"]["claim_lookup"] = "research/claim-lookup-demo.json"
    mutate(payload)
    with pytest.raises(ContextBuildSpecError, match="duplicates the output path"):
        load_spec(_write(tmp_path, payload))


@pytest.mark.parametrize("slug", ["..", "a/../b", "/abs", "ok\n", "Upper"])
def test_bad_slugs_are_rejected(tmp_path: Path, slug: str) -> None:
    with pytest.raises(ContextBuildSpecError, match="slug"):
        load_spec(_write(tmp_path, _spec_payload(slug=slug)))


@pytest.mark.parametrize("date", ["../x", "2026-13-01", "2026-10-05\n"])
def test_bad_dates_are_rejected(tmp_path: Path, date: str) -> None:
    with pytest.raises(ContextBuildSpecError, match="date"):
        load_spec(_write(tmp_path, _spec_payload(date=date)))


@pytest.mark.parametrize("path", [
    "research/../drafts/x.json",
    "research\\context-request-demo.json",
    "research/sub\\x.json",
    "research//x.json",
])
def test_bad_output_paths_are_rejected(tmp_path: Path, path: str) -> None:
    payload = _spec_payload()
    payload["outputs"]["request"] = path
    with pytest.raises(ContextBuildSpecError, match="outputs.request"):
        load_spec(_write(tmp_path, payload))


def test_resume_without_directory_starts_empty(tmp_path: Path) -> None:
    spec = load_spec(_write(tmp_path, _spec_payload()))
    store = CheckpointStore(tmp_path, spec, resume=True)
    assert store.get("search:q1") is None
    store.put("search:q1", {"ok": True})
    assert CheckpointStore(tmp_path, spec, resume=True).get("search:q1") == {"ok": True}


def test_resume_with_nonempty_directory_and_no_manifest_is_refused(tmp_path: Path) -> None:
    spec = load_spec(_write(tmp_path, _spec_payload()))
    directory = tmp_path / ".seomachine" / "context-build" / spec.slug / spec.date
    directory.mkdir(parents=True)
    (directory / "stray.json").write_text("{}", encoding="utf-8")
    with pytest.raises(ContextBuildResumeError, match="manifest"):
        CheckpointStore(tmp_path, spec, resume=True)


@pytest.mark.parametrize("field,value", [
    ("slug", "../../escape"),
    ("slug", "a/../../../escape"),
    ("date", "../../../escape"),
])
def test_directly_built_spec_escaping_root_is_refused(tmp_path: Path, field: str, value: str) -> None:
    spec = load_spec(_write(tmp_path, _spec_payload()))
    escaping = dataclasses.replace(spec, **{field: value})
    victim = tmp_path / "escape"
    victim.mkdir()
    (victim / "keep.txt").write_text("keep", encoding="utf-8")
    for resume in (False, True):
        with pytest.raises(ContextBuildResumeError, match="outside"):
            CheckpointStore(tmp_path, escaping, resume=resume)
    assert (victim / "keep.txt").exists()


def test_clear_failure_raises_resume_error(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    spec = load_spec(_write(tmp_path, _spec_payload()))
    CheckpointStore(tmp_path, spec, resume=False).put("k", 1)

    def _fail(*_args, **_kwargs):
        raise PermissionError("locked")

    monkeypatch.setattr("data_sources.modules.context_build.checkpoints.shutil.rmtree", _fail)
    with pytest.raises(ContextBuildResumeError, match="could not clear"):
        CheckpointStore(tmp_path, spec, resume=False)


def test_clear_that_leaves_directory_raises_resume_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    spec = load_spec(_write(tmp_path, _spec_payload()))
    CheckpointStore(tmp_path, spec, resume=False).put("k", 1)
    monkeypatch.setattr(
        "data_sources.modules.context_build.checkpoints.shutil.rmtree", lambda *_a, **_k: None
    )
    with pytest.raises(ContextBuildResumeError, match="remain"):
        CheckpointStore(tmp_path, spec, resume=False)


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
