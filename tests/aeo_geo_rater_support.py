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


PAA_ARTIFACT = "research/paa-questions-hvac-scheduling-2026-05-22.md"
PAA_QUERY = 'hvac scheduling software'
ASSEMBLY_DATE = '2026-05-22'
PRODUCTION_IMAGE_MARKER = (
    '[IMAGE PLACEHOLDER — ORIGINAL HERO: retain immediately before the '
    'introduction | source: https://example.com/hero.jpg | '
    'alt: "Woman smiling in navy work overalls" | render target: '
    '819 × 461 px; resize and compress before upload]'
)
PAA_PROVENANCE_BLOCK = f"""
```text
PAA/FAQ Provenance
- Source: answersocrates
- Artifact: {PAA_ARTIFACT}
- Selected questions:
  - What is the best way to schedule HVAC technicians?
  - How does HVAC scheduling software reduce missed appointments?
  - Should HVAC scheduling connect to invoicing?
```
"""
FAQ_PROOF_BLOCK = fixture_text("content_evidence:test_aeo_geo_rater-48-1")
AUTHOR_VERIFICATION_BLOCK = """
## Author Verification
- Author: Jordan Lee | URL: https://www.simprogroup.com/authors/jordan-lee | Evidence: Author profile reviewed | Checked date: 2026-08-06 | Status: verified
"""

COMPLIANT_ARTICLE = fixture_text("content_evidence:test_aeo_geo_rater-62-10") + PAA_PROVENANCE_BLOCK + FAQ_PROOF_BLOCK + fixture_text("content_evidence:test_aeo_geo_rater-109-2")


def write_paa_fixture(test_case: unittest.TestCase, content: str) -> str:
    temp_dir = TemporaryDirectory()
    test_case.addCleanup(temp_dir.cleanup)
    root = Path(temp_dir.name)
    artifact = root / PAA_ARTIFACT
    artifact.parent.mkdir(parents=True, exist_ok=True)
    artifact.write_text(
        "\n".join(
            [
                "# AnswerSocrates PAA Questions",
                "",
                "What is the best way to schedule HVAC technicians?",
                "How does HVAC scheduling software reduce missed appointments?",
                "Should HVAC scheduling connect to invoicing?",
            ]
        ),
        encoding="utf-8",
    )
    article_path = root / "drafts" / "hvac-scheduling-software.md"
    article_path.parent.mkdir(parents=True, exist_ok=True)
    article_path.write_text(content, encoding="utf-8")
    artifact.write_text(
        json.dumps(
            build_answersocrates_fixture(
                root,
                query=PAA_QUERY,
                collection_date=ASSEMBLY_DATE,
                questions=(
                    "What is the best way to schedule HVAC technicians?",
                    "How does HVAC scheduling software reduce missed appointments?",
                    "Should HVAC scheduling connect to invoicing?",
                ),
                run_id="aeo-rater-fixture",
            ),
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding='utf-8',
    )
    return str(article_path)


def finalized_no_author_bom():
    return {
        'schema': 'simpro-blog-assembly-bom/v1',
        'lifecycle_state': 'final',
        'author_policy': {
            'status': 'not_provided',
            'name': '',
            'frontmatter_author_required': False,
            'schema_person_required': False,
            'named_author_voice_allowed': False,
        },
    }


def finalized_non_connector_bom():
    bom = finalized_no_author_bom()
    bom['connector_binding'] = {
        'status': 'not_applicable',
        'reason': 'Final article contains no Simpro brand, URL, or connector-sensitive language.',
    }
    return bom


def write_bound_experience_story_evidence(
    test_case: unittest.TestCase,
    root: Path,
) -> tuple[str, Path]:
    index_path, ledger_path = write_selector_fixture(root)
    pack_path, receipt_path = write_context_receipt_fixture(root, index_path)
    evidence_path = root / "selector-evidence.json"
    stdout = StringIO()
    stderr = StringIO()
    with patch(
        "data_sources.modules.customer_proof.connector_inputs.load_validated_claim_set",
        new=load_validated_claim_set_for_unit_test,
    ), redirect_stdout(stdout), redirect_stderr(stderr):
        exit_code = run_customer_proof_selector(
            [
                "hvac scheduling software for contractors",
                "--index",
                str(index_path),
                "--ledger",
                str(ledger_path),
                "--context-pack",
                str(pack_path),
                "--context-receipt",
                str(receipt_path),
                "--evidence-output",
                str(evidence_path),
                "--article-slug",
                "hvac-scheduling-software",
                "--title",
                "HVAC Scheduling Software for Contractors",
                "--objective",
                "Explain connected scheduling workflows",
                "--slate",
                "--roles",
                "metric,quote,theme,experience_story",
                "--require-eeat-story",
                "--limit",
                "10",
                "--selected",
                "experience_story=review-capterra-qbo-service-jobs-quotes-invoices",
            ]
        )
    test_case.assertEqual(exit_code, 0, stderr.getvalue())
    sidecar = PAA_PROVENANCE_BLOCK + "\n## " + stdout.getvalue() + fixture_text("content_evidence:test_aeo_geo_rater-228-3")
    sidecar_path = root / "validation-hvac-scheduling.md"
    sidecar_path.write_text(sidecar, encoding="utf-8")
    return sidecar, sidecar_path



class AeoGeoRaterTestCase(unittest.TestCase):
    def write_no_fit_selector_evidence(
        self,
        root: Path,
        *,
        empty_story_slate: bool = False,
        rejection_reason: str | None = None,
    ) -> tuple[str, Path, Path]:
        index_path, ledger_path = write_selector_fixture(root)
        if empty_story_slate:
            index = json.loads(index_path.read_text(encoding="utf-8"))
            index["proof"] = [
                row for row in index["proof"] if not row.get("review_story")
            ]
            index_path.write_text(json.dumps(index), encoding="utf-8")
        pack_path, receipt_path = write_context_receipt_fixture(root, index_path)
        evidence_path = root / "selector-evidence.json"
        story_id = (
            "none"
            if empty_story_slate
            else "review-capterra-qbo-service-jobs-quotes-invoices"
        )
        rejection_reason = rejection_reason or (
            "no eligible candidate exists because the approved proof inventory "
            "has no identity-backed story for this article objective"
            if empty_story_slate
            else (
                "omitted because this software-user story does not substantiate "
                "the article's job-sheet definition objective"
            )
        )
        stdout = StringIO()
        stderr = StringIO()
        with patch(
            "data_sources.modules.customer_proof.connector_inputs.load_validated_claim_set",
            new=load_validated_claim_set_for_unit_test,
        ), redirect_stdout(stdout), redirect_stderr(stderr):
            exit_code = run_customer_proof_selector(
                [
                    "job sheets for UK field service teams",
                    "--index",
                    str(index_path),
                    "--ledger",
                    str(ledger_path),
                    "--context-pack",
                    str(pack_path),
                    "--context-receipt",
                    str(receipt_path),
                    "--title",
                    "What is a job sheet?",
                    "--objective",
                    "Define job sheets",
                    "--slate",
                    "--roles",
                    "experience_story",
                    "--require-eeat-story",
                    "--limit",
                    "10",
                    "--selected",
                    "experience_story=none",
                    "--reject",
                    f"experience_story={story_id}:{rejection_reason}",
                    "--evidence-output",
                    str(evidence_path),
                ]
            )
        self.assertEqual(exit_code, 0, stderr.getvalue())
        sidecar = fixture_text("content_evidence:test_aeo_geo_rater-384-12") + stdout.getvalue()
        sidecar_path = root / "validation-job-sheets.md"
        sidecar_path.write_text(sidecar, encoding="utf-8")
        return sidecar, sidecar_path, index_path

    def write_bound_experience_story_evidence(
        self,
        root: Path,
    ) -> tuple[str, Path]:
        return write_bound_experience_story_evidence(self, root)

    def rate(self, content: str = COMPLIANT_ARTICLE, metadata=None, **kwargs):
        merged_metadata = {"primary_keyword": "hvac scheduling software"}
        if metadata:
            merged_metadata.update(metadata)
        kwargs.setdefault('paa_workflow_mode', 'new')
        kwargs.setdefault('paa_expected_query', PAA_QUERY)
        kwargs.setdefault('paa_expected_collection_date', ASSEMBLY_DATE)
        kwargs.setdefault('paa_expected_run_id', 'aeo-rater-fixture')
        return rate_aeo_geo(
            content,
            merged_metadata,
            source_path=write_paa_fixture(self, content),
            **kwargs,
        )
    def rate_with_bound_experience(
        self,
        content: str = COMPLIANT_ARTICLE,
        metadata=None,
        *,
        proof_sidecar_suffix: str = "",
        **kwargs,
    ):
        content = content.replace(
            "\n[Schaffer Beacon Mechanical](https://www.simprogroup.com/case-studies/schaffer-beacon-mechanical) shows how field service teams use connected workflows to improve operational control.\n",
            "\n[Megan B's Capterra review](https://www.capterra.com/p/10529/Simpro-Enterprise/reviews/) describes using service jobs, quotes, invoices, and QBO integration in one connected workflow.\n",
        )
        merged_metadata = {"primary_keyword": "hvac scheduling software"}
        if metadata:
            merged_metadata.update(metadata)
        kwargs.setdefault("paa_workflow_mode", "new")
        kwargs.setdefault("paa_expected_query", PAA_QUERY)
        kwargs.setdefault("paa_expected_collection_date", ASSEMBLY_DATE)
        kwargs.setdefault("paa_expected_run_id", "aeo-rater-fixture")
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            proof_sidecar, proof_sidecar_path = (
                self.write_bound_experience_story_evidence(root)
            )
            proof_sidecar += proof_sidecar_suffix
            proof_sidecar_path.write_text(proof_sidecar, encoding="utf-8")
            with patch(
                "data_sources.modules.customer_proof.connector_inputs.load_validated_claim_set",
                new=load_validated_claim_set_for_unit_test,
            ):
                return rate_aeo_geo(
                    content,
                    merged_metadata,
                    source_path=write_paa_fixture(self, content),
                    proof_sidecar_content=proof_sidecar,
                    proof_sidecar_path=str(proof_sidecar_path),
                    **kwargs,
                )

    def rate_without_customer_experience(self, proof_sidecar: str):
        content = COMPLIANT_ARTICLE.replace(
            "\n[Schaffer Beacon Mechanical](https://www.simprogroup.com/case-studies/schaffer-beacon-mechanical) shows how field service teams use connected workflows to improve operational control.\n",
            "\nThe article omits customer stories because none supports its objective.\n",
        )
        return rate_aeo_geo(
            content,
            {"primary_keyword": "hvac scheduling software"},
            source_path=write_paa_fixture(self, content),
            proof_sidecar_content=PAA_PROVENANCE_BLOCK + proof_sidecar,
            paa_expected_query=PAA_QUERY,
            paa_expected_collection_date=ASSEMBLY_DATE,
            paa_expected_run_id="aeo-rater-fixture",
        )
