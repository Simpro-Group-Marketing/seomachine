"""The BOM build refuses what the release scorer always refuses: no PAA capture, an undocumented story no-fit."""

from __future__ import annotations

import json

import pytest
from data_sources.modules.production import bom_build
from data_sources.modules.production.layout import load_or_create_run_id
from tests.production_bom_support import (
    STORY_NO_FIT,
    TODAY,
    good_loader,
    good_transport,
    make_workspace,
    paa_artifact,
    write_json,
)


@pytest.fixture(autouse=True)
def _pinned_clock(monkeypatch):
    monkeypatch.setenv("SEOMACHINE_TEST_CURRENT_UTC_DATE", TODAY)


def _build(layout):
    return bom_build.build_bom(layout, transport=good_transport(), claim_loader=good_loader())


def _no_questions(layout):
    spec = json.loads(layout.bom_spec.read_text(encoding="utf-8"))
    spec["paa_questions"] = []
    write_json(layout.bom_spec, spec)


def _story_role(layout, **changes):
    evidence = json.loads(layout.customer_proof_evidence.read_text(encoding="utf-8"))
    row = next(row for row in evidence["roles"] if row["role"] == "experience_story")
    row.update(changes)
    write_json(layout.customer_proof_evidence, evidence)


def test_no_paa_questions_still_binds_the_paa_artifact(tmp_path):
    layout = make_workspace(tmp_path)
    _no_questions(layout)
    paa = _build(layout)["paa"]
    assert paa["questions"] == []
    assert paa["artifact"]["path"].endswith(layout.paa_artifact.name)
    assert len(paa["artifact"]["sha256"]) == 64


def test_missing_paa_artifact_aborts_even_without_questions(tmp_path):
    layout = make_workspace(tmp_path, paa=False)
    _no_questions(layout)
    with pytest.raises(ValueError, match="paa-evidence"):
        _build(layout)


def test_blocked_paa_capture_with_no_eligible_questions_builds(tmp_path):
    layout = make_workspace(tmp_path)
    _no_questions(layout)
    blocked = {**paa_artifact(load_or_create_run_id(layout)), "eligible_questions": [], "status": "blocked"}
    write_json(layout.paa_artifact, blocked)
    assert _build(layout)["paa"]["questions"] == []


def test_paa_capture_from_another_run_aborts_even_without_questions(tmp_path):
    layout = make_workspace(tmp_path)
    _no_questions(layout)
    write_json(layout.paa_artifact, paa_artifact("another-run"))
    with pytest.raises(ValueError, match="does not match the production run id"):
        _build(layout)


def test_unselected_story_without_documented_no_fit_aborts(tmp_path):
    layout = make_workspace(tmp_path)
    _story_role(layout, rejected_overrides={})
    with pytest.raises(ValueError, match='--reject "experience_story=none:'):
        _build(layout)


def test_unselected_story_with_a_thin_reason_aborts(tmp_path):
    layout = make_workspace(tmp_path)
    _story_role(layout, rejected_overrides={"none": "n/a"})
    with pytest.raises(ValueError, match="experience_story"):
        _build(layout)


def test_documented_story_no_fit_builds_and_is_carried(tmp_path):
    layout = make_workspace(tmp_path)
    _story_role(layout, rejected_overrides={"none": STORY_NO_FIT})
    roles = _build(layout)["customer_proof"]["roles"]
    story = next(row for row in roles if row["role"] == "experience_story")
    assert story["rejected_overrides"] == {"none": STORY_NO_FIT}
