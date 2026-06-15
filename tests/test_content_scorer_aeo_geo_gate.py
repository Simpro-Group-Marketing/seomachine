import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from data_sources.modules.content_scorer import ContentScorer
from data_sources.modules.url_validator import UrlValidationResult, UrlValidationSummary


PAA_ARTIFACT = "research/paa-questions-hvac-scheduling-2026-05-22.md"
METRIC_ARTIFACT = "research/metric-proof-hvac-scheduling-2026-05-22.md"
PAA_PROVENANCE_BLOCK = f"""
```text
PAA/FAQ Provenance
- Source: AnswerSocrates via Playwright MCP
- Artifact: {PAA_ARTIFACT}
- Selected questions:
  - What is the best way to schedule HVAC technicians?
  - How does HVAC scheduling software reduce missed appointments?
  - Should HVAC scheduling connect to invoicing?
```
"""
METRIC_PROOF_BLOCK = f"""
```text
Metric Proof Pack
- Metric requirement: required
- Search log: Checked Simpro company proof for platform scale.
- Approved metric: Simpro supports more than 24,000 trade businesses | URL: {METRIC_ARTIFACT} | Evidence: "more than 24,000 trade businesses" | Status: approved | Use: platform scale proof
```
"""
CUSTOMER_PROOF_BLOCK = """
```text
Customer Proof Slate
- Selector command: python data_sources/modules/customer_proof_selector.py "hvac scheduling software" --proof-role theme --limit 10
- Role: metric | Top candidates: [quote-matrix-bwe-engineering-job-to-invoice] | Selected: [quote-matrix-bwe-engineering-job-to-invoice] | Rejected stronger candidates: [none]
- Role: quote | Top candidates: [quote-matrix-bwe-engineering-job-to-invoice] | Selected: [none] | Rejected stronger candidates: [none]
- Role: theme | Top candidates: [quote-matrix-bwe-engineering-job-to-invoice] | Selected: [quote-matrix-bwe-engineering-job-to-invoice] | Rejected stronger candidates: [none]

Customer Proof Pack
- Pack status: ready.
- Quote Matrix candidates: Checked Quote Matrix for HVAC scheduling proof; no exact quote selected for this test fixture.
- Case-study proof path: BWE Engineering, URL: https://www.simprogroup.com/case-studies/bwe-engineering, supported theme: job-card, invoicing, cash-flow, and field-service workflow.
- Review-site experience evidence: G2, https://www.g2.com/products/simpro/reviews, date checked 2026-06-12, product: Simpro, experience pattern: field workflow pain, evidence summary: reviewers discuss dispatch and field visibility, exact quote/rating approval status: not approved.
- Use in copy: paraphrased case-study proof only.
- Claims excluded: exact review quotes and ratings.

Customer Proof Selection Decision
- Selector command: python data_sources/modules/customer_proof_selector.py "hvac scheduling software" --proof-role theme
- Selected proof: quote-matrix-bwe-engineering-job-to-invoice | Customer: BWE Engineering | URL: https://www.simprogroup.com/case-studies/bwe-engineering | Use: field-service workflow proof
```
"""

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

[BWE Engineering](https://www.simprogroup.com/case-studies/bwe-engineering) shows how field service teams use connected workflows to improve operational control.
""" + METRIC_PROOF_BLOCK + PAA_PROVENANCE_BLOCK + CUSTOMER_PROOF_BLOCK + """

## Frequently Asked Questions

### What is the best way to schedule HVAC technicians?

The best way to schedule HVAC technicians is to use [field service scheduling](https://www.simprogroup.com/features/scheduling-software) that shows availability, job priority, location, and skill fit. This helps office teams assign work without overloading technicians or missing urgent calls. Mobile updates then keep the schedule accurate as jobs change during the day.

### How does HVAC scheduling software reduce missed appointments?

HVAC scheduling software reduces missed appointments by centralizing job details, technician assignments, customer notifications, and status updates. Dispatchers can see conflicts before they become failures, while technicians receive the latest job information through a [field service mobile app](https://www.simprogroup.com/features/field-service-mobile-app). Automated reminders also reduce no-shows and last-minute customer confusion.

### Should HVAC scheduling connect to invoicing?

HVAC scheduling should connect to invoicing because completed work loses value when job details stay trapped in the field. When technician notes, labor time, materials, and approvals flow into [field service invoicing](https://www.simprogroup.com/features/invoicing-software-for-construction), office teams can invoice faster. That reduces rework, protects cash flow, and improves job-level reporting.
"""


def write_paa_fixture(test_case: unittest.TestCase, content: str) -> str:
    temp_dir = TemporaryDirectory()
    test_case.addCleanup(temp_dir.cleanup)
    root = Path(temp_dir.name)
    artifact = root / PAA_ARTIFACT
    artifact.parent.mkdir(parents=True, exist_ok=True)
    artifact.write_text(
        "\n".join(
            [
                "# AnswerSocrates PAA Questions",
                "",
                "What is the best way to schedule HVAC technicians?",
                "How does HVAC scheduling software reduce missed appointments?",
                "Should HVAC scheduling connect to invoicing?",
            ]
        ),
        encoding="utf-8",
    )
    metric_artifact = root / METRIC_ARTIFACT
    metric_artifact.parent.mkdir(parents=True, exist_ok=True)
    metric_artifact.write_text(
        "Simpro supports more than 24,000 trade businesses worldwide.",
        encoding="utf-8",
    )
    article_path = root / "drafts" / "hvac-scheduling-software.md"
    article_path.parent.mkdir(parents=True, exist_ok=True)
    article_path.write_text(content, encoding="utf-8")
    return str(article_path)


def write_sidecar_fixture(test_case: unittest.TestCase, content: str) -> tuple[str, str]:
    article_path = Path(write_paa_fixture(test_case, content))
    sidecar_path = (
        article_path.parent.parent
        / "research"
        / f"validation-{article_path.stem}.md"
    )
    sidecar_path.write_text(METRIC_PROOF_BLOCK + PAA_PROVENANCE_BLOCK + CUSTOMER_PROOF_BLOCK, encoding="utf-8")
    return str(article_path), str(sidecar_path)


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
                source_path=write_paa_fixture(self, content),
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
                source_path=write_paa_fixture(self, COMPLIANT_ARTICLE),
            )

        self.assertTrue(result["passed"])
        self.assertGreaterEqual(result["content_quality_score"], 85)
        self.assertGreaterEqual(result["aeo_geo"]["score"], 90)
        self.assertTrue(result["quality_gates"]["content_quality"]["passed"])
        self.assertTrue(result["quality_gates"]["aeo_geo"]["passed"])
        self.assertTrue(result["quality_gates"]["metric_proof_pack"]["passed"])

    def test_proof_blocks_can_live_in_sidecar_for_scoring(self):
        scorer = ContentScorer()
        content = COMPLIANT_ARTICLE.replace(METRIC_PROOF_BLOCK, "").replace(
            PAA_PROVENANCE_BLOCK,
            "",
        )
        article_path, sidecar_path = write_sidecar_fixture(self, content)

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
                source_path=article_path,
                proof_sidecar=sidecar_path,
            )

        self.assertTrue(result["passed"])
        self.assertTrue(result["quality_gates"]["paa_provenance"]["passed"])
        self.assertTrue(result["quality_gates"]["metric_proof_pack"]["passed"])
        self.assertTrue(result["quality_gates"]["customer_proof_diversity"]["passed"])

    def test_review_story_identity_failure_blocks_content_scorer(self):
        scorer = ContentScorer()
        content = COMPLIANT_ARTICLE.replace(
            "\n[BWE Engineering](https://www.simprogroup.com/case-studies/bwe-engineering) shows how field service teams use connected workflows to improve operational control.\n",
            "\n[G2 reviews](https://www.g2.com/products/simpro/reviews) mention quote-to-invoice workflows for trade businesses.\n",
        )
        content = content.replace(METRIC_PROOF_BLOCK, "").replace(PAA_PROVENANCE_BLOCK, "")
        article_path, sidecar_path = write_sidecar_fixture(self, content)

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
                source_path=article_path,
                proof_sidecar=sidecar_path,
            )

        self.assertFalse(result["passed"])
        self.assertIn("review_story_identity", result["quality_gates"])
        self.assertFalse(result["quality_gates"]["review_story_identity"]["passed"])
        self.assertIn("Review story identity blockers detected", result["priority_fixes"][0]["issue"])

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
                source_path=write_paa_fixture(self, COMPLIANT_ARTICLE),
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
                source_path=write_paa_fixture(self, content),
            )

        self.assertFalse(result["passed"])
        self.assertIn("faq_proof", result["quality_gates"])
        self.assertFalse(result["quality_gates"]["faq_proof"]["passed"])
        self.assertIn("FAQ proof blockers detected", result["priority_fixes"][0]["issue"])

    def test_source_support_failure_blocks_content_scorer_when_enabled(self):
        scorer = ContentScorer()
        source_support_findings = [
            {
                "rule_id": "source_evidence_not_found",
                "severity": "error",
                "line": 35,
                "column": 1,
                "match": "Shaffer Beacon Mechanical achieved a 60% increase in profit margin.",
                "message": "Proof evidence was not found in the cited source.",
            }
        ]

        with patch(
            "data_sources.modules.content_scorer.check_source_support",
            return_value=source_support_findings,
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
                validate_source_support=True,
                source_path=write_paa_fixture(self, COMPLIANT_ARTICLE),
            )

        self.assertFalse(result["passed"])
        self.assertIn("source_support", result["quality_gates"])
        self.assertFalse(result["quality_gates"]["source_support"]["passed"])
        self.assertIn("Source support blockers detected", result["priority_fixes"][0]["issue"])

    def test_source_support_runs_before_url_validation_when_both_are_enabled(self):
        scorer = ContentScorer()
        call_order = []

        def fake_source_support(*args, **kwargs):
            call_order.append("source_support")
            return []

        def fake_url_validation(*args, **kwargs):
            call_order.append("url_validation")
            return UrlValidationSummary([
                UrlValidationResult(
                    url="https://www.simprogroup.com/features/scheduling-software",
                    status="resolved",
                    status_code=200,
                    reason="HTTP 200",
                )
            ])

        with patch(
            "data_sources.modules.content_scorer.check_source_support",
            side_effect=fake_source_support,
        ), patch(
            "data_sources.modules.content_scorer.validate_content_urls",
            side_effect=fake_url_validation,
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
                validate_source_support=True,
                source_path=write_paa_fixture(self, COMPLIANT_ARTICLE),
            )

        self.assertTrue(result["quality_gates"]["source_support"]["passed"])
        self.assertTrue(result["quality_gates"]["url_validation"]["passed"])
        self.assertEqual(call_order, ["source_support", "url_validation"])

    def test_paa_provenance_failure_blocks_content_scorer(self):
        scorer = ContentScorer()
        content = COMPLIANT_ARTICLE.replace(PAA_PROVENANCE_BLOCK, "")

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
                source_path=write_paa_fixture(self, content),
            )

        self.assertFalse(result["passed"])
        self.assertIn("paa_provenance", result["quality_gates"])
        self.assertFalse(result["quality_gates"]["paa_provenance"]["passed"])
        self.assertIn("PAA provenance blockers detected", result["priority_fixes"][0]["issue"])

    def test_metric_proof_pack_failure_blocks_content_scorer(self):
        scorer = ContentScorer()
        content = COMPLIANT_ARTICLE.replace(METRIC_PROOF_BLOCK, "")

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
                source_path=write_paa_fixture(self, content),
            )

        self.assertFalse(result["passed"])
        self.assertIn("metric_proof_pack", result["quality_gates"])
        self.assertFalse(result["quality_gates"]["metric_proof_pack"]["passed"])
        self.assertIn("Metric Proof Pack blockers detected", result["priority_fixes"][0]["issue"])

    def test_customer_proof_diversity_failure_blocks_content_scorer(self):
        scorer = ContentScorer()
        content = COMPLIANT_ARTICLE.replace(CUSTOMER_PROOF_BLOCK, "")

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
                source_path=write_paa_fixture(self, content),
            )

        self.assertFalse(result["passed"])
        self.assertIn("customer_proof_diversity", result["quality_gates"])
        self.assertFalse(result["quality_gates"]["customer_proof_diversity"]["passed"])
        self.assertIn("Customer proof diversity blockers detected", result["priority_fixes"][0]["issue"])


if __name__ == "__main__":
    unittest.main()
