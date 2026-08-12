import hashlib
import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from data_sources.modules import context_binding_generator, context_binding_guard
from data_sources.modules.blog_assembly_stage_receipt import (
    StageReceiptError,
    build_stage_receipt,
    check_receipt_chain,
    load_stage_receipt,
    write_stage_receipt,
)


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
            "---\n"
            "artifact_type: blog\n"
            "brand: Simpro\n"
            "title: Simpro draft\n"
            "objective: Explain coordinated work.\n"
            "audience: field service leaders\n"
            "region: US\n"
            "---\n"
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

    def _write_context_predecessor(
        self,
        *,
        stage="scrub",
        article_hash=None,
        run_id="run-42",
    ):
        output_hash = article_hash or hashlib.sha256(
            self.article.read_bytes()
        ).hexdigest()
        is_draft = stage == "draft"
        predecessor = build_stage_receipt(
            run_id=run_id,
            stage=stage,
            tool_name="blog_writer" if is_draft else "content_scrubber",
            tool_version="1.0.0",
            started_at="2020-08-11T12:00:00Z",
            completed_at="2020-08-11T12:01:00Z",
            mutation=is_draft,
            input_artifact_hashes={
                "article": "0" * 64 if is_draft else output_hash
            },
            output_artifact_hashes={"article": output_hash},
            evidence_hashes=(
                {} if is_draft else {"scrub_statistics": "a" * 64}
            ),
        )
        path = self.root / f"{stage}-predecessor.json"
        write_stage_receipt(path, predecessor)
        return path

    def write_resource_only_context(self, article_text, legacy_sidecar):
        self.article.write_text(
            "---\n"
            "artifact_type: blog\n"
            "brand: Simpro\n"
            "title: Simpro draft\n"
            "objective: Explain coordinated work.\n"
            "audience: field service leaders\n"
            "region: US\n"
            "---\n"
            f"# Simpro draft\n\n{article_text}\n",
            encoding="utf-8",
        )
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
        self.article.write_text(
            "---\n"
            "artifact_type: blog\n"
            "brand: Simpro\n"
            "title: Simpro draft\n"
            "objective: Explain coordinated work.\n"
            "audience: field service leaders\n"
            "region: US\n"
            "---\n"
            f"# Simpro draft\n\n{article_text}\n",
            encoding="utf-8",
        )
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

    def test_cross_brand_official_simpro_hostnames_require_context(self):
        for url in (
            "https://www.simprogroup.com",
            "https://helpguide.simprogroup.com/",
            "simprogroup.com/resources",
            "www.simprogroup.com/features",
            "helpguide.simprogroup.com/article/123",
        ):
            with self.subTest(url=url):
                content = (
                    "---\nbrand: BigChange\nartifact_type: blog\ntitle: Comparison\n---\n"
                    f"# Comparison\n\n[Product reference]({url})\n"
                )

                self.assertTrue(context_binding_guard.requires_context(content))

    def test_simpro_hostname_lookalike_does_not_require_context(self):
        for hostname in (
            "https://evil-simprogroup.com/",
            "evil-simprogroup.com/path",
            "simprogroup.com.evil.example/path",
        ):
            with self.subTest(hostname=hostname):
                content = (
                    "---\nbrand: BigChange\nartifact_type: blog\ntitle: Comparison\n---\n"
                    f"# Comparison\n\n[Unrelated site]({hostname})\n"
                )

                self.assertFalse(context_binding_guard.requires_context(content))

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
            "---\nbrand: Simpro\nartifact_type: landing_page\ntitle: Simpro landing page\n"
            "objective: Explain coordinated work.\naudience: field service leaders\n"
            "region: US\n---\n"
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

    def test_request_objective_audience_and_region_must_match_article_frontmatter(self):
        field_values = {
            "objective": "A different objective",
            "audience": "A different audience",
            "region": "AU",
        }
        original = json.loads(self.request.read_text(encoding="utf-8"))
        for field, mismatched_value in field_values.items():
            with self.subTest(field=field):
                request = json.loads(json.dumps(original))
                request["scope"][field] = mismatched_value
                findings = context_binding_guard.validate_request_article(
                    request,
                    self.article.read_text(encoding="utf-8"),
                    article_path=self.article,
                )
                self.assertIn(
                    "context_request_article_mismatch",
                    {finding["rule_id"] for finding in findings},
                )
                self.assertTrue(
                    any(field in finding["message"].lower() for finding in findings)
                )

    def test_typed_article_missing_request_identity_field_fails_context_binding(self):
        article = (
            "---\nartifact_type: blog\nbrand: Simpro\ntitle: Simpro draft\n"
            "audience: field service leaders\nregion: US\n---\n# Simpro draft\n"
        )
        request = json.loads(self.request.read_text(encoding="utf-8"))

        findings = context_binding_guard.validate_request_article(request, article)

        self.assertIn(
            "context_request_article_mismatch",
            {finding["rule_id"] for finding in findings},
        )
        self.assertTrue(
            any("objective" in finding["message"].lower() for finding in findings)
        )

    def test_cross_brand_article_accepts_simpro_authority_scope_with_matching_artifact_brand(self):
        self.article.write_text(
            "---\nbrand: BigChange\nartifact_type: blog\ntitle: Simpro draft\n"
            "objective: Explain coordinated work.\naudience: field service leaders\n"
            "region: US\n---\n"
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
            "---\nartifact_type: blog\nbrand: Simpro\ntitle: Simpro draft\n"
            "objective: Explain coordinated work.\naudience: field service leaders\n"
            "region: US\n---\n# Simpro draft\n\n"
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

    def test_generator_emits_a_real_context_binding_stage_receipt(self):
        pack = json.loads(self.pack.read_text(encoding="utf-8"))
        pack["sections"]["Approved Claim Evidence"][0]["assertion"] = (
            "Simpro helps teams coordinate work."
        )
        self.pack.write_text(json.dumps(pack), encoding="utf-8")
        receipt_path = self.root / "context-binding-stage-receipt.json"
        article_hash = hashlib.sha256(self.article.read_bytes()).hexdigest()
        previous_path = self._write_context_predecessor(run_id="run-42")

        result = context_binding_generator.generate_and_install(
            self.article,
            self.request,
            self.pack,
            self.receipt,
            self.sidecar,
            repo_context=[
                {"path": "context/seo-guidelines.md", "role": "SEO structure"}
            ],
            client=ValidatingClient(),
            stage_receipt_output=receipt_path,
            run_id="run-42",
            previous_receipt=previous_path,
        )

        stage_receipt = load_stage_receipt(receipt_path)
        self.assertEqual(result["stage_receipt"], stage_receipt)
        self.assertEqual(stage_receipt["stage"], "context_binding")
        self.assertFalse(stage_receipt["mutation"])
        self.assertEqual(
            stage_receipt["input_artifact_hashes"],
            {
                "article": article_hash,
                "context_pack": hashlib.sha256(self.pack.read_bytes()).hexdigest(),
                "context_receipt": hashlib.sha256(self.receipt.read_bytes()).hexdigest(),
                "context_request": hashlib.sha256(self.request.read_bytes()).hexdigest(),
            },
        )
        self.assertEqual(stage_receipt["output_artifact_hashes"]["article"], article_hash)
        self.assertEqual(
            stage_receipt["output_artifact_hashes"]["validation_sidecar"],
            hashlib.sha256(self.sidecar.read_bytes()).hexdigest(),
        )
        self.assertIn("context_binding", stage_receipt["evidence_hashes"])

    def test_non_connector_generator_emits_a_real_unchanged_receipt_chain(self):
        self.article.write_text(
            "---\n"
            "artifact_type: blog\n"
            "brand: BigChange\n"
            "title: Scheduling guide\n"
            "objective: Explain scheduling practices.\n"
            "audience: field service leaders\n"
            "region: US\n"
            "---\n"
            "# Scheduling guide\n\nUse a consistent dispatch routine.\n",
            encoding="utf-8",
        )
        original_article = self.article.read_bytes()
        original_sidecar = b"## Editorial Notes\n\nNo connector claims are used.\n"
        self.sidecar.write_bytes(original_sidecar)
        article_hash = hashlib.sha256(original_article).hexdigest()
        sidecar_hash = hashlib.sha256(original_sidecar).hexdigest()
        draft = build_stage_receipt(
            run_id="run-non-connector",
            stage="draft",
            tool_name="blog_writer",
            tool_version="1.0.0",
            started_at="2026-08-10T12:00:00Z",
            completed_at="2026-08-10T12:01:00Z",
            mutation=True,
            input_artifact_hashes={"article": "0" * 64},
            output_artifact_hashes={"article": article_hash},
        )
        scrub = build_stage_receipt(
            run_id="run-non-connector",
            stage="scrub",
            tool_name="content_scrubber",
            tool_version="1.0.0",
            started_at="2026-08-10T12:02:00Z",
            completed_at="2026-08-10T12:03:00Z",
            mutation=False,
            input_artifact_hashes={"article": article_hash},
            output_artifact_hashes={"article": article_hash},
            evidence_hashes={"scrub_statistics": "a" * 64},
            previous_receipt_hash=draft["receipt_hash"],
        )
        previous_path = self.root / "scrub-stage-receipt.json"
        write_stage_receipt(previous_path, scrub)
        receipt_path = self.root / "context-binding-stage-receipt.json"
        reason = "BigChange editorial content contains no Simpro references or claims."

        result = context_binding_generator.generate_not_applicable_receipt(
            self.article,
            self.sidecar,
            reason,
            stage_receipt_output=receipt_path,
            previous_receipt=previous_path,
        )

        stage_receipt = load_stage_receipt(receipt_path)
        evidence_payload = {
            "article_sha256": article_hash,
            "reason": reason,
            "schema": "seomachine-context-binding-not-applicable/v1",
            "status": "not_applicable",
            "validation_sidecar_sha256": sidecar_hash,
        }
        expected_evidence_hash = hashlib.sha256(
            json.dumps(
                evidence_payload,
                ensure_ascii=True,
                separators=(",", ":"),
                sort_keys=True,
            ).encode("utf-8")
        ).hexdigest()
        self.assertEqual(result["stage_receipt"], stage_receipt)
        self.assertEqual(stage_receipt["run_id"], "run-non-connector")
        self.assertEqual(
            stage_receipt["previous_receipt_hash"], scrub["receipt_hash"]
        )
        self.assertEqual(
            stage_receipt["input_artifact_hashes"],
            {"article": article_hash, "validation_sidecar": sidecar_hash},
        )
        self.assertEqual(
            stage_receipt["output_artifact_hashes"],
            {"article": article_hash, "validation_sidecar": sidecar_hash},
        )
        self.assertEqual(
            stage_receipt["evidence_hashes"],
            {
                "context_binding": expected_evidence_hash,
                "not_applicable_reason": hashlib.sha256(
                    reason.encode("utf-8")
                ).hexdigest(),
            },
        )
        self.assertFalse(stage_receipt["mutation"])
        self.assertEqual(check_receipt_chain([draft, scrub, stage_receipt]), [])
        self.assertEqual(self.article.read_bytes(), original_article)
        self.assertEqual(self.sidecar.read_bytes(), original_sidecar)

    def test_non_connector_generator_fails_closed_for_simpro_content(self):
        original_article = self.article.read_bytes()
        original_sidecar = self.sidecar.read_bytes()
        receipt_path = self.root / "context-binding-stage-receipt.json"

        with self.assertRaises(
            context_binding_generator.ContextBindingGenerationError
        ) as raised:
            context_binding_generator.generate_not_applicable_receipt(
                self.article,
                self.sidecar,
                "No connector context applies.",
                stage_receipt_output=receipt_path,
                run_id="run-42",
            )

        self.assertEqual(raised.exception.code, "context_binding_required")
        self.assertFalse(receipt_path.exists())
        self.assertEqual(self.article.read_bytes(), original_article)
        self.assertEqual(self.sidecar.read_bytes(), original_sidecar)

    def test_non_connector_generator_fails_closed_for_schemeless_simpro_host(self):
        for hostname in (
            "www.simprogroup.com/features",
            "simprogroup.com/resources",
        ):
            with self.subTest(hostname=hostname):
                self.article.write_text(
                    "---\nartifact_type: blog\nbrand: BigChange\ntitle: Guide\n---\n"
                    f"# Guide\n\nRead {hostname} for details.\n",
                    encoding="utf-8",
                )
                output_path = self.root / "context-stage.json"

                with self.assertRaises(
                    context_binding_generator.ContextBindingGenerationError
                ) as raised:
                    context_binding_generator.generate_not_applicable_receipt(
                        self.article,
                        self.sidecar,
                        "The article contains no Simpro references or claims.",
                        stage_receipt_output=output_path,
                        previous_receipt=self._write_context_predecessor(),
                    )

                self.assertEqual(raised.exception.code, "context_binding_required")
                self.assertFalse(output_path.exists())

    def test_non_connector_generator_does_not_match_a_hostname_lookalike(self):
        self.article.write_text(
            "---\nartifact_type: blog\nbrand: BigChange\ntitle: Guide\n---\n"
            "# Guide\n\nRead evil-simprogroup.com for an unrelated example.\n",
            encoding="utf-8",
        )
        output_path = self.root / "context-stage.json"

        context_binding_generator.generate_not_applicable_receipt(
            self.article,
            self.sidecar,
            "The article contains no official Simpro references or claims.",
            stage_receipt_output=output_path,
            previous_receipt=self._write_context_predecessor(),
        )

        self.assertTrue(output_path.is_file())

    def test_non_connector_generator_requires_an_explicit_reason(self):
        self.article.write_text(
            "---\nartifact_type: blog\nbrand: BigChange\ntitle: Guide\n---\n"
            "# Guide\n",
            encoding="utf-8",
        )

        with self.assertRaises(
            context_binding_generator.ContextBindingGenerationError
        ) as raised:
            context_binding_generator.generate_not_applicable_receipt(
                self.article,
                self.sidecar,
                "   ",
                stage_receipt_output=self.root / "context-stage.json",
                run_id="run-42",
            )

        self.assertEqual(
            raised.exception.code,
            "context_not_applicable_reason_missing",
        )

    def test_non_connector_generator_rejects_a_non_utf8_proof_sidecar(self):
        self.article.write_text(
            "---\nartifact_type: blog\nbrand: BigChange\ntitle: Guide\n---\n"
            "# Guide\n",
            encoding="utf-8",
        )
        self.sidecar.write_bytes(b"\xff\xfe")
        output_path = self.root / "context-stage.json"

        with self.assertRaises(
            context_binding_generator.ContextBindingGenerationError
        ) as raised:
            context_binding_generator.generate_not_applicable_receipt(
                self.article,
                self.sidecar,
                "The article contains no Simpro references or claims.",
                stage_receipt_output=output_path,
                run_id="run-42",
            )

        self.assertEqual(raised.exception.code, "binding_input_invalid")
        self.assertFalse(output_path.exists())

    def test_non_connector_generator_supports_post_optimization_stage(self):
        self.article.write_text(
            "---\nartifact_type: blog\nbrand: BigChange\ntitle: Guide\n---\n"
            "# Guide\n",
            encoding="utf-8",
        )

        context_binding_generator.generate_not_applicable_receipt(
            self.article,
            self.sidecar,
            "The final article contains no Simpro references or claims.",
            stage_receipt_output=self.root / "post-context-stage.json",
            run_id="run-42",
            previous_receipt=self._write_context_predecessor(
                stage="post_optimization_scrub"
            ),
            stage="post_optimization_context_binding",
        )

        self.assertEqual(
            load_stage_receipt(self.root / "post-context-stage.json")["stage"],
            "post_optimization_context_binding",
        )

    def test_non_connector_generator_rejects_receipt_input_path_collisions(self):
        self.article.write_text(
            "---\nartifact_type: blog\nbrand: BigChange\ntitle: Guide\n---\n"
            "# Guide\n",
            encoding="utf-8",
        )
        original_article = self.article.read_bytes()
        original_sidecar = self.sidecar.read_bytes()

        with self.assertRaises(
            context_binding_generator.ContextBindingGenerationError
        ) as raised:
            context_binding_generator.generate_not_applicable_receipt(
                self.article,
                self.sidecar,
                "The article contains no Simpro references or claims.",
                stage_receipt_output=self.sidecar,
                run_id="run-42",
            )

        self.assertEqual(raised.exception.code, "context_artifact_path_collision")
        self.assertEqual(self.article.read_bytes(), original_article)
        self.assertEqual(self.sidecar.read_bytes(), original_sidecar)

    def test_non_connector_generator_rejects_a_non_monotonic_predecessor(self):
        self.article.write_text(
            "---\nartifact_type: blog\nbrand: BigChange\ntitle: Guide\n---\n"
            "# Guide\n",
            encoding="utf-8",
        )
        article_hash = hashlib.sha256(self.article.read_bytes()).hexdigest()
        predecessor = build_stage_receipt(
            run_id="run-42",
            stage="scrub",
            tool_name="content_scrubber",
            tool_version="1.0.0",
            started_at="2099-08-11T12:00:00Z",
            completed_at="2099-08-11T12:01:00Z",
            mutation=False,
            input_artifact_hashes={"article": article_hash},
            output_artifact_hashes={"article": article_hash},
            evidence_hashes={"scrub_statistics": "a" * 64},
        )
        predecessor_path = self.root / "future-scrub.json"
        write_stage_receipt(predecessor_path, predecessor)
        output_path = self.root / "context-stage.json"

        with self.assertRaises(StageReceiptError) as raised:
            context_binding_generator.generate_not_applicable_receipt(
                self.article,
                self.sidecar,
                "The article contains no Simpro references or claims.",
                stage_receipt_output=output_path,
                previous_receipt=predecessor_path,
            )

        self.assertEqual(
            raised.exception.code,
            "stage_receipt_timestamps_not_monotonic",
        )
        self.assertFalse(output_path.exists())

    def test_non_connector_generator_requires_the_closed_stage_predecessor(self):
        self.article.write_text(
            "---\nartifact_type: blog\nbrand: BigChange\ntitle: Guide\n---\n"
            "# Guide\n",
            encoding="utf-8",
        )

        with self.assertRaises(StageReceiptError) as raised:
            context_binding_generator.generate_not_applicable_receipt(
                self.article,
                self.sidecar,
                "The article contains no Simpro references or claims.",
                stage_receipt_output=self.root / "context-stage.json",
                run_id="run-42",
            )

        self.assertEqual(
            raised.exception.code,
            "stage_receipt_previous_required",
        )

    def test_non_connector_generator_rejects_the_wrong_predecessor_stage(self):
        self.article.write_text(
            "---\nartifact_type: blog\nbrand: BigChange\ntitle: Guide\n---\n"
            "# Guide\n",
            encoding="utf-8",
        )
        predecessor_path = self._write_context_predecessor(stage="draft")

        with self.assertRaises(StageReceiptError) as raised:
            context_binding_generator.generate_not_applicable_receipt(
                self.article,
                self.sidecar,
                "The article contains no Simpro references or claims.",
                stage_receipt_output=self.root / "context-stage.json",
                previous_receipt=predecessor_path,
            )

        self.assertEqual(
            raised.exception.code,
            "stage_receipt_predecessor_stage_invalid",
        )

    def test_non_connector_generator_rejects_a_stale_predecessor_article_hash(self):
        self.article.write_text(
            "---\nartifact_type: blog\nbrand: BigChange\ntitle: Guide\n---\n"
            "# Guide\n",
            encoding="utf-8",
        )
        predecessor_path = self._write_context_predecessor(article_hash="a" * 64)

        with self.assertRaises(StageReceiptError) as raised:
            context_binding_generator.generate_not_applicable_receipt(
                self.article,
                self.sidecar,
                "The article contains no Simpro references or claims.",
                stage_receipt_output=self.root / "context-stage.json",
                previous_receipt=predecessor_path,
            )

        self.assertEqual(
            raised.exception.code,
            "stage_receipt_article_chain_broken",
        )

    def test_non_connector_cli_accepts_only_the_explicit_not_applicable_mode(self):
        self.article.write_text(
            "---\nartifact_type: blog\nbrand: BigChange\ntitle: Guide\n---\n"
            "# Guide\n",
            encoding="utf-8",
        )
        receipt_path = self.root / "context-stage.json"
        previous_path = self._write_context_predecessor(run_id="run-cli")

        exit_code = context_binding_generator.main(
            [
                str(self.article),
                "--proof-sidecar",
                str(self.sidecar),
                "--not-applicable-reason",
                "This article contains no Simpro references or claims.",
                "--stage-receipt-output",
                str(receipt_path),
                "--run-id",
                "run-cli",
                "--previous-receipt",
                str(previous_path),
            ]
        )

        self.assertEqual(exit_code, 0)
        self.assertEqual(load_stage_receipt(receipt_path)["run_id"], "run-cli")

    def test_non_connector_cli_rejects_mixed_connector_arguments(self):
        self.article.write_text(
            "---\nartifact_type: blog\nbrand: BigChange\ntitle: Guide\n---\n"
            "# Guide\n",
            encoding="utf-8",
        )
        receipt_path = self.root / "context-stage.json"

        output = io.StringIO()
        with redirect_stdout(output):
            exit_code = context_binding_generator.main(
                [
                    str(self.article),
                    "--proof-sidecar",
                    str(self.sidecar),
                    "--not-applicable-reason",
                    "This article contains no Simpro references or claims.",
                    "--context-request",
                    str(self.request),
                    "--stage-receipt-output",
                    str(receipt_path),
                ]
            )

        self.assertEqual(exit_code, 1)
        error_payload = json.loads(output.getvalue())
        self.assertEqual(
            error_payload["error"]["code"],
            "context_binding_mode_conflict",
        )
        self.assertIn("Choose either", error_payload["recovery_hint"])
        self.assertFalse(receipt_path.exists())

    def test_non_connector_cli_requires_a_stage_receipt_output(self):
        self.article.write_text(
            "---\nartifact_type: blog\nbrand: BigChange\ntitle: Guide\n---\n"
            "# Guide\n",
            encoding="utf-8",
        )

        output = io.StringIO()
        with redirect_stdout(output):
            exit_code = context_binding_generator.main(
                [
                    str(self.article),
                    "--proof-sidecar",
                    str(self.sidecar),
                    "--not-applicable-reason",
                    "This article contains no Simpro references or claims.",
                ]
            )

        self.assertEqual(exit_code, 1)
        error_payload = json.loads(output.getvalue())
        self.assertEqual(
            error_payload["error"]["code"],
            "stage_receipt_output_required",
        )
        self.assertIn("stage receipt output", error_payload["recovery_hint"])

    def test_connector_cli_rejects_a_partial_context_artifact_set(self):
        output = io.StringIO()
        with redirect_stdout(output):
            exit_code = context_binding_generator.main(
                [
                    str(self.article),
                    "--proof-sidecar",
                    str(self.sidecar),
                    "--context-request",
                    str(self.request),
                ]
            )

        self.assertEqual(exit_code, 1)
        error_payload = json.loads(output.getvalue())
        self.assertEqual(
            error_payload["error"]["code"],
            "context_artifact_set_incomplete",
        )
        self.assertIn("all three", error_payload["recovery_hint"])

    def test_generator_invalid_previous_receipt_never_modifies_sidecar(self):
        original = "## Editorial Notes\n\nPreserve exactly.\n"
        self.sidecar.write_text(original, encoding="utf-8")
        previous = self.root / "invalid-previous-receipt.json"
        previous.write_text("not json", encoding="utf-8")

        with self.assertRaises(StageReceiptError):
            context_binding_generator.generate_and_install(
                self.article,
                self.request,
                self.pack,
                self.receipt,
                self.sidecar,
                repo_context=[
                    {"path": "context/seo-guidelines.md", "role": "SEO structure"}
                ],
                client=ValidatingClient(),
                stage_receipt_output=self.root / "context-stage.json",
                previous_receipt=previous,
            )

        self.assertEqual(self.sidecar.read_text(encoding="utf-8"), original)

    def test_generator_previous_receipt_cannot_collide_with_sidecar(self):
        original = "## Editorial Notes\n\nPreserve exactly.\n"
        self.sidecar.write_text(original, encoding="utf-8")

        with self.assertRaises(
            context_binding_generator.ContextBindingGenerationError
        ) as raised:
            context_binding_generator.generate_and_install(
                self.article,
                self.request,
                self.pack,
                self.receipt,
                self.sidecar,
                repo_context=[
                    {"path": "context/seo-guidelines.md", "role": "SEO structure"}
                ],
                client=ValidatingClient(),
                stage_receipt_output=self.root / "context-stage.json",
                previous_receipt=self.sidecar,
            )

        self.assertEqual(raised.exception.code, "context_artifact_path_collision")
        self.assertEqual(self.sidecar.read_text(encoding="utf-8"), original)

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

    def test_generator_receipt_failure_rolls_back_sidecar(self):
        original = "## Editorial Notes\n\nPreserve exactly.\n"
        self.sidecar.write_text(original, encoding="utf-8")
        pack = json.loads(self.pack.read_text(encoding="utf-8"))
        pack["sections"]["Approved Claim Evidence"][0]["assertion"] = (
            "Simpro helps teams coordinate work."
        )
        self.pack.write_text(json.dumps(pack), encoding="utf-8")
        receipt_path = self.root / "context-stage.json"
        previous_path = self._write_context_predecessor(run_id="run-rollback")

        with patch.object(
            context_binding_generator,
            "write_stage_receipt",
            side_effect=OSError("receipt write failed"),
        ):
            with self.assertRaisesRegex(OSError, "receipt write failed"):
                context_binding_generator.generate_and_install(
                    self.article,
                    self.request,
                    self.pack,
                    self.receipt,
                    self.sidecar,
                    repo_context=[
                        {
                            "path": "context/seo-guidelines.md",
                            "role": "SEO structure",
                        }
                    ],
                    client=ValidatingClient(),
                    stage_receipt_output=receipt_path,
                    run_id="run-rollback",
                    previous_receipt=previous_path,
                )

        self.assertEqual(self.sidecar.read_text(encoding="utf-8"), original)
        self.assertFalse(receipt_path.exists())

    def test_generator_captures_completion_after_sidecar_output_write(self):
        original = "## Editorial Notes\n\nPreserve exactly.\n"
        self.sidecar.write_text(original, encoding="utf-8")
        pack = json.loads(self.pack.read_text(encoding="utf-8"))
        pack["sections"]["Approved Claim Evidence"][0]["assertion"] = (
            "Simpro helps teams coordinate work."
        )
        self.pack.write_text(json.dumps(pack), encoding="utf-8")
        receipt_path = self.root / "context-stage.json"
        previous_path = self._write_context_predecessor(run_id="run-output-order")
        real_builder = context_binding_generator.build_stage_receipt

        def build_after_output(**kwargs):
            self.assertIn(
                "## Context Binding",
                self.sidecar.read_text(encoding="utf-8"),
            )
            return real_builder(**kwargs)

        with patch.object(
            context_binding_generator,
            "build_stage_receipt",
            side_effect=build_after_output,
        ):
            context_binding_generator.generate_and_install(
                self.article,
                self.request,
                self.pack,
                self.receipt,
                self.sidecar,
                repo_context=[
                    {
                        "path": "context/seo-guidelines.md",
                        "role": "SEO structure",
                    }
                ],
                client=ValidatingClient(),
                stage_receipt_output=receipt_path,
                run_id="run-output-order",
                previous_receipt=previous_path,
            )

        self.assertTrue(receipt_path.is_file())

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


    def test_require_artifact_kind_rejects_missing_identity_without_path_inference(self):
        content = "---\nbrand: Simpro\ntitle: Draft\n---\n# Draft\n"

        with self.assertRaisesRegex(ValueError, "explicit artifact_type"):
            context_binding_guard.require_artifact_kind(
                content,
                article_path="drafts/blog-draft.md",
            )

    def test_require_artifact_kind_rejects_unsupported_explicit_value(self):
        content = "---\nartifact_type: brochure\nbrand: Simpro\n---\n# Draft\n"

        with self.assertRaisesRegex(ValueError, "unsupported"):
            context_binding_guard.require_artifact_kind(content)

    def test_require_artifact_kind_rejects_conflicting_explicit_values(self):
        content = (
            "---\nartifact_type: blog\nartifact_kind: landing_page\n"
            "brand: Simpro\n---\n# Draft\n"
        )

        with self.assertRaisesRegex(ValueError, "conflict"):
            context_binding_guard.require_artifact_kind(content)

    def test_require_artifact_kind_normalizes_supported_explicit_value(self):
        content = "---\nartifact_type: article\nbrand: Simpro\n---\n# Draft\n"

        self.assertEqual(context_binding_guard.require_artifact_kind(content), "blog")

    def test_structured_context_result_exposes_only_connector_approved_bindings(self):
        result = context_binding_guard.validate_context_artifacts(
            self.article,
            proof_sidecar=self.sidecar,
            context_request=self.request,
            context_pack=self.pack,
            context_receipt=self.receipt,
            client=ValidatingClient(),
        )

        self.assertTrue(result.passed)
        self.assertEqual(result.resource_ids, ("res-guidance",))
        self.assertEqual(result.approved_claim_ids, ("claim-simpro-work",))
        self.assertEqual(
            result.context_summary()["revisions"],
            json.loads(self.receipt.read_text(encoding="utf-8"))["revisions"],
        )

    def test_invalid_context_pack_schema_fails_structured_validation(self):
        pack = json.loads(self.pack.read_text(encoding="utf-8"))
        pack["schema"] = "simpro-product-context-pack/v1"
        self.pack.write_text(json.dumps(pack), encoding="utf-8")

        self.assertIn(
            "context_pack_schema_invalid",
            [finding["rule_id"] for finding in self.check()],
        )

    def test_invalid_context_receipt_schema_fails_structured_validation(self):
        receipt = json.loads(self.receipt.read_text(encoding="utf-8"))
        receipt["schema"] = "simpro-context-receipt/v0"
        self.receipt.write_text(json.dumps(receipt), encoding="utf-8")

        self.assertIn(
            "context_receipt_schema_invalid",
            [finding["rule_id"] for finding in self.check()],
        )

    def test_context_pack_receipt_revision_mismatch_fails_structured_validation(self):
        receipt = json.loads(self.receipt.read_text(encoding="utf-8"))
        receipt["revisions"]["manifest_revision"] = "manifest-r2"
        self.receipt.write_text(json.dumps(receipt), encoding="utf-8")

        self.assertIn(
            "context_revisions_invalid",
            [finding["rule_id"] for finding in self.check()],
        )


if __name__ == "__main__":
    unittest.main()
