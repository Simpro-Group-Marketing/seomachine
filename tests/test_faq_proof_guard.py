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


def finding_ids_with_sidecar(content, sidecar):
    return {finding["rule_id"] for finding in check_content(content, proof_content=sidecar)}




def faq_content(question, urls):
    links = " and ".join(
        f"[evidence {index + 1}]({url})" for index, url in enumerate(urls)
    )
    return f"""# Field Service Management

## Frequently Asked Questions

### {question}

Field service management coordinates off-site workers, work orders, schedules and customer service records. {links} supports this explanation.
"""


def faq_sidecar(question, rows, include_policy=True):
    policy = """## FAQ Source Policy

- Allowed source classes: neutral, non_competing_expert.
- Competitor-owned FAQ sources: prohibited.
- Status: aligned.

""" if include_policy else ""
    return f"{policy}## FAQ Proof Map\n\n" + "\n".join(rows)

class FaqProofGuardTests(unittest.TestCase):


    def test_faq_answer_without_linked_proof_fails(self):


        content = """# HVAC Scheduling Software

## Frequently Asked Questions

### How does HVAC scheduling software reduce missed appointments?

HVAC scheduling software reduces missed appointments by centralizing job details, technician assignments, customer notifications, and status updates. Dispatchers can see conflicts before they become failures, while technicians receive the latest job information on mobile.
"""

        findings = check_content(content)

        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["rule_id"], "faq_answer_missing_inline_proof")
        self.assertEqual(findings[0]["severity"], "error")
        self.assertEqual(
            findings[0]["question"],
            "How does HVAC scheduling software reduce missed appointments?",
        )

    def test_faq_answer_with_inline_public_proof_link_passes(self):
        content = """# HVAC Scheduling Software

## Frequently Asked Questions

### How does HVAC scheduling software reduce missed appointments?

HVAC scheduling software reduces missed appointments by centralizing job details, technician assignments, customer notifications, and status updates. The [field service scheduling guide](https://example.com/field-service-scheduling) connects dispatch workflows with field updates.
"""

        self.assertEqual(check_content(content), [])

    def test_faq_answer_with_only_owned_inline_link_fails(self):
        content = """# HVAC Scheduling Software

## Frequently Asked Questions

### How does HVAC scheduling software reduce missed appointments?

HVAC scheduling software reduces missed appointments by centralizing job details, technician assignments, customer notifications, and status updates. Simpro's [field service scheduling software](https://www.simprogroup.com/features/scheduling) connects dispatch workflows with field updates.
"""

        findings = check_content(content)

        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["rule_id"], "faq_answer_missing_inline_proof")

    def test_faq_answer_with_only_question_specific_source_map_fails(self):
        content = """---
Source Map:
- FAQ: How does HVAC scheduling software reduce missed appointments? | Claim: scheduling workflows centralize dispatch and mobile updates | Proof: https://www.simprogroup.com/features/scheduling
---

# HVAC Scheduling Software

## Frequently Asked Questions

### How does HVAC scheduling software reduce missed appointments?

HVAC scheduling software reduces missed appointments by centralizing job details, technician assignments, customer notifications, and status updates. Dispatchers can see conflicts before they become failures, while technicians receive the latest job information on mobile.
"""

        self.assertIn("faq_answer_missing_inline_proof", finding_ids(content))

    def test_faq_answer_with_only_sidecar_faq_proof_map_fails(self):
        content = """# HVAC Scheduling Software

## Frequently Asked Questions

### How does HVAC scheduling software reduce missed appointments?

HVAC scheduling software reduces missed appointments by centralizing job details, technician assignments, customer notifications, and status updates. Dispatchers can see conflicts before they become failures, while technicians receive the latest job information on mobile.
"""
        sidecar = """FAQ Proof Map
- How does HVAC scheduling software reduce missed appointments? URL: https://www.simprogroup.com/features/scheduling
"""

        findings = check_content(content, proof_content=sidecar)

        finding_ids = {finding["rule_id"] for finding in findings}
        self.assertIn("faq_answer_missing_inline_proof", finding_ids)
        self.assertIn("faq_source_policy_missing", finding_ids)

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

        self.assertIn("faq_answer_missing_inline_proof", finding_ids(content))

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


    def test_classified_neutral_faq_source_passes(self):
        question = "What is field service management?"
        url = "https://example.org/fsm-definition"
        sidecar = faq_sidecar(
            question,
            [
                f"- FAQ: {question} | URL: {url} | Source class: neutral | Competitor check: passed | Support: Independent definition."
            ],
        )

        self.assertEqual(check_content(faq_content(question, [url]), proof_content=sidecar), [])

    def test_classified_non_competing_expert_faq_source_passes(self):
        question = "What are AI agents good for?"
        url = "https://expert.example.org/ai-agents"
        sidecar = faq_sidecar(
            question,
            [
                f"- FAQ: {question} | URL: {url} | Source class: non_competing_expert | Competitor check: passed | Support: Expert workflow guidance."
            ],
        )

        self.assertEqual(check_content(faq_content(question, [url]), proof_content=sidecar), [])

    def test_classified_faq_source_requires_an_allowed_source_class(self):
        question = "What is field service management?"
        url = "https://example.org/fsm-definition"
        sidecar = faq_sidecar(
            question,
            [
                f"- FAQ: {question} | URL: {url} | Competitor check: passed | Support: Independent definition."
            ],
        )

        self.assertIn(
            "faq_answer_source_class_missing",
            finding_ids_with_sidecar(faq_content(question, [url]), sidecar),
        )

    def test_unlisted_visible_faq_source_fails_even_when_another_source_is_classified(self):
        question = "What is field service management?"
        classified_url = "https://example.org/fsm-definition"
        unlisted_url = "https://example.net/fsm-guide"
        sidecar = faq_sidecar(
            question,
            [
                f"- FAQ: {question} | URL: {classified_url} | Source class: neutral | Competitor check: passed | Support: Independent definition."
            ],
        )

        self.assertIn(
            "faq_answer_source_map_url_missing",
            finding_ids_with_sidecar(
                faq_content(question, [classified_url, unlisted_url]),
                sidecar,
            ),
        )

    def test_competitor_owned_faq_source_fails_even_with_a_neutral_source(self):
        question = "What is field service management?"
        neutral_url = "https://example.org/fsm-definition"
        competitor_url = "https://competitor.example.com/fsm"
        sidecar = faq_sidecar(
            question,
            [
                f"- FAQ: {question} | URL: {neutral_url} | Source class: neutral | Competitor check: passed | Support: Independent definition.",
                f"- FAQ: {question} | URL: {competitor_url} | Source class: competitor_owned | Competitor check: failed | Support: Vendor documentation is prohibited.",
            ],
        )

        self.assertIn(
            "faq_answer_competitor_owned_source",
            finding_ids_with_sidecar(
                faq_content(question, [neutral_url, competitor_url]),
                sidecar,
            ),
        )

    def test_faq_source_policy_is_required_when_a_sidecar_is_supplied(self):
        question = "What is field service management?"
        url = "https://example.org/fsm-definition"
        sidecar = faq_sidecar(
            question,
            [
                f"- FAQ: {question} | URL: {url} | Source class: neutral | Competitor check: passed | Support: Independent definition."
            ],
            include_policy=False,
        )

        self.assertIn(
            "faq_source_policy_missing",
            finding_ids_with_sidecar(faq_content(question, [url]), sidecar),
        )

    def test_non_faq_comparison_sources_are_unaffected(self):
        content = """# Field Service Management

## Comparison

Vendor documentation may appear in a comparison section when it supports a vendor-specific claim: [competitor documentation](https://competitor.example.com/fsm).
"""
        sidecar = faq_sidecar("Unused question?", [])

        self.assertEqual(check_content(content, proof_content=sidecar), [])

if __name__ == "__main__":
    unittest.main()
