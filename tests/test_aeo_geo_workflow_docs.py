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
            "content_scorer.py",
            "/optimize",
            "85/100",
            "90/100",
        ]

        for text in required:
            self.assertIn(text, rewrite)

    def test_blog_commands_require_eeat_proof_map_inputs(self):
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
            "context/internal-links-map.md",
            "context/features.md",
            "context/competitor-analysis.md",
            "public-facing source links",
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
            "Do not write number words",
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
            "E-E-A-T proof",
            "Experience proof present/missing",
            "Expertise proof present/missing",
            "Review-site VoC candidates",
        ]

        for text in required:
            self.assertIn(text, analyze)

    def test_review_site_experience_evidence_boundary_is_documented(self):
        docs = [
            ROOT / "context" / "aeo-geo-blog-strategy.md",
            ROOT / ".claude" / "commands" / "research.md",
            ROOT / ".claude" / "commands" / "article.md",
            ROOT / ".claude" / "commands" / "write.md",
            ROOT / ".claude" / "commands" / "rewrite.md",
            ROOT / ".claude" / "commands" / "analyze-existing.md",
            ROOT / "CLAUDE.md",
        ]
        required = [
            "review-site experience evidence",
            "first-hand customer experience",
            "star ratings, badges, rankings",
            "current source verification and brief-level approval",
        ]

        for path in docs:
            content = path.read_text(encoding="utf-8")
            for text in required:
                self.assertIn(text, content, f"{path.name} missing {text}")

    def test_customer_proof_pack_contract_is_documented(self):
        docs = [
            ROOT / "context" / "aeo-geo-blog-strategy.md",
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
            "Quote Matrix candidates",
            "Case-study proof paths",
            "Review-site experience evidence",
            "Pack status",
            "Claims excluded",
            "approval status",
        ]

        for path in docs:
            content = path.read_text(encoding="utf-8")
            for text in required:
                self.assertIn(text, content, f"{path.name} missing {text}")

    def test_url_validation_gate_is_documented_across_publish_workflow(self):
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
            "data_sources/modules/url_validator.py",
            "--fail-on unresolved",
            "does not prove the page supports the claim",
        ]

        for path in docs:
            content = path.read_text(encoding="utf-8")
            for text in required:
                self.assertIn(text, content, f"{path.name} missing {text}")

    def test_faq_proof_gate_is_documented_across_blog_workflow(self):
        docs = [
            ROOT / ".claude" / "commands" / "article.md",
            ROOT / ".claude" / "commands" / "write.md",
            ROOT / ".claude" / "commands" / "rewrite.md",
            ROOT / "context" / "aeo-geo-blog-strategy.md",
            ROOT / "README.md",
            ROOT / "CLAUDE.md",
        ]
        required = [
            "FAQ proof",
            "data_sources/modules/faq_proof_guard.py",
            "public proof link",
            "question-specific Source Map",
            "Context file paths alone do not count",
        ]

        for path in docs:
            content = path.read_text(encoding="utf-8")
            for text in required:
                self.assertIn(text, content, f"{path.name} missing {text}")

    def test_numeric_claim_source_guard_is_documented_globally(self):
        docs = [
            ROOT / ".claude" / "commands" / "optimize.md",
            ROOT / ".claude" / "commands" / "write.md",
            ROOT / ".claude" / "commands" / "rewrite.md",
            ROOT / ".claude" / "commands" / "article.md",
            ROOT / "README.md",
            ROOT / "CLAUDE.md",
        ]
        required = [
            "metric, statistic, or numeric business claim",
            "data_sources/modules/numeric_claim_source_guard.py",
            "--fail-on error",
            "public URL or local proof artifact",
        ]

        for path in docs:
            content = path.read_text(encoding="utf-8")
            for text in required:
                self.assertIn(text, content, f"{path.name} missing {text}")


if __name__ == "__main__":
    unittest.main()
