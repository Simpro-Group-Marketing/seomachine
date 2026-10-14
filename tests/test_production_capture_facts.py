"""Chrome captures stand in only for an unreachable fact page, in verify_quotes and in the BOM build."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from data_sources.modules.production import bom_build
from data_sources.modules.production.bom import validate_bom, validate_spec
from data_sources.modules.production.facts import verify_quotes
from data_sources.modules.production.page_capture import PageCapture, load_capture
from tests.production_bom_support import (
    FACT_PAGE,
    FACT_QUOTE,
    FACT_URL,
    TODAY,
    good_transport,
    nonconnector_spec,
    write_json,
)
from tests.production_capture_support import (
    BLOCKED,
    CAPTURE_RECEIPT,
    CAPTURE_TEXT,
    build_blocked,
    capture_workspace,
    write_capture,
)
from tests.production_release_support import PageTransport


@pytest.fixture(autouse=True)
def _environment(monkeypatch):
    monkeypatch.setenv("SEOMACHINE_TEST_CURRENT_UTC_DATE", TODAY)


def _capture(text: str = CAPTURE_TEXT, url: str = FACT_URL) -> PageCapture:
    return PageCapture(
        url=url, captured_at="2026-10-14T08:00:00Z", page_title="Example", text=text,
        text_sha256="0" * 64, path="research/source-captures/x/example.org-1.json", receipt_sha256="1" * 64,
    )


def _status(status: int, *, captures, quote: str = FACT_QUOTE, body: str = ""):
    transport = PageTransport({FACT_URL: (status, body)})
    return verify_quotes([(FACT_URL, quote)], transport=transport, captures=captures)[(FACT_URL, quote)]


def test_blocked_page_with_a_capture_is_verified_by_the_capture():
    check = _status(403, captures={FACT_URL: _capture()})
    assert check.status == "verified_capture"
    assert check.detail == (
        "quote found in Chrome capture research/source-captures/x/example.org-1.json (captured 2026-10-14T08:00:00Z)"
    )


def test_timeout_is_also_covered_by_a_capture():
    transport = PageTransport({FACT_URL: TimeoutError("slow")})
    result = verify_quotes([(FACT_URL, FACT_QUOTE)], transport=transport, captures={FACT_URL: _capture()})
    assert result[(FACT_URL, FACT_QUOTE)].status == "verified_capture"


@pytest.mark.parametrize("status", [404, 410])
def test_a_gone_page_never_uses_a_capture(status):
    assert _status(status, captures={FACT_URL: _capture()}).status == "gone"


def test_a_reachable_page_never_uses_a_capture():
    assert _status(200, captures={FACT_URL: _capture()}, body=FACT_PAGE).status == "verified"
    missing = _status(200, captures={FACT_URL: _capture()}, body="<p>Other text.</p>")
    assert missing.status == "quote_missing"
    assert "capture" not in missing.detail


def test_quote_absent_from_the_capture_is_quote_missing_naming_the_capture():
    check = _status(403, captures={FACT_URL: _capture(text="Nothing relevant here.")})
    assert check.status == "quote_missing"
    assert "research/source-captures/x/example.org-1.json" in check.detail


def test_a_capture_for_another_url_is_not_used():
    other = "https://example.org/other"
    assert _status(403, captures={other: _capture(url=other)}).status == "unreachable"
    assert _status(403, captures=None).status == "unreachable"
    assert _status(403, captures={}).status == "unreachable"


def test_spec_accepts_a_capture_path_and_rejects_a_non_text_one():
    spec = nonconnector_spec()
    spec["facts"][0]["capture"] = CAPTURE_RECEIPT
    assert validate_spec(spec) == []
    spec["facts"][0]["capture"] = 5
    assert any("capture" in error for error in validate_spec(spec))
    spec["facts"][0]["capture"] = "  "
    assert any("capture" in error for error in validate_spec(spec))


def test_blocked_fact_with_a_capture_builds_with_the_capture_recorded(tmp_path):
    layout = capture_workspace(tmp_path)
    bom = build_blocked(layout)
    fact = bom["facts"][0]
    capture = load_capture(CAPTURE_RECEIPT, tmp_path)
    assert fact["verified_via"] == "chrome_capture"
    assert fact["capture"] == {"path": CAPTURE_RECEIPT, "sha256": capture.receipt_sha256, "captured_at": capture.captured_at}
    assert fact["quote"] == FACT_QUOTE
    assert validate_bom(bom) == []


def test_a_reachable_page_builds_without_a_capture_record(tmp_path):
    layout = capture_workspace(tmp_path)
    fact = bom_build.build_bom(layout, transport=good_transport())["facts"][0]
    assert "verified_via" not in fact and "capture" not in fact


def test_capture_for_another_url_refuses_the_build_naming_the_fact(tmp_path):
    layout = capture_workspace(tmp_path, url="https://example.org/other")
    with pytest.raises(ValueError, match=r"fact f1.*capture"):
        bom_build.build_bom(layout, transport=BLOCKED)


def test_quote_absent_from_the_capture_refuses_the_build(tmp_path):
    layout = capture_workspace(tmp_path, text="Just a cookie banner.\n")
    with pytest.raises(ValueError, match=r"fact f1.*quote_missing"):
        bom_build.build_bom(layout, transport=BLOCKED)


def test_gone_page_refuses_the_build_even_with_a_capture(tmp_path):
    layout = capture_workspace(tmp_path)
    with pytest.raises(ValueError, match=r"fact f1.*gone"):
        bom_build.build_bom(layout, transport=PageTransport({FACT_URL: (404, "")}))


def test_tampered_or_missing_capture_refuses_the_build(tmp_path):
    layout = capture_workspace(tmp_path)
    Path(tmp_path / CAPTURE_RECEIPT).with_suffix(".txt").write_text("edited " + CAPTURE_TEXT, encoding="utf-8", newline="\n")
    with pytest.raises(ValueError, match=r"fact f1.*capture"):
        bom_build.build_bom(layout, transport=BLOCKED)
    Path(tmp_path / CAPTURE_RECEIPT).unlink()
    with pytest.raises(ValueError, match=r"fact f1.*capture"):
        bom_build.build_bom(layout, transport=BLOCKED)


def test_claim_numbers_must_still_be_in_the_captured_quote(tmp_path):
    layout = capture_workspace(tmp_path)
    spec = json.loads(layout.bom_spec.read_text(encoding="utf-8"))
    spec["facts"][0]["claim"] = "More than 99,000 trade businesses worldwide trust it"
    write_json(layout.bom_spec, spec)
    with pytest.raises(ValueError, match="claim numbers are not in its quote"):
        bom_build.build_bom(layout, transport=BLOCKED)


def test_two_facts_on_one_url_with_different_captures_refuse(tmp_path):
    layout = capture_workspace(tmp_path)
    write_capture(tmp_path, name="example.org-2")
    spec = json.loads(layout.bom_spec.read_text(encoding="utf-8"))
    spec["facts"].append({**spec["facts"][0], "id": "f2", "capture": CAPTURE_RECEIPT.replace("example.org-1", "example.org-2")})
    write_json(layout.bom_spec, spec)
    with pytest.raises(ValueError, match="different captures"):
        bom_build.build_bom(layout, transport=BLOCKED)


def test_validate_bom_requires_the_capture_binding_for_chrome_verified_facts(tmp_path):
    bom = build_blocked(capture_workspace(tmp_path))
    del bom["facts"][0]["capture"]
    assert any("capture" in error for error in validate_bom(bom))
    bom["facts"][0].pop("verified_via")
    assert validate_bom(bom) == []
