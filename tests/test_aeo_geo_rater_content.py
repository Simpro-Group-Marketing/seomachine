from tests.fixture_text import fixture_text

import hashlib
import json
import re
import unittest
from contextlib import redirect_stderr, redirect_stdout
from datetime import date, timedelta
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from data_sources.modules.content_scoring.aeo_content import _check_capsule_coverage
from data_sources.modules.content_scoring.aeo_content import _check_direct_answer
from data_sources.modules.content_scoring.aeo_eeat import _check_eeat_proof
from data_sources.modules.content_scoring.aeo_faq_paa import _check_faq_proof, _check_faq_questions
from data_sources.modules.content_scoring.aeo_no_fit import _has_documented_no_fit_experience_boundary
from data_sources.modules.content_scoring.aeo_orchestration import rate_aeo_geo
from data_sources.modules.customer_proof_selector import _main as run_customer_proof_selector
from tests.research_provenance_fixtures import build_answersocrates_fixture
from tests.test_customer_proof_selector import (
    write_context_receipt_fixture,
    write_selector_fixture,
)
from tests.vault_context_fixture import load_validated_claim_set_for_unit_test
from tests.aeo_geo_rater_support import (
    ASSEMBLY_DATE,
    AUTHOR_VERIFICATION_BLOCK,
    AeoGeoRaterTestCase,
    COMPLIANT_ARTICLE,
    FAQ_PROOF_BLOCK,
    PAA_PROVENANCE_BLOCK,
    PAA_QUERY,
    PRODUCTION_IMAGE_MARKER,
    finalized_non_connector_bom,
    write_paa_fixture,
)

class AeoGeoRaterContentTests(AeoGeoRaterTestCase):
    def test_capsule_coverage_reports_each_non_faq_h2_at_word_boundaries(self):
        def paragraph(word_count):
            first_sentence = " ".join(f"word{index}" for index in range(word_count - 1))
            return f"{first_sentence}. Final."

        content = "\n\n".join(
            [
                f"## Section {word_count}\n\n{paragraph(word_count)}"
                for word_count in (49, 50, 60, 61)
            ]
            + ["## Frequently Asked Questions\n\n" + paragraph(50)]
        )

        result = _check_capsule_coverage(content)

        self.assertEqual(result["details"]["h2_count"], 4)
        self.assertEqual(result["details"]["capsule_count"], 2)
        self.assertEqual(
            result["details"]["sections"],
            [
                {
                    "heading": f"Section {word_count}",
                    "word_count": word_count,
                    "sentence_count": 2,
                    "passed": word_count in (50, 60),
                    "reason": (
                        "First paragraph is a 50-60 word capsule."
                        if word_count in (50, 60)
                        else "First paragraph must contain 50-60 words."
                    ),
                }
                for word_count in (49, 50, 60, 61)
            ],
        )

    def test_compliant_article_passes_90_point_gate(self):
        result = self.rate_with_bound_experience(
            proof_sidecar_suffix=FAQ_PROOF_BLOCK,
        )
        self.assertTrue(result["passed"], result)
        self.assertGreaterEqual(result["score"], 90)
        self.assertTrue(result["checks"]["direct_answer"]["passed"])
        self.assertTrue(result["checks"]["capsule_coverage"]["passed"])
        self.assertTrue(result["checks"]["faq_questions"]["passed"])
        self.assertTrue(result["checks"]["eeat_proof"]["passed"])
        self.assertTrue(result["checks"]["paa_provenance"]["passed"])

    def test_json_ld_is_excluded_from_reader_visible_section_diagnostics(self):
        baseline = self.rate_with_bound_experience(
            proof_sidecar_suffix=FAQ_PROOF_BLOCK,
        )
        json_ld = """
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "Article",
  "headline": "HVAC Scheduling Software for Contractors",
  "description": "HVAC scheduling software helps field service teams."
}
</script>
"""
        with_json_ld = self.rate_with_bound_experience(
            COMPLIANT_ARTICLE + json_ld,
            proof_sidecar_suffix=FAQ_PROOF_BLOCK,
        )

        self.assertEqual(
            with_json_ld["checks"]["direct_answer"],
            baseline["checks"]["direct_answer"],
        )
        self.assertEqual(
            with_json_ld["checks"]["capsule_coverage"],
            baseline["checks"]["capsule_coverage"],
        )
        self.assertEqual(
            with_json_ld["details"]["section_clarity"],
            baseline["details"]["section_clarity"],
        )

    def test_no_author_article_can_pass_aeo_when_required_context_is_valid(self):
        content = COMPLIANT_ARTICLE.replace("Author: Jordan Lee\n", "").replace(
            "  - Person as author\n",
            "",
        )

        result = self.rate_with_bound_experience(
            content,
            proof_sidecar_suffix=FAQ_PROOF_BLOCK,
        )

        self.assertTrue(result["passed"], result)
        self.assertGreaterEqual(result["score"], 90)
        self.assertTrue(result["checks"]["metadata"]["passed"])
        self.assertTrue(result["checks"]["eeat_proof"]["passed"])
        self.assertFalse(
            result["checks"]["eeat_proof"]["details"]["has_expertise"]
        )

    def test_non_connector_bom_makes_selector_backed_eeat_not_applicable(self):
        result = rate_aeo_geo(
            COMPLIANT_ARTICLE,
            {"primary_keyword": "hvac scheduling software"},
            source_path=write_paa_fixture(self, COMPLIANT_ARTICLE),
            proof_sidecar_content=PAA_PROVENANCE_BLOCK + FAQ_PROOF_BLOCK,
            finalized_bom=finalized_non_connector_bom(),
            assembly_date=ASSEMBLY_DATE,
            paa_workflow_mode="new",
            paa_expected_query=PAA_QUERY,
            paa_expected_collection_date=ASSEMBLY_DATE,
        )

        check = result["checks"]["eeat_proof"]
        self.assertTrue(check["passed"])
        self.assertFalse(check["applicable"])
        self.assertEqual(check["status"], "not_applicable")

    def test_direct_answer_skips_standalone_image_placeholder(self):
        content = COMPLIANT_ARTICLE.replace(
            "# HVAC Scheduling Software for Contractors\n\n",
            "# HVAC Scheduling Software for Contractors\n\n"
            f"{PRODUCTION_IMAGE_MARKER}\n\n",
        )

        result = self.rate(
            content,
            proof_sidecar_content=AUTHOR_VERIFICATION_BLOCK + FAQ_PROOF_BLOCK,
        )
        first_two = result["checks"]["direct_answer"]["details"]["first_two_sentences"]

        self.assertTrue(result["checks"]["direct_answer"]["passed"])
        self.assertTrue(first_two.startswith("HVAC scheduling software helps contractors"))
        self.assertNotIn("IMAGE PLACEHOLDER", first_two)

    def test_direct_answer_accepts_natural_locale_keyword_variant(self):
        result = _check_direct_answer(
            "The strongest construction estimating software in Australia is the option that matches how a business prices work.",
            {"primary_keyword": "construction estimating software australia"},
        )

        self.assertTrue(result["passed"], result)

    def test_direct_answer_skips_original_hero_image_placeholder(self):
        content = COMPLIANT_ARTICLE.replace(
            "# HVAC Scheduling Software for Contractors\n\n",
            "# HVAC Scheduling Software for Contractors\n\n"
            f"{PRODUCTION_IMAGE_MARKER}\n\n",
        )

        result = self.rate(
            content,
            proof_sidecar_content=AUTHOR_VERIFICATION_BLOCK + FAQ_PROOF_BLOCK,
        )
        first_two = result["checks"]["direct_answer"]["details"]["first_two_sentences"]

        self.assertTrue(result["checks"]["direct_answer"]["passed"])
        self.assertNotIn("IMAGE PLACEHOLDER", first_two)

    def test_direct_answer_does_not_skip_mixed_placeholder_and_prose(self):
        mixed_line = (
            "[IMAGE PLACEHOLDER: hero] Teams can fabricate results; [source]"
        )
        content = COMPLIANT_ARTICLE.replace(
            "# HVAC Scheduling Software for Contractors\n\n",
            "# HVAC Scheduling Software for Contractors\n\n"
            f"{mixed_line}\n\n",
        )

        result = self.rate(content)
        first_two = result["checks"]["direct_answer"]["details"]["first_two_sentences"]

        self.assertFalse(result["checks"]["direct_answer"]["passed"])
        self.assertEqual(first_two, mixed_line)

    def test_faq_question_gate_allows_six_natural_language_questions(self):
        content = fixture_text("content_evidence:test_aeo_geo_rater-697-7")

        result = _check_faq_questions(content)

        self.assertTrue(result["passed"])
        self.assertEqual(result["details"]["question_count"], 6)

    def test_faq_question_gate_has_no_fixed_minimum_or_maximum(self):
        one_question = fixture_text("content_evidence:test_aeo_geo_rater-730-8")
        seven_questions = "## Questions and answers\n\n" + "\n\n".join(
            f"### What is scheduling decision {index}?\n\nAnswer."
            for index in range(1, 8)
        )

        one_result = _check_faq_questions(one_question)
        seven_result = _check_faq_questions(seven_questions)

        self.assertTrue(one_result["passed"])
        self.assertEqual(one_result["details"]["question_count"], 1)
        self.assertTrue(seven_result["passed"])
        self.assertEqual(seven_result["details"]["question_count"], 7)

    def test_faq_question_gate_accepts_h3_through_h5_question_headings(self):
        content = fixture_text("content_evidence:test_aeo_geo_rater-750-9")

        result = _check_faq_questions(content)

        self.assertTrue(result['passed'])
        self.assertEqual(result['details']['question_count'], 3)

    def test_paa_provenance_can_live_in_sidecar(self):
        content = COMPLIANT_ARTICLE.replace(PAA_PROVENANCE_BLOCK, "")

        result = self.rate_with_bound_experience(
            content,
            proof_sidecar_suffix=FAQ_PROOF_BLOCK,
        )

        self.assertTrue(result["checks"]["paa_provenance"]["passed"])
        self.assertTrue(result["passed"])

    def test_bare_case_study_link_does_not_satisfy_experience(self):
        result = self.rate()

        details = result["checks"]["eeat_proof"]["details"]

        self.assertFalse(result["checks"]["eeat_proof"]["passed"])
        self.assertTrue(details["case_study_links"])
        self.assertNotIn("case_study_link", details["experience_signals"])
        self.assertIn("author_metadata", details["expertise_signals"])

    def test_bare_simpro_product_link_does_not_satisfy_expertise(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            content = COMPLIANT_ARTICLE.replace("Author: Jordan Lee\n", "").replace(
                "\n[Schaffer Beacon Mechanical](https://www.simprogroup.com/case-studies/schaffer-beacon-mechanical) shows how field service teams use connected workflows to improve operational control.\n",
                "\n[Megan B's Capterra review](https://www.capterra.com/p/10529/Simpro-Enterprise/reviews/) describes using service jobs, quotes, invoices, and QBO integration in one connected workflow.\n\nSee the [Simpro scheduling product page](https://www.simprogroup.com/features/scheduling-software) for product details.\n",
            )
            proof_sidecar, proof_sidecar_path = (
                self.write_bound_experience_story_evidence(root)
            )
            with patch(
                "data_sources.modules.customer_proof.connector_inputs.load_validated_claim_set",
                new=load_validated_claim_set_for_unit_test,
            ):
                result = rate_aeo_geo(
                    content,
                    {"primary_keyword": "hvac scheduling software"},
                    source_path=write_paa_fixture(self, content),
                    proof_sidecar_content=proof_sidecar,
                    proof_sidecar_path=str(proof_sidecar_path),
                )

        details = result["checks"]["eeat_proof"]["details"]

        self.assertTrue(details["has_experience"])
        self.assertFalse(details["has_expertise"])
        self.assertTrue(details["simpro_product_links"])
        self.assertNotIn(
            "simpro_product_or_workflow_link", details["expertise_signals"]
        )
