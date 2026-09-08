import os
import unittest
from tempfile import NamedTemporaryFile

from data_sources.modules.public_artifact_guard import (
    check_content,
    check_file,
    should_fail,
)


class PublicArtifactGuardTests(unittest.TestCase):
    def test_editorial_validation_appendix_fails(self):
        content = """# Article

### Editorial Validation Appendix

```text
Metric Proof Pack
```
"""

        findings = check_content(content)

        self.assertEqual(len(findings), 2)
        self.assertEqual(findings[0]["rule_id"], "internal_validation_artifact")

    def test_proof_heading_inside_fenced_code_fails(self):
        content = """# Article

```text
PAA/FAQ Provenance
- Source: AnswerSocrates
```
"""

        findings = check_content(content)

        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["match"], "PAA/FAQ Provenance")

    def test_early_artifact_plan_heading_fails(self):
        content = """# Article

## Early Artifact Plan

- Early artifact requirement: not applicable
- Reason: internal planning note
"""

        findings = check_content(content)

        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["match"], "## Early Artifact Plan")

    def test_concrete_answer_check_heading_fails(self):
        content = """# Article

Concrete Answer Check

- Concrete answer requirement: not applicable
"""

        findings = check_content(content)

        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["match"], "Concrete Answer Check")

    def test_vault_brand_language_alignment_heading_fails(self):
        content = """# Article

## Vault Brand Language Alignment

- Status: aligned
"""

        findings = check_content(content)

        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["match"], "## Vault Brand Language Alignment")

    def test_source_routing_decision_heading_fails(self):
        content = """# Article

## Source Routing Decision

- Status: aligned
"""

        findings = check_content(content)

        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["match"], "## Source Routing Decision")

    def test_blog_strategy_contract_headings_stay_in_the_sidecar(self):
        headings = (
            "Search Intent and Format Decision",
            "Commercial Pillar and Anchor Decision",
            "Lifecycle Refresh Record",
        )

        for heading in headings:
            with self.subTest(heading=heading):
                findings = check_content(f"# Article\n\n## {heading}\n\n- Status: ready\n")
                self.assertEqual(len(findings), 1)
                self.assertEqual(findings[0]["rule_id"], "internal_validation_artifact")

    def test_author_and_reviewer_verification_headings_stay_in_the_sidecar(self):
        headings = ("Author Verification", "Reviewer Verification")

        for heading in headings:
            with self.subTest(heading=heading):
                findings = check_content(
                    f"# Article\n\n## {heading}\n\n- Status: verified\n"
                )
                self.assertEqual(len(findings), 1)
                self.assertEqual(findings[0]["rule_id"], "internal_validation_artifact")

    def test_fred_authority_selection_heading_fails(self):
        content = """# Article

## Fred Voccola Authority Selection

- Selected: [none]
"""

        findings = check_content(content)

        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["match"], "## Fred Voccola Authority Selection")

    def test_context_binding_and_trace_headings_fail(self):
        content = """# Article

## Context Binding

## Context Claim Use Map

## Discovery Trace

## Selected Resource Inventory
"""

        findings = check_content(content)

        self.assertEqual(
            [finding["match"] for finding in findings],
            [
                "## Context Binding",
                "## Context Claim Use Map",
                "## Discovery Trace",
                "## Selected Resource Inventory",
            ],
        )

    def test_context_recovery_report_heading_fails(self):
        findings = check_content(
            "# Article\n\n## Context Recovery Report\n\nInternal connector attempts."
        )

        self.assertEqual(findings[0]["match"], "## Context Recovery Report")

    def test_context_heading_variants_cannot_leak(self):
        content = """# Article

## Simpro Product Context Binding
## Context Receipt
## Context Validation Receipt
## Context Resource Inventory
## Context Discovery Trace
## Claim Use Map
## Context Pack
## Context Request
## Context Inventory
## Simpro Product Context Pack
## Context Validation
"""
        findings = check_content(content)
        matches = {finding["match"] for finding in findings}
        self.assertIn("## Simpro Product Context Binding", matches)
        self.assertIn("## Context Receipt", matches)
        self.assertIn("## Context Validation Receipt", matches)
        self.assertIn("## Context Resource Inventory", matches)
        self.assertIn("## Context Discovery Trace", matches)
        self.assertIn("## Claim Use Map", matches)
        self.assertIn("## Context Pack", matches)
        self.assertIn("## Context Request", matches)
        self.assertIn("## Context Inventory", matches)
        self.assertIn("## Simpro Product Context Pack", matches)
        self.assertIn("## Context Validation", matches)

    def test_context_pack_subsections_and_decorated_headings_cannot_leak(self):
        content = """# Article

## Approved Claim Evidence
## Constraints and Unresolved Gaps
## Retrieved Guidance
## **Context Pack**
### __Approved Claim Evidence__
## `Context Request`
## [Context Pack](#internal)
## Context Pack {#internal}
## Context Pack {.private}
## Context Pack <!-- internal -->
<h2>Context Pack</h2>
## [Approved Claim Evidence](#proof)
"""

        findings = check_content(content)
        matches = {finding["match"] for finding in findings}
        self.assertEqual(
            matches,
            {
                "## Approved Claim Evidence",
                "## Constraints and Unresolved Gaps",
                "## Retrieved Guidance",
                "## **Context Pack**",
                "### __Approved Claim Evidence__",
                "## `Context Request`",
                "## [Context Pack](#internal)",
                "## Context Pack {#internal}",
                "## Context Pack {.private}",
                "## Context Pack <!-- internal -->",
                "<h2>Context Pack</h2>",
                "## [Approved Claim Evidence](#proof)",
            },
        )

    def test_cod_editorial_review_notes_fail(self):
        content = """# Article

| Workflow | Feature | Status |
|---|---|---|
| Intake | Pulse | Roadmap. Named, not dated. 🔍 *Confirm sequencing and commercial treatment before publication* |
| Scheduling | Intelligent AI Scheduler | Delivered through RAIN. 🔍 *Confirm current Simpro availability - may now be live* |
"""

        findings = check_content(content)
        rule_ids = {finding["rule_id"] for finding in findings}

        self.assertIn("editorial_review_marker", rule_ids)
        self.assertIn("publication_confirmation_note", rule_ids)
        self.assertIn("unresolved_availability_note", rule_ids)

    def test_bracketed_editorial_labels_and_standalone_placeholders_fail(self):
        content = """# Article

[PMM REVIEW: Confirm this claim]
[COD NOTE] Recheck packaging.
[NEEDS REVIEW]

TODO
TBD: replace the source
TK
"""

        findings = check_content(content)
        rule_ids = [finding["rule_id"] for finding in findings]

        self.assertEqual(rule_ids.count("editorial_review_marker"), 3)
        self.assertEqual(rule_ids.count("draft_placeholder_note"), 3)

    def test_reader_instructions_image_placeholders_and_examples_pass(self):
        content = """# Article

Confirm the package and region before choosing a plan.

```text
[IMAGE PLACEHOLDER: Dispatch board showing a cancellation workflow]
[COD NOTE] This is a fenced example.
TODO
```

> "The source text said 'may now be live' during editorial review."
"""

        self.assertEqual(check_content(content), [])

    def test_clean_public_article_passes(self):
        content = """# Article

This is public article copy with a useful customer-facing explanation.
"""

        self.assertEqual(check_content(content), [])

    def test_check_file_and_failure_threshold(self):
        with NamedTemporaryFile("w", encoding="utf-8", suffix=".md", delete=False) as temp_file:
            temp_file.write("# Article\n\nSource Map\n")
            temp_path = temp_file.name

        try:
            findings = check_file(temp_path, fail_on="error")
        finally:
            os.unlink(temp_path)

        self.assertTrue(should_fail(findings, fail_on="error"))
        self.assertFalse(should_fail(findings, fail_on="none"))


if __name__ == "__main__":
    unittest.main()
