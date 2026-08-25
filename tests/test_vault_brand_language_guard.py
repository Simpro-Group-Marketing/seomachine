from tests.fixture_text import fixture_text

import unittest

from data_sources.modules.vault_brand_language_guard import (
    check_content,
    should_fail,
)


VALID_PRODUCT_SIDECAR = fixture_text("sealed_workflows:test_vault_brand_language_guard-9-1")


class VaultBrandLanguageGuardTests(unittest.TestCase):
    def _validated_artifacts(self):
        resource_id = "res-641679c4b6c65e93951cb8d8e1ab88af"
        feature_resource_id = "res-ad3ee1bcd777586d81415ba9298cd755"
        vertical_resource_id = "res-d31f057a305f51918055120d95b76c6a"
        resources = [
            {
                "resource_id": resource_id,
                "title": "Voice and Tone",
                "aliases": ["Brand voice"],
                "headings": ["Writing in the Simpro voice"],
                "topics": ["brand", "voice", "tone"],
                "semantic_roles": ["guidance"],
            },
            {
                "resource_id": feature_resource_id,
                "title": "Digital Forms",
                "aliases": ["Simpro Digital Forms"],
                "headings": ["Digital Forms product guidance"],
                "topics": ["digital forms", "product feature", "recordkeeping"],
                "semantic_roles": ["guidance", "feature"],
            },
            {
                "resource_id": vertical_resource_id,
                "title": "Electrical contractors",
                "aliases": ["Electrical industry"],
                "headings": ["Electrical field service workflows"],
                "topics": ["electrical", "industry", "vertical"],
                "semantic_roles": ["guidance", "vertical"],
            },
        ]
        return (
            {
                "sections": {
                    "Discovery Trace": {
                        "selected_resource_ids": [
                            resource_id,
                            feature_resource_id,
                            vertical_resource_id,
                        ]
                    },
                    "Retrieved Guidance": resources,
                    "Selected Resource Inventory": resources,
                }
            },
            {
                "pack_sha256": "0bb54c045bee7316652b3420389615a8062f6b3b654dd56630a28b2501f060a8",
                "receipt_sha256": "79a12fa9ec9e3287658f44a273dca3b393e557b25bfd564cc6c201ff3620eab9",
                "revisions": {
                    "manifest_revision": "479e1c3ddcc8d3829b0da8544fd917d74d6f0ab547a5808d93129e0adf7ba1d3"
                },
                "resources": resources,
                "claim_decisions": [
                    {"claim_id": "claim-product-CPR-0001", "approved": True}
                ],
            },
        )

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

        self.assertTrue(
            any(
                f["rule_id"] == "vault_brand_language_alignment_missing"
                for f in findings
            )
        )
        self.assertTrue(should_fail(findings, fail_on="error"))

    def test_valid_product_feature_alignment_block_passes(self):
        pack, receipt = self._validated_artifacts()
        findings = check_content(
            "# Job quoting software\n\n"
            "Simpro field service management software helps teams manage quoting and invoicing.",
            proof_content=VALID_PRODUCT_SIDECAR,
            context_pack=pack,
            context_receipt=receipt,
        )

        self.assertEqual(findings, [])

    def test_well_shaped_but_unbound_connector_evidence_fails(self):
        pack, receipt = self._validated_artifacts()
        sidecar = VALID_PRODUCT_SIDECAR.replace(
            "res-641679c4b6c65e93951cb8d8e1ab88af",
            "res-11111111111111111111111111111111",
        ).replace(
            "claim-product-CPR-0001",
            "claim-product-CPR-9999",
        )

        findings = check_content(
            "# Job quoting software\n\n"
            "Simpro field service management software helps teams manage quoting and invoicing.",
            proof_content=sidecar,
            context_pack=pack,
            context_receipt=receipt,
        )
        rule_ids = {finding["rule_id"] for finding in findings}

        self.assertIn("vault_brand_language_resource_id_unbound", rule_ids)
        self.assertIn("vault_brand_language_claim_id_unbound", rule_ids)

    def test_named_feature_rejects_bound_voice_only_resource(self):
        pack, receipt = self._validated_artifacts()
        voice_resource_id = "res-641679c4b6c65e93951cb8d8e1ab88af"
        sidecar = VALID_PRODUCT_SIDECAR.replace(
            "feature resource_id=res-ad3ee1bcd777586d81415ba9298cd755",
            f"feature resource_id={voice_resource_id}",
        )

        findings = check_content(
            "# Digital Forms\n\nSimpro Digital Forms supports digital recordkeeping.",
            proof_content=sidecar,
            context_pack=pack,
            context_receipt=receipt,
        )

        self.assertIn(
            "vault_brand_language_feature_resource_semantics_invalid",
            {finding["rule_id"] for finding in findings},
        )

    def test_named_feature_accepts_matching_connector_semantic_metadata(self):
        pack, receipt = self._validated_artifacts()

        findings = check_content(
            "# Digital Forms\n\nSimpro Digital Forms supports digital recordkeeping.",
            proof_content=VALID_PRODUCT_SIDECAR,
            context_pack=pack,
            context_receipt=receipt,
        )

        self.assertEqual(findings, [])

    def test_named_feature_does_not_match_across_unrelated_metadata_fields(self):
        pack, receipt = self._validated_artifacts()
        feature_resource_id = "res-ad3ee1bcd777586d81415ba9298cd755"
        feature_row = next(
            row
            for row in pack["sections"]["Selected Resource Inventory"]
            if row["resource_id"] == feature_resource_id
        )
        feature_row.update(
            {
                "title": "Feature guidance",
                "aliases": ["Digital"],
                "headings": ["Forms"],
                "topics": ["product feature"],
                "semantic_roles": ["guidance"],
            }
        )

        findings = check_content(
            "# Digital Forms\n\nSimpro Digital Forms supports digital recordkeeping.",
            proof_content=VALID_PRODUCT_SIDECAR,
            context_pack=pack,
            context_receipt=receipt,
        )

        self.assertIn(
            "vault_brand_language_feature_resource_semantics_invalid",
            {finding["rule_id"] for finding in findings},
        )

    def test_feature_semantic_check_fails_closed_without_context_artifacts(self):
        findings = check_content(
            "# Digital Forms\n\nSimpro Digital Forms supports digital recordkeeping.",
            proof_content=VALID_PRODUCT_SIDECAR,
        )

        self.assertIn(
            "vault_brand_language_feature_resource_semantics_invalid",
            {finding["rule_id"] for finding in findings},
        )

    def test_named_feature_requires_specific_feature_resource_evidence(self):
        sidecar = VALID_PRODUCT_SIDECAR.replace(
            "; feature resource_id=res-ad3ee1bcd777586d81415ba9298cd755",
            "",
        )

        findings = check_content(
            "# Digital Forms\n\n"
            "Simpro Digital Forms turns paper recordkeeping into searchable digital records.",
            proof_content=sidecar,
        )

        self.assertTrue(
            any(
                f["rule_id"] == "vault_brand_language_feature_resource_missing"
                for f in findings
            )
        )

    def test_sidecar_declared_feature_is_not_limited_to_static_aliases(self):
        sidecar = VALID_PRODUCT_SIDECAR.replace(
            "; feature resource_id=res-ad3ee1bcd777586d81415ba9298cd755",
            "",
        ) + (
            "\n## Named Feature Status and Commercial Treatment\n\n"
            "| Name | Capability claim ID | Commercial claim ID | Release status | Commercial treatment | Region or account boundary | Public wording decision |\n"
            "|---|---|---|---|---|---|---|\n"
            "| AI CSR Agent | | | roadmap | not_asserted | Not publicly available | omit |\n"
        )

        findings = check_content(
            "# AI roadmap\n\nThe AI CSR Agent is described for Simpro teams.",
            proof_content=sidecar,
        )

        self.assertTrue(
            any(
                f["rule_id"] == "vault_brand_language_feature_resource_missing"
                for f in findings
            )
        )

    def test_solution_industry_scope_requires_vertical_resource_evidence(self):
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

        self.assertTrue(
            any(
                f["rule_id"] == "vault_brand_language_vertical_resource_missing"
                for f in findings
            )
        )

    def test_solution_industry_scope_passes_with_vertical_resource_evidence(self):
        pack, receipt = self._validated_artifacts()
        sidecar = VALID_PRODUCT_SIDECAR.replace(
            "Product/solution language scope: product/feature",
            "Product/solution language scope: solution/industry",
        ).replace(
            "resource_id=res-641679c4b6c65e93951cb8d8e1ab88af; feature resource_id=res-ad3ee1bcd777586d81415ba9298cd755;",
            "resource_id=res-641679c4b6c65e93951cb8d8e1ab88af; feature resource_id=res-ad3ee1bcd777586d81415ba9298cd755; vertical resource_id=res-d31f057a305f51918055120d95b76c6a;",
        )

        findings = check_content(
            "# Electrical field service software\n\n"
            "See field service management options for [electrical contractors]"
            "(https://www.simprogroup.com/industries/electrical).",
            proof_content=sidecar,
            context_pack=pack,
            context_receipt=receipt,
        )

        self.assertEqual(findings, [])

    def test_industry_software_slug_accepts_matching_vertical_profile_resource(self):
        pack, receipt = self._validated_artifacts()
        vertical_resource_id = "res-25a1152f611e5cd69ba57cf16b34a826"
        resource = {
            "resource_id": vertical_resource_id,
            "title": "Electrical Vertical Profile",
            "aliases": [],
            "headings": ["Electrical Vertical Profile", "Trade Snapshot"],
            "topics": ["electrical", "vertical", "profile", "trade"],
            "semantic_roles": ["routing"],
        }
        pack["sections"]["Discovery Trace"]["selected_resource_ids"].append(
            vertical_resource_id
        )
        pack["sections"]["Retrieved Guidance"].append(resource)
        pack["sections"]["Selected Resource Inventory"].append(resource)
        receipt["resources"].append(resource)
        sidecar = VALID_PRODUCT_SIDECAR.replace(
            "Product/solution language scope: product/feature",
            "Product/solution language scope: solution/industry",
        ).replace(
            "resource_id=res-641679c4b6c65e93951cb8d8e1ab88af; feature resource_id=res-ad3ee1bcd777586d81415ba9298cd755;",
            "resource_id=res-641679c4b6c65e93951cb8d8e1ab88af; "
            "feature resource_id=res-ad3ee1bcd777586d81415ba9298cd755; "
            f"vertical resource_id={vertical_resource_id};",
        )

        findings = check_content(
            "# CRM for electricians\n\n"
            "CRM should fit the wider [electrical contractor software]"
            "(https://www.simprogroup.com/industries/electrical-software) stack.",
            proof_content=sidecar,
            context_pack=pack,
            context_receipt=receipt,
        )

        self.assertEqual(findings, [])

    def test_solution_industry_rejects_bound_voice_only_resource(self):
        pack, receipt = self._validated_artifacts()
        voice_resource_id = "res-641679c4b6c65e93951cb8d8e1ab88af"
        sidecar = VALID_PRODUCT_SIDECAR.replace(
            "Product/solution language scope: product/feature",
            "Product/solution language scope: solution/industry",
        ).replace(
            "feature resource_id=res-ad3ee1bcd777586d81415ba9298cd755;",
            f"feature resource_id=res-ad3ee1bcd777586d81415ba9298cd755; vertical resource_id={voice_resource_id};",
        )

        findings = check_content(
            "# Electrical field service software\n\n"
            "See field service management options for [electrical contractors]"
            "(https://www.simprogroup.com/industries/electrical).",
            proof_content=sidecar,
            context_pack=pack,
            context_receipt=receipt,
        )

        self.assertIn(
            "vault_brand_language_vertical_resource_semantics_invalid",
            {finding["rule_id"] for finding in findings},
        )

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

        self.assertTrue(
            any(
                f["rule_id"] == "vault_brand_language_fallback_without_blocker"
                for f in findings
            )
        )

    def test_spoofed_connector_evidence_values_fail(self):
        sidecar = VALID_PRODUCT_SIDECAR.replace(
            VALID_PRODUCT_SIDECAR.split("- Vault connector evidence: ", 1)[
                1
            ].splitlines()[0],
            (
                "vault_status ready; context_pack_hash=present; receipt_hash=present; "
                "resource_id=placeholder; claim_id=example; manifest_revision=current"
            ),
        )

        findings = check_content(
            "# Job quoting software\n\nSimpro field service management software supports quoting.",
            proof_content=sidecar,
        )
        rule_ids = {finding["rule_id"] for finding in findings}

        self.assertIn("vault_brand_language_context_pack_hash_invalid", rule_ids)
        self.assertIn("vault_brand_language_receipt_hash_invalid", rule_ids)
        self.assertIn("vault_brand_language_resource_id_invalid", rule_ids)
        self.assertIn("vault_brand_language_manifest_revision_invalid", rule_ids)
        self.assertIn("vault_brand_language_claim_id_missing", rule_ids)

    def test_declared_proof_sensitive_language_requires_claim_id(self):
        sidecar = VALID_PRODUCT_SIDECAR.replace(
            "; claim_id=claim-product-CPR-0001",
            "",
        )

        findings = check_content(
            "# Job quoting software\n\nSimpro field service management software supports quoting.",
            proof_content=sidecar,
        )

        self.assertTrue(
            any(
                f["rule_id"] == "vault_brand_language_claim_id_missing"
                for f in findings
            )
        )

    def test_no_declared_proof_sensitive_language_does_not_require_claim_id(self):
        sidecar = VALID_PRODUCT_SIDECAR.replace(
            "; claim_id=claim-product-CPR-0001",
            "",
        ).replace(
            "Claims requiring source verification: mapped in Source Map / Customer Proof Pack / Metric Proof Pack",
            "Claims requiring source verification: none",
        )

        findings = check_content(
            "# Job quoting software\n\nSimpro field service management software supports quoting.",
            proof_content=sidecar,
        )

        self.assertEqual(findings, [])

    def test_human_readable_backticked_connector_values_pass(self):
        pack, receipt = self._validated_artifacts()
        sidecar = VALID_PRODUCT_SIDECAR.replace(
            VALID_PRODUCT_SIDECAR.split("- Vault connector evidence: ", 1)[
                1
            ].splitlines()[0],
            (
                "context_pack_hash `0bb54c045bee7316652b3420389615a8062f6b3b654dd56630a28b2501f060a8`; "
                "receipt_hash `79a12fa9ec9e3287658f44a273dca3b393e557b25bfd564cc6c201ff3620eab9`; "
                "resource_id `res-641679c4b6c65e93951cb8d8e1ab88af`; "
                "feature resource_id `res-ad3ee1bcd777586d81415ba9298cd755`; "
                "claim_id `claim-product-CPR-0001`; "
                "manifest_revision `479e1c3ddcc8d3829b0da8544fd917d74d6f0ab547a5808d93129e0adf7ba1d3`"
            ),
        )

        findings = check_content(
            "# Digital Forms\n\nSimpro Digital Forms supports digital records.",
            proof_content=sidecar,
            context_pack=pack,
            context_receipt=receipt,
        )

        self.assertEqual(findings, [])


if __name__ == "__main__":
    unittest.main()
