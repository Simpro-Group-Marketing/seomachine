import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from data_sources.modules import context_binding_generator, context_binding_guard


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


class ValidatingClient:
    def validate_context(self, request, pack, receipt):
        return {"valid": True, "errors": []}


class ContextBindingGuardTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.root = Path(self.temp_dir.name)
        self.article = self.root / "draft.md"
        self.article.write_text(
            "# Simpro draft\n\nSimpro helps teams coordinate work.\n",
            encoding="utf-8",
        )
        self.request = self.root / "context-request-draft.json"
        self.pack = self.root / "context-pack-draft.json"
        self.receipt = self.root / "context-receipt-draft.json"
        self.sidecar = self.root / "validation-draft.md"
        request = {
            "task": "Draft a Simpro blog.",
            "scope": {
                "artifact_type": "blog",
                "brand": "simpro",
                "title": "Simpro draft",
                "objective": "Explain coordinated work.",
                "audience": "field service leaders",
                "region": "US",
                "intended_public_use_modes": ["paraphrase"],
            },
        }
        pack = {
            "schema": "simpro-product-context-pack/v2",
            "revisions": {
                "approval_policy_revision": "policy-r1",
                "claim_registry_revision": "claims-r1",
                "content_revision": "content-r1",
                "contract_revision": "contract-r1",
                "inventory_revision": "inventory-r1",
                "manifest_revision": "manifest-r1",
            },
            "claim_registry_revision": "claims-r1",
            "sections": {
                "Task and Scope": {
                    "task": request["task"],
                    "scope": request["scope"],
                    "task_satisfaction": "satisfied",
                },
                "Discovery Trace": {
                    "entries": [],
                    "selected_resource_ids": ["res-guidance"],
                },
                "Retrieved Guidance": [],
                "Approved Claim Evidence": [
                    {
                        "claim_id": "claim-simpro-work",
                        "use_mode": "paraphrase",
                        "brand_scope": "simpro",
                        "public_url": "https://www.simprogroup.com/",
                        "assertion": "Simpro helps teams coordinate work.",
                    }
                ],
                "Constraints and Unresolved Gaps": {
                    "constraints": [],
                    "unresolved_gaps": [],
                },
                "Selected Resource Inventory": [
                    {
                        "resource_id": "res-guidance",
                        "locator": "renamed/guidance.md",
                        "content_sha256": "resource-hash",
                    }
                ],
            },
        }
        receipt = {
            "schema": "simpro-context-receipt/v1",
            "request_sha256": "request-canonical-hash",
            "pack_sha256": "pack-canonical-hash",
            "receipt_sha256": "receipt-canonical-hash",
            "revisions": pack["revisions"],
            "claim_registry_revision": "claims-r1",
            "resources": pack["sections"]["Selected Resource Inventory"],
            "claim_decisions": [
                {
                    "claim_id": "claim-simpro-work",
                    "approved": True,
                    "use_mode": "paraphrase",
                    "brand_scope": "simpro",
                }
            ],
            "task_satisfaction": "satisfied",
            "unresolved_gaps": [],
        }
        self.request.write_text(json.dumps(request), encoding="utf-8")
        self.pack.write_text(json.dumps(pack), encoding="utf-8")
        self.receipt.write_text(json.dumps(receipt), encoding="utf-8")
        binding = context_binding_guard.build_binding(
            self.article,
            self.request,
            self.pack,
            self.receipt,
            repo_context=[
                {
                    "path": "context/seo-guidelines.md",
                    "role": "SEO structure",
                }
            ],
        )
        public_text = "Simpro helps teams coordinate work."
        claim_map = [
            {
                "claim_id": "claim-simpro-work",
                "use_mode": "paraphrase",
                "brand_scope": "simpro",
                "public_url": "https://www.simprogroup.com/",
                "public_text": public_text,
                "public_text_sha256": sha256_text(public_text),
            }
        ]
        self.sidecar.write_text(
            context_binding_guard.render_generated_blocks(binding, claim_map),
            encoding="utf-8",
        )

    def check(self):
        return context_binding_guard.check_file(
            self.article,
            proof_sidecar=self.sidecar,
            context_request=self.request,
            context_pack=self.pack,
            context_receipt=self.receipt,
            client=ValidatingClient(),
        )

    def write_current_sidecar(self, claim_map):
        binding = context_binding_guard.build_binding(
            self.article,
            self.request,
            self.pack,
            self.receipt,
            repo_context=[],
        )
        self.sidecar.write_text(
            context_binding_guard.render_generated_blocks(binding, claim_map),
            encoding="utf-8",
        )

    def write_resource_only_context(self, article_text, legacy_sidecar):
        self.article.write_text(f"# Simpro draft\n\n{article_text}\n", encoding="utf-8")
        pack = json.loads(self.pack.read_text(encoding="utf-8"))
        receipt = json.loads(self.receipt.read_text(encoding="utf-8"))
        pack["sections"]["Approved Claim Evidence"] = []
        receipt["claim_decisions"] = []
        self.pack.write_text(json.dumps(pack), encoding="utf-8")
        self.receipt.write_text(json.dumps(receipt), encoding="utf-8")
        binding = context_binding_guard.build_binding(
            self.article,
            self.request,
            self.pack,
            self.receipt,
            repo_context=[],
        )
        generated = context_binding_guard.render_generated_blocks(binding, [])
        self.sidecar.write_text(f"{legacy_sidecar.strip()}\n\n{generated}", encoding="utf-8")

    def write_typed_claim_context(self, article_text, use_mode, *, verbatim=None):
        self.article.write_text(f"# Simpro draft\n\n{article_text}\n", encoding="utf-8")
        pack = json.loads(self.pack.read_text(encoding="utf-8"))
        receipt = json.loads(self.receipt.read_text(encoding="utf-8"))
        evidence = pack["sections"]["Approved Claim Evidence"][0]
        evidence.update(
            {
                "use_mode": use_mode,
                "assertion": article_text,
                "public_url": "https://www.simprogroup.com/customers/example/",
            }
        )
        if verbatim is not None:
            evidence["verbatim_evidence"] = {
                "text": verbatim,
                "text_sha256": sha256_text(verbatim),
                "resource_id": "res-guidance",
                "public_url": evidence["public_url"],
            }
        receipt["claim_decisions"][0]["use_mode"] = use_mode
        self.pack.write_text(json.dumps(pack), encoding="utf-8")
        self.receipt.write_text(json.dumps(receipt), encoding="utf-8")
        public_text = verbatim if use_mode == "exact_quote" else article_text
        self.write_current_sidecar(
            [
                {
                    "claim_id": "claim-simpro-work",
                    "use_mode": use_mode,
                    "brand_scope": "simpro",
                    "public_url": evidence["public_url"],
                    "public_text": public_text,
                    "public_text_sha256": sha256_text(public_text),
                }
            ]
        )
    def test_valid_current_binding_and_claim_map_pass(self):
        self.assertEqual(self.check(), [])

    def test_resource_only_pack_cannot_authorize_metric_with_legacy_approved_status(self):
        article_text = "Simpro customers reduced administrative time by 25%."
        self.write_resource_only_context(
            article_text,
            """
## Metric Proof Pack

- Metric requirement: required
- Search log: legacy proof reviewed
- Approved metric: Simpro customers reduced administrative time by 25%. | URL: https://www.simprogroup.com/customers/example/ | Evidence: reduced administrative time by 25% | Status: approved | Use: public metric
""",
        )

        findings = self.check()

        self.assertTrue(
            any(
                finding["rule_id"] == "context_proof_claim_unbound"
                and finding.get("proof_kind") == "metric"
                for finding in findings
            )
        )

    def test_hidden_html_proof_does_not_create_public_proof_obligation(self):
        self.write_resource_only_context(
            '<div style="display:none">Simpro customers reduced administrative time by 25%.</div>\n'
            "Visible editorial guidance.",
            "",
        )

        findings = self.check()

        self.assertFalse(
            any(finding["rule_id"] == "context_proof_claim_unbound" for finding in findings),
            findings,
        )

    def test_resource_only_pack_cannot_authorize_exact_quote_with_legacy_approved_status(self):
        quote = "Simpro gives our technicians one place to work from."
        article_text = f'A customer said, "{quote}"'
        self.write_resource_only_context(
            article_text,
            f"""
## Customer Proof Pack

- Approved quote: {quote} | Customer/brand: Example Customer | URL: https://www.simprogroup.com/customers/example/ | Evidence: {quote} | Status: approved | Use: exact quote
""",
        )

        findings = self.check()

        self.assertTrue(
            any(
                finding["rule_id"] == "context_proof_claim_unbound"
                and finding.get("proof_kind") == "exact_quote"
                for finding in findings
            )
        )

    def test_resource_only_pack_cannot_authorize_unattributed_exact_quote(self):
        quote = "Simpro gives our technicians one place to work from."
        self.write_resource_only_context(
            f'"{quote}"',
            f"""
## Customer Proof Pack

- Approved quote: {quote} | Customer/brand: Example Customer | URL: https://www.simprogroup.com/customers/example/ | Evidence: {quote} | Status: approved | Use: exact quote
""",
        )

        findings = self.check()

        self.assertTrue(
            any(
                finding["rule_id"] == "context_proof_claim_unbound"
                and finding.get("proof_kind") == "exact_quote"
                for finding in findings
            )
        )
    def test_resource_only_pack_cannot_authorize_review_theme_with_legacy_approved_status(self):
        article_text = "Capterra reviewers describe Simpro as making scheduling easier."
        self.write_resource_only_context(
            article_text,
            """
## Review Site Theme Selection

- Platform: Capterra
- Workflow theme: easier scheduling
- URL: https://www.capterra.com/p/10529/Simpro-Enterprise/reviews/
- Status: approved for paraphrased review-theme use
""",
        )

        findings = self.check()

        self.assertTrue(
            any(
                finding["rule_id"] == "context_proof_claim_unbound"
                and finding.get("proof_kind") == "review_theme"
                for finding in findings
            )
        )

    def test_resource_only_pack_cannot_authorize_customer_proof_with_legacy_approved_status(self):
        article_text = (
            "[Example Customer](https://www.simprogroup.com/customers/example/) "
            "reduced administrative work with Simpro."
        )
        self.write_resource_only_context(
            article_text,
            """
## Customer Proof Pack

- Claim: Example Customer reduced administrative work with Simpro. | URL: https://www.simprogroup.com/customers/example/ | Evidence: reduced administrative work | Status: approved | Use: customer proof
""",
        )

        findings = self.check()

        self.assertTrue(
            any(
                finding["rule_id"] == "context_proof_claim_unbound"
                and finding.get("proof_kind") == "customer_proof"
                for finding in findings
            )
        )

    def test_resource_only_pack_cannot_authorize_commercial_claim_with_legacy_approved_status(self):
        article_text = "Simpro helps field service businesses reduce administrative work."
        self.write_resource_only_context(
            article_text,
            """
## Source Map

- Claim: Simpro helps field service businesses reduce administrative work. | URL: https://www.simprogroup.com/ | Evidence: product guidance | Status: approved | Use: commercial proof
""",
        )

        findings = self.check()

        self.assertTrue(
            any(
                finding["rule_id"] == "context_proof_claim_unbound"
                and finding.get("proof_kind") == "commercial_claim"
                for finding in findings
            )
        )

    def test_typed_receipt_claims_authorize_matching_proof_obligations(self):
        cases = (
            (
                "metric",
                "Simpro customers reduced administrative time by 25%.",
                "public_metric",
                None,
            ),
            (
                "exact_quote",
                'A customer said, "Simpro gives our technicians one place to work from."',
                "exact_quote",
                "Simpro gives our technicians one place to work from.",
            ),
            (
                "review_theme",
                "Capterra reviewers describe Simpro as making scheduling easier.",
                "public_paraphrase",
                None,
            ),
            (
                "customer_proof",
                "Example Customer case study shows Simpro reduced administrative work.",
                "public_paraphrase",
                None,
            ),
            (
                "commercial_claim",
                "Simpro helps field service businesses reduce administrative work.",
                "public_claim",
                None,
            ),
        )
        for proof_kind, article_text, use_mode, verbatim in cases:
            with self.subTest(proof_kind=proof_kind):
                self.write_typed_claim_context(article_text, use_mode, verbatim=verbatim)

                findings = self.check()

                self.assertFalse(
                    any(
                        finding["rule_id"] == "context_proof_claim_unbound"
                        and finding.get("proof_kind") == proof_kind
                        for finding in findings
                    ),
                    findings,
                )
    def test_typed_receipt_claim_with_incompatible_use_mode_does_not_authorize_passage(self):
        article_text = "Simpro customers reduced administrative time by 25%."
        self.write_typed_claim_context(article_text, "public_claim")

        findings = self.check()

        self.assertTrue(
            any(
                finding["rule_id"] == "context_proof_claim_unbound"
                and finding.get("proof_kind") == "metric"
                and finding.get("required_use_modes") == ["public_metric"]
                for finding in findings
            )
        )
    def test_explicit_non_simpro_article_with_simpro_copy_requires_context(self):
        self.article.write_text(
            "---\nbrand: BigChange\nartifact_type: blog\ntitle: Simpro comparison\n---\n"
            "# Simpro comparison\n\nBigChange comparison copy mentions Simpro.\n",
            encoding="utf-8",
        )

        findings = context_binding_guard.check_file(self.article)

        self.assertTrue(
            any(finding["rule_id"] == "context_request_missing" for finding in findings)
        )

    def test_explicit_non_simpro_article_without_simpro_copy_is_exempt(self):
        self.article.write_text(
            "---\nbrand: BigChange\nartifact_type: blog\ntitle: Job management\n---\n"
            "# Job management\n\nBigChange workflow copy.\n",
            encoding="utf-8",
        )

        self.assertEqual(context_binding_guard.check_file(self.article), [])

    def test_unbranded_article_fails_safe_into_context_workflow(self):
        self.article.write_text("# Generic workflow article\n\nField service guidance.\n", encoding="utf-8")

        findings = context_binding_guard.check_file(self.article)

        self.assertTrue(
            any(finding["rule_id"] == "context_request_missing" for finding in findings)
        )

    def test_landing_page_request_is_a_supported_context_artifact(self):
        request = json.loads(self.request.read_text(encoding="utf-8"))
        request["scope"]["artifact_type"] = "landing_page"
        request["scope"]["title"] = "Simpro landing page"
        article = (
            "---\nbrand: Simpro\nartifact_type: landing_page\ntitle: Simpro landing page\n---\n"
            "# Simpro landing page\n"
        )

        self.assertEqual(
            context_binding_guard.validate_request_article(request, article),
            [],
        )

    def test_binding_exposes_current_approval_policy_revision(self):
        binding = context_binding_guard.build_binding(
            self.article,
            self.request,
            self.pack,
            self.receipt,
            repo_context=[
                {
                    "path": "context/seo-guidelines.md",
                    "role": "SEO structure",
                }
            ],
        )

        self.assertEqual(binding["approval_policy_revision"], "policy-r1")
        self.assertEqual(binding["claim_registry_revision"], "claims-r1")

    def test_binding_rejects_repo_context_that_claims_factual_authority(self):
        with self.assertRaises(ValueError):
            context_binding_guard.build_binding(
                self.article,
                self.request,
                self.pack,
                self.receipt,
                repo_context=[
                    {
                        "path": "context/features.md",
                        "role": "Simpro product facts",
                    }
                ],
            )

    def test_repository_context_uses_explicit_path_and_role_allowlist(self):
        allowed = [
            ("context/seo-guidelines.md", "SEO structure"),
            ("context/aeo-geo-blog-strategy.md", "AEO/GEO workflow"),
            ("context/style-guide.md", "Editorial mechanics"),
            ("context/target-keywords.md", "Keyword data"),
            ("context/internal-links-map.md", "Internal-link inventory"),
            ("context/cro-best-practices.md", "CRO guidance"),
            ("context/reddit-strategy.md", "Reddit strategy"),
            ("context/writing-examples.md", "Writing examples"),
            ("context/field-service-management-platform-faq-list.md", "FAQ questions and formatting"),
            ("context/customer-proof-usage-ledger.json", "Proof usage tracking"),
        ]

        for path, role in allowed:
            with self.subTest(path=path, role=role):
                binding = context_binding_guard.build_binding(
                    self.article,
                    self.request,
                    self.pack,
                    self.receipt,
                    repo_context=[{"path": path, "role": role}],
                )
                self.assertEqual(binding["repo_context"], [{"path": path, "role": role}])

    def test_repository_context_rejects_non_allowlisted_paths_and_roles(self):
        blocked = [
            ("context/competitor-analysis.md", "SEO structure"),
            ("context/reference/features.md", "SEO structure"),
            ("context/brand-voice.md", "Editorial mechanics"),
            ("context/lightning-positioning.md", "SEO structure"),
            ("context/customer-proof-index.json", "Proof usage tracking"),
            ("context/seo-guidelines.md", "Simpro product facts"),
            ("context/arbitrary.md", "SEO structure"),
        ]

        for path, role in blocked:
            with self.subTest(path=path, role=role), self.assertRaises(ValueError):
                context_binding_guard.build_binding(
                    self.article,
                    self.request,
                    self.pack,
                    self.receipt,
                    repo_context=[{"path": path, "role": role}],
                )

    def test_invalid_repo_context_in_sidecar_returns_structured_finding(self):
        binding = context_binding_guard.build_binding(
            self.article,
            self.request,
            self.pack,
            self.receipt,
            repo_context=[],
        )
        binding["repo_context"] = [
            {
                "path": "context/features.md",
                "role": "Simpro product facts",
            }
        ]
        public_text = "Simpro helps teams coordinate work."
        claim_map = [
            {
                "claim_id": "claim-simpro-work",
                "use_mode": "paraphrase",
                "brand_scope": "simpro",
                "public_url": "https://www.simprogroup.com/",
                "public_text": public_text,
                "public_text_sha256": sha256_text(public_text),
            }
        ]
        self.sidecar.write_text(
            context_binding_guard.render_generated_blocks(binding, claim_map),
            encoding="utf-8",
        )

        findings = self.check()

        self.assertIn(
            "context_binding_invalid",
            {finding["rule_id"] for finding in findings},
        )

    def test_article_edit_invalidates_binding(self):
        self.article.write_text(
            self.article.read_text(encoding="utf-8") + "\nChanged after binding.\n",
            encoding="utf-8",
        )

        findings = self.check()

        self.assertIn(
            "context_article_hash_mismatch",
            {finding["rule_id"] for finding in findings},
        )

    def test_unmapped_receipt_claim_blocks_publication(self):
        binding = context_binding_guard.build_binding(
            self.article,
            self.request,
            self.pack,
            self.receipt,
            repo_context=[],
        )
        self.sidecar.write_text(
            context_binding_guard.render_generated_blocks(binding, []),
            encoding="utf-8",
        )

        findings = self.check()

        self.assertIn(
            "context_claim_use_missing",
            {finding["rule_id"] for finding in findings},
        )

    def test_connector_staleness_error_fails_closed(self):
        class StaleClient:
            def validate_context(self, request, pack, receipt):
                raise context_binding_guard.VaultClientError(
                    "pack_stale",
                    "Pack revisions are stale",
                )

        findings = context_binding_guard.check_file(
            self.article,
            proof_sidecar=self.sidecar,
            context_request=self.request,
            context_pack=self.pack,
            context_receipt=self.receipt,
            client=StaleClient(),
        )

        self.assertEqual(findings[0]["rule_id"], "context_pack_stale")

    def test_unset_root_returns_structured_finding_instead_of_aborting(self):
        with patch(
            "data_sources.modules.context_binding_guard.SimproVaultClient",
            side_effect=context_binding_guard.VaultClientError(
                "root_unset",
                "Configure the vault root",
            ),
        ):
            findings = context_binding_guard.check_file(
                self.article,
                proof_sidecar=self.sidecar,
                context_request=self.request,
                context_pack=self.pack,
                context_receipt=self.receipt,
            )

        self.assertEqual(findings[0]["rule_id"], "context_root_unset")
        self.assertEqual(findings[0]["connector_error_code"], "root_unset")

    def test_request_missing_required_blog_scope_blocks_before_live_validation(self):
        request = json.loads(self.request.read_text(encoding="utf-8"))
        del request["scope"]["region"]
        self.request.write_text(json.dumps(request), encoding="utf-8")

        findings = self.check()

        self.assertIn(
            "context_request_scope_invalid",
            {finding["rule_id"] for finding in findings},
        )

    def test_missing_approval_policy_revision_blocks_before_live_validation(self):
        pack = json.loads(self.pack.read_text(encoding="utf-8"))
        receipt = json.loads(self.receipt.read_text(encoding="utf-8"))
        del pack["revisions"]["approval_policy_revision"]
        del receipt["revisions"]["approval_policy_revision"]
        self.pack.write_text(json.dumps(pack), encoding="utf-8")
        self.receipt.write_text(json.dumps(receipt), encoding="utf-8")

        findings = self.check()

        self.assertIn(
            "context_revisions_invalid",
            {finding["rule_id"] for finding in findings},
        )

    def test_request_title_must_match_article_h1(self):
        request = json.loads(self.request.read_text(encoding="utf-8"))
        request["scope"]["title"] = "An unrelated article"
        self.request.write_text(json.dumps(request), encoding="utf-8")

        findings = self.check()

        self.assertIn(
            "context_request_article_mismatch",
            {finding["rule_id"] for finding in findings},
        )

    def test_cross_brand_article_accepts_simpro_authority_scope_with_matching_artifact_brand(self):
        self.article.write_text(
            "---\nbrand: BigChange\nartifact_type: blog\ntitle: Simpro draft\n---\n"
            "# Simpro draft\n\nSimpro helps teams coordinate work.\n",
            encoding="utf-8",
        )
        request = json.loads(self.request.read_text(encoding="utf-8"))
        request["scope"]["artifact_brand"] = "BigChange"
        self.request.write_text(json.dumps(request), encoding="utf-8")

        findings = self.check()

        self.assertNotIn(
            "context_request_article_mismatch",
            {finding["rule_id"] for finding in findings},
        )

    def test_cross_brand_article_requires_explicit_artifact_brand(self):
        self.article.write_text(
            "---\nbrand: BigChange\nartifact_type: blog\ntitle: Simpro draft\n---\n"
            "# Simpro draft\n\nSimpro helps teams coordinate work.\n",
            encoding="utf-8",
        )

        findings = self.check()

        self.assertIn(
            "context_request_article_mismatch",
            {finding["rule_id"] for finding in findings},
        )

    def test_cross_brand_article_rejects_mismatched_artifact_brand(self):
        self.article.write_text(
            "---\nbrand: ClockShark\nartifact_type: blog\ntitle: Simpro draft\n---\n"
            "# Simpro draft\n\nSimpro helps teams coordinate work.\n",
            encoding="utf-8",
        )
        request = json.loads(self.request.read_text(encoding="utf-8"))
        request["scope"]["artifact_brand"] = "AroFlo"
        self.request.write_text(json.dumps(request), encoding="utf-8")

        findings = self.check()

        self.assertIn(
            "context_request_article_mismatch",
            {finding["rule_id"] for finding in findings},
        )
    def test_request_artifact_type_must_match_article_frontmatter(self):
        self.article.write_text(
            "---\nbrand: Simpro\nartifact_type: landing_page\ntitle: Simpro draft\n---\n"
            "# Simpro draft\n\nSimpro helps teams coordinate work.\n",
            encoding="utf-8",
        )

        findings = self.check()

        self.assertIn(
            "context_request_article_mismatch",
            {finding["rule_id"] for finding in findings},
        )

    def test_article_must_declare_artifact_type_before_binding(self):
        request = json.loads(self.request.read_text(encoding="utf-8"))
        findings = context_binding_guard.validate_request_article(
            request,
            "---\nbrand: Simpro\ntitle: Simpro draft\n---\n"
            "# Simpro draft\n\nSimpro helps teams coordinate work.\n",
        )

        self.assertIn(
            "context_request_article_mismatch",
            {finding["rule_id"] for finding in findings},
        )
        self.assertTrue(
            any("artifact type" in finding["message"].lower() for finding in findings)
        )

    def test_request_contradictory_artifact_fields_return_scope_mismatch(self):
        request = json.loads(self.request.read_text(encoding="utf-8"))
        request["scope"]["artifact_kind"] = "landing_page"
        self.request.write_text(json.dumps(request), encoding="utf-8")

        findings = self.check()

        self.assertIn(
            "context_request_scope_mismatch",
            {finding["rule_id"] for finding in findings},
        )

    def test_request_unsupported_artifact_kind_returns_stable_invalid_scope(self):
        request = json.loads(self.request.read_text(encoding="utf-8"))
        request["scope"]["artifact_kind"] = "brochure"
        self.request.write_text(json.dumps(request), encoding="utf-8")

        findings = self.check()

        self.assertIn(
            "context_request_scope_invalid",
            {finding["rule_id"] for finding in findings},
        )

    def test_article_contradictory_artifact_fields_return_stable_mismatch(self):
        self.article.write_text(
            "---\nbrand: Simpro\nartifact_type: blog\nartifact_kind: landing_page\n"
            "title: Simpro draft\n---\n# Simpro draft\n\n"
            "Simpro helps teams coordinate work.\n",
            encoding="utf-8",
        )

        findings = self.check()

        self.assertIn(
            "context_request_article_mismatch",
            {finding["rule_id"] for finding in findings},
        )

    def test_article_unsupported_artifact_field_returns_stable_mismatch(self):
        self.article.write_text(
            "---\nbrand: Simpro\nartifact_kind: brochure\ntitle: Simpro draft\n---\n"
            "# Simpro draft\n\nSimpro helps teams coordinate work.\n",
            encoding="utf-8",
        )

        findings = self.check()

        self.assertIn(
            "context_request_article_mismatch",
            {finding["rule_id"] for finding in findings},
        )

    def test_every_claim_map_row_is_validated_without_claim_id_collapse(self):
        valid_text = "Simpro helps teams coordinate work."
        self.write_current_sidecar(
            [
                {
                    "claim_id": "claim-simpro-work",
                    "use_mode": "paraphrase",
                    "brand_scope": "simpro",
                    "public_url": "https://www.simprogroup.com/",
                    "public_text": "This passage is not in the article.",
                    "public_text_sha256": sha256_text("This passage is not in the article."),
                },
                {
                    "claim_id": "claim-simpro-work",
                    "use_mode": "paraphrase",
                    "brand_scope": "simpro",
                    "public_url": "https://www.simprogroup.com/",
                    "public_text": valid_text,
                    "public_text_sha256": sha256_text(valid_text),
                },
            ]
        )

        findings = self.check()

        self.assertIn(
            "context_claim_public_text_mismatch",
            {finding["rule_id"] for finding in findings},
        )

    def test_paraphrase_and_public_paraphrase_must_equal_approved_assertion(self):
        for use_mode in ("paraphrase", "public_paraphrase"):
            with self.subTest(use_mode=use_mode):
                article_text = "This is unrelated copy with a recomputed passage hash."
                self.article.write_text(f"# Simpro draft\n\n{article_text}\n", encoding="utf-8")
                pack = json.loads(self.pack.read_text(encoding="utf-8"))
                receipt = json.loads(self.receipt.read_text(encoding="utf-8"))
                pack["sections"]["Approved Claim Evidence"][0].update(
                    {"use_mode": use_mode, "assertion": "Approved source-bound assertion."}
                )
                receipt["claim_decisions"][0]["use_mode"] = use_mode
                self.pack.write_text(json.dumps(pack), encoding="utf-8")
                self.receipt.write_text(json.dumps(receipt), encoding="utf-8")
                self.write_current_sidecar(
                    [
                        {
                            "claim_id": "claim-simpro-work",
                            "use_mode": use_mode,
                            "brand_scope": "simpro",
                            "public_url": "https://www.simprogroup.com/",
                            "public_text": article_text,
                            "public_text_sha256": sha256_text(article_text),
                        }
                    ]
                )

                rule_ids = {finding["rule_id"] for finding in self.check()}
                self.assertIn("context_claim_evidence_mismatch", rule_ids)

    def test_proof_passage_in_frontmatter_or_comment_is_not_public_copy(self):
        public_text = "Simpro helps teams coordinate work."
        for article in (
            f"---\ntitle: Simpro draft\nclaim_copy: {public_text}\n---\n# Simpro draft\n\nBody.\n",
            f"---\ntitle: Simpro draft\n---\n# Simpro draft\n\n<!-- {public_text} -->\nBody.\n",
        ):
            with self.subTest(article=article):
                self.article.write_text(article, encoding="utf-8")
                self.write_current_sidecar(
                    [
                        {
                            "claim_id": "claim-simpro-work",
                            "use_mode": "paraphrase",
                            "brand_scope": "simpro",
                            "public_url": "https://www.simprogroup.com/",
                            "public_text": public_text,
                            "public_text_sha256": sha256_text(public_text),
                        }
                    ]
                )

                self.assertIn(
                    "context_claim_public_text_mismatch",
                    {finding["rule_id"] for finding in self.check()},
                )

    def test_proof_passage_in_hidden_html_metadata_is_not_public_copy(self):
        public_text = "Simpro helps teams coordinate work."
        articles = (
            (
                "script",
                "---\ntitle: Simpro draft\n---\n# Simpro draft\n\n"
                f"<script type=\"application/ld+json\">{{\"claim\":\"{public_text}\"}}</script>\n"
                "Body.\n",
            ),
            (
                "style",
                "---\ntitle: Simpro draft\n---\n# Simpro draft\n\n"
                f"<style>.claim::after {{ content: \"{public_text}\"; }}</style>\n"
                "Body.\n",
            ),
            (
                "hidden",
                "---\ntitle: Simpro draft\n---\n# Simpro draft\n\n"
                f"<div hidden>{public_text}</div>\n"
                "Body.\n",
            ),
            (
                "nested-hidden",
                "---\ntitle: Simpro draft\n---\n# Simpro draft\n\n"
                f"<div hidden><div>intro</div>{public_text}</div>\n"
                "Body.\n",
            ),
            (
                "aria-hidden",
                "---\ntitle: Simpro draft\n---\n# Simpro draft\n\n"
                f"<p aria-hidden=\"true\">{public_text}</p>\n"
                "Body.\n",
            ),
            (
                "display-none",
                "---\ntitle: Simpro draft\n---\n# Simpro draft\n\n"
                f"<div style=\"color: red; display : none !important\">{public_text}</div>\n"
                "Body.\n",
            ),
            (
                "visibility-hidden",
                "---\ntitle: Simpro draft\n---\n# Simpro draft\n\n"
                f"<section style=\"visibility:hidden\"><strong>{public_text}</strong></section>\n"
                "Body.\n",
            ),
            (
                "template",
                "---\ntitle: Simpro draft\n---\n# Simpro draft\n\n"
                f"<template>{public_text}</template>\n"
                "Body.\n",
            ),
        )
        for label, article in articles:
            with self.subTest(label=label):
                self.article.write_text(article, encoding="utf-8")
                self.write_current_sidecar(
                    [
                        {
                            "claim_id": "claim-simpro-work",
                            "use_mode": "paraphrase",
                            "brand_scope": "simpro",
                            "public_url": "https://www.simprogroup.com/",
                            "public_text": public_text,
                            "public_text_sha256": sha256_text(public_text),
                        }
                    ]
                )

                self.assertIn(
                    "context_claim_public_text_mismatch",
                    {finding["rule_id"] for finding in self.check()},
                )

    def test_formatted_visible_body_passage_matches_approved_assertion(self):
        public_text = "Simpro helps teams coordinate work."
        self.article.write_text(
            "---\ntitle: Simpro draft\n---\n# Simpro draft\n\n"
            "**Simpro helps** teams [coordinate work](https://example.com).\n",
            encoding="utf-8",
        )
        self.write_current_sidecar(
            [
                {
                    "claim_id": "claim-simpro-work",
                    "use_mode": "paraphrase",
                    "brand_scope": "simpro",
                    "public_url": "https://www.simprogroup.com/",
                    "public_text": public_text,
                    "public_text_sha256": sha256_text(public_text),
                }
            ]
        )

        self.assertEqual(self.check(), [])

    def test_unknown_public_claim_use_mode_fails_closed(self):
        pack = json.loads(self.pack.read_text(encoding="utf-8"))
        receipt = json.loads(self.receipt.read_text(encoding="utf-8"))
        pack["sections"]["Approved Claim Evidence"][0]["use_mode"] = "social_post"
        receipt["claim_decisions"][0]["use_mode"] = "social_post"
        self.pack.write_text(json.dumps(pack), encoding="utf-8")
        self.receipt.write_text(json.dumps(receipt), encoding="utf-8")
        self.write_current_sidecar(
            [
                {
                    "claim_id": "claim-simpro-work",
                    "use_mode": "social_post",
                    "brand_scope": "simpro",
                    "public_url": "https://www.simprogroup.com/",
                    "public_text": "Simpro helps teams coordinate work.",
                    "public_text_sha256": sha256_text("Simpro helps teams coordinate work."),
                }
            ]
        )

        self.assertIn(
            "context_claim_use_mode_invalid",
            {finding["rule_id"] for finding in self.check()},
        )

    def test_every_supported_public_claim_mode_accepts_bound_evidence(self):
        public_text = "Simpro helps teams coordinate work."
        for use_mode in (
            "authority_support",
            "exact_quote",
            "paraphrase",
            "public_claim",
            "public_metric",
            "public_paraphrase",
        ):
            with self.subTest(use_mode=use_mode):
                pack = json.loads(self.pack.read_text(encoding="utf-8"))
                receipt = json.loads(self.receipt.read_text(encoding="utf-8"))
                evidence = pack["sections"]["Approved Claim Evidence"][0]
                evidence.update({"use_mode": use_mode, "assertion": public_text})
                if use_mode == "exact_quote":
                    evidence["verbatim_evidence"] = {
                        "text": public_text,
                        "text_sha256": sha256_text(public_text),
                        "resource_id": "res-guidance",
                        "public_url": "https://www.simprogroup.com/",
                    }
                receipt["claim_decisions"][0]["use_mode"] = use_mode
                self.pack.write_text(json.dumps(pack), encoding="utf-8")
                self.receipt.write_text(json.dumps(receipt), encoding="utf-8")
                self.write_current_sidecar(
                    [
                        {
                            "claim_id": "claim-simpro-work",
                            "use_mode": use_mode,
                            "brand_scope": "simpro",
                            "public_url": "https://www.simprogroup.com/",
                            "public_text": public_text,
                            "public_text_sha256": sha256_text(public_text),
                        }
                    ]
                )

                self.assertEqual(self.check(), [])

    def test_exact_quote_passage_must_equal_bound_verbatim_evidence(self):
        article_text = "The review says faster scheduling, but this sentence is not the quote."
        self.article.write_text(f"# Simpro draft\n\n{article_text}\n", encoding="utf-8")
        pack = json.loads(self.pack.read_text(encoding="utf-8"))
        receipt = json.loads(self.receipt.read_text(encoding="utf-8"))
        evidence = pack["sections"]["Approved Claim Evidence"][0]
        evidence.update(
            {
                "use_mode": "exact_quote",
                "assertion": "Review exact snippet: faster scheduling",
                "verbatim_evidence": {
                    "text": "faster scheduling",
                    "text_sha256": sha256_text("faster scheduling"),
                    "resource_id": "res-review-source",
                    "public_url": "https://www.simprogroup.com/",
                },
            }
        )
        receipt["claim_decisions"][0]["use_mode"] = "exact_quote"
        self.pack.write_text(json.dumps(pack), encoding="utf-8")
        self.receipt.write_text(json.dumps(receipt), encoding="utf-8")
        self.write_current_sidecar(
            [
                {
                    "claim_id": "claim-simpro-work",
                    "use_mode": "exact_quote",
                    "brand_scope": "simpro",
                    "public_url": "https://www.simprogroup.com/",
                    "public_text": article_text,
                    "public_text_sha256": sha256_text(article_text),
                }
            ]
        )

        findings = self.check()

        self.assertIn(
            "context_claim_exact_quote_mismatch",
            {finding["rule_id"] for finding in findings},
        )

    def test_public_metric_passage_must_equal_bound_assertion(self):
        article_text = "Teams save a lot of time with the platform."
        self.article.write_text(f"# Simpro draft\n\n{article_text}\n", encoding="utf-8")
        pack = json.loads(self.pack.read_text(encoding="utf-8"))
        receipt = json.loads(self.receipt.read_text(encoding="utf-8"))
        evidence = pack["sections"]["Approved Claim Evidence"][0]
        evidence.update(
            {
                "use_mode": "public_metric",
                "assertion": "Teams reduced administrative time by 25%.",
            }
        )
        receipt["claim_decisions"][0]["use_mode"] = "public_metric"
        self.pack.write_text(json.dumps(pack), encoding="utf-8")
        self.receipt.write_text(json.dumps(receipt), encoding="utf-8")
        self.write_current_sidecar(
            [
                {
                    "claim_id": "claim-simpro-work",
                    "use_mode": "public_metric",
                    "brand_scope": "simpro",
                    "public_url": "https://www.simprogroup.com/",
                    "public_text": article_text,
                    "public_text_sha256": sha256_text(article_text),
                }
            ]
        )

        findings = self.check()

        self.assertIn(
            "context_claim_public_metric_mismatch",
            {finding["rule_id"] for finding in findings},
        )

    def test_authority_support_passage_must_equal_bound_assertion(self):
        article_text = "Fred is an experienced leader with useful perspectives."
        self.article.write_text(f"# Simpro draft\n\n{article_text}\n", encoding="utf-8")
        pack = json.loads(self.pack.read_text(encoding="utf-8"))
        receipt = json.loads(self.receipt.read_text(encoding="utf-8"))
        evidence = pack["sections"]["Approved Claim Evidence"][0]
        evidence.update(
            {
                "use_mode": "authority_support",
                "assertion": "Fred describes operating discipline for field service leaders.",
            }
        )
        receipt["claim_decisions"][0]["use_mode"] = "authority_support"
        self.pack.write_text(json.dumps(pack), encoding="utf-8")
        self.receipt.write_text(json.dumps(receipt), encoding="utf-8")
        self.write_current_sidecar(
            [
                {
                    "claim_id": "claim-simpro-work",
                    "use_mode": "authority_support",
                    "brand_scope": "simpro",
                    "public_url": "https://www.simprogroup.com/",
                    "public_text": article_text,
                    "public_text_sha256": sha256_text(article_text),
                }
            ]
        )

        findings = self.check()

        self.assertIn(
            "context_claim_authority_support_mismatch",
            {finding["rule_id"] for finding in findings},
        )

    def test_authority_support_passage_accepts_exact_bound_assertion(self):
        article_text = "Fred describes operating discipline for field service leaders."
        self.article.write_text(f"# Simpro draft\n\n{article_text}\n", encoding="utf-8")
        pack = json.loads(self.pack.read_text(encoding="utf-8"))
        receipt = json.loads(self.receipt.read_text(encoding="utf-8"))
        pack["sections"]["Approved Claim Evidence"][0].update(
            {"use_mode": "authority_support", "assertion": article_text}
        )
        receipt["claim_decisions"][0]["use_mode"] = "authority_support"
        self.pack.write_text(json.dumps(pack), encoding="utf-8")
        self.receipt.write_text(json.dumps(receipt), encoding="utf-8")
        self.write_current_sidecar(
            [
                {
                    "claim_id": "claim-simpro-work",
                    "use_mode": "authority_support",
                    "brand_scope": "simpro",
                    "public_url": "https://www.simprogroup.com/",
                    "public_text": article_text,
                    "public_text_sha256": sha256_text(article_text),
                }
            ]
        )

        self.assertNotIn(
            "context_claim_authority_support_mismatch",
            {finding["rule_id"] for finding in self.check()},
        )

    def test_generator_installs_live_validated_binding_and_claim_map(self):
        pack = json.loads(self.pack.read_text(encoding="utf-8"))
        pack["sections"]["Approved Claim Evidence"][0]["assertion"] = (
            "Simpro helps teams coordinate work."
        )
        self.pack.write_text(json.dumps(pack), encoding="utf-8")
        self.sidecar.write_text("## Editorial Notes\n\nKeep this.\n", encoding="utf-8")

        result = context_binding_generator.generate_and_install(
            self.article,
            self.request,
            self.pack,
            self.receipt,
            self.sidecar,
            repo_context=[{"path": "context/seo-guidelines.md", "role": "SEO structure"}],
            client=ValidatingClient(),
        )

        content = self.sidecar.read_text(encoding="utf-8")
        self.assertIn("## Editorial Notes", content)
        self.assertIn("## Context Binding", content)
        self.assertIn("## Context Claim Use Map", content)
        self.assertEqual(result["claim_use_map"][0]["claim_id"], "claim-simpro-work")
        self.assertEqual(self.check(), [])

    def test_generator_request_mismatch_never_modifies_existing_sidecar(self):
        original = "## Editorial Notes\n\nPreserve exactly.\n"
        self.sidecar.write_text(original, encoding="utf-8")
        request = json.loads(self.request.read_text(encoding="utf-8"))
        request["scope"]["title"] = "Unrelated title"
        self.request.write_text(json.dumps(request), encoding="utf-8")

        with self.assertRaises(context_binding_generator.ContextBindingGenerationError) as raised:
            context_binding_generator.generate_and_install(
                self.article,
                self.request,
                self.pack,
                self.receipt,
                self.sidecar,
                repo_context=[{"path": "context/seo-guidelines.md", "role": "SEO structure"}],
                client=ValidatingClient(),
            )

        self.assertEqual(raised.exception.code, "context_request_article_mismatch")
        self.assertEqual(self.sidecar.read_text(encoding="utf-8"), original)

    def test_generator_brand_mismatch_never_modifies_existing_sidecar(self):
        original = "## Editorial Notes\n\nPreserve exactly.\n"
        self.sidecar.write_text(original, encoding="utf-8")
        self.article.write_text(
            "---\nbrand: BigChange\nartifact_type: blog\ntitle: Simpro draft\n---\n"
            "# Simpro draft\n\nSimpro helps teams coordinate work.\n",
            encoding="utf-8",
        )

        with self.assertRaises(context_binding_generator.ContextBindingGenerationError) as raised:
            context_binding_generator.generate_and_install(
                self.article,
                self.request,
                self.pack,
                self.receipt,
                self.sidecar,
                repo_context=[{"path": "context/seo-guidelines.md", "role": "SEO structure"}],
                client=ValidatingClient(),
            )

        self.assertEqual(raised.exception.code, "context_request_article_mismatch")
        self.assertEqual(self.sidecar.read_text(encoding="utf-8"), original)

    def test_generator_artifact_kind_mismatch_never_modifies_existing_sidecar(self):
        original = "## Editorial Notes\n\nPreserve exactly.\n"
        self.sidecar.write_text(original, encoding="utf-8")
        self.article.write_text(
            "---\nbrand: Simpro\nartifact_type: landing_page\ntitle: Simpro draft\n---\n"
            "# Simpro draft\n\nSimpro helps teams coordinate work.\n",
            encoding="utf-8",
        )

        with self.assertRaises(context_binding_generator.ContextBindingGenerationError) as raised:
            context_binding_generator.generate_and_install(
                self.article,
                self.request,
                self.pack,
                self.receipt,
                self.sidecar,
                repo_context=[{"path": "context/seo-guidelines.md", "role": "SEO structure"}],
                client=ValidatingClient(),
            )

        self.assertEqual(raised.exception.code, "context_request_article_mismatch")
        self.assertEqual(self.sidecar.read_text(encoding="utf-8"), original)

    def test_generator_validates_derived_claim_map_before_writing(self):
        original = "## Editorial Notes\n\nPreserve exactly.\n"
        self.sidecar.write_text(original, encoding="utf-8")
        pack = json.loads(self.pack.read_text(encoding="utf-8"))
        receipt = json.loads(self.receipt.read_text(encoding="utf-8"))
        pack["sections"]["Approved Claim Evidence"][0].update(
            {
                "use_mode": "authority_support",
                "assertion": "Fred describes operating discipline for field service leaders.",
            }
        )
        receipt["claim_decisions"][0]["use_mode"] = "authority_support"
        self.pack.write_text(json.dumps(pack), encoding="utf-8")
        self.receipt.write_text(json.dumps(receipt), encoding="utf-8")
        unrelated = "Simpro helps teams coordinate work."
        bad_map = [
            {
                "claim_id": "claim-simpro-work",
                "use_mode": "authority_support",
                "brand_scope": "simpro",
                "public_url": "https://www.simprogroup.com/",
                "public_text": unrelated,
                "public_text_sha256": sha256_text(unrelated),
            }
        ]

        with patch.object(context_binding_generator, "_derive_claim_map", return_value=bad_map):
            with self.assertRaises(context_binding_generator.ContextBindingGenerationError) as raised:
                context_binding_generator.generate_and_install(
                    self.article,
                    self.request,
                    self.pack,
                    self.receipt,
                    self.sidecar,
                    repo_context=[{"path": "context/seo-guidelines.md", "role": "SEO structure"}],
                    client=ValidatingClient(),
                )

        self.assertEqual(raised.exception.code, "context_claim_authority_support_mismatch")
        self.assertEqual(self.sidecar.read_text(encoding="utf-8"), original)

    def test_generator_requires_five_distinct_resolved_paths(self):
        paths = [self.article, self.request, self.pack, self.receipt, self.sidecar]
        original_bytes = {path: path.read_bytes() for path in paths}
        for left in range(len(paths)):
            for right in range(left + 1, len(paths)):
                with self.subTest(left=left, right=right):
                    arguments = list(paths)
                    arguments[right] = arguments[left]
                    with self.assertRaises(
                        context_binding_generator.ContextBindingGenerationError
                    ) as raised:
                        context_binding_generator.generate_and_install(
                            *arguments,
                            repo_context=[
                                {"path": "context/seo-guidelines.md", "role": "SEO structure"}
                            ],
                            client=ValidatingClient(),
                        )
                    self.assertEqual(raised.exception.code, "context_artifact_path_collision")
                    self.assertEqual(
                        {path: path.read_bytes() for path in paths},
                        original_bytes,
                    )

    def test_generator_rejects_different_text_paths_resolving_to_same_file(self):
        aliased_sidecar = self.root / "unused" / ".." / self.article.name

        with self.assertRaises(context_binding_generator.ContextBindingGenerationError) as raised:
            context_binding_generator.generate_and_install(
                self.article,
                self.request,
                self.pack,
                self.receipt,
                aliased_sidecar,
                repo_context=[{"path": "context/seo-guidelines.md", "role": "SEO structure"}],
                client=ValidatingClient(),
            )

        self.assertEqual(raised.exception.code, "context_artifact_path_collision")

    def test_generator_atomic_replace_failure_preserves_sidecar_and_cleans_temp(self):
        original = "## Editorial Notes\n\nPreserve exactly.\n"
        self.sidecar.write_text(original, encoding="utf-8")
        before = set(self.root.iterdir())

        with patch(
            "data_sources.modules.context_binding_generator.os.replace",
            side_effect=OSError("replace blocked"),
        ):
            with self.assertRaises(context_binding_generator.ContextBindingGenerationError) as raised:
                context_binding_generator.generate_and_install(
                    self.article,
                    self.request,
                    self.pack,
                    self.receipt,
                    self.sidecar,
                    repo_context=[{"path": "context/seo-guidelines.md", "role": "SEO structure"}],
                    client=ValidatingClient(),
                )

        self.assertEqual(raised.exception.code, "sidecar_write_failed")
        self.assertEqual(self.sidecar.read_text(encoding="utf-8"), original)
        self.assertEqual(set(self.root.iterdir()), before)

    def test_generator_replaces_from_same_directory_and_cleans_temp(self):
        pack = json.loads(self.pack.read_text(encoding="utf-8"))
        pack["sections"]["Approved Claim Evidence"][0]["assertion"] = (
            "Simpro helps teams coordinate work."
        )
        self.pack.write_text(json.dumps(pack), encoding="utf-8")
        real_replace = context_binding_generator.os.replace
        calls = []

        def capture_replace(source, destination):
            calls.append((Path(source), Path(destination)))
            return real_replace(source, destination)

        with patch(
            "data_sources.modules.context_binding_generator.os.replace",
            side_effect=capture_replace,
        ):
            context_binding_generator.generate_and_install(
                self.article,
                self.request,
                self.pack,
                self.receipt,
                self.sidecar,
                repo_context=[{"path": "context/seo-guidelines.md", "role": "SEO structure"}],
                client=ValidatingClient(),
            )

        self.assertEqual(len(calls), 1)
        source, destination = calls[0]
        self.assertEqual(source.parent.resolve(), self.sidecar.parent.resolve())
        self.assertEqual(destination.resolve(), self.sidecar.resolve())
        self.assertFalse(source.exists())


if __name__ == "__main__":
    unittest.main()
