from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest


def _write_article_and_sidecar(root: Path) -> tuple[Path, Path]:
    article = root / "drafts" / "closeout.md"
    sidecar = root / "research" / "validation-closeout.md"
    article.parent.mkdir(parents=True, exist_ok=True)
    sidecar.parent.mkdir(parents=True, exist_ok=True)
    article.write_text(
        "# Closeout Draft\n\n"
        "Dispatchers review the schedule before technicians start the day.\n",
        encoding="utf-8",
    )
    sidecar.write_text("# Validation\n\nNo public proof claims are present.\n", encoding="utf-8")
    return article, sidecar


def _passing_scorecard() -> dict:
    return {
        "composite_score": 91,
        "content_quality_score": 91,
        "passed": True,
        "threshold": 85,
        "aeo_geo": {
            "score": 95,
            "passed": True,
            "threshold": 90,
            "checks": {
                "paa_provenance": {
                    "passed": True,
                    "status": "passed",
                    "details": {"finding_count": 0},
                }
            },
        },
        "quality_gates": {
            "content_quality": {"passed": True},
            "url_validation": {"total": 0, "passed": True},
            "source_support": {"finding_count": 0, "passed": True, "findings": []},
        },
        "dimensions": {},
        "priority_fixes": [],
    }


def _patch_clean_dependencies(monkeypatch):
    from data_sources.modules import blog_draft_closeout

    monkeypatch.setattr(
        blog_draft_closeout,
        "scrub_file",
        lambda path: {
            "file": str(Path(path).resolve()),
            "would_change": False,
            "statistics": {"unicode_removed": 0},
        },
    )
    monkeypatch.setattr(blog_draft_closeout, "lint_file", lambda *args, **kwargs: [])
    monkeypatch.setattr(
        blog_draft_closeout,
        "lint_summarize_findings",
        lambda findings: {"error": 0, "warning": 0},
    )
    monkeypatch.setattr(blog_draft_closeout, "lint_should_fail", lambda *args, **kwargs: False)
    monkeypatch.setattr(blog_draft_closeout, "source_support_check_file", lambda *args, **kwargs: [])
    monkeypatch.setattr(
        blog_draft_closeout,
        "source_support_summarize_findings",
        lambda findings: {"error": 0, "warning": 0},
    )
    monkeypatch.setattr(
        blog_draft_closeout,
        "source_support_should_fail",
        lambda *args, **kwargs: False,
    )

    class EmptyUrlSummary:
        passed = True
        total = 0
        resolved_count = 0
        unresolved_count = 0
        manual_review_count = 0
        blockers = []
        results = []

    monkeypatch.setattr(
        blog_draft_closeout,
        "validate_file_urls",
        lambda path: EmptyUrlSummary(),
    )
    monkeypatch.setattr(
        blog_draft_closeout.ContentScorer,
        "score",
        lambda self, content, **kwargs: _passing_scorecard(),
    )
    return blog_draft_closeout


def test_successful_closeout_binds_inputs_and_creates_no_release_artifacts(
    tmp_path: Path,
    monkeypatch,
) -> None:
    blog_draft_closeout = _patch_clean_dependencies(monkeypatch)
    article, sidecar = _write_article_and_sidecar(tmp_path)
    output = tmp_path / "research" / "closeout.json"

    exit_code = blog_draft_closeout.main(
        [
            str(article),
            "--proof-sidecar",
            str(sidecar),
            "--output",
            str(output),
            "--workspace-root",
            str(tmp_path),
        ]
    )

    payload = json.loads(output.read_text(encoding="utf-8"))
    assert exit_code == 0
    assert payload["schema"] == "simpro-blog-draft-closeout/v1"
    assert payload["article"]["sha256"] == hashlib.sha256(article.read_bytes()).hexdigest()
    assert payload["sidecar"]["sha256"] == hashlib.sha256(sidecar.read_bytes()).hexdigest()
    assert payload["release_artifacts_created"] is False
    assert set(payload["checks"]) == {
        "scrub",
        "ai_lint",
        "source_classification",
        "source_support",
        "paa",
        "url_validation",
        "scoring",
    }
    assert payload["checks"]["source_classification"]["status"] == "not_applicable"
    assert payload["passed"] is True
    assert payload["blockers"] == []
    assert not (tmp_path / "release").exists()
    assert not list(tmp_path.rglob("*receipt*.json"))


def test_output_cannot_overwrite_sidecar_and_sidecar_bytes_are_unchanged(
    tmp_path: Path,
    monkeypatch,
) -> None:
    blog_draft_closeout = _patch_clean_dependencies(monkeypatch)
    article, sidecar = _write_article_and_sidecar(tmp_path)
    original_sidecar = sidecar.read_bytes()

    with pytest.raises(SystemExit) as raised:
        blog_draft_closeout.main(
            [
                str(article),
                "--proof-sidecar",
                str(sidecar),
                "--output",
                str(sidecar),
                "--workspace-root",
                str(tmp_path),
            ]
        )

    assert raised.value.code == 2
    assert sidecar.read_bytes() == original_sidecar


def test_output_outside_workspace_is_rejected(tmp_path: Path, monkeypatch) -> None:
    blog_draft_closeout = _patch_clean_dependencies(monkeypatch)
    article, sidecar = _write_article_and_sidecar(tmp_path)
    outside_output = tmp_path.parent / f"{tmp_path.name}-outside-closeout.json"

    with pytest.raises(SystemExit) as raised:
        blog_draft_closeout.main(
            [
                str(article),
                "--proof-sidecar",
                str(sidecar),
                "--output",
                str(outside_output),
                "--workspace-root",
                str(tmp_path),
            ]
        )

    assert raised.value.code == 2
    assert not outside_output.exists()


def test_scorer_skips_duplicate_url_and_source_support_checks_while_explicit_checks_run(
    tmp_path: Path,
    monkeypatch,
) -> None:
    blog_draft_closeout = _patch_clean_dependencies(monkeypatch)
    article, sidecar = _write_article_and_sidecar(tmp_path)
    output = tmp_path / "research" / "closeout.json"
    calls = {"source_support": 0, "url_validation": 0}
    scorer_kwargs = {}

    def record_source_support(*args, **kwargs):
        calls["source_support"] += 1
        return []

    class EmptyUrlSummary:
        passed = True
        total = 0
        resolved_count = 0
        unresolved_count = 0
        manual_review_count = 0
        blockers = []
        results = []

    def record_url_validation(path):
        calls["url_validation"] += 1
        return EmptyUrlSummary()

    def record_score(self, content, **kwargs):
        scorer_kwargs.update(kwargs)
        return _passing_scorecard()

    monkeypatch.setattr(blog_draft_closeout, "source_support_check_file", record_source_support)
    monkeypatch.setattr(blog_draft_closeout, "validate_file_urls", record_url_validation)
    monkeypatch.setattr(blog_draft_closeout.ContentScorer, "score", record_score)

    assert blog_draft_closeout.main(
        [
            str(article),
            "--proof-sidecar",
            str(sidecar),
            "--output",
            str(output),
            "--workspace-root",
            str(tmp_path),
        ]
    ) == 0

    assert calls == {"source_support": 1, "url_validation": 1}
    assert scorer_kwargs["validate_urls"] is False
    assert scorer_kwargs["validate_source_support"] is False
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["checks"]["source_support"]["passed"] is True
    assert payload["checks"]["url_validation"]["passed"] is True


def test_source_classification_missing_decision_blocks_without_release_artifacts(
    tmp_path: Path,
    monkeypatch,
) -> None:
    blog_draft_closeout = _patch_clean_dependencies(monkeypatch)
    article, sidecar = _write_article_and_sidecar(tmp_path)
    inventory = tmp_path / "research" / "source-candidates.json"
    inventory.write_text(
        json.dumps(
            {
                "schema": "simpro-source-candidate-inventory/v1",
                "candidates": [{"source_url": "https://example.com/source"}],
            },
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    output = tmp_path / "research" / "closeout.json"

    exit_code = blog_draft_closeout.main(
        [
            str(article),
            "--proof-sidecar",
            str(sidecar),
            "--output",
            str(output),
            "--workspace-root",
            str(tmp_path),
            "--source-inventory",
            str(inventory),
            "--classification-directory",
            str(tmp_path / "research" / "source-classifications"),
        ]
    )

    payload = json.loads(output.read_text(encoding="utf-8"))
    assert exit_code == 1
    assert payload["release_artifacts_created"] is False
    assert payload["passed"] is False
    assert payload["checks"]["source_classification"]["status"] == "failed"
    assert payload["checks"]["source_classification"]["blockers"][0]["rule_id"] == (
        "source_classification_decision_missing"
    )
    assert payload["blockers"][0]["rule_id"] == "source_classification_decision_missing"
    assert not (tmp_path / "release").exists()


def test_paa_inputs_without_scorer_paa_check_block_closeout(
    tmp_path: Path,
    monkeypatch,
) -> None:
    blog_draft_closeout = _patch_clean_dependencies(monkeypatch)
    article, sidecar = _write_article_and_sidecar(tmp_path)
    output = tmp_path / "research" / "closeout.json"
    scorecard = _passing_scorecard()
    scorecard["aeo_geo"]["checks"] = {}

    monkeypatch.setattr(
        blog_draft_closeout.ContentScorer,
        "score",
        lambda self, content, **kwargs: scorecard,
    )

    exit_code = blog_draft_closeout.main(
        [
            str(article),
            "--proof-sidecar",
            str(sidecar),
            "--output",
            str(output),
            "--workspace-root",
            str(tmp_path),
            "--paa-expected-run-id",
            "answersocrates-run-1",
        ]
    )

    payload = json.loads(output.read_text(encoding="utf-8"))
    assert exit_code == 1
    assert payload["checks"]["paa"]["status"] == "failed"
    assert payload["checks"]["paa"]["blockers"][0]["rule_id"] == "paa_check_unavailable"


def test_closeout_surfaces_scrub_lint_source_url_and_scoring_results(
    tmp_path: Path,
    monkeypatch,
) -> None:
    from data_sources.modules.url_validator import UrlValidationResult, UrlValidationSummary

    blog_draft_closeout = _patch_clean_dependencies(monkeypatch)
    article, sidecar = _write_article_and_sidecar(tmp_path)
    output = tmp_path / "research" / "closeout.json"
    lint_finding = {
        "rule_id": "humanizer.chatbot_residue",
        "severity": "warning",
        "line": 2,
        "message": "Chatbot residue.",
    }
    support_finding = {
        "rule_id": "general_claim_source_missing",
        "severity": "error",
        "line": 2,
        "message": "Missing support.",
    }
    url_result = UrlValidationResult(
        url="https://example.com/dead",
        status="unresolved",
        status_code=404,
        reason="HTTP 404",
        line=4,
        anchor="dead",
    )
    scorecard = _passing_scorecard()
    scorecard["passed"] = False
    scorecard["quality_gates"]["content_quality"] = {"passed": False}
    scorecard["priority_fixes"] = [{"dimension": "humanity", "issue": "Tighten copy"}]

    monkeypatch.setattr(
        blog_draft_closeout,
        "scrub_file",
        lambda path: {
            "file": str(Path(path).resolve()),
            "would_change": True,
            "statistics": {"emdashes_replaced": 1},
        },
    )
    monkeypatch.setattr(blog_draft_closeout, "lint_file", lambda *args, **kwargs: [lint_finding])
    monkeypatch.setattr(
        blog_draft_closeout,
        "lint_summarize_findings",
        lambda findings: {"error": 0, "warning": len(findings)},
    )
    monkeypatch.setattr(blog_draft_closeout, "source_support_check_file", lambda *args, **kwargs: [support_finding])
    monkeypatch.setattr(
        blog_draft_closeout,
        "source_support_summarize_findings",
        lambda findings: {"error": len(findings), "warning": 0},
    )
    monkeypatch.setattr(blog_draft_closeout, "source_support_should_fail", lambda *args, **kwargs: True)
    monkeypatch.setattr(
        blog_draft_closeout,
        "validate_file_urls",
        lambda path: UrlValidationSummary([url_result]),
    )
    monkeypatch.setattr(
        blog_draft_closeout.ContentScorer,
        "score",
        lambda self, content, **kwargs: scorecard,
    )

    exit_code = blog_draft_closeout.main(
        [
            str(article),
            "--proof-sidecar",
            str(sidecar),
            "--output",
            str(output),
            "--workspace-root",
            str(tmp_path),
        ]
    )

    payload = json.loads(output.read_text(encoding="utf-8"))
    assert exit_code == 1
    assert payload["checks"]["scrub"]["would_change"] is True
    assert payload["checks"]["ai_lint"]["findings"] == [lint_finding]
    assert payload["checks"]["source_support"]["findings"] == [support_finding]
    assert payload["checks"]["url_validation"]["results"][0]["status"] == "unresolved"
    assert payload["scorecard"]["priority_fixes"] == scorecard["priority_fixes"]
    assert payload["checks"]["scoring"]["passed"] is False
    assert {blocker["check"] for blocker in payload["blockers"]} >= {
        "scrub",
        "source_support",
        "url_validation",
        "scoring",
    }


def test_blog_draft_closeout_help_exits_zero() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "data_sources.modules.blog_draft_closeout", "--help"],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert "blog_draft_closeout" in result.stdout
