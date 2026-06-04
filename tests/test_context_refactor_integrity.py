import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONTEXT = ROOT / "context"


class ContextRefactorIntegrityTests(unittest.TestCase):
    def test_top_level_context_files_have_standard_header_fields(self):
        required_fields = [
            "**Purpose:**",
            "**Use when:**",
            "**Owns:**",
            "**Does not own:**",
            "**Source boundary:**",
            "**Refresh cadence:**",
            "**Reference detail:**",
        ]

        for path in CONTEXT.glob("*.md"):
            content = path.read_text(encoding="utf-8")
            search_area = "\n".join(content.splitlines()[:20])
            for field in required_fields:
                self.assertIn(field, search_area, f"{path.name} missing {field}")

    def test_context_reference_links_from_top_level_files_resolve(self):
        link_pattern = re.compile(r"\[([^\]]+)\]\((reference/[^)#]+)(?:#[^)]+)?\)")

        for path in CONTEXT.glob("*.md"):
            content = path.read_text(encoding="utf-8")
            for _, target in link_pattern.findall(content):
                resolved = (path.parent / target).resolve()
                self.assertTrue(
                    resolved.exists(),
                    f"{path.name} links to missing reference file {target}",
                )

    def test_competitor_battlecards_are_preserved_as_reference_files(self):
        battlecard_dir = CONTEXT / "reference" / "competitors" / "battlecards"
        battlecards = sorted(battlecard_dir.glob("*.md"))

        self.assertGreaterEqual(len(battlecards), 39)

        for path in battlecards:
            content = path.read_text(encoding="utf-8")
            required = [
                "# ",
                "How We Win",
                "Competitor Strengths",
                "Competitor Weaknesses",
            ]
            for text in required:
                self.assertIn(text, content, f"{path.name} missing {text}")
            self.assertTrue(
                "Company and Solution Overview" in content
                or "Company Overview" in content
                or "Positioning and Overview" in content,
                f"{path.name} missing overview field",
            )

    def test_writing_examples_preserve_full_simpro_articles(self):
        examples_dir = CONTEXT / "reference" / "writing-examples"
        examples = sorted(examples_dir.glob("*.md"))

        self.assertEqual(len(examples), 4)

        for path in examples:
            content = path.read_text(encoding="utf-8")
            required = [
                "**URL:**",
                "**Published:**",
                "## What Makes This Exemplary",
                "## Full Article Text",
            ]
            for text in required:
                self.assertIn(text, content, f"{path.name} missing {text}")

            full_article = content.split("## Full Article Text", 1)[1]
            self.assertGreater(
                len(full_article.split()),
                500,
                f"{path.name} does not preserve full article detail",
            )

    def test_ai_citation_reference_files_preserve_prompt_and_peec_rows(self):
        prompt_runs = (
            CONTEXT
            / "reference"
            / "ai-citations"
            / "2026-05-21-prompt-runs.md"
        ).read_text(encoding="utf-8")
        peec_export = (
            CONTEXT
            / "reference"
            / "ai-citations"
            / "2026-05-21-peec-url-export.md"
        ).read_text(encoding="utf-8")

        prompt_rows = re.findall(r"^\| \d+ \|", prompt_runs, flags=re.MULTILINE)
        peec_rows = re.findall(r"^\| \d+ \|", peec_export, flags=re.MULTILINE)

        self.assertEqual(len(prompt_rows), 25)
        self.assertEqual(len(peec_rows), 40)


if __name__ == "__main__":
    unittest.main()
