import hashlib
import json
import tempfile
import unittest
from contextlib import redirect_stderr
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from data_sources.modules import content_scrubber as content_scrubber_module
from data_sources.modules.content_scrubber import (
    ContentScrubber,
    main,
    scrub_content,
    scrub_file,
)
from data_sources.modules.blog_assembly_stage_receipt import StageReceiptError


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

    def test_scrub_preserves_blank_lines_around_original_image_placeholder(self):
        marker = (
            "![Close up of hand holding broken phone with person in yellow shirt "
            "in background](IMAGE_PLACEHOLDER_ORIGINAL_PHONE)"
        )
        content = (
            "The job details should stay readable.\n\n"
            f"{marker}\n\n"
            "Technicians need the next paragraph on its own line."
        )

        self.assertEqual(scrub_content(content), content)

    def test_scrub_preserves_blank_lines_around_markdown_image_url(self):
        marker = (
            "![Prevent employee time theft with GPS time tracking]"
            "(https://www.datocms-assets.com/16247/time-theft.png)"
        )
        content = (
            "| Review cue | Use it for |\n"
            "|---|---|\n"
            "| Decision | Mark the entry before payroll. |\n\n"
            f"{marker}\n\n"
            "Technicians need the next paragraph on its own line."
        )

        self.assertEqual(scrub_content(content), content)

    def test_scrub_preserves_yaml_and_json_ld_indentation(self):
        content = """---
secondary_keywords:
  - plumbing software
  - plumbing scheduling software
---

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "author": {
    "@type": "Organization",
    "name": "Simpro"
  }
}
</script>
"""

        self.assertEqual(scrub_content(content), content)

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

    def test_stage_receipt_cli_records_real_hashes_and_previous_link(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as tmp:
            root = Path(tmp)
            article = root / 'article.md'
            first_receipt_path = root / 'scrub.json'
            article.write_text('Dispatch work.', encoding='utf-8')
            before = hashlib.sha256(article.read_bytes()).hexdigest()
            first = scrub_file(
                str(article),
                stage_receipt_output=str(first_receipt_path),
                run_id='run-42',
            )
            after = hashlib.sha256(article.read_bytes()).hexdigest()

            self.assertEqual(first['input_artifact_hashes'], {'article': before})
            self.assertEqual(first['output_artifact_hashes'], {'article': after})
            self.assertEqual(first['tool'], {'name': 'content_scrubber', 'version': '1.0.0'})
            self.assertEqual(after, before)
            self.assertFalse(first['mutation'])
            self.assertEqual(set(first['evidence_hashes']), {'scrub_statistics'})
            self.assertEqual(len(first['evidence_hashes']['scrub_statistics']), 64)
            article.write_text('Schedule work.', encoding='utf-8')
            second_receipt_path = root / 'post-scrub.json'
            exit_code = main(
                [
                    str(article),
                    '--stage-receipt-output', str(second_receipt_path),
                    '--previous-receipt', str(first_receipt_path),
                    '--stage', 'post_optimization_scrub',
                ]
            )
            second = json.loads(second_receipt_path.read_text(encoding='utf-8'))

            self.assertEqual(exit_code, 0)
            self.assertEqual(second['run_id'], 'run-42')
            self.assertEqual(second['stage'], 'post_optimization_scrub')
            self.assertEqual(second['previous_receipt_hash'], first['receipt_hash'])

    def test_invalid_previous_receipt_never_mutates_article(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as tmp:
            root = Path(tmp)
            article = root / 'article.md'
            previous = root / 'invalid-previous.json'
            article.write_text('Dispatch' + chr(8212) + 'work.', encoding='utf-8')
            previous.write_text('not json', encoding='utf-8')
            before = article.read_bytes()

            with self.assertRaises(StageReceiptError):
                scrub_file(
                    str(article),
                    stage_receipt_output=str(root / 'scrub.json'),
                    previous_receipt=str(previous),
                )

            self.assertEqual(article.read_bytes(), before)

    def test_receipt_output_cannot_overwrite_article(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as tmp:
            article = Path(tmp) / 'article.md'
            article.write_text('Dispatch' + chr(8212) + 'work.', encoding='utf-8')
            before = article.read_bytes()

            with self.assertRaises(StageReceiptError):
                scrub_file(
                    str(article),
                    stage_receipt_output=str(article),
                    run_id='run-42',
                )

            self.assertEqual(article.read_bytes(), before)

    def test_default_scrub_file_reports_without_article_replace(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as tmp:
            root = Path(tmp)
            article = root / 'article.md'
            article.write_text('Dispatch' + chr(8212) + 'work.', encoding='utf-8')
            before_bytes = article.read_bytes()
            before_files = set(root.iterdir())

            with patch(
                'data_sources.modules.content_scrubber.os.replace',
                side_effect=OSError('replace blocked'),
            ):
                report = scrub_file(str(article))

            self.assertEqual(article.read_bytes(), before_bytes)
            self.assertEqual(set(root.iterdir()), before_files)
            self.assertTrue(report['would_change'])
            self.assertEqual(report['statistics']['emdashes_replaced'], 1)

    def test_receipt_write_failure_rolls_back_in_place_article(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as tmp:
            root = Path(tmp)
            article = root / 'article.md'
            receipt = root / 'scrub-receipt.json'
            article.write_text('Dispatch work.', encoding='utf-8')
            before_bytes = article.read_bytes()

            with patch.object(
                content_scrubber_module,
                'write_stage_receipt',
                side_effect=OSError('receipt write failed'),
            ):
                with self.assertRaisesRegex(OSError, 'receipt write failed'):
                    scrub_file(
                        str(article),
                        stage_receipt_output=str(receipt),
                        run_id='run-rollback',
                    )

            self.assertEqual(article.read_bytes(), before_bytes)
            self.assertFalse(receipt.exists())

    def test_receipt_completion_is_captured_without_article_output_write(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as tmp:
            root = Path(tmp)
            article = root / 'article.md'
            receipt = root / 'scrub-receipt.json'
            article.write_text('Dispatch work.', encoding='utf-8')
            real_builder = content_scrubber_module.build_stage_receipt

            def build_after_output(**kwargs):
                self.assertEqual('Dispatch work.', article.read_text(encoding='utf-8'))
                self.assertFalse(kwargs['mutation'])
                self.assertEqual(kwargs['input_artifact_hashes'], kwargs['output_artifact_hashes'])
                return real_builder(**kwargs)

            with patch.object(
                content_scrubber_module,
                'build_stage_receipt',
                side_effect=build_after_output,
            ):
                scrub_file(
                    str(article),
                    stage_receipt_output=str(receipt),
                    run_id='run-completion-order',
                )

            self.assertTrue(receipt.is_file())

    def test_cli_reports_expected_input_errors_without_traceback(self):
        stderr = StringIO()

        with redirect_stderr(stderr), self.assertRaises(SystemExit) as raised:
            main(['missing-article.md'])

        self.assertEqual(raised.exception.code, 2)
        self.assertIn('error:', stderr.getvalue())
        self.assertNotIn('Traceback', stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
