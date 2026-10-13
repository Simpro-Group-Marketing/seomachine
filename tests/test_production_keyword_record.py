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
PRIMARY_BLOCK = "Field   Service Scheduling\n720\n32\n18.5\n0.12\n1,000,000\n\n"
SECONDARY_BLOCK = "dispatch capacity\n90\n24\n8.2\n0.04\n250,000\n\n"
SERP_BLOCK = "example.com\nhttps://example.com/field-service-scheduling\n"
FILLER = "filler " * 200


def _transcript(gap: str = "", extra: str = "") -> str:
    header = "Semrush phrase_these, database us\nKeyword Volume KD CPC Density Results\n"
    return header + PRIMARY_BLOCK + gap + SECONDARY_BLOCK + SERP_BLOCK + extra


TRANSCRIPT = _transcript()


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


@pytest.mark.parametrize(
    "value",
    [None, True, False, "n/a", "", "high", "720", [], "seven hundred twenty", -720,
     float("nan"), float("inf")],
)
def test_non_numeric_or_invalid_metric_values_raise(tmp_path, value):
    decision = _decision()
    decision["candidate_metrics"][0]["volume"] = value
    with pytest.raises(ValueError, match=r"field service scheduling.*volume"):
        _record(tmp_path, decision)


def test_extra_candidate_key_raises(tmp_path):
    decision = _decision()
    decision["candidate_metrics"][0]["traffic"] = 987654
    with pytest.raises(ValueError, match=r"field service scheduling.*traffic"):
        _record(tmp_path, decision)


def test_partial_keyword_does_not_match(tmp_path):
    decision = _decision()
    decision["candidate_metrics"][1]["keyword"] = "dispatch capac"
    with pytest.raises(ValueError, match="dispatch capac"):
        _record(tmp_path, decision)


def test_metric_only_in_a_distant_block_raises(tmp_path):
    decision = _decision()
    decision["candidate_metrics"][0]["keyword_difficulty"] = 24
    with pytest.raises(ValueError, match=r"field service scheduling.*keyword_difficulty"):
        _record(tmp_path, decision, _transcript(gap=FILLER))


def test_swapped_metrics_between_distant_blocks_raise(tmp_path):
    decision = _decision()
    first, second = decision["candidate_metrics"]
    for field in ("volume", "keyword_difficulty", "cpc", "competitive_density", "results"):
        first[field], second[field] = second[field], first[field]
    with pytest.raises(ValueError, match="field service scheduling"):
        _record(tmp_path, decision, _transcript(gap=FILLER))


def test_distant_blocks_with_correct_metrics_pass(tmp_path):
    assert _record(tmp_path, _decision(), _transcript(gap=FILLER))["decision"]


def test_abbreviated_volume_within_window_still_matches(tmp_path):
    decision = _decision()
    decision["candidate_metrics"][0]["volume"] = 1300
    transcript = _transcript(gap=FILLER).replace("720", "1.3K")
    assert _record(tmp_path, decision, transcript)["decision"]


def test_serp_url_absent_from_transcript_raises(tmp_path):
    decision = _decision()
    decision["serp_finalists"][0]["results"][0]["url"] = "https://other.example/page"
    with pytest.raises(ValueError, match="url"):
        _record(tmp_path, decision)


def test_serp_domain_absent_from_transcript_raises(tmp_path):
    decision = _decision()
    decision["serp_finalists"][0]["results"][0]["domain"] = "other.example"
    with pytest.raises(ValueError, match="domain"):
        _record(tmp_path, decision)


@pytest.mark.parametrize("section", ["question_candidates", "related_candidates"])
def test_nested_candidate_keyword_absent_from_transcript_raises(tmp_path, section):
    decision = _decision()
    decision[section] = [{"keyword": "invented keyword phrase", "volume": 40}]
    with pytest.raises(ValueError, match="invented keyword phrase"):
        _record(tmp_path, decision)


def test_nested_candidate_keyword_present_in_transcript_passes(tmp_path):
    decision = _decision()
    decision["question_candidates"] = [{"keyword": "how to schedule field work", "volume": 40}]
    transcript = _transcript(extra="how to schedule field work 40\nn")
    assert _record(tmp_path, decision, transcript)["decision"]


@pytest.mark.parametrize(
    "collision",
    [("--shortlist-output", "decision.json"), ("--output", "in.json"),
     ("--shortlist-output", "transcript.txt")],
)
def test_cli_exits_two_when_paths_collide(tmp_path, collision):
    args = _cli_inputs(tmp_path, _decision())
    flag, name = collision
    args[args.index(flag) + 1] = str(tmp_path / "research" / name if name == "decision.json" else tmp_path / name)
    before = (tmp_path / "in.json").read_bytes()
    assert keyword_record.main(args) == 2
    assert (tmp_path / "in.json").read_bytes() == before
    assert not (tmp_path / "research" / "decision.json").exists()
