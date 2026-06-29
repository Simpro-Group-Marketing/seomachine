import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from data_sources.modules.aeo_geo_rater import _check_faq_questions, rate_aeo_geo


PAA_ARTIFACT = "research/paa-questions-hvac-scheduling-2026-05-22.md"
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
""" + PAA_PROVENANCE_BLOCK + """

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
    article_path = root / "drafts" / "hvac-scheduling-software.md"
    article_path.parent.mkdir(parents=True, exist_ok=True)
    article_path.write_text(content, encoding="utf-8")
    return str(article_path)


class AeoGeoRaterTests(unittest.TestCase):
    def rate(self, content: str = COMPLIANT_ARTICLE):
        return rate_aeo_geo(
            content,
            {"primary_keyword": "hvac scheduling software"},
            source_path=write_paa_fixture(self, content),
        )

    def test_compliant_article_passes_90_point_gate(self):
        result = self.rate()

        self.assertTrue(result["passed"])
        self.assertGreaterEqual(result["score"], 90)
        self.assertTrue(result["checks"]["direct_answer"]["passed"])
        self.assertTrue(result["checks"]["capsule_coverage"]["passed"])
        self.assertTrue(result["checks"]["faq_questions"]["passed"])
        self.assertTrue(result["checks"]["eeat_proof"]["passed"])
        self.assertTrue(result["checks"]["paa_provenance"]["passed"])

    def test_faq_question_gate_allows_six_natural_language_questions(self):
        content = """## FAQ

### What is field service management software?

Answer.

### Who uses field service management software?

Answer.

### How does field service management software help dispatch?

Answer.

### How much does field service management software cost?

Answer.

### Which field service management software fits growing contractors?

Answer.

### Should I choose an all-in-one FSM platform or a simpler scheduling app?

Answer.
"""

        result = _check_faq_questions(content)

        self.assertTrue(result["passed"])
        self.assertEqual(result["details"]["question_count"], 6)

    def test_paa_provenance_can_live_in_sidecar(self):
        content = COMPLIANT_ARTICLE.replace(PAA_PROVENANCE_BLOCK, "")

        result = rate_aeo_geo(
            content,
            {"primary_keyword": "hvac scheduling software"},
            source_path=write_paa_fixture(self, content),
            proof_sidecar_content=PAA_PROVENANCE_BLOCK,
        )

        self.assertTrue(result["checks"]["paa_provenance"]["passed"])
        self.assertTrue(result["passed"])

    def test_eeat_detects_case_study_experience_and_author_expertise(self):
        result = self.rate()

        details = result["checks"]["eeat_proof"]["details"]

        self.assertTrue(result["checks"]["eeat_proof"]["passed"])
        self.assertTrue(details["case_study_links"])
        self.assertIn("case_study_link", details["experience_signals"])
        self.assertIn("author_metadata", details["expertise_signals"])

    def test_eeat_detects_clockshark_case_study_and_workflow_links(self):
        content = COMPLIANT_ARTICLE.replace(
            "https://www.simprogroup.com/case-studies/schaffer-beacon-mechanical",
            "https://www.clockshark.com/resources/case-study-underground-contractors",
        ).replace(
            "https://www.simprogroup.com/features/scheduling-software",
            "https://www.clockshark.com/tour/job-management",
        )

        result = self.rate(content)
        details = result["checks"]["eeat_proof"]["details"]

        self.assertTrue(result["checks"]["eeat_proof"]["passed"])
        self.assertIn(
            "https://www.clockshark.com/resources/case-study-underground-contractors",
            details["case_study_links"],
        )
        self.assertIn("case_study_link", details["experience_signals"])
        self.assertIn(
            "https://www.clockshark.com/tour/job-management",
            details["clockshark_workflow_links"],
        )
        self.assertIn("clockshark_product_or_workflow_link", details["expertise_signals"])

    def test_eeat_fails_when_external_research_has_no_experience_signal(self):
        content = COMPLIANT_ARTICLE.replace(
            "\n[Schaffer Beacon Mechanical](https://www.simprogroup.com/case-studies/schaffer-beacon-mechanical) shows how field service teams use connected workflows to improve operational control.\n",
            "\nThe article uses public research to explain scheduling workflows.\n",
        )

        result = self.rate(content)

        self.assertFalse(result["checks"]["eeat_proof"]["passed"])
        self.assertFalse(result["passed"])
        self.assertIn("eeat_proof", {issue["check"] for issue in result["issues"]})
        self.assertIn(
            "review-site experience evidence",
            result["checks"]["eeat_proof"]["fix"],
        )

    def test_eeat_fails_when_case_study_has_no_expertise_signal(self):
        content = COMPLIANT_ARTICLE.replace("Author: Jordan Lee\n", "")
        content = content.replace("Last Updated: 2026-05-22\n", "Last Updated: 2026-05-22\n")
        content = content.replace("Simpro connects", "The platform connects")
        content = content.replace(
            "https://www.simprogroup.com/features/scheduling-software",
            "https://www.fieldtechnologiesonline.com/",
        ).replace(
            "https://www.simprogroup.com/features/field-service-mobile-app",
            "https://www.achrnews.com/",
        ).replace(
            "https://www.simprogroup.com/features/invoicing-software-for-construction",
            "https://www.mckinsey.com/",
        )

        result = self.rate(content)

        details = result["checks"]["eeat_proof"]["details"]

        self.assertTrue(details["case_study_links"])
        self.assertFalse(details["expertise_signals"])
        self.assertFalse(result["checks"]["eeat_proof"]["passed"])

    def test_generic_review_site_link_without_story_selection_does_not_satisfy_experience(self):
        content = COMPLIANT_ARTICLE.replace(
            "\n[Schaffer Beacon Mechanical](https://www.simprogroup.com/case-studies/schaffer-beacon-mechanical) shows how field service teams use connected workflows to improve operational control.\n",
            "\n[G2 reviews](https://www.g2.com/products/simpro/reviews) mention field workflow visibility themes for trade businesses.\n",
        )

        result = self.rate(content)

        details = result["checks"]["eeat_proof"]["details"]

        self.assertFalse(result["checks"]["eeat_proof"]["passed"])
        self.assertTrue(details["review_site_links"])
        self.assertNotIn("review_site_link", details["experience_signals"])
        self.assertIn("review_story_selection", result["checks"]["eeat_proof"]["fix"])

    def test_identity_backed_review_story_selection_satisfies_experience(self):
        content = COMPLIANT_ARTICLE.replace(
            "\n[Schaffer Beacon Mechanical](https://www.simprogroup.com/case-studies/schaffer-beacon-mechanical) shows how field service teams use connected workflows to improve operational control.\n",
            "\n[Megan B's Capterra review](https://www.capterra.com/p/10529/Simpro-Enterprise/reviews/) describes a service business using Simpro for service jobs, recurring jobs, quotes, invoices, and QBO integration.\n",
        )
        proof_sidecar = PAA_PROVENANCE_BLOCK + """
```text
Review Story Selection
- Article title: HVAC Scheduling Software for Contractors
- Content objective: explain connected field-service workflows
- Selected story: review-capterra-megan-qbo-quotes | Identity: Megan B | Platform: Capterra | URL: https://www.capterra.com/p/10529/Simpro-Enterprise/reviews/ | Workflow story: owner describes service jobs, recurring jobs, quotes, invoices, and QBO integration | Status: approved | Use: E-E-A-T experience story
- Article link requirement: same paragraph as review-derived paraphrase must link to the selected public review URL
```
"""

        result = rate_aeo_geo(
            content,
            {"primary_keyword": "hvac scheduling software"},
            source_path=write_paa_fixture(self, content),
            proof_sidecar_content=proof_sidecar,
        )

        details = result["checks"]["eeat_proof"]["details"]

        self.assertTrue(result["checks"]["eeat_proof"]["passed"])
        self.assertTrue(details["review_site_links"])
        self.assertIn("review_story_selection", details["experience_signals"])

    def test_clockshark_sidecar_experience_proof_and_workflow_links_satisfy_eeat(self):
        content = COMPLIANT_ARTICLE.replace(
            "Meta Title: HVAC Scheduling Software for Contractors | Simpro",
            "Meta Title: Construction Draw Schedule Explained",
        ).replace(
            "Primary Keyword: hvac scheduling software",
            "Primary Keyword: construction draw schedule",
        ).replace(
            "Author: Jordan Lee",
            "Author: ClockShark Editorial Team",
        ).replace(
            "\n[Schaffer Beacon Mechanical](https://www.simprogroup.com/case-studies/schaffer-beacon-mechanical) shows how field service teams use connected workflows to improve operational control.\n",
            "\nClockShark's [job management tools](https://www.clockshark.com/tour/job-management) show active jobs, completed work hours, and job stages in one place.\n",
        ).replace(
            "https://www.simprogroup.com/features/scheduling-software",
            "https://www.clockshark.com/industries/construction-trades",
        )
        proof_sidecar = PAA_PROVENANCE_BLOCK + """
```text
E-E-A-T Proof Map
- Experience proof: The rewrite uses first-party ClockShark workflow evidence from https://www.clockshark.com/blog/construction-draw-schedule and https://www.clockshark.com/tour/job-management. No customer quote, customer metric, or review story appears in public copy.
- Expertise proof: The rewrite uses source-backed workflow explanation plus ClockShark construction and job-management pages.
```
"""

        result = rate_aeo_geo(
            content,
            {"primary_keyword": "construction draw schedule"},
            source_path=write_paa_fixture(self, content),
            proof_sidecar_content=proof_sidecar,
        )

        details = result["checks"]["eeat_proof"]["details"]

        self.assertTrue(result["checks"]["eeat_proof"]["passed"])
        self.assertIn("sidecar_experience_proof", details["experience_signals"])
        self.assertIn("clockshark_product_or_workflow_link", details["expertise_signals"])

    def test_delayed_answer_fails_direct_answer_check(self):
        content = COMPLIANT_ARTICLE.replace(
            "HVAC scheduling software helps contractors assign technicians, avoid double-booking, and keep customers updated from one real-time calendar.",
            "Running a service business has always been complicated, and teams face more pressure every year.",
        )

        result = self.rate(content)

        self.assertFalse(result["passed"])
        self.assertFalse(result["checks"]["direct_answer"]["passed"])
        self.assertLess(result["score"], 90)

    def test_low_capsule_coverage_blocks_publishing(self):
        content = COMPLIANT_ARTICLE.replace(
            "HVAC scheduling software gives dispatchers a real-time view of technician availability, active jobs, locations, and urgent service requests. Teams use it to assign work, update schedules, send mobile job details, and notify customers when plans change. Simpro connects scheduling with quoting, inventory, invoicing, and reporting for stronger day-to-day job control.",
            "This section explains scheduling in more detail.",
        ).replace(
            "Contractors should choose scheduling software by matching the system to the work they actually run: service calls, planned maintenance, installations, and quoted project work. The best fit supports mobile updates, recurring jobs, drag-and-drop dispatch, customer notifications, and reporting that shows whether the schedule improved labor use, revenue timing, or profitability.",
            "This section explains selection criteria in more detail.",
        )

        result = self.rate(content)

        self.assertFalse(result["checks"]["capsule_coverage"]["passed"])
        self.assertLess(result["score"], 90)

    def test_faq_answers_outside_40_to_60_words_fail(self):
        content = COMPLIANT_ARTICLE.replace(
            "The best way to schedule HVAC technicians is to use [field service scheduling](https://www.simprogroup.com/features/scheduling-software) that shows availability, job priority, location, and skill fit. This helps office teams assign work without overloading technicians or missing urgent calls. Mobile updates then keep the schedule accurate as jobs change during the day.",
            "Use [field service scheduling](https://www.simprogroup.com/features/scheduling-software).",
        )

        result = self.rate(content)

        self.assertFalse(result["checks"]["faq_answer_length"]["passed"])
        self.assertEqual(result["score"], 90)
        self.assertFalse(result["passed"])

    def test_missing_metadata_and_external_links_fail(self):
        content = COMPLIANT_ARTICLE.replace("Author: Jordan Lee\n", "").replace(
            "Last Updated: 2026-05-22\n", ""
        )
        content = content.replace("(https://www.fieldtechnologiesonline.com/)", "()")
        content = content.replace("(https://www.achrnews.com/)", "()")
        content = content.replace("(https://www.mckinsey.com/)", "()")
        content = content.replace("(https://www.simprogroup.com/features/scheduling-software)", "()")
        content = content.replace("(https://www.simprogroup.com/features/field-service-mobile-app)", "()")
        content = content.replace("(https://www.simprogroup.com/features/invoicing-software-for-construction)", "()")

        result = self.rate(content)

        self.assertFalse(result["checks"]["external_sources"]["passed"])
        self.assertFalse(result["checks"]["metadata"]["passed"])
        self.assertLess(result["score"], 90)

    def test_faq_without_linked_proof_blocks_aeo_geo_gate(self):
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

        result = self.rate(content)

        self.assertFalse(result["checks"]["faq_proof"]["passed"])
        self.assertFalse(result["passed"])
        self.assertIn("faq_proof", {issue["check"] for issue in result["issues"]})

    def test_faq_without_paa_provenance_blocks_aeo_geo_gate(self):
        content = COMPLIANT_ARTICLE.replace(PAA_PROVENANCE_BLOCK, "")

        result = self.rate(content)

        self.assertFalse(result["checks"]["paa_provenance"]["passed"])
        self.assertFalse(result["passed"])
        self.assertIn("paa_provenance", {issue["check"] for issue in result["issues"]})


if __name__ == "__main__":
    unittest.main()
