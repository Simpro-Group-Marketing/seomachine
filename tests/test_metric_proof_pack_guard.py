from tests.fixture_text import fixture_text

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from data_sources.modules.metric_proof_pack_guard import (
    check_content,
    check_file,
    should_fail,
)
from data_sources.modules.numeric_claim_source_guard import check_content as check_numeric_claims


REQUIRED_FRONTMATTER = fixture_text("content_evidence:test_metric_proof_pack_guard-14-1")


class MetricProofPackGuardTests(unittest.TestCase):
    def test_metric_required_article_without_pack_fails(self):
        findings = check_content(REQUIRED_FRONTMATTER)

        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["rule_id"], "metric_proof_pack_missing")
        self.assertTrue(should_fail(findings, fail_on="error"))

    def test_body_metric_claim_requires_metric_proof_pack_even_with_neutral_title(self):
        content = fixture_text("content_evidence:test_metric_proof_pack_guard-34-2")

        findings = check_content(content)

        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["rule_id"], "metric_proof_pack_missing")

    def test_metric_required_article_with_no_approved_metrics_fails(self):
        content = REQUIRED_FRONTMATTER + fixture_text("content_evidence:test_metric_proof_pack_guard-50-4")

        findings = check_content(content)

        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["rule_id"], "metric_proof_pack_no_approved_metrics")

    def test_approved_metric_with_matching_local_artifact_passes(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            artifact = root / "research" / "metric-source.md"
            artifact.parent.mkdir(parents=True)
            artifact.write_text(
                "Simpro supports more than 24,000 trade businesses worldwide.",
                encoding="utf-8",
            )
            article = root / "drafts" / "best-hvac-scheduling-software.md"
            content = REQUIRED_FRONTMATTER + fixture_text("content_evidence:test_metric_proof_pack_guard-74-8")
            article.parent.mkdir(parents=True)
            article.write_text(content, encoding="utf-8")

            findings = check_file(str(article))

        self.assertEqual(findings, [])

    def test_approved_metric_from_sidecar_passes_clean_draft(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            artifact = root / "research" / "metric-source.md"
            artifact.parent.mkdir(parents=True)
            artifact.write_text(
                "Simpro supports more than 24,000 trade businesses worldwide.",
                encoding="utf-8",
            )
            article = root / "drafts" / "best-hvac-scheduling-software-2026-06-12.md"
            sidecar = (
                root
                / "research"
                / "validation-best-hvac-scheduling-software-2026-06-12.md"
            )
            article.parent.mkdir(parents=True)
            article.write_text(REQUIRED_FRONTMATTER, encoding="utf-8")
            sidecar.write_text(
                fixture_text("content_evidence:test_metric_proof_pack_guard-107-9"),
                encoding="utf-8",
            )

            findings = check_file(str(article), proof_sidecar=str(sidecar))

        self.assertEqual(findings, [])

    def test_approved_metric_missing_evidence_fails(self):
        content = REQUIRED_FRONTMATTER + fixture_text("content_evidence:test_metric_proof_pack_guard-123-5")

        findings = check_content(content)

        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["rule_id"], "metric_evidence_missing")

    def test_metric_not_applicable_with_documented_reason_passes(self):
        content = fixture_text("content_evidence:test_metric_proof_pack_guard-138-3")

        findings = check_content(content)

        self.assertEqual(findings, [])

    def test_numeric_claim_not_covered_by_pack_still_fails_numeric_guard(self):
        content = REQUIRED_FRONTMATTER + fixture_text("content_evidence:test_metric_proof_pack_guard-159-6")

        numeric_findings = check_numeric_claims(content)

        self.assertEqual(len(numeric_findings), 1)
        self.assertEqual(numeric_findings[0]["rule_id"], "unsupported_numeric_claim")

    def test_public_metric_source_uses_shared_cached_source_fetcher(self):
        content = REQUIRED_FRONTMATTER + fixture_text("content_evidence:test_metric_proof_pack_guard-176-7")

        with patch(
            "data_sources.modules.metric_proof_pack_guard.fetch_source_text",
            return_value="Simpro supports more than 24,000 trade businesses worldwide.",
        ) as fetch_source:
            findings = check_content(content)

        self.assertEqual(findings, [])
        fetch_source.assert_called_once_with("https://example.com/proof")


if __name__ == "__main__":
    unittest.main()
