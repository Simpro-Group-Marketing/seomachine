import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from data_sources.modules.url_validator import UrlValidationResult, UrlValidationSummary
from data_sources.modules.wordpress_publisher import WordPressPublisher


DRAFT = """# Example Draft

**Meta Title**: Example Draft for WordPress Publishing
**Meta Description**: Example draft description for publisher preflight tests.
**Target Keyword**: example draft
**URL Slug**: /blog/example-draft

This draft cites [a dead source](https://example.com/dead).
"""


class WordPressPublisherPreflightTests(unittest.TestCase):
    def test_publish_stops_before_api_calls_when_url_validation_fails(self):
        blocked = UrlValidationResult(
            url="https://example.com/dead",
            status="unresolved",
            status_code=404,
            reason="HTTP 404",
            line=8,
            anchor="dead source",
        )
        publisher = WordPressPublisher(
            url="https://wordpress.example",
            username="editor",
            app_password="password",
        )

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "draft.md"
            path.write_text(DRAFT, encoding="utf-8")

            with patch(
                "data_sources.modules.wordpress_publisher.validate_file_urls",
                return_value=UrlValidationSummary([blocked]),
            ), patch.object(publisher, "create_draft") as create_draft:
                with self.assertRaises(ValueError) as raised:
                    publisher.publish_draft(str(path))

        create_draft.assert_not_called()
        self.assertIn("URL validation failed", str(raised.exception))
        self.assertIn("https://example.com/dead", str(raised.exception))

    def test_publish_stops_before_api_calls_when_source_support_fails(self):
        publisher = WordPressPublisher(
            url="https://wordpress.example",
            username="editor",
            app_password="password",
        )

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "draft.md"
            path.write_text(DRAFT, encoding="utf-8")

            with patch(
                "data_sources.modules.wordpress_publisher.validate_file_urls",
                return_value=UrlValidationSummary([]),
            ), patch(
                "data_sources.modules.wordpress_publisher.require_source_support",
                side_effect=ValueError("Source support validation failed before WordPress publish"),
            ), patch.object(publisher, "create_draft") as create_draft:
                with self.assertRaises(ValueError) as raised:
                    publisher.publish_draft(str(path))

        create_draft.assert_not_called()
        self.assertIn("Source support validation failed", str(raised.exception))


if __name__ == "__main__":
    unittest.main()
