from tests.fixture_text import fixture_text

import unittest
from tempfile import NamedTemporaryFile
import os

from data_sources.modules.numeric_claim_source_guard import (
    check_content,
    check_file,
    should_fail,
)


def finding_ids(content):
    return {finding["rule_id"] for finding in check_content(content)}


class NumericClaimSourceGuardTests(unittest.TestCase):
    def test_current_ebitda_margin_claim_fails_without_public_proof(self):
        content = fixture_text("content_evidence:test_numeric_claim_source_guard-18-1")

        findings = check_content(content)
        unsupported = [
            finding
            for finding in findings
            if finding["rule_id"] == "unsupported_numeric_claim"
        ]

        self.assertEqual(len(unsupported), 1)
        self.assertEqual(unsupported[0]["severity"], "error")
        self.assertIn("15%", unsupported[0]["numeric_tokens"])
        self.assertIn("25%", unsupported[0]["numeric_tokens"])

    def test_corrected_ebitda_margin_claim_with_same_paragraph_link_passes(self):
        content = fixture_text("content_evidence:test_numeric_claim_source_guard-36-2")

        self.assertEqual(check_content(content), [])

    def test_non_owned_numeric_link_must_match_sidecar_proof_when_sidecar_exists(self):
        content = (
            "Contractors reported a 25% profit margin according to "
            "[unrelated guidance](https://example.org/unrelated)."
        )
        sidecar = (
            "## Source Map\n"
            "- Claim: Contractors reported a 25% profit margin. | "
            "Claim type: metric | Source class: independent_research | "
            "URL: https://example.org/margin-study | Evidence: 25% profit margin | "
            "Status: approved\n"
        )

        self.assertIn(
            "unsupported_numeric_claim",
            {
                finding["rule_id"]
                for finding in check_content(content, proof_content=sidecar)
            },
        )

    def test_numeric_claim_rejects_generic_or_bare_proof_links(self):
        generic = (
            "Contractors reported a 25% profit margin under this "
            "[source](https://example.org/margin-study)."
        )
        bare = (
            "Contractors reported a 25% profit margin: "
            "https://example.org/margin-study"
        )

        self.assertIn("unsupported_numeric_claim", finding_ids(generic))
        self.assertIn("unsupported_numeric_claim", finding_ids(bare))

    def test_source_map_claim_without_url_or_artifact_still_fails(self):
        content = fixture_text("content_evidence:test_numeric_claim_source_guard-44-3")

        findings = check_content(content)
        unsupported = [
            finding
            for finding in findings
            if finding["rule_id"] == "unsupported_numeric_claim"
        ]

        self.assertEqual(len(unsupported), 1)
        self.assertEqual(unsupported[0]["severity"], "error")
        self.assertIn("6%", unsupported[0]["numeric_tokens"])

    def test_dates_steps_headings_urls_and_frontmatter_metadata_are_ignored(self):
        content = fixture_text("content_evidence:test_numeric_claim_source_guard-66-4")

        self.assertEqual(check_content(content), [])

    def test_production_image_placeholder_metadata_is_not_a_business_claim(self):
        content = (
            '[IMAGE PLACEHOLDER | source: https://www.simprogroup.com/image.png | '
            'alt: "8 Best Software Tools for Growing Businesses" | '
            'render target: 819 x 250 px | resize and compress before upload]'
        )

        self.assertEqual(check_content(content), [])

    def test_ordered_list_markers_are_not_material_numeric_claims(self):
        content = """# Licensing guide

1. Create an online account with an email address you control.
2. Add an existing registration or license when applicable.
3. Select the application action for the credential you need.
"""

        self.assertEqual(check_content(content), [])

    def test_fdd_item_numbers_are_ignored(self):
        content = fixture_text("content_evidence:test_numeric_claim_source_guard-84-5")

        self.assertEqual(check_content(content), [])

    def test_source_map_with_public_url_cannot_replace_visible_metric_proof(self):
        content = fixture_text("content_evidence:test_numeric_claim_source_guard-94-6")

        self.assertIn("unsupported_numeric_claim", finding_ids(content))

    def test_sidecar_source_map_cannot_replace_visible_metric_proof(self):
        content = fixture_text("content_evidence:test_numeric_claim_source_guard-107-7")
        sidecar = fixture_text("content_evidence:test_numeric_claim_source_guard-111-8")

        self.assertIn(
            "unsupported_numeric_claim",
            {
                finding["rule_id"]
                for finding in check_content(content, proof_content=sidecar)
            },
        )

    def test_list_items_are_checked_as_separate_claims(self):
        content = fixture_text("content_evidence:test_numeric_claim_source_guard-118-9")

        findings = check_content(content)

        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["line"], 4)
        self.assertEqual(
            findings[0]["match"],
            "- Royalty rates in the HVAC franchise industry typically sit at 6% of gross revenue.",
        )

    def test_blockquoted_list_items_are_checked_as_separate_claims(self):
        content = fixture_text("content_evidence:test_numeric_claim_source_guard-135-10")

        findings = check_content(content)

        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["line"], 4)
        self.assertEqual(
            findings[0]["match"],
            "> - Royalty rates in the HVAC franchise industry typically sit at 6% of gross revenue.",
        )

    def test_public_scale_claim_with_modifier_requires_proof(self):
        content = fixture_text("content_evidence:test_numeric_claim_source_guard-152-11")

        findings = check_content(content)

        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["rule_id"], "unsupported_numeric_claim")
        self.assertIn("24,000+", findings[0]["numeric_tokens"])

    def test_spelled_out_metric_multiple_requires_proof(self):
        content = fixture_text("content_evidence:test_numeric_claim_source_guard-164-12")

        findings = check_content(content)

        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["rule_id"], "unsupported_numeric_claim")
        self.assertIn("ten times", findings[0]["numeric_tokens"])

    def test_spelled_out_metric_multiple_with_same_paragraph_link_passes(self):
        content = fixture_text("content_evidence:test_numeric_claim_source_guard-176-13")

        self.assertEqual(check_content(content), [])

    def test_owned_same_paragraph_link_without_matching_proof_row_fails(self):
        content = fixture_text("content_evidence:test_numeric_claim_source_guard-184-14")

        findings = check_content(content)

        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["rule_id"], "unsupported_numeric_claim")
        self.assertIn("24,000+", findings[0]["numeric_tokens"])

    def test_owned_same_paragraph_link_passes_with_matching_proof_row(self):
        content = fixture_text("content_evidence:test_numeric_claim_source_guard-196-15")
        sidecar = fixture_text("content_evidence:test_numeric_claim_source_guard-200-16")

        self.assertEqual(check_content(content, proof_content=sidecar), [])

    def test_single_digit_margin_claim_requires_proof(self):
        content = fixture_text("content_evidence:test_numeric_claim_source_guard-207-17")

        findings = check_content(content)

        self.assertEqual(len(findings), 1)
        self.assertEqual(
            findings[0]["rule_id"],
            "unsupported_verbal_quantified_claim",
        )
        self.assertIn("single-digit", findings[0]["match"])

    def test_average_business_performance_claim_requires_proof(self):
        content = fixture_text("content_evidence:test_numeric_claim_source_guard-222-18")

        self.assertIn(
            "unsupported_verbal_quantified_claim",
            finding_ids(content),
        )

    def test_most_complaints_claim_requires_proof(self):
        content = fixture_text("content_evidence:test_numeric_claim_source_guard-233-19")

        self.assertIn(
            "unsupported_verbal_quantified_claim",
            finding_ids(content),
        )

    def test_number_word_business_size_requires_proof(self):
        content = fixture_text("content_evidence:test_numeric_claim_source_guard-244-20")

        self.assertIn(
            "unsupported_verbal_quantified_claim",
            finding_ids(content),
        )

    def test_operator_group_comparison_requires_proof(self):
        content = fixture_text("content_evidence:test_numeric_claim_source_guard-255-21")

        self.assertIn(
            "unsupported_verbal_quantified_claim",
            finding_ids(content),
        )

    def test_verbal_quantity_with_same_paragraph_public_link_passes(self):
        content = fixture_text("content_evidence:test_numeric_claim_source_guard-266-22")

        self.assertEqual(check_content(content), [])

    def test_verbal_quantity_with_matching_source_map_still_needs_visible_proof(self):
        content = fixture_text("content_evidence:test_numeric_claim_source_guard-274-23")
        sidecar = fixture_text("content_evidence:test_numeric_claim_source_guard-278-24")

        self.assertIn(
            "unsupported_verbal_quantified_claim",
            {
                finding["rule_id"]
                for finding in check_content(content, proof_content=sidecar)
            },
        )

    def test_source_map_must_cover_each_verbal_claim_phrase(self):
        content = fixture_text("content_evidence:test_numeric_claim_source_guard-288-25")
        sidecar = fixture_text("content_evidence:test_numeric_claim_source_guard-292-26")

        self.assertIn(
            "unsupported_verbal_quantified_claim",
            {
                finding["rule_id"]
                for finding in check_content(content, proof_content=sidecar)
            },
        )

    def test_instructional_number_words_are_not_claims(self):
        content = fixture_text("content_evidence:test_numeric_claim_source_guard-308-27")

        self.assertEqual(check_content(content), [])

    def test_check_file_and_failure_threshold(self):
        with NamedTemporaryFile("w", encoding="utf-8", suffix=".md", delete=False) as temp_file:
            temp_file.write(
                "Franchises with group purchasing power typically save 15% to 20% on operational costs."
            )
            temp_path = temp_file.name

        try:
            findings = check_file(temp_path, fail_on="error")
        finally:
            os.unlink(temp_path)

        self.assertTrue(should_fail(findings, fail_on="error"))
        self.assertFalse(should_fail(findings, fail_on="none"))


if __name__ == "__main__":
    unittest.main()
