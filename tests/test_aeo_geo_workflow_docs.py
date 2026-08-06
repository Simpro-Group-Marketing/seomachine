import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class AeoGeoWorkflowDocsTests(unittest.TestCase):
    def test_faq_answer_quality_and_inline_evidence_rule_is_mirrored(self):
        required = [
            "faq_answer_quality_guard.py",
            "40-60 word",
            "authoritative non-owned public evidence link",
            "cannot replace",
        ]
        docs = [
            ROOT / "AGENTS.md",
            ROOT / "CLAUDE.md",
            ROOT / "README.md",
            ROOT / "context" / "aeo-geo-blog-strategy.md",
            ROOT / ".claude" / "commands" / "article.md",
            ROOT / ".claude" / "commands" / "write.md",
            ROOT / ".claude" / "commands" / "rewrite.md",
            ROOT / ".claude" / "commands" / "optimize.md",
            ROOT / ".claude" / "commands" / "publish-readiness.md",
        ]

        for path in docs:
            content = path.read_text(encoding="utf-8")
            for text in required:
                self.assertIn(text, content, f"{path.name} missing {text}")

        rule_paths = [
            ROOT / ".agents" / "rules" / "faq-answer-quality.md",
            ROOT / ".claude" / "rules" / "faq-answer-quality.md",
            ROOT / ".cursor" / "rules" / "faq-answer-quality.mdc",
        ]
        for path in rule_paths:
            self.assertTrue(path.exists(), f"{path} must exist")
            content = path.read_text(encoding="utf-8")
            for text in required:
                self.assertIn(text, content, f"{path.name} missing {text}")

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

    def test_standard_blog_faq_schema_stack_is_documented(self):
        required = [
            "BlogPosting",
            "BreadcrumbList",
            "FAQPage",
            "Person as author",
            "Question and Answer inside FAQPage",
            "ImageObject for the featured image or logo",
            "Organization as publisher reference only",
            "not a separate full schema block",
            "schema_notes",
            "top YAML frontmatter block",
            "between the opening and closing --- delimiters",
        ]

        docs = [
            ROOT / "context" / "aeo-geo-blog-strategy.md",
            ROOT / ".claude" / "commands" / "article.md",
            ROOT / ".claude" / "commands" / "write.md",
            ROOT / ".claude" / "commands" / "rewrite.md",
            ROOT / "README.md",
            ROOT / "CLAUDE.md",
            ROOT / "AGENTS.md",
        ]

        for path in docs:
            content = path.read_text(encoding="utf-8")
            for text in required:
                self.assertIn(text, content, f"{path.name} missing {text}")

        rule_paths = [
            ROOT / ".agents" / "rules" / "blog-schema.md",
            ROOT / ".claude" / "rules" / "blog-schema.md",
            ROOT / ".cursor" / "rules" / "blog-schema.mdc",
        ]
        for path in rule_paths:
            self.assertTrue(path.exists(), f"{path} must exist")
            content = path.read_text(encoding="utf-8")
            for text in required:
                self.assertIn(text, content, f"{path.name} missing {text}")

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

    def test_blog_writing_commands_document_numeric_and_because_reasoning_rules(self):
        command_paths = [
            ROOT / ".claude" / "commands" / "article.md",
            ROOT / ".claude" / "commands" / "write.md",
            ROOT / ".claude" / "commands" / "rewrite.md",
            ROOT / ".claude" / "commands" / "scrub.md",
            ROOT / ".claude" / "commands" / "publish-readiness.md",
        ]
        required = [
            "Use numerals for cardinal numbers",
            "Do not block source-visible metric wording",
            "Because comma decisions are grammar/context dependent",
            "No comma when the because clause is essential to the sentence meaning",
            "Use a comma when the because clause is nonessential, contrastive, or needed to prevent misreading",
            "Review negative constructions carefully because comma placement can change meaning",
        ]

        for path in command_paths:
            content = path.read_text(encoding="utf-8")
            self.assertNotIn(
                "Always put a comma before \"because\"",
                content,
                f"{path.name} must not require a blanket comma before because",
            )
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

    def test_403_replacement_rule_is_documented_across_publish_workflow(self):
        canonical = (ROOT / "context" / "aeo-geo-blog-strategy.md").read_text(
            encoding="utf-8"
        )
        for text in [
            "403 replacement rule",
            "manual_review",
            "public_research_link_guard.py",
            "resolved non-owned public research links",
            "Source Map notes must document the rejected 403 URL and the replacement URL",
        ]:
            self.assertIn(text, canonical)

        docs = [
            ROOT / ".claude" / "commands" / "article.md",
            ROOT / ".claude" / "commands" / "write.md",
            ROOT / ".claude" / "commands" / "rewrite.md",
            ROOT / ".claude" / "commands" / "optimize.md",
            ROOT / ".claude" / "commands" / "publish-readiness.md",
            ROOT / "README.md",
        ]
        required = [
            "403 replacement rule",
            "manual_review",
            "rejected 403 URL",
            "replacement URL",
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
            "authoritative non-owned public evidence link",
            "question-specific Source Map",
            "Context file paths and owned product links alone do not count",
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
            "public_research_link_guard",
            "metric_proof_pack_guard",
            "numeric_claim_source_guard",
            "faq_proof_guard",
            "paa_provenance_guard",
            "source_support_guard",
            "customer_proof_diversity_guard",
            "review_story_identity_guard",
            "early_artifact_guard",
            "answer_withholding_guard",
            "vault_brand_language_guard",
            "content_scorer",
        ]:
            self.assertIn(gate, content)

    def test_early_artifact_gate_is_documented_across_blog_workflow(self):
        strategy = (ROOT / "context" / "aeo-geo-blog-strategy.md").read_text(encoding="utf-8")
        for text in [
            "early_artifact_guard.py",
            "first 300 words",
            "Early Artifact Plan",
            "Early artifact requirement: not applicable",
            "Early usable artifact",
        ]:
            self.assertIn(text, strategy, f"strategy doc missing {text}")

        for name in ["write.md", "rewrite.md"]:
            command = (ROOT / ".claude" / "commands" / name).read_text(encoding="utf-8")
            self.assertIn("first 300 words", command, f"{name} missing early artifact echo")
            self.assertIn("context/aeo-geo-blog-strategy.md", command)

        readiness = (ROOT / ".claude" / "commands" / "publish-readiness.md").read_text(encoding="utf-8")
        self.assertIn("early_artifact_guard", readiness)

        editor = (ROOT / ".claude" / "agents" / "editor.md").read_text(encoding="utf-8")
        self.assertIn("Early Artifact Check", editor)

    def test_answer_withholding_gate_is_documented_across_blog_workflow(self):
        strategy = (ROOT / "context" / "aeo-geo-blog-strategy.md").read_text(encoding="utf-8")
        for text in [
            "answer_withholding_guard.py",
            "Concrete Answer Check",
            "Concrete answer requirement: not applicable",
            "Enter lender-approved value",
            "Placeholder table scaffolds block publish unconditionally",
        ]:
            self.assertIn(text, strategy, f"strategy doc missing {text}")

        for name in ["write.md", "rewrite.md"]:
            command = (ROOT / ".claude" / "commands" / name).read_text(encoding="utf-8")
            self.assertIn("placeholder table scaffolds", command, f"{name} missing scaffold echo")

        readiness = (ROOT / ".claude" / "commands" / "publish-readiness.md").read_text(encoding="utf-8")
        self.assertIn("answer_withholding_guard", readiness)

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
            "public_research_link_guard.py",
            "metric_proof_pack_guard.py",
            "numeric_claim_source_guard.py",
            "faq_proof_guard.py",
            "paa_provenance_guard.py",
            "source_support_guard.py",
            "customer_proof_diversity_guard.py",
            "review_story_identity_guard.py",
            "early_artifact_guard.py",
            "answer_withholding_guard.py",
            "vault_brand_language_guard.py",
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
            "Context file paths and owned product links alone do not count",
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

    def test_agent_governance_rules_apply_without_superpowers_duplication(self):
        rule_paths = [
            ROOT / ".cursor" / "rules" / "agent-governance.mdc",
            ROOT / ".agents" / "rules" / "agent-governance.md",
            ROOT / ".claude" / "rules" / "agent-governance.md",
        ]
        required = [
            "Superpowers owns process mechanics",
            "proof-sensitive",
            "verified evidence",
            "mirror",
            "do not duplicate",
        ]
        forbidden = [
            "superpowers:",
            "REQUIRED SUB-SKILL",
        ]

        for path in rule_paths:
            self.assertTrue(path.exists(), f"{path} must exist")
            content = path.read_text(encoding="utf-8")
            for text in required:
                self.assertIn(text, content, f"{path.name} missing {text}")
            for text in forbidden:
                self.assertNotIn(text, content, f"{path.name} must not duplicate Superpowers triggers")

        cursor_rule = (ROOT / ".cursor" / "rules" / "agent-governance.mdc").read_text(
            encoding="utf-8"
        )
        self.assertIn("alwaysApply: false", cursor_rule)

    def test_customer_proof_recent_use_and_live_scan_policy_is_cross_platform(self):
        docs = [
            ROOT / "context" / "aeo-geo-blog-strategy.md",
            ROOT / "CLAUDE.md",
            ROOT / "AGENTS.md",
            ROOT / "README.md",
            ROOT / ".claude" / "commands" / "research.md",
            ROOT / ".claude" / "commands" / "article.md",
            ROOT / ".claude" / "commands" / "write.md",
            ROOT / ".claude" / "commands" / "rewrite.md",
            ROOT / ".cursor" / "rules" / "customer-proof.mdc",
            ROOT / ".agents" / "rules" / "customer-proof.md",
            ROOT / ".claude" / "rules" / "customer-proof.md",
        ]
        required = [
            "recent_uses_90d",
            "live repo scan",
            "drafts/",
            "rewrites/",
            "research/",
            "published/",
            "backfill",
            "recently used or overused",
            "no stronger underused approved proof fits",
        ]

        for path in docs:
            content = path.read_text(encoding="utf-8")
            for text in required:
                self.assertIn(text, content, f"{path.name} missing {text}")

    def test_publish_docs_and_agents_reference_publish_readiness(self):
        docs = [
            ROOT / ".claude" / "commands" / "publish-draft.md",
            ROOT / ".claude" / "skills" / "grav-publish" / "SKILL.md",
            ROOT / ".claude" / "agents" / "content-analyzer.md",
            ROOT / ".claude" / "agents" / "editor.md",
            ROOT / ".claude" / "agents" / "seo-optimizer.md",
        ]
        for path in docs:
            content = path.read_text(encoding="utf-8")
            self.assertIn("/publish-readiness", content, f"{path.name} missing /publish-readiness")

        landing_publish = (ROOT / ".claude" / "commands" / "landing-publish.md").read_text(
            encoding="utf-8"
        )
        self.assertNotIn("Content score ≥70", landing_publish)
        self.assertIn("Full publish-readiness stack", landing_publish)

        claude = (ROOT / "CLAUDE.md").read_text(encoding="utf-8")
        self.assertNotIn("C:\\Users\\patrick.grueschow\\Desktop\\Repos\\seomachine-main", claude)

        article = (ROOT / ".claude" / "commands" / "article.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("### 12. Run Optimization Agents", article)

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
            ROOT / ".claude" / "agents" / "editor.md",
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
            "specific scenario (with name/details)",
            "when sarah launched her saas product",
            "spent six months stuck at 200 signups per month",
            "until she discovered",
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

    def test_active_blog_guidance_does_not_force_unsupported_specifics(self):
        docs = [
            ROOT / ".claude" / "commands" / "article.md",
            ROOT / ".claude" / "commands" / "write.md",
            ROOT / ".claude" / "commands" / "rewrite.md",
            ROOT / ".claude" / "agents" / "editor.md",
            ROOT / ".claude" / "skills" / "copy-editing" / "SKILL.md",
            ROOT / "context" / "style-guide.md",
            ROOT / "data_sources" / "modules" / "section_writer.py",
        ]
        forbidden_patterns = [
            r"\bmany\b\s*(?:->|\u2192)\s*['\"]?73%",
            r"\brecently\b\s*(?:->|\u2192)\s*['\"]?(?:in\s+)?(?:march\s+2024|last\s+tuesday)",
            r"\bspecific numbers? (?:are|is) included\b",
            r"replace with specific numbers?:\s*['\"]?73% of companies",
            r"\$500/month",
            r"at least one named customer or named number per major section",
            r"Save time\s*\|\s*Save 4 hours every week",
            r"Many customers\s*\|\s*2,847 teams",
            r"Fast results\s*\|\s*Results in 14 days",
        ]

        for path in docs:
            content = path.read_text(encoding="utf-8")
            for pattern in forbidden_patterns:
                self.assertIsNone(
                    re.search(pattern, content, re.IGNORECASE),
                    f"{path} still forces unsupported specificity: {pattern}",
                )

    def test_blog_editorial_quality_contracts_are_documented(self):
        workflow_docs = [
            ROOT / ".claude" / "commands" / "article.md",
            ROOT / ".claude" / "commands" / "write.md",
            ROOT / ".claude" / "commands" / "rewrite.md",
        ]
        reader_contract_terms = [
            "Reader Contract",
            "Primary reader",
            "Sophistication level",
            "Trigger problem",
            "Existing belief",
            "Decision or task helped",
            "Distinctive angle",
            "Promised payoff",
            "Funnel stage",
            "Exclusions",
        ]
        continuity_terms = [
            "Continuity Pass",
            "advance the headline promise",
            "question created by the previous section",
            "repeated resets",
            "logical relationship",
            "complete the introduction",
            "remove or justify",
        ]
        scene_terms = [
            "0-2 editorial scenes",
            "materially improve understanding",
            "Named people or businesses require approved proof",
            "Unnamed workflow scenarios are explanatory only",
            "invented names, dates, metrics, quotes, and outcomes",
        ]
        cta_terms = [
            "intent-sensitive CTA",
            "ToFu: 0-1 soft resource/action CTA",
            "MoFu: one educational next step plus one contextual product CTA",
            "BoFu: 2-3 contextual commercial CTAs",
            "Thought leadership: discussion, reflection, or evidence resource",
        ]
        keyword_terms = [
            "intent/evidence-complete word target",
            "natural terminology coverage",
            "critical keyword placement",
            "semantic variations",
            "keyword-stuffing detection",
        ]

        for path in workflow_docs:
            content = path.read_text(encoding="utf-8")
            for text in reader_contract_terms:
                self.assertIn(text, content, f"{path.name} missing {text}")
            for text in continuity_terms:
                self.assertIn(text, content, f"{path.name} missing {text}")
            for text in scene_terms:
                self.assertIn(text, content, f"{path.name} missing {text}")
            for text in cta_terms:
                self.assertIn(text, content, f"{path.name} missing {text}")
            for text in keyword_terms:
                self.assertIn(text, content, f"{path.name} missing {text}")

        article_command = workflow_docs[0].read_text(encoding="utf-8")
        self.assertNotIn("**Proof-Backed POV**", article_command)
        self.assertGreaterEqual(article_command.count("**Editorial Scene**"), 4)
        self.assertIn("1. **Create Reader Contract**", article_command)
        self.assertIn("3. **Create Reader-Guided Structure**", article_command)
        self.assertNotIn("2. **Create Google-Validated Structure**", article_command)
        self.assertLess(
            article_command.index("1. **Create Reader Contract**"),
            article_command.index("3. **Create Reader-Guided Structure**"),
            "article.md must resolve the Reader Contract before SERP-derived structure planning",
        )

    def test_editorial_docs_remove_hard_story_length_density_requirements(self):
        docs = [
            ROOT / ".claude" / "commands" / "article.md",
            ROOT / ".claude" / "commands" / "write.md",
            ROOT / ".claude" / "commands" / "rewrite.md",
            ROOT / ".claude" / "commands" / "optimize.md",
            ROOT / ".claude" / "commands" / "analyze-existing.md",
            ROOT / ".claude" / "commands" / "research-serp.md",
            ROOT / ".claude" / "commands" / "cluster.md",
            ROOT / ".claude" / "commands" / "priorities.md",
            ROOT / ".claude" / "commands" / "research-topics.md",
            ROOT / ".claude" / "agents" / "editor.md",
            ROOT / ".claude" / "agents" / "seo-optimizer.md",
            ROOT / ".claude" / "agents" / "content-analyzer.md",
            ROOT / ".claude" / "agents" / "cluster-strategist.md",
            ROOT / ".claude" / "agents" / "performance.md",
            ROOT / ".claude" / "agents" / "keyword-mapper.md",
            ROOT / ".claude" / "agents" / "meta-creator.md",
            ROOT / ".claude" / "skills" / "copy-editing" / "SKILL.md",
            ROOT / ".claude" / "skills" / "seo-audit" / "references" / "aeo-geo-patterns.md",
            ROOT / "README.md",
            ROOT / "context" / "seo-guidelines.md",
            ROOT / "context" / "style-guide.md",
            ROOT / "context" / "features.md",
            ROOT / "scripts" / "research_serp_analysis.py",
            ROOT / "scripts" / "research_trending.py",
            ROOT / "scripts" / "research_quick_wins.py",
            ROOT / "scripts" / "research_priorities_comprehensive.py",
            ROOT / "scripts" / "research_performance_matrix.py",
            ROOT / "scripts" / "research_competitor_gaps.py",
            ROOT / "data_sources" / "modules" / "content_length_comparator.py",
            ROOT / "data_sources" / "modules" / "competitor_gap_analyzer.py",
            ROOT / "data_sources" / "modules" / "social_research_aggregator.py",
        ]
        forbidden_patterns = [
            r"specific scenarios " + r"with names",
            r"names, details, " + r"and outcomes",
            r"Mini-Story Check " + r"\(2-3 required",
            r"Minimum 2000 " + r"words",
            r"Keyword density " + r"1-2%",
            r"Primary Keyword Density.*"
            + r"1-2%",
            r"Target:\s*1\.0-2\.0%",
            r"1\.5%\s+density.*\u2713",
            r"Write\s+2,500\+\s+words",
            r"Main Body\s+\(1800-2500\+\s+words\)",
            r"Target Word Count\*\*:\s+Minimum words needed to compete",
            r"Word count expansion",
            r"optimal keyword placement and density",
            r"(?:Introduction|Conclusion)\s+\(150[-\u2013]2(?:00|50)\s+words\)",
            r"\b(?:200[-\u2013]300|250[-\u2013]400|300[-\u2013]400)\s+words(?:\s+per section|\s+total)",
            r"Minimum\*\*:\s+150 words per H2",
            r"Maximum\*\*:\s+500 words per H2",
            r"Ideal\*\*:\s+250[-\u2013]350 words per main section",
            r"subheadings every 300[-\u2013]400 words",
            r"Section length within 150[-\u2013]500 words",
            r"\(Good\)|\(Sparse\)|\(Missing!\)",
            r"optimal/too_low/too_high",
            r"too_short/short/competitive/optimal/long",
            r"recommended word count",
            r"average\s*\+\s*10%",
            r"exceed average by 10%",
            r"meets/exceeds the recommended word count",
            r"exact word count targets",
            r"optimal density targets",
            r"optimal content length recommendation",
            r"determine optimal word count",
            r"Add\s+\d[\d,]*\s+words",
            r"Content expansion.*length comparison",
            r"\b1,500[-\u2013]3,000\b",
            r"\b2,000\+\s+word",
            r"\b2500\+\s+word",
            r"\b2000\+\s+word",
            r"\b2000[-\u2013]3000\b",
            r"\b3,000[-\u2013]5,000\s+words\b",
            r"\b3000\+\s+words\b",
            r"\b500\+\s+words\b",
            r"\b500[-\u2013]800\s+words\b",
            r"\b300[-\u2013]500\s+words\s+minimum\b",
            r"\b250[-\u2013]400\s+words\b",
            r"target word count based on competitor analysis",
            r"Improve keyword density and placement",
            r"optimal blog length",
            r"Distribution Heat Map",
            r"exact-match instance",
            r"(?:Introduction|Section \d+|Conclusion)\s+\(\d+[-\u2013]\d+ words\)",
            r"Target:\s*3/5",
            r"unless\s+3,000\+\s+word article",
            r"Only\s+1\s+instance\s+in\s+400\s+words",
            r"Specific scenario\s+\(with name/details\)",
            r"when Sarah launched her SaaS product",
            r"spent six months stuck at 200 signups per month",
            r"\bmany\b\s*(?:->|\u2192)\s*['\"]?73%",
            r"\$500/month",
            r"At least one named customer or named number per major section",
            r"Length:\s*\[behind/competitive/leading\]",
            r"Competitive length benchmarks",
            r"New sections to add based on competitive gap analysis",
            r"New sections to fill competitive content gaps",
            r"Deepen shallow sections with more detail",
            r"Google-Validated Structure",
            r"sections appear essential",
            r"ranking sections appear essential",
            r"Include top-ranking sections unless",
            r"Address 3\+ competitor gaps",
            r"Fine-tunes keyword placement and density",
            r"4[-\u2013]7 H2 sections",
            r"2[-\u2013]3 (?:should include|H2s include|with) keyword variations",
            r"(?:keyword|primary keyword).{0,30}(?:2[-\u2013]3|2\+) H2",
            r"(?:at least )?2[-\u2013]3 H2 headings",
            r"(?:keyword|primary keyword).{0,40}at least [2-9] H2",
        ]

        for path in docs:
            content = path.read_text(encoding="utf-8")
            for pattern in forbidden_patterns:
                self.assertIsNone(
                    re.search(pattern, content, re.IGNORECASE),
                    f"{path.name} still contains hard editorial proxy: {pattern}",
                )

    def test_serp_gap_and_named_proof_guidance_uses_strong_defaults_with_guards(self):
        research_serp = (
            ROOT / ".claude" / "commands" / "research-serp.md"
        ).read_text(encoding="utf-8")
        article = (ROOT / ".claude" / "commands" / "article.md").read_text(
            encoding="utf-8"
        )
        priorities = (
            ROOT / "scripts" / "research_priorities_comprehensive.py"
        ).read_text(encoding="utf-8")
        seo_guidelines = (ROOT / "context" / "seo-guidelines.md").read_text(
            encoding="utf-8"
        )
        readme = (ROOT / "README.md").read_text(encoding="utf-8")

        for text in [
            "understand what Google wants",
            "Match the dominant observed content type by default",
            "target every applicable feature",
            "Reader Contract exception",
            "Must-have elements",
            "Recommended structure",
        ]:
            self.assertIn(text, research_serp)

        for text in [
            "MUST-FILL GAPS",
            "Success Stories Found",
            "structure that ranks",
            "opportunities to beat",
            "recurring, reader-critical",
            "Named people or businesses require approved proof",
            "## SERP Strategy Decision",
            "do not continue with an undocumented deviation",
        ]:
            self.assertIn(text, article)

        self.assertIn("Evaluate all identified SERP features", priorities)
        self.assertIn("target every applicable feature", priorities)
        self.assertIn("Evaluate all identified coverage gaps", priorities)
        self.assertIn("recurring, reader-critical, evidence-supported", priorities)
        self.assertIn("document the Reader Contract exception", priorities)
        self.assertIn("Use approved named customer proof", seo_guidelines)
        self.assertIn("approved named customer proof", readme)

    def test_direct_writing_workflows_preserve_serp_decision_handoff(self):
        for relative_path in (
            ".claude/commands/write.md",
            ".claude/commands/rewrite.md",
        ):
            content = (ROOT / relative_path).read_text(encoding="utf-8")
            self.assertIn("## SERP Strategy Decision", content)
            self.assertIn("dominant observed content type", content)
            self.assertIn("documented Reader Contract exception", content)
            self.assertIn("verified SERP", content)

    def test_blog_docs_do_not_use_h2_quotas_or_universal_video_embeds(self):
        active_docs = [
            ROOT / ".claude" / "commands" / "article.md",
            ROOT / ".claude" / "commands" / "write.md",
            ROOT / ".claude" / "commands" / "optimize.md",
            ROOT / ".claude" / "agents" / "seo-optimizer.md",
            ROOT / ".claude" / "agents" / "keyword-mapper.md",
            ROOT / "context" / "seo-guidelines.md",
        ]
        h2_quota = re.compile(
            r"H2[^\n]{0,80}(?:\bneed\b|\bminimum\b|\btarget\s*:)[^\n]{0,40}\d",
            re.IGNORECASE,
        )
        universal_video = re.compile(
            r"(?:include|embed|require)[^\n]{0,35}at least one[^\n]{0,30}video|"
            r"at least one[^\n]{0,30}video[^\n]{0,35}(?:include|embed|required)",
            re.IGNORECASE,
        )

        for path in active_docs:
            content = path.read_text(encoding="utf-8")
            self.assertIsNone(h2_quota.search(content), f"H2 quota remains in {path}")
            self.assertIsNone(
                universal_video.search(content),
                f"Universal video requirement remains in {path}",
            )

        article = active_docs[0].read_text(encoding="utf-8")
        self.assertIn("omit the embed", article)
        self.assertIn("VideoObject only when a video is embedded", article)

    def test_proof_infrastructure_routes_only_to_validation_sidecars(self):
        article = (ROOT / ".claude" / "commands" / "article.md").read_text(
            encoding="utf-8"
        )
        rewrite = (ROOT / ".claude" / "commands" / "rewrite.md").read_text(
            encoding="utf-8"
        )

        for content in (article, rewrite):
            self.assertIn("Proof infrastructure belongs only in the validation sidecar", content)
            self.assertIn("sidecar path and status", content)

    def test_fallback_style_and_linter_guidance_remain_proof_safe(self):
        style = (ROOT / "context" / "style-guide.md").read_text(encoding="utf-8")
        brand_voice = (ROOT / "context" / "brand-voice.md").read_text(
            encoding="utf-8"
        )
        features = (ROOT / "context" / "features.md").read_text(encoding="utf-8")
        linter = (
            ROOT / "data_sources" / "modules" / "ai_copy_linter.py"
        ).read_text(encoding="utf-8")

        self.assertNotIn("Always put a comma before because", style)
        self.assertNotIn("Em dashes (—) not hyphens with spaces", style)
        self.assertIn("grammar and sentence meaning", style)
        self.assertNotIn("number, named scenario", linter)
        self.assertIn("approved proof", linter)
        self.assertNotIn(
            "At least one named customer, named number, or named trade per major section",
            brand_voice,
        )
        self.assertNotIn(
            "Round numbers, named customers, specific outcomes — always",
            brand_voice,
        )
        self.assertIn("approved named customers", brand_voice)
        self.assertNotIn("Quantify everything possible", features)
        self.assertIn("Quantify only from approved proof", features)

    def test_analyzer_guidance_does_not_turn_analysis_into_unapproved_public_proof(self):
        analyzer = (
            ROOT / ".claude" / "agents" / "content-analyzer.md"
        ).read_text(encoding="utf-8")

        self.assertIn("verified observed values", analyzer)
        self.assertIn("approved public proof", analyzer)
        self.assertIn("Do not fabricate before/after impact estimates", analyzer)
        self.assertNotIn("Use exact numbers and percentages from analysis modules", analyzer)
        self.assertNotIn("Show before/after impact estimates", analyzer)
        self.assertNotIn("improvement in ranking potential", analyzer)
        self.assertNotIn("Examples and data included", analyzer)

        analyze_existing = (
            ROOT / ".claude" / "commands" / "analyze-existing.md"
        ).read_text(encoding="utf-8")
        self.assertNotIn("Potential traffic increase", analyze_existing)
        self.assertIn("evidence-bound expected direction", analyze_existing)

    def test_serp_research_guidance_keeps_verified_patterns_as_strong_defaults(self):
        research_serp = (
            ROOT / ".claude" / "commands" / "research-serp.md"
        ).read_text(encoding="utf-8")

        self.assertNotIn("without treating them as requirements", research_serp)
        self.assertIn("applicable verified patterns as strong defaults", research_serp)
        self.assertIn("recurring observed structure", research_serp)

    def test_article_strategy_template_exposes_all_exception_and_gap_lanes(self):
        article = (ROOT / ".claude" / "commands" / "article.md").read_text(
            encoding="utf-8"
        )

        for exception_type in [
            "content_type",
            "serp_feature",
            "serp_structure",
            "competitor_gap",
            "cta",
        ]:
            self.assertIn(f"`{exception_type}:", article)
        self.assertIn("QUALIFICATION REQUIRED", article)
        self.assertIn("reader importance and evidence", article)

    def test_blog_guidance_removes_universal_cta_requirements(self):
        docs = [
            ROOT / ".claude" / "commands" / "article.md",
            ROOT / ".claude" / "commands" / "write.md",
            ROOT / ".claude" / "commands" / "rewrite.md",
            ROOT / ".claude" / "commands" / "optimize.md",
            ROOT / ".claude" / "commands" / "analyze-existing.md",
            ROOT / ".claude" / "commands" / "cluster.md",
            ROOT / ".claude" / "commands" / "priorities.md",
            ROOT / ".claude" / "commands" / "research-topics.md",
            ROOT / ".claude" / "agents" / "editor.md",
            ROOT / ".claude" / "agents" / "seo-optimizer.md",
            ROOT / ".claude" / "agents" / "content-analyzer.md",
            ROOT / ".claude" / "agents" / "cluster-strategist.md",
            ROOT / ".claude" / "agents" / "performance.md",
            ROOT / ".claude" / "agents" / "meta-creator.md",
            ROOT / ".claude" / "skills" / "copy-editing" / "SKILL.md",
            ROOT / "README.md",
            ROOT / "context" / "seo-guidelines.md",
            ROOT / "context" / "style-guide.md",
        ]
        forbidden = [
            "CTA included",
            "Strong CTA with risk reversal",
            "Clear CTA in conclusion",
            "Make the CTA obvious, early, and repeated",
            "Conclusion with CTA",
            "Include relevant call-to-action",
            "Stronger conclusion and CTA",
            "Strong summary and clear CTA",
            "Clear call-to-action",
            "keyword & CTA",
            "Include a verb-driven CTA",
            "Problem-Solution-CTA",
            "Demo- or trial-aligned CTA",
            "Objections addressed near CTA",
            "Risk reversals stated",
            "**Clear CTAs**",
        ]

        for path in docs:
            content = path.read_text(encoding="utf-8")
            for text in forbidden:
                self.assertNotIn(
                    text.lower(),
                    content.lower(),
                    f"{path.name} still contains universal CTA requirement: {text}",
                )

        features = (ROOT / "context" / "features.md").read_text(encoding="utf-8")
        self.assertIn("Follow the Reader Contract", features)
        self.assertIn("ToFu may use zero or one", features)
        self.assertIn("thought leadership may close", features)

    def test_headline_and_copy_editing_quality_upgrades_are_documented(self):
        headline = (ROOT / ".claude" / "agents" / "headline-generator.md").read_text(
            encoding="utf-8"
        )
        for text in [
            "Reader Specificity",
            "Payoff Clarity",
            "Distinctiveness",
            "Promise Integrity",
            "Numbers, timeframes, superlatives, urgency, and transformation claims require proof",
        ]:
            self.assertIn(text, headline)

        copy_editing = (
            ROOT / ".claude" / "skills" / "copy-editing" / "SKILL.md"
        ).read_text(encoding="utf-8")
        for text in [
            "### Sweep 6: Stakes and Relevance",
            "operational consequence",
            "affected role",
            "decision pressure",
            "proof-safe author/customer experience",
        ]:
            self.assertIn(text, copy_editing)
        self.assertNotIn("### Sweep 6: Heightened Emotion", copy_editing)

    def test_active_style_and_editor_guidance_keep_specificity_proof_safe(self):
        style = (ROOT / "context" / "style-guide.md").read_text(encoding="utf-8")
        brand_voice = (ROOT / "context" / "brand-voice.md").read_text(
            encoding="utf-8"
        )
        editor = (ROOT / ".claude" / "agents" / "editor.md").read_text(
            encoding="utf-8"
        )

        self.assertIn("numbers and named customers require approved proof", style)
        self.assertIn("otherwise explain concrete workflow value", style)
        self.assertIn("Use named outcomes only when approved proof fits", brand_voice)
        self.assertIn("Proof-approved surprising statistic", editor)
        for stale in (
            "every claim ties to a number or a customer",
            "named-numbers",
            "named-outcome, proof-led",
            "  - Surprising statistic",
        ):
            self.assertNotIn(stale, style + "\n" + brand_voice + "\n" + editor)

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


    def test_workflow_docs_require_obsidian_vault_first_context(self):
        docs = [
            ROOT / "AGENTS.md",
            ROOT / "CLAUDE.md",
            ROOT / "README.md",
            ROOT / ".claude" / "commands" / "research.md",
            ROOT / ".claude" / "commands" / "article.md",
            ROOT / ".claude" / "commands" / "write.md",
            ROOT / ".claude" / "commands" / "rewrite.md",
            ROOT / ".claude" / "commands" / "analyze-existing.md",
        ]
        required = [
            "Obsidian Vault Source Rule",
            r"C:\Users\patrick.grueschow\Desktop\Obsidian\Simpro Brand Context",
            "AGENTS.md -> wiki/cache/hot.md -> wiki/Brand Graph Index.md -> smallest relevant wiki/source/raw pages",
            "repo-local context files are downstream mirrors/fallbacks only",
            "cannot override the vault when the vault is available",
            "Do not use Google Workspace or old marketing-portal URLs as the active read path",
            "Vault Context Read Path",
        ]

        for path in docs:
            content = path.read_text(encoding="utf-8")
            for text in required:
                self.assertIn(text, content, f"{path.name} missing {text}")

    def test_competitor_shortlist_requires_vault_backed_decision(self):
        docs = [
            ROOT / "CLAUDE.md",
            ROOT / "README.md",
            ROOT / ".claude" / "commands" / "research.md",
            ROOT / ".claude" / "commands" / "article.md",
            ROOT / ".claude" / "commands" / "write.md",
            ROOT / ".claude" / "commands" / "rewrite.md",
            ROOT / ".claude" / "commands" / "analyze-existing.md",
            ROOT / "context" / "competitor-analysis.md",
        ]
        required = [
            "Competitive Shortlist Decision",
            "selected competitors",
            "rejected competitors",
            "wiki/competitors/Competitive Context.md",
            "wiki/sources/simpro-battlecards-direct-competitors-1bzgf9r8.md",
            "linked source/raw files",
            "Public competitor pages may shape SERP/article format, but cannot decide named competitors for Simpro public copy",
        ]

        for path in docs:
            content = path.read_text(encoding="utf-8")
            for text in required:
                self.assertIn(text, content, f"{path.name} missing {text}")

    def test_hindsight_boundary_is_documented_for_public_claims(self):
        docs = [
            ROOT / "CLAUDE.md",
            ROOT / "README.md",
            ROOT / ".claude" / "commands" / "research.md",
            ROOT / ".claude" / "commands" / "article.md",
            ROOT / ".claude" / "commands" / "write.md",
            ROOT / ".claude" / "commands" / "rewrite.md",
            ROOT / ".claude" / "commands" / "analyze-existing.md",
            ROOT / "context" / "competitor-analysis.md",
        ]
        required = [
            "Hindsight Boundary",
            "Hindsight/deal intelligence can inform internal strategy",
            "cannot be published as proof, rankings, metrics, or claims unless separately approved and source-verified",
            "wiki/sources/hindsight-copy-of-simpro-battlecards-1elcobgn.md",
        ]

        for path in docs:
            content = path.read_text(encoding="utf-8")
            for text in required:
                self.assertIn(text, content, f"{path.name} missing {text}")

    def test_named_feature_add_on_link_check_is_documented(self):
        docs = [
            ROOT / "CLAUDE.md",
            ROOT / "README.md",
            ROOT / ".claude" / "commands" / "article.md",
            ROOT / ".claude" / "commands" / "write.md",
            ROOT / ".claude" / "commands" / "rewrite.md",
            ROOT / ".claude" / "commands" / "analyze-existing.md",
            ROOT / "context" / "aeo-geo-blog-strategy.md",
        ]
        required = [
            "Named Feature/Add-On Link Check",
            "first meaningful mentions of Simpro features/add-ons",
            "wiki/concepts/payments-and-add-ons.md",
            "wiki/features/Feature Library",
            "vault route checked",
            "link decision",
        ]

        for path in docs:
            content = path.read_text(encoding="utf-8")
            for text in required:
                self.assertIn(text, content, f"{path.name} missing {text}")

    def test_vault_brand_language_alignment_is_documented(self):
        docs = [
            ROOT / "context" / "aeo-geo-blog-strategy.md",
            ROOT / "AGENTS.md",
            ROOT / "CLAUDE.md",
            ROOT / "README.md",
            ROOT / ".claude" / "commands" / "research.md",
            ROOT / ".claude" / "commands" / "article.md",
            ROOT / ".claude" / "commands" / "write.md",
            ROOT / ".claude" / "commands" / "rewrite.md",
            ROOT / ".claude" / "commands" / "analyze-existing.md",
            ROOT / ".claude" / "commands" / "optimize.md",
            ROOT / ".claude" / "commands" / "publish-readiness.md",
        ]
        required = [
            "Vault Brand Language Alignment",
            "vault_brand_language_guard.py",
            "wiki/messaging/Simpro Core Messaging Repository.md",
            "wiki/messaging/Message House.md",
            "wiki/messaging/Core Value Pillars.md",
            "wiki/product/Product Positioning.md",
            "wiki/features/Feature Library.md",
            "wiki/features/source-docs/",
            "wiki/verticals/Vertical Profile Library.md",
            "repo-local `context/brand-voice.md` and `context/style-guide.md` are fallback mirrors",
            "Status: aligned",
            "/publish-readiness",
        ]

        for path in docs:
            content = path.read_text(encoding="utf-8")
            for text in required:
                self.assertIn(text, content, f"{path.name} missing {text}")

    def test_source_routing_decision_is_documented(self):
        source_routing_map = (ROOT / "context" / "source-routing-map.md").read_text(
            encoding="utf-8"
        )
        canonical = (ROOT / "context" / "aeo-geo-blog-strategy.md").read_text(
            encoding="utf-8"
        )
        publish_readiness = (ROOT / ".claude" / "commands" / "publish-readiness.md").read_text(
            encoding="utf-8"
        )

        required = [
            "Source Routing Decision",
            "source_routing_guard.py",
            "Brand voice, audience, ICP, message pillars, tone",
            "SEO mechanics, AEO/GEO workflow, schema notes, publish gates",
            "Customer proof, quotes, metrics, review stories, approval status",
            "Status: aligned",
        ]

        for content, name in [
            (source_routing_map, "source-routing-map.md"),
            (canonical, "aeo-geo-blog-strategy.md"),
            (publish_readiness, "publish-readiness.md"),
        ]:
            for text in required:
                self.assertIn(text, content, f"{name} missing {text}")

    def test_pmm_qa_rule_is_not_part_of_repo_guardrail_update(self):
        docs = [
            ROOT / "AGENTS.md",
            ROOT / "CLAUDE.md",
            ROOT / "README.md",
            ROOT / ".claude" / "commands" / "research.md",
            ROOT / ".claude" / "commands" / "article.md",
            ROOT / ".claude" / "commands" / "write.md",
            ROOT / ".claude" / "commands" / "rewrite.md",
            ROOT / ".claude" / "commands" / "analyze-existing.md",
            ROOT / "context" / "aeo-geo-blog-strategy.md",
            ROOT / "context" / "competitor-analysis.md",
        ]
        forbidden = [
            "Self-Generated Blog PMM QA Rule",
            "AI/self-generated blogs with competitor, product, or proof claims require PMM QA before dev-ready handoff",
            "External PMM QA",
        ]

        for path in docs:
            content = path.read_text(encoding="utf-8")
            for text in forbidden:
                self.assertNotIn(text, content, f"{path.name} must not include deferred PMM QA rule")


    def test_fred_authority_workflow_is_mandatory_and_source_bounded(self):
        selector_command = (
            'python data_sources/modules/fred_authority_selector.py "[topic]" '
            '--title "[title]" --objective "[objective]" --slate --limit 5'
        )
        workflow_paths = [
            ROOT / ".claude" / "commands" / "research.md",
            ROOT / ".claude" / "commands" / "article.md",
            ROOT / ".claude" / "commands" / "write.md",
            ROOT / ".claude" / "commands" / "rewrite.md",
            ROOT / ".claude" / "commands" / "analyze-existing.md",
            ROOT / ".claude" / "commands" / "optimize.md",
        ]
        workflow_required = [
            selector_command,
            "Fred Voccola Authority Selection",
            "Evaluation is mandatory",
            "public use is optional",
            "validation sidecar",
        ]
        for path in workflow_paths:
            content = path.read_text(encoding="utf-8")
            for text in workflow_required:
                self.assertIn(text, content, f"{path.name} missing {text}")

        canonical_paths = [
            ROOT / "AGENTS.md",
            ROOT / "CLAUDE.md",
            ROOT / "README.md",
            ROOT / "context" / "aeo-geo-blog-strategy.md",
        ]
        canonical_required = [
            "fred-voccola-media-inventory.csv",
            "authority-signal-matrix.csv",
            "same paragraph",
            "source_visible_article_text",
            "transcript_and_playback",
            "paraphrase_evidence",
            "playlist-only",
            "youtube-nocookie.com",
            "VideoObject",
            "Expertise",
            "Authority",
            "Experience",
            "customer Experience proof",
            "No usage ledger",
            "public use is optional",
        ]
        for path in canonical_paths:
            content = path.read_text(encoding="utf-8")
            self.assertIn(selector_command, content, f"{path.name} missing selector command")
            for text in canonical_required:
                self.assertIn(text, content, f"{path.name} missing {text}")

        strategy = (ROOT / "context" / "aeo-geo-blog-strategy.md").read_text(
            encoding="utf-8"
        )
        sidecar_fields = [
            "Selector command",
            "Evaluation status",
            "Top candidates",
            "Selected",
            "Fit decision",
            "Intended use",
            "Target section",
            "Authority row",
            "Public URL",
            "Evidence status",
            "Verification method",
            "Evidence excerpt",
            "Timestamp or locator",
            "Playback verified",
            "Exact quote",
            "Embed decision",
            "VideoObject",
        ]
        for field in sidecar_fields:
            self.assertIn(f"- {field}:", strategy, f"canonical strategy missing {field}")

        publish_doc = (ROOT / ".claude" / "commands" / "publish-readiness.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("fred_authority", publish_doc)
        self.assertIn("fred_authority_guard.py", publish_doc)

    def test_faq_source_selection_policy_is_documented_and_enforced(self):
        canonical_paths = [
            ROOT / "AGENTS.md",
            ROOT / "context" / "aeo-geo-blog-strategy.md",
        ]
        workflow_paths = [
            ROOT / ".claude" / "commands" / "article.md",
            ROOT / ".claude" / "commands" / "research.md",
            ROOT / ".claude" / "commands" / "rewrite.md",
            ROOT / ".claude" / "commands" / "write.md",
            ROOT / ".claude" / "commands" / "optimize.md",
            ROOT / ".claude" / "commands" / "publish-readiness.md",
        ]
        required = [
            "FAQ Source Policy",
            "neutral",
            "non_competing_expert",
            "Competitor-owned FAQ sources: prohibited",
            "FAQ Proof Map",
        ]

        for path in canonical_paths + workflow_paths:
            content = path.read_text(encoding="utf-8")
            for text in required:
                self.assertIn(text, content, f"{path.name} missing {text}")

    def test_cod_editorial_voice_routes_and_em_dash_policy_are_enforced(self):
        canonical_paths = [
            ROOT / "AGENTS.md",
            ROOT / "context" / "aeo-geo-blog-strategy.md",
            ROOT / "context" / "style-guide.md",
        ]
        workflow_paths = [
            ROOT / ".claude" / "commands" / "article.md",
            ROOT / ".claude" / "commands" / "write.md",
            ROOT / ".claude" / "commands" / "rewrite.md",
            ROOT / ".claude" / "commands" / "optimize.md",
            ROOT / ".claude" / "commands" / "scrub.md",
            ROOT / ".claude" / "commands" / "publish-readiness.md",
        ]
        required = [
            "wiki/messaging/Voice and Tone.md",
            "wiki/messaging/Tone Voice and Localization Rules.md",
            "Named-author Simpro blogs and thought leadership",
            "first-person judgment",
            "Author opinion must remain distinguishable from empirical fact",
            "Em dashes are prohibited",
            "Product pages and landing pages retain their existing restrained channel treatment",
        ]

        for path in canonical_paths + workflow_paths:
            content = path.read_text(encoding="utf-8")
            for text in required:
                self.assertIn(text, content, f"{path.name} missing {text}")

        forbidden_permissions = [
            "**em dashes**: use",
            "use em dashes",
            "em dashes are allowed",
            "em dash is permitted",
        ]
        for path in canonical_paths + workflow_paths:
            content = path.read_text(encoding="utf-8").lower()
            for text in forbidden_permissions:
                self.assertNotIn(
                    text,
                    content,
                    f"{path.name} simultaneously permits and prohibits em dashes",
                )

    def test_named_feature_status_gate_is_documented(self):
        publish_doc = (
            ROOT / ".claude" / "commands" / "publish-readiness.md"
        ).read_text(encoding="utf-8")
        canonical = (
            ROOT / "context" / "aeo-geo-blog-strategy.md"
        ).read_text(encoding="utf-8")

        for content, name in [
            (publish_doc, "publish-readiness.md"),
            (canonical, "aeo-geo-blog-strategy.md"),
        ]:
            self.assertIn("Named Feature Status and Commercial Treatment", content, name)
            self.assertIn("named_feature_status_guard.py", content, name)
            self.assertIn("Named Feature Status", content, name)

if __name__ == "__main__":
    unittest.main()
