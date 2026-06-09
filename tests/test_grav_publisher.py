import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from data_sources.modules.grav_publisher import GravPublishError, GravPublisher
from data_sources.modules.url_validator import UrlValidationResult, UrlValidationSummary


DRAFT_WITH_SLUG = """---
Meta Title: Payments for Trades Businesses and Faster Cash Flow
Meta Description: Improve payments for trades businesses with clear invoices and flexible options.
Primary Keyword: payments for trades businesses
Secondary Keywords: field service payments, embedded payments, faster field service payments
Author: Simpro
Last Updated: 2026-05-28
URL Slug: /blog/modern-customer-payment-expectations-trades
---

# Payments for Trades Businesses: Meeting Modern Customer Expectations

Payments for trades businesses are the invoice, collection, and reconciliation workflows.

## Why it matters

The payment step now shapes the service experience too.
"""


def _write(tmpdir: str, name: str, content: str) -> str:
    path = Path(tmpdir) / name
    path.write_text(content, encoding="utf-8")
    return str(path)


class ParseTests(unittest.TestCase):
    def setUp(self):
        self.pub = GravPublisher(repo="owner/repo", branch="dev", blog_path="blogs", lang="en")

    def test_parses_frontmatter_fields(self):
        with tempfile.TemporaryDirectory() as tmp:
            draft = self.pub.parse_draft_file(_write(tmp, "post.md", DRAFT_WITH_SLUG))

        self.assertEqual(draft["meta_title"], "Payments for Trades Businesses and Faster Cash Flow")
        self.assertEqual(draft["primary_keyword"], "payments for trades businesses")
        self.assertEqual(draft["author"], "Simpro")
        self.assertEqual(draft["last_updated"], "2026-05-28")

    def test_title_prefers_meta_title(self):
        with tempfile.TemporaryDirectory() as tmp:
            draft = self.pub.parse_draft_file(_write(tmp, "post.md", DRAFT_WITH_SLUG))
        self.assertEqual(draft["title"], "Payments for Trades Businesses and Faster Cash Flow")

    def test_body_strips_frontmatter_and_leading_h1(self):
        with tempfile.TemporaryDirectory() as tmp:
            draft = self.pub.parse_draft_file(_write(tmp, "post.md", DRAFT_WITH_SLUG))
        body = draft["content"]
        self.assertFalse(body.startswith("---"))
        self.assertNotIn("Meta Title:", body)
        self.assertNotIn("# Payments for Trades Businesses:", body)
        self.assertTrue(body.startswith("Payments for trades businesses are the invoice"))
        # Subheadings inside the body are preserved.
        self.assertIn("## Why it matters", body)


class SlugTests(unittest.TestCase):
    def setUp(self):
        self.pub = GravPublisher(repo="owner/repo")

    def test_slug_from_url_slug_field(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = _write(tmp, "some-random-filename-2026.md", DRAFT_WITH_SLUG)
            draft = self.pub.parse_draft_file(path)
        self.assertEqual(draft["slug"], "modern-customer-payment-expectations-trades")

    def test_slug_falls_back_to_filename(self):
        no_slug = DRAFT_WITH_SLUG.replace(
            "URL Slug: /blog/modern-customer-payment-expectations-trades\n", ""
        )
        with tempfile.TemporaryDirectory() as tmp:
            path = _write(tmp, "How To Price HVAC Jobs.md", no_slug)
            draft = self.pub.parse_draft_file(path)
        self.assertEqual(draft["slug"], "how-to-price-hvac-jobs")

    def test_slug_falls_back_to_h1_when_no_slug_or_filename(self):
        no_slug = DRAFT_WITH_SLUG.replace(
            "URL Slug: /blog/modern-customer-payment-expectations-trades\n", ""
        )
        with tempfile.TemporaryDirectory() as tmp:
            # Filename of only punctuation slugifies to empty -> fall back to H1.
            path = _write(tmp, "___.md", no_slug)
            draft = self.pub.parse_draft_file(path)
        self.assertEqual(
            draft["slug"], "payments-for-trades-businesses-meeting-modern-customer-expectations"
        )


class FrontmatterTests(unittest.TestCase):
    def setUp(self):
        self.pub = GravPublisher(repo="owner/repo", blog_path="blogs", lang="en")

    def _draft(self, tmp):
        return self.pub.parse_draft_file(_write(tmp, "post.md", DRAFT_WITH_SLUG))

    def test_frontmatter_contains_grav_fields(self):
        with tempfile.TemporaryDirectory() as tmp:
            fm = self.pub.build_grav_frontmatter(self._draft(tmp))

        self.assertTrue(fm.startswith("---"))
        self.assertTrue(fm.endswith("---"))
        self.assertIn("title: 'Payments for Trades Businesses and Faster Cash Flow'", fm)
        self.assertIn("date: '2026-05-28 00:00'", fm)
        self.assertIn("taxonomy:", fm)
        self.assertIn("        - blog", fm)
        self.assertIn("        - 'field service payments'", fm)
        self.assertIn("    description: 'Improve payments", fm)
        self.assertIn("    keywords: 'payments for trades businesses, field service payments", fm)
        self.assertIn("author: 'Simpro'", fm)
        self.assertIn("published: true", fm)

    def test_yaml_quote_escapes_single_quotes(self):
        self.assertEqual(self.pub._yaml_quote("don't"), "'don''t'")

    def test_article_path_uses_blog_path_slug_and_lang(self):
        self.assertEqual(
            self.pub.article_repo_path("my-post"), "blogs/my-post/article.en.md"
        )

    def test_build_article_combines_frontmatter_and_body(self):
        with tempfile.TemporaryDirectory() as tmp:
            draft = self._draft(tmp)
            article = self.pub.build_article(draft)
        self.assertIn("---\ntitle:", article)
        self.assertIn("Payments for trades businesses are the invoice", article)


class PublishPreflightTests(unittest.TestCase):
    def setUp(self):
        self.pub = GravPublisher(repo="owner/repo", branch="dev", blog_path="blogs", lang="en")

    def test_publish_stops_before_push_when_url_validation_fails(self):
        blocked = UrlValidationResult(
            url="https://example.com/dead",
            status="unresolved",
            status_code=404,
            reason="HTTP 404",
            line=15,
            anchor="dead source",
        )

        with tempfile.TemporaryDirectory() as tmp:
            path = _write(tmp, "post.md", DRAFT_WITH_SLUG)
            with patch(
                "data_sources.modules.grav_publisher.validate_file_urls",
                return_value=UrlValidationSummary([blocked]),
            ), patch.object(self.pub, "push_article") as push_article:
                with self.assertRaises(GravPublishError) as raised:
                    self.pub.publish(path, dry_run=False)

        push_article.assert_not_called()
        self.assertIn("URL validation failed", str(raised.exception))
        self.assertIn("https://example.com/dead", str(raised.exception))

    def test_publish_stops_before_push_when_source_support_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = _write(tmp, "post.md", DRAFT_WITH_SLUG)
            with patch(
                "data_sources.modules.grav_publisher.validate_file_urls",
                return_value=UrlValidationSummary([]),
            ), patch(
                "data_sources.modules.grav_publisher.require_source_support",
                side_effect=GravPublishError("Source support validation failed before Grav publish"),
            ), patch.object(self.pub, "push_article") as push_article:
                with self.assertRaises(GravPublishError) as raised:
                    self.pub.publish(path, dry_run=False)

        push_article.assert_not_called()
        self.assertIn("Source support validation failed", str(raised.exception))


if __name__ == "__main__":
    unittest.main()
