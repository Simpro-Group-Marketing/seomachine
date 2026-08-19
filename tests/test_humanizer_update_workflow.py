import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "humanizer-upstream.yml"


def _workflow() -> str:
    return WORKFLOW.read_text(encoding="utf-8")


def test_workflow_checks_weekly_manually_and_on_review_prs():
    """Removing scheduled discovery or compatibility CI must make this fail."""
    content = _workflow()

    assert "cron: '0 13 * * 1'" in content
    assert "workflow_dispatch:" in content
    assert "pull_request:" in content
    assert "python tools/humanizer_upstream.py verify" in content
    assert "python tools/humanizer_upstream.py check-upstream --ref main" in content


def test_workflow_stages_vendor_only_and_opens_draft_review_pr():
    """Auto-activating policy or auto-merging an upgrade must make this fail."""
    content = _workflow()

    assert "python tools/humanizer_upstream.py stage --ref main" in content
    assert "python tools/humanizer_upstream.py adopt" in content
    assert "git add vendor/blader-humanizer" in content
    assert "git add config/humanizer-policy.json" not in content
    assert "gh pr create --draft" in content
    assert "auto-merge" not in content.lower()
    assert "reviewed_upstream_commit" in content
    for detail in (
        "Current version",
        "Candidate version",
        "Current files",
        "Candidate files",
        "Current verification",
        "Candidate verification",
    ):
        assert detail in content


def test_workflow_compatibility_suite_covers_editor_receipts_scoring_and_readiness():
    content = _workflow()

    for test_file in (
        "tests/test_aeo_geo_workflow_docs.py",
        "tests/test_blog_assembly_stage_receipt.py",
        "tests/test_content_scorer_aeo_geo_gate.py",
        "tests/test_publish_readiness.py",
    ):
        assert test_file in content


def test_workflow_uses_minimum_job_permissions_and_pinned_official_actions():
    """Unpinned actions or broad default write access must make this fail."""
    content = _workflow()

    uses = re.findall(r"uses:\s*(actions/(?:checkout|setup-python))@([^\s]+)", content)
    assert uses
    assert all(re.fullmatch(r"[0-9a-f]{40}", revision) for _, revision in uses)
    assert "permissions:\n      contents: write\n      pull-requests: write" in content
    assert "GH_TOKEN: ${{ github.token }}" in content
