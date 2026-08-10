import tempfile
import unittest
from pathlib import Path

from data_sources.modules.publishable_markdown import read_publishable_markdown


class LegacyMetadataBoundaryTests(unittest.TestCase):
    def test_only_contiguous_leading_legacy_metadata_is_removed(self):
        source = """**Meta Title**: Publish title
**Meta Description**: Publish description

# Display title

Body copy.

**Meta Description**: This is public body content and must remain.
"""
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
        source = """# Display title

Opening paragraph.

**Target Keyword**: visible body label
"""
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "article.md"
            path.write_text(source, encoding="utf-8")
            artifact = read_publishable_markdown(path)

        self.assertEqual(artifact.scalar("target_keyword"), "")
        self.assertIn("**Target Keyword**: visible body label", artifact.body)


if __name__ == "__main__":
    unittest.main()