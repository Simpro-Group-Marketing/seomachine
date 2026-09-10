from tests.fixture_text import fixture_text

import os
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from data_sources.modules import seo_quality_rater as seo_quality_rater_module
from data_sources.modules.keyword_analyzer import KeywordAnalyzer
from data_sources.modules.seo_quality_rater import SEOQualityRater
from data_sources.modules.url_validator import UrlValidationResult, UrlValidationSummary


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def long_article(primary_keyword="payments for trades businesses"):
    sections = []
    for index in range(1, 7):
        sections.append(
            f"## Section {index} for {primary_keyword}\n\n"
            + (
                "This workflow helps field service teams connect jobs, invoices, "
                "customer records, and payment status. "
            )
            * 70
        )

    return (
        f"# {primary_keyword.title()}\n\n"
        f"{primary_keyword} gives customers a clear invoice and a secure payment path.\n\n"
        + "\n\n".join(sections)
        + "\n\n[field service payments](https://www.simprogroup.com/features/payments)\n"
        + "[accounts receivable follow-up with Fast Cash](https://www.simprogroup.com/features/fast-cash)\n"
        + "[field service management software](https://www.simprogroup.com/)\n"
        + "[TEAMWired](https://www.simprogroup.com/case-studies/teamwired)\n"
        + "[Federal Reserve](https://www.frbservices.org/news)\n"
        + "[J.D. Power](https://www.jdpower.com/business)\n"
    )


def article_with_links(links, primary_keyword="payments for trades businesses"):
    return (
        f"# {primary_keyword.title()}\n\n"
        f"{primary_keyword} gives customers a clear invoice and secure payment path.\n\n"
        + "\n\n".join(
            f"## Section {index} for {primary_keyword}\n\n"
            + (
                "This workflow helps field service teams connect jobs, invoices, "
                "customer records, and payment status. "
            )
            * 70
            for index in range(1, 7)
        )
        + "\n\n"
        + links
        + "\n\n[Federal Reserve](https://www.frbservices.org/news)\n"
        + "[J.D. Power](https://www.jdpower.com/business)\n"
    )


def concise_article_with_links(primary_keyword="payments for trades businesses"):
    return (
        f"# {primary_keyword.title()}\n\n"
        f"{primary_keyword} gives office teams a secure way to connect invoices, "
        "job records, and customer payment status without adding another manual "
        "spreadsheet step.\n\n"
        + "\n\n".join(
            f"## Section {index} for {primary_keyword}\n\n"
            + (
                "Office teams need invoice status, customer context, and field updates "
                "in the same workflow. Clear terminology helps readers understand the "
                "payment path without forcing repeated exact-match phrases. "
            )
            * 4
            for index in range(1, 7)
        )
        + "\n\n"
        + "[field service payments](https://www.simprogroup.com/features/payments)\n"
        + "[accounts receivable follow-up with Fast Cash](https://www.simprogroup.com/features/fast-cash)\n"
        + "[field service management software](https://www.simprogroup.com/)\n"
        + "[Federal Reserve](https://www.frbservices.org/news)\n"
        + "[J.D. Power](https://www.jdpower.com/business)\n"
    )


def rate_article_with_links(links, *, brand="Simpro", guidelines=None):
    return SEOQualityRater(guidelines).rate(
        article_with_links(links),
        meta_title=f"Payments for Trades Businesses Guide and Tips | {brand}",
        meta_description=(
            "Payments for trades businesses need online, mobile and field options. "
            "Learn how to reduce friction and protect cash flow today."
        ),
        primary_keyword="payments for trades businesses",
        brand=brand,
    )


class OptimizerModuleTests(unittest.TestCase):
    def test_seo_cli_help_describes_external_authority_source_policy(self):
        output = StringIO()
        with self.assertRaises(SystemExit) as raised, redirect_stdout(output):
            seo_quality_rater_module.main(["--help"])

        self.assertEqual(raised.exception.code, 0)
        help_text = " ".join(output.getvalue().split())
        self.assertIn("2+ distinct non-owned authority sources", help_text)
        self.assertIn("quota-only third", help_text)
        self.assertIn("no maximum", help_text)
        self.assertNotIn("External research requirement: not applicable", help_text)

    def test_seo_quality_rater_reports_release_floor_and_advisory_target(self):
        result = SEOQualityRater().rate(
            long_article(),
            meta_title="Payments for Trades Businesses Guide and Tips | Simpro",
            meta_description=(
                "Payments for trades businesses need online, mobile and field options. "
                "Learn how to reduce friction and protect cash flow today."
            ),
            primary_keyword="payments for trades businesses",
            brand="Simpro",
        )

        self.assertEqual(result["threshold"], seo_quality_rater_module.PUBLISHING_THRESHOLD)
        self.assertEqual(result["target"], 95)
        self.assertEqual(result["target"], seo_quality_rater_module.SEO_TARGET_SCORE)
        self.assertEqual(result["passed"], result["publishing_ready"])
        self.assertEqual(
            result["target_met"],
            result["overall_score"] >= seo_quality_rater_module.SEO_TARGET_SCORE,
        )
        self.assertIn(result["target_status"], {"met", "below_target", "failed_floor"})

    def test_seo_quality_rater_cli_scores_supplied_file(self):
        article = long_article()

        with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".md", delete=False) as temp_file:
            temp_file.write(article)
            temp_path = temp_file.name

        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"

        try:
            completed = subprocess.run(
                [
                    sys.executable,
                    "data_sources/modules/seo_quality_rater.py",
                    temp_path,
                    "--primary-keyword",
                    "payments for trades businesses",
                    "--meta-title",
                    "Payments for Trades Businesses Guide and Tips | Simpro",
                    "--meta-description",
                    "Payments for trades businesses need online, mobile and field options. Learn how to reduce friction and protect cash flow today.",
                ],
                cwd=PROJECT_ROOT,
                env=env,
                text=True,
                encoding="utf-8",
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
        finally:
            os.unlink(temp_path)

        self.assertEqual(completed.returncode, 0, completed.stderr + completed.stdout)
        self.assertIn("Publishing Ready: True", completed.stdout)
        self.assertNotIn("How to Start a Podcast", completed.stdout)
        self.assertNotIn("Content is too short (96 words)", completed.stdout)

    def test_seo_quality_rater_default_does_not_require_long_form_word_count(self):
        result = SEOQualityRater().rate(
            concise_article_with_links(),
            meta_title="Payments for Trades Businesses Guide and Tips | Simpro",
            meta_description=(
                "Payments for trades businesses need online, mobile and field options. "
                "Learn how to reduce friction and protect cash flow today."
            ),
            primary_keyword="payments for trades businesses",
        )

        combined_findings = "\n".join(
            result["critical_issues"] + result["warnings"] + result["suggestions"]
        )
        self.assertLess(result["details"]["word_count"], 2000)
        self.assertNotIn("Content is too short", combined_findings)
        self.assertTrue(result["publishing_ready"], combined_findings)

    def test_seo_quality_rater_default_does_not_require_a_fixed_h2_count(self):
        result = SEOQualityRater()._score_structure(
            {"has_h1": True, "h1_count": 1, "h2_count": 2}
        )

        findings = "\n".join(result["warnings"] + result["suggestions"])
        self.assertEqual(result["score"], 100)
        self.assertNotIn("H2 sections", findings)

    def test_seo_quality_rater_default_uses_craig_style_link_totals(self):
        content = (
            "# Payments for Trades Businesses\n\n"
            "Payments for trades businesses connect invoice and job status.\n\n"
            "## Choose the next action\n\n"
            "Use [field service management software]"
            "(https://www.simprogroup.com/) to connect the handoff."
        )

        result = SEOQualityRater()._score_links(
            content,
            internal_count=1,
            external_count=0,
        )

        findings = "\n".join(result["warnings"] + result["suggestions"])
        self.assertLess(result["score"], 100)
        self.assertIn("Too few internal links", findings)
        self.assertIn("Too few non-owned public research links", findings)

    def test_seo_quality_rater_default_accepts_three_internal_links_with_down_funnel_link(self):
        content = (
            "# Payments for Trades Businesses\n\n"
            "Payments for trades businesses connect invoice and job status.\n\n"
            "## Choose the next action\n\n"
            "Use [field service management software]"
            "(https://www.simprogroup.com/) to connect the handoff.\n"
            "[field service management software]"
            "(https://www.simprogroup.com/) supports follow-up.\n"
            "[payments collection guide]"
            "(https://www.simprogroup.com/blog/payments-as-a-strategic-growth-lever-for-trades) "
            "adds planning detail.\n"
            "[Federal Reserve](https://www.frbservices.org/news) provides payment-system context.\n"
            "[J.D. Power](https://www.jdpower.com/business) provides customer-experience context."
        )

        result = SEOQualityRater()._score_links(
            content,
            internal_count=3,
            external_count=2,
        )

        findings = "\n".join(result["warnings"] + result["suggestions"])
        self.assertGreaterEqual(result["score"], 90)
        self.assertNotIn("Too few internal links", findings)
        self.assertNotIn("Too few non-owned public research links", findings)
        self.assertIn("Could add more internal links", findings)
        self.assertNotIn("Could add more non-owned public research links", findings)

    def test_seo_quality_rater_counts_distinct_external_destinations(self):
        content = (
            "# Payments for Trades Businesses\n\n"
            "Use [Federal Reserve guidance](https://www.frbservices.org/news?utm_source=email).\n"
            "Review the [same Federal Reserve guidance](https://www.frbservices.org/news#updates).\n"
            "Compare [J.D. Power research](https://www.jdpower.com/business).\n"
            "Use [field service payments](https://www.simprogroup.com/features/payments).\n"
            "Read [Fast Cash workflows](https://www.simprogroup.com/features/fast-cash).\n"
            "See the [payments collection guide](https://www.simprogroup.com/blog/payments-guide).\n"
        )

        result = SEOQualityRater()._score_links(
            content,
            internal_count=None,
            external_count=None,
        )

        findings = "\n".join(result["warnings"] + result["suggestions"])
        self.assertNotIn("Too few non-owned public research links", findings)
        self.assertNotIn("Could add more non-owned public research links", findings)

    def test_fragment_mail_and_phone_links_do_not_count_as_internal(self):
        internal, external = seo_quality_rater_module._count_markdown_links(
            "[FAQ](#faq) [Email](mailto:test@example.com) [Call](tel:+15551234567) "
            "[guide](https://www.simprogroup.com/blog/guide) "
            "[authority](https://example.org/rules)",
            brand="Simpro",
        )

        self.assertEqual((internal, external), (1, 1))

    def test_seo_quality_rater_default_ideal_links_score_cleanly(self):
        content = (
            "# Payments for Trades Businesses\n\n"
            "Payments for trades businesses connect invoice and job status.\n\n"
            "## Choose the next action\n\n"
            "Use [field service payments]"
            "(https://www.simprogroup.com/features/payments) to connect the handoff.\n"
            "[accounts receivable follow-up with Fast Cash]"
            "(https://www.simprogroup.com/features/fast-cash) supports follow-up.\n"
            "[field service management software]"
            "(https://www.simprogroup.com/) "
            "supports workflow planning.\n"
            "[payments collection guide]"
            "(https://www.simprogroup.com/blog/payments-as-a-strategic-growth-lever-for-trades) "
            "adds planning detail.\n"
            "[TEAMWired](https://www.simprogroup.com/case-studies/teamwired) adds a related story.\n"
            "[Federal Reserve](https://www.frbservices.org/news) provides payment-system context.\n"
            "[J.D. Power](https://www.jdpower.com/business) provides customer-experience context.\n"
            "[U.S. Bank](https://www.usbank.com/business-banking.html) provides banking context."
        )

        result = SEOQualityRater()._score_links(
            content,
            internal_count=5,
            external_count=3,
        )

        self.assertEqual(result["score"], 100)
        self.assertEqual(result["warnings"], [])
        self.assertEqual(result["suggestions"], [])

    def test_evidence_required_external_links_have_no_maximum_penalty(self):
        result = SEOQualityRater()._score_links(
            "[field service management software](https://www.simprogroup.com/)",
            internal_count=5,
            external_count=12,
        )

        findings = "\n".join(
            result["critical"] + result["warnings"] + result["suggestions"]
        )
        self.assertEqual(result["score"], 100)
        self.assertNotIn("external", findings.casefold())

    def test_seo_quality_rater_warns_when_standard_blog_has_too_many_internal_links(self):
        content = (
            "# Payments for Trades Businesses\n\n"
            "Payments for trades businesses connect invoice and job status.\n\n"
            "## Choose the next action\n\n"
            "Use [field service management software]"
            "(https://www.simprogroup.com/) to connect the handoff."
        )

        result = SEOQualityRater()._score_links(
            content,
            internal_count=8,
            external_count=3,
        )

        findings = "\n".join(result["warnings"] + result["suggestions"])
        self.assertLess(result["score"], 100)
        self.assertIn("Too many internal links", findings)

    def test_seo_quality_rater_allows_more_internal_links_for_long_form_articles(self):
        long_body = " ".join(f"word{i}" for i in range(3000))
        content = (
            "# Payments for Trades Businesses\n\n"
            f"{long_body}\n\n"
            "Use [field service management software]"
            "(https://www.simprogroup.com/) to connect the handoff."
        )

        result = SEOQualityRater()._score_links(
            content,
            internal_count=8,
            external_count=3,
        )

        findings = "\n".join(result["warnings"] + result["suggestions"])
        self.assertEqual(result["score"], 100)
        self.assertNotIn("Too many internal links", findings)

    def test_seo_quality_rater_preserves_explicit_custom_link_totals(self):
        result = SEOQualityRater(
            {
                "min_internal_links": 2,
                "optimal_internal_links": 3,
                "min_external_links": 1,
                "optimal_external_links": 2,
            }
        )._score_links(
            "[field service payment workflows](https://www.simprogroup.com/features/payments)",
            internal_count=1,
            external_count=0,
        )

        findings = "\n".join(result["warnings"] + result["suggestions"])
        self.assertIn("Too few internal links", findings)
        self.assertIn("research links", findings)

    def test_seo_quality_rater_preserves_explicit_custom_h2_rules(self):
        result = SEOQualityRater(
            {"min_h2_sections": 4, "optimal_h2_sections": 6}
        )._score_structure({"has_h1": True, "h1_count": 1, "h2_count": 2})

        self.assertIn("Too few H2 sections", "\n".join(result["warnings"]))

    def test_seo_quality_rater_default_requires_natural_h2_placement_not_a_ratio(self):
        content = (
            "# Payments for Trades Businesses\n\n"
            "Payments for trades businesses give office teams a clear payment path.\n\n"
            "## Payments for trades businesses workflow\n\n"
            "Connect the invoice, job record, and customer status.\n\n"
            "## Reconcile exceptions\n\n"
            "Resolve failed payments and update the job record.\n\n"
            "## Review field handoffs\n\n"
            "Confirm technicians can see the current payment state.\n\n"
            "## Close the loop\n\n"
            "Record the final status and next operational action."
        )
        result = SEOQualityRater().rate(
            content,
            primary_keyword="payments for trades businesses",
            internal_link_count=3,
            external_link_count=2,
        )

        findings = "\n".join(result["warnings"] + result["suggestions"])
        self.assertNotIn("2-3 H2s", findings)
        self.assertNotIn("H2 headings. Target", findings)

    def test_seo_quality_rater_accepts_distinct_aeo_title_topic(self):
        content = """---
brand: Simpro
primary_aeo_topic: ai field service economics
---
# AI Field Service Economics: What to Measure Before You Automate

AI field service management starts with a measurable constraint and a bounded pilot.

## Build the scorecard

Use operating data to compare the same workflow before and after the pilot.
"""

        result = SEOQualityRater().rate(
            content,
            meta_title="AI Field Service Economics: Practical Scorecard | Simpro",
            meta_description=(
                "Use an AI field service economics scorecard to test capacity, "
                "cost, quality, and controls before expanding a field service pilot."
            ),
            primary_keyword="ai field service management",
            secondary_keywords=[],
            internal_link_count=0,
            external_link_count=0,
        )

        self.assertTrue(result["details"]["keyword_in_h1"])
        self.assertTrue(result["details"]["keyword_in_first_100"])
        self.assertEqual(result["details"]["h1_keyword"], "ai field service economics")
        self.assertFalse(
            any("missing from H1" in issue for issue in result["critical_issues"])
        )

    def test_seo_quality_rater_rejects_invalid_explicit_h2_rules(self):
        for guidelines in [
            {"min_h2_sections": 0},
            {"optimal_h2_sections": True},
            {"min_h2_sections": 5, "optimal_h2_sections": 4},
        ]:
            with self.subTest(guidelines=guidelines):
                with self.assertRaisesRegex(ValueError, "h2"):
                    SEOQualityRater(guidelines)

    def test_seo_quality_rater_default_density_mode_ignores_low_density(self):
        result = SEOQualityRater().rate(
            concise_article_with_links(),
            meta_title="Payments for Trades Businesses Guide and Tips | Simpro",
            meta_description=(
                "Payments for trades businesses need online, mobile and field options. "
                "Learn how to reduce friction and protect cash flow today."
            ),
            primary_keyword="payments for trades businesses",
            keyword_density=0.1,
        )

        findings = "\n".join(result["critical_issues"] + result["warnings"])
        self.assertNotIn("density is too low", findings)

    def test_seo_quality_rater_uses_only_visible_body_for_analysis(self):
        body = concise_article_with_links()
        frontmatter = fixture_text("content_evidence:test_optimizer_modules-261-1")
        common = {
            "meta_title": "Payments for Trades Businesses Guide and Tips | Simpro",
            "meta_description": (
                "Payments for trades businesses need online, mobile and field options. "
                "Learn how to reduce friction and protect cash flow today."
            ),
            "primary_keyword": "payments for trades businesses",
        }

        without_frontmatter = SEOQualityRater().rate(body, **common)
        with_frontmatter = SEOQualityRater().rate(frontmatter + body, **common)

        self.assertEqual(with_frontmatter, without_frontmatter)

    def test_seo_quality_rater_ignores_json_ld_for_reader_visible_analysis(self):
        keyword = "payments for trades businesses"
        body = concise_article_with_links(keyword)
        json_ld = f"""
<script type="application/ld+json">
{{
  "@context": "https://schema.org",
  "@type": "Article",
  "headline": "{keyword.title()}",
  "description": "{keyword} connects payment records.",
  "about": "{keyword}"
}}
</script>
"""
        common = {
            "meta_title": "Payments for Trades Businesses Guide and Tips | Simpro",
            "meta_description": (
                "Payments for trades businesses need online, mobile and field options. "
                "Learn how to reduce friction and protect cash flow today."
            ),
            "primary_keyword": keyword,
        }

        without_json_ld = SEOQualityRater().rate(body, **common)
        with_json_ld = SEOQualityRater().rate(body + json_ld, **common)

        self.assertEqual(with_json_ld, without_json_ld)
        findings = "\n".join(with_json_ld["critical_issues"]).lower()
        self.assertNotIn("stuffing", findings)

    def test_reported_keyword_density_never_creates_an_arbitrary_score_penalty(self):
        common = {
            "content": concise_article_with_links(),
            "meta_title": "Payments for Trades Businesses Guide and Tips | Simpro",
            "meta_description": (
                "Payments for trades businesses need online, mobile and field options. "
                "Learn how to reduce friction and protect cash flow today."
            ),
            "primary_keyword": "payments for trades businesses",
        }

        natural = SEOQualityRater().rate(keyword_density=0.5, **common)
        arbitrary_percentage = SEOQualityRater().rate(keyword_density=99.0, **common)

        self.assertLess(
            arbitrary_percentage["category_scores"]["keyword_optimization"],
            natural["category_scores"]["keyword_optimization"],
        )
        self.assertLess(arbitrary_percentage["overall_score"], natural["overall_score"])
        findings = "\n".join(
            arbitrary_percentage["critical_issues"] + arbitrary_percentage["warnings"]
        ).lower()
        self.assertIn("density", findings)
        self.assertNotIn("stuffing", findings)

    def test_contextual_exact_phrase_repetition_is_a_hard_stuffing_failure(self):
        keyword = "field service scheduling"
        repeated = (
            f"# {keyword.title()}\n\n"
            f"{keyword} helps dispatchers assign work. "
            f"{keyword} helps dispatchers assign work. "
            f"{keyword} helps dispatchers assign work.\n\n"
            f"## A practical {keyword} workflow\n\n"
            "Dispatchers review skills, locations, priorities, and customer commitments.\n\n"
            "- Confirm technician availability.\n"
            "- Update the job record."
        )

        result = SEOQualityRater().rate(
            repeated,
            meta_title="Field Service Scheduling Guide for Teams | Simpro",
            meta_description=(
                "Field service scheduling helps teams match technicians to jobs, "
                "coordinate customer commitments, and keep dispatch records current."
            ),
            primary_keyword=keyword,
            keyword_density=0.1,
        )

        findings = "\n".join(result["critical_issues"]).lower()
        self.assertIn("stuffing", findings)
        self.assertIn("repetition", findings)
        self.assertFalse(result["publishing_ready"])

    def test_image_alt_and_placeholder_comment_do_not_trigger_keyword_stuffing(self):
        keyword = "Texas plumbing license"
        content = f"""# Texas Plumbing License Guide

A Texas plumbing license follows credential-specific state requirements.

![Texas plumbing license pathway](IMAGE_PLACEHOLDER_ORIGINAL_TEXAS_LICENSE_HERO)
<!-- [IMAGE PLACEHOLDER 1: Original Texas plumbing license pathway hero] -->

## Requirements at a glance

Use the regulator's current credential pages to compare experience, fees, and supervision.
"""

        result = SEOQualityRater().rate(
            content,
            meta_title="Texas Plumbing License Requirements Guide | Simpro",
            meta_description=(
                "Compare Texas plumber credentials, experience rules, fees, renewal steps, "
                "and official application routes before choosing your next license."
            ),
            primary_keyword=keyword,
        )

        findings = "\n".join(result["critical_issues"]).lower()
        self.assertNotIn("stuffing", findings)

    def test_seo_quality_rater_computes_stuffing_risk_when_density_is_not_supplied(self):
        keyword = "field service scheduling"
        content = (
            f"# {keyword.title()}\n\n"
            + (f"{keyword} improves dispatch. " * 8)
            + ("Teams review capacity and constraints before assigning jobs. " * 20)
        )

        result = SEOQualityRater().rate(
            content,
            meta_title="Field Service Scheduling Guide for Teams | Simpro",
            meta_description=(
                "Field service scheduling guidance for teams reviewing job priority, "
                "capacity, travel constraints, and customer commitments before dispatch."
            ),
            primary_keyword=keyword,
        )

        self.assertIn("stuffing", "\n".join(result["critical_issues"]).lower())

    def test_seo_quality_rater_rejects_invalid_runtime_keyword_density(self):
        common = {
            "content": concise_article_with_links(),
            "meta_title": "Payments for Trades Businesses Guide and Tips | Simpro",
            "meta_description": (
                "Payments for trades businesses need online, mobile and field options. "
                "Learn how to reduce friction and protect cash flow today."
            ),
            "primary_keyword": "payments for trades businesses",
        }

        for density in [-0.1, True, float("nan"), float("inf"), "3.1"]:
            with self.subTest(density=density):
                with self.assertRaisesRegex(ValueError, "keyword_density"):
                    SEOQualityRater().rate(keyword_density=density, **common)

        SEOQualityRater().rate(keyword_density=0, **common)

    def test_seo_quality_rater_validates_public_runtime_inputs(self):
        rater = SEOQualityRater()

        for content in (None, 42):
            with self.subTest(content=content):
                with self.assertRaisesRegex(ValueError, "content"):
                    rater.rate(content)

        for secondary in ("dispatch", [""], [42]):
            with self.subTest(secondary_keywords=secondary):
                with self.assertRaisesRegex(ValueError, "secondary_keywords"):
                    rater.rate("# Scheduling", secondary_keywords=secondary)

        for field_name in ("internal_link_count", "external_link_count"):
            with self.subTest(field_name=field_name):
                with self.assertRaisesRegex(ValueError, field_name):
                    rater.rate("# Scheduling", **{field_name: True})

        with self.assertRaisesRegex(ValueError, "validate_urls"):
            rater.rate("# Scheduling", validate_urls="false")

    def test_seo_quality_rater_rejects_invalid_explicit_word_count_rules(self):
        invalid_guidelines = [
            {"min_word_count": 0},
            {"optimal_word_count": -1},
            {"max_word_count": True},
            {"min_word_count": 1200.5},
            {"max_word_count": float("inf")},
            {"min_word_count": "1200"},
        ]

        for guidelines in invalid_guidelines:
            with self.subTest(guidelines=guidelines):
                with self.assertRaisesRegex(ValueError, "word_count"):
                    SEOQualityRater(guidelines)

    def test_seo_quality_rater_rejects_inverted_word_count_ranges(self):
        for guidelines in [
            {"min_word_count": 1600, "max_word_count": 1200},
            {"min_word_count": 1600, "optimal_word_count": 1200},
            {"optimal_word_count": 1800, "max_word_count": 1600},
        ]:
            with self.subTest(guidelines=guidelines):
                with self.assertRaisesRegex(ValueError, "word_count"):
                    SEOQualityRater(guidelines)

    def test_keyword_analyzer_rejects_invalid_explicit_density_targets(self):
        analyzer = KeywordAnalyzer()

        for target in [0, -1, True, float("nan"), float("inf")]:
            with self.subTest(target=target):
                with self.assertRaisesRegex(ValueError, "target_density"):
                    analyzer.analyze(
                        "Field service scheduling connects work and people.",
                        "field service scheduling",
                        target_density=target,
                    )

    def test_keyword_analyzer_validates_public_text_inputs(self):
        analyzer = KeywordAnalyzer()

        for content in (None, 42):
            with self.subTest(content=content):
                with self.assertRaisesRegex(ValueError, "content"):
                    analyzer.analyze(content, "field service scheduling")

        for keyword in (None, "", "   ", 42):
            with self.subTest(primary_keyword=keyword):
                with self.assertRaisesRegex(ValueError, "primary_keyword"):
                    analyzer.analyze("Scheduling content", keyword)

        for secondary in ("dispatch", [""], [42]):
            with self.subTest(secondary_keywords=secondary):
                with self.assertRaisesRegex(ValueError, "secondary_keywords"):
                    analyzer.analyze(
                        "Scheduling content",
                        "field service scheduling",
                        secondary_keywords=secondary,
                    )

    def test_keyword_analyzer_flags_isolated_paragraph_stuffing(self):
        content = (
            "field service scheduling " * 6
            + "coordinates work.\n\n"
            + "A separate section contains enough ordinary language to keep the "
            + "article-wide exact-match density below the warning threshold. " * 40
        )

        result = KeywordAnalyzer().analyze(
            content,
            "field service scheduling",
        )

        self.assertEqual(result["keyword_stuffing"]["risk_level"], "high")
        self.assertFalse(result["keyword_stuffing"]["safe"])

    def test_keyword_analyzer_uses_unrounded_density_at_stuffing_boundary(self):
        paragraphs = [
            "target phrase " + " ".join(f"word{i}_{j}" for j in range(31))
            for i in range(10)
        ]
        content = "\n\n".join(paragraphs) + " filler filler filler"

        result = KeywordAnalyzer().analyze(content, "target phrase")

        self.assertEqual(result["primary_keyword"]["density"], 3.0)
        self.assertEqual(result["keyword_stuffing"]["risk_level"], "high")

    def test_keyword_analyzer_counts_only_bounded_exact_phrase_matches(self):
        analyzer = KeywordAnalyzer()

        substring_result = analyzer.analyze("application mapping", "app")
        separated_result = analyzer.analyze(
            "Field operations and service scheduling",
            "field service",
        )
        exact_result = analyzer.analyze(
            "FIELD SERVICE improves field\nservice handoffs.",
            "field service",
        )

        for result in (substring_result, separated_result):
            primary = result["primary_keyword"]
            self.assertEqual(primary["exact_matches"], 0)
            self.assertEqual(primary["total_occurrences"], 0)
            self.assertEqual(primary["positions"], [])
            self.assertEqual(primary["density"], 0)

        exact_primary = exact_result["primary_keyword"]
        self.assertEqual(exact_primary["exact_matches"], 2)
        self.assertEqual(exact_primary["total_occurrences"], 2)
        self.assertEqual(len(exact_primary["positions"]), 2)

    def test_keyword_analyzer_does_not_force_exact_keyword_into_conclusion(self):
        result = KeywordAnalyzer().analyze(
            "# Field Service Scheduling\n\n"
            "Field service scheduling coordinates work.\n\n"
            "## Next operational decision\n\n"
            "Review the dispatch handoff before changing the process.",
            "field service scheduling",
        )

        recommendations = "\n".join(result["recommendations"]).lower()
        self.assertNotIn("conclusion", recommendations)

    def test_keyword_analyzer_cli_rejects_invalid_target_without_traceback(self):
        completed = subprocess.run(
            [
                sys.executable,
                "data_sources/modules/keyword_analyzer.py",
                "--target-density",
                "0",
            ],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertEqual(completed.returncode, 2)
        self.assertIn("--target-density", completed.stderr)
        self.assertNotIn("Traceback", completed.stderr)

    def test_seo_quality_rater_cli_rejects_non_finite_density_without_traceback(self):
        completed = subprocess.run(
            [
                sys.executable,
                "data_sources/modules/seo_quality_rater.py",
                "README.md",
                "--keyword-density",
                "nan",
            ],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertEqual(completed.returncode, 2)
        self.assertIn("--keyword-density", completed.stderr)
        self.assertNotIn("Traceback", completed.stderr)

    def test_seo_quality_rater_counts_absolute_simpro_links_as_internal(self):
        content = long_article()

        result = SEOQualityRater().rate(
            content,
            meta_title="Payments for Trades Businesses Guide and Tips | Simpro",
            meta_description=(
                "Payments for trades businesses need online, mobile and field options. "
                "Learn how to reduce friction and protect cash flow today."
            ),
            primary_keyword="payments for trades businesses",
        )

        self.assertNotIn(
            "Too few internal links",
            "\n".join(result["warnings"] + result["suggestions"]),
        )

    def test_seo_quality_rater_warns_when_meta_title_missing_brand_suffix(self):
        result = SEOQualityRater().rate(
            long_article(),
            meta_title="Payments for Trades Businesses: Customer Guide",
            meta_description=(
                "Payments for trades businesses need online, mobile and field options. "
                "Learn how to reduce friction and protect cash flow today."
            ),
            primary_keyword="payments for trades businesses",
        )

        self.assertIn("brand suffix", "\n".join(result["warnings"]))

    def test_seo_quality_rater_accepts_clockshark_brand_suffix(self):
        result = SEOQualityRater().rate(
            long_article("construction draw schedule"),
            meta_title="Construction Draw Schedule Explained | ClockShark",
            meta_description=(
                "Construction draw schedule planning helps contractors prepare draw requests, "
                "track inspections, and protect cash flow."
            ),
            primary_keyword="construction draw schedule",
        )

        self.assertNotIn("brand suffix", "\n".join(result["warnings"]))

    def test_seo_quality_rater_counts_absolute_clockshark_links_as_internal(self):
        result = rate_article_with_links(
            "[ClockShark construction trades](https://www.clockshark.com/industries/construction-trades)\n"
            "[ClockShark job management tools](https://www.clockshark.com/tour/job-management)\n"
            "[construction schedule example](https://www.clockshark.com/blog/construction-schedule-example)\n"
            "[types of construction projects](https://www.clockshark.com/blog/types-of-construction-projects)\n"
            "[Underground Contractors customer story](https://www.clockshark.com/resources/case-study-underground-contractors)\n",
            brand="ClockShark",
        )

        self.assertTrue(result["publishing_ready"], result)
        self.assertNotIn("Too few internal links", "\n".join(result["warnings"] + result["suggestions"]))
        self.assertNotIn("down-funnel", "\n".join(result["critical_issues"]))

    def test_seo_quality_rater_counts_absolute_bigchange_links_as_internal(self):
        result = rate_article_with_links(
            "[mobile workforce management software]"
            "(https://www.bigchange.com/features/mobile-workforce-management-software)\n"
            "[field service management software]"
            "(https://www.bigchange.com/field-service-management-software)\n"
            "[stock setup guide]"
            "(https://www.bigchange.com/blog/how-to-set-up-and-sort-your-stock-hassle-free-with-bigchange)\n",
            brand="BigChange",
        )

        self.assertTrue(result["publishing_ready"], result)
        self.assertNotIn("Too few internal links", "\n".join(result["warnings"] + result["suggestions"]))
        self.assertNotIn("down-funnel", "\n".join(result["critical_issues"]))

    def test_seo_quality_rater_counts_absolute_aroflo_links_as_internal(self):
        result = rate_article_with_links(
            "[job estimating software](https://aroflo.com/features/job-estimating)\n"
            "[construction estimator guide](https://aroflo.com/blog/construction-estimator)\n"
            "[job costing guide](https://aroflo.com/blog/the-how-to-job-costing-guide-that-every-tradesperson-should-read)\n",
            brand="AroFlo",
        )

        self.assertTrue(result["publishing_ready"], result)
        self.assertNotIn("Too few internal links", "\n".join(result["warnings"] + result["suggestions"]))
        self.assertNotIn("down-funnel", "\n".join(result["critical_issues"]))

    def test_seo_quality_rater_rejects_cross_brand_owned_links_as_internal(self):
        cases = (
            ("AroFlo", "https://www.bigchange.com/features/mobile-workforce-management-software"),
            ("BigChange", "https://www.clockshark.com/tour/job-management"),
            ("ClockShark", "https://www.simprogroup.com/features/payments"),
            ("Simpro", "https://aroflo.com/features/job-estimating"),
        )

        for brand, target in cases:
            with self.subTest(brand=brand, target=target):
                result = rate_article_with_links(
                    f"[job management software]({target})\n",
                    brand=brand,
                    guidelines={"min_internal_links": 1},
                )

                issues = "\n".join(result["critical_issues"])
                warnings = "\n".join(result["warnings"] + result["suggestions"])
                self.assertIn("down-funnel internal link", issues)
                self.assertIn("Too few internal links", warnings)

    def test_seo_quality_rater_accepts_natural_locale_keyword_variant(self):
        content = long_article("construction estimating software options in Australia")

        result = SEOQualityRater().rate(
            content,
            meta_title="Best Construction Estimating Software Australia | AroFlo",
            meta_description=(
                "Compare construction estimating software in Australia by features, "
                "pricing, takeoffs and suitability for builders and trade businesses."
            ),
            primary_keyword="construction estimating software australia",
        )

        issues = "\n".join(result["critical_issues"])
        self.assertNotIn("missing from H1", issues)
        self.assertNotIn("missing from first 100 words", issues)

    def test_seo_quality_rater_accepts_state_first_keyword_variant(self):
        content = long_article("california electrical license")

        result = SEOQualityRater().rate(
            content,
            meta_title="California Electrical License Guide | Simpro",
            meta_description=(
                "California electrical license steps cover trainee registration, "
                "work hours, certification exams and contractor licensing."
            ),
            primary_keyword="electrical license california",
        )

        issues = "\n".join(result["critical_issues"])
        self.assertNotIn("missing from H1", issues)
        self.assertNotIn("missing from first 100 words", issues)

    def test_seo_quality_rater_accepts_industries_hub_down_funnel_link(self):
        result = rate_article_with_links(
            "[field service management solutions for your industry]"
            "(https://www.simprogroup.com/industries)\n"
            "[TEAMWired](https://www.simprogroup.com/case-studies/teamwired)\n"
            "[Simpro pricing](https://www.simprogroup.com/pricing)\n"
        )

        self.assertFalse(result["publishing_ready"], result)
        self.assertIn("verified commercial pillar index", "\n".join(result["critical_issues"]))

    def test_seo_quality_rater_counts_industry_cluster_link_as_down_funnel_internal_link(self):
        result = rate_article_with_links(
            "[plumbing contractor software]"
            "(https://www.simprogroup.com/industries/plumbing-software)\n"
            "[plumbing margin guide]"
            "(https://www.simprogroup.com/blog/plumbing-business-profit-margin-guide)\n"
            "[plumbing KPI guide]"
            "(https://www.simprogroup.com/blog/plumbing-kpis-that-protect-margin)\n"
        )

        findings = "\n".join(result["warnings"] + result["suggestions"])
        self.assertTrue(result["publishing_ready"], result)
        self.assertNotIn("down-funnel", "\n".join(result["critical_issues"]))
        self.assertNotIn("Too few internal links", findings)

    def test_seo_quality_rater_accepts_features_hub_down_funnel_link(self):
        result = rate_article_with_links(
            "[job management software for field service teams]"
            "(https://www.bigchange.com/features)\n"
            "[job sheet app](https://www.bigchange.com/job-sheet-app)\n"
            "[job sheet software guide]"
            "(https://www.bigchange.com/blog/job-sheet-software)\n",
            brand="BigChange",
        )

        self.assertTrue(result["publishing_ready"], result)
        self.assertNotIn("down-funnel", "\n".join(result["critical_issues"]))

    def test_seo_quality_rater_accepts_clockshark_tour_down_funnel_link(self):
        result = rate_article_with_links(
            "[time tracking software for construction and field service crews]"
            "(https://www.clockshark.com/tour/time-tracking-software)\n"
            "[paper time card workflow](https://www.clockshark.com/blog/reasons-to-use-a-time-clock-instead-of-paper-time-cards)\n"
            "[employee tracking apps](https://www.clockshark.com/blog/employee-tracking-apps)\n",
            brand="ClockShark",
        )

        self.assertTrue(result["publishing_ready"], result)
        self.assertNotIn("down-funnel", "\n".join(result["critical_issues"]))

    def test_seo_quality_rater_accepts_feature_down_funnel_link(self):
        result = rate_article_with_links(
            "[field service payments](https://www.simprogroup.com/features/payments)\n"
            "[accounts receivable follow-up with Fast Cash](https://www.simprogroup.com/features/fast-cash)\n"
            "[TEAMWired](https://www.simprogroup.com/case-studies/teamwired)\n"
        )

        self.assertFalse(result["publishing_ready"], result)
        self.assertIn("verified commercial pillar index", "\n".join(result["critical_issues"]))

    def test_seo_quality_rater_rejects_name_only_feature_anchor(self):
        cases = [
            ("Simpro Payments", "https://www.simprogroup.com/features/payments"),
            ("Fast Cash", "https://www.simprogroup.com/features/fast-cash"),
        ]

        for anchor, url in cases:
            with self.subTest(anchor=anchor):
                result = rate_article_with_links(
                    f"[{anchor}]({url})\n"
                    "[TEAMWired](https://www.simprogroup.com/case-studies/teamwired)\n"
                    "[Simpro pricing](https://www.simprogroup.com/pricing)\n"
                )

                issues = "\n".join(result["critical_issues"])
                self.assertFalse(result["publishing_ready"], result)
                self.assertIn("name-only", issues)
                self.assertIn("functional", issues)

    def test_seo_quality_rater_rejects_name_only_feature_anchor_even_with_valid_down_funnel_link(self):
        result = rate_article_with_links(
            "[field service payments](https://www.simprogroup.com/features/payments)\n"
            "[Fast Cash](https://www.simprogroup.com/features/fast-cash)\n"
            "[TEAMWired](https://www.simprogroup.com/case-studies/teamwired)\n"
        )

        issues = "\n".join(result["critical_issues"])
        self.assertFalse(result["publishing_ready"], result)
        self.assertIn("name-only", issues)
        self.assertIn("functional", issues)

    def test_seo_quality_rater_accepts_solution_down_funnel_link(self):
        result = rate_article_with_links(
            "[field service management software]"
            "(https://www.simprogroup.com/)\n"
            "[TEAMWired](https://www.simprogroup.com/case-studies/teamwired)\n"
            "[Simpro pricing](https://www.simprogroup.com/pricing)\n"
        )

        self.assertTrue(result["publishing_ready"], result)
        self.assertNotIn("down-funnel", "\n".join(result["critical_issues"]))

    def test_seo_quality_rater_rejects_relative_simpro_commercial_link(self):
        result = rate_article_with_links(
            "[field service management software]"
            "(/)\n"
            "[TEAMWired](https://www.simprogroup.com/case-studies/teamwired)\n"
            "[Simpro pricing](https://www.simprogroup.com/pricing)\n"
        )

        issues = "\n".join(result["critical_issues"])
        self.assertFalse(result["publishing_ready"], result)
        self.assertIn("verified commercial pillar index", issues)
        self.assertIn("exact absolute canonical URL", issues)

    def test_seo_quality_rater_rejects_name_only_solution_anchor(self):
        result = rate_article_with_links(
            "[Simpro Premium](https://www.simprogroup.com/solutions/simpro-premium)\n"
            "[TEAMWired](https://www.simprogroup.com/case-studies/teamwired)\n"
            "[Simpro pricing](https://www.simprogroup.com/pricing)\n"
        )

        issues = "\n".join(result["critical_issues"])
        self.assertFalse(result["publishing_ready"], result)
        self.assertIn("name-only", issues)
        self.assertIn("functional", issues)

    def test_seo_quality_rater_requires_down_funnel_link_beyond_internal_count(self):
        result = rate_article_with_links(
            "[payments blog](https://www.simprogroup.com/blog/payments-as-a-strategic-growth-lever-for-trades)\n"
            "[TEAMWired](https://www.simprogroup.com/case-studies/teamwired)\n"
            "[Simpro pricing](https://www.simprogroup.com/pricing)\n"
            "[book a demo](https://www.simprogroup.com/demo)\n"
        )

        issues = "\n".join(result["critical_issues"])
        self.assertFalse(result["publishing_ready"], result)
        self.assertIn("down-funnel internal link", issues)
        self.assertNotIn("Too few internal links", "\n".join(result["warnings"]))

    def test_seo_quality_rater_rejects_generic_anchor_for_down_funnel_link(self):
        result = rate_article_with_links(
            "[learn more](https://www.simprogroup.com/features/payments)\n"
            "[TEAMWired](https://www.simprogroup.com/case-studies/teamwired)\n"
            "[Simpro pricing](https://www.simprogroup.com/pricing)\n"
        )

        issues = "\n".join(result["critical_issues"])
        self.assertFalse(result["publishing_ready"], result)
        self.assertIn("generic anchor text", issues)

    def test_seo_quality_rater_weak_down_funnel_anchor_guidance_uses_indexed_keyword_language(self):
        result = rate_article_with_links(
            "[operations platform]"
            "(https://www.simprogroup.com/)\n"
            "[TEAMWired](https://www.simprogroup.com/case-studies/teamwired)\n"
            "[Simpro pricing](https://www.simprogroup.com/pricing)\n"
        )

        issues = "\n".join(result["critical_issues"])
        self.assertFalse(result["publishing_ready"], result)
        self.assertIn("indexed main keyword", issues)
        self.assertNotIn("destination keyword", issues)

    def test_seo_quality_rater_rejects_unresolved_urls_when_validation_is_enabled(self):
        blocked = UrlValidationResult(
            url="https://example.com/missing",
            status="unresolved",
            status_code=404,
            reason="HTTP 404",
            line=12,
            anchor="missing source",
        )

        with patch(
            "data_sources.modules.seo_quality_rater.validate_content_urls",
            return_value=UrlValidationSummary([blocked]),
        ):
            result = SEOQualityRater().rate(
                long_article(),
                meta_title="Payments for Trades Businesses Guide and Tips | Simpro",
                meta_description=(
                    "Payments for trades businesses need online, mobile and field options. "
                    "Learn how to reduce friction and protect cash flow today."
                ),
                primary_keyword="payments for trades businesses",
                validate_urls=True,
            )

        issues = "\n".join(result["critical_issues"])
        self.assertFalse(result["publishing_ready"], result)
        self.assertIn("Unresolved URL", issues)
        self.assertIn("https://example.com/missing", issues)

    def test_seo_quality_rater_does_not_count_demo_pricing_blog_or_case_study_as_down_funnel(self):
        result = rate_article_with_links(
            "[read the blog](https://www.simprogroup.com/blog/payments-as-a-strategic-growth-lever-for-trades)\n"
            "[TEAMWired case study](https://www.simprogroup.com/case-studies/teamwired)\n"
            "[Simpro pricing](https://www.simprogroup.com/pricing)\n"
            "[book a demo](https://www.simprogroup.com/demo)\n"
            "[contact Simpro](https://www.simprogroup.com/contact-us)\n"
            "[Simpro](https://www.simprogroup.com/)\n"
        )

        issues = "\n".join(result["critical_issues"])
        self.assertFalse(result["publishing_ready"], result)
        self.assertIn("down-funnel internal link", issues)

    def test_keyword_analyzer_runs_without_optional_sklearn(self):
        from data_sources.modules.keyword_analyzer import analyze_keywords

        result = analyze_keywords(
            long_article(),
            "payments for trades businesses",
            ["field service payments", "embedded payments"],
        )

        self.assertEqual(result["primary_keyword"]["keyword"], "payments for trades businesses")
        self.assertIn("topic_clusters", result)
        self.assertIn("recommendations", result)

    def test_keyword_analyzer_detects_h1_after_frontmatter(self):
        from data_sources.modules.keyword_analyzer import analyze_keywords

        content = (
            "---\n"
            "title: Payments for Trades Businesses\n"
            "---\n\n"
            "# Payments for Trades Businesses: Customer Guide\n\n"
            "Payments for trades businesses need secure invoice and payment paths.\n\n"
            "## Field service payments\n\n"
            "Field service teams need clean payment status."
        )

        result = analyze_keywords(content, "payments for trades businesses")

        self.assertTrue(result["primary_keyword"]["critical_placements"]["in_h1"])

    def test_keyword_analyzer_handles_low_density_and_missing_secondary_recommendations(self):
        from data_sources.modules.keyword_analyzer import analyze_keywords

        content = (
            "# Payments for Trades Businesses\n\n"
            + ("Service teams need clean invoices and payment status. " * 120)
        )

        result = analyze_keywords(
            content,
            "payments for trades businesses",
            ["embedded payments for trades businesses"],
            target_density=1.5,
        )

        recommendations = "\n".join(result["recommendations"])
        self.assertEqual(result["primary_keyword"]["density_status"], "too_low")
        self.assertIn("Target is 1.5%", recommendations)
        self.assertIn("embedded payments for trades businesses", recommendations)

    def test_keyword_analyzer_default_reports_density_without_low_density_prompting(self):
        from data_sources.modules.keyword_analyzer import analyze_keywords

        content = (
            "# Payments for Trades Businesses\n\n"
            "Payments for trades businesses need secure invoice workflows.\n\n"
            + ("Service teams need clear payment status and customer records. " * 120)
        )

        result = analyze_keywords(
            content,
            "payments for trades businesses",
            ["embedded payments for trades businesses"],
        )

        recommendations = "\n".join(result["recommendations"])
        self.assertIsNone(result["primary_keyword"]["target_density"])
        self.assertEqual(result["primary_keyword"]["density_status"], "reported")
        self.assertIn("density", result["primary_keyword"])
        self.assertNotIn("too low", recommendations)
        self.assertNotIn("Add payments for trades businesses naturally", recommendations)
        recommendations.encode("ascii")

    def test_keyword_analyzer_uses_natural_h2_placement_without_a_quota(self):
        from data_sources.modules.keyword_analyzer import analyze_keywords

        content = (
            "# Payments for Trades Businesses\n\n"
            "Payments for trades businesses need secure invoice workflows.\n\n"
            "## Payments for trades businesses workflow\n\n"
            "Connect invoice and job records.\n\n"
            "## Reconcile exceptions\n\nResolve failed payments.\n\n"
            "## Review handoffs\n\nConfirm field status.\n\n"
            "## Close the loop\n\nRecord the next operational action."
        )

        result = analyze_keywords(content, "payments for trades businesses")
        recommendations = "\n".join(result["recommendations"])

        self.assertNotIn("Aim for 2-3 H2s", recommendations)
        self.assertNotIn("1/3 of H2s", recommendations)

    def test_keyword_analyzer_cli_scores_supplied_file(self):
        article = long_article()

        with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".md", delete=False) as temp_file:
            temp_file.write(article)
            temp_path = temp_file.name

        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"

        try:
            completed = subprocess.run(
                [
                    sys.executable,
                    "data_sources/modules/keyword_analyzer.py",
                    temp_path,
                    "--primary-keyword",
                    "payments for trades businesses",
                    "--secondary-keywords",
                    "field service payments,embedded payments",
                ],
                cwd=PROJECT_ROOT,
                env=env,
                text=True,
                encoding="utf-8",
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
        finally:
            os.unlink(temp_path)

        self.assertEqual(completed.returncode, 0, completed.stderr + completed.stdout)
        self.assertIn("Primary Keyword: payments for trades businesses", completed.stdout)
        self.assertNotIn("Primary Keyword: start a podcast", completed.stdout)


if __name__ == "__main__":
    unittest.main()
