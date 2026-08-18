from tests.fixture_text import fixture_text

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from data_sources.modules.early_artifact_guard import (
    check_content,
    check_file,
    should_fail,
)


REQUIRED_FRONTMATTER = fixture_text("content_evidence:test_early_artifact_guard-12-1")


def _prose(word_count):
    words = ["benchmark", "planning", "field", "teams", "review", "work"]
    return " ".join(words[index % len(words)] for index in range(word_count))


FILLED_TABLE = fixture_text("content_evidence:test_early_artifact_guard-25-2")

SCAFFOLD_TABLE = fixture_text("content_evidence:test_early_artifact_guard-31-3")


def finding_ids(content, proof_content=None):
    return {
        finding["rule_id"]
        for finding in check_content(content, proof_content=proof_content)
    }


class EarlyArtifactGuardTests(unittest.TestCase):
    def test_filled_table_within_window_passes(self):
        content = (
            REQUIRED_FRONTMATTER
            + "# Plumbing Benchmarks\n\n"
            + _prose(60)
            + "\n\n"
            + FILLED_TABLE
        )

        self.assertEqual(check_content(content), [])

    def test_article_without_artifact_fails(self):
        content = (
            REQUIRED_FRONTMATTER
            + "# Plumbing Benchmarks\n\n"
            + _prose(80)
            + "\n\n> Key takeaway one about planning.\n"
            + "> Key takeaway two about dispatch.\n\n"
            + "- First checklist style bullet\n"
            + "- Second checklist style bullet\n\n"
            + "Read the [industry overview](https://example.com/overview) for context.\n"
        )

        findings = check_content(content)

        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["rule_id"], "early_artifact_missing")
        self.assertEqual(findings[0]["severity"], "error")
        self.assertTrue(should_fail(findings, fail_on="error"))
        self.assertFalse(should_fail(findings, fail_on="none"))

    def test_artifact_after_window_fails_with_word_offset(self):
        content = (
            REQUIRED_FRONTMATTER
            + "# Plumbing Benchmarks\n\n"
            + _prose(320)
            + "\n\n"
            + FILLED_TABLE
        )

        findings = check_content(content)

        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["rule_id"], "early_artifact_missing")
        self.assertEqual(findings[0]["word_offset"], 320)

    def test_scaffold_table_within_window_does_not_count(self):
        content = (
            REQUIRED_FRONTMATTER
            + "# Plumbing Benchmarks\n\n"
            + _prose(40)
            + "\n\n"
            + SCAFFOLD_TABLE
        )

        self.assertEqual(finding_ids(content), {"early_artifact_missing"})

    def test_download_link_pdf_href_passes(self):
        content = (
            REQUIRED_FRONTMATTER
            + "# Plumbing Benchmarks\n\n"
            + _prose(40)
            + "\n\nGrab the [job sheet form](https://example.com/files/job-sheet.pdf) before your next visit.\n"
        )

        self.assertEqual(check_content(content), [])

    def test_checklist_anchor_text_link_passes(self):
        content = (
            REQUIRED_FRONTMATTER
            + "# Plumbing Benchmarks\n\n"
            + _prose(40)
            + "\n\nUse the [maintenance checklist](https://example.com/resources/maintenance) on every job.\n"
        )

        self.assertEqual(check_content(content), [])

    def test_calculator_href_passes(self):
        content = (
            REQUIRED_FRONTMATTER
            + "# Plumbing Benchmarks\n\n"
            + _prose(40)
            + "\n\nRun your numbers in the [labor burden tool](https://example.com/calculator/labor-burden) first.\n"
        )

        self.assertEqual(check_content(content), [])

    def test_blockquote_and_heading_words_excluded_from_count(self):
        blockquote = "\n".join(
            "> " + _prose(25) for _ in range(10)
        )
        content = (
            REQUIRED_FRONTMATTER
            + "# Plumbing Benchmarks\n\n"
            + _prose(100)
            + "\n\n"
            + blockquote
            + "\n\n## Benchmark Ranges\n\n"
            + _prose(150)
            + "\n\n"
            + FILLED_TABLE
        )

        self.assertEqual(check_content(content), [])

    def test_sidecar_not_applicable_with_reason_passes(self):
        content = (
            REQUIRED_FRONTMATTER
            + "# Plumbing Benchmarks\n\n"
            + _prose(400)
        )
        proof_content = fixture_text("content_evidence:test_early_artifact_guard-157-4")

        self.assertEqual(check_content(content, proof_content=proof_content), [])

    def test_not_applicable_without_reason_fails(self):
        content = (
            REQUIRED_FRONTMATTER
            + "# Plumbing Benchmarks\n\n"
            + _prose(400)
        )
        proof_content = fixture_text("content_evidence:test_early_artifact_guard-170-5")

        self.assertEqual(
            finding_ids(content, proof_content=proof_content),
            {"early_artifact_reason_missing"},
        )

    def test_check_file_reads_explicit_sidecar(self):
        content = (
            REQUIRED_FRONTMATTER
            + "# Plumbing Benchmarks\n\n"
            + _prose(400)
        )
        sidecar = fixture_text("content_evidence:test_early_artifact_guard-185-6")

        with TemporaryDirectory() as root:
            article_path = Path(root) / "drafts" / "plumbing-benchmarks.md"
            article_path.parent.mkdir(parents=True)
            article_path.write_text(content, encoding="utf-8")
            sidecar_path = Path(root) / "validation-plumbing-benchmarks.md"
            sidecar_path.write_text(sidecar, encoding="utf-8")

            self.assertEqual(
                check_file(str(article_path), proof_sidecar=str(sidecar_path)),
                [],
            )

    def test_check_file_rejects_invalid_fail_on(self):
        with self.assertRaises(ValueError):
            check_file("missing.md", fail_on="bogus")


if __name__ == "__main__":
    unittest.main()
