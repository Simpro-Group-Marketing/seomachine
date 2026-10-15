"""Chrome page-capture receipts: record, reload, and refuse anything that was edited or misdescribed."""

from __future__ import annotations

import json
import re

import pytest
from data_sources.modules.production import page_capture
from data_sources.modules.production.page_capture import SCHEMA, load_capture, record_capture

URL = "https://example.org/report"
TITLE = "Annual report"
TEXT = "Trusted by more than 24,000 trade businesses worldwide.\n"


def _record(root, *, url=URL, title=TITLE, text=TEXT):
    text_file = root / "research" / "source-captures" / "demo-2026-10-14" / "example.org-1.txt"
    text_file.parent.mkdir(parents=True, exist_ok=True)
    text_file.write_text(text, encoding="utf-8", newline="\n")
    output = root / "research" / "source-captures" / "demo-2026-10-14" / "example.org-1.json"
    record_capture(url=url, title=title, text_file=text_file, output=output, workspace_root=root, client="claude_code")
    return text_file, output


def _edit_receipt(output, change):
    payload = json.loads(output.read_text(encoding="utf-8"))
    change(payload)
    output.write_text(json.dumps(payload), encoding="utf-8", newline="\n")


def test_record_and_load_round_trip(tmp_path):
    _text_file, output = _record(tmp_path)
    capture = load_capture(output, tmp_path)
    assert capture.url == URL
    assert capture.page_title == TITLE
    assert capture.text == TEXT
    assert capture.path == "research/source-captures/demo-2026-10-14/example.org-1.json"
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", capture.captured_at)
    assert re.fullmatch(r"[0-9a-f]{64}", capture.text_sha256)
    assert re.fullmatch(r"[0-9a-f]{64}", capture.receipt_sha256)
    receipt = json.loads(output.read_text(encoding="utf-8"))
    assert receipt["schema"] == SCHEMA
    assert receipt["surface"] == "chrome_main_window"
    assert receipt["client"] == "claude_code" and capture.client == "claude_code"
    assert receipt["text_path"] == "research/source-captures/demo-2026-10-14/example.org-1.txt"


def test_load_accepts_a_workspace_relative_path(tmp_path):
    _record(tmp_path)
    capture = load_capture("research/source-captures/demo-2026-10-14/example.org-1.json", tmp_path)
    assert capture.url == URL


def test_tampered_text_file_refuses(tmp_path):
    text_file, output = _record(tmp_path)
    text_file.write_text(TEXT.replace("24,000", "99,000"), encoding="utf-8", newline="\n")
    with pytest.raises(ValueError, match="text hash"):
        load_capture(output, tmp_path)


def test_wrong_surface_refuses(tmp_path):
    _text_file, output = _record(tmp_path)
    _edit_receipt(output, lambda payload: payload.update(surface="headless_fetch"))
    with pytest.raises(ValueError, match="surface"):
        load_capture(output, tmp_path)


def test_wrong_schema_refuses(tmp_path):
    _text_file, output = _record(tmp_path)
    _edit_receipt(output, lambda payload: payload.update(schema="other/v1"))
    with pytest.raises(ValueError, match="schema"):
        load_capture(output, tmp_path)


def test_a_capture_recorded_before_the_client_field_reads_as_unrecorded(tmp_path):
    _text_file, output = _record(tmp_path)
    _edit_receipt(output, lambda payload: (payload.pop("client"), payload.update(captured_at="2026-10-14T08:00:00Z")))
    assert load_capture(output, tmp_path).client == "unrecorded"


def test_a_capture_made_after_the_field_shipped_must_name_its_client(tmp_path):
    _text_file, output = _record(tmp_path)
    _edit_receipt(output, lambda payload: payload.pop("client"))
    with pytest.raises(ValueError, match="client"):
        load_capture(output, tmp_path)


def test_an_unknown_client_refuses(tmp_path):
    _text_file, output = _record(tmp_path)
    _edit_receipt(output, lambda payload: payload.update(client="cursor"))
    with pytest.raises(ValueError, match="client"):
        load_capture(output, tmp_path)


def test_record_refuses_codex_inside_claude_code(tmp_path, monkeypatch):
    monkeypatch.setenv("CLAUDECODE", "1")
    text_file, output = _record(tmp_path)
    with pytest.raises(ValueError, match="Claude Code"):
        record_capture(url=URL, title=TITLE, text_file=text_file, output=output, workspace_root=tmp_path,
                       client="codex")
    monkeypatch.delenv("CLAUDECODE")
    record_capture(url=URL, title=TITLE, text_file=text_file, output=output, workspace_root=tmp_path, client="codex")
    assert load_capture(output, tmp_path).client == "codex"


def test_extra_or_missing_key_refuses(tmp_path):
    _text_file, output = _record(tmp_path)
    _edit_receipt(output, lambda payload: payload.update(note="hello"))
    with pytest.raises(ValueError, match="unexpected"):
        load_capture(output, tmp_path)
    _text_file, output = _record(tmp_path)
    _edit_receipt(output, lambda payload: payload.pop("page_title"))
    with pytest.raises(ValueError, match="missing"):
        load_capture(output, tmp_path)


def test_text_path_outside_the_workspace_refuses(tmp_path):
    root = tmp_path / "workspace"
    _text_file, output = _record(root)
    _edit_receipt(output, lambda payload: payload.update(text_path="../outside.txt"))
    with pytest.raises(ValueError, match="text_path"):
        load_capture(output, root)


def test_receipt_outside_the_workspace_refuses(tmp_path):
    root = tmp_path / "workspace"
    root.mkdir()
    other = tmp_path / "elsewhere"
    _text_file, output = _record(other)
    with pytest.raises(ValueError, match="outside the workspace"):
        load_capture(output, root)


def test_record_refuses_a_relative_url_and_empty_text(tmp_path):
    with pytest.raises(ValueError, match="absolute http"):
        _record(tmp_path, url="/report")
    with pytest.raises(ValueError, match="absolute http"):
        _record(tmp_path, url="ftp://example.org/report")
    with pytest.raises(ValueError, match="empty"):
        _record(tmp_path, text="  \n")


def test_record_refuses_files_outside_the_workspace(tmp_path):
    root = tmp_path / "workspace"
    root.mkdir()
    text_file = tmp_path / "outside.txt"
    text_file.write_text(TEXT, encoding="utf-8")
    with pytest.raises(ValueError, match="outside the workspace"):
        record_capture(
            url=URL, title=TITLE, text_file=text_file,
            output=root / "research" / "capture.json", workspace_root=root, client="claude_code",
        )


def test_cli_records_and_reports_errors(tmp_path, capsys):
    text_file = tmp_path / "research" / "source-captures" / "demo-2026-10-14" / "example.org-1.txt"
    text_file.parent.mkdir(parents=True)
    text_file.write_text(TEXT, encoding="utf-8", newline="\n")
    output = text_file.with_suffix(".json")
    args = ["record", "--url", URL, "--title", TITLE, "--text-file", str(text_file),
            "--output", str(output), "--workspace-root", str(tmp_path), "--client", "claude_code"]
    assert page_capture.main(args[:-2]) == 2  # --client is required
    capsys.readouterr()
    assert page_capture.main(args) == 0
    assert load_capture(output, tmp_path).url == URL
    bad = args[:2] + ["/relative"] + args[3:]
    assert page_capture.main(bad) == 2
    err = capsys.readouterr().err.strip().splitlines()
    assert len(err) == 1 and err[0].startswith("page_capture:")
