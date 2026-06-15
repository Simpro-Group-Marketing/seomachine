import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from data_sources.modules.proof_sidecar import (
    compose_with_sidecar,
    default_sidecar_path,
    load_sidecar_content,
)


class ProofSidecarTests(unittest.TestCase):
    def test_default_sidecar_path_for_dated_draft(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            draft = root / "drafts" / "best-hvac-software-2026-06-12.md"
            expected = root / "research" / "validation-best-hvac-software-2026-06-12.md"

            self.assertEqual(default_sidecar_path(draft), expected)

    def test_loads_explicit_sidecar_path(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            draft = root / "drafts" / "article-2026-06-12.md"
            sidecar = root / "proof" / "article-proof.md"
            draft.parent.mkdir(parents=True)
            sidecar.parent.mkdir(parents=True)
            draft.write_text("# Article", encoding="utf-8")
            sidecar.write_text("Metric Proof Pack", encoding="utf-8")

            content = load_sidecar_content(draft, sidecar)

        self.assertEqual(content, "Metric Proof Pack")

    def test_autodiscovers_validation_sidecar(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            draft = root / "drafts" / "best-hvac-software-2026-06-12.md"
            sidecar = root / "research" / "validation-best-hvac-software-2026-06-12.md"
            draft.parent.mkdir(parents=True)
            sidecar.parent.mkdir(parents=True)
            draft.write_text("# Article", encoding="utf-8")
            sidecar.write_text("PAA/FAQ Provenance", encoding="utf-8")

            content = load_sidecar_content(draft)

        self.assertEqual(content, "PAA/FAQ Provenance")

    def test_compose_with_sidecar_keeps_article_first(self):
        combined = compose_with_sidecar("# Article", "Metric Proof Pack")

        self.assertTrue(combined.startswith("# Article"))
        self.assertIn("SEO_MACHINE_PROOF_SIDECAR_START", combined)
        self.assertIn("Metric Proof Pack", combined)


if __name__ == "__main__":
    unittest.main()
