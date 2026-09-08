from tests.fixture_text import fixture_text

import tempfile
import unittest
from pathlib import Path

from data_sources.modules.publishable_markdown import read_publishable_markdown


class LegacyMetadataBoundaryTests(unittest.TestCase):
    def test_only_contiguous_leading_legacy_metadata_is_removed(self):
        source = fixture_text("content_evidence:test_publishable_markdown-10-1")
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "article.md"
            path.write_text(source, encoding="utf-8")
            artifact = read_publishable_markdown(path)

        self.assertEqual(artifact.scalar("meta_title"), "Publish title")
        self.assertEqual(artifact.scalar("meta_description"), "Publish description")
        self.assertNotIn("**Meta Title**: Publish title", artifact.body)
        self.assertIn(
            "**Meta Description**: This is public body content and must remain.",
            artifact.body,
        )

    def test_legacy_metadata_after_public_content_is_not_promoted(self):
        source = fixture_text("content_evidence:test_publishable_markdown-33-2")
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "article.md"
            path.write_text(source, encoding="utf-8")
            artifact = read_publishable_markdown(path)

        self.assertEqual(artifact.scalar("target_keyword"), "")
        self.assertIn("**Target Keyword**: visible body label", artifact.body)


if __name__ == "__main__":
    unittest.main()