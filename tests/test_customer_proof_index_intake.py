import csv
import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from data_sources.modules.customer_proof_index_intake import (
    merge_intake_file,
    validate_intake_file,
)


FIELDNAMES = [
    "proof_id",
    "customer",
    "source_type",
    "industry",
    "region",
    "workflow_fit",
    "themes",
    "public_url",
    "internal_source_ref",
    "approval_status",
    "public_copy_allowed",
    "evidence",
    "last_verified",
    "restrictions",
    "approved_quote",
    "approved_quote_evidence",
    "approved_quote_url",
    "approved_quote_status",
    "approved_metric_claim",
    "approved_metric_evidence",
    "approved_metric_url",
    "approved_metric_status",
    "review_story_allowed",
    "review_identity_type",
    "review_identity_display",
    "review_business_name",
    "review_person_name",
    "review_role_title",
    "review_platform",
    "review_source_row_ref",
    "review_public_url",
    "review_workflow_story",
    "review_copy_use",
    "review_verification_status",
    "review_objective_fit",
    "company_size",
]


def write_index(path: Path, proof_rows=None) -> None:
    path.write_text(
        json.dumps(
            {
                "version": 1,
                "updated_at": "2026-06-12",
                "source_boundary": "Existing test index.",
                "proof": proof_rows or [],
            }
        ),
        encoding="utf-8",
    )


def write_csv(path: Path, rows) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDNAMES)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in FIELDNAMES})


def base_row(**overrides):
    row = {
        "proof_id": "customer-story-queenstown-plumbing",
        "customer": "Queenstown Plumbing",
        "source_type": "customer_story",
        "industry": "plumbing; field service",
        "region": "NZ",
        "workflow_fit": "job management; quoting; invoicing",
        "themes": "small trade workflow; official customer story source route",
        "public_url": "https://www.simprogroup.com/case-studies/queenstown-plumbing",
        "internal_source_ref": "Customer Story folder row: Queenstown Plumbing Customer Story",
        "approval_status": "approved",
        "public_copy_allowed": "false",
        "evidence": "Drive search returned SP | Customer Story - Queenstown Plumbing and the Queenstown Plumbing Customer Story folder.",
        "last_verified": "2026-06-15",
        "restrictions": "Internal story route only; do not use exact quotes or public copy until public URL or public-copy permission is recorded.",
    }
    row.update(overrides)
    return row


class CustomerProofIndexIntakeTests(unittest.TestCase):
    def test_valid_csv_with_customer_story_reference_quote_matrix_and_review_rows_validates(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            index_path = root / "customer-proof-index.json"
            csv_path = root / "intake.csv"
            write_index(index_path)
            write_csv(
                csv_path,
                [
                    base_row(),
                    base_row(
                        proof_id="reference-alarmquest-job-workflow",
                        customer="AlarmQuest",
                        source_type="reference",
                        workflow_fit="job management; service workflow",
                        themes="official reference route; security workflow",
                        internal_source_ref="Simpro References program source row for AlarmQuest",
                        evidence="Official reference route for job workflow validation.",
                        approval_status="approved",
                        public_copy_allowed="false",
                    ),
                    base_row(
                        proof_id="quote-matrix-zebra-plumbing-onsite-quoting",
                        customer="Zebra Plumbing",
                        source_type="quote_matrix",
                        public_url="https://www.simprogroup.com/case-studies/zebra-plumbing",
                        internal_source_ref="Quote Matrix URLs tab row 27",
                        approval_status="approved",
                        public_copy_allowed="true",
                        approved_metric_claim="Zebra Plumbing accelerated quoting speed by 20x",
                        approved_metric_evidence="accelerated quoting speed by 20x",
                        approved_metric_url="https://www.simprogroup.com/case-studies/zebra-plumbing",
                        approved_metric_status="approved",
                    ),
                    base_row(
                        proof_id="review-capterra-quote-invoice-theme",
                        customer="Capterra review theme",
                        source_type="review_site",
                        public_url="https://www.capterra.com/p/10529/Simpro-Enterprise/reviews/",
                        internal_source_ref="Capterra tab row 25",
                        approval_status="approved",
                        public_copy_allowed="true",
                        review_platform="Capterra",
                        review_source_row_ref="Capterra tab row 25",
                        review_public_url="https://www.capterra.com/p/10529/Simpro-Enterprise/reviews/",
                        review_workflow_story="Managing Director describes enquiries, quotes, jobs, costs, and project tracking.",
                        review_copy_use="paraphrased review-theme use only",
                        review_verification_status="brand-captured public review source",
                    ),
                ],
            )

            findings = validate_intake_file(csv_path, index_path=index_path)

            self.assertEqual([], findings)

    def test_duplicate_proof_id_in_csv_fails(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            index_path = root / "customer-proof-index.json"
            csv_path = root / "intake.csv"
            write_index(index_path)
            write_csv(csv_path, [base_row(), base_row()])

            findings = validate_intake_file(csv_path, index_path=index_path)

            self.assertTrue(any(f["rule_id"] == "duplicate_proof_id" for f in findings))

    def test_public_review_story_without_identity_or_url_fails(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            index_path = root / "customer-proof-index.json"
            csv_path = root / "intake.csv"
            write_index(index_path)
            write_csv(
                csv_path,
                [
                    base_row(
                        proof_id="review-capterra-missing-identity",
                        customer="Capterra story candidate",
                        source_type="review_site",
                        public_url="https://www.capterra.com/p/10529/Simpro-Enterprise/reviews/",
                        approval_status="ready",
                        public_copy_allowed="true",
                        review_story_allowed="true",
                        review_platform="Capterra",
                        review_source_row_ref="Capterra tab row 25",
                        review_workflow_story="Review story candidate.",
                    )
                ],
            )

            findings = validate_intake_file(csv_path, index_path=index_path)

            self.assertTrue(any(f["rule_id"] == "review_story_identity_missing" for f in findings))
            self.assertTrue(any(f["rule_id"] == "review_story_public_url_missing" for f in findings))

    def test_google_review_without_public_url_fails_active_index_validation(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            index_path = root / "customer-proof-index.json"
            csv_path = root / "intake.csv"
            write_index(index_path)
            write_csv(
                csv_path,
                [
                    base_row(
                        proof_id="review-google-kingson-electrical-candidate",
                        customer="Kingson Electrical Ltd",
                        source_type="review_site",
                        public_url="",
                        approval_status="approved",
                        public_copy_allowed="false",
                        review_platform="Google Reviews",
                        review_source_row_ref="Google Review Quotes tab row 2",
                        review_workflow_story="Internal Google review route; public URL not captured.",
                        restrictions="Official brand-captured review route; internal only until a usable public Google review URL is captured.",
                    )
                ],
            )

            findings = validate_intake_file(csv_path, index_path=index_path)
            self.assertTrue(any(f["rule_id"] == "public_web_url_missing" for f in findings))

            write_csv(
                csv_path,
                [
                    base_row(
                        proof_id="review-google-kingson-electrical-public",
                        customer="Kingson Electrical Ltd",
                        source_type="review_site",
                        public_url="",
                        approval_status="approved",
                        public_copy_allowed="true",
                        review_platform="Google Reviews",
                        review_source_row_ref="Google Review Quotes tab row 2",
                    )
                ],
            )

            findings = validate_intake_file(csv_path, index_path=index_path)
            self.assertTrue(any(f["rule_id"] == "google_review_public_url_missing" for f in findings))
            self.assertTrue(any(f["rule_id"] == "public_web_url_missing" for f in findings))

    def test_google_docs_url_fails_active_index_validation(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            index_path = root / "customer-proof-index.json"
            csv_path = root / "intake.csv"
            write_index(index_path)
            write_csv(
                csv_path,
                [
                    base_row(
                        proof_id="references-source-register",
                        customer="Simpro References source register",
                        source_type="reference",
                        public_url="https://docs.google.com/presentation/d/example/edit",
                        public_copy_allowed="false",
                    )
                ],
            )

            findings = validate_intake_file(csv_path, index_path=index_path)

            self.assertTrue(any(f["rule_id"] == "public_web_url_missing" for f in findings))

    def test_approved_quote_missing_evidence_or_status_fails(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            index_path = root / "customer-proof-index.json"
            csv_path = root / "intake.csv"
            write_index(index_path)
            write_csv(
                csv_path,
                [
                    base_row(
                        proof_id="quote-matrix-approved-quote-missing-evidence",
                        source_type="quote_matrix",
                        public_url="https://www.simprogroup.com/case-studies/example",
                        public_copy_allowed="true",
                        approval_status="approved",
                        approved_quote="Approved quote text",
                        approved_quote_status="approved",
                    )
                ],
            )

            findings = validate_intake_file(csv_path, index_path=index_path)

            self.assertTrue(any(f["rule_id"] == "approved_quote_evidence_missing" for f in findings))

    def test_approved_metric_missing_public_url_or_evidence_fails(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            index_path = root / "customer-proof-index.json"
            csv_path = root / "intake.csv"
            write_index(index_path)
            write_csv(
                csv_path,
                [
                    base_row(
                        proof_id="quote-matrix-approved-metric-missing-url",
                        source_type="quote_matrix",
                        public_url="",
                        public_copy_allowed="true",
                        approval_status="approved",
                        approved_metric_claim="Customer reduced admin time by 50%",
                        approved_metric_evidence="reduced admin time by 50%",
                        approved_metric_status="approved",
                    )
                ],
            )

            findings = validate_intake_file(csv_path, index_path=index_path)

            self.assertTrue(any(f["rule_id"] == "approved_metric_url_missing" for f in findings))

    def test_merge_updates_existing_row_and_appends_new_rows_deterministically(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            index_path = root / "customer-proof-index.json"
            csv_path = root / "intake.csv"
            out_path = root / "customer-proof-index.json"
            write_index(
                index_path,
                [
                    {
                        "proof_id": "customer-story-queenstown-plumbing",
                        "customer": "Old Queenstown Plumbing",
                        "source_type": "customer_story",
                        "public_url": "https://www.simprogroup.com/case-studies/queenstown-plumbing",
                        "workflow_fit": ["old"],
                        "themes": ["old"],
                        "approval_status": "candidate",
                        "public_copy_allowed": False,
                    }
                ],
            )
            write_csv(
                csv_path,
                [
                    base_row(customer="Queenstown Plumbing Updated"),
                    base_row(
                        proof_id="reference-alarmquest-job-workflow",
                        customer="AlarmQuest",
                        source_type="reference",
                        internal_source_ref="Simpro References program source row for AlarmQuest",
                        workflow_fit="job management; service workflow",
                        themes="official reference route; security workflow",
                        evidence="Official reference route for job workflow validation.",
                        approval_status="approved",
                        public_copy_allowed="false",
                    ),
                ],
            )

            result = merge_intake_file(csv_path, index_path=index_path, out_path=out_path)
            merged = json.loads(out_path.read_text(encoding="utf-8"))
            proof_ids = [row["proof_id"] for row in merged["proof"]]

            self.assertEqual(0, result["errors"])
            self.assertEqual(
                ["customer-story-queenstown-plumbing", "reference-alarmquest-job-workflow"],
                proof_ids,
            )
            self.assertEqual("Queenstown Plumbing Updated", merged["proof"][0]["customer"])

    def test_merge_preserves_review_story_objective_fit_when_supplied(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            index_path = root / "customer-proof-index.json"
            csv_path = root / "intake.csv"
            out_path = root / "customer-proof-index.json"
            write_index(index_path)
            write_csv(
                csv_path,
                [
                    base_row(
                        proof_id="review-capterra-qbo-service-jobs-quotes-invoices",
                        customer="Capterra review theme",
                        source_type="review_site",
                        public_url="https://www.capterra.com/p/10529/Simpro-Enterprise/reviews/",
                        internal_source_ref="Capterra tab row 50",
                        approval_status="approved",
                        public_copy_allowed="true",
                        review_story_allowed="true",
                        review_identity_type="person",
                        review_identity_display="Megan B",
                        review_person_name="Megan B",
                        review_role_title="Owner",
                        review_platform="Capterra",
                        review_source_row_ref="Capterra tab row 50",
                        review_public_url="https://www.capterra.com/p/10529/Simpro-Enterprise/reviews/",
                        review_workflow_story="Capterra row describes service jobs, recurring jobs, invoices, quotes, and QuickBooks Online integration.",
                        review_copy_use="paraphrased E-E-A-T story with same-paragraph source link",
                        review_verification_status="brand-captured public review source",
                        review_objective_fit="service jobs; recurring jobs; invoicing; quotes; QBO",
                        company_size="2-10 employees",
                    )
                ],
            )

            result = merge_intake_file(csv_path, index_path=index_path, out_path=out_path)
            merged = json.loads(out_path.read_text(encoding="utf-8"))

            self.assertTrue(result["passed"])
            self.assertEqual(
                ["service jobs", "recurring jobs", "invoicing", "quotes", "QBO"],
                merged["proof"][0]["review_story"]["objective_fit"],
            )
            self.assertEqual("2-10 employees", merged["proof"][0]["company_size"])

    def test_merge_preserves_existing_metadata_not_represented_in_csv(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            index_path = root / "customer-proof-index.json"
            csv_path = root / "intake.csv"
            out_path = root / "customer-proof-index.json"
            write_index(
                index_path,
                [
                    {
                        "proof_id": "review-capterra-commercial-hvac-cloud-quotes",
                        "customer": "Capterra commercial HVAC president review",
                        "source_type": "review_site",
                        "company_size": "11-50 employees",
                        "workflow_fit": ["quoting"],
                        "themes": ["commercial HVAC quoting"],
                        "public_url": "https://www.capterra.com/p/10529/Simpro-Enterprise/reviews/",
                        "approval_status": "ready",
                        "public_copy_allowed": True,
                        "evidence": "Existing evidence.",
                        "restrictions": [
                            "Use as paraphrased review-story evidence only; exact review wording requires approval."
                        ],
                        "review_story": {
                            "story_allowed": True,
                            "identity_type": "person",
                            "identity_display": "Gerald S",
                            "person_name": "Gerald S",
                            "role_title": "President",
                            "platform": "Capterra",
                            "source_row_ref": "Capterra tab row 19",
                            "public_url": "https://www.capterra.com/p/10529/Simpro-Enterprise/reviews/",
                            "workflow_story": "Existing workflow story.",
                            "objective_fit": ["quoting", "commercial HVAC"],
                            "copy_use": "paraphrased E-E-A-T story with same-paragraph source link",
                            "verification_status": "brand-captured public review source",
                        },
                    }
                ],
            )
            write_csv(
                csv_path,
                [
                    base_row(
                        proof_id="review-capterra-commercial-hvac-cloud-quotes",
                        customer="Capterra commercial HVAC president review",
                        source_type="review_site",
                        public_url="https://www.capterra.com/p/10529/Simpro-Enterprise/reviews/",
                        internal_source_ref="Capterra tab row 19",
                        approval_status="approved",
                        public_copy_allowed="true",
                        evidence="Existing evidence.",
                        restrictions="",
                        review_story_allowed="true",
                        review_identity_type="person",
                        review_identity_display="Gerald S",
                        review_person_name="Gerald S",
                        review_role_title="President",
                        review_platform="Capterra",
                        review_source_row_ref="Capterra tab row 19",
                        review_public_url="https://www.capterra.com/p/10529/Simpro-Enterprise/reviews/",
                        review_workflow_story="Existing workflow story.",
                        review_copy_use="paraphrased E-E-A-T story with same-paragraph source link",
                        review_verification_status="brand-captured public review source",
                    )
                ],
            )

            result = merge_intake_file(csv_path, index_path=index_path, out_path=out_path)
            merged = json.loads(out_path.read_text(encoding="utf-8"))

            self.assertTrue(result["passed"])
            self.assertEqual("approved", merged["proof"][0]["approval_status"])
            self.assertEqual("11-50 employees", merged["proof"][0]["company_size"])
            self.assertEqual(
                ["quoting", "commercial HVAC"],
                merged["proof"][0]["review_story"]["objective_fit"],
            )
            self.assertEqual(
                ["Use as paraphrased review-story evidence only; exact review wording requires approval."],
                merged["proof"][0]["restrictions"],
            )

    def test_validate_accepts_utf8_bom_index_files(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            index_path = root / "customer-proof-index.json"
            csv_path = root / "intake.csv"
            index_path.write_text(
                "\ufeff"
                + json.dumps(
                    {
                        "version": 1,
                        "proof": [],
                    }
                ),
                encoding="utf-8",
            )
            write_csv(csv_path, [base_row()])

            findings = validate_intake_file(csv_path, index_path=index_path)

            self.assertEqual([], findings)


if __name__ == "__main__":
    unittest.main()
