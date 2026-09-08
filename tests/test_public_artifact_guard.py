from tests.fixture_text import fixture_text

import os
import unittest
from tempfile import NamedTemporaryFile

from data_sources.modules.public_artifact_guard import (
    check_content,
    check_file,
    should_fail,
)


class PublicArtifactGuardTests(unittest.TestCase):
    def test_editorial_validation_appendix_fails(self):
        content = fixture_text("content_evidence:test_public_artifact_guard-14-1")

        findings = check_content(content)

        self.assertEqual(len(findings), 2)
        self.assertEqual(findings[0]["rule_id"], "internal_validation_artifact")

    def test_proof_heading_inside_fenced_code_fails(self):
        content = fixture_text("content_evidence:test_public_artifact_guard-29-2")

        findings = check_content(content)

        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["match"], "PAA/FAQ Provenance")

    def test_early_artifact_plan_heading_fails(self):
        content = fixture_text("content_evidence:test_public_artifact_guard-43-3")

        findings = check_content(content)

        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["match"], "## Early Artifact Plan")

    def test_concrete_answer_check_heading_fails(self):
        content = fixture_text("content_evidence:test_public_artifact_guard-57-4")

        findings = check_content(content)

        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["match"], "Concrete Answer Check")

    def test_vault_brand_language_alignment_heading_fails(self):
        content = fixture_text("content_evidence:test_public_artifact_guard-70-5")

        findings = check_content(content)

        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["match"], "## Vault Brand Language Alignment")

    def test_source_routing_decision_heading_fails(self):
        content = fixture_text("content_evidence:test_public_artifact_guard-83-6")

        findings = check_content(content)

        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["match"], "## Source Routing Decision")

    def test_fred_authority_selection_heading_fails(self):
        content = fixture_text("content_evidence:test_public_artifact_guard-96-7")

        findings = check_content(content)

        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["match"], "## Fred Voccola Authority Selection")

    def test_context_binding_and_trace_headings_fail(self):
        content = fixture_text("content_evidence:test_public_artifact_guard-109-8")

        findings = check_content(content)

        self.assertEqual(
            [finding["match"] for finding in findings],
            [
                "## Context Binding",
                "## Context Claim Use Map",
                "## Discovery Trace",
                "## Selected Resource Inventory",
            ],
        )

    def test_context_recovery_report_heading_fails(self):
        findings = check_content(
            "# Article\n\n## Context Recovery Report\n\nInternal connector attempts."
        )

        self.assertEqual(findings[0]["match"], "## Context Recovery Report")

    def test_context_heading_variants_cannot_leak(self):
        content = fixture_text("content_evidence:test_public_artifact_guard-140-9")
        findings = check_content(content)
        matches = {finding["match"] for finding in findings}
        self.assertIn("## Simpro Product Context Binding", matches)
        self.assertIn("## Context Receipt", matches)
        self.assertIn("## Context Validation Receipt", matches)
        self.assertIn("## Context Resource Inventory", matches)
        self.assertIn("## Context Discovery Trace", matches)
        self.assertIn("## Claim Use Map", matches)
        self.assertIn("## Context Pack", matches)
        self.assertIn("## Context Request", matches)
        self.assertIn("## Context Inventory", matches)
        self.assertIn("## Simpro Product Context Pack", matches)
        self.assertIn("## Context Validation", matches)

    def test_context_pack_subsections_and_decorated_headings_cannot_leak(self):
        content = fixture_text("content_evidence:test_public_artifact_guard-169-10")

        findings = check_content(content)
        matches = {finding["match"] for finding in findings}
        self.assertEqual(
            matches,
            {
                "## Approved Claim Evidence",
                "## Constraints and Unresolved Gaps",
                "## Retrieved Guidance",
                "## **Context Pack**",
                "### __Approved Claim Evidence__",
                "## `Context Request`",
                "## [Context Pack](#internal)",
                "## Context Pack {#internal}",
                "## Context Pack {.private}",
                "## Context Pack <!-- internal -->",
                "<h2>Context Pack</h2>",
                "## [Approved Claim Evidence](#proof)",
            },
        )

    def test_all_sidecar_only_proof_and_decision_headings_cannot_leak(self):
        headings = (
            "Customer Proof Slate",
            "Selected Customer Proof Mining",
            "Customer Proof Selection Decision",
            "Review Story Selection",
            "Review Site Theme Selection",
            "Competitive Shortlist Decision",
            "Named Feature/Add-On Link Check",
        )

        for heading in headings:
            with self.subTest(heading=heading):
                findings = check_content(
                    f"# Article\n\n## {heading}\n\n- Status: approved\n"
                )

                self.assertEqual(len(findings), 1)
                self.assertEqual(findings[0]["rule_id"], "internal_validation_artifact")
                self.assertEqual(findings[0]["match"], f"## {heading}")

    def test_inline_markdown_cannot_disguise_internal_headings(self):
        content = fixture_text("content_evidence:test_public_artifact_guard-227-11")

        findings = check_content(content)

        self.assertEqual(
            [finding["match"] for finding in findings],
            [
                "## Customer **Proof Pack**",
                "## Context **Binding**",
                "## Customer `Proof Slate`",
                "## Review ~~Story~~ Selection",
                "## Named Feature/Add-On _Link Check_",
            ],
        )

    def test_inline_html_cannot_disguise_internal_headings(self):
        content = fixture_text("content_evidence:test_public_artifact_guard-250-12")

        findings = check_content(content)

        self.assertEqual(
            [finding["match"] for finding in findings],
            [
                "## Customer <strong>Proof Pack</strong>",
                "## Context <em>Binding</em>",
            ],
        )

    def test_raw_connector_schemas_and_fields_cannot_leak(self):
        content = fixture_text("content_evidence:test_public_artifact_guard-267-13")

        findings = check_content(content)

        self.assertEqual(
            [finding["rule_id"] for finding in findings],
            ["internal_connector_artifact"] * 8,
        )
        self.assertEqual(
            [finding["line"] for finding in findings],
            [3, 4, 5, 6, 7, 8, 9, 10],
        )

    def test_raw_connector_schemas_and_fields_in_frontmatter_fail(self):
        content = fixture_text("content_evidence:test_public_artifact_guard-291-14")

        findings = check_content(content)
        self.assertEqual(
            [finding["rule_id"] for finding in findings],
            ["internal_connector_artifact"] * 3,
        )

    def test_all_receipt_and_revision_hash_fields_cannot_leak(self):
        content = fixture_text("content_evidence:test_public_artifact_guard-308-15")

        findings = check_content(content)

        self.assertEqual(
            [finding["rule_id"] for finding in findings],
            ["internal_connector_artifact"] * 6,
        )

    def test_raw_connector_schemas_and_fields_in_fenced_blocks_fail(self):
        content = fixture_text("content_evidence:test_public_artifact_guard-326-16")

        findings = check_content(content)
        self.assertEqual(
            [finding["rule_id"] for finding in findings],
            ["internal_connector_artifact"] * 4,
        )

    def test_cod_editorial_review_notes_fail(self):
        content = fixture_text("content_evidence:test_public_artifact_guard-346-17")

        findings = check_content(content)
        rule_ids = {finding["rule_id"] for finding in findings}

        self.assertIn("editorial_review_marker", rule_ids)
        self.assertIn("publication_confirmation_note", rule_ids)
        self.assertIn("unresolved_availability_note", rule_ids)

    def test_bracketed_editorial_labels_and_standalone_placeholders_fail(self):
        content = fixture_text("content_evidence:test_public_artifact_guard-362-18")

        findings = check_content(content)
        rule_ids = [finding["rule_id"] for finding in findings]

        self.assertEqual(rule_ids.count("editorial_review_marker"), 3)
        self.assertEqual(rule_ids.count("draft_placeholder_note"), 3)

    def test_blockquotes_cannot_hide_explicit_internal_review_markers(self):
        content = fixture_text("content_evidence:test_public_artifact_guard-380-19")

        findings = check_content(content)

        self.assertEqual(
            [finding["rule_id"] for finding in findings],
            ["editorial_review_marker"] * 4,
        )

    def test_ordinary_prose_about_review_and_proof_sections_passes(self):
        content = fixture_text("content_evidence:test_public_artifact_guard-396-20")

        self.assertEqual(check_content(content), [])

    def test_reader_instructions_image_placeholders_and_examples_pass(self):
        content = fixture_text("content_evidence:test_public_artifact_guard-405-21")

        self.assertEqual(check_content(content), [])

    def test_unclear_media_placeholders_warn_without_error(self):
        content = (
            "# Article\n\n"
            "<!-- IMAGE PLACEHOLDER: Original hero. Source: https://example.com/hero.jpg -->\n\n"
            "<!--\n"
            '[IMAGE PLACEHOLDER | source: https://example.com/commented.png | alt: "Hidden hero" | '
            "render target: 960 x 250 px | resize and compress before upload]\n"
            "-->\n\n"
            "> **Video placeholder:** Retain original Vimeo embed here.\n\n"
            'Theme image: [IMAGE PLACEHOLDER | source: https://example.com/hero.png | '
            'alt: "Hero image" | render target: 960 x 250 px | '
            "resize and compress before upload]\n\n"
            "[IMAGE PLACEHOLDER: Hero image]\n"
        )

        findings = check_content(content)

        self.assertEqual(
            [finding["rule_id"] for finding in findings],
            ["unclear_media_placeholder"] * 5,
        )
        self.assertTrue(
            all(finding["severity"] == "warning" for finding in findings)
        )
        self.assertFalse(should_fail(findings, fail_on="error"))
        self.assertTrue(should_fail(findings, fail_on="warning"))

    def test_canonical_media_placeholders_pass_cleanly(self):
        content = (
            "# Article\n\n"
            '[IMAGE PLACEHOLDER | source: https://example.com/hero.png | alt: '
            '"Hero image for scheduling" | render target: 960 x 250 px | '
            "resize and compress before upload]\n\n"
            '[VIDEO PLACEHOLDER | source: https://www.youtube.com/watch?v=dQw4w9WgXcQ | '
            'title: "Scheduling demo" | placement: after the scheduling section | '
            "embed target: responsive 16:9 youtube-nocookie iframe | "
            "VideoObject: add only after embed]\n"
        )

        self.assertEqual(check_content(content), [])

    def test_clean_public_article_passes(self):
        content = fixture_text("content_evidence:test_public_artifact_guard-421-22")

        self.assertEqual(check_content(content), [])

    def test_check_file_and_failure_threshold(self):
        with NamedTemporaryFile(
            "w", encoding="utf-8", suffix=".md", delete=False
        ) as temp_file:
            temp_file.write("# Article\n\nSource Map\n")
            temp_path = temp_file.name

        try:
            findings = check_file(temp_path, fail_on="error")
        finally:
            os.unlink(temp_path)

        self.assertTrue(should_fail(findings, fail_on="error"))
        self.assertFalse(should_fail(findings, fail_on="none"))


if __name__ == "__main__":
    unittest.main()
