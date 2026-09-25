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
    AUTHOR_VERIFICATION_BLOCK,
    AeoGeoRaterTestCase,
    COMPLIANT_ARTICLE,
    FAQ_PROOF_BLOCK,
    PAA_PROVENANCE_BLOCK,
    finalized_no_author_bom,
)

class AeoGeoRaterMetadataTests(AeoGeoRaterTestCase):
    def test_no_author_voice_blocks_first_person_singular_outside_quotes(self):
        content = COMPLIANT_ARTICLE.replace('Author: Jordan Lee\n', '').replace(
            '  - Person as author\n',
            '',
        )
        content = content.replace(
            '# HVAC Scheduling Software for Contractors\n',
            '# HVAC Scheduling Software for Contractors\n\nI believe dispatchers should start with technician constraints.\n',
            1,
        )

        result = self.rate(
            content,
            finalized_bom=finalized_no_author_bom(),
        )

        self.assertFalse(result['checks']['author_voice']['passed'])
        self.assertIn(
            'I',
            result['checks']['author_voice']['details']['first_person_terms'],
        )

    def test_no_author_voice_ignores_first_person_inside_markdown_quote(self):
        content = COMPLIANT_ARTICLE.replace('Author: Jordan Lee\n', '').replace(
            '  - Person as author\n',
            '',
        )
        content = content.replace(
            '# HVAC Scheduling Software for Contractors\n',
            '# HVAC Scheduling Software for Contractors\n\n> “I believe dispatchers need one calendar.”\n',
            1,
        )

        result = self.rate(
            content,
            finalized_bom=finalized_no_author_bom(),
        )

        self.assertTrue(result['checks']['author_voice']['passed'])

    def test_no_author_voice_ignores_i_query_parameter_in_public_url(self):
        content = COMPLIANT_ARTICLE.replace('Author: Jordan Lee\n', '').replace(
            '  - Person as author\n',
            '',
        )
        content += (
            '\n[Listen to the episode]'
            '(https://podcasts.apple.com/show/episode?id=1&i=2).\n'
        )

        result = self.rate(
            content,
            finalized_bom=finalized_no_author_bom(),
        )

        self.assertTrue(result['checks']['author_voice']['passed'])

    def test_no_author_voice_ignores_lowercase_i_in_relative_image_url(self):
        content = COMPLIANT_ARTICLE.replace('Author: Jordan Lee\n', '').replace(
            '  - Person as author\n',
            '',
        )
        content += '\n![Official vendor logo](/mya-i-lojy-logo.png)\n'

        result = self.rate(
            content,
            finalized_bom=finalized_no_author_bom(),
        )

        self.assertTrue(result['checks']['author_voice']['passed'])

    def test_no_author_voice_ignores_first_person_inside_unicode_inline_quote(self):
        content = COMPLIANT_ARTICLE.replace('Author: Jordan Lee\n', '').replace(
            '  - Person as author\n',
            '',
        )
        quoted = chr(0x201C) + 'I believe dispatchers need one calendar.' + chr(0x201D)
        content = content.replace(
            '# HVAC Scheduling Software for Contractors\n',
            '# HVAC Scheduling Software for Contractors\n\n' + quoted + '\n',
            1,
        )

        result = self.rate(
            content,
            finalized_bom=finalized_no_author_bom(),
        )

        self.assertTrue(result['checks']['author_voice']['passed'])

    def test_no_author_voice_ignores_first_person_query_headings(self):
        content = COMPLIANT_ARTICLE.replace('Author: Jordan Lee\n', '').replace(
            '  - Person as author\n',
            '',
        )
        content = content.replace(
            '## How should contractors choose scheduling software?',
            '## Should I choose connected scheduling software?',
            1,
        )

        result = self.rate(
            content,
            finalized_bom=finalized_no_author_bom(),
        )

        self.assertTrue(result['checks']['author_voice']['passed'])

    def test_no_author_voice_blocks_first_person_judgment_in_visible_heading(self):
        content = COMPLIANT_ARTICLE.replace('Author: Jordan Lee\n', '').replace(
            '  - Person as author\n',
            '',
        )
        content = content.replace(
            '## How should contractors choose scheduling software?',
            '## Why I recommend connected scheduling software',
            1,
        )

        result = self.rate(
            content,
            finalized_bom=finalized_no_author_bom(),
        )

        self.assertFalse(result['checks']['author_voice']['passed'])
        self.assertIn(
            'I',
            result['checks']['author_voice']['details']['first_person_terms'],
        )

    def test_schema_notes_require_exact_canonical_names_without_splitting_and(self):
        result = self.rate()
        near_match = self.rate(
            COMPLIANT_ARTICLE.replace('  - BlogPosting\n', '  - NotBlogPosting\n')
        )
        short_image_name = self.rate(
            COMPLIANT_ARTICLE.replace(
                '  - ImageObject for the featured image or logo\n',
                '  - ImageObject\n',
            )
        )

        self.assertTrue(result['checks']['schema']['passed'])
        self.assertIn(
            'Question and Answer inside FAQPage',
            result['checks']['schema']['details']['entities'],
        )
        self.assertFalse(near_match['checks']['schema']['passed'])
        self.assertIn(
            'BlogPosting',
            near_match['checks']['schema']['details']['missing_entities'],
        )
        self.assertFalse(short_image_name['checks']['schema']['passed'])
        self.assertIn(
            'ImageObject for the featured image or logo',
            short_image_name['checks']['schema']['details']['missing_entities'],
        )

    def test_schema_video_object_tracks_supported_iframe_and_native_video(self):
        embeds = (
            '<iframe src=https://www.youtube-nocookie.com/embed/dQw4w9WgXcQ title=dispatch-demo></iframe>',
            '<video controls><source src=https://cdn.example.com/dispatch-demo.mp4 type=video/mp4></video>',
        )
        for embed in embeds:
            with self.subTest(embed=embed):
                content = COMPLIANT_ARTICLE.replace(
                    '  - Person as author\n',
                    '  - Person as author\n  - VideoObject\n',
                ) + f'\n{embed}\n'
                result = self.rate(content)

                self.assertTrue(result['checks']['schema']['passed'])
                self.assertTrue(
                    result['checks']['schema']['details']['has_supported_video_embed']
                )

    def test_schema_blocks_malformed_attempted_video_embed(self):
        content = COMPLIANT_ARTICLE + (
            '\n<iframe src="https://www.youtube-nocookie.com/embed/abc123"></iframe>\n'
        )

        result = self.rate(content)

        self.assertFalse(result['checks']['schema']['passed'])
        self.assertTrue(result['checks']['schema']['details']['video_embed_errors'])

    def test_schema_rejects_video_object_for_unsupported_iframe(self):
        content = COMPLIANT_ARTICLE.replace(
            '  - Person as author\n',
            '  - Person as author\n  - VideoObject\n',
        ) + '\n<iframe src=https://example.com/embed/abc123></iframe>\n'

        result = self.rate(content)

        self.assertFalse(result['checks']['schema']['passed'])
        self.assertIn(
            'VideoObject',
            result['checks']['schema']['details']['unexpected_entities'],
        )

    def test_external_link_count_is_diagnostic_not_a_quality_criterion(self):
        content = COMPLIANT_ARTICLE.replace(
            '[Field Technologies Online](https://www.fieldtechnologiesonline.com/)',
            'Field Technologies Online',
        ).replace(
            '[ACHR News](https://www.achrnews.com/)',
            'ACHR News',
        )

        result = self.rate(content)

        check = result['checks']['external_sources']
        self.assertFalse(check['applicable'])
        self.assertEqual(check['status'], 'not_applicable')
        self.assertTrue(check['passed'])

        guidance = " ".join(
            str(check.get(field, ""))
            for field in ("issue", "fix")
        ) + " " + str(check.get("details", {}).get("reason", ""))
        self.assertIn("2 distinct", guidance)
        self.assertIn("quota-only third", guidance)
        self.assertIn("no maximum", guidance)

    def test_faq_proof_repair_respects_machine_assigned_citation_mode(self):
        check = _check_faq_proof(
            "",
            None,
            prevalidated_findings=(
                {
                    "rule_id": "faq_inline_proof_missing",
                    "severity": "error",
                    "question": "What license is required?",
                    "citation_mode": "inline_required",
                },
            ),
        )

        self.assertFalse(check["passed"])
        self.assertIn("citation_mode", check["fix"])
        self.assertIn("inline_required", check["fix"])
        self.assertIn("first visible answer paragraph", check["fix"])
        self.assertIn("natural", check["fix"])
        self.assertIn("quota-only", check["fix"])
        self.assertNotIn("inside each FAQ answer", check["fix"])

    def test_missing_metadata_fails_while_external_link_count_stays_diagnostic(self):
        content = COMPLIANT_ARTICLE.replace("Author: Jordan Lee\n", "").replace(
            "Last Updated: 2026-05-22\n", ""
        )
        content = content.replace("(https://www.fieldtechnologiesonline.com/)", "()")
        content = content.replace("(https://www.achrnews.com/)", "()")
        content = content.replace("(https://www.mckinsey.com/)", "()")
        content = content.replace("(https://www.simprogroup.com/features/scheduling-software)", "()")
        content = content.replace("(https://www.simprogroup.com/features/field-service-mobile-app)", "()")
        content = content.replace("(https://www.simprogroup.com/features/invoicing-software-for-construction)", "()")

        result = self.rate(content)

        self.assertTrue(result["checks"]["external_sources"]["passed"])
        self.assertFalse(result["checks"]["external_sources"]["applicable"])
        self.assertFalse(result["checks"]["metadata"]["passed"])
        self.assertLess(result["score"], 90)

    def test_unbound_no_author_policy_metadata_is_not_authoritative(self):
        content = COMPLIANT_ARTICLE.replace("Author: Jordan Lee\n", "")

        result = self.rate(content, metadata={"author_policy_status": "not_provided"})

        metadata_check = result["checks"]["metadata"]
        self.assertTrue(metadata_check["passed"])
        self.assertFalse(metadata_check["details"]["has_author"])
        self.assertEqual(
            metadata_check["details"]["author_policy_status"],
            "",
        )

    def test_missing_author_without_no_author_policy_still_passes_metadata(self):
        content = COMPLIANT_ARTICLE.replace("Author: Jordan Lee\n", "")

        result = self.rate(content)

        self.assertTrue(result["checks"]["metadata"]["passed"])

    def test_faq_without_linked_proof_blocks_aeo_geo_gate(self):
        content = COMPLIANT_ARTICLE.replace(
            "[field service scheduling](https://www.fieldtechnologiesonline.com/)",
            "a live dispatch calendar",
        ).replace(
            "[field service mobile app](https://www.achrnews.com/)",
            "mobile software",
        ).replace(
            "[field service invoicing](https://www.mckinsey.com/)",
            "invoicing",
        ).replace(FAQ_PROOF_BLOCK, "")

        result = self.rate(content)

        self.assertFalse(result["checks"]["faq_proof"]["passed"])
        self.assertFalse(result["passed"])
        self.assertIn("faq_proof", {issue["check"] for issue in result["issues"]})

    def test_generic_faq_opener_blocks_aeo_geo_and_reduces_score(self):
        content = COMPLIANT_ARTICLE.replace(
            "The best way to schedule HVAC technicians is to use [field service scheduling](https://www.fieldtechnologiesonline.com/) that shows availability, job priority, location, and skill fit. This helps office teams assign work without overloading technicians or missing urgent calls. Mobile updates then keep the schedule accurate as jobs change during the day.",
            "It depends on technician availability, location, job priority and skill fit. [Field service scheduling](https://www.fieldtechnologiesonline.com/) gives office teams one view for assigning urgent calls, balancing workloads, customer commitments and calendar updates when jobs change across the full service schedule for dispatchers and technicians.",
        )

        result = self.rate(content)

        self.assertLess(result["score"], 100)
        self.assertFalse(result["checks"]["faq_answer_quality"]["passed"])
        self.assertFalse(result["passed"])
        self.assertIn(
            "faq_answer_quality",
            {issue["check"] for issue in result["issues"]},
        )

    def test_faq_without_paa_provenance_blocks_aeo_geo_gate(self):
        content = COMPLIANT_ARTICLE.replace(PAA_PROVENANCE_BLOCK, "")

        result = self.rate(
            content,
            proof_sidecar_content=AUTHOR_VERIFICATION_BLOCK + FAQ_PROOF_BLOCK,
        )

        self.assertFalse(result["checks"]["paa_provenance"]["passed"])
        self.assertFalse(result["passed"])
        self.assertIn("paa_provenance", {issue["check"] for issue in result["issues"]})
