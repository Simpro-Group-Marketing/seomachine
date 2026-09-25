"""Regression coverage for non-blocking publish-readiness warnings."""

import pytest

from data_sources.modules import publish_readiness
from tests.test_publish_readiness import files as readiness_files
from tests.test_publish_readiness import finding, run_with_patches


@pytest.fixture
def files(tmp_path):
    return readiness_files.__wrapped__(tmp_path)


def test_eeat_warning_is_reported_separately_from_blockers_and_priority_fixes(files):
    article, sidecar = files
    result, _, _, _ = run_with_patches(
        article,
        sidecar,
        overrides={
            "eeat_strength": [
                finding("eeat_strength_safe_but_weak", severity="warning")
            ]
        },
    )

    eeat = next(row for row in result["gates"] if row["name"] == "eeat_strength")
    report = publish_readiness.format_text_report(result)

    assert result["passed"] is True
    assert result.get("blockers", []) == []
    assert eeat["warnings"] == 1
    assert eeat["blockers"] == []
    assert result["priority_fixes"] == []
    assert "Warnings:" in report
    assert "eeat_strength_safe_but_weak" in report
    assert "Priority fixes:" not in report
