from dataclasses import replace
from unittest.mock import Mock, patch

from data_sources.modules.content_scorer import ContentScorer
from data_sources.modules.content_scoring.common import default_scoring_dependencies


def _passing_dependencies():
    return replace(
        default_scoring_dependencies(),
        rate_aeo_geo=Mock(
            return_value={
                "score": 100,
                "passed": True,
                "threshold": 90,
                "checks": {
                    "faq_proof": {
                        "passed": True,
                        "details": {"finding_count": 0, "findings": []},
                    },
                    "paa_provenance": {
                        "passed": True,
                        "details": {"finding_count": 0, "findings": []},
                    },
                },
                "issues": [],
            }
        ),
        check_metric_proof_pack=Mock(return_value=[]),
        check_customer_proof_diversity=Mock(return_value=[]),
        check_review_story_identity=Mock(return_value=[]),
    )


def _content(total_visible_words: int) -> str:
    heading_words = 3
    body_words = total_visible_words - heading_words
    return "# Field Service Workflow\n\n" + " ".join(
        f"word{index}" for index in range(body_words)
    )


def _score_with_perfect_dimensions(total_visible_words: int) -> dict:
    scorer = ContentScorer(_passing_dependencies())
    with patch.object(
        ContentScorer,
        "_score_humanity",
        return_value={"score": 100, "issues": [], "details": {}},
    ), patch.object(
        ContentScorer,
        "_score_specificity",
        return_value={"score": 100, "issues": [], "details": {}},
    ), patch.object(
        ContentScorer,
        "_score_structure_balance",
        return_value={"score": 100, "issues": [], "details": {}, "prose_ratio": 0.65},
    ), patch.object(
        ContentScorer,
        "_score_seo",
        return_value={"score": 100, "passed": True, "issues": [], "details": {}},
    ), patch.object(
        ContentScorer,
        "_score_readability",
        return_value={"score": 100, "issues": [], "details": {}, "flesch": 68},
    ):
        return scorer.score(
            _content(total_visible_words),
            {"primary_keyword": "field service workflow"},
        )


def test_sub_150_word_articles_fail_even_with_perfect_dimension_scores():
    for total_visible_words in (93, 149):
        result = _score_with_perfect_dimensions(total_visible_words)

        assert result["composite_score"] == 100
        assert not result["passed"]
        assert result["quality_gates"]["minimum_visible_words"] == {
            "word_count": total_visible_words,
            "threshold": 150,
            "passed": False,
        }
        assert result["priority_fixes"][0]["dimension"] == "minimum_visible_words"


def test_150_visible_words_satisfies_the_release_floor():
    result = _score_with_perfect_dimensions(150)

    assert result["passed"]
    assert result["quality_gates"]["minimum_visible_words"] == {
        "word_count": 150,
        "threshold": 150,
        "passed": True,
    }
