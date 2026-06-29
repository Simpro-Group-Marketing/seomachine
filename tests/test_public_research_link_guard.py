import unittest

from data_sources.modules import public_research_link_guard
from data_sources.modules.url_validator import UrlValidationResult, UrlValidationSummary


DOL_SOURCE_MAP = """
## Source Map

- Claim: Covered employers must keep records for non-exempt workers, including hours worked each day and total hours worked each workweek. | URL: https://www.dol.gov/agencies/whd/fact-sheets/21-flsa-recordkeeping | Evidence: Records include hours worked each day and total hours worked each workweek | Status: approved | Use: recordkeeping section
"""


class PublicResearchLinkGuardTests(unittest.TestCase):
    def test_fails_when_flsa_recordkeeping_claim_has_only_sidecar_dol_proof(self):
        article = """# Draft

## Keep employee time tracking compliant

FLSA recordkeeping rules include hours worked each day and total hours worked each workweek.
"""

        findings = public_research_link_guard.check_content(
            article,
            proof_content=DOL_SOURCE_MAP,
            url_summary=UrlValidationSummary([]),
        )

        rule_ids = {finding["rule_id"] for finding in findings}
        self.assertIn("public_research_link_missing", rule_ids)
        self.assertIn("sidecar_research_requires_public_link", rule_ids)

    def test_fails_when_public_dol_link_is_manual_review(self):
        url = "https://www.dol.gov/agencies/whd/flsa"
        article = f"""# Draft

## Keep employee time tracking compliant

Use the [FLSA overview]({url}) for wage-hour recordkeeping guidance.
"""
        summary = UrlValidationSummary([
            UrlValidationResult(
                url=url,
                status="manual_review",
                status_code=403,
                reason="HTTP 403",
                line=5,
                anchor="FLSA overview",
            )
        ])

        findings = public_research_link_guard.check_content(
            article,
            proof_content=DOL_SOURCE_MAP,
            url_summary=summary,
        )

        manual = [
            finding
            for finding in findings
            if finding["rule_id"] == "manual_review_public_research_link"
        ]
        self.assertEqual(len(manual), 1)
        self.assertIn(
            "Replace this source with an equivalent resolved public source",
            manual[0]["message"],
        )
        self.assertIn(
            "Do not remove the citation without replacing it",
            manual[0]["suggestion"],
        )

    def test_passes_when_public_ecfr_replacement_link_resolves(self):
        replacement = (
            "https://www.ecfr.gov/current/title-29/subtitle-B/chapter-V/"
            "subchapter-A/part-516/subpart-A/section-516.2"
        )
        article = f"""# Draft

## Keep employee time tracking compliant

Federal [recordkeeping rules for covered employees]({replacement}) include hours worked each workday and total hours worked each workweek.
"""
        summary = UrlValidationSummary([
            UrlValidationResult(
                url=replacement,
                status="resolved",
                status_code=200,
                reason="HTTP 200",
                line=5,
                anchor="recordkeeping rules for covered employees",
            )
        ])

        findings = public_research_link_guard.check_content(
            article,
            proof_content=DOL_SOURCE_MAP,
            url_summary=summary,
        )

        self.assertEqual(findings, [])

    def test_passes_when_claim_removed_and_no_sidecar_research_is_needed(self):
        article = """# Draft

## Track time from field to payroll

Use a clear time policy, manager review, and approved hours before payroll.
"""

        findings = public_research_link_guard.check_content(
            article,
            proof_content="External research requirement: not applicable\nReason: workflow-only copy.",
            url_summary=UrlValidationSummary([]),
        )

        self.assertEqual(findings, [])

    def test_owned_clockshark_links_do_not_count_as_external_research(self):
        article = """# Draft

## Keep employee time tracking compliant

FLSA recordkeeping guidance matters for payroll records. ClockShark has [online timesheets](https://www.clockshark.com/tour/online-time-sheets).
"""
        summary = UrlValidationSummary([
            UrlValidationResult(
                url="https://www.clockshark.com/tour/online-time-sheets",
                status="resolved",
                status_code=200,
                reason="HTTP 200",
                line=5,
                anchor="online timesheets",
            )
        ])

        findings = public_research_link_guard.check_content(
            article,
            proof_content=DOL_SOURCE_MAP,
            url_summary=summary,
        )

        self.assertTrue(findings)
        self.assertIn(
            "Owned ClockShark/Simpro product links do not count",
            " ".join(str(finding.get("suggestion", "")) for finding in findings),
        )


if __name__ == "__main__":
    unittest.main()
