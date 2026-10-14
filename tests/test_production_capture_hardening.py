"""Capture hardening: location, canonical paths, clock sanity, the narrow fallback, and age limit."""

from __future__ import annotations

import datetime
import hashlib
import json
from pathlib import Path

import pytest
import requests
from data_sources.modules.production import bom_build, page_capture
from data_sources.modules.production.bom import validate_bom
from data_sources.modules.production.facts import verify_quotes
from data_sources.modules.production.page_capture import PageCapture, load_capture, record_capture
from data_sources.modules.production.record import latest_record
from data_sources.modules.production.truth import check_truth
from tests.production_bom_support import FACT_PAGE, FACT_QUOTE, FACT_URL, TODAY
from tests.production_capture_support import (
    BLOCKED,
    CAPTURE_DIR,
    CAPTURE_RECEIPT,
    CAPTURE_TEXT,
    LINKED_ARTICLE_TEXT,
    build_blocked,
    capture_workspace,
)
from tests.production_release_support import Checks, PageTransport, run

URL = "https://example.org/report"


@pytest.fixture(autouse=True)
def _environment(monkeypatch):
    monkeypatch.setenv("SEOMACHINE_TEST_CURRENT_UTC_DATE", TODAY)


def _write(root: Path, folder: str, text: str = CAPTURE_TEXT) -> tuple[Path, Path]:
    text_file = root / folder / "page.txt"
    text_file.parent.mkdir(parents=True, exist_ok=True)
    text_file.write_text(text, encoding="utf-8", newline="\n")
    return text_file, text_file.with_suffix(".json")


def _clock(monkeypatch, moved: datetime.timedelta) -> None:
    real = datetime.datetime.now(datetime.timezone.utc)
    monkeypatch.setattr(page_capture, "utc_now", lambda: real + moved)


def test_capture_files_must_live_under_research_source_captures(tmp_path):
    text_file, output = _write(tmp_path, "research/other")
    with pytest.raises(ValueError, match=r"research/source-captures"):
        record_capture(url=URL, title="T", text_file=text_file, output=output, workspace_root=tmp_path)
    text_file, _ = _write(tmp_path, CAPTURE_DIR)
    with pytest.raises(ValueError, match=r"research/source-captures"):
        record_capture(
            url=URL, title="T", text_file=text_file, output=tmp_path / "research" / "r.json", workspace_root=tmp_path
        )


def test_load_refuses_a_receipt_or_text_outside_source_captures(tmp_path):
    text_file, output = _write(tmp_path, CAPTURE_DIR)
    record_capture(url=URL, title="T", text_file=text_file, output=output, workspace_root=tmp_path)
    moved = tmp_path / "research" / "moved.json"
    moved.write_bytes(output.read_bytes())
    with pytest.raises(ValueError, match=r"research/source-captures"):
        load_capture(moved, tmp_path)
    other_text, _ = _write(tmp_path, "research/other")
    receipt = json.loads(output.read_text(encoding="utf-8"))
    receipt.update(text_path="research/other/page.txt", text_sha256=hashlib.sha256(other_text.read_bytes()).hexdigest())
    output.write_text(json.dumps(receipt), encoding="utf-8", newline="\n")
    with pytest.raises(ValueError, match=r"research/source-captures"):
        load_capture(output, tmp_path)


def test_record_refuses_a_non_canonical_text_path(tmp_path):
    text_file = tmp_path / CAPTURE_DIR / "my page.txt"
    text_file.parent.mkdir(parents=True)
    text_file.write_text(CAPTURE_TEXT, encoding="utf-8", newline="\n")
    output = tmp_path / CAPTURE_DIR / "page.json"
    with pytest.raises(ValueError, match="canonical"):
        record_capture(url=URL, title="T", text_file=text_file, output=output, workspace_root=tmp_path)
    assert not output.exists()


def test_future_dated_capture_is_refused_but_five_minutes_of_skew_is_allowed(tmp_path, monkeypatch):
    text_file, output = _write(tmp_path, CAPTURE_DIR)
    record_capture(url=URL, title="T", text_file=text_file, output=output, workspace_root=tmp_path)
    _clock(monkeypatch, datetime.timedelta(minutes=-3))
    assert load_capture(output, tmp_path).url == URL
    _clock(monkeypatch, datetime.timedelta(minutes=-10))
    with pytest.raises(ValueError, match="future"):
        load_capture(output, tmp_path)


def test_load_refuses_empty_captured_text(tmp_path):
    text_file, output = _write(tmp_path, CAPTURE_DIR)
    record_capture(url=URL, title="T", text_file=text_file, output=output, workspace_root=tmp_path)
    text_file.write_text(" \n", encoding="utf-8", newline="\n")
    receipt = json.loads(output.read_text(encoding="utf-8"))
    receipt["text_sha256"] = hashlib.sha256(text_file.read_bytes()).hexdigest()
    output.write_text(json.dumps(receipt), encoding="utf-8", newline="\n")
    with pytest.raises(ValueError, match="empty"):
        load_capture(output, tmp_path)


def _capture() -> PageCapture:
    return PageCapture(
        URL, "2026-10-14T08:00:00Z", "T", CAPTURE_TEXT, "0" * 64, "research/source-captures/x.json", "1" * 64
    )


def _check(reply):
    transport = PageTransport({URL: reply})
    return verify_quotes([(URL, FACT_QUOTE)], transport=transport, captures={URL: _capture()})[(URL, FACT_QUOTE)]


@pytest.mark.parametrize("status", [403, 429, 503])
def test_blocking_statuses_use_the_capture(status):
    assert _check((status, "")).status == "verified_capture"


@pytest.mark.parametrize("status", [401, 451, 400, 408, 500, 502])
def test_other_statuses_never_use_the_capture(status):
    assert _check((status, "")).status == "unreachable"


@pytest.mark.parametrize("error", [requests.Timeout("slow"), requests.ConnectionError("refused"), TimeoutError("t")])
def test_timeouts_and_connection_errors_use_the_capture(error):
    assert _check(error).status == "verified_capture"


def test_other_errors_never_use_the_capture():
    assert _check(ValueError("response too large")).status == "unreachable"


def test_stale_capture_refuses_the_build_naming_the_fact_and_remedy(tmp_path, monkeypatch):
    layout = capture_workspace(tmp_path)
    _clock(monkeypatch, datetime.timedelta(days=bom_build.CAPTURE_MAX_AGE_DAYS - 1))
    assert bom_build.build_bom(layout, transport=BLOCKED)["facts"][0]["verified_via"] == "chrome_capture"
    _clock(monkeypatch, datetime.timedelta(days=bom_build.CAPTURE_MAX_AGE_DAYS + 1))
    with pytest.raises(ValueError, match=r"fact f1.*older than 90 days.*re-capture the page in Chrome"):
        bom_build.build_bom(layout, transport=BLOCKED)


def test_a_stale_capture_is_ignored_while_the_page_is_reachable(tmp_path, monkeypatch):
    layout = capture_workspace(tmp_path)
    _clock(monkeypatch, datetime.timedelta(days=200))
    fact = bom_build.build_bom(layout, transport=PageTransport({FACT_URL: (200, FACT_PAGE)}))["facts"][0]
    assert "verified_via" not in fact


def _binding(**overrides):
    binding = {"path": CAPTURE_RECEIPT, "sha256": "a" * 64, "captured_at": "2026-10-14T08:00:00Z"}
    binding.update(overrides)
    return binding


def test_validate_bom_binds_capture_strictly(tmp_path):
    bom = build_blocked(capture_workspace(tmp_path))
    fact = bom["facts"][0]
    assert validate_bom(bom) == []
    for broken in (
        _binding(sha256="A" * 64), _binding(sha256="a" * 63), _binding(captured_at="2026-10-14"),
        _binding(captured_at="2026-10-14T08:00:00+00:00"), {**_binding(), "extra": "x"},
        {"path": CAPTURE_RECEIPT, "sha256": "a" * 64},
    ):
        fact["capture"] = broken
        assert any("capture" in error for error in validate_bom(bom)), broken
    fact["capture"] = _binding()
    fact.pop("verified_via")
    assert any("verified_via" in error for error in validate_bom(bom))


def test_capture_url_with_a_trailing_slash_refuses_the_build(tmp_path):
    layout = capture_workspace(tmp_path, url=FACT_URL + "/")
    with pytest.raises(ValueError, match=r"fact f1.*not the fact url"):
        bom_build.build_bom(layout, transport=BLOCKED)


def _rebind(tmp_path, bom, **receipt_changes):
    receipt_path = tmp_path / CAPTURE_RECEIPT
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    receipt.update(receipt_changes)
    receipt_path.write_text(json.dumps(receipt), encoding="utf-8", newline="\n")
    bom["facts"][0]["capture"]["sha256"] = hashlib.sha256(receipt_path.read_bytes()).hexdigest()


def test_truth_blocks_when_the_receipt_url_differs_from_the_fact_url(tmp_path):
    bom = build_blocked(capture_workspace(tmp_path))
    _rebind(tmp_path, bom, url=FACT_URL + "/")
    findings = check_truth(LINKED_ARTICLE_TEXT, bom, transport=BLOCKED, workspace_root=tmp_path)
    assert [f.severity for f in findings if f.check == "fact_quote"] == ["block"]


def test_release_blocks_when_the_page_answers_without_the_quote(tmp_path, monkeypatch):
    layout = capture_workspace(tmp_path)
    build_blocked(layout)
    Checks(monkeypatch, real_truth=True)
    assert run(layout, transport=PageTransport({FACT_URL: (200, "<p>The page was rewritten.</p>")})) == 1
    messages = [row["message"] for row in latest_record(layout)["findings"]]
    assert any("quote_missing" in message for message in messages)
