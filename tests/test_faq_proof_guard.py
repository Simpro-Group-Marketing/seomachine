import os
import unittest
from tempfile import NamedTemporaryFile

from data_sources.modules.faq_proof_guard import (
    check_content,
    check_file,
    should_fail,
)


def finding_ids(content):
    return {finding["rule_id"] for finding in check_content(content)}


class FaqProofGuardTests(unittest.TestCase):
    def test_faq_answer_without_linked_proof_fails(self):
        content = """# HVAC Scheduling Software

## Frequently Asked Questions

### How does HVAC scheduling software reduce missed appointments?

HVAC scheduling software reduces missed appointments by centralizing job details, technician assignments, customer notifications, and status updates. Dispatchers can see conflicts before they become failures, while technicians receive the latest job information on mobile.
"""

        findings = check_content(content)

        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["rule_id"], "faq_answer_missing_linked_proof")
        self.assertEqual(findings[0]["severity"], "error")
        self.assertEqual(
            findings[0]["question"],
            "How does HVAC scheduling software reduce missed appointments?",
        )

    def test_faq_answer_with_inline_public_proof_link_passes(self):
        content = """# HVAC Scheduling Software

## Frequently Asked Questions

### How does HVAC scheduling software reduce missed appointments?

HVAC scheduling software reduces missed appointments by centralizing job details, technician assignments, customer notifications, and status updates. Simpro's [field service scheduling software](https://www.simprogroup.com/features/scheduling) connects dispatch workflows with field updates.
"""

        self.assertEqual(check_content(content), [])

    def test_faq_answer_with_question_specific_source_map_public_url_passes(self):
        content = """---
Source Map:
- FAQ: How does HVAC scheduling software reduce missed appointments? | Claim: scheduling workflows centralize dispatch and mobile updates | Proof: https://www.simprogroup.com/features/scheduling
---

# HVAC Scheduling Software

## Frequently Asked Questions

### How does HVAC scheduling software reduce missed appointments?

HVAC scheduling software reduces missed appointments by centralizing job details, technician assignments, customer notifications, and status updates. Dispatchers can see conflicts before they become failures, while technicians receive the latest job information on mobile.
"""

        self.assertEqual(check_content(content), [])

    def test_faq_answer_with_sidecar_faq_proof_map_passes(self):
        content = """# HVAC Scheduling Software

## Frequently Asked Questions

### How does HVAC scheduling software reduce missed appointments?

HVAC scheduling software reduces missed appointments by centralizing job details, technician assignments, customer notifications, and status updates. Dispatchers can see conflicts before they become failures, while technicians receive the latest job information on mobile.
"""
        sidecar = """FAQ Proof Map
- How does HVAC scheduling software reduce missed appointments? URL: https://www.simprogroup.com/features/scheduling
"""

        self.assertEqual(check_content(content, proof_content=sidecar), [])

    def test_context_only_source_map_does_not_count_as_public_proof(self):
        content = """---
Source Map:
- FAQ: How does HVAC scheduling software reduce missed appointments? | Claim: scheduling workflows centralize dispatch and mobile updates | Proof: context/features.md
---

# HVAC Scheduling Software

## Frequently Asked Questions

### How does HVAC scheduling software reduce missed appointments?

HVAC scheduling software reduces missed appointments by centralizing job details, technician assignments, customer notifications, and status updates. Dispatchers can see conflicts before they become failures, while technicians receive the latest job information on mobile.
"""

        self.assertIn("faq_answer_missing_linked_proof", finding_ids(content))

    def test_non_faq_content_is_not_checked(self):
        content = """# HVAC Scheduling Software

## Scheduling workflows

HVAC scheduling software helps teams coordinate dispatch, job updates, and invoicing.
"""

        self.assertEqual(check_content(content), [])

    def test_check_file_and_failure_threshold(self):
        with NamedTemporaryFile("w", encoding="utf-8", suffix=".md", delete=False) as temp_file:
            temp_file.write(
                """# HVAC Scheduling Software

## Frequently Asked Questions

### Should HVAC scheduling connect to invoicing?

HVAC scheduling should connect to invoicing because completed work loses value when job details stay trapped in the field.
"""
            )
            temp_path = temp_file.name

        try:
            findings = check_file(temp_path, fail_on="error")
        finally:
            os.unlink(temp_path)

        self.assertTrue(should_fail(findings, fail_on="error"))
        self.assertFalse(should_fail(findings, fail_on="none"))


if __name__ == "__main__":
    unittest.main()
