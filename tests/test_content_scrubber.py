import unittest

from data_sources.modules.content_scrubber import ContentScrubber, scrub_content


class ContentScrubberTests(unittest.TestCase):
    def test_scrub_preserves_standalone_original_hero_image_placeholder_exactly(self):
        marker = (
            '[IMAGE PLACEHOLDER — ORIGINAL HERO: retain immediately before the '
            'introduction | source: '
            'https://www.simprogroup.com/images/2/9/6/5/f/'
            '2965fceb5942ff039f447cff8ce3cd7aee49b2f9-'
            'simpro-best-trades-for-women.jpg | alt: '
            '"Woman smiling in navy work overalls" | render target: '
            '819 × 461 px; resize and compress before upload]'
        )

        self.assertEqual(scrub_content(marker), marker)

    def test_scrub_placeholder_restoration_does_not_collide_after_zero_width_cleanup(self):
        marker = (
            '[IMAGE PLACEHOLDER — ORIGINAL HERO: retain immediately before the '
            'introduction | source: https://example.com/hero.jpg | '
            'alt: "Woman smiling in navy work overalls" | render target: '
            '819 × 461 px; resize and compress before upload]'
        )
        near_token = "SCRUBBERPROTECTEDIMAGEPLACEHOLDER0\u200bTOKEN"
        content = f"{near_token}\r\n{marker}\r\nTail"

        cleaned = scrub_content(content)

        self.assertEqual(
            cleaned,
            "SCRUBBERPROTECTEDIMAGEPLACEHOLDER0TOKEN\r\n"
            f"{marker}\r\nTail",
        )
        self.assertEqual(cleaned.count(marker), 1)

    def test_scrub_collision_check_models_cleanup_for_current_private_token(self):
        marker = (
            '[IMAGE PLACEHOLDER — ORIGINAL HERO: retain immediately before the '
            'introduction | source: https://example.com/hero.jpg | '
            'alt: "Woman smiling in navy work overalls" | render target: '
            '819 × 461 px; resize and compress before upload]'
        )
        near_token = "\ue000SCRUBBERIMAGEPLACEHOLDER0\u200b\ue001"
        content = f"{near_token}\n{marker}\nTail"

        cleaned = scrub_content(content)

        self.assertEqual(
            cleaned,
            "\ue000SCRUBBERIMAGEPLACEHOLDER0\ue001\n"
            f"{marker}\nTail",
        )
        self.assertEqual(cleaned.count(marker), 1)

    def test_scrub_placeholder_protection_cannot_collide_after_ai_phrase_cleanup(self):
        marker = (
            '[IMAGE PLACEHOLDER — ORIGINAL HERO: retain immediately before the '
            'introduction | source: https://example.com/hero.jpg | '
            'alt: "Woman smiling in navy work overalls" | render target: '
            '819 × 461 px; resize and compress before upload]'
        )
        near_token = (
            "\ue000SCRUBBERIt is important to note that "
            "IMAGEPLACEHOLDER0\ue001"
        )
        content = f"{near_token}\n{marker}\nTail"

        cleaned = scrub_content(content)

        self.assertEqual(
            cleaned,
            "\ue000SCRUBBERIMAGEPLACEHOLDER0\ue001\n"
            f"{marker}\nTail",
        )
        self.assertEqual(cleaned.count(marker), 1)

    def test_scrub_still_replaces_em_dash_in_prose_and_leaves_semicolon_for_lint(self):
        cleaned = scrub_content(
            "The production note uses an em dash — in prose; editors must revise it."
        )

        self.assertNotIn("—", cleaned)
        self.assertIn(";", cleaned)

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

    def test_scrub_preserves_us_abbreviation(self):
        cleaned = scrub_content(
            "U.S. consumers use mobile payments. U.S. businesses track payment speed."
        )

        self.assertIn("U.S. consumers", cleaned)
        self.assertIn("U.S. businesses", cleaned)
        self.assertNotIn("U. S.", cleaned)

    def test_scrub_is_idempotent_after_em_dash_replacement(self):
        once = scrub_content("Dispatch is clean" + chr(8212) + "jobs still move.")
        twice = scrub_content(once)

        self.assertEqual(once, twice)


if __name__ == "__main__":
    unittest.main()
