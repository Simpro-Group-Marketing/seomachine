from pathlib import Path

import pytest

from data_sources.modules.engagement_analyzer import EngagementAnalyzer


ROOT = Path(__file__).resolve().parents[1]


def _article_with_ctas(*, early: bool, late: bool, word_count: int = 700) -> str:
    words = ["workflow"] * word_count
    if early:
        words[40:42] = ["Learn", "more"]
    if late:
        words[int(word_count * 0.8):int(word_count * 0.8) + 5] = [
            "Start",
            "a",
            "free",
            "trial",
            "today",
        ]
    return " ".join(words)


@pytest.mark.parametrize("profile", ["tofu", "thought_leadership"])
def test_one_reader_value_next_step_meets_early_stage_profiles(profile):
    result = EngagementAnalyzer().analyze("A useful opening. Learn more", cta_profile=profile)

    assert result["ctas"]["profile"] == profile
    assert result["ctas"]["required_min"] == 1
    assert result["ctas"]["requires_distribution"] is False
    assert result["ctas"]["requires_early_cta"] is False
    assert result["ctas"]["meets_profile"] is True
    assert result["scores"]["ctas"] is True


def test_mofu_requires_two_distributed_ctas():
    one_cta = EngagementAnalyzer().analyze(
        _article_with_ctas(early=True, late=False), cta_profile="mofu"
    )
    distributed = EngagementAnalyzer().analyze(
        _article_with_ctas(early=True, late=True), cta_profile="mofu"
    )

    assert one_cta["ctas"]["required_min"] == 2
    assert one_cta["ctas"]["requires_distribution"] is True
    assert one_cta["ctas"]["meets_profile"] is False
    assert distributed["ctas"]["meets_profile"] is True


def test_bofu_requires_distribution_and_cta_within_500_words():
    late_content = " ".join(["workflow"] * 550 + ["Learn", "more"] + ["detail"] * 150 + ["Start", "a", "free", "trial", "today"])
    late = EngagementAnalyzer().analyze(late_content, cta_profile="bofu")
    passing = EngagementAnalyzer().analyze(
        _article_with_ctas(early=True, late=True), cta_profile="bofu"
    )

    assert late["ctas"]["requires_early_cta"] is True
    assert late["ctas"]["within_500_words"] is False
    assert late["ctas"]["meets_profile"] is False
    assert passing["ctas"]["within_500_words"] is True
    assert passing["ctas"]["meets_profile"] is True


def test_unknown_cta_profile_fails_closed():
    with pytest.raises(ValueError, match=r"^Unsupported CTA profile: enterprise$"):
        EngagementAnalyzer().analyze("Learn more", cta_profile="enterprise")


def test_default_calls_retain_mofu_behavior():
    result = EngagementAnalyzer().analyze("A useful opening. Learn more")

    assert result["ctas"]["profile"] == "mofu"
    assert result["ctas"]["required_min"] == 2
    assert result["ctas"]["meets_profile"] is False


def test_named_people_and_fabricated_story_patterns_are_not_engagement_criteria():
    source = (ROOT / "data_sources" / "modules" / "engagement_analyzer.py").read_text(
        encoding="utf-8"
    )
    result = EngagementAnalyzer().analyze(
        "Sarah launched a business in 2024 and saved 40 percent. Learn more",
        cta_profile="tofu",
    )

    assert "NAME_PATTERNS" not in source
    assert "_analyze_mini_stories" not in source
    assert "stories" not in result

