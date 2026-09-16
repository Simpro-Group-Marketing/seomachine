from data_sources.modules.content_scoring.reporting import ScoringReportingMixin


def test_report_separates_content_quality_hard_gates_and_overall_statuses():
    result = {
        "composite_score": 92,
        "passed": False,
        "threshold": 90,
        "aeo_geo": {"score": 88, "threshold": 90, "passed": False},
        "quality_gates": {
            "content_quality": {"passed": True},
            "aeo_geo": {"passed": False},
        },
        "dimensions": {},
        "priority_fixes": [
            {"dimension": "aeo_geo", "issue": "Add proof", "fix": "Cite source"}
        ],
    }

    report = ScoringReportingMixin().format_report(result)

    assert "Composite Score: 92/100 (PASSED)" in report
    assert "Content Quality: PASSED" in report
    assert "Hard Gates: FAILED" in report
    assert "Overall: FAILED" in report
    assert "BELOW THRESHOLD" not in report
    assert "Priority Fixes:" in report
