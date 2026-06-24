import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class AeoGeoWorkflowDocsTests(unittest.TestCase):
    def test_article_command_documents_answer_socrates_workflow_and_gates(self):
        article = (ROOT / ".claude" / "commands" / "article.md").read_text(
            encoding="utf-8"
        )

        required = [
            "AnswerSocrates",
            "Playwright MCP",
            "research/paa-questions-[topic-slug]-[YYYY-MM-DD].md",
            "AEO/GEO Map",
            "85/100",
            "90/100",
        ]

        for text in required:
            self.assertIn(text, article)

    def test_write_command_documents_aeo_geo_requirements(self):
        write = (ROOT / ".claude" / "commands" / "write.md").read_text(
            encoding="utf-8"
        )

        required = [
            "AEO/GEO",
            "Capsule Method",
            "source mapping",
            "PAA",
            "BlogPosting",
            "FAQPage",
            "Author",
            "VideoObject",
            "90/100",
        ]

        for text in required:
            self.assertIn(text, write)

    def test_canonical_strategy_doc_exists(self):
        strategy = ROOT / "context" / "aeo-geo-blog-strategy.md"

        self.assertTrue(strategy.exists())

    def test_canonical_strategy_doc_supports_rewrite_workflow(self):
        strategy = (ROOT / "context" / "aeo-geo-blog-strategy.md").read_text(
            encoding="utf-8"
        )

        required = [
            "/analyze-existing",
            "/rewrite",
            "Question Relevance Selection",
            "Source Map",
            "E-E-A-T proof",
            "Experience",
            "Expertise",
            "Authority/Trust",
            "E-E-A-T Proof Map",
            "context-backed metrics",
            "public-facing source links",
            "context-backed proof",
            "internal source of truth",
            "85/100",
            "90/100",
        ]

        for text in required:
            self.assertIn(text, strategy)

    def test_rewrite_command_documents_full_aeo_geo_workflow(self):
        rewrite = (ROOT / ".claude" / "commands" / "rewrite.md").read_text(
            encoding="utf-8"
        )

        required = [
            "AEO/GEO",
            "context/aeo-geo-blog-strategy.md",
            "AEO/GEO variable resolution",
            "PAA/FAQ provenance",
            "research/paa-questions-[topic-slug]-[YYYY-MM-DD].md",
            "Source Map",
            "E-E-A-T proof",
            "E-E-A-T Proof Map",
            "Experience",
            "Expertise",
            "Do not invent",
            "repo context",
            "internal source of truth",
            "public-facing source links",
            "suggested blog focus",
            "/publish-readiness",
            "/optimize",
            "85/100",
            "90/100",
        ]

        for text in required:
            self.assertIn(text, rewrite)

    def test_blog_commands_require_eeat_proof_map_inputs(self):
        canonical = (ROOT / "context" / "aeo-geo-blog-strategy.md").read_text(
            encoding="utf-8"
        )
        detailed_required = [
            "context/internal-links-map.md",
            "context/features.md",
            "context/competitor-analysis.md",
            "public-facing source links",
        ]
        for text in detailed_required:
            self.assertIn(text, canonical)

        command_paths = [
            ROOT / ".claude" / "commands" / "article.md",
            ROOT / ".claude" / "commands" / "write.md",
            ROOT / ".claude" / "commands" / "rewrite.md",
            ROOT / ".claude" / "commands" / "analyze-existing.md",
        ]
        required = [
            "E-E-A-T Proof Map",
            "Experience",
            "Expertise",
            "context/aeo-geo-blog-strategy.md",
        ]

        for path in command_paths:
            content = path.read_text(encoding="utf-8")
            for text in required:
                self.assertIn(text, content, f"{path.name} missing {text}")

    def test_docs_allow_context_backed_metrics_only_with_public_links(self):
        docs = [
            ROOT / "context" / "aeo-geo-blog-strategy.md",
            ROOT / ".claude" / "commands" / "article.md",
            ROOT / ".claude" / "commands" / "write.md",
            ROOT / ".claude" / "commands" / "rewrite.md",
            ROOT / "README.md",
            ROOT / "CLAUDE.md",
        ]

        for path in docs:
            content = path.read_text(encoding="utf-8")
            self.assertIn("context-backed", content, f"{path.name} missing context-backed")
            self.assertIn(
                "public-facing source links",
                content,
                f"{path.name} missing public-facing source links",
            )

    def test_blog_writing_commands_document_numeric_and_because_rules(self):
        command_paths = [
            ROOT / ".claude" / "commands" / "article.md",
            ROOT / ".claude" / "commands" / "write.md",
            ROOT / ".claude" / "commands" / "rewrite.md",
        ]
        required = [
            "Use numerals for cardinal numbers",
            "Do not block source-visible metric wording",
            "Always put a comma before \"because\"",
        ]

        for path in command_paths:
            content = path.read_text(encoding="utf-8")
            for text in required:
                self.assertIn(text, content, f"{path.name} missing {text}")

    def test_blog_writing_commands_ban_source_meta_commentary(self):
        command_paths = [
            ROOT / ".claude" / "commands" / "article.md",
            ROOT / ".claude" / "commands" / "write.md",
            ROOT / ".claude" / "commands" / "rewrite.md",
        ]
        required = [
            "source/proof meta-commentary",
            "Translate proof into audience-facing takeaways",
        ]

        for path in command_paths:
            content = path.read_text(encoding="utf-8")
            for text in required:
                self.assertIn(text, content, f"{path.name} missing {text}")

    def test_blog_workflow_docs_treat_ai_copy_avoid_rules_as_blocking(self):
        command_paths = [
            ROOT / ".claude" / "commands" / "scrub.md",
            ROOT / ".claude" / "commands" / "write.md",
            ROOT / ".claude" / "commands" / "rewrite.md",
            ROOT / ".claude" / "commands" / "optimize.md",
            ROOT / ".claude" / "commands" / "publish-readiness.md",
        ]
        required = [
            "copy avoid-rule errors",
            "modal verbs, passive voice, repeated starts, vague generalizations, filler words, and long sentences",
        ]
        banned = [
            "Include warning findings in review notes unless strict mode is requested",
            "Warnings go into review notes unless strict mode is requested",
        ]

        for path in command_paths:
            content = path.read_text(encoding="utf-8")
            for text in required:
                self.assertIn(text, content, f"{path.name} missing {text}")
            for text in banned:
                self.assertNotIn(text, content, f"{path.name} keeps non-blocking avoid-rule language")

    def test_blog_workflow_docs_require_optional_experience_story_consideration(self):
        docs = [
            ROOT / ".claude" / "commands" / "write.md",
            ROOT / ".claude" / "commands" / "rewrite.md",
            ROOT / ".claude" / "commands" / "optimize.md",
            ROOT / "README.md",
            ROOT / "CLAUDE.md",
            ROOT / "AGENTS.md",
            ROOT / ".cursor" / "rules" / "customer-proof.mdc",
            ROOT / ".agents" / "rules" / "customer-proof.md",
            ROOT / ".claude" / "rules" / "customer-proof.md",
        ]
        canonical_required = [
            "experience_story consideration is required",
            "E-E-A-T story usage is optional",
        ]
        doc_required = [
            *canonical_required,
            "context/aeo-geo-blog-strategy.md",
        ]
        banned = [
            "every blog needs an E-E-A-T story",
            "must add an E-E-A-T story",
        ]

        canonical = (ROOT / "context" / "aeo-geo-blog-strategy.md").read_text(
            encoding="utf-8"
        )
        for text in canonical_required:
            self.assertIn(text, canonical, f"canonical proof policy missing {text}")

        for path in docs:
            content = path.read_text(encoding="utf-8")
            for text in doc_required:
                self.assertIn(text, content, f"{path.name} missing {text}")
            for text in banned:
                self.assertNotIn(text, content, f"{path.name} implies mandatory story use")

    def test_blog_writing_commands_require_down_funnel_internal_link(self):
        command_paths = [
            ROOT / ".claude" / "commands" / "article.md",
            ROOT / ".claude" / "commands" / "write.md",
            ROOT / ".claude" / "commands" / "rewrite.md",
        ]
        required = [
            "down-funnel internal link",
            "/industries",
            "/solutions/",
            "/features/",
            "Anchor text must match the destination keyword",
        ]

        for path in command_paths:
            content = path.read_text(encoding="utf-8")
            for text in required:
                self.assertIn(text, content, f"{path.name} missing {text}")

    def test_blog_writing_commands_limit_links_per_paragraph(self):
        command_paths = [
            ROOT / ".claude" / "commands" / "article.md",
            ROOT / ".claude" / "commands" / "write.md",
            ROOT / ".claude" / "commands" / "rewrite.md",
        ]
        required = [
            "Only 1 link per paragraph",
            "Move the second link to a separate paragraph",
        ]

        for path in command_paths:
            content = path.read_text(encoding="utf-8")
            for text in required:
                self.assertIn(text, content, f"{path.name} missing {text}")

    def test_blog_writing_docs_require_functional_feature_solution_anchors(self):
        docs = [
            ROOT / ".claude" / "commands" / "write.md",
            ROOT / ".claude" / "commands" / "rewrite.md",
            ROOT / ".claude" / "agents" / "internal-linker.md",
        ]
        required = [
            "function-bearing anchor text",
            "A feature or solution name alone is not enough",
        ]

        for path in docs:
            content = path.read_text(encoding="utf-8")
            for text in required:
                self.assertIn(text, content, f"{path.name} missing {text}")

    def test_internal_links_map_includes_industries_hub(self):
        link_map = (ROOT / "context" / "internal-links-map.md").read_text(
            encoding="utf-8"
        )

        required = [
            "https://www.simprogroup.com/industries",
            "field service management solutions for your industry",
            "field service software for trade industries",
            "software for trades businesses",
        ]

        for text in required:
            self.assertIn(text, link_map)

    def test_readme_claude_and_internal_linker_document_down_funnel_rule(self):
        docs = [
            ROOT / "README.md",
            ROOT / "CLAUDE.md",
            ROOT / ".claude" / "agents" / "internal-linker.md",
        ]
        required = [
            "down-funnel internal link",
            "https://www.simprogroup.com/industries",
            "Anchor text must match the destination keyword",
        ]

        for path in docs:
            content = path.read_text(encoding="utf-8")
            for text in required:
                self.assertIn(text, content, f"{path.name} missing {text}")

    def test_analyze_existing_command_documents_rewrite_strategy_inputs(self):
        analyze = (ROOT / ".claude" / "commands" / "analyze-existing.md").read_text(
            encoding="utf-8"
        )

        required = [
            "AEO/GEO readiness audit",
            "Missing strategy inputs",
            "Required PAA/source/proof artifacts",
            "Rewrite-specific AEO/GEO acceptance checklist",
            "PAA/FAQ provenance",
            "source map",
            "E-E-A-T Proof Map",
            "Experience",
            "Expertise",
            "review-site candidates",
            "context/aeo-geo-blog-strategy.md",
        ]

        for text in required:
            self.assertIn(text, analyze)

    def test_review_site_experience_evidence_boundary_is_documented(self):
        canonical = (ROOT / "context" / "aeo-geo-blog-strategy.md").read_text(
            encoding="utf-8"
        )
        detailed_required = [
            "review-site experience evidence",
            "first-hand customer experience",
            "star ratings, badges, rankings",
            "current source verification and brief-level approval",
        ]
        for text in detailed_required:
            self.assertIn(text, canonical)

        docs = [
            ROOT / ".claude" / "commands" / "research.md",
            ROOT / ".claude" / "commands" / "article.md",
            ROOT / ".claude" / "commands" / "write.md",
            ROOT / ".claude" / "commands" / "rewrite.md",
            ROOT / ".claude" / "commands" / "analyze-existing.md",
            ROOT / "CLAUDE.md",
        ]
        required = [
            "context/aeo-geo-blog-strategy.md",
            "review",
            "proof",
        ]

        for path in docs:
            content = path.read_text(encoding="utf-8")
            for text in required:
                self.assertIn(text, content, f"{path.name} missing {text}")

    def test_customer_proof_pack_contract_is_documented(self):
        canonical = (ROOT / "context" / "aeo-geo-blog-strategy.md").read_text(
            encoding="utf-8"
        )
        detailed_required = [
            "Customer Proof Pack",
            "Quote Matrix candidates",
            "Case-study proof paths",
            "Review-site experience evidence",
            "Approved quotes",
            "Pack status",
            "Claims excluded",
            "approval status",
        ]
        for text in detailed_required:
            self.assertIn(text, canonical)

        docs = [
            ROOT / ".claude" / "commands" / "research.md",
            ROOT / ".claude" / "commands" / "article.md",
            ROOT / ".claude" / "commands" / "write.md",
            ROOT / ".claude" / "commands" / "rewrite.md",
            ROOT / ".claude" / "commands" / "analyze-existing.md",
            ROOT / "CLAUDE.md",
            ROOT / "README.md",
        ]
        required = [
            "Customer Proof Pack",
            "context/aeo-geo-blog-strategy.md",
        ]

        for path in docs:
            content = path.read_text(encoding="utf-8")
            for text in required:
                self.assertIn(text, content, f"{path.name} missing {text}")

    def test_url_validation_gate_is_documented_across_publish_workflow(self):
        canonical = (ROOT / "context" / "aeo-geo-blog-strategy.md").read_text(
            encoding="utf-8"
        )
        for text in [
            "URL validation",
            "url_validator.py",
            "does not prove the page supports the claim",
        ]:
            self.assertIn(text, canonical)

        docs = [
            ROOT / ".claude" / "commands" / "optimize.md",
            ROOT / ".claude" / "commands" / "write.md",
            ROOT / ".claude" / "commands" / "rewrite.md",
            ROOT / ".claude" / "commands" / "article.md",
            ROOT / "README.md",
            ROOT / "CLAUDE.md",
        ]
        required = [
            "URL validation",
            "/publish-readiness",
            "context/aeo-geo-blog-strategy.md",
        ]

        for path in docs:
            content = path.read_text(encoding="utf-8")
            for text in required:
                self.assertIn(text, content, f"{path.name} missing {text}")

    def test_faq_proof_gate_is_documented_across_blog_workflow(self):
        canonical = (ROOT / "context" / "aeo-geo-blog-strategy.md").read_text(
            encoding="utf-8"
        )
        for text in [
            "FAQ proof",
            "faq_proof_guard.py",
            "public proof link",
            "question-specific Source Map",
            "Context file paths alone do not count",
        ]:
            self.assertIn(text, canonical)

        docs = [
            ROOT / ".claude" / "commands" / "article.md",
            ROOT / ".claude" / "commands" / "write.md",
            ROOT / ".claude" / "commands" / "rewrite.md",
            ROOT / "README.md",
            ROOT / "CLAUDE.md",
        ]
        required = [
            "FAQ proof",
            "/publish-readiness",
            "context/aeo-geo-blog-strategy.md",
        ]

        for path in docs:
            content = path.read_text(encoding="utf-8")
            for text in required:
                self.assertIn(text, content, f"{path.name} missing {text}")

    def test_paa_provenance_gate_is_documented_across_blog_workflow(self):
        canonical = (ROOT / "context" / "aeo-geo-blog-strategy.md").read_text(
            encoding="utf-8"
        )
        for text in [
            "PAA provenance",
            "paa_provenance_guard.py",
            "Proof links alone do not prove question provenance",
        ]:
            self.assertIn(text, canonical)

        workflow_docs = [
            ROOT / ".claude" / "commands" / "optimize.md",
            ROOT / ".claude" / "commands" / "article.md",
            ROOT / ".claude" / "commands" / "write.md",
            ROOT / ".claude" / "commands" / "rewrite.md",
            ROOT / "README.md",
            ROOT / "CLAUDE.md",
        ]
        command_required = [
            "PAA provenance",
            "/publish-readiness",
            "context/aeo-geo-blog-strategy.md",
        ]

        for path in workflow_docs:
            content = path.read_text(encoding="utf-8")
            for text in command_required:
                self.assertIn(text, content, f"{path.name} missing {text}")

        source_label_docs = [
            ROOT / ".claude" / "commands" / "article.md",
            ROOT / ".claude" / "commands" / "write.md",
            ROOT / ".claude" / "commands" / "rewrite.md",
            ROOT / "context" / "aeo-geo-blog-strategy.md",
            ROOT / "README.md",
            ROOT / "CLAUDE.md",
        ]
        for path in source_label_docs:
            content = path.read_text(encoding="utf-8")
            self.assertIn("AnswerSocrates", content, f"{path.name} missing AnswerSocrates")
            self.assertTrue(
                "user PAA/FAQ CSV" in content or "user-provided CSV" in content,
                f"{path.name} missing user PAA/FAQ CSV or user-provided CSV wording",
            )

        for path in workflow_docs:
            content = path.read_text(encoding="utf-8")
            self.assertNotIn(
                "Proof links alone do not prove question provenance",
                content,
                f"{path.name} should point to canonical PAA policy instead of duplicating it",
            )

    def test_numeric_claim_source_guard_is_documented_globally(self):
        canonical = (ROOT / "context" / "aeo-geo-blog-strategy.md").read_text(
            encoding="utf-8"
        )
        for text in [
            "Numeric claim source guard",
            "Numeric claim source guard and source support guard still prove any numbers",
            "public proof URL or local proof artifact",
        ]:
            self.assertIn(text, canonical)

        docs = [
            ROOT / ".claude" / "commands" / "optimize.md",
            ROOT / ".claude" / "commands" / "write.md",
            ROOT / ".claude" / "commands" / "rewrite.md",
            ROOT / ".claude" / "commands" / "article.md",
            ROOT / "README.md",
            ROOT / "CLAUDE.md",
        ]
        required = [
            "/publish-readiness",
            "context/aeo-geo-blog-strategy.md",
        ]

        for path in docs:
            content = path.read_text(encoding="utf-8")
            for text in required:
                self.assertIn(text, content, f"{path.name} missing {text}")

    def test_metric_proof_pack_gate_is_documented_across_blog_workflow(self):
        canonical = (ROOT / "context" / "aeo-geo-blog-strategy.md").read_text(
            encoding="utf-8"
        )
        for text in [
            "Metric Proof Pack",
            "metric_proof_pack_guard.py",
            "Approved metric",
            "Search log",
            "source-visible Evidence",
        ]:
            self.assertIn(text, canonical)

        docs = [
            ROOT / ".claude" / "commands" / "research.md",
            ROOT / ".claude" / "commands" / "optimize.md",
            ROOT / ".claude" / "commands" / "article.md",
            ROOT / ".claude" / "commands" / "write.md",
            ROOT / ".claude" / "commands" / "rewrite.md",
            ROOT / "README.md",
            ROOT / "CLAUDE.md",
        ]
        required = [
            "Metric Proof Pack",
            "/publish-readiness",
            "context/aeo-geo-blog-strategy.md",
        ]

        for path in docs:
            content = path.read_text(encoding="utf-8")
            for text in required:
                self.assertIn(text, content, f"{path.name} missing {text}")

    def test_validation_sidecar_workflow_is_documented(self):
        canonical = (ROOT / "context" / "aeo-geo-blog-strategy.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("public_artifact_guard.py", canonical)

        docs = [
            ROOT / ".claude" / "commands" / "optimize.md",
            ROOT / ".claude" / "commands" / "article.md",
            ROOT / ".claude" / "commands" / "write.md",
            ROOT / ".claude" / "commands" / "rewrite.md",
            ROOT / "README.md",
            ROOT / "CLAUDE.md",
        ]
        required = [
            "validation sidecar",
            "research/validation-[topic-slug]-[YYYY-MM-DD].md",
            "--proof-sidecar",
            "Editorial Validation Appendix",
            "/publish-readiness",
        ]

        for path in docs:
            content = path.read_text(encoding="utf-8")
            for text in required:
                self.assertIn(text, content, f"{path.name} missing {text}")

    def test_source_support_guard_is_documented_across_blog_workflow(self):
        canonical = (ROOT / "context" / "aeo-geo-blog-strategy.md").read_text(
            encoding="utf-8"
        )
        for text in [
            "source support guard",
            "source_support_guard.py",
            "Evidence",
            "Approved quote",
            "quotes, testimonials",
            "named customer metric",
            "Approved metrics",
        ]:
            self.assertIn(text, canonical)

        docs = [
            ROOT / ".claude" / "commands" / "optimize.md",
            ROOT / ".claude" / "commands" / "write.md",
            ROOT / ".claude" / "commands" / "rewrite.md",
            ROOT / ".claude" / "commands" / "article.md",
            ROOT / "README.md",
            ROOT / "CLAUDE.md",
        ]
        required = [
            "source support",
            "/publish-readiness",
            "context/aeo-geo-blog-strategy.md",
        ]

        for path in docs:
            content = path.read_text(encoding="utf-8")
            for text in required:
                self.assertIn(text, content, f"{path.name} missing {text}")

    def test_publish_scoring_commands_include_source_support_flag(self):
        docs = [
            ROOT / ".claude" / "commands" / "optimize.md",
            ROOT / ".claude" / "commands" / "write.md",
            ROOT / ".claude" / "commands" / "rewrite.md",
            ROOT / ".claude" / "commands" / "article.md",
            ROOT / "README.md",
            ROOT / "CLAUDE.md",
        ]

        for path in docs:
            content = path.read_text(encoding="utf-8")
            for line in content.splitlines():
                if "content_scorer.py" in line and "--validate-urls" in line:
                    self.assertIn(
                        "--validate-source-support",
                        line,
                        f"{path.name} scorer command missing --validate-source-support: {line}",
                    )

    def test_publish_readiness_runner_is_documented_as_preferred_command(self):
        docs = [
            ROOT / ".claude" / "commands" / "research.md",
            ROOT / ".claude" / "commands" / "optimize.md",
            ROOT / ".claude" / "commands" / "article.md",
            ROOT / ".claude" / "commands" / "write.md",
            ROOT / ".claude" / "commands" / "rewrite.md",
            ROOT / "README.md",
            ROOT / "CLAUDE.md",
            ROOT / "AGENTS.md",
            ROOT / ".cursor" / "rules" / "customer-proof.mdc",
        ]
        preferred_command = "/publish-readiness [file] --proof-sidecar research/validation-[topic-slug]-[YYYY-MM-DD].md"

        for path in docs:
            content = path.read_text(encoding="utf-8")
            self.assertIn(
                preferred_command,
                content,
                f"{path.name} must document /publish-readiness as the preferred publish gate command",
            )

    def test_publish_readiness_slash_command_contract_exists(self):
        command_path = ROOT / ".claude" / "commands" / "publish-readiness.md"
        content = command_path.read_text(encoding="utf-8")

        self.assertIn(
            "/publish-readiness [file] --proof-sidecar research/validation-[topic-slug]-[YYYY-MM-DD].md",
            content,
        )
        self.assertIn("Do not ask the user to call the Python runner manually", content)
        for gate in [
            "public_artifact_guard",
            "ai_copy_linter",
            "url_validator",
            "metric_proof_pack_guard",
            "numeric_claim_source_guard",
            "faq_proof_guard",
            "paa_provenance_guard",
            "source_support_guard",
            "customer_proof_diversity_guard",
            "review_story_identity_guard",
            "content_scorer",
        ]:
            self.assertIn(gate, content)

    def test_noncanonical_blog_workflows_do_not_require_manual_publish_gate_scripts(self):
        docs = [
            ROOT / ".claude" / "commands" / "research.md",
            ROOT / ".claude" / "commands" / "optimize.md",
            ROOT / ".claude" / "commands" / "article.md",
            ROOT / ".claude" / "commands" / "write.md",
            ROOT / ".claude" / "commands" / "rewrite.md",
            ROOT / "README.md",
            ROOT / "CLAUDE.md",
            ROOT / "AGENTS.md",
            ROOT / ".cursor" / "rules" / "customer-proof.mdc",
            ROOT / ".agents" / "rules" / "customer-proof.md",
            ROOT / ".claude" / "rules" / "customer-proof.md",
        ]
        publish_gate_modules = [
            "public_artifact_guard.py",
            "ai_copy_linter.py",
            "url_validator.py",
            "metric_proof_pack_guard.py",
            "numeric_claim_source_guard.py",
            "faq_proof_guard.py",
            "paa_provenance_guard.py",
            "source_support_guard.py",
            "customer_proof_diversity_guard.py",
            "review_story_identity_guard.py",
            "content_scorer.py",
            "publish_readiness.py",
        ]

        for path in docs:
            content = path.read_text(encoding="utf-8")
            for line in content.splitlines():
                if "python " not in line:
                    continue
                self.assertFalse(
                    any(module in line for module in publish_gate_modules),
                    f"{path.name} should use /publish-readiness instead of manual publish gate script: {line}",
                )

    def test_proof_aware_guard_command_examples_include_sidecar(self):
        docs = [
            ROOT / ".claude" / "commands" / "research.md",
            ROOT / ".claude" / "commands" / "optimize.md",
            ROOT / ".claude" / "commands" / "article.md",
            ROOT / ".claude" / "commands" / "write.md",
            ROOT / ".claude" / "commands" / "rewrite.md",
            ROOT / "context" / "aeo-geo-blog-strategy.md",
            ROOT / "README.md",
            ROOT / "CLAUDE.md",
            ROOT / "AGENTS.md",
            ROOT / ".cursor" / "rules" / "customer-proof.mdc",
        ]
        proof_aware_guards = [
            "metric_proof_pack_guard.py",
            "numeric_claim_source_guard.py",
            "faq_proof_guard.py",
            "paa_provenance_guard.py",
            "source_support_guard.py",
            "customer_proof_diversity_guard.py",
            "review_story_identity_guard.py",
        ]

        for path in docs:
            content = path.read_text(encoding="utf-8")
            for line in content.splitlines():
                if "python " not in line:
                    continue
                if not any(guard in line for guard in proof_aware_guards):
                    continue
                self.assertIn(
                    "--proof-sidecar",
                    line,
                    f"{path.name} proof-aware guard command missing --proof-sidecar: {line}",
                )

    def test_noncanonical_docs_do_not_duplicate_long_proof_policy(self):
        noncanonical_docs = [
            ROOT / ".claude" / "commands" / "research.md",
            ROOT / ".claude" / "commands" / "optimize.md",
            ROOT / ".claude" / "commands" / "article.md",
            ROOT / ".claude" / "commands" / "write.md",
            ROOT / ".claude" / "commands" / "rewrite.md",
            ROOT / "README.md",
            ROOT / "CLAUDE.md",
            ROOT / "AGENTS.md",
            ROOT / ".cursor" / "rules" / "customer-proof.mdc",
        ]
        canonical = (ROOT / "context" / "aeo-geo-blog-strategy.md").read_text(
            encoding="utf-8"
        )
        canonical_snippets = [
            "Metric-sensitive topics must include a Metric Proof Pack before drafting or publish readiness",
            "The source support guard requires each high-risk claim to map to a strict proof row",
            "The PAA provenance guard requires each FAQ question to map",
            "Review narratives are first-hand customer experience",
            "For Capterra rows that fit a blog topic",
            "Every `/research`, `/article`, `/write`, `/analyze-existing`, and `/rewrite` workflow must resolve a task-specific Customer Proof Pack",
            "Case-study proof paths and Review-site experience evidence may support non-numeric E-E-A-T",
            "FAQ proof is required for each claim-bearing answer",
        ]
        for snippet in canonical_snippets:
            self.assertIn(snippet, canonical, f"canonical strategy missing policy snippet: {snippet}")

        for path in noncanonical_docs:
            content = path.read_text(encoding="utf-8")
            self.assertIn(
                "context/aeo-geo-blog-strategy.md",
                content,
                f"{path.name} must point to the canonical proof policy",
            )
            for snippet in canonical_snippets:
                self.assertNotIn(
                    snippet,
                    content,
                    f"{path.name} duplicates canonical proof policy: {snippet}",
                )

    def test_noncanonical_docs_do_not_duplicate_publish_command_examples(self):
        docs = [
            ROOT / ".claude" / "commands" / "research.md",
            ROOT / ".claude" / "commands" / "optimize.md",
            ROOT / ".claude" / "commands" / "article.md",
            ROOT / ".claude" / "commands" / "write.md",
            ROOT / ".claude" / "commands" / "rewrite.md",
            ROOT / "README.md",
            ROOT / "CLAUDE.md",
            ROOT / "AGENTS.md",
            ROOT / ".cursor" / "rules" / "customer-proof.mdc",
        ]
        command_modules = [
            "metric_proof_pack_guard.py",
            "numeric_claim_source_guard.py",
            "faq_proof_guard.py",
            "paa_provenance_guard.py",
            "source_support_guard.py",
            "customer_proof_diversity_guard.py",
            "review_story_identity_guard.py",
            "content_scorer.py",
        ]

        for path in docs:
            content = path.read_text(encoding="utf-8")
            for module in command_modules:
                command_count = sum(
                    1
                    for line in content.splitlines()
                    if "python " in line and module in line
                )
                self.assertLessEqual(
                    command_count,
                    1,
                    f"{path.name} duplicates {module} command examples {command_count} times",
                )

    def test_customer_proof_selection_governance_is_documented(self):
        canonical = (ROOT / "context" / "aeo-geo-blog-strategy.md").read_text(
            encoding="utf-8"
        )
        for text in [
            "customer_proof_selector.py",
            "customer_proof_diversity_guard.py",
            "--slate",
            "customer-proof-index.json",
            "customer-proof-usage-ledger.json",
            "Reuse reason",
            "Customer Proof Selection Decision",
            "Customer Proof Slate",
            "source-specific",
        ]:
            self.assertIn(text, canonical)

        docs = [
            ROOT / ".claude" / "commands" / "research.md",
            ROOT / ".claude" / "commands" / "article.md",
            ROOT / ".claude" / "commands" / "write.md",
            ROOT / ".claude" / "commands" / "rewrite.md",
            ROOT / "README.md",
            ROOT / "CLAUDE.md",
        ]
        required = [
            "Customer Proof Slate",
            "context/aeo-geo-blog-strategy.md",
        ]

        for path in docs:
            content = path.read_text(encoding="utf-8")
            for text in required:
                self.assertIn(text, content, f"{path.name} missing {text}")

    def test_customer_proof_selector_runs_automatically_before_drafting(self):
        docs = [
            ROOT / "context" / "aeo-geo-blog-strategy.md",
            ROOT / ".claude" / "commands" / "research.md",
            ROOT / ".claude" / "commands" / "article.md",
            ROOT / ".claude" / "commands" / "write.md",
            ROOT / ".claude" / "commands" / "rewrite.md",
            ROOT / "README.md",
            ROOT / "CLAUDE.md",
            ROOT / "AGENTS.md",
            ROOT / ".cursor" / "rules" / "customer-proof.mdc",
            ROOT / ".agents" / "rules" / "customer-proof.md",
            ROOT / ".claude" / "rules" / "customer-proof.md",
        ]
        canonical = ROOT / "context" / "aeo-geo-blog-strategy.md"
        required = [
            "automatically run",
            "Customer Proof Slate",
            "experience_story consideration is required",
            "E-E-A-T story usage is optional",
            "Selected: [none]",
        ]

        for path in docs:
            content = path.read_text(encoding="utf-8")
            selector_index = content.find("customer_proof_selector.py")
            self.assertGreaterEqual(
                selector_index,
                0,
                f"{path.name} missing customer_proof_selector.py",
            )
            selector_window = content[
                max(0, selector_index - 500) : selector_index + 800
            ].lower()
            self.assertIn(
                "automatically run",
                selector_window,
                f"{path.name} must make customer_proof_selector.py automatic",
            )
            self.assertNotIn(
                "run or consult",
                content.lower(),
                f"{path.name} must not make customer proof selection optional",
            )
            for text in required:
                self.assertIn(text, content, f"{path.name} missing {text}")
            if path != canonical:
                self.assertIn(
                    "context/aeo-geo-blog-strategy.md",
                    content,
                    f"{path.name} missing context/aeo-geo-blog-strategy.md",
                )

    def test_selected_customer_proof_mining_is_documented(self):
        canonical = (ROOT / "context" / "aeo-geo-blog-strategy.md").read_text(
            encoding="utf-8"
        )
        for text in [
            "Selected Customer Proof Mining",
            "Checked for: exact quotes, customer metrics, POV story, workflow themes",
            "proof mining reads the selected public URL",
        ]:
            self.assertIn(text, canonical)

        docs = [
            ROOT / ".claude" / "commands" / "write.md",
            ROOT / ".claude" / "commands" / "rewrite.md",
            ROOT / ".claude" / "commands" / "optimize.md",
            ROOT / "README.md",
            ROOT / "CLAUDE.md",
            ROOT / "AGENTS.md",
            ROOT / ".cursor" / "rules" / "customer-proof.mdc",
            ROOT / ".agents" / "rules" / "customer-proof.md",
            ROOT / ".claude" / "rules" / "customer-proof.md",
        ]
        for path in docs:
            content = path.read_text(encoding="utf-8")
            self.assertIn("Selected Customer Proof Mining", content, f"{path.name} missing proof-mining block")
            self.assertIn("context/aeo-geo-blog-strategy.md", content, f"{path.name} missing canonical policy link")

    def test_customer_proof_index_intake_workflow_is_documented(self):
        canonical = (ROOT / "context" / "aeo-geo-blog-strategy.md").read_text(
            encoding="utf-8"
        )
        required = [
            "customer_proof_index_health.py",
            "customer_proof_index_intake.py",
            "context/customer-proof-intake-template.csv",
        ]
        for text in required + ["proof-index intake", "proof-index health"]:
            self.assertIn(text, canonical)

        docs = [
            ROOT / ".claude" / "commands" / "research.md",
            ROOT / ".claude" / "commands" / "article.md",
            ROOT / ".claude" / "commands" / "write.md",
            ROOT / ".claude" / "commands" / "rewrite.md",
            ROOT / "README.md",
            ROOT / "CLAUDE.md",
            ROOT / "AGENTS.md",
            ROOT / ".cursor" / "rules" / "customer-proof.mdc",
            ROOT / ".agents" / "rules" / "customer-proof.md",
            ROOT / ".claude" / "rules" / "customer-proof.md",
        ]
        required = [
            "context/customer-proof-intake-template.csv",
            "context/aeo-geo-blog-strategy.md",
        ]
        for path in docs:
            content = path.read_text(encoding="utf-8")
            for text in required:
                self.assertIn(text, content, f"{path.name} missing {text}")

    def test_customer_proof_rules_apply_across_agent_platforms(self):
        rule_paths = [
            ROOT / ".cursor" / "rules" / "customer-proof.mdc",
            ROOT / ".agents" / "rules" / "customer-proof.md",
            ROOT / ".claude" / "rules" / "customer-proof.md",
        ]
        for path in rule_paths:
            self.assertTrue(path.exists(), f"{path} must exist")
            content = path.read_text(encoding="utf-8")
            self.assertIn("Customer Proof Slate", content, f"{path.name} missing Customer Proof Slate")
            self.assertIn("--slate", content, f"{path.name} missing generated slate command")
            self.assertIn("selector-first", content.lower(), f"{path.name} missing selector-first language")
            self.assertIn("context/aeo-geo-blog-strategy.md", content, f"{path.name} missing canonical policy link")

        cursor_rule = (ROOT / ".cursor" / "rules" / "customer-proof.mdc").read_text(
            encoding="utf-8"
        )
        self.assertIn("alwaysApply: true", cursor_rule)

    def test_research_performance_is_slash_command_first(self):
        research_performance = (
            ROOT / ".claude" / "commands" / "research-performance.md"
        ).read_text(encoding="utf-8")

        required = [
            "/research-performance [blog URL or path]",
            "This is a slash-command workflow",
            "Do not ask the user to run Python scripts by hand",
            "research/performance-review-[topic-slug]-[YYYY-MM-DD].md",
            "Recommended next slash command",
        ]
        for text in required:
            self.assertIn(text, research_performance)

        user_facing_docs = [
            ROOT / ".claude" / "commands" / "research-performance.md",
            ROOT / ".claude" / "commands" / "content-calendar.md",
            ROOT / "README.md",
            ROOT / "CLAUDE.md",
        ]
        forbidden = [
            "python3 research_performance_matrix.py",
            "python3 scripts/research_performance_matrix.py",
            "scripts/research_performance_matrix.py",
        ]
        for path in user_facing_docs:
            content = path.read_text(encoding="utf-8")
            for text in forbidden:
                self.assertNotIn(
                    text,
                    content,
                    f"{path.name} exposes performance script instead of slash command workflow",
                )

    def test_review_story_identity_governance_is_documented(self):
        canonical = (ROOT / "context" / "aeo-geo-blog-strategy.md").read_text(
            encoding="utf-8"
        )
        detailed_required = [
            "Review Story Selection",
            "review_story_identity_guard.py",
            "identity-backed",
            "public review URL",
            "same paragraph",
        ]
        for text in detailed_required:
            self.assertIn(text, canonical)

        docs = [
            ROOT / ".claude" / "commands" / "research.md",
            ROOT / ".claude" / "commands" / "optimize.md",
            ROOT / ".claude" / "commands" / "article.md",
            ROOT / ".claude" / "commands" / "write.md",
            ROOT / ".claude" / "commands" / "rewrite.md",
            ROOT / "README.md",
            ROOT / "CLAUDE.md",
            ROOT / "AGENTS.md",
        ]
        required = [
            "review",
            "context/aeo-geo-blog-strategy.md",
            "/publish-readiness",
        ]
        for path in docs:
            content = path.read_text(encoding="utf-8")
            for text in required:
                self.assertIn(text, content, f"{path.name} missing {text}")

    def test_story_policy_blocks_fictional_named_personas(self):
        canonical = (ROOT / "context" / "aeo-geo-blog-strategy.md").read_text(
            encoding="utf-8"
        )
        required = [
            "E-E-A-T stories are optional",
            "actual person or business POV",
            "fictional named personas are prohibited",
            "Unnamed workflow scenarios are explanatory only",
        ]
        for text in required:
            self.assertIn(text, canonical)

        docs = [
            ROOT / ".claude" / "commands" / "article.md",
            ROOT / ".claude" / "commands" / "write.md",
            ROOT / ".claude" / "commands" / "rewrite.md",
            ROOT / "README.md",
            ROOT / "CLAUDE.md",
            ROOT / "AGENTS.md",
            ROOT / ".cursor" / "rules" / "customer-proof.mdc",
            ROOT / ".agents" / "rules" / "customer-proof.md",
            ROOT / ".claude" / "rules" / "customer-proof.md",
        ]
        forbidden = [
            "use names, even if fictional",
            "Every article MUST include 2-3 mini-scenarios",
            "2-3 mini-stories with names/details/outcomes",
            "2-3 mini-stories with specifics",
        ]
        for path in docs:
            content = path.read_text(encoding="utf-8")
            lowered = content.lower()
            self.assertIn(
                "proof-backed customer/review pov",
                lowered,
                f"{path.name} missing optional proof-backed POV rule",
            )
            for text in forbidden:
                self.assertNotIn(text.lower(), lowered, f"{path.name} still allows fictional stories")

    def test_capterra_review_site_theme_policy_is_documented(self):
        canonical = (ROOT / "context" / "aeo-geo-blog-strategy.md").read_text(
            encoding="utf-8"
        )
        detailed_required = [
            "Review Site Theme Selection",
            "https://www.capterra.com/p/10529/Simpro-Enterprise/reviews/",
            "Capterra tab row",
            "paraphrased review-theme use",
            "no exact quote, reviewer-name claim, rating, ranking, or metric unless separately approved",
        ]
        for text in detailed_required:
            self.assertIn(text, canonical)

        docs = [
            ROOT / ".claude" / "commands" / "research.md",
            ROOT / ".claude" / "commands" / "article.md",
            ROOT / ".claude" / "commands" / "write.md",
            ROOT / ".claude" / "commands" / "rewrite.md",
            ROOT / "README.md",
            ROOT / "CLAUDE.md",
            ROOT / "AGENTS.md",
        ]
        required = [
            "context/aeo-geo-blog-strategy.md",
            "review",
        ]
        for path in docs:
            content = path.read_text(encoding="utf-8")
            for text in required:
                self.assertIn(text, content, f"{path.name} missing {text}")


if __name__ == "__main__":
    unittest.main()
