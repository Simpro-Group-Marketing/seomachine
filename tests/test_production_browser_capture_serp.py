"""`browser_capture serp` turns Google AU organic results read from the Chrome DOM into a raw SERP capture."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import pytest

from data_sources.modules.editorial_plan.contracts import SERP_RAW_CAPTURE_ATTESTATION_PURPOSE
from data_sources.modules.editorial_plan.serp_capture import build_serp_evidence
from data_sources.modules.editorial_plan.serp_validation import check_serp_evidence_payload
from data_sources.modules.execution_attestation import attest_mapping
from data_sources.modules.editorial_plan.serp_raw import load_normalized_serp_raw_capture
from data_sources.modules.production import browser_capture

QUERY = "job management software for tradies"
RUN_ID = "3f2b8c1e-5d47-4a9b-8e21-7c0d9a6b4f13"
ROWS = [
    {"position": 1, "url": "https://www.tradifyhq.com/au", "title": "Tradify | Job Management Software for Tradies"},
    {"position": 2, "url": "https://www.fergus.com/au/", "title": "Fergus - Job Management Software For Trades"},
    {"position": 3, "url": "https://www.servicem8.com/au", "title": "ServiceM8 | Job management app for trades"},
    {"position": 4, "url": "https://www.simprogroup.com/au/", "title": "Simpro | Field Service Management Software"},
    {"position": 5, "url": "https://aroflo.com/", "title": "AroFlo | Job Management Software"},
    {"position": 6, "url": "https://www.reddit.com/r/AusTradies/comments/abc/job_app/", "title": "Best job app for a sole trader?"},
    {"position": 7, "url": "https://www.capterra.com.au/directory/30010/field-service/software", "title": "Best Field Service Software 2026"},
    {"position": 8, "url": "https://www.getapp.com.au/directory/1020/job-management/software", "title": "Job Management Software"},
    {"position": 9, "url": "https://www.youtube.com/watch?v=abc123", "title": "Which job management app should tradies use?"},
    {"position": 10, "url": "https://tradiepad.com.au/", "title": "Tradiepad - Job Management for Tradies"},
    {"position": 11, "url": "https://www.payaus.com.au/blog/apps", "title": "10 Best Apps for Tradies in 2026"},
]
FEATURES = ["People also ask", "Sponsored results", "Videos"]


@pytest.fixture(autouse=True)
def _attestation_key(monkeypatch):
    monkeypatch.setenv("SEOMACHINE_ARTIFACT_ATTESTATION_KEY", "k" * 48)


def _now_stamp() -> str:
    moment = datetime.now(timezone.utc).replace(microsecond=0) - timedelta(seconds=5)
    return moment.strftime("%Y-%m-%dT%H:%M:%SZ")


def _workspace(tmp_path: Path, results: object = None) -> Path:
    (tmp_path / "research").mkdir()
    payload = {"organic_results": ROWS, "features": FEATURES} if results is None else results
    (tmp_path / "research" / "serp-results.json").write_text(json.dumps(payload), encoding="utf-8")
    return tmp_path


def _argv(root: Path, **overrides: str) -> list[str]:
    values = {
        "--query": QUERY,
        "--run-id": RUN_ID,
        "--google-country": "au",
        "--results-file": "research/serp-results.json",
        "--collected-at": _now_stamp(),
        "--output": "research/serp-raw-chrome.json",
        "--workspace-root": str(root),
        "--client": "claude_code",
    }
    values.update(overrides)
    argv = ["serp"]
    for flag, value in values.items():
        argv += [flag, value]
    return argv


def _raw(root: Path) -> Path:
    return root / "research" / "serp-raw-chrome.json"


def test_recorded_capture_passes_raw_validation_and_builds_evidence(tmp_path, capsys):
    root = _workspace(tmp_path)

    assert browser_capture.main(_argv(root)) == 0

    normalized = load_normalized_serp_raw_capture(_raw(root), workspace_root=root)
    assert [row["url"] for row in normalized["organic_results"]] == [row["url"] for row in ROWS]
    assert normalized["features"] == FEATURES
    evidence = build_serp_evidence(
        raw_capture_path=_raw(root), workspace_root=root, must_have_sections=[], competitor_gaps=[]
    )
    assert evidence["status"] == "verified"
    assert evidence["collector"] == {"name": "research_serp_analysis:chrome_connector", "version": "1.0.0"}
    assert evidence["client"] == "claude_code"
    assert json.loads(_raw(root).read_text(encoding="utf-8"))["client"] == "claude_code"
    assert evidence["run_id"] == RUN_ID
    assert [(row["position"], row["url"], row["title"]) for row in evidence["results"]] == [
        (row["position"], row["url"], row["title"]) for row in ROWS[:10]
    ]


def _resigned(root: Path, change) -> None:
    """Edit the raw capture and sign it again, as a capture made under another contract would be."""
    capture = json.loads(_raw(root).read_text(encoding="utf-8"))
    capture.pop("execution_attestation")
    change(capture)
    signed = attest_mapping(capture, purpose=SERP_RAW_CAPTURE_ATTESTATION_PURPOSE, workspace_root=root)
    _raw(root).write_text(json.dumps(signed), encoding="utf-8")


def _evidence(root: Path) -> dict:
    return build_serp_evidence(
        raw_capture_path=_raw(root), workspace_root=root, must_have_sections=[], competitor_gaps=[]
    )


def test_a_capture_recorded_before_the_client_field_still_builds_evidence(tmp_path):
    root = _workspace(tmp_path)
    assert browser_capture.main(_argv(root)) == 0
    _resigned(root, lambda capture: capture.pop("client"))
    assert "client" not in _evidence(root)


def test_a_capture_with_an_unknown_client_is_refused(tmp_path):
    root = _workspace(tmp_path)
    assert browser_capture.main(_argv(root)) == 0
    _resigned(root, lambda capture: capture.update(client="cursor"))
    with pytest.raises(ValueError, match="shape"):
        load_normalized_serp_raw_capture(_raw(root), workspace_root=root)


def test_evidence_that_disagrees_with_its_capture_on_the_client_is_refused(tmp_path):
    root = _workspace(tmp_path)
    assert browser_capture.main(_argv(root)) == 0
    evidence = _evidence(root)
    evidence["client"] = "codex"
    rules = {row["rule_id"] for row in check_serp_evidence_payload(
        evidence, expected_query=QUERY, assembly_date=None, expected_run_id=RUN_ID, workspace_root=root,
    )}
    assert "serp_raw_capture_metadata_mismatch" in rules


def test_the_client_flag_is_required(tmp_path):
    root = _workspace(tmp_path)
    assert browser_capture.main(_argv(root)[:-2]) == 2
    assert not _raw(root).exists()


def test_request_binds_query_country_language_and_no_personalization(tmp_path):
    root = _workspace(tmp_path)

    assert browser_capture.main(_argv(root)) == 0

    capture = json.loads(_raw(root).read_text(encoding="utf-8"))
    assert capture["schema"] == "simpro-serp-raw-capture/v1"
    assert capture["execution_attestation"]["purpose"] == "simpro-serp-raw-capture/v1"
    assert capture["request"]["locale"] == {"hl": "en", "gl": "au", "pws": "0"}
    url = urlparse(capture["request"]["url"])
    assert (url.scheme, url.hostname, url.path) == ("https", "www.google.com", "/search")
    assert parse_qs(url.query) == {"q": [QUERY], "hl": ["en"], "gl": ["au"], "pws": ["0"]}


def test_rows_are_ordered_by_position_and_a_bare_list_needs_no_features(tmp_path):
    root = _workspace(tmp_path, list(reversed(ROWS[:3])))

    assert browser_capture.main(_argv(root)) == 0

    capture = json.loads(_raw(root).read_text(encoding="utf-8"))
    assert [row["position"] for row in capture["raw_response"]["organic_results"]] == [1, 2, 3]
    assert capture["raw_response"]["features"] == []


def test_evidence_output_writes_the_verified_evidence(tmp_path):
    root = _workspace(tmp_path)

    argv = _argv(root, **{"--evidence-output": "research/serp-evidence.json"})
    assert browser_capture.main(argv) == 0

    evidence = json.loads((root / "research" / "serp-evidence.json").read_text(encoding="utf-8"))
    assert evidence["schema"] == "simpro-serp-evidence/v1"
    assert evidence["raw_capture"]["path"] == "research/serp-raw-chrome.json"
    assert [row["url"] for row in evidence["results"]] == [row["url"] for row in ROWS[:10]]


def test_tampered_capture_fails_attestation(tmp_path):
    root = _workspace(tmp_path)
    assert browser_capture.main(_argv(root)) == 0
    capture = json.loads(_raw(root).read_text(encoding="utf-8"))
    capture["raw_response"]["organic_results"][0]["url"] = "https://www.simprogroup.com/au/"
    _raw(root).write_text(json.dumps(capture), encoding="utf-8")

    with pytest.raises(ValueError, match="attestation is invalid"):
        load_normalized_serp_raw_capture(_raw(root), workspace_root=root)


def _refused(root: Path, capsys, **overrides: str) -> str:
    assert browser_capture.main(_argv(root, **overrides)) == 2
    assert not _raw(root).exists()
    error = capsys.readouterr().err.strip()
    assert error.startswith("browser_capture:") and "\n" not in error
    return error


def _row(position: object, url: str = "https://example.com.au/", title: str = "Example") -> dict:
    return {"position": position, "url": url, "title": title}


@pytest.mark.parametrize("results", [[], {"organic_results": [], "features": []}])
def test_refuses_empty_results(tmp_path, capsys, results):
    assert "empty" in _refused(_workspace(tmp_path, results), capsys)


@pytest.mark.parametrize(
    "url", ["/relative/path", "ftp://example.com/file", "www.example.com", "https://", "javascript:alert(1)"]
)
def test_refuses_result_urls_that_are_not_absolute_http(tmp_path, capsys, url):
    assert "url" in _refused(_workspace(tmp_path, [_row(1, url=url)]), capsys)


@pytest.mark.parametrize(
    "positions", [[1, 3], [1, 1], [0, 1], [2, 3], [1, True], [1, "2"]]
)
def test_refuses_positions_that_are_not_one_to_n(tmp_path, capsys, positions):
    rows = [_row(position, url=f"https://example{index}.com.au/") for index, position in enumerate(positions)]
    assert "position" in _refused(_workspace(tmp_path, rows), capsys)


@pytest.mark.parametrize(
    "row",
    [
        {"position": 1, "url": "https://example.com.au/", "title": "  "},
        {"position": 1, "url": "https://example.com.au/"},
        {"position": 1, "url": "https://example.com.au/", "title": "x", "rank": 1},
    ],
)
def test_refuses_malformed_rows(tmp_path, capsys, row):
    assert "result" in _refused(_workspace(tmp_path, [row]), capsys)


def test_refuses_malformed_features(tmp_path, capsys):
    results = {"organic_results": [_row(1)], "features": ["People also ask", ""]}
    assert "features" in _refused(_workspace(tmp_path, results), capsys)


def test_refuses_a_run_id_that_is_not_a_uuid(tmp_path, capsys):
    assert "run id" in _refused(_workspace(tmp_path), capsys, **{"--run-id": "serp-run-1"}).casefold()


def test_refuses_results_file_outside_the_workspace(tmp_path, capsys):
    root = tmp_path / "ws"
    root.mkdir()
    _workspace(root)
    outside = tmp_path / "results.json"
    outside.write_text(json.dumps([_row(1)]), encoding="utf-8")
    assert "outside the workspace" in _refused(root, capsys, **{"--results-file": str(outside)})


def test_refuses_evidence_output_outside_the_workspace(tmp_path, capsys):
    root = tmp_path / "ws"
    root.mkdir()
    _workspace(root)
    assert "outside the workspace" in _refused(root, capsys, **{"--evidence-output": "../evidence.json"})


@pytest.mark.parametrize("stamp", ["2026-10-15T10:00:00+00:00", "2026-10-15", "2999-01-01T00:00:00Z"])
def test_refuses_invalid_collection_times(tmp_path, capsys, stamp):
    assert "collected" in _refused(_workspace(tmp_path), capsys, **{"--collected-at": stamp})


def test_refuses_an_unapproved_country(tmp_path, capsys):
    assert browser_capture.main(_argv(_workspace(tmp_path), **{"--google-country": "de"})) == 2
    assert not _raw(tmp_path).exists()
