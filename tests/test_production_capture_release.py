"""A fact page that blocks bots releases on its Chrome capture with a warning; an edited capture blocks."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from data_sources.modules.production import release
from data_sources.modules.production.record import latest_record, verify_publishable
from data_sources.modules.production.truth import check_truth
from tests.production_bom_support import FACT_URL, TODAY
from tests.production_capture_support import (
    BLOCKED,
    CAPTURE_RECEIPT,
    CAPTURE_TEXT,
    LINKED_ARTICLE_TEXT,
    build_blocked,
    capture_workspace,
)
from tests.production_release_support import Checks, PageTransport, run


@pytest.fixture(autouse=True)
def _environment(monkeypatch):
    monkeypatch.setenv("SEOMACHINE_TEST_CURRENT_UTC_DATE", TODAY)
    monkeypatch.delenv(release.ENV_WORKERS, raising=False)


def _rows(layout, check):
    return [row for row in latest_record(layout)["findings"] if row["check"] == check]


def test_blocked_fact_with_a_valid_capture_releases_with_a_warning(tmp_path, monkeypatch):
    layout = capture_workspace(tmp_path)
    bom = build_blocked(layout)
    captured_at = bom["facts"][0]["capture"]["captured_at"]
    Checks(monkeypatch, real_truth=True)
    assert run(layout, transport=BLOCKED) == 0
    quote_rows = _rows(layout, "fact_quote")
    assert [row["severity"] for row in quote_rows] == ["warn"]
    for part in ("f1", FACT_URL, captured_at, CAPTURE_RECEIPT):
        assert part in quote_rows[0]["message"]
    assert [row["severity"] for row in _rows(layout, "link_resolution")] == ["warn"]
    assert _rows(layout, "fact_carried_forward") == []
    assert verify_publishable(layout.article, layout.root)["passed"] is True
    rebuilt = json.loads(layout.bom.read_text(encoding="utf-8"))["facts"][0]
    assert rebuilt["verified_via"] == "chrome_capture"


def test_a_page_that_is_reachable_again_drops_the_capture_warning(tmp_path, monkeypatch):
    layout = capture_workspace(tmp_path)
    build_blocked(layout)
    Checks(monkeypatch, real_truth=True)
    assert run(layout, transport=PageTransport()) == 0
    assert _rows(layout, "fact_quote") == []
    assert "capture" not in json.loads(layout.bom.read_text(encoding="utf-8"))["facts"][0]


def test_edited_capture_at_release_blocks(tmp_path, monkeypatch):
    layout = capture_workspace(tmp_path)
    build_blocked(layout)
    Checks(monkeypatch, real_truth=True)
    Path(tmp_path / CAPTURE_RECEIPT).with_suffix(".txt").write_text(
        CAPTURE_TEXT.replace("24,000", "99,000"), encoding="utf-8", newline="\n"
    )
    assert run(layout, transport=BLOCKED) == 1
    with pytest.raises(ValueError, match="did not pass"):
        verify_publishable(layout.article, layout.root)


def test_truth_blocks_when_the_bound_capture_was_edited_after_the_build(tmp_path):
    layout = capture_workspace(tmp_path)
    bom = build_blocked(layout)
    Path(tmp_path / CAPTURE_RECEIPT).with_suffix(".txt").write_text(
        CAPTURE_TEXT + "added line\n", encoding="utf-8", newline="\n"
    )
    findings = check_truth(LINKED_ARTICLE_TEXT, bom, transport=BLOCKED, workspace_root=tmp_path)
    rows = [f for f in findings if f.check == "fact_quote"]
    assert [f.severity for f in rows] == ["block"]
    assert CAPTURE_RECEIPT in rows[0].message and "f1" in rows[0].message
    link = [f for f in findings if f.check == "link_resolution"]
    assert [f.severity for f in link] == ["block"]


def test_truth_warns_for_a_valid_capture_and_blocks_when_the_capture_changed_hash(tmp_path):
    layout = capture_workspace(tmp_path)
    bom = build_blocked(layout)
    findings = check_truth(LINKED_ARTICLE_TEXT, bom, transport=BLOCKED, workspace_root=tmp_path)
    assert [f.severity for f in findings if f.check == "fact_quote"] == ["warn"]
    bom["facts"][0]["capture"]["sha256"] = "0" * 64
    findings = check_truth(LINKED_ARTICLE_TEXT, bom, transport=BLOCKED, workspace_root=tmp_path)
    assert [f.severity for f in findings if f.check == "fact_quote"] == ["block"]


def test_truth_without_a_workspace_root_does_not_trust_a_capture(tmp_path):
    bom = build_blocked(capture_workspace(tmp_path))
    findings = check_truth(LINKED_ARTICLE_TEXT, bom, transport=BLOCKED)
    assert [f.severity for f in findings if f.check == "fact_quote"] == ["warn"]
    assert [f.severity for f in findings if f.check == "link_resolution"] == ["warn"]
    assert "capture" not in [f.message for f in findings if f.check == "fact_quote"][0]
