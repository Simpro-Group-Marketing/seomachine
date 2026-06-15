import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from data_sources.modules.source_support_guard import (
    check_content,
    check_file,
    fetch_source_text,
    require_source_support,
    should_fail,
)


SHAFFER_URL = "https://www.simprogroup.com/case-studies/schaffer-beacon-mechanical"
EBITDA_URL = "https://profitabilitypartners.io/what-is-ebitda-contractors/"
PDF_URL = "https://example.com/report.pdf"
G2_URL = "https://www.g2.com/products/simpro/reviews"


def fetcher_with(source_text_by_url):
    def fetcher(url):
        if url not in source_text_by_url:
            raise RuntimeError(f"missing mocked source for {url}")
        return source_text_by_url[url]

    return fetcher


class SourceSupportGuardTests(unittest.TestCase):
    def test_fetch_source_text_uses_builtin_file_cache_when_diskcache_is_unavailable(self):
        class FakeResponse:
            text = "<html><body>Visible proof text for source support.</body></html>"

            def raise_for_status(self):
                return None

        old_cwd = os.getcwd()
        with tempfile.TemporaryDirectory() as temp_dir:
            os.chdir(temp_dir)
            try:
                request = Mock(return_value=FakeResponse())
                with patch("data_sources.modules.source_support_guard.Cache", None), patch(
                    "data_sources.modules.source_support_guard.requests.get",
                    request,
                ):
                    first = fetch_source_text("https://example.com/source")
                    second = fetch_source_text("https://example.com/source")

                self.assertIn("Visible proof text", first)
                self.assertEqual(first, second)
                self.assertEqual(request.call_count, 1)
            finally:
                os.chdir(old_cwd)

    def test_contextual_case_study_link_passes_with_case_study_proof_path(self):
        content = f"""---
Customer Proof Pack:
- Case-study proof paths: Shaffer Beacon Mechanical, {SHAFFER_URL}, supported non-numeric theme: HVAC/plumbing operations perspective
---

# HVAC franchise software

[The Shaffer Beacon Mechanical case study]({SHAFFER_URL}) adds an HVAC and plumbing operator perspective to the discussion of franchise-ready field workflows.
"""

        findings = check_content(content, fetcher=fetcher_with({}))

        self.assertEqual(findings, [])

    def test_review_site_paraphrased_context_passes_with_review_experience_evidence(self):
        content = f"""---
Customer Proof Pack:
- Review-site experience evidence: G2, {G2_URL}, date checked 2026-06-09, product: Simpro, experience pattern: field workflow pain, evidence summary: reviewers discuss dispatch and field visibility, exact quote/rating approval status: not approved
---

# Field service software

Public review themes can inform a paraphrased E-E-A-T discussion of field workflow pain, without naming a reviewer or using ratings.
"""

        findings = check_content(content, fetcher=fetcher_with({}))

        self.assertEqual(findings, [])

    def test_named_customer_outcome_without_number_requires_claim_row(self):
        content = f"""---
Customer Proof Pack:
- Case-study proof paths: Shaffer Beacon Mechanical, {SHAFFER_URL}, supported non-numeric theme: centralized job data
---

# HVAC franchise software

[Shaffer Beacon Mechanical]({SHAFFER_URL}) centralized job data across office and field teams.
"""

        findings = check_content(content, fetcher=fetcher_with({}))

        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["rule_id"], "missing_strict_proof")

    def test_shaffer_60_percent_claim_fails_when_source_lacks_evidence(self):
        content = f"""---
Source Map:
- Claim: Shaffer Beacon Mechanical achieved a 60% increase in profit margin | URL: {SHAFFER_URL} | Evidence: "60% increase in profit margin" | Status: approved | Use: named customer metric
---

# HVAC franchise software

Standardized operations software is what makes brand standards enforceable. [Shaffer Beacon Mechanical]({SHAFFER_URL}), an HVAC and mechanical contractor, achieved a 60% increase in profit margin using Simpro's real-time job costing workflows.
"""

        findings = check_content(
            content,
            fetcher=fetcher_with(
                {
                    SHAFFER_URL: (
                        "Shaffer Beacon Mechanical is an HVAC & Plumbing contractor. "
                        "Simpro helped centralize data, increased profits, and can "
                        "process twice the amount of business with the same resources."
                    )
                }
            ),
        )

        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["rule_id"], "source_evidence_not_found")
        self.assertIn("60%", findings[0]["match"])

    def test_corrected_shaffer_claim_passes_with_customer_proof_pack_evidence(self):
        content = f"""---
Customer Proof Pack:
- Claim: Shaffer Beacon Mechanical can process twice the amount of business with the same resources | URL: {SHAFFER_URL} | Evidence: "We can process twice the amount of business with the same amount of resources" | Status: approved | Use: paraphrased customer outcome
---

# HVAC franchise software

Standardized operations software is what makes brand standards enforceable. [Shaffer Beacon Mechanical]({SHAFFER_URL}), an HVAC and plumbing contractor, used Simpro to centralize job data and process twice the amount of business with the same resources.
"""

        findings = check_content(
            content,
            fetcher=fetcher_with(
                {
                    SHAFFER_URL: (
                        "Simpro helped the team at Shaffer Beacon centralize all of "
                        "their data. \"We can process twice the amount of business "
                        "with the same amount of resources,\" Hrdlicka said."
                    )
                }
            ),
        )

        self.assertEqual(findings, [])

    def test_named_customer_metric_fails_when_only_source_map_approves_it(self):
        content = f"""---
Source Map:
- Claim: Shaffer Beacon Mechanical achieved a 60% increase in profit margin | URL: {SHAFFER_URL} | Evidence: "60% increase in profit margin" | Status: approved | Use: named customer metric
---

# HVAC franchise software

[Shaffer Beacon Mechanical]({SHAFFER_URL}) achieved a 60% increase in profit margin using Simpro job costing workflows.
"""

        findings = check_content(
            content,
            fetcher=fetcher_with({SHAFFER_URL: "Shaffer Beacon Mechanical achieved a 60% increase in profit margin."}),
        )

        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["rule_id"], "named_customer_metric_requires_approved_metric")

    def test_named_customer_metric_passes_with_approved_metric_row(self):
        content = f"""---
Customer Proof Pack:
- Approved metric: Shaffer Beacon Mechanical achieved a 60% increase in profit margin | Customer/brand: Shaffer Beacon Mechanical | URL: {SHAFFER_URL} | Evidence: "60% increase in profit margin" | Status: approved
---

# HVAC franchise software

[Shaffer Beacon Mechanical]({SHAFFER_URL}) achieved a 60% increase in profit margin using Simpro job costing workflows.
"""

        findings = check_content(
            content,
            fetcher=fetcher_with({SHAFFER_URL: "Shaffer Beacon Mechanical achieved a 60% increase in profit margin."}),
        )

        self.assertEqual(findings, [])

    def test_named_customer_metric_passes_with_sidecar_approved_metric_row(self):
        content = f"""# HVAC franchise software

[Shaffer Beacon Mechanical]({SHAFFER_URL}) achieved a 60% increase in profit margin using Simpro job costing workflows.
"""
        sidecar = f"""Customer Proof Pack
- Approved metric: Shaffer Beacon Mechanical achieved a 60% increase in profit margin | Customer/brand: Shaffer Beacon Mechanical | URL: {SHAFFER_URL} | Evidence: "60% increase in profit margin" | Status: approved
"""

        findings = check_content(
            content,
            proof_content=sidecar,
            fetcher=fetcher_with({SHAFFER_URL: "Shaffer Beacon Mechanical achieved a 60% increase in profit margin."}),
        )

        self.assertEqual(findings, [])

    def test_spelled_out_named_customer_metric_passes_with_approved_metric_row(self):
        bge_url = "https://www.simprogroup.com/case-studies/bge-digital"
        content = f"""---
Customer Proof Pack:
- Approved metric: BGE Digital put quotes out ten times quicker than spreadsheets | Customer/brand: BGE Digital | URL: {bge_url} | Evidence: "put a quote out ten times quicker" | Status: approved
---

# Quoting workflow

[BGE Digital]({bge_url}) put quotes out ten times quicker than spreadsheets after changing its quoting workflow.
"""

        findings = check_content(
            content,
            fetcher=fetcher_with({bge_url: "BGE Digital can put a quote out ten times quicker than spreadsheets."}),
        )

        self.assertEqual(findings, [])

    def test_ebitda_claim_passes_when_source_contains_evidence(self):
        content = f"""---
Source Map:
- Claim: HVAC operators should target 15% to 20% EBITDA margins | URL: {EBITDA_URL} | Evidence: "15% to 20% EBITDA margins" | Status: approved | Use: FAQ benchmark
---

# HVAC profitability

Well-run HVAC operators should target [15% to 20% EBITDA margins]({EBITDA_URL}) when service, replacement, and maintenance work are balanced.
"""

        findings = check_content(
            content,
            fetcher=fetcher_with({EBITDA_URL: "HVAC companies should target 15% to 20% EBITDA margins when well run."}),
        )

        self.assertEqual(findings, [])

    def test_source_that_lacks_evidence_snippet_fails(self):
        content = f"""---
Source Map:
- Claim: HVAC operators should target 15% to 20% EBITDA margins | URL: {EBITDA_URL} | Evidence: "15% to 20% EBITDA margins" | Status: approved | Use: FAQ benchmark
---

# HVAC profitability

Well-run HVAC operators should target [15% to 20% EBITDA margins]({EBITDA_URL}) when service, replacement, and maintenance work are balanced.
"""

        findings = check_content(
            content,
            fetcher=fetcher_with({EBITDA_URL: "HVAC companies need clean books and disciplined reporting."}),
        )

        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["rule_id"], "source_evidence_not_found")

    def test_context_only_proof_path_fails(self):
        content = """---
Source Map:
- Claim: Shaffer Beacon Mechanical achieved a 60% increase in profit margin | URL: context/features.md | Evidence: "60% increase in profit margin" | Status: approved | Use: named customer metric
---

# HVAC franchise software

Shaffer Beacon Mechanical achieved a 60% increase in profit margin using Simpro job costing workflows.
"""

        findings = check_content(content, fetcher=fetcher_with({}))

        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["rule_id"], "missing_strict_proof")

    def test_pdf_source_without_local_text_artifact_fails(self):
        content = f"""---
Source Map:
- Claim: Specialty trade contractors reported adjusted EBITDA margins from 18.1% to 20.4% | URL: {PDF_URL} | Evidence: "18.1% to 20.4%" | Status: approved | Use: benchmark
---

# HVAC profitability

Specialty trade contractors reported adjusted EBITDA margins from 18.1% to 20.4%.
"""

        findings = check_content(content, fetcher=fetcher_with({}))

        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["rule_id"], "unsupported_pdf_source")

    def test_pdf_source_with_local_text_artifact_passes(self):
        with tempfile.TemporaryDirectory() as tmp:
            proof = Path(tmp) / "gf-data-proof.md"
            proof.write_text("Specialty trades adjusted EBITDA margin was 18.1% to 20.4%.", encoding="utf-8")
            content = f"""---
Source Map:
- Claim: Specialty trade contractors reported adjusted EBITDA margins from 18.1% to 20.4% | URL: {PDF_URL} | Evidence: "18.1% to 20.4%" | Artifact: gf-data-proof.md | Status: approved | Use: benchmark
---

# HVAC profitability

Specialty trade contractors reported adjusted EBITDA margins from 18.1% to 20.4%.
"""

            findings = check_content(content, base_path=tmp, fetcher=fetcher_with({}))

        self.assertEqual(findings, [])

    def test_unreachable_source_fails_closed(self):
        def failing_fetcher(url):
            raise RuntimeError("timeout")

        content = f"""---
Source Map:
- Claim: HVAC operators should target 15% to 20% EBITDA margins | URL: {EBITDA_URL} | Evidence: "15% to 20% EBITDA margins" | Status: approved | Use: FAQ benchmark
---

# HVAC profitability

Well-run HVAC operators should target [15% to 20% EBITDA margins]({EBITDA_URL}) when service, replacement, and maintenance work are balanced.
"""

        findings = check_content(content, fetcher=failing_fetcher)

        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["rule_id"], "source_fetch_failed")

    def test_exact_case_study_quote_fails_without_approved_quote(self):
        content = f"""---
Customer Proof Pack:
- Case-study proof paths: Shaffer Beacon Mechanical, {SHAFFER_URL}, supported non-numeric theme: technician workflow perspective
---

# HVAC franchise software

[Shaffer Beacon Mechanical]({SHAFFER_URL}) said, "The system gives our technicians one place to work from."
"""

        findings = check_content(content, fetcher=fetcher_with({SHAFFER_URL: "The system gives our technicians one place to work from."}))

        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["rule_id"], "quote_requires_approved_quote")

    def test_exact_case_study_quote_passes_with_approved_quote(self):
        content = f"""---
Customer Proof Pack:
- Approved quote: "The system gives our technicians one place to work from." | Customer/brand: Shaffer Beacon Mechanical | Source type: case study | URL: {SHAFFER_URL} | Evidence: "The system gives our technicians one place to work from." | Status: approved | Use: exact quote
---

# HVAC franchise software

[Shaffer Beacon Mechanical]({SHAFFER_URL}) said, "The system gives our technicians one place to work from."
"""

        findings = check_content(content, fetcher=fetcher_with({SHAFFER_URL: "The system gives our technicians one place to work from."}))

        self.assertEqual(findings, [])

    def test_exact_review_quote_fails_with_only_review_experience_evidence(self):
        content = f"""---
Customer Proof Pack:
- Review-site experience evidence: G2, {G2_URL}, date checked 2026-06-09, product: Simpro, experience pattern: scheduling pain, evidence summary: reviewers mention scheduling workflows, exact quote/rating approval status: not approved
---

# Field service software

A G2 reviewer said, "Scheduling is much easier for our field team now."
"""

        findings = check_content(content, fetcher=fetcher_with({G2_URL: "Scheduling is much easier for our field team now."}))

        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["rule_id"], "quote_requires_approved_quote")

    def test_approved_quote_with_candidate_status_fails(self):
        content = f"""---
Customer Proof Pack:
- Approved quote: "The system gives our technicians one place to work from." | Customer/brand: Shaffer Beacon Mechanical | Source type: case study | URL: {SHAFFER_URL} | Evidence: "The system gives our technicians one place to work from." | Status: candidate | Use: exact quote
---

# HVAC franchise software

[Shaffer Beacon Mechanical]({SHAFFER_URL}) said, "The system gives our technicians one place to work from."
"""

        findings = check_content(content, fetcher=fetcher_with({SHAFFER_URL: "The system gives our technicians one place to work from."}))

        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["rule_id"], "quote_requires_approved_quote")

    def test_approved_quote_with_missing_source_evidence_fails(self):
        content = f"""---
Customer Proof Pack:
- Approved quote: "The system gives our technicians one place to work from." | Customer/brand: Shaffer Beacon Mechanical | Source type: case study | URL: {SHAFFER_URL} | Evidence: "The system gives our technicians one place to work from." | Status: approved | Use: exact quote
---

# HVAC franchise software

[Shaffer Beacon Mechanical]({SHAFFER_URL}) said, "The system gives our technicians one place to work from."
"""

        findings = check_content(content, fetcher=fetcher_with({SHAFFER_URL: "Shaffer Beacon Mechanical uses Simpro for HVAC and plumbing workflows."}))

        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["rule_id"], "source_evidence_not_found")

    def test_named_reviewer_ranking_language_fails_without_approved_strict_row(self):
        content = f"""---
Customer Proof Pack:
- Review-site experience evidence: G2, {G2_URL}, date checked 2026-06-09, product: Simpro, experience pattern: category comparison, evidence summary: reviewers discuss field service software options, exact quote/rating approval status: not approved
---

# Field service software

G2 reviewer Jane Smith described Simpro as a category leader for field service software.
"""

        findings = check_content(content, fetcher=fetcher_with({G2_URL: "Jane Smith described Simpro as a category leader for field service software."}))

        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["rule_id"], "missing_strict_proof")

    def test_named_reviewer_ranking_language_passes_with_approved_strict_row(self):
        content = f"""---
Customer Proof Pack:
- Claim: G2 reviewer Jane Smith described Simpro as a category leader for field service software | URL: {G2_URL} | Evidence: "Jane Smith described Simpro as a category leader for field service software" | Status: approved | Use: named reviewer claim
---

# Field service software

G2 reviewer Jane Smith described Simpro as a category leader for field service software.
"""

        findings = check_content(content, fetcher=fetcher_with({G2_URL: "Jane Smith described Simpro as a category leader for field service software."}))

        self.assertEqual(findings, [])

    def test_check_file_failure_threshold_and_require_source_support(self):
        content = f"""---
Source Map:
- Claim: HVAC operators should target 15% to 20% EBITDA margins | URL: {EBITDA_URL} | Evidence: "15% to 20% EBITDA margins" | Status: approved | Use: FAQ benchmark
---

# HVAC profitability

Well-run HVAC operators should target [15% to 20% EBITDA margins]({EBITDA_URL}) when service, replacement, and maintenance work are balanced.
"""

        with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".md", delete=False) as temp_file:
            temp_file.write(content)
            temp_path = temp_file.name

        try:
            findings = check_file(
                temp_path,
                fail_on="error",
                fetcher=fetcher_with({EBITDA_URL: "This page has no EBITDA benchmark."}),
            )
            self.assertTrue(should_fail(findings, fail_on="error"))
            self.assertFalse(should_fail(findings, fail_on="none"))
            with self.assertRaises(ValueError):
                require_source_support(
                    temp_path,
                    context="publish",
                    fetcher=fetcher_with({EBITDA_URL: "This page has no EBITDA benchmark."}),
                )
        finally:
            os.unlink(temp_path)


if __name__ == "__main__":
    unittest.main()
