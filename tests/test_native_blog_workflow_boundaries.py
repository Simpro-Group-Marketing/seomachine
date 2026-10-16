from tests.fixture_text import fixture_text

import re
from pathlib import Path

import pytest

from data_sources.modules.readiness.adapters import _scorecard_from_scorer_result
from data_sources.modules import context_binding_generator, customer_proof_selector
from data_sources.modules.content_scrubber import scrub_file
from data_sources.modules import fred_authority_selector
from data_sources.modules.grav_publisher import GravPublisher


ROOT = Path(__file__).resolve().parents[1]
# Ceiling includes machine-review, non-vault proof, ItemList schema,
# risk-tiered proof-link suites, and P0 readiness integrity coverage.


BLOG_MARKDOWN = fixture_text("content_evidence:test_native_blog_workflow_boundaries-17-1")


def test_scrub_file_reports_changes_without_mutating_article_markdown(tmp_path):
    article = tmp_path / "article.md"
    article.write_text("Dispatch" + chr(8212) + "work.\n", encoding="utf-8")
    before = article.read_bytes()

    report = scrub_file(str(article))

    assert article.read_bytes() == before
    assert report["would_change"] is True
    assert report["statistics"]["emdashes_replaced"] == 1
    assert "cleaned_content" not in report


def test_grav_dry_run_does_not_persist_local_blog_markdown_preview(tmp_path, monkeypatch):
    article = tmp_path / "post.md"
    article.write_text(BLOG_MARKDOWN, encoding="utf-8")
    publisher = GravPublisher(repo="owner/repo", blog_path="blogs", lang="en")
    publisher.preview_root = tmp_path / "preview"
    monkeypatch.setattr("data_sources.modules.production.publish_gate.require_release", lambda *args: None)
    result = publisher.publish(str(article), dry_run=True)

    assert result["dry_run"] is True
    assert "preview_path" not in result
    assert result["article"].startswith("---\ntitle:")
    assert not publisher.preview_root.exists()


def test_landing_scorecard_marks_blog_only_gates_not_applicable():
    scorer_result = {
        "passed": True,
        "content_quality_score": 82.0,
        "threshold": 75,
        "aeo_geo": {
            "score": None,
            "threshold": None,
            "passed": True,
            "not_applicable": True,
        },
        "priority_fixes": [],
    }

    scorecard = _scorecard_from_scorer_result(scorer_result)

    assert scorecard["passed"] is True
    assert scorecard["content_quality"] == {
        "score": 82.0,
        "threshold": 75,
        "passed": True,
    }
    assert scorecard["seo_quality"] == {
        "score": None,
        "threshold": None,
        "passed": True,
        "critical_issue_count": 0,
        "not_applicable": True,
    }
    assert scorecard["aeo_geo"] == {
        "score": None,
        "threshold": None,
        "passed": True,
        "not_applicable": True,
    }


def test_redundant_python_blog_workflow_modules_are_removed():
    retired_modules = [
        ROOT / "data_sources" / "modules" / "article_planner.py",
        ROOT / "data_sources" / "modules" / "section_writer.py",
        ROOT / "data_sources" / "modules" / "blog_assembly_mutation_recorder.py",
        ROOT / "data_sources" / "modules" / "competitor_gap_analyzer.py",
        ROOT / "data_sources" / "modules" / "social_research_aggregator.py",
        ROOT / "data_sources" / "modules" / "engagement_analyzer.py",
    ]

    assert [path for path in retired_modules if path.exists()] == []


def test_retained_python_modules_do_not_hardcode_blog_copy_writes():
    write_call = re.compile(
        r'''write_text\(|\.open\([^)]*["']w|open\([^)]*["']w|atomic_write_text\(|atomic_write_json\('''
    )
    forbidden_dirs = (
        'drafts/',
        r'drafts\\',
        'rewrites/',
        r'rewrites\\',
        'published/',
        r'published\\',
    )
    violations = []

    for path in (ROOT / "data_sources" / "modules").glob("*.py"):
        for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            if write_call.search(line) and any(directory in line for directory in forbidden_dirs):
                violations.append(f"{path.relative_to(ROOT)}:{line_number}: {line.strip()}")

    assert violations == []


@pytest.mark.parametrize(
    "writer",
    [
        context_binding_generator._atomic_write_text,
        fred_authority_selector._atomic_write_text,
    ],
)
def test_text_governance_writers_reject_public_article_directories(tmp_path, writer):
    destination = tmp_path / "drafts" / "governance.md"
    destination.parent.mkdir()

    with pytest.raises(ValueError, match="public article director"):
        writer(destination, "governance only\n")

    assert not destination.exists()


def test_selector_evidence_rejects_public_article_directories(tmp_path):
    output = tmp_path / "rewrites" / "selector-evidence.json"

    with pytest.raises(ValueError, match="public article director"):
        customer_proof_selector._validate_evidence_output_paths(
            output,
            output.with_name(f"{output.name}.tmp"),
            {},
        )
