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
from tests.aeo_geo_rater_support import AeoGeoRaterTestCase, finalized_no_author_bom


class AeoGeoRaterNoFitTests(AeoGeoRaterTestCase):
    def test_rate_api_accepts_bound_quality_context_for_no_faq_article(self):
        no_faq = fixture_text("content_evidence:test_aeo_geo_rater-248-4")
        with patch(
            'data_sources.modules.blog_assembly_contract.current_utc_date',
            return_value=date(2026, 5, 22),
        ):
            result = rate_aeo_geo(
                no_faq,
                {
                    'primary_keyword': 'field service scheduling',
                    'faq_policy_status': 'not_applicable',
                    'assembly_date': '2026-05-22',
                },
                finalized_bom=finalized_no_author_bom(),
                paa_workflow_mode='new',
                paa_expected_query='field service scheduling',
                paa_expected_collection_date='2026-05-22',
            )

        self.assertFalse(result['checks']['faq_questions']['applicable'])
        self.assertTrue(result['checks']['metadata']['passed'])

    def test_what_is_query_accepts_equivalent_declarative_definition(self):
        result = _check_direct_answer(
            "A job sheet is a working record for a job or site visit. "
            "It captures the task, work, time, materials, evidence and sign-off.",
            {"primary_keyword": "what is a job sheet"},
        )

        self.assertTrue(result["passed"], result)
        self.assertTrue(result["details"]["includes_target"])

    def test_topic_qualified_frequently_asked_questions_heading_is_recognized(self):
        result = _check_faq_questions(
            fixture_text("content_evidence:test_aeo_geo_rater-298-11")
        )

        self.assertTrue(result["passed"])
        self.assertEqual(result["details"]["question_count"], 3)

    def test_no_fit_boundary_accepts_current_rerun_verified_selector_evidence(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            sidecar, sidecar_path, _index_path = self.write_no_fit_selector_evidence(root)
            with patch(
                "data_sources.modules.customer_proof.connector_inputs.load_validated_claim_set",
                new=load_validated_claim_set_for_unit_test,
            ):
                result = _has_documented_no_fit_experience_boundary(
                    sidecar,
                    proof_sidecar_path=str(sidecar_path),
                )

        self.assertTrue(result)

    def test_no_fit_boundary_accepts_hash_verified_rejection_reason_with_commas(self):
        rejection_reason = (
            "omitted because this software-user story covers invoicing, dispatch, and "
            "field scheduling rather than the article's job-sheet definition objective"
        )
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            sidecar, sidecar_path, _index_path = self.write_no_fit_selector_evidence(
                root,
                rejection_reason=rejection_reason,
            )
            with patch(
                "data_sources.modules.customer_proof.connector_inputs.load_validated_claim_set",
                new=load_validated_claim_set_for_unit_test,
            ):
                result = _has_documented_no_fit_experience_boundary(
                    sidecar,
                    proof_sidecar_path=str(sidecar_path),
                )

        self.assertTrue(result)

    def test_rate_aeo_geo_loads_no_fit_sidecar_from_path(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _sidecar, sidecar_path, _index_path = self.write_no_fit_selector_evidence(root)
            content = (
                "# Job Sheets Guide\n\n"
                "Job sheets help teams record work clearly.\n\n"
                "## Frequently asked questions\n\n"
                "### What is a job sheet?\n\n"
                "A job sheet is a work record used to track job details and follow-up tasks.\n"
            )
            with patch(
                "data_sources.modules.customer_proof.connector_inputs.load_validated_claim_set",
                new=load_validated_claim_set_for_unit_test,
            ):
                result = rate_aeo_geo(
                    content,
                    {"primary_keyword": "job sheets"},
                    proof_sidecar_path=str(sidecar_path),
                )

        details = result["checks"]["eeat_proof"]["details"]
        self.assertTrue(details["has_documented_no_fit_boundary"], result)
        self.assertTrue(result["checks"]["eeat_proof"]["passed"], result)

    def test_no_fit_boundary_accepts_rerun_verified_empty_story_slate(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            sidecar, sidecar_path, _index_path = self.write_no_fit_selector_evidence(
                root,
                empty_story_slate=True,
            )
            with patch(
                "data_sources.modules.customer_proof.connector_inputs.load_validated_claim_set",
                new=load_validated_claim_set_for_unit_test,
            ):
                result = _has_documented_no_fit_experience_boundary(
                    sidecar,
                    proof_sidecar_path=str(sidecar_path),
                )

        self.assertTrue(result)

    def test_no_fit_boundary_rejects_selector_evidence_when_an_input_changes(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            sidecar, sidecar_path, index_path = self.write_no_fit_selector_evidence(root)
            index = json.loads(index_path.read_text(encoding="utf-8"))
            index["version"] = 2
            index_path.write_text(json.dumps(index), encoding="utf-8")
            with patch(
                "data_sources.modules.customer_proof.connector_inputs.load_validated_claim_set",
                new=load_validated_claim_set_for_unit_test,
            ):
                result = _has_documented_no_fit_experience_boundary(
                    sidecar,
                    proof_sidecar_path=str(sidecar_path),
                )

        self.assertFalse(result)

    def test_no_fit_boundary_rejects_rehashed_evidence_with_forged_candidates(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            sidecar, sidecar_path, _index_path = self.write_no_fit_selector_evidence(root)
            evidence_path = root / "selector-evidence.json"
            evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
            evidence["roles"][0]["candidate_ids"] = ["invented-proof"]
            evidence_bytes = (
                json.dumps(evidence, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
            ).encode("utf-8")
            evidence_path.write_bytes(evidence_bytes)
            digest = hashlib.sha256(evidence_bytes).hexdigest()
            sidecar = re.sub(
                r"(?im)(^- Selector evidence: .*? \| SHA-256: )[0-9a-f]{64}$",
                rf"\g<1>{digest}",
                sidecar,
            )
            sidecar_path.write_text(sidecar, encoding="utf-8")
            with patch(
                "data_sources.modules.customer_proof.connector_inputs.load_validated_claim_set",
                new=load_validated_claim_set_for_unit_test,
            ):
                result = _has_documented_no_fit_experience_boundary(
                    sidecar,
                    proof_sidecar_path=str(sidecar_path),
                )

        self.assertFalse(result)

    def test_no_fit_boundary_rejects_stale_selector_reference_date(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            sidecar, sidecar_path, _index_path = self.write_no_fit_selector_evidence(root)
            evidence_path = root / "selector-evidence.json"
            evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
            evidence["inputs"]["reference_date"] = (
                date.today() - timedelta(days=1)
            ).isoformat()
            evidence_bytes = (
                json.dumps(evidence, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
            ).encode("utf-8")
            evidence_path.write_bytes(evidence_bytes)
            digest = hashlib.sha256(evidence_bytes).hexdigest()
            sidecar = re.sub(
                r"(?im)(^- Selector evidence: .*? \| SHA-256: )[0-9a-f]{64}$",
                rf"\g<1>{digest}",
                sidecar,
            )
            sidecar_path.write_text(sidecar, encoding="utf-8")
            with patch(
                "data_sources.modules.customer_proof.connector_inputs.load_validated_claim_set",
                new=load_validated_claim_set_for_unit_test,
            ):
                result = _has_documented_no_fit_experience_boundary(
                    sidecar,
                    proof_sidecar_path=str(sidecar_path),
                )

        self.assertFalse(result)

    def test_no_fit_boundary_rejects_malformed_evidence_without_crashing(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            sidecar, sidecar_path, _index_path = self.write_no_fit_selector_evidence(root)
            evidence_path = root / "selector-evidence.json"
            evidence_bytes = b"[]\n"
            evidence_path.write_bytes(evidence_bytes)
            digest = hashlib.sha256(evidence_bytes).hexdigest()
            sidecar = re.sub(
                r"(?im)(^- Selector evidence: .*? \| SHA-256: )[0-9a-f]{64}$",
                rf"\g<1>{digest}",
                sidecar,
            )
            sidecar_path.write_text(sidecar, encoding="utf-8")

            self.assertFalse(
                _has_documented_no_fit_experience_boundary(
                    sidecar,
                    proof_sidecar_path=str(sidecar_path),
                )
            )

    def test_no_fit_boundary_ignores_sidecar_candidate_and_rejection_mismatches(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            sidecar, sidecar_path, _index_path = self.write_no_fit_selector_evidence(root)
            sidecar = sidecar.replace(
                "Top candidates: [review-capterra-qbo-service-jobs-quotes-invoices]",
                "Top candidates: [invented-proof]",
            )
            sidecar = sidecar.replace(
                "omitted because this software-user story does not substantiate "
                "the article's job-sheet definition objective",
                "invented sidecar rejection reason",
            )
            sidecar_path.write_text(sidecar, encoding="utf-8")
            with patch(
                "data_sources.modules.customer_proof.connector_inputs.load_validated_claim_set",
                new=load_validated_claim_set_for_unit_test,
            ):
                result = _has_documented_no_fit_experience_boundary(
                    sidecar,
                    proof_sidecar_path=str(sidecar_path),
                )

        self.assertTrue(result)

    def test_no_fit_boundary_rejects_unverifiable_typed_hash(self):
        sidecar = fixture_text("content_evidence:test_aeo_geo_rater-548-5")

        self.assertFalse(_has_documented_no_fit_experience_boundary(sidecar))
    def test_no_fit_boundary_rejects_a_copied_selector_command_without_receipt(self):
        sidecar = fixture_text("content_evidence:test_aeo_geo_rater-563-6")

        self.assertFalse(_has_documented_no_fit_experience_boundary(sidecar))
