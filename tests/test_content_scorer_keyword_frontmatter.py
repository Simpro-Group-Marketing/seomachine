"""Contextual keyword repetition checks that ignore frontmatter metadata."""

import unittest

from data_sources.modules.content_scorer import ContentScorer


class ContextualKeywordFrontmatterTest(unittest.TestCase):
    def test_contextual_keyword_repetition_ignores_frontmatter_metadata(self):
        content = """---
meta_title: Workplace Risk Assessment Guide
meta_description: Workplace risk assessment guidance for service teams.
primary_keyword: workplace risk assessment
---

# Workplace Risk Assessment Guide

[IMAGE PLACEHOLDER | source: original illustration; filename: workplace-risk-assessment-guide.webp | alt: "Workplace risk assessment guide" | render target: 1200x675 WebP | resize and compress before upload]

A workplace risk assessment gives a field team one practical decision.
"""

        result = ContentScorer()._score_seo(content, {})

        self.assertFalse(
            any("Contextual keyword stuffing" in issue for issue in result["critical_issues"])
        )


if __name__ == "__main__":
    unittest.main()
