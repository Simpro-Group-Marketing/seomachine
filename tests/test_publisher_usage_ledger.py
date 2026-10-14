"""The proof-use ledger writer the publishers call after a successful live publish."""

from __future__ import annotations

import datetime
import json
import os
import subprocess
import sys

import pytest

from data_sources.modules.production import usage_ledger
from data_sources.modules.production.record import verify_publishable
from data_sources.modules.production.usage_ledger import (
    REUSE_REASON,
    proof_use_entries,
    record_publish_use,
)
from tests.production_bom_support import ARTICLE, NONVAULT_ID, TODAY
from tests.production_release_support import Checks, run, workspace

STORY_URL = "https://www.clockshark.com/testimonials/chesapeake"
LINKED = (
    "# Crew Time Tracking Guide\n\nCrews log time from any phone.\n\n## How crews track time\n\n"
    f"Chesapeake Lawn and Home runs [time tracking for mobile crews]({STORY_URL}).\n"
)
EXPECTED = {
    "proof_id": NONVAULT_ID,
    "source_type": "customer_story",
    "customer": "Chesapeake Lawn and Home",
    "source_url": STORY_URL,
    "article_slug": "field-service-software",
    "artifact_path": ARTICLE,
    "date_used": TODAY,
    "section": "How crews track time",
    "use_type": "theme",
    "claim_summary": "ClockShark page states: payroll and time tracking for mobile crews.",
    "reuse_reason": REUSE_REASON,
}


@pytest.fixture(autouse=True)
def _today(monkeypatch):
    monkeypatch.setenv("SEOMACHINE_TEST_CURRENT_UTC_DATE", TODAY)


def _released(tmp_path, monkeypatch, text=LINKED):
    layout = workspace(tmp_path, text=text)
    Checks(monkeypatch)
    assert run(layout) == 0
    return layout


def _ledger_path(layout):
    return layout.root / "config" / "customer-proof-usage-ledger.json"


def test_publish_use_appends_one_entry_per_linked_bom_proof_item(tmp_path, monkeypatch):
    layout = _released(tmp_path, monkeypatch)
    assert record_publish_use(layout.article, layout.root, published_path=ARTICLE) == [EXPECTED]
    ledger = json.loads(_ledger_path(layout).read_text(encoding="utf-8"))
    assert ledger["uses"] == [EXPECTED] and ledger["updated_at"] == TODAY
    assert list(ledger["uses"][0]) == list(EXPECTED)
    assert verify_publishable(layout.article, layout.root)["passed"] is True


def test_publish_use_dedupes_on_proof_and_artifact(tmp_path, monkeypatch):
    layout = _released(tmp_path, monkeypatch)
    record_publish_use(layout.article, layout.root, published_path=ARTICLE)
    before = _ledger_path(layout).read_bytes()
    assert record_publish_use(layout.article, layout.root, published_path=ARTICLE) == []
    assert _ledger_path(layout).read_bytes() == before
    assert record_publish_use(layout.article, layout.root, published_path=ARTICLE, date="2026-10-20") == []


def test_unlinked_proof_item_writes_nothing(tmp_path, monkeypatch):
    layout = _released(tmp_path, monkeypatch, text="# Crew Time Tracking Guide\n\nNo links here.\n")
    before = _ledger_path(layout).read_bytes()
    assert record_publish_use(layout.article, layout.root, published_path=ARTICLE) == []
    assert _ledger_path(layout).read_bytes() == before


def test_an_article_edited_after_its_release_is_refused_without_a_write(tmp_path, monkeypatch):
    layout = _released(tmp_path, monkeypatch)
    before = _ledger_path(layout).read_bytes()
    layout.article.write_text(LINKED + "\nEdited.\n", encoding="utf-8")
    with pytest.raises(ValueError, match="changed since its passing release"):
        record_publish_use(layout.article, layout.root, published_path=ARTICLE)
    assert _ledger_path(layout).read_bytes() == before


def test_existing_ledger_order_and_crlf_newlines_are_kept(tmp_path, monkeypatch):
    layout = _released(tmp_path, monkeypatch)
    existing = {"version": 1, "updated_at": "2026-01-01", "source_boundary": "scan", "uses": [{"proof_id": "old"}]}
    _ledger_path(layout).write_bytes(json.dumps(existing, indent=2).replace("\n", "\r\n").encode() + b"\r\n")
    record_publish_use(layout.article, layout.root, published_path=ARTICLE)
    raw = _ledger_path(layout).read_bytes()
    assert raw.count(b"\r\n") == raw.count(b"\n") and raw.endswith(b"}\r\n")
    ledger = json.loads(raw)
    assert list(ledger) == ["version", "updated_at", "source_boundary", "uses"]
    assert ledger["uses"] == [{"proof_id": "old"}, EXPECTED]


def _connector_bom(*items):
    return {"identity": {"slug": "fsm-guide"}, "context": {"status": "bound"}, "proof": list(items)}


def _item(kind, url, **extra):
    return {"id": "p1", "claim_id": f"claim-{kind}", "kind": kind, "url": url,
            "text": "Acme cut invoicing time.", "customer": "Acme", **extra}


def test_connector_claims_map_kind_and_source_type_and_the_section_heading():
    story = "https://www.simprogroup.com/customers/acme"
    quotes = "https://www.simprogroup.com/resources/acme-quotes"
    article = (
        f"# Guide\n\nIntro cites [Acme]({quotes}).\n\n## Faster invoicing\n\n"
        f"Acme sped up [invoicing]({story}).\n\n## Stories\n\nMore from [Acme]({story}).\n"
    )
    bom = _connector_bom(
        _item("metric", story, use_mode="public_metric", claim_type="public_metric"),
        _item("quote", quotes, use_mode="exact_quote", claim_type="exact_quote"),
        _item("experience_story", "https://www.capterra.com/p/1/x", use_mode="public_paraphrase"),
    )
    entries = proof_use_entries(bom, article, nonvault_rows=[], published_path="drafts/a.md", date_used=TODAY)
    summary = [(e["proof_id"], e["use_type"], e["source_type"], e["section"]) for e in entries]
    assert summary == [
        ("claim-metric", "metric", "customer_story", "Faster invoicing"),
        ("claim-quote", "approved_quote", "quote_matrix", ""),
    ]
    assert entries[0]["article_slug"] == "fsm-guide" and entries[0]["customer"] == "Acme"


def test_claim_summary_is_trimmed_to_200_characters():
    url = "https://www.simprogroup.com/customers/acme"
    bom = _connector_bom(_item("theme", url, text="word " * 80, use_mode="public_paraphrase"))
    (entry,) = proof_use_entries(bom, f"[Acme]({url})\n", nonvault_rows=[], published_path="drafts/a.md",
                                 date_used=TODAY)
    assert len(entry["claim_summary"]) <= 200 and entry["claim_summary"].startswith("word word")


def test_nonconnector_source_type_comes_from_the_nonvault_row():
    url = "https://www.bigchange.com/success-stories/x"
    bom = {"identity": {"slug": "s"}, "context": {"status": "not_applicable"},
           "proof": [_item("theme", url, claim_id="bigchange-row")]}
    rows = [{"proof_id": "bigchange-row", "source_type": "case_study"}]
    (entry,) = proof_use_entries(bom, f"[x]({url})\n", nonvault_rows=rows, published_path="p", date_used=TODAY)
    assert entry["source_type"] == "case_study"
    with pytest.raises(ValueError, match="bigchange-row"):
        proof_use_entries(bom, f"[x]({url})\n", nonvault_rows=[], published_path="p", date_used=TODAY)


def test_a_held_ledger_lock_times_out_with_a_clear_error_and_no_write(tmp_path, monkeypatch):
    layout = _released(tmp_path, monkeypatch)
    monkeypatch.setattr(usage_ledger, "LOCK_WAIT_SECONDS", 0.2)
    lock = _ledger_path(layout).with_name("customer-proof-usage-ledger.json.lock")
    _hold(lock, os.getpid(), 0)
    before = _ledger_path(layout).read_bytes()
    with pytest.raises(TimeoutError, match="usage ledger is locked by another publish"):
        record_publish_use(layout.article, layout.root, published_path=ARTICLE)
    assert _ledger_path(layout).read_bytes() == before and lock.exists()
    lock.unlink()
    assert record_publish_use(layout.article, layout.root, published_path=ARTICLE) == [EXPECTED]
    assert not lock.exists()


def _hold(lock, pid: int, age_seconds: float) -> None:
    created = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(seconds=age_seconds)
    lock.write_text(json.dumps({"pid": pid, "created_at": created.isoformat()}), encoding="utf-8")


def _dead_pid() -> int:
    process = subprocess.Popen([sys.executable, "-c", "pass"])
    process.wait()
    return process.pid


def test_pid_probe_tells_a_live_process_from_an_exited_one():
    assert usage_ledger._pid_running(os.getpid()) is True
    assert usage_ledger._pid_running(_dead_pid()) is False


@pytest.mark.parametrize("holder", ["dead", "old"])
def test_a_stale_ledger_lock_is_broken_and_the_write_succeeds(tmp_path, monkeypatch, holder):
    layout = _released(tmp_path, monkeypatch)
    monkeypatch.setattr(usage_ledger, "LOCK_WAIT_SECONDS", 5.0)
    lock = _ledger_path(layout).with_name("customer-proof-usage-ledger.json.lock")
    _hold(lock, _dead_pid(), 0) if holder == "dead" else _hold(lock, os.getpid(), 120)
    assert record_publish_use(layout.article, layout.root, published_path=ARTICLE) == [EXPECTED]
    assert not lock.exists()


def test_the_lockfile_names_its_holder(tmp_path, monkeypatch):
    layout = _released(tmp_path, monkeypatch)
    seen = {}
    real_append = usage_ledger._append_entries

    def spy(path, entries):
        seen.update(json.loads(path.with_name(path.name + ".lock").read_text(encoding="utf-8")))
        return real_append(path, entries)

    monkeypatch.setattr(usage_ledger, "_append_entries", spy)
    record_publish_use(layout.article, layout.root, published_path=ARTICLE)
    assert seen["pid"] == os.getpid() and datetime.datetime.fromisoformat(seen["created_at"]).tzinfo
