from tests.fixture_text import fixture_text

import os
import unittest
from tempfile import NamedTemporaryFile

from data_sources.modules.ai_copy_linter import lint_content, lint_file, should_fail


def finding_ids(content):
    return {finding["rule_id"] for finding in lint_content(content)}


class AiCopyLinterTests(unittest.TestCase):
    def test_chatbot_residue_from_reviewed_policy_is_error(self):
        """Removing reviewed policy-regex enforcement must make this fail."""
        findings = lint_content(
            "I hope this helps. Feel free to ask if you need another version."
        )

        residue = [
            finding
            for finding in findings
            if finding["rule_id"] == "humanizer.chatbot_residue"
        ]
        self.assertEqual(len(residue), 2)
        self.assertTrue(all(finding["severity"] == "error" for finding in residue))

    def test_chatbot_facing_offers_and_prompts_are_residue_errors(self):
        content = (
            "Should I continue? Want me to give examples? "
            "Let me know if you need anything else. You're absolutely right!"
        )

        findings = lint_content(content)
        residue = [
            finding
            for finding in findings
            if finding["rule_id"] == "humanizer.chatbot_residue"
        ]

        self.assertEqual(len(residue), 4)
        self.assertTrue(all(finding["severity"] == "error" for finding in residue))

    def test_chatbot_residue_inside_exact_quotes_is_not_style_linted(self):
        """Scanning exact quoted source text with Humanizer must make this fail."""
        content = (
            '> The reviewer wrote, "I hope this helps."\n\n'
            "The source text says "
            + chr(8220)
            + "Feel free to ask for more detail."
            + chr(8221)
        )

        findings = lint_content(content)

        self.assertNotIn(
            "humanizer.chatbot_residue",
            {finding["rule_id"] for finding in findings},
        )

    def test_chatbot_residue_inside_html_comment_is_not_style_linted(self):
        """Scanning hidden workflow comments with Humanizer must make this fail."""
        findings = lint_content("<!-- I hope this helps. -->\nThe article ends here.")

        self.assertNotIn(
            "humanizer.chatbot_residue",
            {finding["rule_id"] for finding in findings},
        )

    def test_contextual_humanizer_patterns_do_not_enter_release_linter(self):
        """Compiling advisory patterns into release findings must make this fail."""
        findings = lint_content(
            "This serves as the operating record. Let's dive in. Frankly, the handoff is late."
        )

        self.assertFalse(
            [
                finding
                for finding in findings
                if str(finding["rule_id"]).startswith("humanizer.")
            ]
        )

    def test_required_comparison_disclosure_is_not_linted_as_passive_voice(self):
        disclosure = (
            "This guide is published by AroFlo, a software provider included in this comparison. "
            "We evaluated AroFlo against the same criteria used for every other platform listed. "
            "Product information was reviewed using official vendor documentation and independent "
            "software review sources in August 2026."
        )

        self.assertEqual(lint_content(disclosure), [])

    def test_comparison_disclosure_with_appended_passive_copy_is_linted(self):
        disclosure = (
            "This guide is published by AroFlo, a software provider included in this comparison. "
            "We evaluated AroFlo against the same criteria used for every other platform listed. "
            "Product information was reviewed using official vendor documentation and independent "
            "software review sources in August 2026. The shortlist was selected by the publisher."
        )

        self.assertIn("passive_voice", finding_ids(disclosure))

    def test_standalone_original_hero_image_placeholder_is_ignored(self):
        quote = chr(34)
        content = (
            '[IMAGE PLACEHOLDER — ORIGINAL HERO: retain immediately before the '
            'introduction | source: '
            'https://www.simprogroup.com/images/2/9/6/5/f/'
            '2965fceb5942ff039f447cff8ce3cd7aee49b2f9-'
            'simpro-best-trades-for-women.jpg | alt: '
            + quote
            + 'Woman smiling in navy work overalls'
            + quote
            + ' | render target: 819 × 461 px; resize and compress before upload]'
        )

        self.assertEqual(lint_content(content), [])

    def test_incomplete_image_placeholder_does_not_bypass_copy_rules(self):
        findings = lint_content(
            "[IMAGE PLACEHOLDER: prohibited prose; editors must revise it]"
        )

        self.assertIn("semicolon", {finding["rule_id"] for finding in findings})

    def test_mixed_image_placeholder_and_prose_does_not_bypass_copy_rules(self):
        findings = lint_content(
            "[IMAGE PLACEHOLDER: hero] Teams can fabricate results; [source]"
        )

        self.assertIn("semicolon", {finding["rule_id"] for finding in findings})

    def test_image_placeholder_punctuation_in_prose_is_still_linted(self):
        findings = lint_content(
            'The production note uses an em dash — in prose; editors must revise it.'
        )

        self.assertEqual(
            {'em_dash', 'semicolon'},
            {
                finding['rule_id']
                for finding in findings
                if finding['rule_id'] in {'em_dash', 'semicolon'}
            },
        )

    def test_first_word_preposition_in_heading_is_allowed(self):
        findings = lint_content('## From Apprentice to Owner')

        self.assertNotIn(
            'title_capitalized_preposition',
            {finding['rule_id'] for finding in findings},
        )

    def test_how_can_heading_allows_modal_can(self):
        findings = lint_content('## How Women Can Start a Career in the Trades')

        self.assertNotIn(
            'modal_verb',
            {finding['rule_id'] for finding in findings},
        )

    def test_how_can_heading_does_not_hide_another_modal(self):
        findings = lint_content('## How Women Can and Should Start in the Trades')

        self.assertIn(
            'modal_verb',
            {finding['rule_id'] for finding in findings},
        )

    def test_em_dash_is_error(self):
        findings = lint_content("Dispatch looks clean" + chr(8212) + "until jobs move.")

        self.assertIn("em_dash", {finding["rule_id"] for finding in findings})
        self.assertEqual(findings[0]["severity"], "error")

    def test_semicolon_is_error(self):
        self.assertIn("semicolon", finding_ids("Dispatch is late; invoices slip."))

    def test_spelled_out_metric_words_do_not_block_lint(self):
        findings = lint_content(
            "The BGE Digital case study reports the team put quotes out ten times quicker."
        )

        number_words = [
            finding for finding in findings if finding["rule_id"] == "spelled_out_number"
        ]

        self.assertEqual(number_words, [])

    def test_restrictive_because_clause_is_not_linted(self):
        findings = lint_content("Invoices slow down because job data stays in the field.")

        self.assertEqual(findings, [])

    def test_because_comma_decisions_are_not_regex_linted(self):
        findings = lint_content(
            "Invoices did not move faster because dispatch was cleaner. They moved faster "
            "because job data reached finance on time."
        )

        self.assertEqual(findings, [])

    def test_not_just_but_also_pattern_is_error(self):
        self.assertIn(
            "not_just_but_also",
            finding_ids("This is not just scheduling, but also profit control."),
        )

    def test_banned_setup_phrase_is_error(self):
        self.assertIn(
            "setup_phrase",
            finding_ids("In conclusion, field teams need cleaner job data."),
        )

    def test_hashtag_is_error(self):
        self.assertIn("hashtag", finding_ids("Track the job before it slips. #fieldservice"))

    def test_internal_repo_context_language_is_error(self):
        content = (
            "Repo context maps TEAMWired to a payment proof point, so the rewrite can route "
            "readers to the approved internal proof path."
        )

        findings = lint_content(content)
        internal = [
            finding
            for finding in findings
            if finding["rule_id"] == "internal_process_language"
        ]

        self.assertTrue(internal)
        self.assertEqual(internal[0]["severity"], "error")

    def test_context_file_references_are_error_in_public_copy(self):
        self.assertIn(
            "internal_process_language",
            finding_ids("Use context/features.md as the source for this customer claim."),
        )

    def test_source_meta_commentary_is_error(self):
        content = (
            "That case study is useful for this topic, since it links payment speed "
            "to operational workflow."
        )

        findings = lint_content(content)
        meta = [
            finding
            for finding in findings
            if finding["rule_id"] == "source_meta_commentary"
        ]

        self.assertEqual(len(meta), 1)
        self.assertEqual(meta[0]["severity"], "error")

    def test_audience_facing_case_study_language_is_allowed(self):
        self.assertNotIn(
            "source_meta_commentary",
            finding_ids(
                "The TEAMWired case study shows how faster invoices can shorten "
                "payment time after field work is complete."
            ),
        )

    def test_named_fictional_scenario_framing_is_error(self):
        findings = lint_content(
            "Picture Marissa, an operations manager at an electrical contractor. "
            "Her estimator sends a polished quote from the office."
        )

        fictional = [
            finding
            for finding in findings
            if finding["rule_id"] == "named_fictional_scenario"
        ]

        self.assertEqual(len(fictional), 1)
        self.assertEqual(fictional[0]["severity"], "error")

    def test_imagine_and_meet_stock_named_scenarios_are_errors(self):
        content = (
            "Imagine Sarah trying to invoice from a spreadsheet.\n\n"
            "Meet Mike, a contractor who tracks job notes in email."
        )

        fictional = [
            finding
            for finding in lint_content(content)
            if finding["rule_id"] == "named_fictional_scenario"
        ]

        self.assertEqual(len(fictional), 2)

    def test_sourced_review_and_case_study_story_language_is_allowed(self):
        content = (
            "A [Capterra review from Joel A.]"
            "(https://www.capterra.com/p/10529/Simpro-Enterprise/reviews/) "
            "describes lead, quote, job, invoice, payment, QuickBooks, and mobile field work.\n\n"
            "The [Zebra Plumbing case study]"
            "(https://www.simprogroup.com/case-studies/zebra-plumbing) reports faster quoting."
        )

        self.assertNotIn("named_fictional_scenario", finding_ids(content))

    def test_multiple_links_in_one_paragraph_is_error(self):
        content = (
            "The [Federal Reserve](https://www.frbservices.org/news) reported "
            "payment changes. Teams comparing "
            "[software for trades businesses](https://www.simprogroup.com/industries) "
            "need a clear payment workflow."
        )

        findings = lint_content(content)
        multiple_links = [
            finding
            for finding in findings
            if finding["rule_id"] == "multiple_links_in_paragraph"
        ]

        self.assertEqual(len(multiple_links), 1)
        self.assertEqual(multiple_links[0]["severity"], "error")

    def test_one_link_per_paragraph_is_allowed(self):
        content = (
            "The [Federal Reserve](https://www.frbservices.org/news) reported "
            "payment changes.\n\n"
            "Teams comparing [software for trades businesses]"
            "(https://www.simprogroup.com/industries) need clear payment workflows."
        )

        self.assertNotIn("multiple_links_in_paragraph", finding_ids(content))

    def test_rhetorical_setup_question_is_warning(self):
        findings = lint_content("Are you tired of missed job updates? Use 1 job record.")

        rhetorical = [finding for finding in findings if finding["rule_id"] == "rhetorical_question"]
        self.assertEqual(len(rhetorical), 1)
        self.assertEqual(rhetorical[0]["severity"], "warning")

    def test_passive_voice_is_error(self):
        findings = lint_content("The invoice was created after the technician left.")

        passive = [finding for finding in findings if finding["rule_id"] == "passive_voice"]
        self.assertEqual(len(passive), 1)
        self.assertEqual(passive[0]["severity"], "error")

    def test_modal_verbs_are_errors(self):
        findings = lint_content("Teams can assign work faster when dispatchers see capacity.")

        modal = [finding for finding in findings if finding["rule_id"] == "modal_verb"]
        self.assertEqual(len(modal), 1)
        self.assertEqual(modal[0]["severity"], "error")

    def test_filler_words_are_errors(self):
        findings = lint_content("Dispatchers just need one job record.")

        filler = [finding for finding in findings if finding["rule_id"] == "filler_word"]
        self.assertEqual(len(filler), 1)
        self.assertEqual(filler[0]["severity"], "error")

    def test_filler_words_in_faq_question_headings_are_allowed(self):
        content = "## FAQ\n\n### Is PPC just Google Ads?\n\nNo. PPC is a pricing model."

        findings = lint_content(content)

        filler = [finding for finding in findings if finding["rule_id"] == "filler_word"]
        self.assertEqual(filler, [])

    def test_modal_verbs_in_faq_question_headings_are_allowed(self):
        content = (
            "## FAQ\n\n"
            "### Should I choose an all-in-one FSM platform or a simpler scheduling app?\n\n"
            "Choose the all-in-one platform when jobs need quoting, scheduling, dispatch, "
            "invoicing, reporting, and customer records in one workflow."
        )

        findings = lint_content(content)

        modal = [finding for finding in findings if finding["rule_id"] == "modal_verb"]
        self.assertEqual(modal, [])

    def test_vague_words_in_faq_question_headings_are_allowed(self):
        content = (
            "## FAQ\n\n"
            "### What documents are usually needed for a draw request?\n\n"
            "A draw request needs the milestone, requested amount, and inspection evidence."
        )

        findings = lint_content(content)

        vague = [finding for finding in findings if finding["rule_id"] == "vague_generalization"]
        self.assertEqual(vague, [])

    def test_passive_voice_in_faq_question_headings_is_allowed(self):
        content = (
            "## FAQ\n\n"
            "### Can a construction draw schedule be changed after the project starts?\n\n"
            "Project stakeholders change the schedule through the approved contract process."
        )

        findings = lint_content(content)

        passive = [finding for finding in findings if finding["rule_id"] == "passive_voice"]
        self.assertEqual(passive, [])

    def test_vague_generalizations_are_errors(self):
        findings = lint_content("Many teams track job outcomes after dispatch.")

        vague = [finding for finding in findings if finding["rule_id"] == "vague_generalization"]
        self.assertEqual(len(vague), 1)
        self.assertEqual(vague[0]["severity"], "error")

    def test_long_sentences_are_errors(self):
        findings = lint_content(
            "Dispatchers review lead source, customer history, service area, job type, "
            "technician capacity, route timing, estimate status, invoice status, payment "
            "status, margin risk, seasonal demand, replacement intent, office ownership, "
            "and technician availability before spend increases."
        )

        long_sentence = [
            finding for finding in findings if finding["rule_id"] == "long_sentence"
        ]
        self.assertEqual(len(long_sentence), 1)
        self.assertEqual(long_sentence[0]["severity"], "error")

    def test_repeated_sentence_starts_are_errors(self):
        findings = lint_content(
            "Lead source follows each job.\n"
            "Lead source stays visible after booking.\n"
            "Lead source links ad spend to invoices."
        )

        repeated = [
            finding
            for finding in findings
            if finding["rule_id"] == "repeated_sentence_start"
        ]
        self.assertEqual(len(repeated), 1)
        self.assertEqual(repeated[0]["severity"], "error")

    def test_repeated_sentence_starts_ignore_faq_question_headings(self):
        findings = lint_content(
            "## FAQ\n\n### What is FSM?\n\nFSM handles job delivery.\n\n"
            "### What is CRM?\n\nCRM handles relationships.\n\n"
            "### What is ERP?\n\nERP handles core business records."
        )
        self.assertFalse([finding for finding in findings if finding["rule_id"] == "repeated_sentence_start"])

    def test_markdown_links_urls_code_and_frontmatter_are_ignored(self):
        content = fixture_text("content_evidence:test_ai_copy_linter-354-1")

        self.assertEqual(lint_content(content), [])

    def test_capitalized_prepositions_in_title_fields_are_errors(self):
        content = fixture_text("content_evidence:test_ai_copy_linter-372-2")

        findings = [
            finding
            for finding in lint_content(content)
            if finding["rule_id"] == "title_capitalized_preposition"
        ]

        self.assertEqual(len(findings), 3)
        self.assertTrue(all(finding["severity"] == "error" for finding in findings))
        self.assertTrue(all(finding["match"] == "Into" for finding in findings))

    def test_lowercase_prepositions_in_title_fields_are_allowed(self):
        content = fixture_text("content_evidence:test_ai_copy_linter-391-3")

        self.assertNotIn("title_capitalized_preposition", finding_ids(content))

    def test_capitalized_prepositions_in_subheadings_are_errors(self):
        content = fixture_text("content_evidence:test_ai_copy_linter-402-4")

        findings = [
            finding
            for finding in lint_content(content)
            if finding["rule_id"] == "title_capitalized_preposition"
        ]

        self.assertEqual(
            [(finding["line"], finding["match"]) for finding in findings],
            [(1, "To"), (3, "In")],
        )

    def test_output_fields_are_present(self):
        finding = lint_content("Furthermore, teams can improve dispatch.")[0]

        self.assertEqual(
            set(finding.keys()),
            {
                "rule_id",
                "severity",
                "line",
                "column",
                "match",
                "message",
                "suggestion",
            },
        )

    def test_lint_file_and_failure_threshold(self):
        with NamedTemporaryFile("w", encoding="utf-8", suffix=".md", delete=False) as temp_file:
            temp_file.write("Dispatch is late; invoices slip.")
            temp_path = temp_file.name

        try:
            findings = lint_file(temp_path, fail_on="error")
        finally:
            os.unlink(temp_path)

        self.assertTrue(should_fail(findings, fail_on="error"))
        self.assertFalse(should_fail(findings, fail_on="none"))


if __name__ == "__main__":
    unittest.main()
