import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "scripts" / "research_serp_analysis.py"


def load_research_serp_module():
    spec = importlib.util.spec_from_file_location("research_serp_analysis", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class FakeIntentAnalyzer:
    def analyze(self, keyword, serp_features, top_results):
        return {
            "primary_intent": "informational",
            "confidence": {"overall": 82},
            "recommendations": ["Use a direct-answer structure."],
        }


class FakeContentLengthComparator:
    def fetch_word_count(self, url):
        return {
            "https://example.com/labor-burden": 1200,
            "https://example.com/payroll-burden": 900,
            "https://example.com/excel-template": 1500,
        }.get(url, 0)


class FakeDataForSEO:
    def __init__(self, serp_data=None, error=None):
        if error:
            raise error
        self.serp_data = serp_data or {
            "organic_results": [
                {
                    "title": "Labor Burden Rate Calculator",
                    "url": "https://dataforseo.example/calculator",
                    "description": "Structured API result.",
                }
            ],
            "features": ["people_also_ask"],
        }

    def get_serp_data(self, keyword, limit=20):
        return self.serp_data


class ResearchSerpPlaywrightFallbackTests(unittest.TestCase):
    def test_playwright_capture_uses_structural_serp_evidence_not_generic_page_text(self):
        module = load_research_serp_module()

        code = module.build_playwright_serp_extraction_code(
            "https://www.google.com/search?q=field+service+scheduling"
        )

        self.assertIn("featureEvidenceNodes", code)
        self.assertIn("peopleAlsoAskRoot", code)
        self.assertIn("resultContainerSelectors", code)
        self.assertIn("isVerifiedFeatureHeading", code)
        self.assertIn(
            "'a, nav, [role=\"navigation\"], div.MjjYud, div.g, "
            "div[data-sokoban-container]'",
            code,
        )
        self.assertNotIn("candidateRoot = candidateRoot.parentElement", code)
        self.assertIn(".map(nodeText)", code)
        self.assertIn("parsed.hostname.endsWith('.google.com')", code)
        self.assertNotIn("pattern.test(bodyText)", code)
        self.assertNotIn("|| anchor.parentElement", code)
        self.assertNotIn("bodyText\n      .split", code)
        self.assertNotIn(
            "'h1, h2, h3, [role=\"heading\"], [aria-label]'",
            code,
        )

    def test_playwright_dom_extraction_rejects_lookalike_features_and_links(self):
        module = load_research_serp_module()
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            self.skipTest("Playwright is not installed")

        html = """
        <nav><h2>Images</h2></nav>
        <div class="MjjYud">
          <a href="https://example.com/videos"><h3>Videos</h3></a>
          <p>A normal organic result whose title resembles a SERP feature.</p>
        </div>
        <section>
          <h2>People also ask</h2>
          <button>How should dispatch constraints be prioritized?</button>
        </section>
        <div><button>Is this unrelated question included?</button></div>
        <div class="g">
          <a href="https://example.com/guide"><h3>Scheduling Guide</h3></a>
          <p>Verified organic result container.</p>
        </div>
        <div class="g">
          <a href="https://support.google.com/help"><h3>Google Help</h3></a>
        </div>
        <a href="https://example.com/navigation"><h3>Outside Result Container</h3></a>
        """

        try:
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=True)
                page = browser.new_page()
                page.set_content(html)
                feature_payload = page.evaluate(
                    module.build_playwright_serp_feature_extraction_code()
                )
                organic_results = page.evaluate(
                    module.build_playwright_serp_organic_extraction_code()
                )
                browser.close()
        except Exception as exc:
            self.skipTest(f"Playwright Chromium is unavailable: {exc}")

        self.assertEqual(feature_payload["features"], ["people_also_ask"])
        self.assertEqual(
            feature_payload["paaQuestions"],
            ["How should dispatch constraints be prioritized?"],
        )
        self.assertEqual(
            [result["url"] for result in organic_results],
            ["https://example.com/videos", "https://example.com/guide"],
        )

    def test_real_content_comparator_exposes_public_fetch_method(self):
        module = load_research_serp_module()

        comparator = module.ContentLengthComparator()

        self.assertTrue(callable(comparator.fetch_word_count))
        self.assertTrue(callable(comparator.fetch_content_context))

    def test_content_brief_preserves_every_observed_serp_feature_for_evaluation(self):
        module = load_research_serp_module()
        analysis = {
            "top_results": [{"title": "Scheduling Guide", "url": "https://example.com"}],
            "dominant_content_type": "General Article",
            "serp_features": [
                "people_also_ask",
                "local_pack",
                "shopping_results",
                "ai_overview",
            ],
            "freshness_signals": [],
            "common_h2_topics": [],
            "search_intent": "informational",
        }

        brief = module.generate_content_brief("scheduling", analysis)
        rendered = "\n".join(brief["serp_features_to_evaluate"]).lower()

        for feature in analysis["serp_features"]:
            self.assertIn(feature.replace("_", " "), rendered)

    def test_content_brief_does_not_invent_default_content_type(self):
        module = load_research_serp_module()
        analysis = {
            "top_results": [{"title": "Scheduling", "url": "https://example.com"}],
            "serp_features": [],
            "freshness_signals": [],
            "common_h2_topics": [],
            "search_intent": "informational",
        }

        brief = module.generate_content_brief("scheduling", analysis)

        self.assertEqual(brief["content_type"], "Unknown")

    def test_content_requirements_report_word_counts_without_generating_target(self):
        module = load_research_serp_module()
        analysis = {
            "content_types": ["Guide", "Guide"],
            "word_counts": [900, 1100],
            "freshness_signals": [],
            "serp_features": [],
        }
        messages = []

        module.calculate_content_requirements(
            analysis,
            [{}, {}],
            messages.append,
        )

        self.assertEqual(analysis["avg_word_count"], 1000)
        self.assertNotIn("recommended_word_count", analysis)
        self.assertFalse(any("Recommended" in message for message in messages))

    def test_content_requirements_console_lists_every_observed_serp_feature(self):
        module = load_research_serp_module()
        features = [
            "featured_snippet",
            "people_also_ask",
            "video",
            "images",
            "local_pack",
            "ai_overview",
        ]
        analysis = {
            "content_types": [],
            "word_counts": [],
            "freshness_signals": [],
            "serp_features": features,
        }
        messages = []

        module.calculate_content_requirements(analysis, [{}], messages.append)

        rendered = "\n".join(str(message) for message in messages)
        for feature in features:
            self.assertIn(feature, rendered)

    def test_serp_analysis_extracts_only_recurring_h2s_with_url_provenance(self):
        module = load_research_serp_module()

        class HeadingComparator:
            def fetch_content_context(self, url):
                unique = url.rsplit("/", 1)[-1]
                return {
                    "word_count": 900,
                    "h2_headings": [
                        "Plan dispatch constraints",
                        f"Unique section {unique}",
                    ],
                }

        serp_results = [
            {
                "title": f"Scheduling Guide {index}",
                "url": f"https://example.com/{index}",
                "description": "Guide",
            }
            for index in range(1, 4)
        ]

        with tempfile.TemporaryDirectory() as temp_dir:
            result = module.run_serp_analysis(
                "field service scheduling",
                output_dir=temp_dir,
                now=datetime(2026, 8, 6),
                dataforseo_factory=lambda: FakeDataForSEO(
                    serp_data={"organic_results": serp_results, "features": []}
                ),
                fallback_runner=lambda *args, **kwargs: {},
                intent_analyzer_factory=FakeIntentAnalyzer,
                content_comparator_factory=HeadingComparator,
                print_fn=lambda message="": None,
            )

            self.assertEqual(result["common_h2_topics"], ["Plan dispatch constraints"])
            observations = result["heading_observations"]
            self.assertEqual(len(observations), 3)
            self.assertTrue(all(item["url"] for item in observations))
            self.assertNotIn("Unique section 1", result["common_h2_topics"])

            report = (
                Path(temp_dir) / "serp-analysis-field-service-scheduling.md"
            ).read_text(encoding="utf-8")
            self.assertIn("Plan dispatch constraints", report)
            self.assertIn("https://example.com/1", report)

    def test_freshness_matching_uses_word_boundaries(self):
        module = load_research_serp_module()

        self.assertTrue(module.has_freshness_signal("New scheduling guide", datetime(2026, 8, 6)))
        self.assertFalse(module.has_freshness_signal("Renew scheduling access", datetime(2026, 8, 6)))

    def test_domain_mix_does_not_invent_competitive_difficulty(self):
        module = load_research_serp_module()

        self.assertEqual(
            module.assess_difficulty(["forbes.com", "www.youtube.com"] * 5),
            "unresolved",
        )

    def test_content_brief_does_not_present_format_heuristics_as_observed_facts(self):
        module = load_research_serp_module()
        analysis = {
            "top_results": [
                {
                    "title": "How to Schedule Field Work in 2026",
                    "url": "https://example.com/scheduling",
                }
            ],
            "dominant_content_type": "How-To Guide",
            "content_type_distribution": {"How-To Guide": 1},
            "title_patterns": ["How to Schedule Field Work in 2026"],
            "serp_features": [],
            "freshness_signals": [1],
            "common_h2_topics": [],
            "search_intent": "informational",
        }

        brief = module.generate_content_brief(
            "field service scheduling",
            analysis,
            now=datetime(2026, 8, 5),
        )

        self.assertEqual(
            brief["observed_elements"],
            ["1 of 1 result titles contain a freshness signal"],
        )
        self.assertEqual(brief["structure_patterns"], [])
        self.assertIsNone(brief["recommended_word_count"])
        self.assertEqual(brief["must_have_elements"], brief["observed_elements"])
        self.assertEqual(
            brief["serp_features_to_target"],
            brief["serp_features_to_evaluate"],
        )
        self.assertEqual(
            brief["structure_recommendations"],
            brief["structure_patterns"],
        )
        serialized = json.dumps(brief)
        for unobserved_claim in [
            "Visual aids",
            "Prerequisites section",
            "Time estimate",
            "Troubleshooting tips",
            "Recent statistics and examples",
        ]:
            self.assertNotIn(unobserved_claim, serialized)

    def test_cli_parser_accepts_optional_positive_word_target(self):
        module = load_research_serp_module()

        args = module.parse_cli_args(
            ["field service scheduling", "--word-target", "1600"]
        )

        self.assertEqual(args.keyword, "field service scheduling")
        self.assertEqual(args.word_target, 1600)
        with self.assertRaises(SystemExit):
            module.parse_cli_args(["field service scheduling", "--word-target", "0"])

    def test_run_serp_analysis_rejects_blank_keyword_before_side_effects(self):
        module = load_research_serp_module()

        for keyword in ["", "   ", None]:
            with self.subTest(keyword=keyword):
                with self.assertRaisesRegex(ValueError, "keyword"):
                    module.run_serp_analysis(keyword)

    def test_cli_without_arguments_preserves_usage_success_contract(self):
        completed = subprocess.run(
            [sys.executable, str(SCRIPT_PATH)],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertEqual(completed.returncode, 0)
        self.assertIn("Usage:", completed.stdout)
        self.assertEqual(completed.stderr, "")

    def test_playwright_fallback_normalizes_visible_serp_payload_and_writes_raw_artifact(self):
        module = load_research_serp_module()

        def fake_cli_runner(keyword):
            return json.dumps(
                {
                    "search_url": "https://www.google.com/search?q=labor+burden+rate+calculator&num=10&hl=en&gl=us&pws=0",
                    "organic_results": [
                        {
                            "title": "Labor Burden Calculator",
                            "url": "https://example.com/labor-burden",
                            "description": "Calculate true labor cost.",
                        },
                        {
                            "title": "Payroll Burden Guide",
                            "url": "https://example.com/payroll-burden",
                            "description": "Payroll burden formula.",
                        },
                    ],
                    "features": ["people_also_ask", "video"],
                    "paa_questions": [
                        "How do you calculate labor burden rate?",
                        "What is a 40% payroll burden?",
                    ],
                    "blocker": None,
                }
            )

        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            result = module.run_playwright_serp_fallback(
                "labor burden rate calculator",
                output_dir=output_dir,
                now=datetime(2026, 7, 7, 9, 15),
                cli_runner=fake_cli_runner,
                npx_checker=lambda: True,
            )

            self.assertTrue(result["fallback_used"])
            self.assertIsNone(result["fallback_blocker"])
            self.assertEqual(result["organic_results"][0]["position"], 1)
            self.assertEqual(result["organic_results"][0]["source"], "playwright_google")
            self.assertEqual(result["features"], ["people_also_ask", "video"])
            self.assertEqual(
                result["paa_questions"],
                [
                    "How do you calculate labor burden rate?",
                    "What is a 40% payroll burden?",
                ],
            )

            artifact = output_dir / "serp-playwright-labor-burden-rate-calculator-2026-07-07.json"
            self.assertTrue(artifact.exists())
            raw = json.loads(artifact.read_text(encoding="utf-8"))
            self.assertEqual(raw["keyword"], "labor burden rate calculator")
            self.assertEqual(raw["locale"], {"hl": "en", "gl": "us", "pws": "0"})

    def test_playwright_fallback_records_blocker_without_inventing_results(self):
        module = load_research_serp_module()

        with tempfile.TemporaryDirectory() as temp_dir:
            result = module.run_playwright_serp_fallback(
                "blocked keyword",
                output_dir=Path(temp_dir),
                now=datetime(2026, 7, 7),
                cli_runner=lambda keyword: json.dumps(
                    {
                        "search_url": "https://www.google.com/search?q=blocked+keyword&num=10&hl=en&gl=us&pws=0",
                        "organic_results": [],
                        "features": [],
                        "paa_questions": ["Should not survive blocker"],
                        "blocker": "captcha_or_unusual_traffic",
                    }
                ),
                npx_checker=lambda: True,
            )

            self.assertTrue(result["fallback_used"])
            self.assertEqual(result["fallback_blocker"], "captcha_or_unusual_traffic")
            self.assertEqual(result["organic_results"], [])
            self.assertEqual(result["paa_questions"], [])

    def test_missing_dataforseo_credentials_uses_playwright_fallback_and_writes_report(self):
        module = load_research_serp_module()

        def fake_fallback(keyword, output_dir, now):
            return {
                "fallback_used": True,
                "fallback_blocker": None,
                "search_url": "https://www.google.com/search?q=labor+burden+rate+calculator&num=10&hl=en&gl=us&pws=0",
                "raw_artifact": str(output_dir / "serp-playwright-labor-burden-rate-calculator-2026-07-07.json"),
                "organic_results": [
                    {
                        "position": 1,
                        "title": "Labor Burden Calculator",
                        "url": "https://example.com/labor-burden",
                        "description": "Calculate true labor cost.",
                        "domain": "example.com",
                        "source": "playwright_google",
                    }
                ],
                "features": ["people_also_ask"],
                "paa_questions": ["How do you calculate labor burden rate?"],
            }

        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            result = module.run_serp_analysis(
                "labor burden rate calculator",
                output_dir=output_dir,
                now=datetime(2026, 7, 7, 9, 30),
                dataforseo_factory=lambda: FakeDataForSEO(
                    error=RuntimeError("DATAFORSEO_LOGIN and DATAFORSEO_PASSWORD must be set")
                ),
                fallback_runner=fake_fallback,
                intent_analyzer_factory=FakeIntentAnalyzer,
                content_comparator_factory=FakeContentLengthComparator,
                print_fn=lambda message="": None,
            )

            self.assertTrue(result["fallback_used"])
            self.assertIn("DATAFORSEO_LOGIN", result["dataforseo_error"])
            report = output_dir / "serp-analysis-labor-burden-rate-calculator.md"
            self.assertTrue(report.exists())
            report_text = report.read_text(encoding="utf-8")
            self.assertIn("## Playwright SERP Fallback", report_text)
            self.assertIn("DataForSEO failure reason", report_text)
            self.assertIn("browser-visible only", report_text)
            self.assertIn("How do you calculate labor burden rate?", report_text)
            self.assertIn("Competitor word counts are context only", report_text)
            self.assertIn("Unresolved until Reader Contract planning", report_text)
            self.assertNotIn("Recommended Word Count", report_text)
            self.assertNotIn("2,000+ words", report_text)

    def test_caller_word_target_is_serialized_without_serp_derived_expansion(self):
        module = load_research_serp_module()

        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            messages = []
            result = module.run_serp_analysis(
                "labor burden rate calculator",
                word_target=1600,
                output_dir=output_dir,
                now=datetime(2026, 7, 7),
                dataforseo_factory=lambda: FakeDataForSEO(
                    serp_data={
                        "organic_results": [
                            {
                                "title": "Labor Burden Guide",
                                "url": "https://example.com/labor-burden",
                                "description": "Guide",
                            },
                            {
                                "title": "Payroll Burden Guide",
                                "url": "https://example.com/payroll-burden",
                                "description": "Guide",
                            },
                        ],
                        "features": [],
                    }
                ),
                fallback_runner=lambda *args, **kwargs: {},
                intent_analyzer_factory=FakeIntentAnalyzer,
                content_comparator_factory=FakeContentLengthComparator,
                print_fn=lambda message="": messages.append(message),
            )

            self.assertEqual(result["word_target"], 1600)
            self.assertEqual(result["difference_from_observed_average"], 550)
            self.assertEqual(
                [item["word_count"] for item in result["competitor_lengths"]],
                [1200, 900],
            )
            self.assertNotIn("recommended_word_count", result)
            report_text = (
                output_dir / "serp-analysis-labor-burden-rate-calculator.md"
            ).read_text(encoding="utf-8")
            self.assertIn("Caller-Supplied Word Target:** 1,600 words", report_text)
            self.assertIn(
                "Difference From Observed Competitor Average:** +550 words",
                report_text,
            )
            self.assertIn("### Individual Competitor Counts", report_text)
            self.assertIn("Labor Burden Guide", report_text)
            self.assertNotIn("exceed average by 10%", report_text)
            for stale in ["Your content should be"]:
                self.assertNotIn(stale, report_text)
                self.assertNotIn(stale, "\n".join(messages))
            self.assertIn(
                "Match the dominant content type",
                "\n".join(messages),
            )
            self.assertIn(
                "Target the SERP features present",
                "\n".join(messages),
            )
            self.assertIn("Observed Content Pattern", report_text)
            self.assertIn("SERP Features To Evaluate", report_text)
            self.assertIn("Observed Structure Patterns", report_text)
            self.assertIn("Default Recommendation and Exception Rule", report_text)
            self.assertIn("Observation and Proof Status", report_text)
            self.assertIn("documented Reader Contract exception", report_text)
            self.assertIn("SERP Features To Evaluate", report_text)
            self.assertIn("Observed Structure Patterns", report_text)
            self.assertIn("Observation and Proof Status", report_text)
            self.assertIn("SERP Features To Evaluate", report_text)
            self.assertIn("Observed Structure Patterns", report_text)

    def test_run_serp_analysis_preserves_positional_output_dir_compatibility(self):
        module = load_research_serp_module()

        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            result = module.run_serp_analysis(
                "labor burden rate calculator",
                output_dir,
                datetime(2026, 7, 7),
                lambda: FakeDataForSEO(),
                lambda *args, **kwargs: {},
                FakeIntentAnalyzer,
                FakeContentLengthComparator,
                lambda message="": None,
            )

            self.assertIsNone(result["word_target"])
            self.assertTrue(
                (output_dir / "serp-analysis-labor-burden-rate-calculator.md").exists()
            )

    def test_top_10_report_keeps_word_counts_aligned_when_a_fetch_fails(self):
        module = load_research_serp_module()

        class SparseContentLengthComparator:
            def fetch_word_count(self, url):
                return {
                    "https://example.com/second": 1200,
                }.get(url, 0)

        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            module.run_serp_analysis(
                "field service scheduling",
                output_dir=output_dir,
                now=datetime(2026, 7, 7),
                dataforseo_factory=lambda: FakeDataForSEO(
                    serp_data={
                        "organic_results": [
                            {
                                "title": "First result",
                                "url": "https://example.com/first",
                                "description": "No count",
                            },
                            {
                                "title": "Second result",
                                "url": "https://example.com/second",
                                "description": "Has count",
                            },
                        ],
                        "features": [],
                    }
                ),
                fallback_runner=lambda *args, **kwargs: {},
                intent_analyzer_factory=FakeIntentAnalyzer,
                content_comparator_factory=SparseContentLengthComparator,
                print_fn=lambda message="": None,
            )

            report_text = (
                output_dir / "serp-analysis-field-service-scheduling.md"
            ).read_text(encoding="utf-8")
            self.assertIn("| 1 | example.com | General Article | N/A |", report_text)
            self.assertIn("| 2 | example.com | General Article | 1,200 |", report_text)

    def test_dataforseo_success_does_not_call_playwright_fallback(self):
        module = load_research_serp_module()
        fallback_called = False

        def fallback_runner(keyword, output_dir, now):
            nonlocal fallback_called
            fallback_called = True
            return {}

        with tempfile.TemporaryDirectory() as temp_dir:
            result = module.run_serp_analysis(
                "labor burden rate calculator",
                output_dir=Path(temp_dir),
                now=datetime(2026, 7, 7),
                dataforseo_factory=lambda: FakeDataForSEO(),
                fallback_runner=fallback_runner,
                intent_analyzer_factory=FakeIntentAnalyzer,
                content_comparator_factory=FakeContentLengthComparator,
                print_fn=lambda message="": None,
            )

            self.assertFalse(result.get("fallback_used", False))
            self.assertFalse(fallback_called)
            self.assertEqual(result["top_results"][0]["url"], "https://dataforseo.example/calculator")

    def test_blocked_fallback_report_does_not_invent_competitive_metrics(self):
        module = load_research_serp_module()

        def blocked_fallback(keyword, output_dir, now):
            return {
                "fallback_used": True,
                "fallback_blocker": "captcha_or_consent_or_unusual_traffic",
                "search_url": "https://www.google.com/search?q=blocked&num=10&hl=en&gl=us&pws=0",
                "raw_artifact": str(output_dir / "serp-playwright-blocked-keyword-2026-07-07.json"),
                "captured_at": "2026-07-07T09:30:00",
                "organic_results": [],
                "features": [],
                "paa_questions": [],
            }

        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            messages = []
            result = module.run_serp_analysis(
                "blocked keyword",
                output_dir=output_dir,
                now=datetime(2026, 7, 7, 9, 30),
                dataforseo_factory=lambda: FakeDataForSEO(
                    error=RuntimeError("DATAFORSEO_LOGIN and DATAFORSEO_PASSWORD must be set")
                ),
                fallback_runner=blocked_fallback,
                intent_analyzer_factory=FakeIntentAnalyzer,
                content_comparator_factory=FakeContentLengthComparator,
                print_fn=lambda message="": messages.append(message),
            )

            self.assertEqual(result["competitive_difficulty"], "unknown")
            report_text = (output_dir / "serp-analysis-blocked-keyword.md").read_text(
                encoding="utf-8"
            )
            self.assertIn("Competitive Difficulty:** UNKNOWN", report_text)
            self.assertIn("SERP-derived content brief unavailable", report_text)
            self.assertIn("Do not use SERP competitor metrics from this run", report_text)
            self.assertNotIn("Low competition - Opportunity", report_text)
            self.assertIn(
                "4. Do not use competitor rankings, PAA questions, or difficulty claims from this blocked run",
                messages,
            )
            self.assertNotIn(
                "3. Ensure your content meets/exceeds the recommended word count",
                messages,
            )

    def test_research_serp_command_documents_fallback_order(self):
        command_doc = (ROOT / ".claude" / "commands" / "research-serp.md").read_text(
            encoding="utf-8"
        )

        self.assertIn("DataForSEO", command_doc)
        self.assertIn("Playwright SERP fallback", command_doc)
        self.assertIn("documented blocker plus verified non-SERP evidence only", command_doc)


if __name__ == "__main__":
    unittest.main()
