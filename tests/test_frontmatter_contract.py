import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from data_sources.modules.artifact_detection import (
    extract_frontmatter,
    strip_frontmatter,
)
from data_sources.modules.grav_publisher import GravPublisher
from data_sources.modules.publish_readiness import run_publish_readiness
from data_sources.modules.publishable_markdown import (
    FrontmatterError,
    read_publishable_markdown,
)
from data_sources.modules.wordpress_publisher import WordPressPublisher


VALID_COMPLEX_FRONTMATTER = """---
brand: Simpro
artifact_type: blog
artifact_kind: article
tags: ['field service', 'job management']
schema_notes: |-
  BlogPosting
  FAQPage
---
# Valid draft

Body copy.
"""


class StrictFrontmatterContractTests(unittest.TestCase):
    def test_valid_yaml_lists_and_block_scalars_have_canonical_values(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "draft.md"
            path.write_text(VALID_COMPLEX_FRONTMATTER, encoding="utf-8")

            artifact = read_publishable_markdown(path)
            guard_metadata = extract_frontmatter(VALID_COMPLEX_FRONTMATTER)
            body, body_line = strip_frontmatter(VALID_COMPLEX_FRONTMATTER)

        self.assertEqual(artifact.metadata["tags"], ["field service", "job management"])
        self.assertEqual(artifact.metadata["schema_notes"], "BlogPosting\nFAQPage")
        self.assertEqual(guard_metadata["tags"], "field service, job management")
        self.assertEqual(guard_metadata["schema_notes"], "BlogPosting\nFAQPage")
        self.assertEqual(body_line, 10)
        self.assertTrue(body.startswith("# Valid draft"))

    def test_duplicate_or_conflicting_identity_metadata_is_rejected(self):
        invalid_documents = {
            "duplicate brand": "---\nbrand: Simpro\nbrand: BigChange\n---\nBody\n",
            "normalized duplicate type": (
                "---\nartifact-type: blog\nartifact_type: landing_page\n---\nBody\n"
            ),
            "conflicting type fields": (
                "---\nartifact_type: blog\nartifact_kind: landing_page\n---\nBody\n"
            ),
        }
        for label, content in invalid_documents.items():
            with self.subTest(label=label), self.assertRaises(FrontmatterError):
                extract_frontmatter(content)

    def test_malformed_or_nested_frontmatter_is_rejected(self):
        invalid_documents = {
            "malformed indentation": (
                "---\nbrand: Simpro\n  artifact_type: landing_page\n---\nBody\n"
            ),
            "nested object": (
                "---\nbrand: Simpro\nauthor:\n  name: Editor\n---\nBody\n"
            ),
            "nested list": (
                "---\nbrand: Simpro\ntags:\n  - [one, two]\n---\nBody\n"
            ),
            "unterminated": "---\nbrand: Simpro\nBody\n",
        }
        for label, content in invalid_documents.items():
            with self.subTest(label=label), self.assertRaises(FrontmatterError):
                extract_frontmatter(content)

    def test_publishers_and_guard_reject_the_same_invalid_frontmatter(self):
        invalid_documents = {
            "duplicate": "---\nbrand: Simpro\nbrand: BigChange\n---\n# Draft\n\nBody.\n",
            "conflict": (
                "---\nartifact_type: blog\nartifact_kind: landing_page\n---\nBody\n"
            ),
            "malformed": (
                "---\nbrand: Simpro\n  artifact_type: landing_page\n---\nBody\n"
            ),
            "object": "---\nbrand: Simpro\nauthor:\n  name: Editor\n---\nBody\n",
        }
        wordpress = WordPressPublisher(
            url="https://wordpress.example",
            username="editor",
            app_password="password",
        )
        grav = GravPublisher(repo="owner/repo")
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "draft.md"
            for label, content in invalid_documents.items():
                path.write_text(content, encoding="utf-8")
                operations = (
                    lambda: extract_frontmatter(content),
                    lambda: wordpress.parse_draft_file(str(path)),
                    lambda: grav.parse_draft_file(str(path)),
                )
                for operation in operations:
                    with (
                        self.subTest(label=label, operation=operation),
                        self.assertRaises(FrontmatterError),
                    ):
                        operation()

    def test_publish_operations_stop_before_readiness_or_external_write(self):
        content = "---\nbrand: Simpro\nbrand: BigChange\n---\n# Draft\n\nBody.\n"
        wordpress = WordPressPublisher(
            url="https://wordpress.example",
            username="editor",
            app_password="password",
        )
        grav = GravPublisher(repo="owner/repo")
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "draft.md"
            preview_root = Path(tmp) / "preview"
            path.write_text(content, encoding="utf-8")
            grav.preview_root = preview_root
            with (
                patch(
                    "data_sources.modules.wordpress_publisher.run_publish_readiness"
                ) as wordpress_readiness,
                patch.object(wordpress, "create_draft") as create_draft,
                patch(
                    "data_sources.modules.grav_publisher.run_publish_readiness"
                ) as grav_readiness,
            ):
                with self.assertRaises(FrontmatterError):
                    wordpress.publish_draft(str(path))
                with self.assertRaises(FrontmatterError):
                    grav.publish(str(path), dry_run=True)

        wordpress_readiness.assert_not_called()
        grav_readiness.assert_not_called()
        create_draft.assert_not_called()
        self.assertFalse(preview_root.exists())
    def test_invalid_utf8_is_rejected_by_publishable_reader(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "draft.md"
            path.write_bytes(b"---\nbrand: Simpro\n---\n\xff\n")

            with self.assertRaisesRegex(FrontmatterError, "UTF-8"):
                read_publishable_markdown(path)

    def test_publish_readiness_returns_structured_frontmatter_blocker(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "draft.md"
            path.write_text(
                "---\nbrand: Simpro\nbrand: BigChange\n---\n# Draft\n\nBody.\n",
                encoding="utf-8",
            )

            result = run_publish_readiness(path)

        self.assertFalse(result["passed"])
        self.assertIsNone(result["score"])
        self.assertEqual(result["gates"][0]["name"], "frontmatter_metadata")
        self.assertEqual(result["gates"][0]["findings"][0]["rule_id"], "frontmatter_invalid")

    def test_publish_readiness_structures_invalid_utf8_as_a_blocker(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "draft.md"
            path.write_bytes(b"---\nbrand: Simpro\n---\n\xff\n")

            result = run_publish_readiness(path)

        self.assertFalse(result["passed"])
        self.assertEqual(result["gates"][0]["name"], "frontmatter_metadata")
        self.assertIn("UTF-8", result["gates"][0]["blockers"][0])


if __name__ == "__main__":
    unittest.main()
