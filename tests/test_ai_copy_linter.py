import os
import unittest
from tempfile import NamedTemporaryFile

from data_sources.modules.ai_copy_linter import lint_content, lint_file, should_fail


def finding_ids(content):
    return {finding["rule_id"] for finding in lint_content(content)}


class AiCopyLinterTests(unittest.TestCase):
    def test_em_dash_is_error(self):
        findings = lint_content("Dispatch looks clean" + chr(8212) + "until jobs move.")

        self.assertIn("em_dash", {finding["rule_id"] for finding in findings})
        self.assertEqual(findings[0]["severity"], "error")

    def test_semicolon_is_error(self):
        self.assertIn("semicolon", finding_ids("Dispatch is late; invoices slip."))

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

    def test_rhetorical_setup_question_is_warning(self):
        findings = lint_content("Are you tired of missed job updates? Use one job record.")

        rhetorical = [finding for finding in findings if finding["rule_id"] == "rhetorical_question"]
        self.assertEqual(len(rhetorical), 1)
        self.assertEqual(rhetorical[0]["severity"], "warning")

    def test_passive_voice_is_warning(self):
        findings = lint_content("The invoice was created after the technician left.")

        passive = [finding for finding in findings if finding["rule_id"] == "passive_voice"]
        self.assertEqual(len(passive), 1)
        self.assertEqual(passive[0]["severity"], "warning")

    def test_modal_verbs_are_warnings(self):
        findings = lint_content("Teams can assign work faster when dispatchers see capacity.")

        modal = [finding for finding in findings if finding["rule_id"] == "modal_verb"]
        self.assertEqual(len(modal), 1)
        self.assertEqual(modal[0]["severity"], "warning")

    def test_markdown_links_urls_code_and_frontmatter_are_ignored(self):
        content = """---
Meta Description: In conclusion, use this #tag
---

[In conclusion](https://example.com/not-just-but-also?tag=#field)

Visit https://example.com/not-just-but-also;done

```
This is not just code, but also a sample #tag;
```

Use one dispatch record.
"""

        self.assertEqual(lint_content(content), [])

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
