from tests.fixture_text import fixture_text

import unittest

from data_sources.modules import public_research_link_guard
from data_sources.modules.url_validator import UrlValidationResult, UrlValidationSummary


DOL_SOURCE_MAP = fixture_text("content_evidence:test_public_research_link_guard-7-1")


class PublicResearchLinkGuardTests(unittest.TestCase):
    def test_fails_when_flsa_recordkeeping_claim_has_only_sidecar_dol_proof(self):
        article = fixture_text("content_evidence:test_public_research_link_guard-16-2")

        findings = public_research_link_guard.check_content(
            article,
            proof_content=DOL_SOURCE_MAP,
            url_summary=UrlValidationSummary([]),
        )

        rule_ids = {finding["rule_id"] for finding in findings}
        self.assertEqual(rule_ids, {"public_research_inline_proof_missing"})

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

        replacement_sidecar = f"""## Source Map
- Claim: Federal recordkeeping rules for covered employees include hours worked each workday and total hours worked each workweek. | Claim type: process | Source class: primary_authority | Evidence relation: directly_supports | URL: {replacement} | Evidence: "hours worked" | Status: approved
"""
        findings = public_research_link_guard.check_content(
            article,
            proof_content=replacement_sidecar,
            url_summary=summary,
        )

        self.assertEqual(findings, [])

    def test_passes_when_claim_removed_and_no_sidecar_research_is_needed(self):
        article = fixture_text("content_evidence:test_public_research_link_guard-104-3")

        findings = public_research_link_guard.check_content(
            article,
            proof_content="External research requirement: not applicable\nReason: workflow-only copy.",
            url_summary=UrlValidationSummary([]),
        )

        self.assertEqual(findings, [])

    def test_manual_not_applicable_declaration_cannot_suppress_a_legal_claim(self):
        article = """# Draft

## Renewal

Texas licenses must be renewed annually.
"""

        findings = public_research_link_guard.check_content(
            article,
            proof_content=(
                "External research requirement: not applicable\n"
                "Reason: workflow-only copy."
            ),
            url_summary=UrlValidationSummary([]),
        )

        self.assertIn(
            "public_research_inline_proof_missing",
            {finding["rule_id"] for finding in findings},
        )

    def test_owned_clockshark_links_do_not_count_as_external_research(self):
        article = fixture_text("content_evidence:test_public_research_link_guard-120-4")
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

    def test_semantic_faq_heading_is_left_to_the_faq_guard(self):
        url = "https://www.dol.gov/agencies/whd/fact-sheets/21-flsa-recordkeeping"
        article = f"""# Draft

## Questions field service leaders ask

Read the [Department of Labor overview]({url}) before setting policy.

##### Which FLSA records must covered employers keep?

FLSA recordkeeping rules include hours worked each day and total hours worked each workweek.
"""
        summary = UrlValidationSummary([
            UrlValidationResult(
                url=url,
                status="resolved",
                status_code=200,
                reason="HTTP 200",
                line=5,
                anchor="Department of Labor overview",
            )
        ])

        findings = public_research_link_guard.check_content(
            article,
            url_summary=summary,
        )

        self.assertNotIn(
            "public_research_inline_proof_missing",
            {finding["rule_id"] for finding in findings},
        )

    def test_legal_claim_requires_approved_source_in_same_paragraph(self):
        url = "https://www.ecfr.gov/current/title-29/part-516"
        article = f"""# Draft

## Keep employee time tracking compliant

Covered employers must retain wage-hour records.

The [official federal recordkeeping rules]({url}) explain the details.
"""
        sidecar = f"""## Source Map
- Claim: Covered employers must retain wage-hour records. | Claim type: process | Source class: primary_authority | Evidence relation: directly_supports | URL: {url} | Evidence: "retain records" | Status: approved
"""

        findings = public_research_link_guard.check_content(
            article,
            proof_content=sidecar,
            url_summary=UrlValidationSummary([
                UrlValidationResult(
                    url=url,
                    status="resolved",
                    status_code=200,
                    reason="HTTP 200",
                    line=7,
                    anchor="official federal recordkeeping rules",
                )
            ]),
        )

        self.assertIn(
            "public_research_inline_proof_missing",
            {finding["rule_id"] for finding in findings},
        )

    def test_legal_claim_rejects_generic_proof_anchor(self):
        url = "https://www.ecfr.gov/current/title-29/part-516"
        article = f"""# Draft

## Keep employee time tracking compliant

Covered employers must retain wage-hour records under this [source]({url}).
"""
        sidecar = f"""## Source Map
- Claim: Covered employers must retain wage-hour records. | Claim type: process | Source class: primary_authority | Evidence relation: directly_supports | URL: {url} | Evidence: "retain records" | Status: approved
"""

        findings = public_research_link_guard.check_content(
            article,
            proof_content=sidecar,
            url_summary=UrlValidationSummary([
                UrlValidationResult(
                    url=url,
                    status="resolved",
                    status_code=200,
                    reason="HTTP 200",
                    line=5,
                    anchor="source",
                )
            ]),
        )

        self.assertIn(
            "public_research_generic_proof_anchor",
            {finding["rule_id"] for finding in findings},
        )


if __name__ == "__main__":
    unittest.main()
