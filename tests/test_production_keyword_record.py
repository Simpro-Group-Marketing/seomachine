from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

import pytest

from data_sources.modules import semrush_keyword_decision_guard as guard
from data_sources.modules.production import keyword_record
from data_sources.modules.production.keyword_record import record_keyword_decision

PRIMARY = "field service scheduling"
SECONDARY = "dispatch capacity"
TRANSCRIPT = (
    "Semrush phrase_these, database us\n"
    "Keyword | Volume | KD | CPC | Density | Results\n"
    "Field   Service Scheduling | 720 | 32 | 18.5 | 0.12 | 1,000,000\n"
    "dispatch capacity | 90 | 24 | 8.2 | 0.04 | 250,000\n"
)


@pytest.fixture(autouse=True)
def _attestation_key(monkeypatch):
    monkeypatch.setenv("SEOMACHINE_ARTIFACT_ATTESTATION_KEY", "k" * 48)


def _report(name: str, parameters: dict | None = None) -> dict:
    return {"report": name, "parameters": parameters or {}, "status": "completed"}


def _decision() -> dict:
    return {
        "brand": "Simpro",
        "market": "US",
        "database": "us",
        "collection_date": "2026-10-13",
        "source_boundary": guard.SOURCE_BOUNDARY,
        "seed_terms": [PRIMARY, SECONDARY],
        "connector_reports": [
            _report("_keyword_research"),
            _report("_get_report_schema", {"report": "phrase_these"}),
            _report("phrase_these", {"phrase": f"{PRIMARY};{SECONDARY}", "database": "us"}),
            _report("phrase_related", {"phrase": PRIMARY, "database": "us"}),
            _report("phrase_questions", {"phrase": PRIMARY, "database": "us"}),
            _report("phrase_organic", {"phrase": PRIMARY, "database": "us"}),
            _report("phrase_this", {"phrase": PRIMARY, "database": "us"}),
        ],
        "candidate_metrics": [
            {
                "keyword": PRIMARY,
                "volume": 720,
                "keyword_difficulty": 32,
                "cpc": 18.5,
                "competitive_density": 0.12,
                "results": 1000000,
            },
            {
                "keyword": SECONDARY,
                "volume": 90,
                "keyword_difficulty": 24,
                "cpc": 8.2,
                "competitive_density": 0.04,
                "results": 250000,
            },
        ],
        "serp_finalists": [
            {
                "keyword": PRIMARY,
                "database": "us",
                "results": [
                    {
                        "position": 1,
                        "position_type": "organic",
                        "domain": "example.com",
                        "url": "https://example.com/field-service-scheduling",
                        "triggered_serp_features": [],
                    }
                ],
            }
        ],
        "question_candidates": [],
        "related_candidates": [],
        "selected_primary_keyword": PRIMARY,
        "selected_secondary_keywords": [SECONDARY],
        "rejected_keywords": [
            {"keyword": "employee scheduling software", "reason": "Different buyer lane."}
        ],
        "selection_rationale": "Intent fit and SERP feasibility support the target.",
        "decision_rule": "Highest volume with keyword difficulty under 40.",
    }


def _record(tmp_path: Path, decision: dict, transcript: str = TRANSCRIPT) -> dict:
    return record_keyword_decision(
        decision,
        transcript,
        workspace_root=tmp_path,
        transcript_path=tmp_path / "research" / "semrush-transcript.txt",
    )


def test_volume_absent_from_transcript_raises_naming_keyword_and_field(tmp_path):
    decision = _decision()
    decision["candidate_metrics"][0]["volume"] = 721
    with pytest.raises(ValueError, match=r"field service scheduling.*volume"):
        _record(tmp_path, decision)


def test_keyword_absent_from_transcript_raises(tmp_path):
    decision = _decision()
    decision["candidate_metrics"][1]["keyword"] = "route planning software"
    with pytest.raises(ValueError, match="route planning software"):
        _record(tmp_path, decision)


def test_abbreviated_transcript_volume_satisfies_the_number(tmp_path):
    decision = _decision()
    decision["candidate_metrics"][0]["volume"] = 1300
    transcript = TRANSCRIPT.replace("720", "1.3K")
    result = _record(tmp_path, decision, transcript)
    assert result["decision"]["candidate_metrics"][0]["volume"] == 1300


def test_supported_decision_passes_the_guard_with_no_errors(tmp_path):
    result = _record(tmp_path, _decision())["decision"]
    findings = guard.check_decision(result, assembly_date="2026-10-13")
    assert [f for f in findings if f.get("severity") == "error"] == []
    assert "decision_rule" not in result


def test_shortlist_binds_transcript_and_decision_hashes(tmp_path):
    result = _record(tmp_path, _decision())
    shortlist = result["shortlist"]
    assert shortlist["schema"] == "simpro-keyword-shortlist/v1"
    assert shortlist["transcript"] == {
        "path": "research/semrush-transcript.txt",
        "sha256": hashlib.sha256(TRANSCRIPT.encode("utf-8")).hexdigest(),
    }
    assert shortlist["decision_sha256"] == keyword_record.canonical_json_sha256(result["decision"])
    assert shortlist["primary"] == PRIMARY
    assert shortlist["secondary"] == [SECONDARY]
    assert shortlist["candidates"] == result["decision"]["candidate_metrics"]
    assert shortlist["decision_rule"] == "Highest volume with keyword difficulty under 40."


def test_unknown_input_key_raises(tmp_path):
    decision = _decision()
    decision["workspace_root"] = str(tmp_path)
    with pytest.raises(ValueError, match="workspace_root"):
        _record(tmp_path, decision)


def test_missing_decision_rule_raises(tmp_path):
    decision = _decision()
    decision["decision_rule"] = "  "
    with pytest.raises(ValueError, match="decision_rule"):
        _record(tmp_path, decision)


def test_input_mapping_is_not_mutated(tmp_path):
    decision = _decision()
    before = copy.deepcopy(decision)
    _record(tmp_path, decision)
    assert decision == before


def _cli_inputs(tmp_path: Path, decision: dict, transcript: str = TRANSCRIPT) -> list[str]:
    (tmp_path / "in.json").write_text(json.dumps(decision), encoding="utf-8")
    (tmp_path / "transcript.txt").write_bytes(transcript.encode("utf-8"))
    return [
        "--decision", str(tmp_path / "in.json"),
        "--transcript", str(tmp_path / "transcript.txt"),
        "--output", str(tmp_path / "research" / "decision.json"),
        "--shortlist-output", str(tmp_path / "research" / "shortlist.json"),
        "--workspace-root", str(tmp_path),
    ]


def test_cli_writes_both_files_and_exits_zero(tmp_path):
    assert keyword_record.main(_cli_inputs(tmp_path, _decision())) == 0
    decision_path = tmp_path / "research" / "decision.json"
    shortlist = json.loads((tmp_path / "research" / "shortlist.json").read_text(encoding="utf-8"))
    assert shortlist["transcript"]["path"] == "transcript.txt"
    assert shortlist["decision_sha256"] == hashlib.sha256(decision_path.read_bytes()).hexdigest()


def test_cli_exits_one_on_failed_honesty_check(tmp_path, capsys):
    decision = _decision()
    decision["candidate_metrics"][0]["cpc"] = 99.9
    assert keyword_record.main(_cli_inputs(tmp_path, decision)) == 1
    assert "cpc" in capsys.readouterr().err
    assert not (tmp_path / "research" / "decision.json").exists()


def test_cli_exits_two_on_missing_input_file(tmp_path):
    args = _cli_inputs(tmp_path, _decision())
    (tmp_path / "transcript.txt").unlink()
    assert keyword_record.main(args) == 2


def test_cli_exits_two_on_bad_arguments(tmp_path):
    assert keyword_record.main(["--decision", str(tmp_path / "in.json")]) == 2
