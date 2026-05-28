import unittest

from data_sources.modules.content_scrubber import ContentScrubber, scrub_content


class ContentScrubberTests(unittest.TestCase):
    def test_scrub_reports_ai_phrase_replacements_after_stats_reset(self):
        scrubber = ContentScrubber()

        cleaned, stats = scrubber.scrub(
            "It is important to note that teams leverage field data."
        )

        self.assertEqual(cleaned, "teams use field data.")
        self.assertEqual(stats["ai_phrases_replaced"], 2)

    def test_verbose_scrub_content_does_not_crash_after_ai_phrase_replacement(self):
        content = (
            "In today's digital landscape, it is important to note that teams "
            "use AI " + chr(8212) + " and field data."
        )

        cleaned = scrub_content(content, verbose=True)

        self.assertIn("teams use AI", cleaned)
        self.assertNotIn("In today's digital landscape", cleaned)

    def test_real_unicode_em_dash_gets_replaced(self):
        cleaned = scrub_content("Dispatch is clean" + chr(8212) + "jobs still move.")

        self.assertNotIn(chr(8212), cleaned)
        self.assertIn("Dispatch is clean", cleaned)
        self.assertIn("jobs still move.", cleaned)

    def test_scrub_output_does_not_introduce_semicolons(self):
        cleaned = scrub_content("Dispatchers can see capacity" + chr(8212) + "teams can assign work.")

        self.assertNotIn(";", cleaned)

    def test_scrub_is_idempotent_after_em_dash_replacement(self):
        once = scrub_content("Dispatch is clean" + chr(8212) + "jobs still move.")
        twice = scrub_content(once)

        self.assertEqual(once, twice)


if __name__ == "__main__":
    unittest.main()
