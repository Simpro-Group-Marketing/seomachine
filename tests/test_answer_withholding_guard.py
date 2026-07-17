import unittest

from data_sources.modules.answer_withholding_guard import (
    check_content,
    check_file,
    should_fail,
)
from data_sources.modules.artifact_detection import is_placeholder_cell


COST_FRONTMATTER = """---
title: "Plumbing Cost Benchmarks Australia"
primary_keyword: plumbing cost benchmarks
---

"""

SCHEDULE_FRONTMATTER = """---
title: "Construction Draw Schedule Explained"
primary_keyword: construction draw schedule
---

"""

NEUTRAL_FRONTMATTER = """---
title: "Field Service Job Tracking Tips"
primary_keyword: field service job tracking
---

"""


def _prose(word_count):
    words = ["planning", "crews", "dispatch", "records", "review", "work"]
    return " ".join(words[index % len(words)] for index in range(word_count))


DRAW_SCHEDULE_SCAFFOLD = """| Draw stage | Typical work included | Request trigger | Documentation to gather | % of contract sum |
|---|---|---|---|---|
| Draw 1: site prep and foundation | Permits, site work, excavation, footings, foundation, slab or crawlspace | Foundation milestone complete | Photos, permits, inspection notes, invoices, and updated schedule | Enter lender-approved value |
| Draw 2: framing and exterior shell | Framing, roof dry-in, windows, exterior doors, sheathing, and weatherproofing | Structural shell milestone complete | Photos, supplier invoices, inspection notes, and field progress report | Enter lender-approved value |
| Draw 3: mechanical, electrical, and plumbing rough-ins | HVAC, electrical, plumbing, and related rough-in work before walls close | Rough-in milestone complete | Trade inspection status, rough-in photos, invoices, and change-order log | Enter lender-approved value |
"""

FILLED_DRAW_SCHEDULE = """| Draw stage | Typical work included | % of contract sum |
|---|---|---|
| Draw 1: foundation | Site work, excavation, footings, foundation | 20% |
| Draw 2: framing | Framing, roof dry-in, windows, exterior doors | 20% |
| Draw 3: rough-ins | HVAC, electrical, and plumbing rough-in work | 10% |
| Draw 4: interior finishes | Drywall, paint, trim, and cabinetry | 25% |
| Draw 5: exterior and site | Siding, driveway, grading, and landscaping | 15% |
| Draw 6: final completion | Punch list, inspections, and certificate of occupancy | 10% |
"""

GUIDANCE_TABLE = """| Service | Typical range | Pricing notes |
|---|---|---|
| Hourly call-out | $95 to $150 | Confirm whether this includes call-out, diagnosis, parts, and GST |
| Hot water install | $1,200 to $1,800 | Use this as a market range and adjust for access and system type |
"""


def finding_ids(content, proof_content=None):
    return {
        finding["rule_id"]
        for finding in check_content(content, proof_content=proof_content)
    }


class PlaceholderScaffoldTests(unittest.TestCase):
    def test_placeholder_column_table_fails_scaffold(self):
        content = (
            SCHEDULE_FRONTMATTER
            + "# Construction Draw Schedule\n\n"
            + _prose(30)
            + " Draws run from 20% down to 10% of the contract sum.\n\n"
            + DRAW_SCHEDULE_SCAFFOLD
        )

        findings = [
            finding
            for finding in check_content(content)
            if finding["rule_id"] == "placeholder_table_scaffold"
        ]

        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["severity"], "error")
        self.assertEqual(findings[0]["match"], "Enter lender-approved value")
        self.assertIn("% of contract sum", findings[0]["message"])
        self.assertTrue(should_fail(findings, fail_on="error"))

    def test_filled_numeric_table_passes(self):
        content = (
            SCHEDULE_FRONTMATTER
            + "# Construction Draw Schedule\n\n"
            + _prose(30)
            + "\n\n"
            + FILLED_DRAW_SCHEDULE
        )

        self.assertEqual(check_content(content), [])

    def test_majority_placeholder_cells_fails(self):
        content = (
            NEUTRAL_FRONTMATTER
            + "# Field Service Job Tracking Tips\n\n"
            + _prose(30)
            + "\n\n| Field | Owner | Status |\n|---|---|---|\n| Job number | TBD | — |\n"
        )

        self.assertEqual(finding_ids(content), {"placeholder_table_scaffold"})

    def test_tbd_varies_and_empty_cells_count_as_placeholder(self):
        self.assertTrue(is_placeholder_cell("TBD"))
        self.assertTrue(is_placeholder_cell("Varies by region"))
        self.assertTrue(is_placeholder_cell(""))
        self.assertTrue(is_placeholder_cell("Enter lender-approved value"))
        self.assertTrue(is_placeholder_cell("N/A"))

    def test_guidance_cells_are_not_placeholders(self):
        self.assertFalse(
            is_placeholder_cell(
                "Confirm whether this includes call-out, diagnosis, parts, and GST"
            )
        )
        content = (
            COST_FRONTMATTER
            + "# Plumbing Cost Benchmarks\n\n"
            + "Standard rates sit around $95 to $150 per hour in most metro areas.\n\n"
            + GUIDANCE_TABLE
        )

        self.assertEqual(check_content(content), [])

    def test_scaffold_fails_even_when_sidecar_marks_not_applicable(self):
        content = (
            SCHEDULE_FRONTMATTER
            + "# Construction Draw Schedule\n\n"
            + _prose(30)
            + "\n\n"
            + DRAW_SCHEDULE_SCAFFOLD
        )
        proof_content = """## Concrete Answer Check
- Concrete answer requirement: not applicable
- Reason: Draw values are lender-specific for this audience.
"""

        self.assertEqual(
            finding_ids(content, proof_content=proof_content),
            {"placeholder_table_scaffold"},
        )


class NumericAnswerTests(unittest.TestCase):
    def test_cost_query_without_numeric_answer_fails(self):
        content = (
            COST_FRONTMATTER
            + "# Plumbing Cost Benchmarks\n\n"
            + _prose(120)
        )

        self.assertEqual(finding_ids(content), {"numeric_answer_missing"})

    def test_cost_query_with_dollar_range_in_intro_passes(self):
        content = (
            COST_FRONTMATTER
            + "# Plumbing Cost Benchmarks\n\n"
            + "Standard plumber rates commonly sit around $80 to $200 per hour.\n\n"
            + _prose(120)
        )

        self.assertEqual(check_content(content), [])

    def test_cost_query_satisfied_by_numeric_table_anywhere(self):
        content = (
            COST_FRONTMATTER
            + "# Plumbing Cost Benchmarks\n\n"
            + _prose(120)
            + "\n\n"
            + FILLED_DRAW_SCHEDULE
        )

        self.assertEqual(check_content(content), [])

    def test_untriggered_article_without_numbers_passes(self):
        content = (
            NEUTRAL_FRONTMATTER
            + "# Field Service Job Tracking Tips\n\n"
            + _prose(200)
        )

        self.assertEqual(check_content(content), [])

    def test_sidecar_not_applicable_with_reason_passes(self):
        content = (
            COST_FRONTMATTER
            + "# Plumbing Cost Benchmarks\n\n"
            + _prose(120)
        )
        proof_content = """## Concrete Answer Check
- Concrete answer requirement: not applicable
- Reason: The article covers cost drivers, and rates vary too widely for a range.
"""

        self.assertEqual(check_content(content, proof_content=proof_content), [])

    def test_sidecar_not_applicable_without_reason_fails(self):
        content = (
            COST_FRONTMATTER
            + "# Plumbing Cost Benchmarks\n\n"
            + _prose(120)
        )
        proof_content = """## Concrete Answer Check
- Concrete answer requirement: not applicable
"""

        self.assertEqual(
            finding_ids(content, proof_content=proof_content),
            {"concrete_answer_reason_missing"},
        )


class TemplateAnswerTests(unittest.TestCase):
    def test_schedule_query_without_table_or_download_fails_template_rule(self):
        content = (
            SCHEDULE_FRONTMATTER
            + "# Construction Draw Schedule\n\n"
            + "A draw schedule maps 5 to 7 payments to completed milestones.\n\n"
            + _prose(120)
        )

        self.assertEqual(finding_ids(content), {"template_answer_missing"})

    def test_schedule_query_with_download_link_passes(self):
        content = (
            SCHEDULE_FRONTMATTER
            + "# Construction Draw Schedule\n\n"
            + "A draw schedule maps 5 to 7 payments to completed milestones.\n\n"
            + _prose(120)
            + "\n\nGrab the [draw schedule template](https://example.com/files/draw-schedule.xlsx) to start.\n"
        )

        self.assertEqual(check_content(content), [])

    def test_check_file_rejects_invalid_fail_on(self):
        with self.assertRaises(ValueError):
            check_file("missing.md", fail_on="bogus")


if __name__ == "__main__":
    unittest.main()
