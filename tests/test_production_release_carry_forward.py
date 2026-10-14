"""Release carry-forward trust: only a pipeline-written BOM carries facts; carry-forwards leave a record trace."""

from __future__ import annotations

import json

import pytest
from data_sources.modules.production import release
from data_sources.modules.production.layout import stored_bom_sha256
from data_sources.modules.production.record import file_sha256, latest_record, verify_publishable
from data_sources.modules.production.truth_text import Finding
from tests.production_bom_support import FACT_URL, TODAY, write_json
from tests.production_release_support import ARTICLE_TEXT, LINKED_ARTICLE_TEXT, Checks, PageTransport, run, workspace

FORGED_QUOTE = "Trusted by more than 99,000 trade businesses worldwide"
FORGED_CLAIM = "More than 99,000 trade businesses worldwide trust it"
STAMP = "2026-10-01T08:00:00Z"


@pytest.fixture(autouse=True)
def _environment(monkeypatch):
    monkeypatch.setenv("SEOMACHINE_TEST_CURRENT_UTC_DATE", TODAY)
    monkeypatch.delenv(release.ENV_WORKERS, raising=False)


def _edit_bom(layout, change):
    bom = json.loads(layout.bom.read_text(encoding="utf-8"))
    change(bom["facts"][0])
    write_json(layout.bom, bom)


def test_forged_prior_bom_is_not_carried_forward(tmp_path, monkeypatch):
    layout = workspace(tmp_path, text=LINKED_ARTICLE_TEXT.replace("24,000", "99,000"))
    Checks(monkeypatch, real_truth=True)
    spec = json.loads(layout.bom_spec.read_text(encoding="utf-8"))
    spec["facts"][0].update(quote=FORGED_QUOTE, claim=FORGED_CLAIM)
    write_json(layout.bom_spec, spec)
    _edit_bom(layout, lambda fact: fact.update(quote=FORGED_QUOTE, claim=FORGED_CLAIM, verified_at=STAMP))
    assert run(layout, transport=PageTransport({FACT_URL: (403, "")})) == 1
    with pytest.raises(ValueError, match="did not pass"):
        verify_publishable(layout.article, layout.root)


def test_hand_edited_prior_bom_with_a_forged_stamp_is_not_carried_forward(tmp_path, monkeypatch):
    layout = workspace(tmp_path, text=LINKED_ARTICLE_TEXT)
    Checks(monkeypatch, real_truth=True)
    _edit_bom(layout, lambda fact: fact.update(verified_at="forged"))
    assert run(layout, transport=PageTransport({FACT_URL: (403, "")})) == 1


def test_hand_edited_prior_bom_with_a_valid_stamp_is_not_carried_forward(tmp_path, monkeypatch):
    layout = workspace(tmp_path, text=LINKED_ARTICLE_TEXT)
    Checks(monkeypatch, real_truth=True)
    _edit_bom(layout, lambda fact: fact.update(verified_at=STAMP))
    assert run(layout, transport=PageTransport({FACT_URL: (403, "")})) == 1


def test_a_pipeline_written_prior_bom_still_carries_forward_with_a_warning(tmp_path, monkeypatch):
    layout = workspace(tmp_path, text=LINKED_ARTICLE_TEXT)
    Checks(monkeypatch, real_truth=True)
    original = json.loads(layout.bom.read_text(encoding="utf-8"))["facts"][0]["verified_at"]
    assert run(layout, transport=PageTransport({FACT_URL: (403, "")})) == 0
    assert json.loads(layout.bom.read_text(encoding="utf-8"))["facts"][0]["verified_at"] == original
    assert verify_publishable(layout.article, layout.root)["passed"] is True


def test_every_pipeline_bom_write_records_its_hash_in_the_run_state(tmp_path, monkeypatch):
    layout = workspace(tmp_path)
    assert stored_bom_sha256(layout) == file_sha256(layout.bom)
    Checks(monkeypatch)
    assert run(layout, transport=PageTransport()) == 0
    assert stored_bom_sha256(layout) == file_sha256(layout.bom)
    assert json.loads(layout.run_state.read_text(encoding="utf-8"))["bom_sha256"] == file_sha256(layout.bom)


def test_a_carried_forward_fact_is_recorded_even_when_truth_cannot_warn(tmp_path, monkeypatch):
    layout = workspace(tmp_path, text=ARTICLE_TEXT)
    Checks(monkeypatch)
    original = json.loads(layout.bom.read_text(encoding="utf-8"))["facts"][0]["verified_at"]
    assert run(layout, transport=PageTransport({FACT_URL: (403, "")})) == 0
    rows = [row for row in latest_record(layout)["findings"] if row["check"] == "fact_carried_forward"]
    assert [row["severity"] for row in rows] == ["warn"]
    for part in ("f1", FACT_URL, original, "HTTP 403"):
        assert part in rows[0]["message"]


def test_summary_prints_every_non_warn_finding(tmp_path, monkeypatch, capsys):
    layout = workspace(tmp_path)
    checks = Checks(monkeypatch)
    checks.truth_findings = [Finding("odd_check", "error", "odd severity message", 3)]
    assert run(layout, transport=PageTransport()) == 1
    assert "BLOCK odd_check line 3: odd severity message" in capsys.readouterr().out
