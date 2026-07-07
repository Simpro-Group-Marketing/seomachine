import importlib.util
import json
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
