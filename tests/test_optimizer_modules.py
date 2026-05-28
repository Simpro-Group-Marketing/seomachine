import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from data_sources.modules.seo_quality_rater import SEOQualityRater


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def long_article(primary_keyword="payments for trades businesses"):
    sections = []
    for index in range(1, 7):
        sections.append(
            f"## Section {index} for {primary_keyword}\n\n"
            + (
                f"{primary_keyword} helps field service teams connect jobs, invoices, "
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
                f"{primary_keyword} helps field service teams connect jobs, invoices, "
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


def rate_article_with_links(links):
    return SEOQualityRater().rate(
        article_with_links(links),
        meta_title="Payments for Trades Businesses: Customer Guide",
        meta_description=(
            "Payments for trades businesses need online, mobile and field options. "
            "Learn how to reduce friction and protect cash flow today."
        ),
        primary_keyword="payments for trades businesses",
    )


class OptimizerModuleTests(unittest.TestCase):
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
                    "Payments for Trades Businesses: Customer Guide",
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

    def test_seo_quality_rater_counts_absolute_simpro_links_as_internal(self):
        content = long_article()

        result = SEOQualityRater().rate(
            content,
            meta_title="Payments for Trades Businesses: Customer Guide",
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

    def test_seo_quality_rater_accepts_industries_hub_down_funnel_link(self):
        result = rate_article_with_links(
            "[field service management solutions for your industry]"
            "(https://www.simprogroup.com/industries)\n"
            "[TEAMWired](https://www.simprogroup.com/case-studies/teamwired)\n"
            "[Simpro pricing](https://www.simprogroup.com/pricing)\n"
        )

        self.assertTrue(result["publishing_ready"], result)
        self.assertNotIn("down-funnel", "\n".join(result["critical_issues"]))

    def test_seo_quality_rater_accepts_feature_down_funnel_link(self):
        result = rate_article_with_links(
            "[field service payments](https://www.simprogroup.com/features/payments)\n"
            "[accounts receivable follow-up with Fast Cash](https://www.simprogroup.com/features/fast-cash)\n"
            "[TEAMWired](https://www.simprogroup.com/case-studies/teamwired)\n"
        )

        self.assertTrue(result["publishing_ready"], result)
        self.assertNotIn("down-funnel", "\n".join(result["critical_issues"]))

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
            "(https://www.simprogroup.com/solutions/field-service-management-software)\n"
            "[TEAMWired](https://www.simprogroup.com/case-studies/teamwired)\n"
            "[Simpro pricing](https://www.simprogroup.com/pricing)\n"
        )

        self.assertTrue(result["publishing_ready"], result)
        self.assertNotIn("down-funnel", "\n".join(result["critical_issues"]))

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
        )

        recommendations = "\n".join(result["recommendations"])
        self.assertIn("payments for trades businesses", recommendations)
        self.assertIn("embedded payments for trades businesses", recommendations)
        recommendations.encode("ascii")

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
