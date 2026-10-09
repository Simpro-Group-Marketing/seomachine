import json
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONTEXT = ROOT / "context"


class ContextRefactorIntegrityTests(unittest.TestCase):
    def test_context_policy_registers_every_remaining_context_file(self):
        policy = json.loads((CONTEXT / "context-policy.json").read_text(encoding="utf-8"))
        registered = {
            str(path).replace("\\", "/").lstrip("./")
            for path in policy["files"]
        }
        actual = {
            path.relative_to(ROOT).as_posix()
            for path in CONTEXT.rglob("*")
            if path.is_file()
        }

        self.assertEqual(policy["schema"], "seomachine-context-boundary-policy/v1")
        self.assertEqual(registered, actual)

        allowed_categories = set(policy["allowed_categories"])
        self.assertEqual(
            allowed_categories,
            {
                "seo_aeo",
                "editorial_strategy",
                "cro_best_practice",
                "link_map",
                "source_governance",
            },
        )
        for path, row in policy["files"].items():
            self.assertIn(row["category"], allowed_categories, path)

    def test_local_brand_authority_mirrors_are_removed(self):
        def removed_file(*parts: str, suffix: str) -> Path:
            return CONTEXT / ("-".join(parts) + suffix)

        removed_paths = [
            removed_file("brand", "voice", suffix=".md"),
            removed_file("style", "guide", suffix=".md"),
            CONTEXT / ("features" + ".md"),
            removed_file("lightning", "positioning", suffix=".md"),
            removed_file("customer", "proof", "index", suffix=".json"),
            removed_file("customer", "proof", "usage", "ledger", suffix=".json"),
            removed_file("customer", "proof", "intake", "template", suffix=".csv"),
            removed_file("competitor", "analysis", suffix=".md"),
            CONTEXT / "reference" / "competitors" / "battlecards",
            CONTEXT / "reference" / "writing-examples",
            CONTEXT / "reference" / "coverage",
        ]

        for path in removed_paths:
            self.assertFalse(path.exists(), f"{path} must not remain active context")

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

    def test_competitor_reference_is_reduced_to_seo_market_signals(self):
        battlecard_dir = CONTEXT / "reference" / "competitors" / "battlecards"
        seo_signals = CONTEXT / "reference" / "competitors" / "seo-market-signals.md"
        content = seo_signals.read_text(encoding="utf-8")

        self.assertFalse(battlecard_dir.exists())
        self.assertIn("**Category:** seo_aeo", content)
        self.assertIn("Dated search/visibility evidence", content)
        self.assertIn("Do not use this file to decide a public competitor shortlist", content)
        self.assertNotIn("How We Win", content)
        self.assertNotIn("Competitor Weaknesses", content)

    def test_writing_examples_are_abstract_patterns_only(self):
        examples_dir = CONTEXT / "reference" / "writing-examples"
        pattern_library = CONTEXT / "writing-examples.md"
        content = pattern_library.read_text(encoding="utf-8")

        self.assertFalse(examples_dir.exists())
        self.assertIn("Abstract, brand-neutral article mechanics", content)
        self.assertIn("This file intentionally contains no copied brand prose", content)
        self.assertIn("Reusable Article Patterns", content)
        self.assertNotIn("## Full Article Text", content)
        self.assertNotIn("**URL:**", content)
        self.assertNotIn("What Makes This Exemplary", content)

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

    def test_context_policy_documents_vault_only_brand_boundary(self):
        policy = json.loads((CONTEXT / "context-policy.json").read_text(encoding="utf-8"))
        boundary = policy["boundary"]

        self.assertIn("Brand Vault connector", boundary["brand_authority"])
        self.assertIn("SEO/AEO", boundary["local_context_role"])
        self.assertIn("no local fallback", boundary["connector_failure"])


if __name__ == "__main__":
    unittest.main()
