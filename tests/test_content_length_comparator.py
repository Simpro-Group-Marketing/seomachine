import unittest
import socket
from unittest.mock import Mock, patch

from data_sources.modules.content_length_comparator import (
    ContentLengthComparator,
    compare_content_length,
)
from data_sources.modules.public_http import COMPETITOR_CONTENT_POLICY


SERP_RESULTS = [
    {"url": "https://example.com/one", "title": "One", "domain": "example.com"},
    {"url": "https://example.com/two", "title": "Two", "domain": "example.com"},
    {"url": "https://example.com/three", "title": "Three", "domain": "example.com"},
    {"url": "https://example.com/four", "title": "Four", "domain": "example.com"},
]


class StubContentLengthComparator(ContentLengthComparator):
    WORD_COUNTS = {
        "https://example.com/one": 800,
        "https://example.com/two": 1000,
        "https://example.com/three": 1200,
        "https://example.com/four": 1400,
    }

    def fetch_word_count(self, url):
        return self.WORD_COUNTS.get(url)

    def _fetch_word_count(self, url):
        return self.fetch_word_count(url)


class ContentLengthComparatorTests(unittest.TestCase):
    EXPECTED_KEYS = {
        "keyword",
        "competitors_analyzed",
        "observed_word_count",
        "word_target",
        "statistics",
        "competitor_lengths",
        "observed_position",
        "length_context",
        "competitive_analysis",
    }

    def test_unavailable_serp_context_returns_clean_context_shape(self):
        result = StubContentLengthComparator().analyze(
            "field service scheduling",
            observed_word_count=900,
            serp_results=[],
        )

        self.assertEqual(set(result), self.EXPECTED_KEYS)
        self.assertEqual(result["competitors_analyzed"], 0)
        self.assertEqual(result["competitor_lengths"], [])
        self.assertEqual(result["statistics"], {})
        self.assertIsNone(result["observed_position"])
        self.assertEqual(result["length_context"]["status"], "reported")
        self.assertEqual(result["length_context"]["target_source"], "unresolved")
        self.assertNotIn("status", result)
        self.assertNotIn("error", result)

    def test_failed_fetches_return_clean_context_shape_with_caller_target(self):
        result = StubContentLengthComparator().analyze(
            "field service scheduling",
            observed_word_count=900,
            serp_results=[{"url": "https://example.com/missing", "title": "Missing"}],
            word_target=1100,
        )

        self.assertEqual(set(result), self.EXPECTED_KEYS)
        self.assertEqual(result["competitors_analyzed"], 0)
        self.assertEqual(result["competitor_lengths"], [])
        self.assertEqual(result["statistics"], {})
        self.assertEqual(result["word_target"], 1100)
        self.assertEqual(result["length_context"]["target_source"], "caller_supplied")
        self.assertEqual(result["length_context"]["difference_from_target"], -200)
        self.assertIn("Could not fetch competitor content", result["length_context"]["message"])

    def test_fetch_content_disabled_reports_unfetched_context_not_failed_fetch(self):
        result = StubContentLengthComparator().analyze(
            "field service scheduling",
            observed_word_count=900,
            serp_results=SERP_RESULTS,
            fetch_content=False,
        )

        self.assertEqual(result["competitors_analyzed"], 0)
        self.assertIn("Competitor content was not fetched", result["length_context"]["message"])
        self.assertNotIn("Could not fetch competitor content", result["length_context"]["message"])

    def test_zero_competitors_leave_comparison_unresolved(self):
        result = StubContentLengthComparator().analyze(
            "field service scheduling",
            observed_word_count=900,
            serp_results=[],
        )

        self.assertIsNone(result["competitive_analysis"]["comparison"])

    def test_context_only_result_has_no_derived_recommendations_or_gaps(self):
        result = StubContentLengthComparator().analyze(
            "field service scheduling",
            observed_word_count=900,
            serp_results=SERP_RESULTS,
        )

        self.assertEqual(result["observed_word_count"], 900)
        self.assertIsNone(result["word_target"])
        self.assertEqual(result["length_context"]["status"], "reported")
        self.assertEqual(result["length_context"]["target_source"], "unresolved")
        self.assertNotIn("recommendation", result)
        self.assertNotIn("gap_to_median", result["competitive_analysis"])
        self.assertNotIn("gap_to_75th_percentile", result["competitive_analysis"])

    def test_caller_target_is_reported_without_expansion_recommendation(self):
        result = StubContentLengthComparator().analyze(
            "field service scheduling",
            observed_word_count=900,
            serp_results=SERP_RESULTS,
            word_target=1100,
        )

        self.assertEqual(result["word_target"], 1100)
        self.assertEqual(result["length_context"]["target_source"], "caller_supplied")
        self.assertEqual(result["length_context"]["difference_from_target"], -200)
        self.assertNotIn("add 200", result["length_context"]["message"].lower())

    def test_public_fetch_method_exists(self):
        self.assertTrue(callable(ContentLengthComparator().fetch_word_count))
        self.assertTrue(callable(ContentLengthComparator().fetch_content_context))

    def test_public_content_context_uses_injected_transport(self):
        transport = Mock()
        response = Mock()
        response.content = b"<html><body><main><h2>Observed heading</h2><p>Observed page words.</p></main></body></html>"
        response.raise_for_status.return_value = None
        transport.request.return_value = response

        context = ContentLengthComparator(transport=transport).fetch_content_context(
            "https://example.com/guide"
        )

        self.assertGreater(context["word_count"], 0)
        transport.request.assert_called_once_with(
            "GET",
            "https://example.com/guide",
            headers=ContentLengthComparator(transport=transport).headers,
            policy=COMPETITOR_CONTENT_POLICY,
        )

    @patch("data_sources.modules.content_length_comparator.request_public_url")
    def test_public_content_context_fetches_word_count_and_h2_headings_once(self, request):
        response = Mock()
        response.content = b"""
            <html><body><article>
              <h2>Plan the dispatch rules</h2>
              <p>Field service teams coordinate urgent work and technician skills.</p>
              <h2>Review scheduling exceptions</h2>
              <p>Dispatchers review constraints before changing the schedule.</p>
            </article></body></html>
        """
        response.raise_for_status.return_value = None
        request.return_value = response

        context = ContentLengthComparator().fetch_content_context(
            "https://example.com/guide"
        )

        self.assertEqual(
            context["h2_headings"],
            ["Plan the dispatch rules", "Review scheduling exceptions"],
        )
        self.assertGreater(context["word_count"], 0)
        request.assert_called_once()

    def test_public_content_context_blocks_private_destination(self):
        def resolver(host, port, *, type=socket.SOCK_STREAM):
            return [(socket.AF_INET, type, 6, "", ("10.0.0.8", port))]

        context = ContentLengthComparator(resolver=resolver).fetch_content_context(
            "http://internal.example/report"
        )

        self.assertIsNone(context["word_count"])
        self.assertEqual(context["h2_headings"], [])

    def test_observed_position_never_uses_zero_based_competitor_label(self):
        result = StubContentLengthComparator().analyze(
            "field service scheduling",
            observed_word_count=800,
            serp_results=SERP_RESULTS,
        )

        self.assertNotIn("position 0", result["observed_position"])

    def test_clean_break_wrapper_uses_observed_word_count_name(self):
        with self.assertRaises(TypeError):
            compare_content_length(
                "field service scheduling",
                your_word_count=900,
                serp_results=SERP_RESULTS,
                fetch_content=False,
            )

    def test_invalid_observed_count_or_target_is_rejected(self):
        comparator = StubContentLengthComparator()
        for value in [-1, True, 2.5]:
            with self.subTest(observed_word_count=value):
                with self.assertRaisesRegex(ValueError, "observed_word_count"):
                    comparator.analyze(
                        "field service scheduling",
                        observed_word_count=value,
                        serp_results=SERP_RESULTS,
                    )

        for value in [0, -1, True, 2.5]:
            with self.subTest(word_target=value):
                with self.assertRaisesRegex(ValueError, "word_target"):
                    comparator.analyze(
                        "field service scheduling",
                        observed_word_count=900,
                        serp_results=SERP_RESULTS,
                        word_target=value,
                    )

    def test_malformed_fetch_flag_or_serp_results_are_rejected(self):
        comparator = StubContentLengthComparator()

        with self.assertRaisesRegex(ValueError, "fetch_content"):
            comparator.analyze(
                "field service scheduling",
                serp_results=SERP_RESULTS,
                fetch_content="false",
            )

        for serp_results in ["not a list", [{"title": "Missing URL"}], [42]]:
            with self.subTest(serp_results=serp_results):
                with self.assertRaisesRegex(ValueError, "serp_results"):
                    comparator.analyze(
                        "field service scheduling",
                        serp_results=serp_results,
                    )

    def test_keyword_must_be_non_empty(self):
        comparator = StubContentLengthComparator()

        for keyword in ["", "   ", None]:
            with self.subTest(keyword=keyword):
                with self.assertRaisesRegex(ValueError, "keyword"):
                    comparator.analyze(keyword, serp_results=SERP_RESULTS)

    def test_null_optional_serp_metadata_is_normalized(self):
        result = StubContentLengthComparator().analyze(
            "field service scheduling",
            serp_results=[
                {
                    "url": "https://example.com/one",
                    "title": None,
                    "domain": None,
                }
            ],
        )

        self.assertEqual(result["competitor_lengths"][0]["title"], "")
        self.assertEqual(result["competitor_lengths"][0]["domain"], "")


if __name__ == "__main__":
    unittest.main()
