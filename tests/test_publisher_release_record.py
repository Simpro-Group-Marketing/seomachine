"""Blog publishers trust only a passing release record and record proof use after a live publish."""

from __future__ import annotations

import sys
from unittest.mock import patch

import pytest

from data_sources.modules import grav_publisher, wordpress_publisher
from data_sources.modules.grav_publisher import GravPartialPublishError, GravPublisher, GravPublishError
from data_sources.modules.production.truth_text import Finding
from data_sources.modules.wordpress_publisher import WordPressPartialPublishError, WordPressPublisher
from tests.production_bom_support import ARTICLE, TODAY
from tests.production_release_support import Checks, run, workspace
from tests.test_publisher_usage_ledger import EXPECTED, LINKED

GATE = "data_sources.modules.production.publish_gate"
PUSHED = {"action": "created", "commit_url": "https://github.example/commit/1"}


@pytest.fixture(autouse=True)
def _today(monkeypatch):
    monkeypatch.setenv("SEOMACHINE_TEST_CURRENT_UTC_DATE", TODAY)


@pytest.fixture
def checks(monkeypatch):
    return Checks(monkeypatch)


@pytest.fixture
def layout(tmp_path, checks):
    layout = workspace(tmp_path, text=LINKED)
    assert run(layout) == 0
    return layout


def _ledger(layout):
    return (layout.root / "config" / "customer-proof-usage-ledger.json").read_bytes()


def _wordpress():
    return WordPressPublisher(url="https://wordpress.example", username="editor", app_password="password")


def _wp_publish(layout, publisher=None, **mocks):
    publisher = publisher or _wordpress()
    create = mocks.get("create", {"id": 7, "link": "https://wordpress.example/?p=7"})
    with (
        patch.object(publisher, "create_draft", return_value=create) as create_draft,
        patch.object(publisher, "set_yoast_meta", **mocks.get("yoast", {"return_value": {"yoast_seo": {}}})),
    ):
        try:
            return publisher.publish_draft(str(layout.article), workspace_root=layout.root), create_draft
        except Exception as error:
            error.create_draft = create_draft
            raise


def _grav():
    return GravPublisher(repo="owner/repo", branch="dev", blog_path="blogs", lang="en")


# ---- WordPress -------------------------------------------------------------------------------


def test_wordpress_blog_publishes_with_a_passing_record_and_records_proof_use(layout):
    result, create_draft = _wp_publish(layout)
    create_draft.assert_called_once()
    assert result["post_id"] == 7
    assert f'"artifact_path": "{ARTICLE}"' in _ledger(layout).decode()
    assert EXPECTED["proof_id"] in _ledger(layout).decode()


def test_wordpress_refuses_an_article_edited_after_its_release(layout):
    layout.article.write_text(LINKED + "\nEdited.\n", encoding="utf-8")
    before = _ledger(layout)
    with pytest.raises(ValueError, match="changed since its passing release") as raised:
        _wp_publish(layout)
    raised.value.create_draft.assert_not_called()
    assert _ledger(layout) == before


def test_wordpress_refuses_a_failing_record(layout, checks):
    checks.truth_findings = [Finding("fact_quote", "block", "gone", None)]
    assert run(layout) == 1
    with pytest.raises(ValueError, match="did not pass") as raised:
        _wp_publish(layout)
    raised.value.create_draft.assert_not_called()


def test_wordpress_meta_failure_leaves_the_ledger_untouched(layout):
    before = _ledger(layout)
    with pytest.raises(WordPressPartialPublishError):
        _wp_publish(layout, yoast={"side_effect": RuntimeError("Yoast update failed")})
    assert _ledger(layout) == before


def test_wordpress_landing_page_still_runs_the_old_readiness_gate(tmp_path):
    page = tmp_path / "landing-page.md"
    page.write_text("# Landing Page\n\nBook a demo today.\n", encoding="utf-8")
    publisher = _wordpress()
    with (
        patch.object(wordpress_publisher, "run_publish_readiness", return_value={"passed": True}) as readiness,
        patch(f"{GATE}.verify_publishable") as verify,
        patch(f"{GATE}.record_publish_use") as ledger,
        patch.object(publisher, "create_draft", return_value={"id": 3, "link": ""}),
        patch.object(publisher, "set_yoast_meta", return_value={}),
    ):
        publisher.publish_draft(str(page), post_type="page")
    readiness.assert_called_once_with(str(page), proof_sidecar=None, artifact_kind="landing_page")
    verify.assert_not_called()
    ledger.assert_not_called()


@pytest.mark.parametrize("flag", ["--proof-sidecar", "--context-pack", "--assembly-bom", "--vault-root"])
def test_retired_gate_flag_on_a_blog_post_exits_two(tmp_path, capsys, flag):
    argv = ["wordpress_publisher.py", str(tmp_path / "post.md"), flag, "x"]
    with patch.object(sys, "argv", argv), pytest.raises(SystemExit) as raised:
        wordpress_publisher.main()
    assert raised.value.code == 2
    assert f"{flag} is retired for blog posts" in capsys.readouterr().err


# ---- Grav ------------------------------------------------------------------------------------


def test_grav_publishes_with_a_passing_record_and_records_proof_use(layout):
    publisher = _grav()
    with patch.object(publisher, "push_article", return_value=dict(PUSHED)) as push:
        result = publisher.publish(str(layout.article), workspace_root=layout.root)
    push.assert_called_once()
    assert result["dry_run"] is False
    assert f'"artifact_path": "{ARTICLE}"' in _ledger(layout).decode()


def test_grav_dry_run_needs_a_passing_record_and_never_writes_the_ledger(layout, tmp_path):
    before = _ledger(layout)
    assert _grav().publish(str(layout.article), dry_run=True, workspace_root=layout.root)["dry_run"] is True
    assert _ledger(layout) == before
    unreleased = workspace(tmp_path / "fresh", text=LINKED)
    with pytest.raises(GravPublishError, match="no release record"):
        _grav().publish(str(unreleased.article), dry_run=True, workspace_root=unreleased.root)


def test_grav_refuses_an_edited_article_and_a_failing_record(layout, checks):
    publisher = _grav()
    with patch.object(publisher, "push_article") as push:
        layout.article.write_text(LINKED + "\nEdited.\n", encoding="utf-8")
        with pytest.raises(GravPublishError, match="changed since its passing release"):
            publisher.publish(str(layout.article), workspace_root=layout.root)
        checks.truth_findings = [Finding("fact_quote", "block", "gone", None)]
        assert run(layout) == 1
        with pytest.raises(GravPublishError, match="did not pass"):
            publisher.publish(str(layout.article), workspace_root=layout.root)
    push.assert_not_called()


def test_grav_push_failure_or_partial_publish_leaves_the_ledger_untouched(layout):
    before = _ledger(layout)
    publisher = _grav()
    with patch.object(publisher, "push_article", side_effect=GravPublishError("gh failed")):
        with pytest.raises(GravPublishError, match="gh failed"):
            publisher.publish(str(layout.article), workspace_root=layout.root)

    def push_and_edit(*args, **kwargs):
        layout.article.write_text(LINKED + "\nEdited during push.\n", encoding="utf-8")
        return dict(PUSHED)

    with patch.object(publisher, "push_article", side_effect=push_and_edit):
        with pytest.raises(GravPartialPublishError):
            publisher.publish(str(layout.article), workspace_root=layout.root)
    assert _ledger(layout) == before


def test_grav_cli_rejects_a_retired_gate_flag(tmp_path, capsys):
    argv = ["grav_publisher.py", str(tmp_path / "post.md"), "--proof-sidecar", "x"]
    with patch.object(sys, "argv", argv), pytest.raises(SystemExit) as raised:
        grav_publisher.main()
    assert raised.value.code == 2
    assert "--proof-sidecar" in capsys.readouterr().err
