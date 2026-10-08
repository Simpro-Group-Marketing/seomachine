import dataclasses
from unittest.mock import patch

from data_sources.modules.content_scorer import ContentScorer
from data_sources.modules.content_scoring.common import default_scoring_dependencies


PROSE = (
    "Use the same service job in every product demonstration. "
    "Keep the steps clear, record each result, and compare the evidence."
)


def test_readability_scope_excludes_tables_placeholders_and_empty_anchors() -> None:
    content = f"""# Buyer guide

{PROSE}

| Tool | Buyer fit |
|---|---|
| Alpha | Service teams |

Tool | Buyer fit
--- | ---
Beta | Project teams

<table><tr><td>HTML comparison detail</td></tr></table>

[CMS MODULE PLACEHOLDER | type: comparison matrix]
[IMAGE PLACEHOLDER | source: approved asset | alt: "Buyer guide" | render target: 819 x 250 px | resize and compress before upload]
[VIDEO PLACEHOLDER | source: approved video | title: "Buyer guide" | placement: comparison section | embed target: responsive 16:9 | VideoObject: add only after embed]
Visible sentence before <a id="comparison"></a> another empty anchor <a id="second"></a> stays visible.

- Keep this visible checklist item.
"""

    prepared, details = ContentScorer()._prepare_readability_content(content)

    assert PROSE in prepared
    assert "Buyer guide." in prepared
    assert "Keep this visible checklist item." in prepared
    assert "Alpha" not in prepared
    assert "Beta" not in prepared
    assert "HTML comparison detail" not in prepared
    assert "PLACEHOLDER" not in prepared
    assert details["analysis_scope"] == (
        "visible_prose_excluding_tables_placeholders_and_empty_anchors"
    )
    assert details["excluded_markdown_tables"] == 2
    assert details["excluded_html_tables"] == 1
    assert details["excluded_image_placeholders"] == 1
    assert details["excluded_video_placeholders"] == 1
    assert details["excluded_cms_placeholders"] == 1
    assert details["excluded_empty_anchors"] == 2
    assert details["normalized_markdown_headings"] == 1
    assert details["analyzed_words"] == len(prepared.split())


def test_non_prose_handoff_structures_cannot_change_readability_metrics() -> None:
    scorer = ContentScorer()
    baseline, _ = scorer._prepare_readability_content(PROSE)
    with_handoff, _ = scorer._prepare_readability_content(
        f"""{PROSE}

| Tool | Buyer fit |
|---|---|
| Alpha | Service teams |

<table><tr><td>HTML comparison detail</td></tr></table>
[CMS MODULE PLACEHOLDER | type: comparison matrix]
[IMAGE PLACEHOLDER | source: approved asset | alt: "Buyer guide" | render target: 819 x 250 px | resize and compress before upload]
<a id="comparison"></a>
"""
    )

    assert baseline == with_handoff
    assert scorer._score_readability(baseline) == scorer._score_readability(with_handoff)


def test_shared_analysis_still_keeps_visible_table_text() -> None:
    content = (
        f"{PROSE}\n\n"
        "| Tool | Buyer fit |\n"
        "|---|---|\n"
        "| Alpha | Service teams |\n"
    )
    scorer = ContentScorer()

    shared_analysis = scorer._clean_for_analysis(content)
    readability_analysis, _ = scorer._prepare_readability_content(content)

    assert "Alpha" in shared_analysis
    assert "Alpha" not in readability_analysis


def test_non_table_pipes_and_noncanonical_placeholders_remain_visible() -> None:
    content = f"""{PROSE}

This ordinary sentence uses A | B as a written comparison.
| This is not followed by a delimiter |
This line remains visible.
[IMAGE PLACEHOLDER: incomplete handoff]
"""

    prepared, details = ContentScorer()._prepare_readability_content(content)

    assert "A | B" in prepared
    assert "not followed by a delimiter" in prepared
    assert "This line remains visible." in prepared
    assert "incomplete handoff" in prepared
    assert details["excluded_markdown_tables"] == 0
    assert details["excluded_image_placeholders"] == 0


def test_orchestration_uses_the_narrow_scope_for_readability_only() -> None:
    content = f"""# Buyer guide

{PROSE}

| Tool | Buyer fit |
|---|---|
| Alpha | Service teams |
"""
    dimension = {"score": 100, "issues": [], "details": {}}
    structure = {**dimension, "prose_ratio": 0.65}
    seo = {**dimension, "passed": True}
    gate_context = {
        "aeo_geo": {
            "score": 100,
            "passed": True,
            "threshold": 90,
            "checks": {},
            "issues": [],
        }
    }

    with (
        patch.object(ContentScorer, "_score_humanity", return_value=dimension) as humanity,
        patch.object(ContentScorer, "_score_specificity", return_value=dimension) as specificity,
        patch.object(ContentScorer, "_score_structure_balance", return_value=structure),
        patch.object(ContentScorer, "_score_seo", return_value=seo),
        patch.object(ContentScorer, "_score_readability", return_value=dimension) as readability,
        patch.object(ContentScorer, "_run_quality_gates", return_value=gate_context),
        patch.object(ContentScorer, "_quality_gates_passed", return_value=True),
        patch.object(ContentScorer, "_build_quality_gates", return_value={}),
        patch(
            "data_sources.modules.content_scoring.orchestration.build_priority_fixes",
            return_value=[],
        ),
    ):
        result = ContentScorer().score(content)

    assert "Alpha" in humanity.call_args.args[0]
    assert "Alpha" in specificity.call_args.args[0]
    assert "Alpha" not in readability.call_args.args[0]
    assert result["dimensions"]["readability"]["details"][
        "excluded_markdown_tables"
    ] == 1


class _Boom:
    def analyze(self, content):
        raise RuntimeError("tokenizer crashed")


class _ErrorKey:
    def analyze(self, content):
        return {"error": "No readable content provided"}


def _scorer(factory) -> ContentScorer:
    deps = dataclasses.replace(
        default_scoring_dependencies(), readability_scorer_factory=factory
    )
    return ContentScorer(dependencies=deps)


def test_readability_crash_scores_zero_with_visible_issue() -> None:
    result = _scorer(_Boom)._score_readability("Some prose here.")

    assert result["score"] == 0
    assert any(
        issue["issue"].startswith("Readability scoring failed")
        and issue["severity"] == "high"
        for issue in result["issues"]
    )


def test_readability_error_payload_scores_zero() -> None:
    result = _scorer(_ErrorKey)._score_readability("Some prose here.")

    assert result["score"] == 0
    assert result["details"]["scoring_error"].startswith("Readability scoring failed")


def _score_with_readability_crash() -> tuple:
    from tests.test_content_scorer_minimum_word_gate import (
        _content,
        _passing_dependencies,
    )

    deps = dataclasses.replace(
        _passing_dependencies(), readability_scorer_factory=_Boom
    )
    perfect = {"score": 100, "issues": [], "details": {}}
    with patch.object(ContentScorer, "_score_humanity", return_value=perfect), patch.object(
        ContentScorer, "_score_specificity", return_value=perfect
    ), patch.object(
        ContentScorer,
        "_score_structure_balance",
        return_value={**perfect, "prose_ratio": 0.65},
    ), patch.object(
        ContentScorer, "_score_seo", return_value={**perfect, "passed": True}
    ):
        scorer = ContentScorer(dependencies=deps)
        return scorer, scorer.score(
            _content(200), {"primary_keyword": "field service workflow"}
        )


def test_readability_failure_blocks_content_quality_despite_composite_pass() -> None:
    _, result = _score_with_readability_crash()

    assert result["composite_score"] >= result["threshold"]
    assert result["quality_gates"]["content_quality"]["passed"] is False
    assert not result["passed"]
    assert result["priority_fixes"][0]["issue"].startswith("Readability scoring failed")


def test_format_report_shows_content_quality_failed_on_readability_failure() -> None:
    scorer, result = _score_with_readability_crash()
    assert result["composite_score"] >= result["threshold"]

    report = scorer.format_report(result)

    assert "Content Quality: FAILED" in report
    assert "Content Quality: PASSED" not in report
    assert "(PASSED)" not in report
    assert "Overall: FAILED" in report
