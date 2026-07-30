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

    def test_fred_authority_selection_heading_fails(self):
        content = """# Article

## Fred Voccola Authority Selection

- Selected: [none]
"""

        findings = check_content(content)

        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["match"], "## Fred Voccola Authority Selection")

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
