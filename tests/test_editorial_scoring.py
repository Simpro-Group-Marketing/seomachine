from data_sources.modules.content_scorer import ContentScorer
from data_sources.modules.keyword_analyzer import KeywordAnalyzer
from data_sources.modules.seo_quality_rater import SEOQualityRater


PRIMARY_KEYWORD = "field service workflow"
META_TITLE = "Field Service Workflow Decisions That Matter | Simpro"
META_DESCRIPTION = (
    "A field service workflow guide for operations teams choosing practical ways "
    "to coordinate jobs, reduce rework, and make sound process decisions today."
)


def _article(paragraph_count: int = 6) -> str:
    paragraph = (
        "Field service workflow choices shape how office and field teams share job "
        "status, handle exceptions, assign responsibility, and decide what happens "
        "next. A useful process makes constraints visible, gives each role clear "
        "information, and helps the team respond without restarting the work."
    )
    return (
        "# Field Service Workflow Decisions\n\n"
        "Field service workflow design starts with the decision the team needs to make.\n\n"
        "## Map the decision\n\n"
        + "\n\n".join([paragraph] * paragraph_count)
        + "\n\n## Choose the next step\n\n"
        + paragraph
    )


def _metadata() -> dict[str, str]:
    return {
        "meta_title": META_TITLE,
        "meta_description": META_DESCRIPTION,
        "primary_keyword": PRIMARY_KEYWORD,
    }


def test_complete_short_blog_has_no_word_count_penalty_in_both_scorers():
    short = _article(6)
    long = _article(55)
    very_long = _article(80)

    rater_short = SEOQualityRater().rate(short, **_metadata())
    rater_long = SEOQualityRater().rate(long, **_metadata())
    rater_very_long = SEOQualityRater().rate(very_long, **_metadata())
    scorer_short = ContentScorer()._score_seo(short, _metadata())
    scorer_long = ContentScorer()._score_seo(long, _metadata())

    assert rater_short["details"]["word_count"] < 2000
    assert scorer_short["details"]["word_count"] < 2000
    assert rater_short["category_scores"]["content"] == rater_long["category_scores"]["content"]
    assert rater_long["category_scores"]["content"] == rater_very_long["category_scores"]["content"]
    assert scorer_short["score"] == scorer_long["score"]
    combined = "\n".join(
        rater_short["critical_issues"]
        + rater_short["warnings"]
        + rater_short["suggestions"]
        + [issue["issue"] for issue in scorer_short["issues"]]
    ).lower()
    assert "too short" not in combined
    assert "2,000 words" not in combined
    assert not any(
        "breaking into multiple articles" in item.lower()
        for item in rater_very_long["suggestions"]
    )


def test_low_keyword_density_has_no_recommendation_or_score_penalty():
    content = _article(30)
    low_keyword_content = (
        "# Field Service Workflow\n\n"
        + "Teams coordinate jobs, exceptions, responsibilities, and next steps. " * 250
    )
    keyword_result = KeywordAnalyzer().analyze(low_keyword_content, PRIMARY_KEYWORD)
    no_density = SEOQualityRater().rate(content, **_metadata())
    low_density = SEOQualityRater().rate(content, keyword_density=0.1, **_metadata())

    recommendations = "\n".join(keyword_result["recommendations"]).lower()
    low_findings = "\n".join(
        low_density["critical_issues"]
        + low_density["warnings"]
        + low_density["suggestions"]
    ).lower()
    assert "density is too low" not in recommendations
    assert "density is slightly low" not in recommendations
    assert keyword_result["primary_keyword"]["density"] < 0.5
    assert "density is too low" not in low_findings
    assert low_density["category_scores"]["keyword_optimization"] == no_density["category_scores"]["keyword_optimization"]


def test_h1_and_first_100_word_placement_checks_remain_active():
    content = "Introductory context without the target phrase. " * 30
    result = SEOQualityRater().rate(content, primary_keyword=PRIMARY_KEYWORD)
    findings = "\n".join(result["critical_issues"] + result["warnings"])

    assert "Missing H1" in findings
    assert "first 100 words" in findings


def test_high_keyword_density_still_produces_stuffing_findings():
    content = _article(6)
    keyword_result = KeywordAnalyzer().analyze(
        "# Field Service Workflow\n\n" + (PRIMARY_KEYWORD + ". ") * 80,
        PRIMARY_KEYWORD,
    )
    rater_result = SEOQualityRater().rate(
        content,
        keyword_density=4.0,
        **_metadata(),
    )

    assert keyword_result["keyword_stuffing"]["risk_level"] == "high"
    assert any("stuffing" in item.lower() for item in keyword_result["recommendations"])
    assert any("too high" in item.lower() for item in rater_result["critical_issues"])


def test_word_count_and_density_remain_available_as_diagnostics():
    content = _article(6)
    keyword_result = KeywordAnalyzer().analyze(content, PRIMARY_KEYWORD)
    rater_result = SEOQualityRater().rate(
        content,
        keyword_density=0.4,
        **_metadata(),
    )

    assert isinstance(keyword_result["word_count"], int)
    assert isinstance(keyword_result["primary_keyword"]["density"], float)
    assert isinstance(rater_result["details"]["word_count"], int)
    assert rater_result["details"]["keyword_density"] == 0.4
