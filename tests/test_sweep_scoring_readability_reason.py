"""The sweep names the readability failure when it alone blocks content quality."""
from __future__ import annotations

from data_sources.modules.release_workflow import precheck_sweep

READABILITY_ERROR = "Readability scoring failed: input could not be parsed"


def _result(*, composite: float = 88.0, scoring_error: str | None = READABILITY_ERROR):
    details = {"scoring_error": scoring_error} if scoring_error else {}
    return {
        "passed": False,
        "composite_score": composite,
        "quality_gates": {
            "content_quality": {
                "score": composite, "threshold": 85, "passed": not scoring_error and composite >= 85,
            },
            "seo_quality": {"score": 100, "threshold": 90, "passed": True},
            "aeo_geo": {"score": 95, "threshold": 90, "passed": True, "checks": {}},
        },
        "aeo_geo": {"score": 95, "threshold": 90, "passed": True, "checks": {}},
        "dimensions": {"readability": {"score": 0, "details": details}},
        "priority_fixes": [{"issue": scoring_error, "severity": "high"}] if scoring_error else [],
    }


def test_readability_failure_reason_is_in_not_passed_message() -> None:
    rows = precheck_sweep.scorer_findings(_result())
    row = next(r for r in rows if r["rule_id"] == "content_scorer.not_passed")
    assert row["severity"] == "error"
    assert "content_quality 88.0/85" in row["message"]
    assert "Readability scoring failed" in row["message"]


def test_message_is_unchanged_when_content_quality_fails_on_score() -> None:
    rows = precheck_sweep.scorer_findings(_result(composite=80.0, scoring_error=None))
    row = next(r for r in rows if r["rule_id"] == "content_scorer.not_passed")
    assert "Readability" not in row["message"]
