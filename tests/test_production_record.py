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
SPEC_BINDING = {"path": "research/production-bom-spec-field-service-software-2026-10-13.json", "sha256": "a" * 64}
EVIDENCE_BINDING = {"path": "research/customer-proof-selector-evidence-field-service-software.json",
                    "sha256": "b" * 64}
PAA_BINDING = {"path": "research/paa-evidence-field-service-software-2026-10-13.json", "sha256": "c" * 64}


def _bom() -> dict:
    return {
        "schema": "simpro-production-bom/v1",
        "identity": {"run_id": RUN_ID, "spec": dict(SPEC_BINDING)},
        "paa": {"artifact": dict(PAA_BINDING), "questions": []},
        "customer_proof": {"evidence": dict(EVIDENCE_BINDING), "roles": []},
        "context": {"status": "not_applicable", "reason": "x"},
    }


@pytest.fixture
def layout(tmp_path):
    value = Layout.for_article(ARTICLE, tmp_path)
    value.article.parent.mkdir(parents=True, exist_ok=True)
    value.article.write_text("# Article\n", encoding="utf-8", newline="\n")
    write_json(value.bom, _bom())
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
        scores=scores or score_gates(scorer_result()),
        bom=_bom(),
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
    assert payload["spec"] == SPEC_BINDING
    assert payload["evidence"] == {"customer_proof.evidence": EVIDENCE_BINDING, "paa.artifact": PAA_BINDING}
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
    write_json(layout.bom, {**_bom(), "sections": []})
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


def test_verify_publishable_refuses_an_article_outside_the_layout(layout):
    with pytest.raises(ValueError):
        record.verify_publishable(layout.root / "notes" / "x.md", layout.root)
