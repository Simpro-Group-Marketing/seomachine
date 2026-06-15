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
