import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from data_sources.modules.metric_proof_pack_guard import (
    check_content,
    check_file,
    should_fail,
)
from data_sources.modules.numeric_claim_source_guard import check_content as check_numeric_claims


REQUIRED_FRONTMATTER = """---
title: "Best HVAC Scheduling Software"
primary_keyword: "hvac scheduling software"
---

# Best HVAC Scheduling Software

HVAC scheduling software helps contractors plan work.
"""


class MetricProofPackGuardTests(unittest.TestCase):
    def test_metric_required_article_without_pack_fails(self):
        findings = check_content(REQUIRED_FRONTMATTER)

        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["rule_id"], "metric_proof_pack_missing")
        self.assertTrue(should_fail(findings, fail_on="error"))

    def test_metric_required_article_with_no_approved_metrics_fails(self):
        content = REQUIRED_FRONTMATTER + """
```text
Metric Proof Pack
- Metric requirement: required
- Search log: Checked public case studies and found no approved metric.
- Approved metrics: none used
```
"""

        findings = check_content(content)

        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["rule_id"], "metric_proof_pack_no_approved_metrics")

    def test_approved_metric_with_matching_local_artifact_passes(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            artifact = root / "research" / "metric-source.md"
            artifact.parent.mkdir(parents=True)
            artifact.write_text(
                "Simpro supports more than 24,000 trade businesses worldwide.",
                encoding="utf-8",
            )
            article = root / "drafts" / "best-hvac-scheduling-software.md"
            content = REQUIRED_FRONTMATTER + """
```text
Metric Proof Pack
- Metric requirement: required
- Search log: Checked Simpro company proof for platform scale.
- Approved metric: Simpro supports more than 24,000 trade businesses | URL: research/metric-source.md | Evidence: "more than 24,000 trade businesses" | Status: approved | Use: platform scale proof
```
"""
            article.parent.mkdir(parents=True)
            article.write_text(content, encoding="utf-8")

            findings = check_file(str(article))

        self.assertEqual(findings, [])

    def test_approved_metric_from_sidecar_passes_clean_draft(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            artifact = root / "research" / "metric-source.md"
            artifact.parent.mkdir(parents=True)
            artifact.write_text(
                "Simpro supports more than 24,000 trade businesses worldwide.",
                encoding="utf-8",
            )
            article = root / "drafts" / "best-hvac-scheduling-software-2026-06-12.md"
            sidecar = (
                root
                / "research"
                / "validation-best-hvac-scheduling-software-2026-06-12.md"
            )
            article.parent.mkdir(parents=True)
            article.write_text(REQUIRED_FRONTMATTER, encoding="utf-8")
            sidecar.write_text(
                """
```text
Metric Proof Pack
- Metric requirement: required
- Search log: Checked Simpro company proof for platform scale.
- Approved metric: Simpro supports more than 24,000 trade businesses | URL: research/metric-source.md | Evidence: "more than 24,000 trade businesses" | Status: approved | Use: platform scale proof
```
""",
                encoding="utf-8",
            )

            findings = check_file(str(article), proof_sidecar=str(sidecar))

        self.assertEqual(findings, [])

    def test_approved_metric_missing_evidence_fails(self):
        content = REQUIRED_FRONTMATTER + """
```text
Metric Proof Pack
- Metric requirement: required
- Search log: Checked Simpro company proof for platform scale.
- Approved metric: Simpro supports more than 24,000 trade businesses | URL: research/metric-source.md | Status: approved | Use: platform scale proof
```
"""

        findings = check_content(content)

        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["rule_id"], "metric_evidence_missing")

    def test_metric_not_applicable_with_documented_reason_passes(self):
        content = """---
title: "How to Name Field Service Jobs"
primary_keyword: "field service job naming"
---

# How to Name Field Service Jobs

```text
Metric Proof Pack
- Metric requirement: not applicable
- Reason: This naming workflow article does not make comparative, performance, cost, ROI, KPI, profit, margin, pricing, or software-selection claims.
- Search log: Not required after editorial classification.
- Approved metrics: none used
```
"""

        findings = check_content(content)

        self.assertEqual(findings, [])

    def test_numeric_claim_not_covered_by_pack_still_fails_numeric_guard(self):
        content = REQUIRED_FRONTMATTER + """
```text
Metric Proof Pack
- Metric requirement: required
- Search log: Checked Simpro company proof for platform scale.
- Approved metric: Simpro supports more than 24,000 trade businesses | URL: https://example.com/proof | Evidence: "more than 24,000 trade businesses" | Status: approved | Use: platform scale proof
```

Simpro users cut admin by 40% after implementation.
"""

        numeric_findings = check_numeric_claims(content)

        self.assertEqual(len(numeric_findings), 1)
        self.assertEqual(numeric_findings[0]["rule_id"], "unsupported_numeric_claim")

    def test_public_metric_source_uses_shared_cached_source_fetcher(self):
        content = REQUIRED_FRONTMATTER + """
```text
Metric Proof Pack
- Metric requirement: required
- Search log: Checked Simpro company proof for platform scale.
- Approved metric: Simpro supports more than 24,000 trade businesses | URL: https://example.com/proof | Evidence: "more than 24,000 trade businesses" | Status: approved | Use: platform scale proof
```
"""

        with patch(
            "data_sources.modules.metric_proof_pack_guard.fetch_source_text",
            return_value="Simpro supports more than 24,000 trade businesses worldwide.",
        ) as fetch_source:
            findings = check_content(content)

        self.assertEqual(findings, [])
        fetch_source.assert_called_once_with("https://example.com/proof")


if __name__ == "__main__":
    unittest.main()
