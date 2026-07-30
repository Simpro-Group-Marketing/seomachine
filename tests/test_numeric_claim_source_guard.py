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
        content = """# How profitable is an HVAC business?

HVAC businesses rank among the most profitable in home services. Well-run operations typically report EBITDA margins of 15% to 25% before owner compensation.
"""

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
        content = """# How profitable is an HVAC business?

Well-run HVAC operators in the $5M to $30M range should target [15% to 20% EBITDA margins](https://profitabilitypartners.io/what-is-ebitda-contractors/) when service, replacement, and maintenance work are balanced.
"""

        self.assertEqual(check_content(content), [])

    def test_source_map_claim_without_url_or_artifact_still_fails(self):
        content = """---
Source Map:
- Royalty rates ~6% | Industry standard per FDD conventions | no anchor | Step 3
---

# Franchise royalty planning

Royalty rates in the HVAC franchise industry typically sit at 6% of gross revenue.
"""

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
        content = """---
Rewrite Date: 2026-06-09
Word Count Change: ~2,900 -> ~3,300
SEO Score Improvement: 85 -> 90
---

# 6-step HVAC franchise guide

## Step 4: Set up the franchise legally

Read https://example.com/report-2026-06-09?discount=25 for the background source.

From serious planning to selling a first franchise unit, expect 6 to 18 months.
"""

        self.assertEqual(check_content(content), [])

    def test_fdd_item_numbers_are_ignored(self):
        content = """# Franchise diligence

Use each brand's FDD Item 7 to model fees, equipment, inventory, insurance, marketing, and working capital.

Financial performance disclosures, when a franchisor makes them, belong in Item 19 of the FDD.
"""

        self.assertEqual(check_content(content), [])

    def test_source_map_with_public_url_can_support_body_claim(self):
        content = """---
Source Map:
- Specialty trade contractor EBITDA margins 18.1% to 20.4% | https://middlemarketgrowth.org/wp-content/uploads/2025/04/GF-Data-4th-Quarter-Highlights-and-Products.pdf | benchmark support | FAQ
---

# HVAC profitability

Specialty trade contractors in GF Data's 2024 sample reported adjusted EBITDA margins from 18.1% to 20.4%.
"""

        self.assertEqual(check_content(content), [])

    def test_sidecar_source_map_can_support_body_claim(self):
        content = """# Operational scale

The 24,000+ trade businesses already running on Simpro use documented workflows, pricing catalogs, and job card standards.
"""
        sidecar = """Source Map
- Claim: Simpro Group platforms are used by more than 24,000 trade businesses | URL: https://www.simprogroup.com/company/press/simpro-group-unveils-lightning | Evidence: "More than 24,000 trade businesses" | Status: approved
"""

        self.assertEqual(check_content(content, proof_content=sidecar), [])

    def test_list_items_are_checked_as_separate_claims(self):
        content = """# Franchise checklist

- Step 1: Document the operating manual.
- Royalty rates in the HVAC franchise industry typically sit at 6% of gross revenue.
- Read the FDD before signing.
"""

        findings = check_content(content)

        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["line"], 4)
        self.assertEqual(
            findings[0]["match"],
            "- Royalty rates in the HVAC franchise industry typically sit at 6% of gross revenue.",
        )

    def test_blockquoted_list_items_are_checked_as_separate_claims(self):
        content = """# Franchise checklist

> - Step 1: Document the operating manual.
> - Royalty rates in the HVAC franchise industry typically sit at 6% of gross revenue.
> - Read the FDD before signing.
"""

        findings = check_content(content)

        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["line"], 4)
        self.assertEqual(
            findings[0]["match"],
            "> - Royalty rates in the HVAC franchise industry typically sit at 6% of gross revenue.",
        )

    def test_public_scale_claim_with_modifier_requires_proof(self):
        content = """# Operational scale

The 24,000+ trade businesses already running on Simpro use documented workflows, pricing catalogs, and job card standards.
"""

        findings = check_content(content)

        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["rule_id"], "unsupported_numeric_claim")
        self.assertIn("24,000+", findings[0]["numeric_tokens"])

    def test_spelled_out_metric_multiple_requires_proof(self):
        content = """# Quoting workflow

BGE Digital put quotes out ten times quicker than spreadsheets after changing its quoting workflow.
"""

        findings = check_content(content)

        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["rule_id"], "unsupported_numeric_claim")
        self.assertIn("ten times", findings[0]["numeric_tokens"])

    def test_spelled_out_metric_multiple_with_same_paragraph_link_passes(self):
        content = """# Quoting workflow

[BGE Digital](https://example.com/case-studies/bge-digital) put quotes out ten times quicker than spreadsheets after changing its quoting workflow.
"""

        self.assertEqual(check_content(content), [])

    def test_owned_same_paragraph_link_without_matching_proof_row_fails(self):
        content = """# Operational scale

Simpro supports [24,000+ trade businesses](https://www.simprogroup.com/) through field service workflows.
"""

        findings = check_content(content)

        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["rule_id"], "unsupported_numeric_claim")
        self.assertIn("24,000+", findings[0]["numeric_tokens"])

    def test_owned_same_paragraph_link_passes_with_matching_proof_row(self):
        content = """# Operational scale

Simpro supports [24,000+ trade businesses](https://www.simprogroup.com/company/press/simpro-group-unveils-lightning) through field service workflows.
"""
        sidecar = """Source Map
- Claim: Simpro Group platforms are used by more than 24,000 trade businesses | URL: https://www.simprogroup.com/company/press/simpro-group-unveils-lightning | Evidence: "More than 24,000 trade businesses" | Status: approved
"""

        self.assertEqual(check_content(content, proof_content=sidecar), [])

    def test_single_digit_margin_claim_requires_proof(self):
        content = """# Operating margin

The average field service trade business runs on a single-digit net margin.
"""

        findings = check_content(content)

        self.assertEqual(len(findings), 1)
        self.assertEqual(
            findings[0]["rule_id"],
            "unsupported_verbal_quantified_claim",
        )
        self.assertIn("single-digit", findings[0]["match"])

    def test_average_business_performance_claim_requires_proof(self):
        content = """# Business performance

The average operator carries higher costs when dispatch work stays manual.
"""

        self.assertIn(
            "unsupported_verbal_quantified_claim",
            finding_ids(content),
        )

    def test_most_complaints_claim_requires_proof(self):
        content = """# Customer communication

Most customer complaints are about the silence after the job.
"""

        self.assertIn(
            "unsupported_verbal_quantified_claim",
            finding_ids(content),
        )

    def test_number_word_business_size_requires_proof(self):
        content = """# Back office capacity

A twenty-person shop has to squeeze coordination work in between jobs.
"""

        self.assertIn(
            "unsupported_verbal_quantified_claim",
            finding_ids(content),
        )

    def test_operator_group_comparison_requires_proof(self):
        content = """# Business performance

National operators run healthier than small field service businesses because they have larger back offices.
"""

        self.assertIn(
            "unsupported_verbal_quantified_claim",
            finding_ids(content),
        )

    def test_verbal_quantity_with_same_paragraph_public_link_passes(self):
        content = """# Operating margin

The [average contractor margin](https://example.org/field-service-margins) remains in the single-digit range.
"""

        self.assertEqual(check_content(content), [])

    def test_verbal_quantity_with_matching_source_map_row_passes(self):
        content = """# Customer communication

Most customer complaints are about the silence after the job.
"""
        sidecar = """## Source Map

| Claim | URL | Status |
|---|---|---|
| Most customer complaints are about the silence after the job | https://example.org/customer-complaints | approved |
"""

        self.assertEqual(check_content(content, proof_content=sidecar), [])

    def test_source_map_must_cover_each_verbal_claim_phrase(self):
        content = """# Operating margin

The average trade business runs on a single-digit net margin.
"""
        sidecar = """## Source Map

| Claim | URL | Status |
|---|---|---|
| Single-digit net margin | https://example.org/field-service-margins | approved |
"""

        self.assertIn(
            "unsupported_verbal_quantified_claim",
            {
                finding["rule_id"]
                for finding in check_content(content, proof_content=sidecar)
            },
        )

    def test_instructional_number_words_are_not_claims(self):
        content = """# Pilot setup

Pick one workflow, one user group, and one review period.
"""

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
