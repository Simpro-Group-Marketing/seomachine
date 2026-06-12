import os
import tempfile
import unittest
from pathlib import Path

from data_sources.modules.paa_provenance_guard import (
    check_content,
    check_file,
    should_fail,
)


def article_with_faq(provenance_block: str = "") -> str:
    return f"""# HVAC Scheduling Software

{provenance_block}

## Frequently Asked Questions

### What is the best way to schedule HVAC technicians?

The best way to schedule HVAC technicians is to use [field service scheduling](https://www.simprogroup.com/features/scheduling-software) that shows availability, job priority, location, and skill fit. This helps office teams assign work without overloading technicians or missing urgent calls.

### Should HVAC scheduling connect to invoicing?

HVAC scheduling should connect to invoicing because completed work loses value when job details stay trapped in the field. When technician notes and approvals flow into [field service invoicing](https://www.simprogroup.com/features/invoicing-software-for-construction), office teams can invoice faster.
"""


class PaaProvenanceGuardTests(unittest.TestCase):
    def test_no_faq_section_passes(self):
        content = """# HVAC Scheduling Software

## Scheduling workflows

HVAC scheduling software helps teams coordinate dispatch, job updates, and invoicing.
"""

        self.assertEqual(check_content(content), [])

    def test_faq_with_proof_links_but_no_provenance_fails(self):
        findings = check_content(article_with_faq())

        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["rule_id"], "paa_provenance_missing")
        self.assertEqual(findings[0]["severity"], "error")

    def test_matching_answersocrates_artifact_passes(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            artifact = root / "research" / "paa-questions-hvac-scheduling-2026-06-12.md"
            artifact.parent.mkdir()
            artifact.write_text(
                """# PAA Questions: HVAC Scheduling

**Source:** AnswerSocrates via Playwright MCP

- What is the best way to schedule HVAC technicians?
- Should HVAC scheduling connect to invoicing?
""",
                encoding="utf-8",
            )
            article = root / "drafts" / "hvac-scheduling.md"
            article.parent.mkdir()
            article.write_text(
                article_with_faq(
                    """```text
PAA/FAQ Provenance
- Source: AnswerSocrates via Playwright MCP
- Artifact: research/paa-questions-hvac-scheduling-2026-06-12.md
- Selected questions:
  - What is the best way to schedule HVAC technicians?
  - Should HVAC scheduling connect to invoicing?
```"""
                ),
                encoding="utf-8",
            )

            self.assertEqual(check_file(str(article)), [])

    def test_faq_question_missing_from_artifact_fails(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            artifact = root / "research" / "paa-questions-hvac-scheduling-2026-06-12.md"
            artifact.parent.mkdir()
            artifact.write_text(
                """# PAA Questions: HVAC Scheduling

**Source:** AnswerSocrates via Playwright MCP

- What is the best way to schedule HVAC technicians?
""",
                encoding="utf-8",
            )
            article = root / "drafts" / "hvac-scheduling.md"
            article.parent.mkdir()
            article.write_text(
                article_with_faq(
                    """```text
PAA/FAQ Provenance
- Source: AnswerSocrates via Playwright MCP
- Artifact: research/paa-questions-hvac-scheduling-2026-06-12.md
- Selected questions:
  - What is the best way to schedule HVAC technicians?
  - Should HVAC scheduling connect to invoicing?
```"""
                ),
                encoding="utf-8",
            )

            findings = check_file(str(article))

        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["rule_id"], "paa_question_missing_from_artifact")
        self.assertEqual(
            findings[0]["question"],
            "Should HVAC scheduling connect to invoicing?",
        )

    def test_missing_artifact_path_fails(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            article = Path(temp_dir) / "drafts" / "hvac-scheduling.md"
            article.parent.mkdir()
            article.write_text(
                article_with_faq(
                    """```text
PAA/FAQ Provenance
- Source: AnswerSocrates via Playwright MCP
- Artifact: research/missing-paa.md
- Selected questions:
  - What is the best way to schedule HVAC technicians?
  - Should HVAC scheduling connect to invoicing?
```"""
                ),
                encoding="utf-8",
            )

            findings = check_file(str(article))

        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["rule_id"], "paa_artifact_missing")

    def test_unsupported_source_label_fails(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            artifact = root / "research" / "paa-questions-hvac-scheduling-2026-06-12.md"
            artifact.parent.mkdir()
            artifact.write_text(
                """# PAA Questions: HVAC Scheduling

- What is the best way to schedule HVAC technicians?
- Should HVAC scheduling connect to invoicing?
""",
                encoding="utf-8",
            )
            article = root / "drafts" / "hvac-scheduling.md"
            article.parent.mkdir()
            article.write_text(
                article_with_faq(
                    """```text
PAA/FAQ Provenance
- Source: internal brainstorm
- Artifact: research/paa-questions-hvac-scheduling-2026-06-12.md
- Selected questions:
  - What is the best way to schedule HVAC technicians?
  - Should HVAC scheduling connect to invoicing?
```"""
                ),
                encoding="utf-8",
            )

            findings = check_file(str(article))

        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["rule_id"], "paa_source_unsupported")

    def test_check_file_and_failure_threshold(self):
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".md", delete=False) as temp_file:
            temp_file.write(article_with_faq())
            temp_path = temp_file.name

        try:
            findings = check_file(temp_path, fail_on="error")
        finally:
            os.unlink(temp_path)

        self.assertTrue(should_fail(findings, fail_on="error"))
        self.assertFalse(should_fail(findings, fail_on="none"))


if __name__ == "__main__":
    unittest.main()
