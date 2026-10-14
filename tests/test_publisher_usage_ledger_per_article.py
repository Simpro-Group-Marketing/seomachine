"""The usage ledger records each proof once per article, whichever day or publisher records it."""

from __future__ import annotations

import json

import pytest

from data_sources.modules.production import usage_ledger
from data_sources.modules.production.usage_ledger import record_publish_use
from tests.production_bom_support import ARTICLE, NONVAULT_ID, TODAY
from tests.production_release_support import Checks, run, workspace

STORY_URL = "https://www.clockshark.com/testimonials/chesapeake"
LINKED = (
    "# Crew Time Tracking Guide\n\nCrews log time from any phone.\n\n## How crews track time\n\n"
    f"Chesapeake Lawn and Home runs [time tracking for mobile crews]({STORY_URL}).\n"
)


@pytest.fixture(autouse=True)
def _today(monkeypatch):
    monkeypatch.setenv("SEOMACHINE_TEST_CURRENT_UTC_DATE", TODAY)


def test_a_later_publish_of_the_same_article_adds_no_second_use(tmp_path, monkeypatch):
    layout = workspace(tmp_path, text=LINKED)
    Checks(monkeypatch)
    assert run(layout) == 0
    assert len(record_publish_use(layout.article, layout.root, published_path=ARTICLE)) == 1
    ledger = layout.root / "config" / "customer-proof-usage-ledger.json"
    before = ledger.read_bytes()
    assert record_publish_use(layout.article, layout.root, published_path=ARTICLE, date="2026-10-20") == []
    assert ledger.read_bytes() == before


def test_the_same_proof_in_another_article_is_still_recorded(tmp_path):
    ledger = tmp_path / "ledger.json"
    first = {"proof_id": NONVAULT_ID, "artifact_path": ARTICLE, "date_used": TODAY}
    assert usage_ledger._append_entries(ledger, [first]) == [first]
    other = {**first, "artifact_path": "drafts/other-article-2026-10-13.md", "date_used": "2026-10-20"}
    assert usage_ledger._append_entries(ledger, [{**first, "date_used": "2026-10-20"}, other]) == [other]
    uses = json.loads(ledger.read_text(encoding="utf-8"))["uses"]
    assert [(use["artifact_path"], use["date_used"]) for use in uses] == [
        (ARTICLE, TODAY), ("drafts/other-article-2026-10-13.md", "2026-10-20")]
