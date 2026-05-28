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
        + "\n\n[Simpro Payments](https://www.simprogroup.com/features/payments)\n"
        + "[Fast Cash](https://www.simprogroup.com/features/fast-cash)\n"
        + "[TEAMWired](https://www.simprogroup.com/case-studies/teamwired)\n"
        + "[Federal Reserve](https://www.frbservices.org/news)\n"
        + "[J.D. Power](https://www.jdpower.com/business)\n"
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
