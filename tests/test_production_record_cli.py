"""The record CLI: `python -m data_sources.modules.production.record verify <article>`."""

from __future__ import annotations

import pytest

from data_sources.modules.production import record, release
from data_sources.modules.production.record import latest_record_path
from tests.production_bom_support import ARTICLE, TODAY
from tests.production_release_support import ARTICLE_TEXT, Checks, run, workspace


@pytest.fixture(autouse=True)
def _environment(monkeypatch):
    monkeypatch.setenv("SEOMACHINE_TEST_CURRENT_UTC_DATE", TODAY)
    monkeypatch.delenv(release.ENV_WORKERS, raising=False)


def _verify(root, *extra):
    return record.main(["verify", ARTICLE, "--workspace-root", str(root), *extra])


def test_publishable_article_exits_zero_and_prints_the_record(tmp_path, monkeypatch, capsys):
    layout = workspace(tmp_path)
    Checks(monkeypatch)
    assert run(layout) == 0
    capsys.readouterr()
    assert _verify(tmp_path) == 0
    out = capsys.readouterr().out
    assert str(latest_record_path(layout)) in out and "passed: true" in out


def test_edited_article_exits_one_with_the_reason(tmp_path, monkeypatch, capsys):
    layout = workspace(tmp_path)
    Checks(monkeypatch)
    assert run(layout) == 0
    layout.article.write_text(ARTICLE_TEXT + "\nEdited.\n", encoding="utf-8")
    capsys.readouterr()
    assert _verify(tmp_path) == 1
    out = capsys.readouterr().out
    assert "passed: true" in out and "refused: article changed since its passing release" in out


def test_failed_release_exits_one(tmp_path, monkeypatch, capsys):
    layout = workspace(tmp_path)
    checks = Checks(monkeypatch)
    checks.truth_findings = [release.Finding("fact_quote", "block", "gone", None)]
    assert run(layout) == 1
    capsys.readouterr()
    assert _verify(tmp_path) == 1
    out = capsys.readouterr().out
    assert "passed: false" in out and "did not pass" in out


def test_no_record_exits_one(tmp_path, capsys):
    workspace(tmp_path)
    assert _verify(tmp_path) == 1
    out = capsys.readouterr().out
    assert "record: none" in out and "no release record" in out


@pytest.mark.parametrize("argv", [[], ["verify"], ["publish", ARTICLE], ["verify", ARTICLE, "--bogus"]])
def test_argument_errors_exit_two(argv):
    assert record.main(argv) == 2


def test_article_outside_drafts_or_rewrites_exits_two(tmp_path, capsys):
    assert record.main(["verify", "notes/elsewhere.md", "--workspace-root", str(tmp_path)]) == 2
    assert "drafts" in capsys.readouterr().err
