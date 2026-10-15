"""`browser_capture paa` turns verbatim AnswerSocrates page text into a recordable Chrome capture."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from data_sources.modules.execution_attestation import attest_mapping
from data_sources.modules.paa_provenance.cli import _record_main
from data_sources.modules.production import browser_capture

QUERY = "job management software for tradies"
RUN_ID = "3f2b8c1e-5d47-4a9b-8e21-7c0d9a6b4f13"
PAGE_URL = "https://answersocrates.com/"
TITLE = "Answer Socrates: Free Question Keyword Research Tool Generator"
QUESTIONS = [
    "What is the best job management software for tradies?",
    "How much does tradie software cost?",
    "Is there a free job management app?",
    "What app do tradies use for quoting?",
]
# Page text as Chrome returns it: one block element per line, nav links included.
PAGE_TEXT = "\n".join(
    [
        "Answer Socrates",
        "Log in",
        "Sign up",
        QUERY,
        "212 questions generated",
        "Country: Australia",
        "Language: English",
        "People Also Ask",
        *QUESTIONS,
        "Want the nested follow-ups Google hides? Run the PAA Extractor — uses 1 credit.",
        "Visible question suggestions",
        "Can Tradify Do Invoicing",
        "What Is The Best App For Tradies?",
        "Frequently Asked Questions",
        "What is Answer Socrates?",
    ]
) + "\n"


@pytest.fixture(autouse=True)
def _attestation_key(monkeypatch):
    monkeypatch.setenv("SEOMACHINE_ARTIFACT_ATTESTATION_KEY", "k" * 48)


def _stamp(value: datetime) -> str:
    return value.strftime("%Y-%m-%dT%H:%M:%SZ")


def _times() -> tuple[str, str, str]:
    completed = datetime.now(timezone.utc).replace(microsecond=0) - timedelta(seconds=5)
    started = completed - timedelta(seconds=40)
    return _stamp(started), _stamp(completed), completed.date().isoformat()


def _workspace(tmp_path: Path, text: str = PAGE_TEXT) -> Path:
    (tmp_path / "research").mkdir()
    (tmp_path / "research" / "answersocrates-page.txt").write_text(text, encoding="utf-8", newline="\n")
    return tmp_path


def _argv(root: Path, **overrides: str) -> list[str]:
    started, completed, _ = _times()
    values = {
        "--query": QUERY,
        "--run-id": RUN_ID,
        "--page-url": PAGE_URL,
        "--page-title": TITLE,
        "--text-file": "research/answersocrates-page.txt",
        "--started-at": started,
        "--completed-at": completed,
        "--output": "research/answersocrates-chrome-raw.json",
        "--workspace-root": str(root),
        "--client": "claude_code",
    }
    values.update(overrides)
    argv = ["paa"]
    for flag, value in values.items():
        argv += [flag, value]
    return argv


def _record(root: Path, collection_date: str | None = None) -> int:
    collection_date = collection_date or _times()[2]
    return _record_main(
        [
            "--query", QUERY,
            "--collection-date", collection_date,
            "--run-id", RUN_ID,
            "--raw-capture-input", str(root / "research" / "answersocrates-chrome-raw.json"),
            "--workspace-root", str(root),
            "--output", str(root / "research" / "paa-evidence.json"),
        ]
    )


def test_recorded_capture_passes_the_paa_record_guard(tmp_path, capsys):
    root = _workspace(tmp_path)

    assert browser_capture.main(_argv(root)) == 0
    capsys.readouterr()
    assert _record(root) == 0

    artifact = json.loads((root / "research" / "paa-evidence.json").read_text(encoding="utf-8"))
    assert artifact["status"] == "collected"
    assert artifact["query"] == QUERY
    assert artifact["eligible_questions"] == QUESTIONS
    assert artifact["run_receipt"]["tool"] == {"name": "answersocrates_chrome_connector", "version": "1.0.0"}


def test_capture_keeps_the_page_text_verbatim_and_derives_sections(tmp_path):
    root = _workspace(tmp_path)

    assert browser_capture.main(_argv(root)) == 0

    capture = json.loads((root / "research" / "answersocrates-chrome-raw.json").read_text(encoding="utf-8"))
    assert capture["schema"] == "simpro-answersocrates-chrome-connector-capture/v1"
    assert capture["collector"] == {"name": "answersocrates_chrome_connector", "version": "1.0.0"}
    assert capture["client"] == "claude_code"
    assert capture["execution_attestation"]["purpose"] == capture["schema"]
    assert capture["raw_response"]["stderr"] == ""
    assert capture["raw_response"]["returncode"] == 0
    browser = json.loads(capture["raw_response"]["stdout"])
    assert browser["body_text"] == PAGE_TEXT
    assert browser["page_url"] == PAGE_URL
    assert browser["page_title"] == TITLE
    assert browser["sections"] == [{"heading": "People Also Ask", "items": QUESTIONS}]
    assert browser["blocker_observations"] == []


def test_blank_lines_between_questions_are_skipped(tmp_path):
    spaced = PAGE_TEXT.replace("\n", "\n\n")
    root = _workspace(tmp_path, spaced)

    assert browser_capture.main(_argv(root)) == 0

    capture = json.loads((root / "research" / "answersocrates-chrome-raw.json").read_text(encoding="utf-8"))
    assert json.loads(capture["raw_response"]["stdout"])["sections"][0]["items"] == QUESTIONS


def test_tampered_capture_fails_attestation(tmp_path, capsys):
    root = _workspace(tmp_path)
    assert browser_capture.main(_argv(root)) == 0
    path = root / "research" / "answersocrates-chrome-raw.json"
    capture = json.loads(path.read_text(encoding="utf-8"))
    browser = json.loads(capture["raw_response"]["stdout"])
    browser["sections"][0]["items"].append("Is Simpro the best tradie app?")
    capture["raw_response"]["stdout"] = json.dumps(browser)
    path.write_text(json.dumps(capture), encoding="utf-8")

    with pytest.raises(ValueError, match="attestation is invalid"):
        _record(root)


def _resigned(root: Path, change) -> None:
    """Edit the recorded capture and sign it again, as a capture made under another contract would be."""
    path = root / "research" / "answersocrates-chrome-raw.json"
    capture = json.loads(path.read_text(encoding="utf-8"))
    capture.pop("execution_attestation")
    change(capture)
    path.write_text(json.dumps(attest_mapping(capture, purpose=capture["schema"], workspace_root=root)), encoding="utf-8")


def test_a_capture_recorded_before_the_client_field_still_records(tmp_path, capsys):
    root = _workspace(tmp_path)
    assert browser_capture.main(_argv(root)) == 0
    _resigned(root, lambda capture: (capture.pop("client"), capture.update(
        started_at="2026-10-14T13:59:00Z", completed_at="2026-10-14T14:00:00Z")))
    capsys.readouterr()
    assert _record(root, collection_date="2026-10-14") == 0


def test_a_capture_made_after_the_field_shipped_must_name_its_client(tmp_path, capsys):
    root = _workspace(tmp_path)
    assert browser_capture.main(_argv(root)) == 0
    _resigned(root, lambda capture: capture.pop("client"))
    with pytest.raises(ValueError, match="shape"):
        _record(root)


def test_a_capture_with_an_unknown_client_is_refused(tmp_path, capsys):
    root = _workspace(tmp_path)
    assert browser_capture.main(_argv(root)) == 0
    _resigned(root, lambda capture: capture.update(client="cursor"))
    with pytest.raises(ValueError, match="shape"):
        _record(root)


def test_the_client_flag_is_required(tmp_path, capsys):
    root = _workspace(tmp_path)
    argv = _argv(root)
    assert browser_capture.main(argv[:-2]) == 2
    assert not (root / "research" / "answersocrates-chrome-raw.json").exists()


def test_codex_is_refused_inside_claude_code(tmp_path, capsys, monkeypatch):
    monkeypatch.setenv("CLAUDECODE", "1")
    _refused(_workspace(tmp_path), capsys, **{"--client": "codex"})


def _refused(root: Path, capsys, **overrides: str) -> str:
    assert browser_capture.main(_argv(root, **overrides)) == 2
    assert not (root / "research" / "answersocrates-chrome-raw.json").exists()
    error = capsys.readouterr().err.strip()
    assert error.startswith("browser_capture:") and "\n" not in error
    return error


def test_refuses_empty_text(tmp_path, capsys):
    assert "empty" in _refused(_workspace(tmp_path, " \n\n"), capsys)


def test_refuses_text_without_a_people_also_ask_heading_line(tmp_path, capsys):
    collapsed = " ".join(PAGE_TEXT.split())
    assert "People Also Ask" in _refused(_workspace(tmp_path, collapsed), capsys)


def test_refuses_a_heading_with_no_questions_under_it(tmp_path, capsys):
    text = f"{QUERY}\nPeople Also Ask\nVisible question suggestions\nHow To Quote A Job\n"
    assert "question" in _refused(_workspace(tmp_path, text), capsys)


@pytest.mark.parametrize(
    "url",
    ["http://answersocrates.com/", "https://answersocrates.example.com/", "https://answersocrates.com/?q=x"],
)
def test_refuses_a_page_url_that_is_not_answersocrates(tmp_path, capsys, url):
    assert "page url" in _refused(_workspace(tmp_path), capsys, **{"--page-url": url}).casefold()


@pytest.mark.parametrize("run_id", ["run-1", "", "3F2B8C1E-5D47-4A9B-8E21-7C0D9A6B4F13"])
def test_refuses_a_run_id_that_is_not_a_uuid(tmp_path, capsys, run_id):
    assert "run id" in _refused(_workspace(tmp_path), capsys, **{"--run-id": run_id}).casefold()


def test_refuses_text_file_outside_the_workspace(tmp_path, capsys):
    root = tmp_path / "ws"
    root.mkdir()
    _workspace(root)
    outside = tmp_path / "outside.txt"
    outside.write_text(PAGE_TEXT, encoding="utf-8")
    assert "outside the workspace" in _refused(root, capsys, **{"--text-file": str(outside)})


def test_refuses_output_outside_the_workspace(tmp_path, capsys):
    root = tmp_path / "ws"
    root.mkdir()
    _workspace(root)
    assert "outside the workspace" in _refused(root, capsys, **{"--output": "../raw.json"})
    assert not (tmp_path / "raw.json").exists()


@pytest.mark.parametrize(
    ("started", "completed"),
    [
        ("2026-10-15T10:00:00+00:00", "2026-10-15T10:01:00Z"),
        ("2026-10-15T10:00:00Z", "2026-10-15 10:01:00Z"),
        ("2026-10-15T10:01:00Z", "2026-10-15T10:00:00Z"),
        ("2026-10-15T10:01:00Z", "2026-10-15T10:01:00Z"),
        ("2026-10-15T10:00:00Z", "2999-01-01T00:00:00Z"),
    ],
)
def test_refuses_invalid_capture_times(tmp_path, capsys, started, completed):
    error = _refused(_workspace(tmp_path), capsys, **{"--started-at": started, "--completed-at": completed})
    assert "time" in error or "completed" in error or "future" in error


def test_refuses_page_text_that_does_not_show_the_query(tmp_path, capsys):
    error = _refused(_workspace(tmp_path), capsys, **{"--query": "field service software"})
    assert "query" in error


def test_refuses_an_untrimmed_query(tmp_path, capsys):
    assert "query" in _refused(_workspace(tmp_path), capsys, **{"--query": f" {QUERY}"})
