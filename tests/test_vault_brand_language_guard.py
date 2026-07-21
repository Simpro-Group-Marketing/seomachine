import unittest

from data_sources.modules.vault_brand_language_guard import (
    check_content,
    should_fail,
)


VALID_PRODUCT_SIDECAR = """## Vault Brand Language Alignment
- Article title: Best job quoting and invoicing software
- Product/solution language scope: product/feature
- Vault routes checked: AGENTS.md; wiki/cache/hot.md; wiki/Brand Graph Index.md; wiki/messaging/Simpro Core Messaging Repository.md; wiki/messaging/Message House.md; wiki/messaging/Core Value Pillars.md; wiki/product/Product Positioning.md; wiki/features/Feature Library.md; wiki/features/source-docs/simpro-overview25-us-digital-pdf-1av204-d.md
- Product/feature language applied: AI-first operating platform category, Simpro product naming, Operational Visibility and Control value pillar, quote-to-cash workflow phrase, avoided all-in-one and generic solutions.
- Solution/industry language applied: not applicable
- Fallback context use: none
- Claims requiring source verification: mapped in Source Map / Customer Proof Pack / Metric Proof Pack
- Status: aligned
"""


class VaultBrandLanguageGuardTests(unittest.TestCase):
    def test_no_product_or_solution_trigger_passes_without_sidecar_block(self):
        findings = check_content(
            "# Dispatch planning\n\n"
            "A dispatch plan should assign work based on availability, location, and job priority.",
            proof_content="",
        )

        self.assertEqual(findings, [])

    def test_triggered_simpro_product_copy_requires_alignment_block(self):
        findings = check_content(
            "# Job quoting software\n\n"
            "Simpro field service management software helps teams manage quoting and invoicing.",
            proof_content="",
        )

        self.assertTrue(any(f["rule_id"] == "vault_brand_language_alignment_missing" for f in findings))
        self.assertTrue(should_fail(findings, fail_on="error"))

    def test_valid_product_feature_alignment_block_passes(self):
        findings = check_content(
            "# Job quoting software\n\n"
            "Simpro field service management software helps teams manage quoting and invoicing.",
            proof_content=VALID_PRODUCT_SIDECAR,
        )

        self.assertEqual(findings, [])

    def test_named_feature_requires_specific_feature_source_doc_route(self):
        sidecar = VALID_PRODUCT_SIDECAR.replace(
            "; wiki/features/source-docs/simpro-overview25-us-digital-pdf-1av204-d.md",
            "",
        )

        findings = check_content(
            "# Digital Forms\n\n"
            "Simpro Digital Forms turns paper recordkeeping into searchable digital records.",
            proof_content=sidecar,
        )

        self.assertTrue(any(f["rule_id"] == "vault_brand_language_feature_source_route_missing" for f in findings))

    def test_solution_industry_scope_requires_vertical_profile_route(self):
        sidecar = VALID_PRODUCT_SIDECAR.replace(
            "Product/solution language scope: product/feature",
            "Product/solution language scope: solution/industry",
        )

        findings = check_content(
            "# Electrical field service software\n\n"
            "See field service management options for [electrical contractors]"
            "(https://www.simprogroup.com/industries/electrical).",
            proof_content=sidecar,
        )

        self.assertTrue(any(f["rule_id"] == "vault_brand_language_vertical_route_missing" for f in findings))

    def test_fallback_context_requires_vault_unavailable_blocker(self):
        sidecar = VALID_PRODUCT_SIDECAR.replace(
            "Fallback context use: none",
            "Fallback context use: context/brand-voice.md and context/style-guide.md",
        )

        findings = check_content(
            "# Job quoting software\n\n"
            "Simpro field service management software helps teams manage quoting and invoicing.",
            proof_content=sidecar,
        )

        self.assertTrue(any(f["rule_id"] == "vault_brand_language_fallback_without_blocker" for f in findings))


if __name__ == "__main__":
    unittest.main()
