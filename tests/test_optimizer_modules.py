import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

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
        + "[field service management software](https://www.simprogroup.com/solutions/field-service-management)\n"
        + "[Federal Reserve](https://www.frbservices.org/news)\n"
        + "[J.D. Power](https://www.jdpower.com/business)\n"
    )


def rate_article_with_links(links):
    return SEOQualityRater().rate(
        article_with_links(links),
        meta_title="Payments for Trades Businesses Guide and Tips | Simpro",
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

    def test_seo_quality_rater_default_density_mode_detects_high_and_stuffed_content(self):
        common = {
            "content": concise_article_with_links(),
            "meta_title": "Payments for Trades Businesses Guide and Tips | Simpro",
            "meta_description": (
                "Payments for trades businesses need online, mobile and field options. "
                "Learn how to reduce friction and protect cash flow today."
            ),
            "primary_keyword": "payments for trades businesses",
        }

        high = SEOQualityRater().rate(keyword_density=2.6, **common)
        stuffed = SEOQualityRater().rate(keyword_density=3.1, **common)

        self.assertIn("slightly high (2.6%)", "\n".join(high["warnings"]))
        self.assertIn("stuffing", "\n".join(stuffed["critical_issues"]).lower())

    def test_seo_quality_rater_derives_legacy_thresholds_from_custom_maximum(self):
        guidelines = SEOQualityRater()._default_guidelines()
        guidelines.pop("keyword_high_density_warning")
        guidelines.pop("keyword_stuffing_density")
        guidelines["primary_keyword_density_min"] = 0.5
        guidelines["primary_keyword_density_max"] = 1.0
        result = SEOQualityRater(guidelines).rate(
            concise_article_with_links(),
            meta_title="Payments for Trades Businesses Guide and Tips | Simpro",
            meta_description=(
                "Payments for trades businesses need online, mobile and field options. "
                "Learn how to reduce friction and protect cash flow today."
            ),
            primary_keyword="payments for trades businesses",
            keyword_density=2.0,
        )

        self.assertIn("stuffing", "\n".join(result["critical_issues"]).lower())

    def test_seo_quality_rater_explicit_thresholds_override_legacy_maximum(self):
        guidelines = SEOQualityRater()._default_guidelines()
        guidelines["primary_keyword_density_min"] = 0.5
        guidelines["primary_keyword_density_max"] = 1.0
        guidelines["keyword_high_density_warning"] = 4.0
        guidelines["keyword_stuffing_density"] = 5.0
        result = SEOQualityRater(guidelines).rate(
            concise_article_with_links(),
            meta_title="Payments for Trades Businesses Guide and Tips | Simpro",
            meta_description=(
                "Payments for trades businesses need online, mobile and field options. "
                "Learn how to reduce friction and protect cash flow today."
            ),
            primary_keyword="payments for trades businesses",
            keyword_density=2.0,
        )

        density_findings = [
            finding
            for finding in result["critical_issues"] + result["warnings"]
            if "density" in finding.lower() or "stuffing" in finding.lower()
        ]
        self.assertEqual(density_findings, [])

    def test_seo_quality_rater_merges_partial_custom_guidelines(self):
        result = SEOQualityRater(
            {"primary_keyword_density_max": 1.0}
        ).rate(
            concise_article_with_links(),
            meta_title="Payments for Trades Businesses Guide and Tips | Simpro",
            meta_description=(
                "Payments for trades businesses need online, mobile and field options. "
                "Learn how to reduce friction and protect cash flow today."
            ),
            primary_keyword="payments for trades businesses",
            keyword_density=1.6,
        )

        self.assertIn("stuffing", "\n".join(result["critical_issues"]).lower())

    def test_seo_quality_rater_resolves_mixed_new_and_legacy_thresholds_independently(self):
        rater = SEOQualityRater(
            {
                "primary_keyword_density_max": 1.0,
                "keyword_high_density_warning": 1.2,
            }
        )
        common = {
            "content": concise_article_with_links(),
            "meta_title": "Payments for Trades Businesses Guide and Tips | Simpro",
            "meta_description": (
                "Payments for trades businesses need online, mobile and field options. "
                "Learn how to reduce friction and protect cash flow today."
            ),
            "primary_keyword": "payments for trades businesses",
        }

        below_warning = rater.rate(keyword_density=1.1, **common)
        warned = rater.rate(keyword_density=1.3, **common)
        stuffed = rater.rate(keyword_density=1.6, **common)

        self.assertNotIn("slightly high", "\n".join(below_warning["warnings"]).lower())
        self.assertIn("slightly high", "\n".join(warned["warnings"]).lower())
        self.assertIn("stuffing", "\n".join(stuffed["critical_issues"]).lower())

    def test_seo_quality_rater_density_boundaries_are_strict(self):
        common = {
            "content": concise_article_with_links(),
            "meta_title": "Payments for Trades Businesses Guide and Tips | Simpro",
            "meta_description": (
                "Payments for trades businesses need online, mobile and field options. "
                "Learn how to reduce friction and protect cash flow today."
            ),
            "primary_keyword": "payments for trades businesses",
        }

        warning_boundary = SEOQualityRater().rate(keyword_density=2.5, **common)
        stuffing_boundary = SEOQualityRater().rate(keyword_density=3.0, **common)

        warning_findings = "\n".join(
            warning_boundary["critical_issues"] + warning_boundary["warnings"]
        )
        self.assertNotIn("density is", warning_findings.lower())
        self.assertNotIn("stuffing", warning_findings.lower())
        self.assertIn("slightly high (3.0%)", "\n".join(stuffing_boundary["warnings"]))
        self.assertNotIn("stuffing", "\n".join(stuffing_boundary["critical_issues"]).lower())

    def test_seo_quality_rater_rejects_invalid_density_thresholds(self):
        invalid_guidelines = [
            {"keyword_high_density_warning": 0},
            {"keyword_stuffing_density": float("nan")},
            {
                "keyword_high_density_warning": 4.0,
                "keyword_stuffing_density": 3.0,
            },
        ]

        for guidelines in invalid_guidelines:
            with self.subTest(guidelines=guidelines):
                with self.assertRaises(ValueError):
                    SEOQualityRater(guidelines)

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

    def test_seo_quality_rater_rejects_inverted_legacy_density_range(self):
        with self.assertRaisesRegex(ValueError, "density"):
            SEOQualityRater(
                {
                    "primary_keyword_density_min": 3.0,
                    "primary_keyword_density_max": 1.0,
                }
            )

        for guidelines in [
            {"min_word_count": 1600, "max_word_count": 1200},
            {"min_word_count": 1600, "optimal_word_count": 1200},
            {"optimal_word_count": 1800, "max_word_count": 1600},
        ]:
            with self.subTest(guidelines=guidelines):
                with self.assertRaisesRegex(ValueError, "word_count"):
                    SEOQualityRater(guidelines)

    def test_seo_quality_rater_low_density_message_does_not_render_none(self):
        result = SEOQualityRater(
            {"primary_keyword_density_min": 0.5}
        ).rate(
            concise_article_with_links(),
            meta_title="Payments for Trades Businesses Guide and Tips | Simpro",
            meta_description=(
                "Payments for trades businesses need online, mobile and field options. "
                "Learn how to reduce friction and protect cash flow today."
            ),
            primary_keyword="payments for trades businesses",
            keyword_density=0.1,
        )

        warning = "\n".join(result["warnings"])
        self.assertIn("Minimum is 0.5%", warning)
        self.assertNotIn("None", warning)

    def test_seo_quality_rater_stuffing_protection_precedes_custom_minimum(self):
        result = SEOQualityRater(
            {"primary_keyword_density_min": 4.0}
        ).rate(
            concise_article_with_links(),
            meta_title="Payments for Trades Businesses Guide and Tips | Simpro",
            meta_description=(
                "Payments for trades businesses need online, mobile and field options. "
                "Learn how to reduce friction and protect cash flow today."
            ),
            primary_keyword="payments for trades businesses",
            keyword_density=3.1,
        )

        self.assertIn("stuffing", "\n".join(result["critical_issues"]).lower())
        self.assertNotIn("too low", "\n".join(result["warnings"]).lower())

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
            "[Underground Contractors customer story](https://www.clockshark.com/resources/case-study-underground-contractors)\n"
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
            "(https://www.bigchange.com/blog/how-to-set-up-and-sort-your-stock-hassle-free-with-bigchange)\n"
        )

        self.assertTrue(result["publishing_ready"], result)
        self.assertNotIn("Too few internal links", "\n".join(result["warnings"] + result["suggestions"]))
        self.assertNotIn("down-funnel", "\n".join(result["critical_issues"]))

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
