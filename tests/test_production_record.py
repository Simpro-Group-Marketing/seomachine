"""Tests for the production release record and the publisher check."""

from __future__ import annotations

import hashlib
import json
import re

import pytest
from data_sources.modules.production import record
from data_sources.modules.production.layout import Layout, load_or_create_run_id
from data_sources.modules.production.scoring import score_gates
from data_sources.modules.production.truth_text import Finding
from tests.production_bom_support import ARTICLE, write_json
from tests.production_scoring_support import scorer_result

RUN_ID = "0f1e2d3c-4b5a-4987-8a6b-5c4d3e2f1a0b"
SPEC_PATH = "research/production-bom-spec-field-service-software-2026-10-13.json"
EVIDENCE_PATH = "research/customer-proof-selector-evidence-field-service-software.json"
PAA_PATH = "research/paa-evidence-field-service-software-2026-10-13.json"


def _binding(root, relative: str) -> dict:
    return {"path": relative, "sha256": hashlib.sha256((root / relative).read_bytes()).hexdigest()}


def _bom(root) -> dict:
    return {
        "schema": "simpro-production-bom/v1",
        "identity": {"run_id": RUN_ID, "spec": _binding(root, SPEC_PATH)},
        "paa": {"artifact": _binding(root, PAA_PATH), "questions": []},
        "customer_proof": {"evidence": _binding(root, EVIDENCE_PATH), "roles": []},
        "context": {"status": "not_applicable", "reason": "x"},
    }


@pytest.fixture
def layout(tmp_path):
    value = Layout.for_article(ARTICLE, tmp_path)
    value.article.parent.mkdir(parents=True, exist_ok=True)
    value.article.write_text("# Article\n", encoding="utf-8", newline="\n")
    for relative in (SPEC_PATH, EVIDENCE_PATH, PAA_PATH):
        write_json(tmp_path / relative, {"file": relative})
    write_json(value.bom, _bom(tmp_path))
    load_or_create_run_id(value, run_id=RUN_ID)
    return value


def _sha(path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write(layout, *, findings=(), scores=None, article_sha=None, bom_sha=None, workers=2):
    return record.write_record(
        layout, RUN_ID,
        article_sha256=article_sha or _sha(layout.article),
        bom_sha256=bom_sha or _sha(layout.bom),
        findings=list(findings),
        scores=score_gates(scorer_result()) if scores is None else scores,
        bom=_bom(layout.root),
        workers=workers,
    )


# ---- record schema and fields ----------------------------------------------------


def test_record_schema_and_fields(layout):
    findings = [Finding("lint", "warn", "modal_verb: x", 4), Finding("fact_quote", "warn", "y", None)]
    path = _write(layout, findings=findings, workers=3)
    assert path == layout.root / "research" / "releases" / f"field-service-software-2026-10-13-{RUN_ID[:8]}-1" / (
        "release-record.json")
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert record.RECORD_SCHEMA == "simpro-release-record/v1"
    assert set(payload) == {
        "schema", "run_id", "created_at", "article", "bom", "spec", "evidence", "findings",
        "blocks", "warns", "scores", "passed", "workers",
    }
    assert payload["schema"] == record.RECORD_SCHEMA and payload["run_id"] == RUN_ID
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", payload["created_at"])
    assert payload["article"] == {"path": ARTICLE, "sha256": _sha(layout.article)}
    assert payload["bom"] == {"path": "research/production-bom-field-service-software-2026-10-13.json",
                              "sha256": _sha(layout.bom)}
    assert payload["spec"] == _binding(layout.root, SPEC_PATH)
    assert payload["evidence"] == {"customer_proof.evidence": _binding(layout.root, EVIDENCE_PATH),
                                   "paa.artifact": _binding(layout.root, PAA_PATH)}
    assert payload["findings"] == [
        {"check": "lint", "severity": "warn", "message": "modal_verb: x", "line": 4},
        {"check": "fact_quote", "severity": "warn", "message": "y", "line": None},
    ]
    assert (payload["blocks"], payload["warns"]) == (0, 2)
    assert payload["scores"] == score_gates(scorer_result())
    assert payload["scores"]["gates"]["seo_quality"]["threshold"] == 90
    assert payload["passed"] is True and payload["workers"] == 3


def test_block_finding_fails_the_record(layout):
    payload = json.loads(_write(layout, findings=[Finding("fact_quote", "block", "gone", 9)]).read_text("utf-8"))
    assert payload["blocks"] == 1 and payload["passed"] is False


def test_failed_scores_fail_the_record(layout):
    payload = json.loads(_write(layout, scores=score_gates(scorer_result(aeo=80))).read_text("utf-8"))
    assert payload["blocks"] == 0 and payload["passed"] is False


def test_each_record_gets_the_next_release_dir(layout):
    first, second = _write(layout), _write(layout)
    assert first.parent.name.endswith("-1") and second.parent.name.endswith("-2")
    assert first.is_file() and second.is_file()


def test_next_release_dir_follows_the_highest_number_not_the_first_gap(layout):
    _first, second, _third = _write(layout), _write(layout), _write(layout)
    second.unlink()
    second.parent.rmdir()
    fourth = _write(layout)
    assert fourth.parent.name.endswith("-4")
    assert record.latest_record_path(layout) == fourth


def test_unknown_severity_fails_the_record(layout):
    payload = json.loads(_write(layout, findings=[Finding("lint", "BLOCK", "shouted", 2)]).read_text("utf-8"))
    assert payload["passed"] is False and payload["blocks"] == 1


def test_failure_record_without_scores_or_bom(layout):
    path = record.write_record(
        layout, RUN_ID, article_sha256=_sha(layout.article), bom_sha256=None,
        findings=[Finding("bom_refused", "block", "fact f1 is quote_missing", None)],
        scores=None, bom=None, workers=2,
    )
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert (payload["bom"], payload["scores"], payload["spec"], payload["evidence"]) == (None, None, None, {})
    assert payload["passed"] is False and payload["blocks"] == 1


# ---- latest_record -----------------------------------------------------------------


def test_latest_record_is_none_without_releases(layout):
    assert record.latest_record(layout) is None


def test_latest_record_reads_the_highest_numbered_dir(layout):
    for _ in range(10):
        _write(layout)
    newest = _write(layout, scores=score_gates(scorer_result(aeo=80)))
    assert newest.parent.name.endswith("-11")
    assert record.latest_record(layout)["passed"] is False


def test_latest_record_rejects_an_unreadable_latest_record(layout):
    path = _write(layout)
    path.write_text("{broken", encoding="utf-8")
    with pytest.raises(ValueError, match="unreadable"):
        record.latest_record(layout)


# ---- verify_publishable --------------------------------------------------------------


def test_verify_publishable_returns_the_passing_record(layout):
    _write(layout)
    assert record.verify_publishable(layout.article, layout.root)["passed"] is True


def test_verify_publishable_refuses_without_a_record(layout):
    with pytest.raises(ValueError, match="no release record"):
        record.verify_publishable(layout.article, layout.root)


def test_verify_publishable_refuses_an_edited_article(layout):
    _write(layout)
    layout.article.write_text("# Article\n\nEdited after release.\n", encoding="utf-8", newline="\n")
    with pytest.raises(ValueError, match="article changed"):
        record.verify_publishable(layout.article, layout.root)


def test_verify_publishable_refuses_a_failing_latest_record(layout):
    _write(layout, findings=[Finding("fact_quote", "block", "gone", 9)])
    with pytest.raises(ValueError, match="did not pass"):
        record.verify_publishable(layout.article, layout.root)


def test_newer_failing_record_supersedes_an_older_pass(layout):
    _write(layout)
    _write(layout, scores=score_gates(scorer_result(seo=50)))
    with pytest.raises(ValueError, match="did not pass"):
        record.verify_publishable(layout.article, layout.root)


def test_verify_publishable_refuses_a_changed_bom(layout):
    _write(layout)
    write_json(layout.bom, {**_bom(layout.root), "sections": []})
    with pytest.raises(ValueError, match="BOM changed"):
        record.verify_publishable(layout.article, layout.root)


def test_verify_publishable_refuses_a_missing_bom(layout):
    _write(layout)
    layout.bom.unlink()
    with pytest.raises(ValueError, match="BOM changed"):
        record.verify_publishable(layout.article, layout.root)


def test_verify_publishable_refuses_a_record_from_another_run(layout):
    _write(layout)
    path = record.latest_record_path(layout)
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["run_id"] = RUN_ID[:8] + "-0000-4000-8000-000000000000"
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="run"):
        record.verify_publishable(layout.article, layout.root)


def test_verify_publishable_refuses_an_identical_copy_under_rewrites(layout):
    _write(layout)
    copy = layout.root / "rewrites" / layout.article.name
    copy.parent.mkdir()
    copy.write_bytes(layout.article.read_bytes())
    with pytest.raises(ValueError, match="drafts/"):
        record.verify_publishable(copy, layout.root)
    assert record.verify_publishable(layout.article, layout.root)["passed"] is True


@pytest.mark.parametrize("relative", [SPEC_PATH, EVIDENCE_PATH, PAA_PATH])
def test_verify_publishable_refuses_a_changed_spec_or_evidence_file(layout, relative):
    _write(layout)
    write_json(layout.root / relative, {"file": relative, "edited": True})
    with pytest.raises(ValueError, match=relative):
        record.verify_publishable(layout.article, layout.root)


def test_verify_publishable_refuses_an_article_outside_the_layout(layout):
    with pytest.raises(ValueError):
        record.verify_publishable(layout.root / "notes" / "x.md", layout.root)
