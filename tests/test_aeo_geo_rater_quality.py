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
    ASSEMBLY_DATE,
    AeoGeoRaterTestCase,
    COMPLIANT_ARTICLE,
    FAQ_PROOF_BLOCK,
    PAA_ARTIFACT,
    PAA_PROVENANCE_BLOCK,
    PAA_QUERY,
    finalized_no_author_bom,
    write_paa_fixture,
)

class AeoGeoRaterQualityTests(AeoGeoRaterTestCase):
    def test_delayed_answer_fails_direct_answer_check(self):
        content = COMPLIANT_ARTICLE.replace(
            "HVAC scheduling software helps contractors assign technicians, avoid double-booking, and keep customers updated from one real-time calendar.",
            "Running a service business has always been complicated, and teams face more pressure every year.",
        )
        result = self.rate(content)

        self.assertFalse(result["passed"])
        self.assertFalse(result["checks"]["direct_answer"]["passed"])
        self.assertLess(result["score"], 90)

    def test_low_capsule_coverage_blocks_publishing(self):
        content = COMPLIANT_ARTICLE.replace(
            "HVAC scheduling software gives dispatchers a real-time view of technician availability, active jobs, locations, and urgent service requests. Teams use it to assign work, update schedules, send mobile job details, and notify customers when plans change. Simpro connects scheduling with quoting, inventory, invoicing, and reporting for stronger day-to-day job control.",
            "This section explains scheduling in more detail.",
        ).replace(
            "Contractors should choose scheduling software by matching the system to the work they actually run: service calls, planned maintenance, installations, and quoted project work. The best fit supports mobile updates, recurring jobs, drag-and-drop dispatch, customer notifications, and reporting that shows whether the schedule improved labor use, revenue timing, or profitability.",
            "This section explains selection criteria in more detail.",
        )

        result = self.rate(content)

        self.assertFalse(result["checks"]["capsule_coverage"]["passed"])
        self.assertLess(result["score"], 90)

    def test_faq_answers_outside_40_to_60_words_fail(self):
        content = COMPLIANT_ARTICLE.replace(
            "The best way to schedule HVAC technicians is to use [field service scheduling](https://www.fieldtechnologiesonline.com/) that shows availability, job priority, location, and skill fit. This helps office teams assign work without overloading technicians or missing urgent calls. Mobile updates then keep the schedule accurate as jobs change during the day.",
            "Use [field service scheduling](https://www.fieldtechnologiesonline.com/).",
        )

        result = self.rate(content)

        self.assertFalse(result["checks"]["faq_answer_length"]["passed"])
        self.assertLess(result['score'], 100)
        self.assertFalse(result["passed"])

    def test_faq_checks_are_not_applicable_and_reweighted_for_approved_no_faq(self):
        content = COMPLIANT_ARTICLE.split('\n## Frequently Asked Questions', 1)[0]
        content = content.replace('  - FAQPage\n', '').replace(
            '  - Question and Answer inside FAQPage\n',
            '',
        )

        source_path = write_paa_fixture(self, content)
        paa_artifact = Path(source_path).parents[1] / PAA_ARTIFACT
        result = self.rate_with_bound_experience(
            content,
            {
                'primary_keyword': 'hvac scheduling software',
                'faq_policy_status': 'not_applicable',
            },
            paa_workflow_mode='new',
            paa_expected_query=PAA_QUERY,
            paa_expected_collection_date=ASSEMBLY_DATE,
            paa_artifact=str(paa_artifact),
        )

        for check_name in (
            'faq_questions',
            'faq_answer_length',
            'faq_answer_quality',
            'faq_proof',
        ):
            with self.subTest(check_name=check_name):
                check = result['checks'][check_name]
                self.assertFalse(check['applicable'])
                self.assertEqual(check['status'], 'not_applicable')
        self.assertEqual(result['score'], 100)
        self.assertTrue(result['passed'])

    def test_not_applicable_faq_policy_rejects_visible_faq(self):
        result = self.rate(
            metadata={'faq_policy_status': 'not_applicable'},
        )

        self.assertFalse(result['checks']['faq_policy']['passed'])
        self.assertFalse(result['passed'])

    def test_raw_prevalidated_findings_do_not_suppress_faq_and_paa_runs(self):
        with patch(
            "data_sources.modules.content_scoring.aeo_faq_paa.check_faq_answer_quality",
            return_value=[],
        ) as faq_answer_gate, patch(
            "data_sources.modules.content_scoring.aeo_faq_paa.check_faq_proof",
            return_value=[],
        ) as faq_proof_gate, patch(
            "data_sources.modules.content_scoring.aeo_faq_paa.check_paa_provenance_content",
            return_value=[],
        ) as paa_gate:
            result = self.rate_with_bound_experience(
                prevalidated_gate_findings={
                    "faq_answer_quality": (),
                    "faq_proof": (),
                    "paa_provenance": (),
                }
            )

        faq_answer_gate.assert_called_once()
        faq_proof_gate.assert_called_once()
        paa_gate.assert_called_once()
        self.assertTrue(result['checks']['faq_answer_quality']['passed'])
        self.assertTrue(result['checks']['faq_proof']['passed'])
        self.assertTrue(result['checks']['paa_provenance']['passed'])

    def test_raw_prevalidated_findings_cannot_bypass_faq_and_paa_validation(self):
        content = COMPLIANT_ARTICLE.replace(PAA_PROVENANCE_BLOCK, "").replace(
            FAQ_PROOF_BLOCK,
            "",
        )
        content = re.sub(r"\[([^\]]+)\]\(https?://[^)]+\)", r"\1", content)

        result = rate_aeo_geo(
            content,
            {"primary_keyword": "hvac scheduling software"},
            prevalidated_gate_findings={
                "faq_answer_quality": (),
                "faq_proof": (),
                "paa_provenance": (),
            },
        )

        self.assertFalse(result["checks"]["faq_proof"]["passed"])
        self.assertFalse(result["checks"]["paa_provenance"]["passed"])

    def test_not_applicable_faq_policy_rejects_common_questions_heading(self):
        content = COMPLIANT_ARTICLE.replace(
            '## Frequently Asked Questions',
            '## Common questions',
        )

        result = self.rate(
            content,
            metadata={'faq_policy_status': 'not_applicable'},
        )

        self.assertFalse(result['checks']['faq_policy']['passed'])
        self.assertFalse(result['passed'])

    def test_unsupported_faq_markup_is_a_hard_failure(self):
        content = COMPLIANT_ARTICLE.split('\n## Frequently Asked Questions', 1)[0]
        content = content.replace('  - FAQPage\n', '').replace(
            '  - Question and Answer inside FAQPage\n',
            '',
        )
        content += (
            '\n<details><summary>What does scheduling software do?</summary>'
            'It coordinates work.</details>\n'
        )
        source_path = write_paa_fixture(self, content)
        paa_artifact = Path(source_path).parents[1] / PAA_ARTIFACT

        result = self.rate_with_bound_experience(
            content,
            {
                'primary_keyword': 'hvac scheduling software',
                'faq_policy_status': 'not_applicable',
            },
            paa_workflow_mode='new',
            paa_expected_query=PAA_QUERY,
            paa_expected_collection_date=ASSEMBLY_DATE,
            paa_artifact=str(paa_artifact),
        )

        self.assertFalse(result['checks']['faq_structure']['passed'])
        self.assertFalse(result['passed'])

    def test_bound_assembly_date_controls_freshness_across_machine_dates(self):
        with patch(
            'data_sources.modules.blog_assembly_contract.current_utc_date',
            return_value=date(2099, 1, 2),
        ):
            result = self.rate(
                metadata={'assembly_date': '2099-01-02'},
                content=COMPLIANT_ARTICLE.replace(
                    'Last Updated: 2026-05-22',
                    'Last Updated: 2099-01-02',
                ),
            )

        self.assertEqual(
            result['checks']['metadata']['details']['freshness_status'],
            'valid',
        )

    def test_metadata_requires_canonical_iso_freshness_and_blocks_future_updates(self):
        malformed = COMPLIANT_ARTICLE.replace(
            'Last Updated: 2026-05-22',
            'Last Updated: May 22, 2026',
        )
        malformed_result = self.rate(malformed)
        with patch(
            'data_sources.modules.blog_assembly_contract.current_utc_date',
            return_value=date(2026, 5, 23),
        ):
            mismatch_result = self.rate(
                metadata={'assembly_date': '2026-05-23'},
            )

        self.assertFalse(malformed_result['checks']['metadata']['passed'])
        self.assertEqual(
            malformed_result['checks']['metadata']['details']['freshness_status'],
            'invalid',
        )
        self.assertTrue(mismatch_result['checks']['metadata']['passed'])
        self.assertEqual(
            mismatch_result['checks']['metadata']['details']['freshness_status'],
            'valid',
        )

    def test_missing_author_does_not_require_finalized_bom_for_aeo_metadata(self):
        content = COMPLIANT_ARTICLE.replace('Author: Jordan Lee\n', '').replace(
            '  - Person as author\n',
            '',
        )

        unbound = self.rate(
            content,
            metadata={'author_policy_status': 'not_provided'},
        )
        finalized = self.rate(
            content,
            finalized_bom=finalized_no_author_bom(),
        )

        self.assertTrue(unbound['checks']['metadata']['passed'])
        self.assertEqual(
            unbound['checks']['metadata']['details']['author_policy_status'],
            '',
        )
        self.assertTrue(finalized['checks']['metadata']['passed'])
        self.assertEqual(
            finalized['checks']['metadata']['details']['author_policy_status'],
            'not_provided',
        )
