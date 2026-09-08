from tests.fixture_text import fixture_text

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
    policy = fixture_text("content_evidence:test_faq_proof_guard-37-1") if include_policy else ""
    return f"{policy}## FAQ Proof Map\n\n" + "\n".join(rows)

class FaqProofGuardTests(unittest.TestCase):

    def test_common_questions_heading_is_checked(self):
        content = faq_content(
            "What does field service software do?",
            [],
        ).replace("## Frequently Asked Questions", "## Common questions")

        findings = check_content(content)

        self.assertEqual(findings[0]["rule_id"], "faq_answer_missing_inline_proof")

    def test_unsupported_details_markup_is_blocked(self):
        content = (
            "# Guide\n\n"
            "<details><summary>What does field service software do?</summary>"
            "It coordinates work.</details>\n"
        )

        findings = check_content(content)

        self.assertEqual(findings[0]["rule_id"], "faq_structure_unsupported")


    def test_faq_answer_without_linked_proof_fails(self):


        content = fixture_text("content_evidence:test_faq_proof_guard-73-2")

        findings = check_content(content)

        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["rule_id"], "faq_answer_missing_inline_proof")
        self.assertEqual(findings[0]["severity"], "error")
        self.assertEqual(
            findings[0]["question"],
            "How does HVAC scheduling software reduce missed appointments?",
        )

    def test_faq_answer_with_inline_public_proof_link_passes(self):
        content = fixture_text("content_evidence:test_faq_proof_guard-93-3")

        self.assertEqual(check_content(content), [])

    def test_faq_answer_with_only_owned_inline_link_fails(self):
        content = fixture_text("content_evidence:test_faq_proof_guard-105-4")

        findings = check_content(content)

        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["rule_id"], "faq_answer_missing_inline_proof")

    def test_faq_answer_with_only_question_specific_source_map_fails(self):
        content = fixture_text("content_evidence:test_faq_proof_guard-120-5")

        self.assertIn("faq_answer_missing_inline_proof", finding_ids(content))

    def test_faq_answer_with_only_sidecar_faq_proof_map_fails(self):
        content = fixture_text("content_evidence:test_faq_proof_guard-137-6")
        sidecar = fixture_text("content_evidence:test_faq_proof_guard-145-7")

        findings = check_content(content, proof_content=sidecar)

        finding_ids = {finding["rule_id"] for finding in findings}
        self.assertIn("faq_answer_missing_inline_proof", finding_ids)
        self.assertIn("faq_source_policy_missing", finding_ids)

    def test_context_only_source_map_does_not_count_as_public_proof(self):
        content = fixture_text("content_evidence:test_faq_proof_guard-156-8")

        self.assertIn("faq_answer_missing_inline_proof", finding_ids(content))

    def test_non_faq_content_is_not_checked(self):
        content = fixture_text("content_evidence:test_faq_proof_guard-173-9")

        self.assertEqual(check_content(content), [])

    def test_check_file_and_failure_threshold(self):
        with NamedTemporaryFile("w", encoding="utf-8", suffix=".md", delete=False) as temp_file:
            temp_file.write(
                fixture_text("content_evidence:test_faq_proof_guard-185-11")
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
        content = fixture_text("content_evidence:test_faq_proof_guard-300-10")
        sidecar = faq_sidecar("Unused question?", [])

        self.assertEqual(check_content(content, proof_content=sidecar), [])

if __name__ == "__main__":
    unittest.main()
