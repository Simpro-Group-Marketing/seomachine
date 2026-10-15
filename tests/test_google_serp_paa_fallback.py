"""Google SERP PAA fallback when AnswerSocrates is unavailable: recorder, scorer, proof view, release, record."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from data_sources.modules.paa_provenance import google_serp
from data_sources.modules.paa_provenance.evaluation import check_content
from data_sources.modules.production import google_paa
from data_sources.modules.production.proof_view import render_proof_view
from tests.test_production_record import _write, layout  # noqa: F401  (layout is a fixture)

QUERY = "job management software for tradies"
RUN_ID = "63751020-42d3-4466-a501-c488e9050686"
DATE = "2026-10-15"
OBSERVED = f"{DATE}T14:47:30Z"
COLLECTED = f"{DATE}T15:00:00Z"
PAGE = "https://www.google.com/search?q=job+management+software+for+tradies&hl=en&gl=au&pws=0"
ANSWERSOCRATES = "https://answersocrates.com/paa-extractor"
BLOCKER_TEXT = "You've Used All Your Searches"
QUESTIONS = ["What is the best job management software for tradies?", "Is Tradify free?"]
ARTICLE = "# Title\n\nBody text.\n"
FAQ_ARTICLE = "# Title\n\nBody.\n\n## FAQ\n\n### Is Tradify free?\n\nAnswer.\n"


def _args(tmp_path: Path, questions=QUESTIONS, **changes) -> list[str]:
    research = tmp_path / "research"
    research.mkdir(exist_ok=True)
    questions_file = research / "google-paa-questions.json"
    questions_file.write_text(json.dumps(questions), encoding="utf-8")
    blocker_file = research / "answersocrates-blocker.txt"
    blocker_file.write_text(BLOCKER_TEXT, encoding="utf-8")
    args = {
        "--query": QUERY, "--run-id": RUN_ID, "--google-country": "au", "--page-url": PAGE,
        "--collected-at": COLLECTED, "--questions-file": str(questions_file),
        "--answersocrates-state": "quota", "--answersocrates-text-file": str(blocker_file),
        "--answersocrates-url": ANSWERSOCRATES, "--answersocrates-observed-at": OBSERVED,
        "--output": str(research / "paa-evidence-x-2026-10-15.json"), "--workspace-root": str(tmp_path),
        "--client": "claude_code", **changes,
    }
    return [item for pair in args.items() for item in pair]


@pytest.fixture
def capture(tmp_path) -> Path:
    assert google_paa.main(_args(tmp_path)) == 0
    return tmp_path / "research" / "paa-evidence-x-2026-10-15.json"


def _bom(path: Path, questions=()) -> dict:
    return {"paa": {"artifact": {"path": str(path), "sha256": "x"}, "questions": [{"question": q} for q in questions]},
            "identity": {"brand": "Simpro"}}


def _check(content, path, questions=(), **overrides):
    expected = {"expected_query": QUERY, "expected_collection_date": DATE, "expected_run_id": RUN_ID}
    view = render_proof_view(_bom(path, questions), article=content, root=None)
    return check_content(content, proof_content=view, paa_artifact=str(path), **{**expected, **overrides})


def _rules(findings) -> list[str]:
    return [finding["rule_id"] for finding in findings]


def _edit(path: Path, change) -> None:
    payload = json.loads(path.read_text(encoding="utf-8"))
    change(payload)
    path.write_text(json.dumps(payload), encoding="utf-8")


# ---- recorder ---------------------------------------------------------------------


def test_recorder_writes_an_attested_capture_with_the_blocker(capture):
    payload = json.loads(capture.read_text(encoding="utf-8"))
    assert payload["schema"] == google_serp.GOOGLE_SERP_PAA_SCHEMA
    assert payload["collector"] == google_serp.GOOGLE_SERP_PAA_COLLECTOR
    assert payload["eligible_questions"] == QUESTIONS
    assert payload["collection_date"] == DATE and payload["run_receipt"] == {"run_id": RUN_ID}
    assert payload["answersocrates_blocker"] == {
        "state": "quota", "observed_text": BLOCKER_TEXT, "page_url": ANSWERSOCRATES, "observed_at": OBSERVED,
    }
    assert "temporary_test_path" not in payload and "execution_attestation" in payload
    assert payload["client"] == "claude_code"


def test_recorder_accepts_a_results_page_with_no_paa_box(tmp_path):
    assert google_paa.main(_args(tmp_path, questions=[])) == 0


@pytest.mark.parametrize("change", [
    {"--page-url": ANSWERSOCRATES},
    {"--collected-at": "2999-01-01T00:00:00Z"},
    {"--query": " "},
    {"--answersocrates-url": "https://example.com/"},
    {"--answersocrates-observed-at": "2026-10-14T23:00:00Z"},
    {"--answersocrates-observed-at": f"{DATE}T15:30:00Z"},
])
def test_recorder_refuses_bad_inputs(tmp_path, change):
    assert google_paa.main(_args(tmp_path, **change)) == 2
    assert not (tmp_path / "research" / "paa-evidence-x-2026-10-15.json").exists()


def test_recorder_refuses_codex_inside_claude_code(tmp_path, monkeypatch):
    monkeypatch.setenv("CLAUDECODE", "1")
    assert google_paa.main(_args(tmp_path, **{"--client": "codex"})) == 2


def test_recorder_refuses_an_unknown_blocker_state(tmp_path):
    assert google_paa.main(_args(tmp_path, **{"--answersocrates-state": "slow"})) == 2


def test_recorder_refuses_empty_blocker_text(tmp_path):
    args = _args(tmp_path)
    (tmp_path / "research" / "answersocrates-blocker.txt").write_text("  \n", encoding="utf-8")
    assert google_paa.main(args) == 2


def test_recorder_refuses_a_line_that_is_not_a_question(tmp_path):
    assert google_paa.main(_args(tmp_path, questions=["Tradify pricing"])) == 2


# ---- scorer ---------------------------------------------------------------------------


def test_proof_view_labels_the_google_source(capture):
    assert "- Source: google_serp_paa" in render_proof_view(_bom(capture), root=None)


def test_scorer_accepts_a_valid_capture_with_no_faq(capture, monkeypatch):
    monkeypatch.delenv("SEOMACHINE_TEMP_GOOGLE_SERP_PAA", raising=False)
    assert _check(ARTICLE, capture) == []


def test_scorer_accepts_an_faq_question_from_the_capture(capture):
    assert _check(FAQ_ARTICLE, capture, questions=["Is Tradify free?"]) == []


def test_scorer_refuses_an_faq_question_the_capture_lacks(capture):
    article = FAQ_ARTICLE.replace("Is Tradify free?", "Is Simpro free?")
    assert _check(article, capture, questions=["Is Simpro free?"]) != []


@pytest.mark.parametrize("overrides", [
    {"expected_query": "other query"}, {"expected_collection_date": "2026-10-16"}, {"expected_run_id": "other"},
])
def test_scorer_refuses_a_capture_for_another_query_date_or_run(capture, overrides):
    assert _rules(_check(ARTICLE, capture, **overrides)) == ["paa_google_serp_capture_invalid"]


def test_scorer_refuses_a_tampered_capture(capture):
    _edit(capture, lambda payload: payload["eligible_questions"].append("Invented question?"))
    assert _rules(_check(ARTICLE, capture)) == ["paa_google_serp_capture_invalid"]


def _resign(path: Path, change) -> None:
    from data_sources.modules.execution_attestation import attest_mapping

    payload = json.loads(path.read_text(encoding="utf-8"))
    payload.pop("execution_attestation")
    change(payload)
    signed = attest_mapping(payload, purpose=google_serp.GOOGLE_SERP_PAA_SCHEMA, workspace_root=path.parents[1])
    path.write_text(json.dumps(signed), encoding="utf-8")


def test_a_capture_recorded_before_the_client_field_still_validates(capture):
    _resign(capture, lambda payload: payload.pop("client"))
    assert _check(ARTICLE, capture) == []


def test_a_capture_with_an_unknown_client_is_refused(capture):
    _resign(capture, lambda payload: payload.update(client="cursor"))
    assert _rules(_check(ARTICLE, capture)) == ["paa_google_serp_capture_invalid"]


def test_validator_refuses_a_capture_without_a_blocker(capture):
    _edit(capture, lambda payload: payload.pop("answersocrates_blocker"))
    _questions, _blocker, error = google_serp.google_serp_questions(
        capture, None, expected_query=QUERY, expected_collection_date=DATE, expected_run_id=RUN_ID,
    )
    assert error


def test_validator_returns_questions_and_blocker(capture):
    questions, blocker, error = google_serp.google_serp_questions(
        capture, None, expected_query=QUERY, expected_collection_date=DATE, expected_run_id=RUN_ID,
    )
    assert (questions, blocker["state"], error) == (tuple(QUESTIONS), "quota", "")


def test_capture_detection(capture, tmp_path):
    assert google_serp.is_google_serp_capture(capture)
    other = tmp_path / "research" / "other.json"
    other.write_text(json.dumps({"schema": "simpro-answersocrates-artifact/v1"}), encoding="utf-8")
    assert not google_serp.is_google_serp_capture(other)
    assert not google_serp.is_google_serp_capture(tmp_path / "missing.json")


# ---- release and record ---------------------------------------------------------------


def test_release_record_names_the_fallback_and_its_blocker(capture, tmp_path):
    from data_sources.modules.production import release

    relative = capture.relative_to(tmp_path).as_posix()
    bom = {"paa": {"artifact": {"path": relative, "sha256": "x"}, "questions": []}}
    findings = release._paa_source_findings(tmp_path, bom)
    assert [(f.check, f.severity) for f in findings] == [(google_serp.RELEASE_CHECK, "warn")]
    assert "quota" in findings[0].message and "claude_code" in findings[0].message
    assert release._paa_source_findings(tmp_path, {"paa": {"artifact": None, "questions": []}}) == []


def test_a_google_paa_release_is_publishable(layout):  # noqa: F811
    from data_sources.modules.production import record
    from data_sources.modules.production.truth_text import Finding

    _write(layout, findings=[Finding(google_serp.RELEASE_CHECK, "warn", "Google SERP fallback", None)])
    assert record.verify_publishable(layout.article, layout.root)["passed"] is True
