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
    AeoGeoRaterTestCase,
    COMPLIANT_ARTICLE,
    PAA_PROVENANCE_BLOCK,
    write_paa_fixture,
)

class AeoGeoRaterEeatTests(AeoGeoRaterTestCase):
    def test_unbound_reviewer_frontmatter_cannot_satisfy_expertise(self):
        for field in ("reviewer", "reviewed_by", "expert_reviewer"):
            with self.subTest(field=field):
                result = _check_eeat_proof(
                    "# Scheduling guide\n\nUse current job information.",
                    "# Scheduling guide\n\nUse current job information.",
                    {field: "Dr Example Reviewer"},
                )

                self.assertFalse(result["details"]["has_expertise"])
                self.assertNotIn(
                    "reviewer_metadata",
                    result["details"]["expertise_signals"],
                )

    def test_eeat_fails_when_external_research_has_no_experience_signal(self):
        content = COMPLIANT_ARTICLE.replace(
            "\n[Schaffer Beacon Mechanical](https://www.simprogroup.com/case-studies/schaffer-beacon-mechanical) shows how field service teams use connected workflows to improve operational control.\n",
            "\nThe article uses public research to explain scheduling workflows.\n",
        )
        result = self.rate(content)

        self.assertFalse(result["checks"]["eeat_proof"]["passed"])
        self.assertFalse(result["passed"])
        self.assertIn("eeat_proof", {issue["check"] for issue in result["issues"]})
        self.assertIn(
            "review-site experience evidence",
            result["checks"]["eeat_proof"]["fix"],
        )

    def test_eeat_fails_when_case_study_has_no_expertise_signal(self):
        content = COMPLIANT_ARTICLE.replace("Author: Jordan Lee\n", "")
        content = content.replace("Last Updated: 2026-05-22\n", "Last Updated: 2026-05-22\n")
        content = content.replace("Simpro connects", "The platform connects")
        content = content.replace(
            "https://www.simprogroup.com/features/scheduling-software",
            "https://www.fieldtechnologiesonline.com/",
        ).replace(
            "https://www.simprogroup.com/features/field-service-mobile-app",
            "https://www.achrnews.com/",
        ).replace(
            "https://www.simprogroup.com/features/invoicing-software-for-construction",
            "https://www.mckinsey.com/",
        )

        result = self.rate(content)

        details = result["checks"]["eeat_proof"]["details"]

        self.assertTrue(details["case_study_links"])
        self.assertFalse(details["expertise_signals"])
        self.assertFalse(result["checks"]["eeat_proof"]["passed"])

    def test_generic_review_site_link_without_story_selection_does_not_satisfy_experience(self):
        content = COMPLIANT_ARTICLE.replace(
            "\n[Schaffer Beacon Mechanical](https://www.simprogroup.com/case-studies/schaffer-beacon-mechanical) shows how field service teams use connected workflows to improve operational control.\n",
            "\n[G2 reviews](https://www.g2.com/products/simpro/reviews) mention field workflow visibility themes for trade businesses.\n",
        )

        result = self.rate(content)

        details = result["checks"]["eeat_proof"]["details"]

        self.assertFalse(result["checks"]["eeat_proof"]["passed"])
        self.assertTrue(details["review_site_links"])
        self.assertNotIn("review_site_link", details["experience_signals"])
        self.assertIn("hash-verified", result["checks"]["eeat_proof"]["fix"])

    def test_self_asserted_review_story_selection_does_not_satisfy_experience(self):
        content = COMPLIANT_ARTICLE.replace(
            "\n[Schaffer Beacon Mechanical](https://www.simprogroup.com/case-studies/schaffer-beacon-mechanical) shows how field service teams use connected workflows to improve operational control.\n",
            "\n[Megan B's Capterra review](https://www.capterra.com/p/10529/Simpro-Enterprise/reviews/) describes a service business using Simpro for service jobs, recurring jobs, quotes, invoices, and QBO integration.\n",
        )
        proof_sidecar = PAA_PROVENANCE_BLOCK + fixture_text("content_evidence:test_aeo_geo_rater-896-13")

        result = rate_aeo_geo(
            content,
            {"primary_keyword": "hvac scheduling software"},
            source_path=write_paa_fixture(self, content),
            proof_sidecar_content=proof_sidecar,
        )

        details = result["checks"]["eeat_proof"]["details"]

        self.assertFalse(result["checks"]["eeat_proof"]["passed"])
        self.assertTrue(details["review_site_links"])
        self.assertNotIn("review_story_selection", details["experience_signals"])

    def test_self_asserted_approved_sidecar_label_does_not_satisfy_experience(self):
        content = COMPLIANT_ARTICLE.replace(
            "Meta Title: HVAC Scheduling Software for Contractors | Simpro",
            "Meta Title: Construction Draw Schedule Explained",
        ).replace(
            "Primary Keyword: hvac scheduling software",
            "Primary Keyword: construction draw schedule",
        ).replace(
            "Author: Jordan Lee",
            "Author: ClockShark Editorial Team",
        ).replace(
            "\n[Schaffer Beacon Mechanical](https://www.simprogroup.com/case-studies/schaffer-beacon-mechanical) shows how field service teams use connected workflows to improve operational control.\n",
            "\nClockShark's [job management tools](https://www.clockshark.com/tour/job-management) show active jobs, completed work hours, and job stages in one place.\n",
        ).replace(
            "https://www.simprogroup.com/features/scheduling-software",
            "https://www.clockshark.com/industries/construction-trades",
        )
        proof_sidecar = PAA_PROVENANCE_BLOCK + fixture_text("content_evidence:test_aeo_geo_rater-936-14")

        result = rate_aeo_geo(
            content,
            {"primary_keyword": "construction draw schedule"},
            source_path=write_paa_fixture(self, content),
            proof_sidecar_content=proof_sidecar,
        )

        details = result["checks"]["eeat_proof"]["details"]

        self.assertFalse(result["checks"]["eeat_proof"]["passed"])
        self.assertNotIn("sidecar_experience_proof", details["experience_signals"])

    def test_invented_approved_experience_url_does_not_satisfy_experience(self):
        content = COMPLIANT_ARTICLE.replace(
            "\n[Schaffer Beacon Mechanical](https://www.simprogroup.com/case-studies/schaffer-beacon-mechanical) shows how field service teams use connected workflows to improve operational control.\n",
            "\nThe article does not use customer experience proof.\n",
        )
        proof_sidecar = PAA_PROVENANCE_BLOCK + fixture_text("content_evidence:test_aeo_geo_rater-961-15")

        result = rate_aeo_geo(
            content,
            {"primary_keyword": "hvac scheduling software"},
            source_path=write_paa_fixture(self, content),
            proof_sidecar_content=proof_sidecar,
        )

        details = result["checks"]["eeat_proof"]["details"]
        self.assertFalse(result["checks"]["eeat_proof"]["passed"])
        self.assertFalse(details["has_experience"])

    def test_bound_selector_and_mining_visible_in_article_satisfies_experience(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            content = COMPLIANT_ARTICLE.replace(
                "\n[Schaffer Beacon Mechanical](https://www.simprogroup.com/case-studies/schaffer-beacon-mechanical) shows how field service teams use connected workflows to improve operational control.\n",
                "\n[Megan B's Capterra review](https://www.capterra.com/p/10529/Simpro-Enterprise/reviews/) describes using service jobs, quotes, invoices, and QBO integration in one connected workflow.\n",
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
        self.assertTrue(result["checks"]["eeat_proof"]["passed"], result)
        self.assertIn(
            "validated_customer_experience", details["experience_signals"]
        )

    def test_receipt_approved_fred_authority_satisfies_expertise(self):
        body = (
            "For connected field service context, see Fred Voccola's "
            "[Webinar: The Connected Intelligence Revolution for Field Service Ops]"
            "(https://youtube.com/watch?v=5pXio-zMXFI)."
        )
        proof_sidecar = "## Fred Voccola Authority Selection\n- Evaluation status: completed\n- Top candidates: [FVMI-0003]\n- Selected: [FVMI-0003]\n- Context receipt: research/context-receipt-what-is-an-end-to-end-solution.json\n- Claim IDs: [claim-fred-FVMI-0003]\n- Receipt revision: dd7488e21bcbeae9506147a29c9e5dd18f19d21d3051cc516a06e39d9b387319\n- Approval source: connector_claim_result\n- Fit decision: Selected for inline authority citation only.\n- Intended use: inline_citation\n- Target section: What Is an End to End Solution for Field Service?\n- Authority row: [res-7b30f511fc345ff2bb5fd9e515f03d06]\n- Public URL: https://youtube.com/watch?v=5pXio-zMXFI\n- Evidence status: receipt_approved\n- Verification method: not_applicable\n- Evidence excerpt: not applicable\n- Timestamp or locator: not applicable\n- Playback verified: not_applicable\n- Exact quote: not applicable\n- Embed decision: no\n- VideoObject: not applicable"

        with patch("data_sources.modules.content_scoring.aeo_eeat._has_documented_no_fit_experience_boundary", return_value=True):
            result = _check_eeat_proof(
                body,
                body,
                {},
                proof_sidecar_content=proof_sidecar,
            )

        self.assertTrue(result["passed"])
        self.assertIn("fred_authority", result["details"]["expertise_signals"])

    def test_bound_selector_and_mining_without_visible_story_does_not_satisfy_experience(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            content = COMPLIANT_ARTICLE.replace(
                "\n[Schaffer Beacon Mechanical](https://www.simprogroup.com/case-studies/schaffer-beacon-mechanical) shows how field service teams use connected workflows to improve operational control.\n",
                "\nThe selected customer story is not used in this article.\n",
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
        self.assertFalse(result["checks"]["eeat_proof"]["passed"])
        self.assertNotIn(
            "validated_customer_experience", details["experience_signals"]
        )

    def test_handwritten_no_fit_boundary_without_selector_evidence_fails_closed(self):
        result = self.rate_without_customer_experience(
            fixture_text("content_evidence:test_aeo_geo_rater-1035-16")
        )
        details = result["checks"]["eeat_proof"]["details"]

        self.assertFalse(result["checks"]["eeat_proof"]["passed"])
        self.assertNotIn(
            "documented_no_fit_experience_boundary",
            details["experience_signals"],
        )

    def test_documented_no_fit_requires_substantive_first_hand_reason(self):
        result = self.rate_without_customer_experience(
            fixture_text("content_evidence:test_aeo_geo_rater-1057-17")
        )

        self.assertFalse(result["checks"]["eeat_proof"]["passed"])

    def test_documented_no_fit_requires_experience_story_rejection_reason(self):
        result = self.rate_without_customer_experience(
            fixture_text("content_evidence:test_aeo_geo_rater-1074-18")
        )

        self.assertFalse(result["checks"]["eeat_proof"]["passed"])

    def test_documented_no_fit_rejects_non_substantive_candidate_reason(self):
        result = self.rate_without_customer_experience(
            fixture_text("content_evidence:test_aeo_geo_rater-1091-19")
        )

        self.assertFalse(result["checks"]["eeat_proof"]["passed"])

    def test_documented_no_fit_requires_a_real_top_candidate(self):
        result = self.rate_without_customer_experience(
            fixture_text("content_evidence:test_aeo_geo_rater-1108-20")
        )

        self.assertFalse(result["checks"]["eeat_proof"]["passed"])

    def test_documented_no_fit_rejects_null_pseudo_candidate(self):
        result = self.rate_without_customer_experience(
            fixture_text("content_evidence:test_aeo_geo_rater-1125-21")
        )

        self.assertFalse(result["checks"]["eeat_proof"]["passed"])

    def test_documented_no_fit_rejects_unknown_proof_id(self):
        result = self.rate_without_customer_experience(
            fixture_text("content_evidence:test_aeo_geo_rater-1142-22")
        )

        self.assertFalse(result["checks"]["eeat_proof"]["passed"])

    def test_documented_no_fit_rejects_non_review_story_proof_ids(self):
        for proof_id in (
            "case-study-bge-digital",
            "quote-matrix-bwe-engineering-job-to-invoice",
        ):
            with self.subTest(proof_id=proof_id):
                result = self.rate_without_customer_experience(
                    f"""
```text
E-E-A-T Proof Map
- First-hand evidence decision: Selected: [none]. No approved identity-backed source in the selector slate substantiates women choosing or working in the ranked trades.
```

```text
Customer Proof Slate
- Role: experience_story | Top candidates: [{proof_id}] | Selected: [none] | Rejected stronger candidates: [{proof_id}: omitted because this proof does not substantiate the article's women-in-trades career objective]
```
"""
                )

                self.assertFalse(result["checks"]["eeat_proof"]["passed"])

    @patch(
        "data_sources.modules.content_scoring.aeo_no_fit._customer_proof_ids",
        return_value=frozenset(),
    )
    def test_documented_no_fit_fails_closed_when_proof_index_is_unavailable(
        self,
        _proof_ids,
    ):
        result = self.rate_without_customer_experience(
            fixture_text("content_evidence:test_aeo_geo_rater-1188-23")
        )

        self.assertFalse(result["checks"]["eeat_proof"]["passed"])

    def test_aggregate_workforce_statistics_do_not_satisfy_experience(self):
        result = self.rate_without_customer_experience(
            fixture_text("content_evidence:test_aeo_geo_rater-1205-24")
        )

        self.assertFalse(result["checks"]["eeat_proof"]["passed"])
        self.assertNotIn(
            "sidecar_experience_proof",
            result["checks"]["eeat_proof"]["details"]["experience_signals"],
        )

    def test_numeric_apprenticeship_evidence_does_not_satisfy_experience(self):
        result = self.rate_without_customer_experience(
            fixture_text("content_evidence:test_aeo_geo_rater-1221-25")
        )

        self.assertFalse(result["checks"]["eeat_proof"]["passed"])
        self.assertNotIn(
            "sidecar_experience_proof",
            result["checks"]["eeat_proof"]["details"]["experience_signals"],
        )

    def test_unavailable_first_hand_evidence_does_not_satisfy_experience(self):
        result = self.rate_without_customer_experience(
            fixture_text("content_evidence:test_aeo_geo_rater-1237-26")
        )

        self.assertFalse(result["checks"]["eeat_proof"]["passed"])
        self.assertNotIn(
            "sidecar_experience_proof",
            result["checks"]["eeat_proof"]["details"]["experience_signals"],
        )

    def test_post_negated_first_hand_evidence_does_not_satisfy_experience(self):
        result = self.rate_without_customer_experience(
            fixture_text("content_evidence:test_aeo_geo_rater-1253-27")
        )

        self.assertFalse(result["checks"]["eeat_proof"]["passed"])
        self.assertNotIn(
            "sidecar_experience_proof",
            result["checks"]["eeat_proof"]["details"]["experience_signals"],
        )

    def test_non_allowlisted_experience_proof_status_does_not_satisfy_experience(self):
        for status in (
            "rejected",
            "blocked",
            "withdrawn",
            "revoked",
            "expired",
            "approved but withdrawn",
        ):
            with self.subTest(status=status):
                result = self.rate_without_customer_experience(
                    f"""
```text
E-E-A-T Proof Map
- Experience proof: URL: https://example.com/source | Proof type: identity-backed experience | Evidence: The article uses first-hand experience evidence from an identity-backed public account. | Status: {status}
```
"""
                )

                self.assertFalse(result["checks"]["eeat_proof"]["passed"])
                self.assertNotIn(
                    "sidecar_experience_proof",
                    result["checks"]["eeat_proof"]["details"]["experience_signals"],
                )

    def test_self_asserted_experience_status_never_satisfies_experience(self):
        for status in (
            "approved",
            "approved for public use",
            "verified",
            "verified for public use",
        ):
            with self.subTest(status=status):
                result = self.rate_without_customer_experience(
                    f"""
```text
E-E-A-T Proof Map
- Experience proof: URL: https://example.com/source | Proof type: identity-backed experience | Evidence: The article uses first-hand experience evidence from an identity-backed public account. | Status: {status}
```
"""
                )

                self.assertFalse(result["checks"]["eeat_proof"]["passed"])
                self.assertNotIn(
                    "sidecar_experience_proof",
                    result["checks"]["eeat_proof"]["details"]["experience_signals"],
                )

    def test_generic_first_hand_experience_requires_proof_type(self):
        result = self.rate_without_customer_experience(
            fixture_text("content_evidence:test_aeo_geo_rater-1317-28")
        )

        self.assertFalse(result["checks"]["eeat_proof"]["passed"])
        self.assertNotIn(
            "sidecar_experience_proof",
            result["checks"]["eeat_proof"]["details"]["experience_signals"],
        )

    def test_generic_experience_proof_type_requires_exact_allowlist_value(self):
        result = self.rate_without_customer_experience(
            fixture_text("content_evidence:test_aeo_geo_rater-1333-29")
        )

        self.assertFalse(result["checks"]["eeat_proof"]["passed"])

    def test_experience_proof_without_status_does_not_satisfy_experience(self):
        result = self.rate_without_customer_experience(
            fixture_text("content_evidence:test_aeo_geo_rater-1345-30")
        )

        self.assertFalse(result["checks"]["eeat_proof"]["passed"])
        self.assertNotIn(
            "sidecar_experience_proof",
            result["checks"]["eeat_proof"]["details"]["experience_signals"],
        )
