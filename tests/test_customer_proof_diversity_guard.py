from tests.fixture_text import fixture_text
import json
import unittest
from contextlib import redirect_stdout
from datetime import date
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from data_sources.modules.customer_proof_diversity_guard import (
    _stronger_slate_candidate_findings,
    check_content as _check_content,
    check_file,
    should_fail,
)
from data_sources.modules.customer_proof_selector import _main as selector_main
from data_sources.modules.nonvault_customer_proof_selector import (
    build_nonvault_customer_proof_slate,
    write_nonvault_selector_evidence,
)
from tests.nonvault_proof_fixture import write_nonvault_proof_inputs
from tests.test_customer_proof_selector import write_context_receipt_fixture
from tests.vault_context_fixture import load_validated_claim_set_for_unit_test

ARTICLE_WITH_CASE_STUDY = fixture_text("content_evidence:test_customer_proof_diversity_guard-20-1")
ARTICLE_WITH_CLOCKSHARK_CASE_STUDY = fixture_text("content_evidence:test_customer_proof_diversity_guard-25-2")
CUSTOMER_LINK_URL = "https://www.simprogroup.com/customers/acme-services"


def check_content(*args, **kwargs):
    kwargs.setdefault("reference_date", date(2026, 8, 28))
    return _check_content(*args, **kwargs)


def test_nonconnector_customer_story_accepts_hash_bound_nonvault_selector(tmp_path):
    index_path, ledger_path = write_nonvault_proof_inputs(tmp_path / "proof")
    evidence_path = tmp_path / "research" / "nonvault-proof.json"
    _, digest, roles = write_nonvault_selector_evidence(
        evidence_path,
        topic="employee time theft",
        brand="ClockShark",
        title="Employee Time Theft",
        objective="Prevent buddy punching fairly.",
        article_slug="employee-time-theft",
        roles=("metric", "quote", "theme", "experience_story"),
        require_eeat_story=True,
        limit=10,
        reference_date=date(2026, 8, 28),
        selected_overrides={
            "theme": "clockshark-customer-story-mabrys-electrical-service",
            "experience_story": "clockshark-customer-story-mabrys-electrical-service",
        },
        rejected_overrides={},
        index_path=index_path,
        ledger_path=ledger_path,
    )
    article = tmp_path / "article.md"
    article.write_text(
        "# Employee Time Theft\n\n"
        "Mabry's Electrical Service reported buddy punching before changing its "
        "timekeeping process. The [customer story]"
        "(https://www.clockshark.com/testimonials/mabry-s-electrical-service-inc) "
        "is one company's experience, not a guaranteed result.\n",
        encoding="utf-8",
    )
    sidecar = tmp_path / "validation.md"
    sidecar.write_text(
        "## "
        + build_nonvault_customer_proof_slate(
            selector_command=(
                'python data_sources/modules/nonvault_customer_proof_selector.py '
                '"employee time theft"'
            ),
            roles=roles,
            evidence_path=str(evidence_path),
            evidence_sha256=digest,
        )
        + "\n## Selected Customer Proof Mining\n"
        "- Proof: clockshark-customer-story-mabrys-electrical-service | Customer: Mabry's Electrical Service | URL: https://www.clockshark.com/testimonials/mabry-s-electrical-service-inc\n"
        "- Checked for: exact quotes, customer metrics, POV story, workflow themes\n"
        "- Usable quotes found: none found\n"
        "- Usable metrics found: none found\n"
        "- Usable POV/story found: buddy-punching workflow story\n"
        "- Recommended use: paraphrased experience story\n"
        "- Final use in copy: paraphrased experience story\n"
        "- Excluded proof: exact quotes and metrics are not approved\n"
        "- Status: approved\n\n"
        "## Customer Proof Pack\n"
        "- Pack status: ready\n"
        "- Customer Story proof path: Mabry's Electrical Service | URL: https://www.clockshark.com/testimonials/mabry-s-electrical-service-inc\n"
        "- Approved quotes: none used\n"
        "- Approved metrics: none used\n"
        "- Use in copy: paraphrased customer experience\n"
        "- Claims excluded: exact quotes, metrics, and ratings\n\n"
        "## Customer Proof Selection Decision\n"
        "- Selector command: python data_sources/modules/nonvault_customer_proof_selector.py \"employee time theft\"\n"
        "- Selected proof: clockshark-customer-story-mabrys-electrical-service | Customer: Mabry's Electrical Service | URL: https://www.clockshark.com/testimonials/mabry-s-electrical-service-inc | Use: experience story\n"
        "- Rejected stronger candidates: none\n"
        "- Final use in copy: paraphrased experience story\n",
        encoding="utf-8",
    )

    findings = check_file(
        article,
        proof_sidecar=sidecar,
        ledger_path=ledger_path,
        proof_index_path=index_path,
    )

    assert findings == []


def proof_slate(
    *,
    metric_selected: str = "case-study-teamwired",
    quote_selected: str = "none",
    theme_selected: str = "case-study-teamwired",
    experience_story_selected: str = "none",
    metric_top: str = "case-study-teamwired",
    quote_top: str = "case-study-teamwired",
    theme_top: str = "case-study-teamwired",
    experience_story_top: str = "review-capterra-owner-quote-invoice",
    metric_rejected: str = "none",
    quote_rejected: str = "none",
    theme_rejected: str = "none",
    experience_story_rejected: str = (
        "review-capterra-owner-quote-invoice: omitted because this section needs "
        "case-study workflow proof, not a review POV story"
    ),
    include_experience_story: bool = True,
) -> str:
    rows = [
        "Customer Proof Slate",
        '- Selector command: python data_sources/modules/customer_proof_selector.py "teamwired invoicing" --proof-role metric --limit 10',
        f"- Role: metric | Top candidates: [{metric_top}] | Selected: [{metric_selected}] | Rejected stronger candidates: [{metric_rejected}]",
        f"- Role: quote | Top candidates: [{quote_top}] | Selected: [{quote_selected}] | Rejected stronger candidates: [{quote_rejected}]",
        f"- Role: theme | Top candidates: [{theme_top}] | Selected: [{theme_selected}] | Rejected stronger candidates: [{theme_rejected}]",
    ]
    if include_experience_story:
        rows.append(
            f"- Role: experience_story | Top candidates: [{experience_story_top}] | Selected: [{experience_story_selected}] | Rejected stronger candidates: [{experience_story_rejected}]"
        )
    return "\n".join(rows) + "\n\n"


def proof_mining(
    *,
    usable_quotes: str = "none found",
    usable_metrics: str = "none found",
    usable_pov: str = "none found",
    recommended_use: str = "theme",
    final_use: str = "paraphrased case-study theme proof only",
    excluded_proof: str = "none",
    include_checked_for: bool = True,
    include_recommended_use: bool = True,
    include_final_use: bool = True,
    include_status: bool = True,
    include_usable_quotes: bool = True,
    include_usable_metrics: bool = True,
) -> str:
    rows = [
        "Selected Customer Proof Mining",
        "- Proof: case-study-teamwired | Customer: TEAMWired | URL: https://www.simprogroup.com/case-studies/teamwired",
    ]
    if include_checked_for:
        rows.append(
            "- Checked for: exact quotes, customer metrics, POV story, workflow themes"
        )
    if include_usable_quotes:
        rows.append(f"- Usable quotes found: {usable_quotes}")
    if include_usable_metrics:
        rows.append(f"- Usable metrics found: {usable_metrics}")
    rows.append(f"- Usable POV/story found: {usable_pov}")
    if include_recommended_use:
        rows.append(f"- Recommended use: {recommended_use}")
    if include_final_use:
        rows.append(f"- Final use in copy: {final_use}")
    rows.append(f"- Excluded proof: {excluded_proof}")
    if include_status:
        rows.append("- Status: approved")
    return "\n".join(rows) + "\n\n"


def customer_link_sidecar(*, rows: str) -> str:
    return (
        proof_slate(
            metric_selected="customer-acme-services",
            quote_selected="customer-acme-services",
            theme_selected="customer-acme-services",
            metric_top="customer-acme-services",
            quote_top="customer-acme-services",
            theme_top="customer-acme-services",
        )
        + proof_mining(
            usable_quotes='"Scheduling is much easier for our field team now."',
            usable_metrics="Acme Services completed 40% more jobs.",
            usable_pov="Acme Services centralized dispatch for field teams.",
            recommended_use="customer quote, metric, and outcome",
            final_use="customer quote, metric, outcome, and POV/story",
        )
        + "Customer Proof Pack\n"
        + "- Pack status: ready.\n"
        + "- Quote Matrix candidates: Acme Services selected for scheduling proof.\n"
        + rows
        + "- Use in copy: customer quote, metric, and outcome.\n"
        + "- Claims excluded: none.\n\n"
        + "Customer Proof Selection Decision\n"
        + '- Selector command: python data_sources/modules/customer_proof_selector.py "Acme scheduling" --proof-role quote\n'
        + f"- Selected proof: customer-acme-services | Customer: Acme Services | URL: {CUSTOMER_LINK_URL} | Use: customer quote, metric, and outcome\n"
    )


class CustomerProofDiversityGuardTests(unittest.TestCase):
    def setUp(self):
        validation_patch = patch(
            "data_sources.modules.customer_proof_selector.load_validated_claim_set",
            new=load_validated_claim_set_for_unit_test,
        )
        validation_patch.start()
        self.addCleanup(validation_patch.stop)

    def test_clockshark_case_study_resource_path_requires_customer_proof_pack(self):
        findings = check_content(
            ARTICLE_WITH_CLOCKSHARK_CASE_STUDY,
            proof_content="",
        )

        self.assertTrue(
            any(f["rule_id"] == "customer_proof_pack_missing" for f in findings)
        )
        self.assertTrue(should_fail(findings, fail_on="error"))

    def test_one_recent_use_warns_and_requires_source_specific_comparison(self):
        sidecar = """Customer Proof Pack
- Pack status: ready.
- Quote Matrix candidates: Checked Quote Matrix for quote-to-cash proof.
- Case-study proof path: TEAMWired, URL: https://www.simprogroup.com/case-studies/teamwired, supported theme: invoicing workflow.
- Use in copy: paraphrased case-study proof only.
- Claims excluded: exact review quotes.

Customer Proof Selection Decision
- Selector command: python data_sources/modules/customer_proof_selector.py "teamwired invoicing" --proof-role metric
- Selected proof: case-study-teamwired | Customer: TEAMWired | URL: https://www.simprogroup.com/case-studies/teamwired | Use: invoicing workflow proof
"""
        ledger = {
            "version": 1,
            "uses": [
                {
                    "proof_id": "case-study-teamwired",
                    "customer": "TEAMWired",
                    "source_url": "https://www.simprogroup.com/case-studies/teamwired",
                    "article_slug": "prior-article",
                    "artifact_path": "published/prior-article.md",
                    "date_used": "2026-06-12",
                    "section": "body",
                    "use_type": "metric",
                    "claim_summary": "invoicing proof",
                }
            ],
        }

        with TemporaryDirectory() as temp_dir:
            ledger_path = Path(temp_dir) / "ledger.json"
            index_path = Path(temp_dir) / "index.json"
            ledger_path.write_text(json.dumps(ledger), encoding="utf-8")
            index_path.write_text(json.dumps({"version": 1, "proof": []}), encoding="utf-8")
            findings = check_content(
                ARTICLE_WITH_CASE_STUDY,
                proof_content=sidecar,
                ledger_path=ledger_path,
                proof_index_path=index_path,
            )

        severities = {finding["rule_id"]: finding["severity"] for finding in findings}
        self.assertEqual("warning", severities["customer_proof_recent_use_warning"])
        self.assertEqual("error", severities["customer_proof_reuse_requires_source_specific_reason"])
        self.assertEqual("error", severities["customer_proof_zero_use_comparison_missing"])

    def test_only_case_studies_without_non_case_study_search_attempt_fails(self):
        sidecar = fixture_text("content_evidence:test_customer_proof_diversity_guard-123-3")

        with TemporaryDirectory() as temp_dir:
            ledger_path = Path(temp_dir) / "ledger.json"
            ledger_path.write_text(
                json.dumps({"version": 1, "uses": []}), encoding="utf-8"
            )
            findings = check_content(
                ARTICLE_WITH_CASE_STUDY,
                proof_content=sidecar,
                ledger_path=ledger_path,
            )

        self.assertTrue(
            any(
                f["rule_id"] == "customer_proof_non_case_study_attempt_missing"
                for f in findings
            )
        )
        self.assertTrue(should_fail(findings, fail_on="error"))

    def test_customer_proof_without_mining_block_fails(self):
        sidecar = (
            proof_slate()
            + fixture_text("content_evidence:test_customer_proof_diversity_guard-154-14")
        )

        with TemporaryDirectory() as temp_dir:
            ledger_path = Path(temp_dir) / "ledger.json"
            ledger_path.write_text(
                json.dumps({"version": 1, "uses": []}), encoding="utf-8"
            )
            findings = check_content(
                ARTICLE_WITH_CASE_STUDY,
                proof_content=sidecar,
                ledger_path=ledger_path,
            )

        self.assertTrue(
            any(
                f["rule_id"] == "selected_customer_proof_mining_missing"
                for f in findings
            )
        )

    def test_mining_block_missing_required_fields_fails(self):
        sidecar = (
            proof_slate()
            + proof_mining(
                include_checked_for=False,
                include_recommended_use=False,
                include_final_use=False,
                include_status=False,
            )
            + fixture_text("content_evidence:test_customer_proof_diversity_guard-195-15")
        )

        with TemporaryDirectory() as temp_dir:
            ledger_path = Path(temp_dir) / "ledger.json"
            ledger_path.write_text(
                json.dumps({"version": 1, "uses": []}), encoding="utf-8"
            )
            findings = check_content(
                ARTICLE_WITH_CASE_STUDY,
                proof_content=sidecar,
                ledger_path=ledger_path,
            )

        missing = [
            f
            for f in findings
            if f["rule_id"] == "selected_customer_proof_mining_required_field_missing"
        ]
        self.assertGreaterEqual(len(missing), 4)

    def test_approved_quotes_none_requires_quote_mining_result(self):
        sidecar = (
            proof_slate()
            + proof_mining(include_usable_quotes=False)
            + fixture_text("content_evidence:test_customer_proof_diversity_guard-231-16")
        )

        with TemporaryDirectory() as temp_dir:
            ledger_path = Path(temp_dir) / "ledger.json"
            ledger_path.write_text(
                json.dumps({"version": 1, "uses": []}), encoding="utf-8"
            )
            findings = check_content(
                ARTICLE_WITH_CASE_STUDY,
                proof_content=sidecar,
                ledger_path=ledger_path,
            )

        self.assertTrue(
            any(
                f["rule_id"] == "selected_customer_proof_mining_quote_result_missing"
                for f in findings
            )
        )

    def test_usable_quote_omitted_without_rejection_reason_warns(self):
        sidecar = (
            proof_slate()
            + proof_mining(
                usable_quotes="Joel Anderson quote about quote-to-job workflow is usable if an exact quote is selected",
                excluded_proof="none",
            )
            + fixture_text("content_evidence:test_customer_proof_diversity_guard-271-17")
        )

        with TemporaryDirectory() as temp_dir:
            ledger_path = Path(temp_dir) / "ledger.json"
            ledger_path.write_text(
                json.dumps({"version": 1, "uses": []}), encoding="utf-8"
            )
            findings = check_content(
                ARTICLE_WITH_CASE_STUDY,
                proof_content=sidecar,
                ledger_path=ledger_path,
            )

        warning = next(
            finding
            for finding in findings
            if finding["rule_id"]
            == "selected_customer_proof_mining_usable_proof_omitted"
        )
        self.assertEqual(warning["severity"], "warning")
        self.assertFalse(should_fail(findings, fail_on="error"))

    def test_usable_quote_omitted_with_rejection_reason_passes(self):
        sidecar = (
            proof_slate()
            + proof_mining(
                usable_quotes="Joel Anderson quote about quote-to-job workflow is usable if an exact quote is selected",
                excluded_proof="exact Joel Anderson quote omitted because this section needs concise paraphrased workflow proof, not a quote block",
            )
            + fixture_text("content_evidence:test_customer_proof_diversity_guard-313-18")
        )
        with TemporaryDirectory() as temp_dir:
            ledger_path = Path(temp_dir) / "ledger.json"
            ledger_path.write_text(
                json.dumps({"version": 1, "uses": []}), encoding="utf-8"
            )
            findings = check_content(
                ARTICLE_WITH_CASE_STUDY,
                proof_content=sidecar,
                ledger_path=ledger_path,
            )

        self.assertEqual(findings, [])

    def test_repeated_case_study_without_reuse_reason_fails(self):
        sidecar = fixture_text("content_evidence:test_customer_proof_diversity_guard-341-4")
        ledger = {
            "version": 1,
            "uses": [
                {
                    "proof_id": "case-study-teamwired",
                    "source_type": "case_study",
                    "customer": "TEAMWired",
                    "source_url": "https://www.simprogroup.com/case-studies/teamwired",
                    "article_slug": f"article-{index}",
                    "artifact_path": f"drafts/article-{index}.md",
                    "date_used": "2026-06-12",
                    "section": "body",
                    "use_type": "metric",
                    "claim_summary": "invoicing proof",
                    "reuse_reason": "",
                }
                for index in range(3)
            ],
        }

        with TemporaryDirectory() as temp_dir:
            ledger_path = Path(temp_dir) / "ledger.json"
            ledger_path.write_text(json.dumps(ledger), encoding="utf-8")
            findings = check_content(
                ARTICLE_WITH_CASE_STUDY,
                proof_content=sidecar,
                ledger_path=ledger_path,
            )

        self.assertTrue(
            any(
                f["rule_id"] == "customer_proof_reuse_requires_source_specific_reason"
                for f in findings
            )
        )

    def test_documented_quote_matrix_and_reuse_reason_passes(self):
        sidecar = (
            proof_slate()
            + proof_mining()
            + fixture_text("content_evidence:test_customer_proof_diversity_guard-389-19")
        )
        ledger = {
            "version": 1,
            "uses": [
                {
                    "proof_id": "case-study-teamwired",
                    "source_type": "case_study",
                    "customer": "TEAMWired",
                    "source_url": "https://www.simprogroup.com/case-studies/teamwired",
                    "article_slug": f"article-{index}",
                    "artifact_path": f"drafts/article-{index}.md",
                    "date_used": "2026-06-12",
                    "section": "body",
                    "use_type": "metric",
                    "claim_summary": "invoicing proof",
                    "reuse_reason": "",
                }
                for index in range(3)
            ],
        }
        index = {"version": 1, "proof": []}

        with TemporaryDirectory() as temp_dir:
            ledger_path = Path(temp_dir) / "ledger.json"
            index_path = Path(temp_dir) / "index.json"
            ledger_path.write_text(json.dumps(ledger), encoding="utf-8")
            index_path.write_text(json.dumps(index), encoding="utf-8")
            findings = check_content(
                ARTICLE_WITH_CASE_STUDY,
                proof_content=sidecar,
                ledger_path=ledger_path,
                proof_index_path=index_path,
            )

        self.assertEqual(
            [finding["rule_id"] for finding in findings],
            ["customer_proof_recent_use_warning"],
        )

    def test_selector_generated_slate_is_accepted_by_diversity_guard(self):
        article = fixture_text("content_evidence:test_customer_proof_diversity_guard-440-5")
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            index_path = root / "index.json"
            ledger_path = root / "ledger.json"
            index_path.write_text(
                json.dumps(
                    {
                        "version": 1,
                        "proof": [
                            {
                                "proof_id": "quote-matrix-zebra-plumbing-onsite-quoting",
                                "customer": "Zebra Plumbing",
                                "source_type": "quote_matrix",
                                "workflow_fit": ["quoting", "invoicing"],
                                "themes": ["onsite quoting"],
                                "public_url": "https://www.simprogroup.com/case-studies/zebra-plumbing",
                                "approval_status": "approved",
                                "public_copy_allowed": True,
                                "approved_metrics": [
                                    {"metric": "20x quoting", "status": "approved"}
                                ],
                            },
                            {
                                "proof_id": "quote-matrix-bwe-engineering-job-to-invoice",
                                "customer": "BWE Engineering",
                                "source_type": "quote_matrix",
                                "workflow_fit": ["job cards", "invoicing"],
                                "themes": ["job-to-invoice"],
                                "public_url": "https://www.simprogroup.com/case-studies/bwe-engineering",
                                "approval_status": "approved",
                                "public_copy_allowed": True,
                                "approved_quotes": [
                                    {"quote": "Approved quote", "status": "approved"}
                                ],
                            },
                            {
                                "proof_id": "review-capterra-owner-quote-invoice",
                                "customer": "Capterra owner review",
                                "source_type": "review_site",
                                "workflow_fit": ["quoting", "invoicing"],
                                "themes": ["quote-to-invoice workflow"],
                                "public_url": "https://www.capterra.com/p/10529/Simpro-Enterprise/reviews/",
                                "approval_status": "approved",
                                "public_copy_allowed": True,
                                "review_story": {
                                    "story_allowed": True,
                                    "identity_type": "person",
                                    "identity_display": "Megan B",
                                    "public_url": "https://www.capterra.com/p/10529/Simpro-Enterprise/reviews/",
                                },
                            },
                        ],
                    }
                ),
                encoding="utf-8",
            )
            ledger_path.write_text(
                json.dumps({"version": 1, "uses": []}), encoding="utf-8"
            )
            pack_path, receipt_path = write_context_receipt_fixture(root, index_path)
            buffer = StringIO()

            with redirect_stdout(buffer):
                selector_main(
                    [
                        "job quoting software",
                        "--index",
                        str(index_path),
                        "--ledger",
                        str(ledger_path),
                        "--context-pack",
                        str(pack_path),
                        "--context-receipt",
                        str(receipt_path),
                        "--slate",
                        "--roles",
                        "metric,quote,theme,experience_story",
                        "--require-eeat-story",
                        "--selected",
                        "experience_story=none",
                        "--reject",
                        "experience_story=review-capterra-owner-quote-invoice:omitted because this fixture needs Zebra onsite quoting proof instead of a review story",
                        "--limit",
                        "3",
                    ]
                )

            sidecar = (
                buffer.getvalue()
                + proof_mining(
                    usable_metrics="20x quoting metric available for Zebra Plumbing",
                    recommended_use="theme and metric if needed",
                    final_use="paraphrased customer proof only",
                    excluded_proof="metric proof omitted because this fixture only checks slate compatibility",
                )
                + fixture_text("content_evidence:test_customer_proof_diversity_guard-539-31")
            )

            findings = check_content(
                article,
                proof_content=sidecar,
                ledger_path=ledger_path,
                proof_index_path=index_path,
            )

        self.assertEqual(
            [finding for finding in findings if finding["severity"] == "error"], []
        )

    def test_customer_proof_without_slate_fails(self):
        sidecar = fixture_text("content_evidence:test_customer_proof_diversity_guard-565-6")

        findings = check_content(ARTICLE_WITH_CASE_STUDY, proof_content=sidecar)

        self.assertTrue(
            any(f["rule_id"] == "customer_proof_slate_missing" for f in findings)
        )
        self.assertTrue(
            any(
                f["rule_id"] == "customer_proof_selector_context_unavailable"
                for f in findings
            )
        )
        self.assertTrue(should_fail(findings, fail_on="error"))

    def test_customer_proof_requires_experience_story_consideration_role(self):
        sidecar = (
            proof_slate(include_experience_story=False)
            + proof_mining()
            + fixture_text("content_evidence:test_customer_proof_diversity_guard-595-20")
        )

        with TemporaryDirectory() as temp_dir:
            ledger_path = Path(temp_dir) / "ledger.json"
            ledger_path.write_text(
                json.dumps({"version": 1, "uses": []}), encoding="utf-8"
            )
            findings = check_content(
                ARTICLE_WITH_CASE_STUDY,
                proof_content=sidecar,
                ledger_path=ledger_path,
            )

        self.assertTrue(
            any(
                f["rule_id"] == "customer_proof_slate_experience_story_missing"
                for f in findings
            )
        )

    def test_experience_story_none_selected_without_rejection_reason_fails(self):
        sidecar = (
            proof_slate(experience_story_rejected="none")
            + proof_mining()
            + fixture_text("content_evidence:test_customer_proof_diversity_guard-631-21")
        )

        with TemporaryDirectory() as temp_dir:
            ledger_path = Path(temp_dir) / "ledger.json"
            ledger_path.write_text(
                json.dumps({"version": 1, "uses": []}), encoding="utf-8"
            )
            findings = check_content(
                ARTICLE_WITH_CASE_STUDY,
                proof_content=sidecar,
                ledger_path=ledger_path,
            )

        self.assertTrue(
            any(
                f["rule_id"]
                == "customer_proof_slate_experience_story_rejection_missing"
                for f in findings
            )
        )

    def test_experience_story_none_selected_with_rejection_reason_passes(self):
        sidecar = (
            proof_slate()
            + proof_mining()
            + fixture_text("content_evidence:test_customer_proof_diversity_guard-668-22")
        )

        with TemporaryDirectory() as temp_dir:
            ledger_path = Path(temp_dir) / "ledger.json"
            ledger_path.write_text(
                json.dumps({"version": 1, "uses": []}), encoding="utf-8"
            )
            findings = check_content(
                ARTICLE_WITH_CASE_STUDY,
                proof_content=sidecar,
                ledger_path=ledger_path,
            )

        self.assertEqual(
            [finding for finding in findings if finding["severity"] == "error"], []
        )

    def test_no_customer_proof_does_not_require_experience_story_slate_role(self):
        findings = check_content(
            "# HVAC PPC\n\nTrack paid search from click to booked job."
        )

        self.assertEqual(findings, [])

    def test_neutral_customer_definition_url_does_not_count_as_customer_proof(self):
        findings = check_content(
            "# CRM\n\n[Investopedia](https://www.investopedia.com/terms/c/customer_relation_management.asp) defines CRM for customer relationship management."
        )

        self.assertEqual(findings, [])

    def test_selected_proof_missing_from_slate_fails(self):
        sidecar = (
            proof_slate(
                metric_selected="quote-matrix-bwe-engineering-job-to-invoice",
                theme_selected="quote-matrix-bwe-engineering-job-to-invoice",
            )
            + fixture_text("content_evidence:test_customer_proof_diversity_guard-710-23")
        )

        findings = check_content(ARTICLE_WITH_CASE_STUDY, proof_content=sidecar)

        self.assertTrue(
            any(
                f["rule_id"] == "customer_proof_selected_not_in_slate" for f in findings
            )
        )

    def test_non_overused_selected_proof_with_stronger_slate_candidate_warns(self):
        sidecar = (
            proof_slate(
                metric_top="quote-matrix-bwe-engineering-job-to-invoice, case-study-teamwired",
                metric_selected="case-study-teamwired",
            )
            + proof_mining()
            + fixture_text("content_evidence:test_customer_proof_diversity_guard-739-24")
        )
        with TemporaryDirectory() as temp_dir:
            ledger_path = Path(temp_dir) / "ledger.json"
            ledger_path.write_text(
                json.dumps({"version": 1, "uses": []}), encoding="utf-8"
            )
            findings = check_content(
                ARTICLE_WITH_CASE_STUDY,
                proof_content=sidecar,
                ledger_path=ledger_path,
            )

        warning = next(
            finding
            for finding in findings
            if finding["rule_id"] == "customer_proof_stronger_slate_candidate_available"
        )
        self.assertEqual(warning["severity"], "warning")
        self.assertFalse(should_fail(findings, fail_on="error"))

    def test_slate_selection_outside_top_candidates_fails(self):
        findings = _stronger_slate_candidate_findings(
            {
                "line": 1,
                "roles": {
                    "metric": {
                        "line": 2,
                        "top_candidates": ["receipt-approved-proof"],
                        "selected": ["unapproved-proof"],
                        "rejected": {},
                    }
                },
            }
        )

        finding = next(
            finding
            for finding in findings
            if finding["rule_id"]
            == "customer_proof_slate_selected_not_in_top_candidates"
        )
        self.assertEqual(finding["severity"], "error")
        self.assertEqual(finding["match"], "unapproved-proof")

    def test_stronger_slate_candidate_rejected_with_reason_passes(self):
        sidecar = (
            proof_slate(
                metric_top="quote-matrix-bwe-engineering-job-to-invoice, case-study-teamwired",
                metric_selected="case-study-teamwired",
                metric_rejected="quote-matrix-bwe-engineering-job-to-invoice: rejected because this section needs security-specific invoicing proof",
            )
            + proof_mining()
            + fixture_text("content_evidence:test_customer_proof_diversity_guard-803-25")
        )
        with TemporaryDirectory() as temp_dir:
            ledger_path = Path(temp_dir) / "ledger.json"
            ledger_path.write_text(
                json.dumps({"version": 1, "uses": []}), encoding="utf-8"
            )
            findings = check_content(
                ARTICLE_WITH_CASE_STUDY,
                proof_content=sidecar,
                ledger_path=ledger_path,
            )

        self.assertEqual(findings, [])

    def test_review_story_copy_requires_experience_story_slate_role(self):
        sidecar = (
            proof_slate(include_experience_story=False)
            + fixture_text("content_evidence:test_customer_proof_diversity_guard-832-26")
        )

        findings = check_content(
            "# Reviews\n\nA [Capterra reviewer](https://www.capterra.com/p/10529/Simpro-Enterprise/reviews/) describes quote-to-invoice workflow.",
            proof_content=sidecar,
        )

        self.assertTrue(
            any(
                f["rule_id"] == "customer_proof_slate_experience_story_missing"
                for f in findings
            )
        )

    def test_vague_global_reuse_reason_fails_for_repeated_proof(self):
        sidecar = fixture_text("content_evidence:test_customer_proof_diversity_guard-863-7")
        ledger = {
            "version": 1,
            "uses": [
                {
                    "proof_id": "case-study-teamwired",
                    "source_type": "case_study",
                    "customer": "TEAMWired",
                    "source_url": "https://www.simprogroup.com/case-studies/teamwired",
                    "article_slug": f"article-{index}",
                    "artifact_path": f"drafts/article-{index}.md",
                    "date_used": "2026-06-12",
                    "section": "body",
                    "use_type": "metric",
                    "claim_summary": "invoicing proof",
                    "reuse_reason": "",
                }
                for index in range(3)
            ],
        }

        with TemporaryDirectory() as temp_dir:
            ledger_path = Path(temp_dir) / "ledger.json"
            ledger_path.write_text(json.dumps(ledger), encoding="utf-8")
            findings = check_content(
                ARTICLE_WITH_CASE_STUDY,
                proof_content=sidecar,
                ledger_path=ledger_path,
            )

        self.assertTrue(
            any(
                f["rule_id"] == "customer_proof_reuse_requires_source_specific_reason"
                for f in findings
            )
        )

    def test_overused_proof_with_better_underused_candidate_fails_even_with_specific_reuse_reason(
        self,
    ):
        sidecar = fixture_text("content_evidence:test_customer_proof_diversity_guard-911-8")
        ledger = {
            "version": 1,
            "uses": [
                {
                    "proof_id": "case-study-teamwired",
                    "source_type": "case_study",
                    "customer": "TEAMWired",
                    "source_url": "https://www.simprogroup.com/case-studies/teamwired",
                    "article_slug": f"article-{index}",
                    "artifact_path": f"drafts/article-{index}.md",
                    "date_used": "2026-06-12",
                    "section": "body",
                    "use_type": "metric",
                    "claim_summary": "invoicing proof",
                    "reuse_reason": "",
                }
                for index in range(3)
            ],
        }
        index = {
            "version": 1,
            "proof": [
                {
                    "proof_id": "case-study-teamwired",
                    "customer": "TEAMWired",
                    "source_type": "case_study",
                    "workflow_fit": ["invoicing", "payments"],
                    "themes": ["manual invoicing"],
                    "public_url": "https://www.simprogroup.com/case-studies/teamwired",
                    "approval_status": "approved",
                    "public_copy_allowed": True,
                    "approved_metrics": [
                        {"claim": "TEAMWired manual invoicing time fell by 90%"}
                    ],
                },
                {
                    "proof_id": "quote-matrix-bwe-engineering-job-to-invoice",
                    "customer": "BWE Engineering",
                    "source_type": "quote_matrix",
                    "workflow_fit": [
                        "job cards",
                        "invoicing",
                        "cash flow",
                        "field service",
                    ],
                    "themes": ["job-to-invoice speed", "cash flow"],
                    "public_url": "https://www.simprogroup.com/case-studies/bwe-engineering",
                    "approval_status": "approved",
                    "public_copy_allowed": True,
                    "approved_metrics": [
                        {"claim": "BWE Engineering reduced job-to-invoice time by 50%"}
                    ],
                },
            ],
        }

        with TemporaryDirectory() as temp_dir:
            ledger_path = Path(temp_dir) / "ledger.json"
            index_path = Path(temp_dir) / "index.json"
            ledger_path.write_text(json.dumps(ledger), encoding="utf-8")
            index_path.write_text(json.dumps(index), encoding="utf-8")
            pack_path, receipt_path = write_context_receipt_fixture(
                Path(temp_dir), index_path
            )
            findings = check_content(
                ARTICLE_WITH_CASE_STUDY,
                proof_content=sidecar,
                ledger_path=ledger_path,
                proof_index_path=index_path,
                context_pack=pack_path,
                context_receipt=receipt_path,
            )

        self.assertTrue(
            any(
                f["rule_id"] == "customer_proof_stronger_underused_candidate_available"
                for f in findings
            )
        )

    def test_overused_proof_passes_when_stronger_underused_candidate_is_rejected_with_reason(
        self,
    ):
        sidecar = (
            proof_slate(
                metric_top="quote-matrix-bwe-engineering-job-to-invoice, case-study-teamwired",
                metric_selected="case-study-teamwired",
                metric_rejected="quote-matrix-bwe-engineering-job-to-invoice: rejected because BWE is agricultural engineering, while this section specifically needs security contractor invoicing proof",
            )
            + proof_mining()
            + fixture_text("content_evidence:test_customer_proof_diversity_guard-1014-27")
        )
        ledger = {
            "version": 1,
            "uses": [
                {
                    "proof_id": "case-study-teamwired",
                    "source_type": "case_study",
                    "customer": "TEAMWired",
                    "source_url": "https://www.simprogroup.com/case-studies/teamwired",
                    "article_slug": f"article-{index}",
                    "artifact_path": f"drafts/article-{index}.md",
                    "date_used": "2026-06-12",
                    "section": "body",
                    "use_type": "metric",
                    "claim_summary": "invoicing proof",
                    "reuse_reason": "",
                }
                for index in range(3)
            ],
        }
        index = {
            "version": 1,
            "proof": [
                {
                    "proof_id": "case-study-teamwired",
                    "customer": "TEAMWired",
                    "source_type": "case_study",
                    "workflow_fit": ["invoicing", "payments"],
                    "themes": ["manual invoicing"],
                    "public_url": "https://www.simprogroup.com/case-studies/teamwired",
                    "approval_status": "approved",
                    "public_copy_allowed": True,
                    "approved_metrics": [
                        {"claim": "TEAMWired manual invoicing time fell by 90%"}
                    ],
                },
                {
                    "proof_id": "quote-matrix-bwe-engineering-job-to-invoice",
                    "customer": "BWE Engineering",
                    "source_type": "quote_matrix",
                    "workflow_fit": [
                        "job cards",
                        "invoicing",
                        "cash flow",
                        "field service",
                    ],
                    "themes": ["job-to-invoice speed", "cash flow"],
                    "public_url": "https://www.simprogroup.com/case-studies/bwe-engineering",
                    "approval_status": "approved",
                    "public_copy_allowed": True,
                    "approved_metrics": [
                        {"claim": "BWE Engineering reduced job-to-invoice time by 50%"}
                    ],
                },
            ],
        }

        with TemporaryDirectory() as temp_dir:
            ledger_path = Path(temp_dir) / "ledger.json"
            index_path = Path(temp_dir) / "index.json"
            ledger_path.write_text(json.dumps(ledger), encoding="utf-8")
            index_path.write_text(json.dumps(index), encoding="utf-8")
            pack_path, receipt_path = write_context_receipt_fixture(
                Path(temp_dir), index_path
            )
            findings = check_content(
                ARTICLE_WITH_CASE_STUDY,
                proof_content=sidecar,
                ledger_path=ledger_path,
                proof_index_path=index_path,
                context_pack=pack_path,
                context_receipt=receipt_path,
            )

        self.assertEqual(
            [finding["rule_id"] for finding in findings],
            ["customer_proof_recent_use_warning"],
        )

    def test_reuse_threshold_counts_unique_article_slugs(self):
        sidecar = fixture_text("content_evidence:test_customer_proof_diversity_guard-1105-9")
        ledger = {
            "version": 1,
            "uses": [
                {
                    "proof_id": "case-study-teamwired",
                    "source_type": "case_study",
                    "customer": "TEAMWired",
                    "source_url": "https://www.simprogroup.com/case-studies/teamwired",
                    "article_slug": "same-article",
                    "artifact_path": f"artifact-{index}.md",
                    "date_used": "2026-06-12",
                    "section": "body",
                    "use_type": "metric",
                    "claim_summary": "invoicing proof",
                    "reuse_reason": "",
                }
                for index in range(5)
            ],
        }

        with TemporaryDirectory() as temp_dir:
            ledger_path = Path(temp_dir) / "ledger.json"
            ledger_path.write_text(json.dumps(ledger), encoding="utf-8")
            findings = check_content(
                ARTICLE_WITH_CASE_STUDY,
                proof_content=sidecar,
                ledger_path=ledger_path,
            )

        warning = next(
            finding
            for finding in findings
            if finding["rule_id"] == "customer_proof_recent_use_warning"
        )
        self.assertIn("1 recent use(s)", warning["message"])
        self.assertTrue(
            any(
                finding["rule_id"] == "customer_proof_reuse_requires_source_specific_reason"
                for finding in findings
            )
        )

    def test_missing_proof_index_fails_when_overused_selection_must_be_compared(self):
        sidecar = fixture_text("content_evidence:test_customer_proof_diversity_guard-1151-10")
        ledger = {
            "version": 1,
            "uses": [
                {
                    "proof_id": "case-study-teamwired",
                    "source_type": "case_study",
                    "customer": "TEAMWired",
                    "source_url": "https://www.simprogroup.com/case-studies/teamwired",
                    "article_slug": f"article-{index}",
                    "artifact_path": f"drafts/article-{index}.md",
                    "date_used": "2026-06-12",
                    "section": "body",
                    "use_type": "metric",
                    "claim_summary": "invoicing proof",
                    "reuse_reason": "",
                }
                for index in range(3)
            ],
        }

        with TemporaryDirectory() as temp_dir:
            ledger_path = Path(temp_dir) / "ledger.json"
            missing_index_path = Path(temp_dir) / "missing-index.json"
            ledger_path.write_text(json.dumps(ledger), encoding="utf-8")
            findings = check_content(
                ARTICLE_WITH_CASE_STUDY,
                proof_content=sidecar,
                ledger_path=ledger_path,
                proof_index_path=missing_index_path,
            )

        self.assertTrue(
            any(f["rule_id"] == "customer_proof_index_missing" for f in findings)
        )

    def test_overuse_baseline_triggers_reuse_guard_without_usage_rows(self):
        article = fixture_text("content_evidence:test_customer_proof_diversity_guard-1200-11")
        sidecar = fixture_text("content_evidence:test_customer_proof_diversity_guard-1204-12")
        ledger = {
            "version": 1,
            "overuse_baselines": [
                {
                    "proof_id": "case-study-bge-digital",
                    "customer": "BGE Digital",
                    "source_url": "https://www.simprogroup.com/case-studies/bge-digital",
                    "recent_uses_90d": 3,
                    "total_uses": 3,
                    "source_note": "repo scan before active article repair",
                    "last_reviewed": "2026-06-15",
                }
            ],
            "uses": [],
        }

        with TemporaryDirectory() as temp_dir:
            ledger_path = Path(temp_dir) / "ledger.json"
            ledger_path.write_text(json.dumps(ledger), encoding="utf-8")
            findings = check_content(
                article,
                proof_content=sidecar,
                ledger_path=ledger_path,
            )

        self.assertTrue(
            any(
                f["rule_id"] == "customer_proof_reuse_requires_source_specific_reason"
                for f in findings
            )
        )

    def test_review_site_theme_evidence_passes_without_exact_quote(self):
        sidecar = (
            proof_slate(
                metric_selected="case-study-bge-digital",
                theme_selected="case-study-bge-digital",
                metric_top="case-study-bge-digital",
                theme_top="case-study-bge-digital",
            )
            + proof_mining()
            + fixture_text("content_evidence:test_customer_proof_diversity_guard-1257-28")
        )

        with TemporaryDirectory() as temp_dir:
            ledger_path = Path(temp_dir) / "ledger.json"
            ledger_path.write_text(
                json.dumps({"version": 1, "uses": []}), encoding="utf-8"
            )
            findings = check_content(
                "# Quoting\n\nReview themes can inform a paraphrased workflow discussion.",
                proof_content=sidecar,
                ledger_path=ledger_path,
            )

        self.assertEqual(findings, [])

    def test_exact_quote_requires_approved_quote_row(self):
        sidecar = fixture_text("content_evidence:test_customer_proof_diversity_guard-1285-13")
        article = '# Review proof\n\nA G2 reviewer said, "Scheduling is much easier for our field team now."'

        with TemporaryDirectory() as temp_dir:
            ledger_path = Path(temp_dir) / "ledger.json"
            ledger_path.write_text(
                json.dumps({"version": 1, "uses": []}), encoding="utf-8"
            )
            findings = check_content(
                article, proof_content=sidecar, ledger_path=ledger_path
            )

        self.assertTrue(
            any(
                f["rule_id"] == "customer_quote_requires_approved_quote"
                for f in findings
            )
        )

    def test_exact_quote_passes_with_approved_quote_row(self):
        sidecar = (
            proof_slate(
                metric_selected="none",
                quote_selected="quote-matrix-example-customer",
                theme_selected="none",
                quote_top="quote-matrix-example-customer",
            )
            + proof_mining(
                usable_quotes='"Scheduling is much easier for our field team now." approved for exact quote use',
                recommended_use="exact quote",
                final_use="exact quote",
            )
            + fixture_text("content_evidence:test_customer_proof_diversity_guard-1322-29")
        )
        article = (
            '# Review proof\n\nExample Customer said, "Scheduling is much easier for our '
            'field team now," in its [scheduling workflow account]'
            '(https://example.com/customer-proof).'
        )

        with TemporaryDirectory() as temp_dir:
            ledger_path = Path(temp_dir) / "ledger.json"
            ledger_path.write_text(
                json.dumps({"version": 1, "uses": []}), encoding="utf-8"
            )
            findings = check_content(
                article, proof_content=sidecar, ledger_path=ledger_path
            )

        self.assertEqual(findings, [])

    def test_approved_exact_quote_without_contextual_link_fails(self):
        rows = (
            '- Approved quote: "Scheduling is much easier for our field team now." '
            f'| Customer/brand: Acme Services | URL: {CUSTOMER_LINK_URL} '
            '| Evidence: "Scheduling is much easier for our field team now." '
            '| Status: approved | Use: exact customer quote\n'
        )
        article = (
            '# Scheduling proof\n\nAcme Services said, "Scheduling is much easier '
            'for our field team now."'
        )

        findings = check_content(
            article,
            proof_content=customer_link_sidecar(rows=rows),
            ledger_path=Path("missing-ledger.json"),
        )

        self.assertTrue(
            any(
                finding["rule_id"] == "customer_proof_visible_link_missing"
                for finding in findings
            )
        )

    def test_missing_pack_cannot_suppress_customer_link_finding(self):
        proof = (
            '## Source Map\n- Approved quote: "Scheduling is much easier for our field team now." '
            f'| Customer/brand: Acme Services | URL: {CUSTOMER_LINK_URL} '
            '| Evidence: "Scheduling is much easier for our field team now." '
            '| Status: approved | Use: exact customer quote\n'
        )
        article = (
            '# Scheduling proof\n\nAcme Services said, "Scheduling is much easier '
            'for our field team now."'
        )

        rules = {
            finding["rule_id"]
            for finding in check_content(
                article,
                proof_content=proof,
                ledger_path=Path("missing-ledger.json"),
            )
        }

        self.assertIn("customer_proof_visible_link_missing", rules)

    def test_approved_nonnumeric_customer_outcome_without_contextual_link_fails(self):
        rows = (
            '- Claim: Acme Services centralized dispatch for field teams. '
            f'| Source class: customer_proof | URL: {CUSTOMER_LINK_URL} '
            '| Evidence: Acme Services centralized dispatch for field teams. '
            '| Status: approved | Use: customer outcome\n'
        )
        article = (
            "# Dispatch proof\n\nAcme Services centralized dispatch for field teams."
        )

        findings = check_content(
            article,
            proof_content=customer_link_sidecar(rows=rows),
            ledger_path=Path("missing-ledger.json"),
        )

        self.assertTrue(
            any(
                finding["rule_id"] == "customer_proof_visible_link_missing"
                for finding in findings
            )
        )

    def test_one_contextual_customer_link_supports_quote_metric_and_outcome(self):
        rows = (
            '- Approved quote: "Scheduling is much easier for our field team now." '
            f'| Customer/brand: Acme Services | URL: {CUSTOMER_LINK_URL} '
            '| Evidence: "Scheduling is much easier for our field team now." '
            '| Status: approved | Use: exact customer quote\n'
            '- Approved metric: Acme Services completed 40% more jobs. '
            f'| Customer/brand: Acme Services | URL: {CUSTOMER_LINK_URL} '
            '| Evidence: Acme Services completed 40% more jobs. '
            '| Status: approved | Use: customer metric\n'
            '- Claim: Acme Services centralized dispatch for field teams. '
            f'| Source class: customer_proof | URL: {CUSTOMER_LINK_URL} '
            '| Evidence: Acme Services centralized dispatch for field teams. '
            '| Status: approved | Use: customer outcome\n'
        )
        article = (
            "# Customer proof\n\n"
            f"[Acme Services]({CUSTOMER_LINK_URL}) centralized dispatch for field "
            "teams. Acme Services completed 40% more jobs. Acme Services said, "
            '"Scheduling is much easier for our field team now."'
        )

        findings = check_content(
            article,
            proof_content=customer_link_sidecar(rows=rows),
            ledger_path=Path("missing-ledger.json"),
        )

        self.assertEqual(findings, [])

    def test_generic_or_bare_customer_proof_anchor_fails(self):
        rows = (
            '- Claim: Acme Services centralized dispatch for field teams. '
            f'| Source class: customer_proof | URL: {CUSTOMER_LINK_URL} '
            '| Evidence: Acme Services centralized dispatch for field teams. '
            '| Status: approved | Use: customer outcome\n'
        )
        articles = (
            (
                "generic",
                "# Dispatch proof\n\nAcme Services centralized dispatch for field "
                f"teams. [Source]({CUSTOMER_LINK_URL})",
            ),
            (
                "bare",
                "# Dispatch proof\n\nAcme Services centralized dispatch for field "
                f"teams. {CUSTOMER_LINK_URL}",
            ),
        )

        for label, article in articles:
            with self.subTest(label=label):
                findings = check_content(
                    article,
                    proof_content=customer_link_sidecar(rows=rows),
                    ledger_path=Path("missing-ledger.json"),
                )

                self.assertTrue(
                    any(
                        finding["rule_id"]
                        == "customer_proof_anchor_not_descriptive"
                        for finding in findings
                    )
                )

    def test_customer_link_canonicalizes_tracking_fragment_and_trailing_slash(self):
        rows = (
            '- Claim: Acme Services centralized dispatch for field teams. '
            f'| Source class: customer_proof | URL: {CUSTOMER_LINK_URL}/ '
            '| Evidence: Acme Services centralized dispatch for field teams. '
            '| Status: approved | Use: customer outcome\n'
        )
        article = (
            "# Dispatch proof\n\n"
            f"[Acme Services customer story]({CUSTOMER_LINK_URL}?utm_source=blog#results) "
            "shows that Acme Services centralized dispatch for field teams."
        )

        findings = check_content(
            article,
            proof_content=customer_link_sidecar(rows=rows),
            ledger_path=Path("missing-ledger.json"),
        )

        self.assertEqual(findings, [])

    def test_check_file_accepts_sidecar_and_ledger_paths(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            article = root / "drafts" / "job-quoting.md"
            sidecar = root / "research" / "validation-job-quoting.md"
            ledger = root / "context" / "customer-proof-usage-ledger.json"
            article.parent.mkdir(parents=True)
            sidecar.parent.mkdir(parents=True)
            ledger.parent.mkdir(parents=True)
            article.write_text(ARTICLE_WITH_CASE_STUDY, encoding="utf-8")
            sidecar.write_text(
                proof_slate()
                + proof_mining()
                + fixture_text("content_evidence:test_customer_proof_diversity_guard-1360-32"),
                encoding="utf-8",
            )
            ledger.write_text(json.dumps({"version": 1, "uses": []}), encoding="utf-8")

            findings = check_file(
                article,
                proof_sidecar=str(sidecar),
                ledger_path=ledger,
            )

        self.assertTrue(
            any(
                finding["rule_id"] == "customer_proof_selector_evidence_unverified"
                for finding in findings
            )
        )

    def test_verified_selector_evidence_must_match_every_slate_role(self):
        sidecar = (
            proof_slate()
            + proof_mining()
            + fixture_text("content_evidence:test_customer_proof_diversity_guard-1393-30")
        )
        verified_roles = {
            "metric": {
                "candidate_ids": ["different-proof"],
                "claim_ids": ["claim-different"],
                "selected_id": "different-proof",
                "rejected_overrides": {},
            },
            "quote": {
                "candidate_ids": ["case-study-teamwired"],
                "claim_ids": ["claim-quote"],
                "selected_id": "none",
                "rejected_overrides": {},
            },
            "theme": {
                "candidate_ids": ["case-study-teamwired"],
                "claim_ids": ["claim-theme"],
                "selected_id": "case-study-teamwired",
                "rejected_overrides": {},
            },
            "experience_story": {
                "candidate_ids": ["review-capterra-owner-quote-invoice"],
                "claim_ids": ["claim-story"],
                "selected_id": "none",
                "rejected_overrides": {
                    "review-capterra-owner-quote-invoice": (
                        "omitted because this section needs case-study workflow proof, "
                        "not a review POV story"
                    )
                },
            },
        }
        with patch(
            "data_sources.modules.customer_proof_diversity_guard.verify_selector_evidence_roles",
            return_value=verified_roles,
        ):
            findings = check_content(
                ARTICLE_WITH_CASE_STUDY,
                proof_content=sidecar,
                proof_sidecar_path="validation.md",
            )

        self.assertTrue(
            any(
                finding["rule_id"] == "customer_proof_selector_evidence_slate_mismatch"
                for finding in findings
            )
        )


if __name__ == "__main__":
    unittest.main()
