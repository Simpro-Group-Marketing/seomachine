from tests.fixture_text import fixture_text

import re
from pathlib import Path

import pytest

from data_sources.modules import publish_readiness
from data_sources.modules import context_binding_generator, customer_proof_selector
from data_sources.modules.content_scrubber import scrub_file
from data_sources.modules import fred_authority_selector
from data_sources.modules.blog_assembly_stage_receipt import StageReceiptError
from data_sources.modules.grav_publisher import GravPublisher


ROOT = Path(__file__).resolve().parents[1]
# Ceiling includes machine-review, non-vault proof, ItemList schema,
# risk-tiered proof-link suites, and P0 readiness integrity coverage.
PYTHON_TEST_LOC_REFACTOR_CEILING = 37_000


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


def test_receipt_backed_scrub_writes_governance_only_not_article(tmp_path):
    article = tmp_path / "article.md"
    receipt_path = tmp_path / "scrub-receipt.json"
    article.write_text("Schedule" + chr(8212) + "work.\n", encoding="utf-8")
    before = article.read_bytes()

    with pytest.raises(StageReceiptError) as raised:
        scrub_file(
            str(article),
            stage_receipt_output=str(receipt_path),
            run_id="run-native-boundary",
        )

    assert article.read_bytes() == before
    assert raised.value.code == "scrub_changes_required"
    assert not receipt_path.exists()

def test_grav_dry_run_does_not_persist_local_blog_markdown_preview(tmp_path):
    article = tmp_path / "post.md"
    article.write_text(BLOG_MARKDOWN, encoding="utf-8")
    publisher = GravPublisher(repo="owner/repo", blog_path="blogs", lang="en")
    publisher.preview_root = tmp_path / "preview"

    result = publisher.publish(str(article), dry_run=True)

    assert result["dry_run"] is True
    assert "preview_path" not in result
    assert result["article"].startswith("---\ntitle:")
    assert not publisher.preview_root.exists()


def test_readiness_scorecard_keeps_content_seo_and_aeo_gates_independent():
    scorer_result = {
        "passed": False,
        "content_quality_score": 91.0,
        "threshold": 85,
        "aeo_geo": {"score": 94, "threshold": 90, "passed": True},
        "quality_gates": {
            "content_quality": {
                "score": 91.0,
                "threshold": 85,
                "passed": True,
            },
            "seo_quality": {
                "score": 89,
                "threshold": 85,
                "passed": True,
                "critical_issues": [],
            },
            "aeo_geo": {
                "score": 94,
                "threshold": 90,
                "passed": True,
            },
        },
    }

    scorecard = publish_readiness._scorecard_from_scorer_result(
        scorer_result,
        artifact_kind="blog",
    )

    assert scorecard["passed"] is False
    assert scorecard["content_quality"] == {
        "score": 91.0,
        "threshold": 85,
        "passed": True,
    }
    assert scorecard["seo_quality"]["score"] == 89
    assert scorecard["seo_quality"]["threshold"] == 90
    assert scorecard["seo_quality"]["target"] == 95
    assert scorecard["seo_quality"]["passed"] is False
    assert scorecard["seo_quality"]["target_met"] is False
    assert scorecard["seo_quality"]["target_status"] == "failed_floor"
    assert scorecard["seo_quality"]["critical_issue_count"] == 0
    assert scorecard["aeo_geo"] == {
        "score": 94,
        "threshold": 90,
        "passed": True,
    }


@pytest.mark.parametrize(
    "seo_score,expected_passed,expected_target_met,expected_target_status",
    [
        (90, True, False, "below_target"),
        (92, True, False, "below_target"),
        (95, True, True, "met"),
    ],
)
def test_readiness_scorecard_reports_seo_target_separately_from_release_floor(
    seo_score,
    expected_passed,
    expected_target_met,
    expected_target_status,
):
    scorecard = publish_readiness._scorecard_from_scorer_result(
        {
            "content_quality_score": 95,
            "threshold": 85,
            "quality_gates": {
                "seo_quality": {
                    "score": seo_score,
                    "passed": expected_passed,
                    "critical_issues": [],
                },
                "aeo_geo": {"score": 95, "threshold": 90, "passed": True},
            },
        },
        artifact_kind="blog",
    )

    assert scorecard["passed"] is True
    assert scorecard["seo_quality"]["threshold"] == 90
    assert scorecard["seo_quality"]["target"] == 95
    assert scorecard["seo_quality"]["passed"] is expected_passed
    assert scorecard["seo_quality"]["target_met"] is expected_target_met
    assert scorecard["seo_quality"]["target_status"] == expected_target_status


def test_readiness_scorecard_fails_floor_when_critical_issues_exist_even_at_target():
    scorecard = publish_readiness._scorecard_from_scorer_result(
        {
            "content_quality_score": 95,
            "threshold": 85,
            "quality_gates": {
                "seo_quality": {
                    "score": 95,
                    "passed": True,
                    "critical_issues": ["Unsupported SEO claim"],
                },
                "aeo_geo": {"score": 95, "threshold": 90, "passed": True},
            },
        },
        artifact_kind="blog",
    )

    assert scorecard["passed"] is False
    assert scorecard["seo_quality"]["passed"] is False
    assert scorecard["seo_quality"]["target_met"] is True
    assert scorecard["seo_quality"]["target_status"] == "failed_floor"
    assert scorecard["seo_quality"]["critical_issue_count"] == 1


def test_readiness_scorecard_uses_the_canonical_seo_threshold(monkeypatch):
    monkeypatch.setattr(publish_readiness, "SEO_PUBLISHING_THRESHOLD", 91, raising=False)
    scorecard = publish_readiness._scorecard_from_scorer_result(
        {
            "content_quality_score": 95,
            "threshold": 85,
            "quality_gates": {
                "seo_quality": {
                    "score": 90,
                    "passed": True,
                    "critical_issues": [],
                },
                "aeo_geo": {"score": 95, "threshold": 90, "passed": True},
            },
        },
        artifact_kind="blog",
    )

    assert scorecard["seo_quality"]["threshold"] == 91
    assert scorecard["seo_quality"]["passed"] is False


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

    scorecard = publish_readiness._scorecard_from_scorer_result(
        scorer_result,
        artifact_kind="landing_page",
    )

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


def test_python_test_loc_stays_below_the_refactor_ceiling():
    python_test_loc = sum(
        1
        for path in (ROOT / "tests").rglob("*.py")
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    )

    assert python_test_loc <= PYTHON_TEST_LOC_REFACTOR_CEILING


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
