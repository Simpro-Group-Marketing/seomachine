import unittest

from data_sources.modules.source_routing_guard import check_content, should_fail


VALID_SIDECAR = """## Source Routing Decision
- Article title: Top 12 Trades for Women in 2026: Pay, Demand & How to Start
- Vault-sourced data types: Brand voice, audience, tone, product solution language, competitor shortlist boundary, customer proof approval boundary
- Repo-context-sourced data types: SEO mechanics, AEO/GEO workflow, schema notes, publish gates, internal links, keyword snapshots, AI citation targets, CRO, Reddit, writing examples
- Vault routes checked: AGENTS.md; wiki/cache/hot.md; wiki/Brand Graph Index.md; wiki/messaging/Voice and Tone.md; wiki/messaging/Tone Voice and Localization Rules.md; wiki/messaging/Simpro Core Messaging Repository.md; wiki/messaging/Message House.md; wiki/messaging/Core Value Pillars.md; wiki/product/Product Positioning.md; wiki/features/Feature Library.md
- Repo context files checked: context/aeo-geo-blog-strategy.md; context/seo-guidelines.md; context/internal-links-map.md; context/target-keywords.md; context/customer-proof-index.json; context/customer-proof-usage-ledger.json
- Fallback context use: none
- Conflicts found: none
- Status: aligned
"""


class SourceRoutingGuardTests(unittest.TestCase):
    def test_non_simpro_copy_does_not_require_source_routing_decision(self):
        findings = check_content(
            "# Dispatch planning\n\n"
            "A dispatch plan should assign jobs based on technician availability.",
            proof_content="",
        )

        self.assertEqual(findings, [])

    def test_simpro_article_requires_source_routing_decision(self):
        findings = check_content(
            "# Field service software\n\n"
            "Simpro field service management software helps office and field teams coordinate work.",
            proof_content="",
        )

        self.assertTrue(any(f["rule_id"] == "source_routing_decision_missing" for f in findings))
        self.assertTrue(should_fail(findings, fail_on="error"))

    def test_valid_source_routing_decision_passes(self):
        findings = check_content(
            "# Field service software\n\n"
            "Simpro field service management software helps office and field teams coordinate work.",
            proof_content=VALID_SIDECAR,
        )

        self.assertEqual(findings, [])

    def test_repo_fallback_requires_vault_unavailable_blocker(self):
        sidecar = VALID_SIDECAR.replace(
            "Fallback context use: none",
            "Fallback context use: context/brand-voice.md and context/style-guide.md",
        )

        findings = check_content(
            "# Field service software\n\n"
            "Simpro field service management software helps office and field teams coordinate work.",
            proof_content=sidecar,
        )

        self.assertTrue(any(f["rule_id"] == "source_routing_fallback_without_blocker" for f in findings))

    def test_vault_first_data_cannot_be_repo_context_primary(self):
        sidecar = VALID_SIDECAR.replace(
            "Repo-context-sourced data types: SEO mechanics, AEO/GEO workflow, schema notes, publish gates, internal links, keyword snapshots, AI citation targets, CRO, Reddit, writing examples",
            "Repo-context-sourced data types: brand voice from context/brand-voice.md; product feature claims from context/features.md; SEO mechanics",
        )

        findings = check_content(
            "# Field service software\n\n"
            "Simpro field service management software helps office and field teams coordinate work.",
            proof_content=sidecar,
        )

        self.assertTrue(any(f["rule_id"] == "source_routing_repo_primary_vault_first_data" for f in findings))

    def test_vault_route_missing_fails(self):
        sidecar = VALID_SIDECAR.replace(
            "AGENTS.md; wiki/cache/hot.md; wiki/Brand Graph Index.md; ",
            "",
        )

        findings = check_content(
            "# Field service software\n\n"
            "Simpro field service management software helps office and field teams coordinate work.",
            proof_content=sidecar,
        )

        self.assertTrue(any(f["rule_id"] == "source_routing_core_route_missing" for f in findings))

    def test_voice_and_tone_route_missing_fails(self):
        sidecar = VALID_SIDECAR.replace(
            "wiki/messaging/Voice and Tone.md; ",
            "",
        )

        findings = check_content(
            "# Field service software\n\n"
            "Simpro field service management software helps office and field teams coordinate work.",
            proof_content=sidecar,
        )

        self.assertTrue(any(f["rule_id"] == "source_routing_core_route_missing" for f in findings))

    def test_repo_primary_workflow_context_passes(self):
        sidecar = VALID_SIDECAR.replace(
            "Vault-sourced data types: Brand voice, audience, tone, product solution language, competitor shortlist boundary, customer proof approval boundary",
            "Vault-sourced data types: Brand voice, audience, tone",
        ).replace(
            "Repo-context-sourced data types: SEO mechanics, AEO/GEO workflow, schema notes, publish gates, internal links, keyword snapshots, AI citation targets, CRO, Reddit, writing examples",
            "Repo-context-sourced data types: SEO mechanics, AEO/GEO workflow, schema notes, publish gates, internal links, keyword snapshots",
        )

        findings = check_content(
            "# Blog refresh\n\n"
            "Use Simpro examples only after source routing confirms the active read path.",
            proof_content=sidecar,
        )

        self.assertEqual(findings, [])

    def test_fred_authority_heading_ends_source_routing_block(self):
        sidecar = VALID_SIDECAR.rstrip() + """
## Fred Voccola Authority Selection
- Fallback context use: repo-only Fred evidence without a vault blocker
- Status: blocked
"""

        findings = check_content(
            "# Blog refresh\n\nSimpro examples use the active vault read path.",
            proof_content=sidecar,
        )

        self.assertEqual(findings, [])


if __name__ == "__main__":
    unittest.main()
