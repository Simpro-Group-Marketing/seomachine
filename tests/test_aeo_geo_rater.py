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

from data_sources.modules.aeo_geo_rater import (
    _check_direct_answer,
    _check_eeat_proof,
    _check_faq_questions,
    _has_documented_no_fit_experience_boundary,
    rate_aeo_geo,
)
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
FAQ_PROOF_BLOCK = """
```text
## FAQ Source Policy
- Allowed source classes: neutral, non_competing_expert.
- Competitor-owned FAQ sources: prohibited.
- Status: aligned.

## FAQ Proof Map
- FAQ: What is the best way to schedule HVAC technicians? | URL: https://www.fieldtechnologiesonline.com/ | Source class: neutral | Competitor check: passed | Evidence: scheduling workflow supports availability, priority, location, and skill-fit claims | Status: approved
- FAQ: How does HVAC scheduling software reduce missed appointments? | URL: https://www.achrnews.com/ | Source class: neutral | Competitor check: passed | Evidence: mobile job details and status updates support appointment coordination claims | Status: approved
- FAQ: Should HVAC scheduling connect to invoicing? | URL: https://www.mckinsey.com/ | Source class: neutral | Competitor check: passed | Evidence: invoicing workflow supports completed-work-to-invoice claims | Status: approved
```
"""

COMPLIANT_ARTICLE = """---
Meta Title: HVAC Scheduling Software for Contractors | Simpro
Meta Description: HVAC scheduling software helps contractors assign jobs, avoid double-booking, and keep technicians moving from one real-time calendar.
Primary Keyword: hvac scheduling software
Author: Jordan Lee
Last Updated: 2026-05-22
PAA Workflow Mode: new
PAA Expected Query: hvac scheduling software
PAA Expected Collection Date: 2026-05-22
schema_notes:
  - BlogPosting
  - BreadcrumbList
  - FAQPage
  - Question and Answer inside FAQPage
  - ImageObject for the featured image or logo
  - Organization as publisher reference only, not a separate full schema block
  - Person as author
---

# HVAC Scheduling Software for Contractors

HVAC scheduling software helps contractors assign technicians, avoid double-booking, and keep customers updated from one real-time calendar. For growing trade businesses, the right scheduling workflow connects dispatch, mobile job details, inventory, and invoicing so office teams can protect margins without running the day from spreadsheets.

> **Key Takeaways**
> - HVAC scheduling software should show technician availability, job status, and customer commitments in one dispatch view.
> - Contractors need mobile job details so field teams can finish work without calling the office for every update.
> - The strongest scheduling workflows connect quoting, inventory, invoicing, and reporting instead of stopping at the calendar.

## What does HVAC scheduling software do?

HVAC scheduling software gives dispatchers a real-time view of technician availability, active jobs, locations, and urgent service requests. Teams use it to assign work, update schedules, send mobile job details, and notify customers when plans change. Simpro connects scheduling with quoting, inventory, invoicing, and reporting for stronger day-to-day job control.

The scheduling workflow should make the next best action clear for dispatchers, technicians, and managers. According to [Field Technologies Online](https://www.fieldtechnologiesonline.com/), field teams need real-time visibility to reduce wasted trips and missed updates.

## How should contractors choose scheduling software?

Contractors should choose scheduling software by matching the system to the work they actually run: service calls, planned maintenance, installations, and quoted project work. The best fit supports mobile updates, recurring jobs, drag-and-drop dispatch, customer notifications, and reporting that shows whether the schedule improved labor use, revenue timing, or profitability.

That means the buying process should include workflow testing, not only feature comparison. The [ACHR News](https://www.achrnews.com/) regularly covers HVAC labor constraints, which makes dispatch efficiency a practical operating issue rather than a software preference.

## Why does scheduling affect profit?

Scheduling affects profit because every missed appointment, double-booking, and underprepared site visit creates labor leakage. A strong schedule protects billable hours, keeps technicians focused on the right work, and gives managers earlier warning when jobs are slipping. For HVAC contractors, dispatch discipline shapes margin visibility before the invoice reaches accounting.

The profit impact compounds when scheduling is connected to job costing. Research from [McKinsey](https://www.mckinsey.com/) has shown that field productivity depends on better planning, tighter coordination, and faster information flow across operational teams.

[Schaffer Beacon Mechanical](https://www.simprogroup.com/case-studies/schaffer-beacon-mechanical) shows how field service teams use connected workflows to improve operational control.
""" + PAA_PROVENANCE_BLOCK + FAQ_PROOF_BLOCK + """

## Frequently Asked Questions

### What is the best way to schedule HVAC technicians?

The best way to schedule HVAC technicians is to use [field service scheduling](https://www.fieldtechnologiesonline.com/) that shows availability, job priority, location, and skill fit. This helps office teams assign work without overloading technicians or missing urgent calls. Mobile updates then keep the schedule accurate as jobs change during the day.

### How does HVAC scheduling software reduce missed appointments?

HVAC scheduling software reduces missed appointments by centralizing job details, technician assignments, customer notifications, and status updates. Dispatchers can see conflicts before they become failures, while technicians receive the latest job information through a [field service mobile app](https://www.achrnews.com/). Automated reminders also reduce no-shows and last-minute customer confusion.

### Should HVAC scheduling connect to invoicing?

HVAC scheduling should connect to invoicing because completed work loses value when job details stay trapped in the field. When technician notes, labor time, materials, and approvals flow into [field service invoicing](https://www.mckinsey.com/), office teams can invoice faster. That reduces rework, protects cash flow, and improves job-level reporting.
"""


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
        "data_sources.modules.customer_proof_selector.load_validated_claim_set",
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
    sidecar = PAA_PROVENANCE_BLOCK + "\n## " + stdout.getvalue() + """

## Selected Customer Proof Mining
- Proof: review-capterra-qbo-service-jobs-quotes-invoices | Customer: Capterra owner review with QBO integration | URL: https://www.capterra.com/p/10529/Simpro-Enterprise/reviews/
- Checked for: exact quotes, customer metrics, POV story, workflow themes
- Usable quotes found: none found
- Usable metrics found: none found
- Usable POV/story found: Megan B describes using service jobs, quotes, invoices, and QBO integration.
- Recommended use: identity-backed experience story in the scheduling workflow section
- Final use in copy: Megan B experience story in the scheduling workflow section
- Excluded proof: exact review wording and ratings
- Status: approved
"""
    sidecar_path = root / "validation-hvac-scheduling.md"
    sidecar_path.write_text(sidecar, encoding="utf-8")
    return sidecar, sidecar_path


class AeoGeoRaterTests(unittest.TestCase):
    def test_rate_api_accepts_bound_quality_context_for_no_faq_article(self):
        no_faq = '''---
primary_keyword: field service scheduling
last_updated: 2026-05-22
schema_notes:
  - BlogPosting
  - BreadcrumbList
  - ImageObject for the featured image or logo
  - Organization as publisher reference only, not a separate full schema block
---

# Field Service Scheduling

Field service scheduling helps dispatchers assign work from one calendar.

## Dispatch workflow

Field service scheduling gives teams a reliable view of current work and technician capacity. Dispatchers can match urgent jobs to available technicians, update assignments as conditions change, and keep office and field staff working from the same operating picture throughout the service day.
'''
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
            """## Frequently asked questions about job sheets

### Do job sheets need to be signed by the customer?

This answer has enough detail for the question parser.

### Can a job sheet be used as proof of work?

This answer has enough detail for the question parser.

### When should a job sheet be completed?

This answer has enough detail for the question parser.
"""
        )

        self.assertTrue(result["passed"])
        self.assertEqual(result["details"]["question_count"], 3)

    def write_no_fit_selector_evidence(
        self,
        root: Path,
        *,
        empty_story_slate: bool = False,
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
        stdout = StringIO()
        stderr = StringIO()
        with patch(
            "data_sources.modules.customer_proof_selector.load_validated_claim_set",
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
                    (
                        f"experience_story={story_id}:"
                        + (
                            "no eligible candidate exists because the approved proof inventory "
                            "has no identity-backed story for this article objective"
                            if empty_story_slate
                            else (
                                "omitted because this software-user story does not substantiate "
                                "the article's job-sheet definition objective"
                            )
                        )
                    ),
                    "--evidence-output",
                    str(evidence_path),
                ]
            )
        self.assertEqual(exit_code, 0, stderr.getvalue())
        sidecar = """## E-E-A-T Proof Map
- First-hand evidence decision: Selected: [none] because no approved customer story in the selector slate substantiates this article objective.

## """ + stdout.getvalue()
        sidecar_path = root / "validation-job-sheets.md"
        sidecar_path.write_text(sidecar, encoding="utf-8")
        return sidecar, sidecar_path, index_path

    def write_bound_experience_story_evidence(
        self,
        root: Path,
    ) -> tuple[str, Path]:
        return write_bound_experience_story_evidence(self, root)

    def test_no_fit_boundary_accepts_current_rerun_verified_selector_evidence(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            sidecar, sidecar_path, _index_path = self.write_no_fit_selector_evidence(root)
            with patch(
                "data_sources.modules.customer_proof_selector.load_validated_claim_set",
                new=load_validated_claim_set_for_unit_test,
            ):
                result = _has_documented_no_fit_experience_boundary(
                    sidecar,
                    proof_sidecar_path=str(sidecar_path),
                )

        self.assertTrue(result)

    def test_no_fit_boundary_accepts_rerun_verified_empty_story_slate(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            sidecar, sidecar_path, _index_path = self.write_no_fit_selector_evidence(
                root,
                empty_story_slate=True,
            )
            with patch(
                "data_sources.modules.customer_proof_selector.load_validated_claim_set",
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
                "data_sources.modules.customer_proof_selector.load_validated_claim_set",
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
                "data_sources.modules.customer_proof_selector.load_validated_claim_set",
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
                "data_sources.modules.customer_proof_selector.load_validated_claim_set",
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

    def test_no_fit_boundary_rejects_sidecar_candidate_list_mismatch(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            sidecar, sidecar_path, _index_path = self.write_no_fit_selector_evidence(root)
            sidecar = sidecar.replace(
                "Top candidates: [review-capterra-qbo-service-jobs-quotes-invoices]",
                "Top candidates: [invented-proof]",
            )
            sidecar_path.write_text(sidecar, encoding="utf-8")
            with patch(
                "data_sources.modules.customer_proof_selector.load_validated_claim_set",
                new=load_validated_claim_set_for_unit_test,
            ):
                result = _has_documented_no_fit_experience_boundary(
                    sidecar,
                    proof_sidecar_path=str(sidecar_path),
                )

        self.assertFalse(result)
    def test_no_fit_boundary_rejects_unverifiable_typed_hash(self):
        sidecar = """## Customer proof selector

- Selector command: python data_sources/modules/customer_proof_selector.py "job sheets for UK field service teams" --title "What is a job sheet?" --objective "Define job sheets" --require-eeat-story --slate --roles metric,quote,theme,experience_story --limit 10
- Selector execution: completed | Exit code: 0 | Output SHA-256: aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa

## E-E-A-T Proof Map
- First-hand evidence decision: Selected: [none] because no approved, brand-appropriate customer story supports this article objective.

## Customer Proof Slate
- Role: experience_story | Top candidates: [none] | Selected: [none] | Rejected stronger candidates: [none: no eligible candidate exists because the proof index has no brand-appropriate story for this article]
"""

        self.assertFalse(_has_documented_no_fit_experience_boundary(sidecar))

    def test_no_fit_boundary_rejects_a_copied_selector_command_without_receipt(self):
        sidecar = """## Customer proof selector

- Selector command: python data_sources/modules/customer_proof_selector.py "job sheets for UK field service teams" --title "What is a job sheet?" --objective "Define job sheets" --require-eeat-story --slate --roles metric,quote,theme,experience_story --limit 10

## E-E-A-T Proof Map
- First-hand evidence decision: Selected: [none] because no approved, brand-appropriate customer story supports this article objective.

## Customer Proof Slate
- Role: experience_story | Top candidates: [none] | Selected: [none] | Rejected stronger candidates: [none: no eligible candidate exists because the proof index has no brand-appropriate story for this article]
"""

        self.assertFalse(_has_documented_no_fit_experience_boundary(sidecar))

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
                "data_sources.modules.customer_proof_selector.load_validated_claim_set",
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

    def test_direct_answer_skips_standalone_image_placeholder(self):
        content = COMPLIANT_ARTICLE.replace(
            "# HVAC Scheduling Software for Contractors\n\n",
            "# HVAC Scheduling Software for Contractors\n\n"
            f"{PRODUCTION_IMAGE_MARKER}\n\n",
        )

        result = self.rate(content)
        first_two = result["checks"]["direct_answer"]["details"]["first_two_sentences"]

        self.assertTrue(result["checks"]["direct_answer"]["passed"])
        self.assertTrue(first_two.startswith("HVAC scheduling software helps contractors"))
        self.assertNotIn("IMAGE PLACEHOLDER", first_two)

    def test_direct_answer_skips_original_hero_image_placeholder(self):
        content = COMPLIANT_ARTICLE.replace(
            "# HVAC Scheduling Software for Contractors\n\n",
            "# HVAC Scheduling Software for Contractors\n\n"
            f"{PRODUCTION_IMAGE_MARKER}\n\n",
        )

        result = self.rate(content)
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
        content = """## FAQ

### What is field service management software?

Answer.

### Who uses field service management software?

Answer.

### How does field service management software help dispatch?

Answer.

### How much does field service management software cost?

Answer.

### Which field service management software fits growing contractors?

Answer.

### Should I choose an all-in-one FSM platform or a simpler scheduling app?

Answer.
"""

        result = _check_faq_questions(content)

        self.assertTrue(result["passed"])
        self.assertEqual(result["details"]["question_count"], 6)

    def test_faq_question_gate_has_no_fixed_minimum_or_maximum(self):
        one_question = """## Common questions

### What does scheduling software do?

Answer.
"""
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
        content = '''## FAQ

### What does scheduling software do?

Answer.

#### How should dispatchers assign urgent work?

Answer.

##### Should technicians receive mobile updates?

Answer.
'''

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
                "data_sources.modules.customer_proof_selector.load_validated_claim_set",
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
        proof_sidecar = PAA_PROVENANCE_BLOCK + """
```text
Review Story Selection
- Article title: HVAC Scheduling Software for Contractors
- Content objective: explain connected field-service workflows
- Selected story: review-capterra-megan-qbo-quotes | Identity: Megan B | Platform: Capterra | URL: https://www.capterra.com/p/10529/Simpro-Enterprise/reviews/ | Workflow story: owner describes service jobs, recurring jobs, quotes, invoices, and QBO integration | Status: approved | Use: E-E-A-T experience story
- Article link requirement: same paragraph as review-derived paraphrase must link to the selected public review URL
```
"""

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
        proof_sidecar = PAA_PROVENANCE_BLOCK + """
```text
E-E-A-T Proof Map
- Experience proof: The rewrite uses first-party ClockShark workflow evidence from https://www.clockshark.com/blog/construction-draw-schedule and https://www.clockshark.com/tour/job-management. No customer quote, customer metric, or review story appears in public copy. | Status: approved for public use
- Expertise proof: The rewrite uses source-backed workflow explanation plus ClockShark construction and job-management pages.
```
"""

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
        proof_sidecar = PAA_PROVENANCE_BLOCK + """
## E-E-A-T Proof Map
- Experience proof: URL: https://example.com/invented | Proof type: identity-backed experience | Evidence: invented customer workflow story | Status: approved
"""

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
                "data_sources.modules.customer_proof_selector.load_validated_claim_set",
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
                "data_sources.modules.customer_proof_selector.load_validated_claim_set",
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
            """
```text
E-E-A-T Proof Map
- First-hand evidence decision: Selected: [none]. No approved identity-backed source in the selector slate substantiates women choosing or working in the ranked trades.
```

```text
Customer Proof Slate
- Role: experience_story | Top candidates: [review-capterra-trades-sme-job-costing-xero-qbo] | Selected: [none] | Rejected stronger candidates: [review-capterra-trades-sme-job-costing-xero-qbo: omitted because this software-user story does not substantiate the article's women-in-trades career objective]
```
"""
        )
        details = result["checks"]["eeat_proof"]["details"]

        self.assertFalse(result["checks"]["eeat_proof"]["passed"])
        self.assertNotIn(
            "documented_no_fit_experience_boundary",
            details["experience_signals"],
        )

    def test_documented_no_fit_requires_substantive_first_hand_reason(self):
        result = self.rate_without_customer_experience(
            """
```text
E-E-A-T Proof Map
- First-hand evidence decision: Selected: [none]. No fit.
```

```text
Customer Proof Slate
- Role: experience_story | Top candidates: [review-capterra-trades-sme-job-costing-xero-qbo] | Selected: [none] | Rejected stronger candidates: [review-capterra-trades-sme-job-costing-xero-qbo: omitted because this software-user story does not substantiate the article's women-in-trades career objective]
```
"""
        )

        self.assertFalse(result["checks"]["eeat_proof"]["passed"])

    def test_documented_no_fit_requires_experience_story_rejection_reason(self):
        result = self.rate_without_customer_experience(
            """
```text
E-E-A-T Proof Map
- First-hand evidence decision: Selected: [none]. No approved identity-backed source in the selector slate substantiates women choosing or working in the ranked trades.
```

```text
Customer Proof Slate
- Role: experience_story | Top candidates: [review-capterra-trades-sme-job-costing-xero-qbo] | Selected: [none] | Rejected stronger candidates: [none]
```
"""
        )

        self.assertFalse(result["checks"]["eeat_proof"]["passed"])

    def test_documented_no_fit_rejects_non_substantive_candidate_reason(self):
        result = self.rate_without_customer_experience(
            """
```text
E-E-A-T Proof Map
- First-hand evidence decision: Selected: [none]. No approved identity-backed source in the selector slate substantiates women choosing or working in the ranked trades.
```

```text
Customer Proof Slate
- Role: experience_story | Top candidates: [x] | Selected: [none] | Rejected stronger candidates: [x: y]
```
"""
        )

        self.assertFalse(result["checks"]["eeat_proof"]["passed"])

    def test_documented_no_fit_requires_a_real_top_candidate(self):
        result = self.rate_without_customer_experience(
            """
```text
E-E-A-T Proof Map
- First-hand evidence decision: Selected: [none]. No approved identity-backed source in the selector slate substantiates women choosing or working in the ranked trades.
```

```text
Customer Proof Slate
- Role: experience_story | Top candidates: [none] | Selected: [none] | Rejected stronger candidates: [none: omitted because this placeholder story does not substantiate the article's women-in-trades career objective]
```
"""
        )

        self.assertFalse(result["checks"]["eeat_proof"]["passed"])

    def test_documented_no_fit_rejects_null_pseudo_candidate(self):
        result = self.rate_without_customer_experience(
            """
```text
E-E-A-T Proof Map
- First-hand evidence decision: Selected: [none]. No approved identity-backed source in the selector slate substantiates women choosing or working in the ranked trades.
```

```text
Customer Proof Slate
- Role: experience_story | Top candidates: [null] | Selected: [none] | Rejected stronger candidates: [null: omitted because this placeholder story does not substantiate the article's women-in-trades career objective]
```
"""
        )

        self.assertFalse(result["checks"]["eeat_proof"]["passed"])

    def test_documented_no_fit_rejects_unknown_proof_id(self):
        result = self.rate_without_customer_experience(
            """
```text
E-E-A-T Proof Map
- First-hand evidence decision: Selected: [none]. No approved identity-backed source in the selector slate substantiates women choosing or working in the ranked trades.
```

```text
Customer Proof Slate
- Role: experience_story | Top candidates: [review-capterra-invented-proof-id] | Selected: [none] | Rejected stronger candidates: [review-capterra-invented-proof-id: omitted because this invented story does not substantiate the article's women-in-trades career objective]
```
"""
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
        "data_sources.modules.aeo_geo_rater._customer_proof_ids",
        return_value=frozenset(),
    )
    def test_documented_no_fit_fails_closed_when_proof_index_is_unavailable(
        self,
        _proof_ids,
    ):
        result = self.rate_without_customer_experience(
            """
```text
E-E-A-T Proof Map
- First-hand evidence decision: Selected: [none]. No approved identity-backed source in the selector slate substantiates women choosing or working in the ranked trades.
```

```text
Customer Proof Slate
- Role: experience_story | Top candidates: [review-capterra-trades-sme-job-costing-xero-qbo] | Selected: [none] | Rejected stronger candidates: [review-capterra-trades-sme-job-costing-xero-qbo: omitted because this software-user story does not substantiate the article's women-in-trades career objective]
```
"""
        )

        self.assertFalse(result["checks"]["eeat_proof"]["passed"])

    def test_aggregate_workforce_statistics_do_not_satisfy_experience(self):
        result = self.rate_without_customer_experience(
            """
```text
E-E-A-T Proof Map
- Experience proof: URL: https://www.apprenticeship.gov/sites/default/files/DOLIndFSWomen_043024-508.pdf | Evidence: aggregate workforce participation statistics, not a customer story, testimonial, or individual lived-experience claim. | Status: approved
```
"""
        )

        self.assertFalse(result["checks"]["eeat_proof"]["passed"])
        self.assertNotIn(
            "sidecar_experience_proof",
            result["checks"]["eeat_proof"]["details"]["experience_signals"],
        )

    def test_numeric_apprenticeship_evidence_does_not_satisfy_experience(self):
        result = self.rate_without_customer_experience(
            """
```text
E-E-A-T Proof Map
- Experience proof: URL: https://www.apprenticeship.gov/data-and-statistics | Evidence: 108,829 women were active apprentices in FY 2023. | Status: approved
```
"""
        )

        self.assertFalse(result["checks"]["eeat_proof"]["passed"])
        self.assertNotIn(
            "sidecar_experience_proof",
            result["checks"]["eeat_proof"]["details"]["experience_signals"],
        )

    def test_unavailable_first_hand_evidence_does_not_satisfy_experience(self):
        result = self.rate_without_customer_experience(
            """
```text
E-E-A-T Proof Map
- Experience proof: URL: https://example.com/source | Evidence: First-hand evidence is not available. | Status: approved
```
"""
        )

        self.assertFalse(result["checks"]["eeat_proof"]["passed"])
        self.assertNotIn(
            "sidecar_experience_proof",
            result["checks"]["eeat_proof"]["details"]["experience_signals"],
        )

    def test_post_negated_first_hand_evidence_does_not_satisfy_experience(self):
        result = self.rate_without_customer_experience(
            """
```text
E-E-A-T Proof Map
- Experience proof: URL: https://example.com/source | Evidence: The article uses first-hand evidence, but it is unavailable. | Status: approved for public use
```
"""
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
            """
```text
E-E-A-T Proof Map
- Experience proof: URL: https://example.com/source | Evidence: The article uses first-hand experience evidence from an identity-backed public account. | Status: approved
```
"""
        )

        self.assertFalse(result["checks"]["eeat_proof"]["passed"])
        self.assertNotIn(
            "sidecar_experience_proof",
            result["checks"]["eeat_proof"]["details"]["experience_signals"],
        )

    def test_generic_experience_proof_type_requires_exact_allowlist_value(self):
        result = self.rate_without_customer_experience(
            """
```text
E-E-A-T Proof Map
- Experience proof: URL: https://example.com/source | Proof type: first-hand evidence but unavailable | Evidence: The article uses first-hand evidence. | Status: approved
```
"""
        )

        self.assertFalse(result["checks"]["eeat_proof"]["passed"])

    def test_experience_proof_without_status_does_not_satisfy_experience(self):
        result = self.rate_without_customer_experience(
            """
```text
E-E-A-T Proof Map
- Experience proof: URL: https://example.com/source | Evidence: The article uses first-hand experience evidence from an identity-backed public account.
```
"""
        )

        self.assertFalse(result["checks"]["eeat_proof"]["passed"])
        self.assertNotIn(
            "sidecar_experience_proof",
            result["checks"]["eeat_proof"]["details"]["experience_signals"],
        )

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
            "data_sources.modules.aeo_geo_rater.check_faq_answer_quality",
            return_value=[],
        ) as faq_answer_gate, patch(
            "data_sources.modules.aeo_geo_rater.check_faq_proof",
            return_value=[],
        ) as faq_proof_gate, patch(
            "data_sources.modules.aeo_geo_rater.check_paa_provenance_content",
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

    def test_metadata_requires_canonical_iso_freshness_and_matches_assembly_date(self):
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
        self.assertFalse(mismatch_result['checks']['metadata']['passed'])
        self.assertEqual(
            mismatch_result['checks']['metadata']['details']['freshness_status'],
            'assembly_date_mismatch',
        )

    def test_missing_author_requires_validated_finalized_bom_no_author_policy(self):
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

        self.assertFalse(unbound['checks']['metadata']['passed'])
        self.assertTrue(finalized['checks']['metadata']['passed'])
        self.assertEqual(
            finalized['checks']['metadata']['details']['author_policy_status'],
            'not_provided',
        )

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
        self.assertFalse(metadata_check["passed"])
        self.assertFalse(metadata_check["details"]["has_author"])
        self.assertEqual(
            metadata_check["details"]["author_policy_status"],
            "",
        )

    def test_missing_author_without_no_author_policy_still_fails_metadata(self):
        content = COMPLIANT_ARTICLE.replace("Author: Jordan Lee\n", "")

        result = self.rate(content)

        self.assertFalse(result["checks"]["metadata"]["passed"])

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

        result = self.rate(content)

        self.assertFalse(result["checks"]["paa_provenance"]["passed"])
        self.assertFalse(result["passed"])
        self.assertIn("paa_provenance", {issue["check"] for issue in result["issues"]})


if __name__ == "__main__":
    unittest.main()
