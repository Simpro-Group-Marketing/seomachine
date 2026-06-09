import unittest
from unittest.mock import patch

from data_sources.modules.content_scorer import ContentScorer
from data_sources.modules.url_validator import UrlValidationResult, UrlValidationSummary


COMPLIANT_ARTICLE = """---
Meta Title: HVAC Scheduling Software for Contractors | Simpro
Meta Description: HVAC scheduling software helps contractors assign jobs, avoid double-booking, and keep technicians moving from one real-time calendar.
Primary Keyword: hvac scheduling software
Author: Jordan Lee
Last Updated: 2026-05-22
---

# HVAC Scheduling Software for Contractors

HVAC scheduling software helps contractors assign technicians, avoid double-booking, and keep customers updated from one real-time calendar. For growing trade businesses, the right scheduling workflow connects dispatch, mobile job details, inventory, and invoicing so office teams can protect margins without running the day from spreadsheets.

> **Key Takeaways**
> - HVAC scheduling software should show technician availability, job status, and customer commitments in one dispatch view.
> - Contractors need mobile job details so field teams can finish work without calling the office for every update.
> - The strongest scheduling workflows connect quoting, inventory, invoicing, and reporting instead of stopping at the calendar.

## What does HVAC scheduling software do?

HVAC scheduling software gives dispatchers a real-time view of technician availability, active jobs, locations, and urgent service requests. Teams use it to assign work, update schedules, send mobile job details, and notify customers when plans change. Simpro connects scheduling with quoting, inventory, invoicing, and reporting for stronger day-to-day job control.

The scheduling workflow should make the next best action clear for dispatchers, technicians, and managers. According to [Field Technologies Online](https://www.fieldtechnologiesonline.com/), field teams need real-time visibility to reduce wasted trips and missed updates.

## How should contractors choose scheduling software?

Contractors should choose scheduling software by matching the system to the work they actually run: service calls, planned maintenance, installations, and quoted project work. The best fit supports mobile updates, recurring jobs, drag-and-drop dispatch, customer notifications, and reporting that shows whether the schedule improved labor use, revenue timing, or profitability.

That means the buying process should include workflow testing, not only feature comparison. The [ACHR News](https://www.achrnews.com/) regularly covers HVAC labor constraints, which makes dispatch efficiency a practical operating issue rather than a software preference.

## Why does scheduling affect profit?

Scheduling affects profit because every missed appointment, double-booking, and underprepared site visit creates labor leakage. A strong schedule protects billable hours, keeps technicians focused on the right work, and gives managers earlier warning when jobs are slipping. For HVAC contractors, dispatch discipline shapes margin visibility before the invoice reaches accounting.

The profit impact compounds when scheduling is connected to job costing. Research from [McKinsey](https://www.mckinsey.com/) has shown that field productivity depends on better planning, tighter coordination, and faster information flow across operational teams.

[Schaffer Beacon Mechanical](https://www.simprogroup.com/case-studies/schaffer-beacon-mechanical) shows how field service teams use connected workflows to improve operational control.

## Frequently Asked Questions

### What is the best way to schedule HVAC technicians?

The best way to schedule HVAC technicians is to use [field service scheduling](https://www.simprogroup.com/features/scheduling-software) that shows availability, job priority, location, and skill fit. This helps office teams assign work without overloading technicians or missing urgent calls. Mobile updates then keep the schedule accurate as jobs change during the day.

### How does HVAC scheduling software reduce missed appointments?

HVAC scheduling software reduces missed appointments by centralizing job details, technician assignments, customer notifications, and status updates. Dispatchers can see conflicts before they become failures, while technicians receive the latest job information through a [field service mobile app](https://www.simprogroup.com/features/field-service-mobile-app). Automated reminders also reduce no-shows and last-minute customer confusion.

### Should HVAC scheduling connect to invoicing?

HVAC scheduling should connect to invoicing because completed work loses value when job details stay trapped in the field. When technician notes, labor time, materials, and approvals flow into [field service invoicing](https://www.simprogroup.com/features/invoicing-software-for-construction), office teams can invoice faster. That reduces rework, protects cash flow, and improves job-level reporting.
"""


class ContentScorerAeoGeoGateTests(unittest.TestCase):
    def test_legacy_70_score_no_longer_meets_quality_threshold(self):
        scorer = ContentScorer()

        self.assertEqual(scorer.PASS_THRESHOLD, 85)

    def test_seo_score_reads_lowercase_frontmatter_metadata(self):
        scorer = ContentScorer()
        content = COMPLIANT_ARTICLE.replace(
            "Meta Title: HVAC Scheduling Software for Contractors | Simpro",
            "meta_title: HVAC Scheduling Software for Contractors | Simpro",
        ).replace(
            "Meta Description: HVAC scheduling software helps contractors assign jobs, avoid double-booking, and keep technicians moving from one real-time calendar.",
            "meta_description: HVAC scheduling software helps contractors assign jobs, avoid double-booking, and keep technicians moving from one real-time calendar.",
        ).replace(
            "Primary Keyword: hvac scheduling software",
            "primary_keyword: hvac scheduling software",
        )

        result = scorer._score_seo(content, {})

        self.assertEqual(result["details"]["meta_title"], "HVAC Scheduling Software for Contractors | Simpro")
        self.assertEqual(result["details"]["primary_keyword"], "hvac scheduling software")
        self.assertNotIn("Missing meta title", [issue["issue"] for issue in result["issues"]])
        self.assertNotIn("Missing meta description", [issue["issue"] for issue in result["issues"]])

    def test_content_quality_can_pass_while_aeo_geo_gate_fails(self):
        scorer = ContentScorer()
        content = COMPLIANT_ARTICLE.replace(
            "HVAC scheduling software helps contractors assign technicians, avoid double-booking, and keep customers updated from one real-time calendar.",
            "Running a service business has always been complicated, and teams face more pressure every year.",
        )

        with patch.object(
            ContentScorer,
            "_score_humanity",
            return_value={"score": 100, "issues": [], "details": {}},
        ), patch.object(
            ContentScorer,
            "_score_specificity",
            return_value={"score": 100, "issues": [], "details": {}},
        ), patch.object(
            ContentScorer,
            "_score_structure_balance",
            return_value={"score": 100, "issues": [], "details": {}, "prose_ratio": 0.65},
        ), patch.object(
            ContentScorer,
            "_score_seo",
            return_value={"score": 100, "issues": [], "details": {}},
        ), patch.object(
            ContentScorer,
            "_score_readability",
            return_value={"score": 100, "issues": [], "details": {}, "flesch": 68},
        ):
            result = scorer.score(
                content,
                {"primary_keyword": "hvac scheduling software"},
            )

        self.assertFalse(result["passed"])
        self.assertGreaterEqual(result["content_quality_score"], 85)
        self.assertLess(result["aeo_geo"]["score"], 90)
        self.assertIn("aeo_geo", result["quality_gates"])
        self.assertFalse(result["quality_gates"]["aeo_geo"]["passed"])

    def test_fully_compliant_content_passes_quality_and_aeo_geo_gates(self):
        scorer = ContentScorer()

        with patch.object(
            ContentScorer,
            "_score_humanity",
            return_value={"score": 100, "issues": [], "details": {}},
        ), patch.object(
            ContentScorer,
            "_score_specificity",
            return_value={"score": 100, "issues": [], "details": {}},
        ), patch.object(
            ContentScorer,
            "_score_structure_balance",
            return_value={"score": 100, "issues": [], "details": {}, "prose_ratio": 0.65},
        ), patch.object(
            ContentScorer,
            "_score_seo",
            return_value={"score": 100, "issues": [], "details": {}},
        ), patch.object(
            ContentScorer,
            "_score_readability",
            return_value={"score": 100, "issues": [], "details": {}, "flesch": 68},
        ):
            result = scorer.score(
                COMPLIANT_ARTICLE,
                {"primary_keyword": "hvac scheduling software"},
            )

        self.assertTrue(result["passed"])
        self.assertGreaterEqual(result["content_quality_score"], 85)
        self.assertGreaterEqual(result["aeo_geo"]["score"], 90)
        self.assertTrue(result["quality_gates"]["content_quality"]["passed"])
        self.assertTrue(result["quality_gates"]["aeo_geo"]["passed"])

    def test_url_validation_failure_blocks_content_scorer_when_enabled(self):
        scorer = ContentScorer()
        blocked = UrlValidationResult(
            url="https://example.com/dead",
            status="unresolved",
            status_code=404,
            reason="HTTP 404",
            line=9,
            anchor="dead source",
        )

        with patch(
            "data_sources.modules.content_scorer.validate_content_urls",
            return_value=UrlValidationSummary([blocked]),
        ), patch.object(
            ContentScorer,
            "_score_humanity",
            return_value={"score": 100, "issues": [], "details": {}},
        ), patch.object(
            ContentScorer,
            "_score_specificity",
            return_value={"score": 100, "issues": [], "details": {}},
        ), patch.object(
            ContentScorer,
            "_score_structure_balance",
            return_value={"score": 100, "issues": [], "details": {}, "prose_ratio": 0.65},
        ), patch.object(
            ContentScorer,
            "_score_seo",
            return_value={"score": 100, "issues": [], "details": {}},
        ), patch.object(
            ContentScorer,
            "_score_readability",
            return_value={"score": 100, "issues": [], "details": {}, "flesch": 68},
        ):
            result = scorer.score(
                COMPLIANT_ARTICLE,
                {"primary_keyword": "hvac scheduling software"},
                validate_urls=True,
            )

        self.assertFalse(result["passed"])
        self.assertIn("url_validation", result["quality_gates"])
        self.assertFalse(result["quality_gates"]["url_validation"]["passed"])
        self.assertIn("URL validation blockers detected", result["priority_fixes"][0]["issue"])

    def test_faq_proof_failure_blocks_content_scorer(self):
        scorer = ContentScorer()
        content = COMPLIANT_ARTICLE.replace(
            "[field service scheduling](https://www.simprogroup.com/features/scheduling-software)",
            "a live dispatch calendar",
        ).replace(
            "[field service mobile app](https://www.simprogroup.com/features/field-service-mobile-app)",
            "mobile software",
        ).replace(
            "[field service invoicing](https://www.simprogroup.com/features/invoicing-software-for-construction)",
            "invoicing",
        )

        with patch.object(
            ContentScorer,
            "_score_humanity",
            return_value={"score": 100, "issues": [], "details": {}},
        ), patch.object(
            ContentScorer,
            "_score_specificity",
            return_value={"score": 100, "issues": [], "details": {}},
        ), patch.object(
            ContentScorer,
            "_score_structure_balance",
            return_value={"score": 100, "issues": [], "details": {}, "prose_ratio": 0.65},
        ), patch.object(
            ContentScorer,
            "_score_seo",
            return_value={"score": 100, "issues": [], "details": {}},
        ), patch.object(
            ContentScorer,
            "_score_readability",
            return_value={"score": 100, "issues": [], "details": {}, "flesch": 68},
        ):
            result = scorer.score(
                content,
                {"primary_keyword": "hvac scheduling software"},
            )

        self.assertFalse(result["passed"])
        self.assertIn("faq_proof", result["quality_gates"])
        self.assertFalse(result["quality_gates"]["faq_proof"]["passed"])
        self.assertIn("FAQ proof blockers detected", result["priority_fixes"][0]["issue"])


if __name__ == "__main__":
    unittest.main()
