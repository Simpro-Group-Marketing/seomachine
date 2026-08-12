import re
import shlex
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _fenced_block_after(content: str, heading: str) -> str:
    heading_index = content.index(heading)
    fence_start = content.index("```", heading_index) + 3
    newline = content.find("\n", fence_start)
    if newline >= 0 and content[fence_start:newline].strip().casefold() in {
        "markdown",
        "text",
        "powershell",
    }:
        fence_start = newline + 1
    fence_end = content.index("```", fence_start)
    return content[fence_start:fence_end].strip() + "\n"


def _mutation_recorder_commands(content: str) -> list[list[str]]:
    script = "data_sources/modules/blog_assembly_mutation_recorder.py"
    commands: list[list[str]] = []
    for line in content.splitlines():
        stripped = line.strip()
        if not stripped.startswith(f"python {script} "):
            continue
        tokens = shlex.split(stripped, posix=True)
        if len(tokens) >= 3 and tokens[1] == script:
            commands.append(tokens[2:])
    return commands


def _command_option_values(command: list[str], option: str) -> list[str]:
    return [
        command[index + 1]
        for index, token in enumerate(command[:-1])
        if token == option
    ]


class AeoGeoWorkflowDocsTests(unittest.TestCase):
    def test_blog_workflows_document_the_executable_nonconnector_receipt_branch(self):
        workflow_paths = [
            ROOT / "README.md",
            ROOT / "context" / "aeo-geo-blog-strategy.md",
            ROOT / ".claude" / "commands" / "article.md",
            ROOT / ".claude" / "commands" / "write.md",
            ROOT / ".claude" / "commands" / "rewrite.md",
            ROOT / ".claude" / "commands" / "optimize.md",
            ROOT / ".claude" / "commands" / "publish-readiness.md",
        ]
        reason = (
            "Final article contains no Simpro brand, URL, or "
            "connector-sensitive language."
        )
        for path in workflow_paths:
            content = path.read_text(encoding="utf-8")
            with self.subTest(path=path.name):
                self.assertIn("--not-applicable-reason", content)
                self.assertIn(reason, content)
                self.assertIn("omit context request/pack/receipt", content.casefold())

    def test_blog_frontmatter_templates_use_block_schema_notes_without_comma_splitting(self):
        workflow_paths = [
            ROOT / ".claude" / "commands" / "article.md",
            ROOT / ".claude" / "commands" / "write.md",
            ROOT / ".claude" / "commands" / "rewrite.md",
        ]
        canonical_organization = (
            '"Organization as publisher reference only, not a separate full schema block"'
        )
        for path in workflow_paths:
            content = path.read_text(encoding="utf-8")
            with self.subTest(path=path.name):
                self.assertNotRegex(content, r"(?m)^\s*schema_notes:\s*\[")
                self.assertRegex(
                    content,
                    r"(?m)^\s*schema_notes:\s*$\n\s*- BlogPosting\s*$\n"
                    r"\s*- BreadcrumbList\s*$\n"
                    r"\s*- ImageObject for the featured image or logo\s*$",
                )
                self.assertIn(canonical_organization, content)

    def test_public_workflows_regenerate_context_binding_after_final_mutation(self):
        blog_workflow_paths = [
            ROOT / ".claude" / "commands" / "article.md",
            ROOT / ".claude" / "commands" / "write.md",
            ROOT / ".claude" / "commands" / "rewrite.md",
            ROOT / ".claude" / "commands" / "optimize.md",
        ]
        for path in blog_workflow_paths:
            content = path.read_text(encoding="utf-8")
            for marker in (
                "blog_assembly_mutation_recorder.py start",
                "blog_assembly_mutation_recorder.py finish",
                "python data_sources/modules/context_binding_generator.py",
                "--proof-sidecar",
                "--context-request",
                "--context-pack",
                "--context-receipt",
                "--stage-receipt-output",
            ):
                with self.subTest(path=path.name, marker=marker):
                    self.assertIn(marker.casefold(), content.casefold())

            start = content.find("blog_assembly_mutation_recorder.py start")
            finish = content.find("blog_assembly_mutation_recorder.py finish")
            binding = content.find("python data_sources/modules/context_binding_generator.py")
            self.assertLess(start, finish, path.name)
            self.assertLess(finish, binding, path.name)

        non_blog_publish_paths = [
            ROOT / ".claude" / "commands" / "publish-draft.md",
            ROOT / ".claude" / "commands" / "landing-write.md",
            ROOT / ".claude" / "commands" / "landing-publish.md",
        ]
        required = [
            "python data_sources/modules/context_binding_generator.py",
            "--proof-sidecar",
            "--context-request",
            "--context-pack",
            "--context-receipt",
            "after the final content mutation",
        ]

        for path in non_blog_publish_paths:
            content = path.read_text(encoding="utf-8")
            for marker in required:
                with self.subTest(path=path.name, marker=marker):
                    self.assertIn(marker.casefold(), content.casefold())

    def test_landing_write_requires_receipt_approved_proof_or_omission(self):
        landing_write = (ROOT / ".claude" / "commands" / "landing-write.md").read_text(
            encoding="utf-8"
        )

        for unsafe_template in (
            "Join 24,000+ businesses and 450,000+ users",
            "Trusted by 24,000+ businesses and 450,000+ users",
            "[Testimonial with specific results]",
            "[Second testimonial]",
            "[Short testimonial with specific result]",
            "At least 2 testimonials with names",
            "At least 1 testimonial",
        ):
            self.assertNotIn(unsafe_template, landing_write)

        normalized = landing_write.casefold()
        for requirement in (
            "receipt-approved claim",
            "claim_id",
            "public url",
            "omit",
            "do not invent",
        ):
            self.assertIn(requirement, normalized)
    def test_sub_90_aeo_geo_score_triggers_automatic_repair_loop(self):
        required = [
            "AEO/GEO Recovery Loop",
            "below 90/100",
            "aeo_geo.checks",
            "top 3-5 fixes",
            "scorer or parser false negative",
            "2 iterations",
            "/scrub",
            "/publish-readiness",
        ]
        docs = [
            ROOT / "context" / "aeo-geo-blog-strategy.md",
            ROOT / ".claude" / "commands" / "rewrite.md",
            ROOT / ".claude" / "commands" / "optimize.md",
            ROOT / ".claude" / "commands" / "publish-readiness.md",
        ]

        for path in docs:
            content = path.read_text(encoding="utf-8")
            for text in required:
                self.assertIn(text, content, f"{path.name} missing {text}")

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
            "research/paa-questions-[topic-slug]-[YYYY-MM-DD].json",
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
            "If a named author is present",
            "If no named author is available",
            "omit `author`",
            "omit `Person as author`",
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
            "research/paa-questions-[topic-slug]-[YYYY-MM-DD].json",
            "Source Map",
            "E-E-A-T proof",
            "E-E-A-T Proof Map",
            "Experience",
            "Expertise",
            "Do not invent",
            "repo context",
            "connector-unavailable blocker",
            "never becomes public-claim approval authority",
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
            "context_pack_hash",
            "receipt_hash",
            "resource_id",
            "claim_id",
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
            "resource_id",
            "approved claim",
            "receipt_hash",
        ]

        for path in command_paths:
            content = path.read_text(encoding="utf-8")
            for text in required:
                self.assertIn(text, content, f"{path.name} missing {text}")

    def test_docs_require_receipt_backed_metrics_with_public_links(self):
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
            self.assertIn("receipt_hash", content, f"{path.name} missing receipt binding")
            self.assertIn("claim_id", content, f"{path.name} missing approved claim ID")
            self.assertTrue(
                "public-facing source link" in content or "public URL" in content,
                f"{path.name} missing public evidence link requirement",
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

    def test_blog_writing_commands_do_not_impose_per_paragraph_link_quotas(self):
        command_paths = [
            ROOT / ".claude" / "commands" / "article.md",
            ROOT / ".claude" / "commands" / "write.md",
            ROOT / ".claude" / "commands" / "rewrite.md",
        ]
        for path in command_paths:
            content = path.read_text(encoding="utf-8")
            self.assertNotRegex(
                content,
                re.compile(r"only\s+\d+\s+links?\s+per\s+paragraph", re.IGNORECASE),
                f"{path.name} contains a fixed per-paragraph link quota",
            )
            self.assertIn(
                "Place each link where it directly supports the sentence and reader task",
                content,
                f"{path.name} must document intent-based link placement",
            )

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
            "structured AnswerSocrates artifact",
            "dedicated brief section takes precedence",
            "supplemental research and cannot satisfy PAA provenance",
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

        strict_source_docs = [
            ROOT / ".claude" / "commands" / "article.md",
            ROOT / ".claude" / "commands" / "rewrite.md",
            ROOT / "context" / "aeo-geo-blog-strategy.md",
            ROOT / "README.md",
        ]
        for path in strict_source_docs:
            content = path.read_text(encoding="utf-8")
            for marker in (
                "structured AnswerSocrates artifact",
                "dedicated brief section",
                "genuine blocked state",
                "cannot satisfy PAA provenance",
            ):
                self.assertIn(marker, content, f"{path.name} missing {marker}")

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

    def test_publish_readiness_runner_is_documented_as_two_phase_command(self):
        owner = ROOT / ".claude" / "commands" / "publish-readiness.md"
        content = owner.read_text(encoding="utf-8")
        for marker in (
            "python data_sources/modules/publish_readiness.py",
            "--phase preflight",
            "--phase final",
            "--output",
        ):
            self.assertIn(marker, content, f"{owner.name} missing {marker}")

        reference_docs = [
            ROOT / ".claude" / "commands" / "research.md",
            ROOT / ".claude" / "commands" / "optimize.md",
            ROOT / ".claude" / "commands" / "write.md",
            ROOT / "CLAUDE.md",
            ROOT / "AGENTS.md",
            ROOT / ".cursor" / "rules" / "customer-proof.mdc",
        ]
        for path in [
            *reference_docs,
            ROOT / ".claude" / "commands" / "article.md",
            ROOT / ".claude" / "commands" / "rewrite.md",
            ROOT / "README.md",
        ]:
            content = path.read_text(encoding="utf-8")
            self.assertIn("/publish-readiness", content, path.name)

    def test_publish_readiness_two_phase_command_contract_exists(self):
        command_path = ROOT / ".claude" / "commands" / "publish-readiness.md"
        content = command_path.read_text(encoding="utf-8")

        readiness_commands = [
            line.strip()
            for line in content.splitlines()
            if line.strip().startswith("python data_sources/modules/publish_readiness.py")
        ]
        self.assertTrue(
            any("--phase preflight" in line and "--output" in line for line in readiness_commands)
        )
        self.assertTrue(
            any("--phase final" in line and "--output" in line for line in readiness_commands)
        )
        self.assertNotIn(
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

    def test_noncanonical_blog_workflows_do_not_require_manual_individual_gate_scripts(self):
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
        ]

        for path in docs:
            content = path.read_text(encoding="utf-8")
            for line in content.splitlines():
                if "python " not in line:
                    continue
                if "paa_provenance_guard.py record" in line:
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
                if "paa_provenance_guard.py record" in line:
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
                    if "python " in line
                    and module in line
                    and "paa_provenance_guard.py record" not in line
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

    def test_mandatory_customer_proof_selector_commands_include_context_artifacts(self):
        docs = [
            ROOT / "context" / "aeo-geo-blog-strategy.md",
            ROOT / ".claude" / "commands" / "research.md",
            ROOT / ".claude" / "commands" / "write.md",
            ROOT / ".claude" / "commands" / "rewrite.md",
            ROOT / ".claude" / "rules" / "customer-proof.md",
            ROOT / "README.md",
            ROOT / "CLAUDE.md",
            ROOT / "AGENTS.md",
        ]
        required_flags = ("--context-pack", "--context-receipt")

        for path in docs:
            for line_number, line in enumerate(
                path.read_text(encoding="utf-8").splitlines(), start=1
            ):
                if (
                    "python data_sources/modules/customer_proof_selector.py" not in line
                    or "--slate" not in line
                ):
                    continue
                for flag in required_flags:
                    self.assertIn(flag, line, f"{path}:{line_number} missing {flag}")

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

    def test_blog_assembly_bom_output_inventory_is_complete(self):
        publish_readiness = (ROOT / ".claude" / "commands" / "publish-readiness.md").read_text(
            encoding="utf-8"
        )
        required = [
            "--validation-sidecar",
            "--editorial-plan",
            "--serp-evidence",
            "--paa-artifact",
            "--context-request",
            "--context-pack",
            "--context-receipt",
            "--customer-proof-selector-evidence",
            "--fred-authority-evidence",
            "--stage-receipt",
            "--assembly-bom",
        ]
        for text in required:
            self.assertIn(text, publish_readiness)

    def test_publish_readiness_owns_non_circular_two_phase_seal(self):
        owner = ROOT / ".claude" / "commands" / "publish-readiness.md"
        ordered_markers = [
            "blog_assembly_bom.py build",
            "--phase preflight",
            "blog_assembly_bom.py finalize",
            "--phase final",
        ]
        content = owner.read_text(encoding="utf-8")
        positions = [content.find(marker) for marker in ordered_markers]
        self.assertTrue(all(position >= 0 for position in positions))
        self.assertEqual(positions, sorted(positions))
        self.assertIn("verification_scope: source_artifact", content)
        self.assertIn("detached final-readiness attestation", content)
        self.assertIn("not hashed back into the BOM", content)

        readiness_commands = [
            line.strip()
            for line in content.splitlines()
            if "python data_sources/modules/publish_readiness.py" in line
        ]
        self.assertGreaterEqual(len(readiness_commands), 2)
        self.assertTrue(
            any("--phase preflight" in line and "--output" in line for line in readiness_commands)
        )
        self.assertTrue(
            any("--phase final" in line and "--output" in line for line in readiness_commands)
        )

    def test_active_blog_docs_do_not_offer_one_pass_readiness_commands(self):
        docs = [
            ROOT / ".claude" / "commands" / "article.md",
            ROOT / ".claude" / "commands" / "rewrite.md",
            ROOT / ".claude" / "commands" / "write.md",
            ROOT / ".claude" / "commands" / "optimize.md",
            ROOT / ".claude" / "commands" / "publish-readiness.md",
            ROOT / "context" / "aeo-geo-blog-strategy.md",
            ROOT / "README.md",
        ]
        for path in docs:
            content = path.read_text(encoding="utf-8")
            stale = [
                line
                for line in content.splitlines()
                if line.strip().startswith("/publish-readiness ")
            ]
            self.assertEqual([], stale, f"{path.name} contains a stale one-pass command")

    def test_docs_show_genuine_receipt_chain_and_deterministic_preflight_companion(self):
        docs = [
            ROOT / ".claude" / "commands" / "article.md",
            ROOT / ".claude" / "commands" / "rewrite.md",
        ]
        required = (
            "blog_assembly_mutation_recorder.py start",
            "blog_assembly_mutation_recorder.py finish",
            "content_scrubber.py",
            "context_binding_generator.py",
            "--stage-receipt-output",
            "--assembly-date",
            "--workspace-root",
            "--previous-receipt",
        )
        for path in docs:
            content = path.read_text(encoding="utf-8")
            for marker in required:
                self.assertIn(marker, content, f"{path.name} missing {marker}")

        owner = (ROOT / ".claude" / "commands" / "publish-readiness.md").read_text(
            encoding="utf-8"
        )
        self.assertIn(
            "preflight-readiness-[topic-slug]-[YYYY-MM-DD]-stage-receipt.json",
            owner,
        )

    def test_documented_mutation_receipts_bind_artifacts_by_contract_role(self):
        draft_docs = [
            ROOT / ".claude" / "commands" / "article.md",
            ROOT / ".claude" / "commands" / "write.md",
            ROOT / ".claude" / "commands" / "rewrite.md",
            ROOT / "context" / "aeo-geo-blog-strategy.md",
            ROOT / "README.md",
        ]
        all_docs = [*draft_docs, ROOT / ".claude" / "commands" / "optimize.md"]
        labeled_path = re.compile(
            r"^(?:[a-z][a-z0-9_]*|agent_output\.[a-z][a-z0-9-]*)=\S+$"
        )

        for path in all_docs:
            commands = _mutation_recorder_commands(path.read_text(encoding="utf-8"))
            self.assertTrue(commands, f"{path.name} has no executable mutation command")
            for command in commands:
                for option in ("--input", "--evidence"):
                    for value in _command_option_values(command, option):
                        self.assertRegex(
                            value,
                            labeled_path,
                            f"{path.name} documents an unlabeled {option} value: {value}",
                        )

        for path in draft_docs:
            commands = _mutation_recorder_commands(path.read_text(encoding="utf-8"))
            starts = [
                command
                for command in commands
                if command[0] == "start"
                and _command_option_values(command, "--stage") == ["draft"]
            ]
            finishes = [
                command
                for command in commands
                if command[0] == "finish"
                and any("draft-state.json" in value for value in _command_option_values(command, "--state"))
            ]
            self.assertEqual(1, len(starts), f"{path.name} must define one draft start")
            self.assertEqual(1, len(finishes), f"{path.name} must define one draft finish")
            self.assertEqual(
                ["editorial_plan=research/editorial-plan-[topic-slug]-[YYYY-MM-DD].json"],
                _command_option_values(starts[0], "--input"),
                f"{path.name} must bind the editorial plan as the draft input",
            )
            self.assertEqual(
                ["serp_evidence=research/serp-evidence-[topic-slug]-[YYYY-MM-DD].json"],
                _command_option_values(finishes[0], "--evidence"),
                f"{path.name} must bind verified SERP research as draft evidence",
            )

        optimize = (ROOT / ".claude" / "commands" / "optimize.md").read_text(
            encoding="utf-8"
        )
        optimization_finishes = [
            command
            for command in _mutation_recorder_commands(optimize)
            if command[0] == "finish"
            and any(
                "optimization-state.json" in value
                for value in _command_option_values(command, "--state")
            )
        ]
        self.assertEqual(1, len(optimization_finishes))
        self.assertEqual(
            [
                f"agent_output.{agent_id}=research/agent-outputs/"
                f"{agent_id}-[topic-slug]-[YYYY-MM-DD].md"
                for agent_id in (
                    "content-analyzer",
                    "seo-optimizer",
                    "meta-creator",
                    "internal-linker",
                    "keyword-mapper",
                )
            ],
            _command_option_values(optimization_finishes[0], "--evidence"),
        )

    def test_paa_precedence_and_conditional_faq_policy_are_semantic(self):
        docs = [
            ROOT / ".claude" / "commands" / "article.md",
            ROOT / ".claude" / "commands" / "rewrite.md",
            ROOT / ".claude" / "commands" / "write.md",
            ROOT / ".claude" / "commands" / "research-serp.md",
            ROOT / "context" / "aeo-geo-blog-strategy.md",
            ROOT / "README.md",
        ]
        required = [
            "structured AnswerSocrates artifact",
            "dedicated brief section",
            "takes precedence",
            "exact questions as visible FAQ headings",
            "genuine blocked state",
            "login, CAPTCHA, quota, or unavailability",
            "supplemental research",
            "cannot satisfy PAA provenance",
            "FAQ policy: required | not_applicable",
            "non-empty rationale",
        ]
        for path in docs:
            content = path.read_text(encoding="utf-8")
            for marker in required:
                self.assertIn(marker, content, f"{path.name} missing {marker}")

        write = (ROOT / ".claude" / "commands" / "write.md").read_text(encoding="utf-8")
        self.assertIn("For rewrites only", write)
        self.assertNotIn("ask for a PAA/FAQ CSV", write)
        research_serp = (ROOT / ".claude" / "commands" / "research-serp.md").read_text(
            encoding="utf-8"
        )
        self.assertNotIn("Feed the PAA questions", research_serp)

    def test_documented_answersocrates_templates_parse_with_exact_contract(self):
        docs = [
            ROOT / ".claude" / "commands" / "article.md",
            ROOT / "context" / "aeo-geo-blog-strategy.md",
        ]
        for path in docs:
            content = path.read_text(encoding="utf-8")
            collected = _fenced_block_after(
                content,
                "### Collected AnswerSocrates Artifact Template",
            )
            collected_command = shlex.split(collected.strip(), posix=True)
            self.assertEqual(
                [
                    "python",
                    "data_sources/modules/paa_provenance_guard.py",
                    "record",
                ],
                collected_command[:3],
                path.name,
            )
            for option in (
                "--raw-capture",
                "--expected-query",
                "--expected-collection-date",
                "--expected-run-id",
                "--workspace-root",
                "--output",
            ):
                self.assertIn(option, collected_command, f"{path.name} missing {option}")
            self.assertTrue(
                _command_option_values(collected_command, "--output")[0].endswith(".json")
            )
            self.assertIn("simpro-answersocrates-artifact/v1", content)
            self.assertIn("simpro-answersocrates-run-receipt/v1", content)
            self.assertIn("repository-approved Playwright collector", content)
            self.assertIn("Handwritten labels", content)

            blocked = _fenced_block_after(
                content,
                "### Blocked AnswerSocrates Artifact Template",
            )
            blocked_command = shlex.split(blocked.strip(), posix=True)
            self.assertEqual(
                [
                    "python",
                    "data_sources/modules/paa_provenance_guard.py",
                    "record",
                ],
                blocked_command[:3],
                path.name,
            )
            for option in (
                "--raw-capture", "--expected-query", "--expected-collection-date",
                "--expected-run-id", "--workspace-root", "--output",
            ):
                self.assertIn(option, blocked_command, f"{path.name} missing {option}")
            for removed in ("--status", "--blocker", "--blocker-reason"):
                self.assertNotIn(removed, blocked_command, f"{path.name} retains {removed}")

        rewrite_docs = [
            ROOT / ".claude" / "commands" / "rewrite.md",
            ROOT / "context" / "aeo-geo-blog-strategy.md",
            ROOT / "README.md",
        ]
        for path in rewrite_docs:
            self.assertIn(
                "## Pre-picked PAA Questions",
                path.read_text(encoding="utf-8"),
                f"{path.name} omits the exact brief heading consumed by the guard",
            )

    def test_active_blog_guidance_has_no_fixed_research_or_link_counts(self):
        docs = [
            ROOT / "README.md",
            ROOT / "context" / "aeo-geo-blog-strategy.md",
            ROOT / "context" / "seo-guidelines.md",
            ROOT / ".claude" / "commands" / "article.md",
            ROOT / ".claude" / "commands" / "research.md",
            ROOT / ".claude" / "commands" / "write.md",
            ROOT / ".claude" / "commands" / "rewrite.md",
            ROOT / ".claude" / "commands" / "analyze-existing.md",
            ROOT / ".claude" / "commands" / "optimize.md",
            ROOT / ".claude" / "commands" / "research-serp.md",
            ROOT / ".claude" / "agents" / "seo-optimizer.md",
            ROOT / ".claude" / "agents" / "internal-linker.md",
            ROOT / ".claude" / "agents" / "content-analyzer.md",
        ]
        forbidden_patterns = [
            r"top\s+\d+(?:\s*[-\u2013]\s*\d+)?\s+(?:competitor|source|ranking result)",
            r"visit\s+\d+\s+(?:actual\s+)?(?:threads?|videos?)",
            r"\d+\s*[-\u2013]\s*\d+\s+(?:external|internal|authority|related)?\s*links?",
            r"\d+\s*[-\u2013]\s*\d+\s+(?:PAA|FAQ)(?:/FAQ)?\s+questions?",
            r"at\s+least\s+\d+\s+(?:external|internal|authority|source)\s+links?",
            r"\d+\s*[-\u2013]\s*\d+\+?\s+(?:quality\s+)?(?:external|internal|authority)\s+links?",
            r"\d+\s*[-\u2013]\s*\d+\s+(?:closest|selected)\s+(?:PAA|FAQ)(?:/FAQ)?\s+questions?",
            r"at\s+least\s+(?:\d+|one|two|three|four|five)\s+source-backed\s+claims?",
            r"target\s+range:\s*\d+\s*[-\u2013]\s*\d+\s+internal\s+links?",
            r"\d+\s+or\s+more\s+competitors?",
            r"(?:one|\d+(?:\s*[-\u2013]\s*\d+)?)\s+strategic\s+links?\s+maximum",
            r"\d+\s*[-\u2013]\s*\d+\s+related\s+(?:articles?|blog posts?)\s+to\s+link",
        ]
        for path in docs:
            content = path.read_text(encoding="utf-8")
            for pattern in forbidden_patterns:
                self.assertIsNone(
                    re.search(pattern, content, flags=re.IGNORECASE),
                    f"{path.name} contains fixed-count guidance: {pattern}",
                )

        combined = "\n".join(path.read_text(encoding="utf-8") for path in docs)
        self.assertNotRegex(combined, re.compile(r"\bLSI\b", re.IGNORECASE))
        self.assertNotIn("industrying", combined.casefold())
        self.assertNotRegex(
            combined,
            re.compile(r"80\s*[-\u2013]\s*89[^\n]*(?:publishable|ready)", re.IGNORECASE),
        )
        self.assertNotIn("default to competitive length", combined.casefold())

    def test_docs_require_observation_bound_serp_and_source_evidence(self):
        serp_docs = [
            ROOT / ".claude" / "commands" / "article.md",
            ROOT / ".claude" / "commands" / "research-serp.md",
            ROOT / "context" / "aeo-geo-blog-strategy.md",
        ]
        for path in serp_docs:
            content = path.read_text(encoding="utf-8")
            self.assertIn("simpro-serp-evidence/v1", content, path.name)
            self.assertIn("result", content.casefold(), path.name)
            self.assertIn("evidence hash", content.casefold(), path.name)
            self.assertRegex(content, re.compile(r"metadata-only", re.IGNORECASE))

        source_docs = [
            ROOT / ".claude" / "commands" / "article.md",
            ROOT / ".claude" / "commands" / "write.md",
            ROOT / ".claude" / "commands" / "rewrite.md",
            ROOT / "context" / "aeo-geo-blog-strategy.md",
        ]
        for path in source_docs:
            content = path.read_text(encoding="utf-8")
            for marker in (
                "Evidence relation: directly_supports",
                "Classification artifact",
                "Classification hash",
                "simpro-source-classification/v1",
                "Capture receipt",
                "Capture receipt hash",
                "simpro-source-capture-receipt/v1",
            ):
                self.assertIn(marker, content, f"{path.name} missing {marker}")

        contribution_docs = [
            ROOT / ".claude" / "commands" / "article.md",
            ROOT / ".claude" / "commands" / "write.md",
            ROOT / ".claude" / "commands" / "rewrite.md",
            ROOT / "context" / "aeo-geo-blog-strategy.md",
        ]
        for path in contribution_docs:
            content = path.read_text(encoding="utf-8")
            self.assertIn("visible_evidence", content, path.name)

    def test_tool_emitted_artifacts_document_local_execution_attestation_boundary(self):
        workflow_docs = [
            ROOT / "README.md",
            ROOT / "context" / "aeo-geo-blog-strategy.md",
            ROOT / ".claude" / "commands" / "article.md",
            ROOT / ".claude" / "commands" / "write.md",
            ROOT / ".claude" / "commands" / "rewrite.md",
            ROOT / ".claude" / "commands" / "optimize.md",
            ROOT / ".claude" / "commands" / "publish-readiness.md",
        ]
        required_markers = (
            "tool-emitted machine artifacts",
            "`execution_attestation`",
            "keyed local execution-integrity attestation",
            "simpro-blog-stage-receipt/v1",
            "simpro-serp-evidence/v1",
            "simpro-answersocrates-run-receipt/v1",
            "simpro-source-classification/v1",
            "simpro-source-capture-receipt/v1",
            "does not provide a remote/provider signature",
            "external observations are true",
        )
        for path in workflow_docs:
            content = path.read_text(encoding="utf-8")
            for marker in required_markers:
                self.assertIn(
                    marker.casefold(),
                    content.casefold(),
                    f"{path.name} missing {marker}",
                )

        research_serp = (
            ROOT / ".claude" / "commands" / "research-serp.md"
        ).read_text(encoding="utf-8")
        for marker in (
            "`execution_attestation`",
            "keyed local execution-integrity attestation",
            "simpro-serp-evidence/v1",
            "simpro-answersocrates-run-receipt/v1",
            "does not provide a remote/provider signature",
        ):
            self.assertIn(
                marker.casefold(),
                research_serp.casefold(),
                f"research-serp.md missing {marker}",
            )

    def test_attestation_trust_key_operations_are_documented(self):
        for path in (
            ROOT / "README.md",
            ROOT / "context" / "aeo-geo-blog-strategy.md",
        ):
            content = path.read_text(encoding="utf-8")
            for marker in (
                "SEOMACHINE_ARTIFACT_ATTESTATION_KEY",
                ".cache/seomachine-execution-attestation.key",
                "invalidates existing attestations",
            ):
                self.assertIn(marker, content, f"{path.name} missing {marker}")

    def test_post_optimization_docs_define_closed_receipt_sequence(self):
        docs = [
            ROOT / ".claude" / "commands" / "article.md",
            ROOT / ".claude" / "commands" / "rewrite.md",
            ROOT / "context" / "aeo-geo-blog-strategy.md",
        ]
        stages = [
            "optimization",
            "post_optimization_scrub",
            "post_optimization_context_binding",
            "final_preflight_readiness",
        ]
        for path in docs:
            content = path.read_text(encoding="utf-8")
            anchor = content.find("Closed post-optimization receipt sequence")
            self.assertGreaterEqual(anchor, 0, f"{path.name} missing closed sequence")
            section = content[anchor:]
            positions = [section.find(stage) for stage in stages]
            self.assertTrue(all(position >= 0 for position in positions), path.name)
            self.assertEqual(positions, sorted(positions), path.name)
            self.assertIn("/publish-readiness", section, path.name)

    def test_post_optimization_reseal_preserves_the_prior_bom_identity(self):
        owner = (ROOT / ".claude" / "commands" / "publish-readiness.md").read_text(
            encoding="utf-8"
        )
        for marker in (
            "research/blog-assembly-bom-[topic-slug]-[YYYY-MM-DD].json",
            "research/blog-assembly-bom-[topic-slug]-[YYYY-MM-DD]-final.json",
            "research/blog-assembly-bom-[topic-slug]-[YYYY-MM-DD]-post-optimization.json",
            "research/blog-assembly-bom-[topic-slug]-[YYYY-MM-DD]-post-optimization-final.json",
            "Do not overwrite the BOM referenced by the prior preflight",
        ):
            self.assertIn(marker, owner)

        for path in (
            ROOT / "README.md",
            ROOT / "context" / "aeo-geo-blog-strategy.md",
            ROOT / ".claude" / "commands" / "article.md",
            ROOT / ".claude" / "commands" / "write.md",
            ROOT / ".claude" / "commands" / "rewrite.md",
            ROOT / ".claude" / "commands" / "optimize.md",
        ):
            content = path.read_text(encoding="utf-8")
            with self.subTest(path=path.name):
                self.assertIn("immutable", content)
                self.assertIn("/publish-readiness", content)

    def test_editorial_plan_docs_cover_world_class_quality_decisions(self):
        workflow_paths = [
            ROOT / ".claude" / "commands" / "article.md",
            ROOT / ".claude" / "commands" / "write.md",
            ROOT / ".claude" / "commands" / "rewrite.md",
        ]
        article = workflow_paths[0].read_text(encoding="utf-8")
        strategy = (ROOT / "context" / "aeo-geo-blog-strategy.md").read_text(
            encoding="utf-8"
        )
        for marker in (
            "simpro-blog-editorial-plan/v1",
            "complete Reader Contract",
            "verified intent and SERP decisions",
            "at least 1 original contribution",
            "primary and supporting entity coverage",
            "clear | differentiated | blocked",
            "required contextual down-funnel link",
            "FAQ policy: required | not_applicable",
            "PAA source/binding/selected-question decision",
        ):
            self.assertIn(marker, strategy, f"canonical strategy missing {marker}")

        for heading in (
            "## Reader Contract",
            "## SERP Strategy Decision",
            "## Original Contribution Map",
            "## Entity Map",
            "## Query Ownership and Cannibalization Decision",
            "## Internal-Link Plan",
            "## FAQ and PAA Policy",
        ):
            self.assertIn(heading, article)

        self.assertIn("`blocked` prevents readiness", article)
        self.assertIn("no fixed count", article)

        for path in workflow_paths:
            content = path.read_text(encoding="utf-8")
            for marker in (
                "simpro-blog-editorial-plan/v1",
                "serialize_article_plan(plan)",
                "research/editorial-plan-[topic-slug]-[YYYY-MM-DD].json",
                "Original Contribution Map",
                "Entity Map",
                "Query Ownership and Cannibalization Decision",
                "Internal-Link Plan",
                "FAQ and PAA Policy",
            ):
                self.assertIn(marker, content, f"{path.name} missing {marker}")

    def test_blog_workflow_docs_require_strict_identity_and_current_freshness(self):
        docs = [
            ROOT / ".claude" / "commands" / "article.md",
            ROOT / ".claude" / "commands" / "write.md",
            ROOT / ".claude" / "commands" / "rewrite.md",
        ]
        for path in docs:
            content = path.read_text(encoding="utf-8")
            for field in (
                "artifact_type",
                "brand",
                "title",
                "objective",
                "audience",
                "region",
                "last_updated",
                "schema_notes",
            ):
                self.assertRegex(content, rf"(?m)^\s*{field}:", path.name)
            self.assertIn("matching the assembly date", content, path.name)

    def test_blog_schema_author_is_conditional_not_universal(self):
        docs = [
            ROOT / "AGENTS.md",
            ROOT / "CLAUDE.md",
            ROOT / "README.md",
            ROOT / "context" / "aeo-geo-blog-strategy.md",
            ROOT / "context" / "seo-guidelines.md",
            ROOT / ".claude" / "commands" / "article.md",
            ROOT / ".claude" / "commands" / "write.md",
            ROOT / ".claude" / "commands" / "rewrite.md",
            ROOT / ".agents" / "rules" / "blog-schema.md",
            ROOT / ".claude" / "rules" / "blog-schema.md",
            ROOT / ".cursor" / "rules" / "blog-schema.mdc",
        ]
        required = [
            "If a named author is present",
            "If no named author is available",
            "omit `author`",
            "omit `Person as author`",
            "Organization as publisher reference only",
        ]
        forbidden = [
            "Author attribution in frontmatter",
            "Named author in frontmatter",
            "Author attribution: Named author",
            'Author attribution (named, not generic "Team")',
        ]
        for path in docs:
            content = path.read_text(encoding="utf-8")
            for text in required:
                self.assertIn(text, content, f"{path.name} missing {text}")
            for text in forbidden:
                self.assertNotIn(
                    text,
                    content,
                    f"{path.name} still makes author universal",
                )

        active_workflows = [
            ROOT / ".claude" / "commands" / "article.md",
            ROOT / ".claude" / "commands" / "write.md",
            ROOT / ".claude" / "commands" / "rewrite.md",
            ROOT / ".claude" / "commands" / "publish-readiness.md",
            ROOT / "context" / "aeo-geo-blog-strategy.md",
            ROOT / "context" / "seo-guidelines.md",
        ]
        no_author_voice_rule = (
            "When `author_policy.status` is `not_provided`, first-person singular "
            "author judgment outside quotes is prohibited."
        )
        for path in active_workflows:
            self.assertIn(
                no_author_voice_rule,
                path.read_text(encoding="utf-8"),
                f"{path.name} omits the no-author voice boundary",
            )

    def test_schema_conditionals_use_exact_visible_content_contracts(self):
        docs = [
            ROOT / ".claude" / "commands" / "article.md",
            ROOT / ".claude" / "commands" / "write.md",
            ROOT / ".claude" / "commands" / "rewrite.md",
            ROOT / ".claude" / "commands" / "publish-readiness.md",
            ROOT / "context" / "aeo-geo-blog-strategy.md",
            ROOT / "context" / "seo-guidelines.md",
        ]
        required = (
            "`FAQPage` and `Question and Answer inside FAQPage` are required only "
            "when visible FAQs exist.",
            "Require `VideoObject` if and only if a verified video embed exists.",
            "`Person as author` is required only when a named author exists.",
        )
        for path in docs:
            content = path.read_text(encoding="utf-8")
            for marker in required:
                self.assertIn(marker, content, f"{path.name} missing {marker}")

    def test_general_source_support_docs_use_exact_source_classes(self):
        docs = [
            ROOT / ".claude" / "commands" / "article.md",
            ROOT / ".claude" / "commands" / "write.md",
            ROOT / ".claude" / "commands" / "rewrite.md",
            ROOT / ".claude" / "commands" / "publish-readiness.md",
            ROOT / "context" / "aeo-geo-blog-strategy.md",
        ]
        source_classes = (
            "primary_authority",
            "independent_research",
            "non_competing_expert",
            "owned_product",
            "customer_proof",
            "review_platform",
            "competitor",
        )
        for path in docs:
            content = path.read_text(encoding="utf-8")
            self.assertIn("General Source Support Classes", content, path.name)
            for source_class in source_classes:
                self.assertIn(
                    f"`{source_class}`",
                    content,
                    f"{path.name} missing {source_class}",
                )

    def test_readme_has_no_malformed_workflow_copy(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertNotIn(" ? ", readme)
        self.assertNotIn("¦", readme)

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

        for path in docs[:2]:
            content = path.read_text(encoding="utf-8")
            for argument in ("--context-request", "--context-pack", "--context-receipt"):
                self.assertIn(argument, content, f"{path.name} missing {argument}")

        landing_publish = (ROOT / ".claude" / "commands" / "landing-publish.md").read_text(
            encoding="utf-8"
        )
        self.assertNotIn("Content score Ã¢â€°Â¥70", landing_publish)
        self.assertIn("Full publish-readiness stack", landing_publish)
        self.assertIn("publisher.publish_draft(", landing_publish)
        self.assertNotIn("publisher.create_page(", landing_publish)
        for argument in ("context_request", "context_pack", "context_receipt"):
            self.assertIn(argument, landing_publish)

        claude = (ROOT / "CLAUDE.md").read_text(encoding="utf-8")
        self.assertNotIn("C:\\Users\\patrick.grueschow\\Desktop\\Repos\\seomachine-main", claude)

        article = (ROOT / ".claude" / "commands" / "article.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("### 12. Run Optimization Agents", article)

    def test_blog_workflows_rerun_binding_and_readiness_after_optimization_mutations(self):
        workflow_paths = [
            ROOT / ".claude" / "commands" / "article.md",
            ROOT / ".claude" / "commands" / "write.md",
            ROOT / ".claude" / "commands" / "rewrite.md",
            ROOT / ".claude" / "commands" / "optimize.md",
        ]
        for path in workflow_paths:
            content = path.read_text(encoding="utf-8").casefold()
            marker = "after optimization mutations"
            self.assertIn(marker, content, f"{path.name} missing post-optimization section")
            post = content[content.index(marker):]
            stages = (
                "optimization",
                "post_optimization_scrub",
                "post_optimization_context_binding",
                "final_preflight_readiness",
            )
            positions = [post.find(stage) for stage in stages]
            self.assertTrue(all(position >= 0 for position in positions), path.name)
            self.assertEqual(positions, sorted(positions), path.name)

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
        self.assertIn("Require `VideoObject` if and only if a verified video embed exists.", article)

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
        self.assertNotIn("Em dashes (Ã¢â‚¬â€) not hyphens with spaces", style)
        self.assertIn("grammar and sentence meaning", style)
        self.assertNotIn("number, named scenario", linter)
        self.assertIn("approved proof", linter)
        self.assertNotIn(
            "At least one named customer, named number, or named trade per major section",
            brand_voice,
        )
        self.assertNotIn(
            "Round numbers, named customers, specific outcomes Ã¢â‚¬â€ always",
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
            "Simpro vault connector as the active context source",
            "The only configured content location is the vault root",
            "Required connector workflow",
            "search in the task's natural language",
            "read and expand results by `resource_id`",
            "repo-local context files are downstream mirrors or operational state only",
            "cannot override the vault connector when the vault is available",
            "Do not use Google Workspace or old marketing-portal URLs as the active read path",
            "generated vault context binding",
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
            "connector-discovered competitive-context resources",
            "approved claim IDs where public proof is used",
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
            "cannot be published as proof, rankings, metrics, or claims unless separately approved and source-verified through the claim registry",
            "Keep raw deal counts out of public copy",
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
            "connector-discovered product and feature resources",
            "`resource_id` values",
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
            "connector evidence",
            "context_pack_hash",
            "receipt_hash",
            "feature-specific `resource_id` evidence",
            "solution or vertical `resource_id` evidence",
            "repo-local `context/brand-voice.md` and `context/style-guide.md` are fallback mirrors",
            "Status: aligned",
            "/publish-readiness",
        ]

        for path in docs:
            content = path.read_text(encoding="utf-8")
            for text in required:
                self.assertIn(text, content, f"{path.name} missing {text}")

    def test_source_routing_policy_uses_context_binding_and_claim_gates(self):
        source_routing_map = (ROOT / "context" / "source-routing-map.md").read_text(
            encoding="utf-8"
        )
        canonical = (ROOT / "context" / "aeo-geo-blog-strategy.md").read_text(
            encoding="utf-8"
        )
        publish_readiness = (ROOT / ".claude" / "commands" / "publish-readiness.md").read_text(
            encoding="utf-8"
        )

        for text in [
            "Routing Matrix",
            "Context Binding",
            "claim-specific gates",
            "Brand voice, audience, ICP, message pillars, tone",
            "SEO mechanics, AEO/GEO workflow, schema notes, publish gates",
            "Customer proof, quotes, metrics, review stories, approval status",
        ]:
            self.assertIn(text, source_routing_map, f"source-routing-map.md missing {text}")

        self.assertIn("generated vault context binding", canonical)
        self.assertIn("claim-specific gates", canonical)
        self.assertIn("Strict artifact identity is the first", publish_readiness)
        self.assertIn("Context Binding follows", publish_readiness)
        self.assertIn("claim-specific gates", publish_readiness)

        for content, name in [
            (source_routing_map, "source-routing-map.md"),
            (canonical, "aeo-geo-blog-strategy.md"),
            (publish_readiness, "publish-readiness.md"),
        ]:
            self.assertNotIn("Source Routing Decision", content, name)
            self.assertNotIn("Vault Context Read Path", content, name)
            self.assertNotIn("source_routing_guard.py", content, name)

    def test_simpro_publish_readiness_examples_include_context_binding_inputs(self):
        paths = [
            *sorted((ROOT / ".claude" / "commands").glob("*.md")),
            ROOT / ".claude" / "agents" / "editor.md",
            ROOT / ".claude" / "skills" / "grav-publish" / "SKILL.md",
        ]
        required_flags = ("--context-request", "--context-pack", "--context-receipt")

        for path in paths:
            for line_number, line in enumerate(
                path.read_text(encoding="utf-8").splitlines(), start=1
            ):
                if "/publish-readiness" not in line or "--proof-sidecar" not in line:
                    continue
                for flag in required_flags:
                    self.assertIn(flag, line, f"{path}:{line_number} missing {flag}")

    def test_editor_and_lightning_skill_use_connector_resources(self):
        editor = (ROOT / ".claude" / "agents" / "editor.md").read_text(
            encoding="utf-8"
        )
        competitor_skill = (
            ROOT / ".claude" / "skills" / "competitor-alternatives" / "SKILL.md"
        ).read_text(encoding="utf-8")

        for text in ("semantic search", "resource_id", "fallback mirror"):
            self.assertIn(text, editor)
        for text in ("semantic search", "resource_id", "approved claims"):
            self.assertIn(text, competitor_skill)

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
        selector_command_prefix = (
            'python data_sources/modules/fred_authority_selector.py "[topic]" '
            '--title "[title]" --objective "[objective]"'
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
            selector_command_prefix,
            '--output "research/fred-authority-selection-[topic-slug].md"',
            "Fred Voccola Authority Selection",
            "Evaluation is mandatory",
            "public use is optional",
            "validation sidecar",
        ]
        for path in workflow_paths:
            content = path.read_text(encoding="utf-8")
            for text in workflow_required:
                self.assertIn(text, content, f"{path.name} missing {text}")

        receipt_bound_workflows = [
            ROOT / ".claude" / "commands" / "article.md",
            ROOT / ".claude" / "commands" / "analyze-existing.md",
            ROOT / ".claude" / "commands" / "optimize.md",
        ]
        receipt_flags = (
            '--context-pack "research/context-pack-[topic-slug].json"',
            '--context-receipt "research/context-receipt-[topic-slug].json"',
        )
        for path in receipt_bound_workflows:
            content = path.read_text(encoding="utf-8")
            command_line = next(
                line for line in content.splitlines() if "fred_authority_selector.py" in line
            )
            for flag in receipt_flags:
                self.assertIn(flag, command_line, f"{path.name} Fred command missing {flag}")

        canonical_paths = [
            ROOT / "AGENTS.md",
            ROOT / "CLAUDE.md",
            ROOT / "README.md",
            ROOT / "context" / "aeo-geo-blog-strategy.md",
        ]
        canonical_required = [
            "vault connector and claim registry are the sole eligibility source",
            "current connector revisions",
            "resource hashes",
            "claim decisions",
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
            self.assertIn(
                selector_command_prefix,
                content,
                f"{path.name} missing selector command",
            )
            for flag in receipt_flags:
                self.assertIn(flag, content, f"{path.name} missing {flag}")
            for text in canonical_required:
                self.assertIn(text, content, f"{path.name} missing {text}")

    def test_article_analysis_and_optimization_use_connector_authority(self):
        paths = [
            ROOT / ".claude" / "commands" / "article.md",
            ROOT / ".claude" / "commands" / "analyze-existing.md",
            ROOT / ".claude" / "commands" / "optimize.md",
        ]
        prohibited = (
            "wiki/",
            r"C:\Users\patrick.grueschow\Desktop\Obsidian",
            "fred-voccola-media-inventory.csv",
            "authority-signal-matrix.csv",
            "| `expertise` | Use @context/features.md",
            "metric/proof point from @context/features.md",
            "@context/features.md - your brand product information",
        )

        for path in paths:
            content = path.read_text(encoding="utf-8")
            self.assertIn("semantic search", content, path.name)
            self.assertIn("`resource_id`", content, path.name)
            self.assertIn("vault-unavailable blocker", content, path.name)
            for text in prohibited:
                self.assertNotIn(text, content, f"{path.name} contains legacy authority: {text}")

        article = paths[0].read_text(encoding="utf-8")
        customer_proof_line = next(
            line for line in article.splitlines() if "customer_proof_selector.py" in line
        )
        for flag in ("--context-pack", "--context-receipt"):
            self.assertIn(flag, customer_proof_line)

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
            "retrieve current voice and tone guidance through the vault connector",
            "`resource_id` reads",
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

    def test_blog_optimization_agents_do_not_default_to_legacy_brand(self):
        for relative_path in (
            ".claude/agents/seo-optimizer.md",
            ".claude/agents/meta-creator.md",
        ):
            content = (ROOT / relative_path).read_text(encoding="utf-8")
            self.assertIn("Reader Contract", content, relative_path)
            self.assertIn("active vault context", content, relative_path)
            legacy_defaults = [
                "| Castos",
                "castos.com",
                "podcast creator needs",
                "Podcast-Focused",
                "Podcast Industry Relevance",
            ]
            for phrase in legacy_defaults:
                self.assertNotIn(phrase, content, relative_path)

    def test_research_workflows_do_not_prescribe_fixed_competitor_counts(self):
        for path in (ROOT / ".claude" / "commands").glob("*research*.md"):
            content = path.read_text(encoding="utf-8")
            self.assertNotRegex(
                content,
                r"(?i)(?:top|analy[sz]e)\s+\d+(?:\s*-\s*\d+)?\s+competitors",
                path.name,
            )
        landing_research = (
            ROOT / ".claude" / "commands" / "landing-research.md"
        ).read_text(encoding="utf-8")
        self.assertIn("there is no fixed competitor count", landing_research)
        self.assertIn("There is no fixed total", landing_research)
        self.assertIn("FAQ Decision", landing_research)

    def test_research_provenance_docs_remove_caller_authored_paa_and_bind_run_and_decision(self):
        article = (ROOT / ".claude" / "commands" / "article.md").read_text(encoding="utf-8")
        strategy = (ROOT / "context" / "aeo-geo-blog-strategy.md").read_text(encoding="utf-8")
        serp = (ROOT / ".claude" / "commands" / "research-serp.md").read_text(encoding="utf-8")
        for content in (article, strategy):
            for removed in (
                "--eligible-question", "--ineligible-fragment", "--blocker-reason",
                "--status blocked", "--blocker \"",
            ):
                self.assertNotIn(removed, content)
            for required in (
                "--raw-capture", "--expected-query", "--expected-collection-date",
                "--expected-run-id", "--workspace-root",
            ):
                self.assertIn(required, content)
            self.assertIn("approved repository decision path", content)
            self.assertIn("callers cannot override `source_class` or `publisher_relationship`", content)
        commands = [
            shlex.split(line.strip(), posix=True)
            for line in serp.splitlines()
            if line.strip().startswith("python scripts/research_serp_analysis.py ")
        ]
        self.assertTrue(commands)
        for command in commands:
            self.assertIn("--run-id", command)

if __name__ == "__main__":
    unittest.main()
