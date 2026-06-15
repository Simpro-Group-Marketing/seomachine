import json
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory

from data_sources.modules.customer_proof_selector import _main, select_customer_proofs


def write_selector_fixture(root: Path) -> tuple[Path, Path]:
    index_path = root / "customer-proof-index.json"
    ledger_path = root / "customer-proof-usage-ledger.json"
    index_path.write_text(
        json.dumps(
            {
                "version": 1,
                "proof": [
                    {
                        "proof_id": "quote-matrix-zebra-plumbing-onsite-quoting",
                        "customer": "Zebra Plumbing",
                        "source_type": "quote_matrix",
                        "industry": ["plumbing", "small trade"],
                        "workflow_fit": ["quoting", "invoicing", "payments"],
                        "themes": ["onsite quotes", "invoice speed"],
                        "public_url": "https://www.simprogroup.com/case-studies/zebra-plumbing",
                        "approval_status": "approved",
                        "public_copy_allowed": True,
                        "approved_metrics": [
                            {
                                "metric": "20x quoting workflow",
                                "status": "approved",
                            }
                        ],
                    },
                    {
                        "proof_id": "quote-matrix-bwe-engineering-job-to-invoice",
                        "customer": "BWE Engineering",
                        "source_type": "quote_matrix",
                        "industry": ["engineering", "field service"],
                        "workflow_fit": ["job cards", "invoicing"],
                        "themes": ["job-to-invoice workflow"],
                        "public_url": "https://www.simprogroup.com/case-studies/bwe-engineering",
                        "approval_status": "approved",
                        "public_copy_allowed": True,
                        "approved_quotes": [
                            {
                                "quote": "Approved public quote text",
                                "status": "approved",
                            }
                        ],
                    },
                    {
                        "proof_id": "review-capterra-qbo-service-jobs-quotes-invoices",
                        "customer": "Capterra owner review with QBO integration",
                        "source_type": "review_site",
                        "workflow_fit": ["service jobs", "quoting", "invoicing", "QBO"],
                        "themes": ["quotes", "invoices", "QuickBooks Online integration"],
                        "public_url": "https://www.capterra.com/p/10529/Simpro-Enterprise/reviews/",
                        "approval_status": "ready",
                        "public_copy_allowed": True,
                        "review_story": {
                            "story_allowed": True,
                            "identity_type": "person",
                            "identity_display": "Megan B",
                            "person_name": "Megan B",
                            "platform": "Capterra",
                            "source_row_ref": "Capterra tab row 50",
                            "public_url": "https://www.capterra.com/p/10529/Simpro-Enterprise/reviews/",
                            "workflow_story": "Owner describes service jobs, quotes, invoices, and QBO integration.",
                            "verification_status": "brand-captured public review source",
                        },
                    },
                ],
            }
        ),
        encoding="utf-8",
    )
    ledger_path.write_text(json.dumps({"version": 1, "uses": []}), encoding="utf-8")
    return index_path, ledger_path


class CustomerProofSelectorTests(unittest.TestCase):
    def test_underused_matching_reference_beats_overused_case_study(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            index_path = root / "customer-proof-index.json"
            ledger_path = root / "customer-proof-usage-ledger.json"

            index_path.write_text(
                json.dumps(
                    {
                        "version": 1,
                        "proof": [
                            {
                                "proof_id": "case-study-teamwired",
                                "customer": "TEAMWired",
                                "source_type": "case_study",
                                "industry": ["security", "low voltage"],
                                "workflow_fit": ["invoicing", "payments"],
                                "themes": ["manual invoicing", "cash collection"],
                                "public_url": "https://www.simprogroup.com/case-studies/teamwired",
                                "approval_status": "approved",
                                "public_copy_allowed": True,
                                "evidence": "time office staff spent manually invoicing customers plummeted by 90%",
                            },
                            {
                                "proof_id": "reference-alarmquest-quote-invoice",
                                "customer": "AlarmQuest",
                                "source_type": "reference",
                                "industry": ["security", "alarms"],
                                "workflow_fit": ["quoting", "invoicing", "field service"],
                                "themes": ["quote-to-cash", "small trade business", "invoice generation"],
                                "internal_source_ref": "References sheet 1tWlR0WNDRRnvA5b-2fdBdjC7rwaQQs1CYCc48pD62HE",
                                "approval_status": "approved",
                                "public_copy_allowed": True,
                                "evidence": "Reference candidate for quote-to-cash workflow validation.",
                            },
                        ],
                    }
                ),
                encoding="utf-8",
            )
            ledger_path.write_text(
                json.dumps(
                    {
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
                                "claim_summary": "manual invoicing proof",
                                "reuse_reason": "",
                            }
                            for index in range(4)
                        ],
                    }
                ),
                encoding="utf-8",
            )

            results = select_customer_proofs(
                "best job quoting and invoicing software for small trade business",
                index_path=index_path,
                ledger_path=ledger_path,
                limit=2,
            )

        self.assertEqual(results[0]["proof_id"], "reference-alarmquest-quote-invoice")
        self.assertTrue(results[1]["overused"])
        self.assertLess(results[1]["score"], results[0]["score"])

    def test_selector_marks_recent_reuse_counts(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            index_path = root / "customer-proof-index.json"
            ledger_path = root / "customer-proof-usage-ledger.json"
            index_path.write_text(
                json.dumps(
                    {
                        "version": 1,
                        "proof": [
                            {
                                "proof_id": "case-study-bge-digital",
                                "customer": "BGE Digital",
                                "source_type": "case_study",
                                "workflow_fit": ["quoting", "estimating"],
                                "themes": ["quote speed"],
                                "public_url": "https://www.simprogroup.com/case-studies/bge-digital",
                                "approval_status": "approved",
                                "public_copy_allowed": True,
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            ledger_path.write_text(
                json.dumps(
                    {
                        "version": 1,
                        "uses": [
                            {
                                "proof_id": "case-study-bge-digital",
                                "source_type": "case_study",
                                "customer": "BGE Digital",
                                "source_url": "https://www.simprogroup.com/case-studies/bge-digital",
                                "article_slug": "best-job-quoting",
                                "artifact_path": "drafts/best-job-quoting.md",
                                "date_used": "2026-06-12",
                                "section": "body",
                                "use_type": "metric",
                                "claim_summary": "quote speed",
                                "reuse_reason": "",
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )

            result = select_customer_proofs(
                "quoting software",
                index_path=index_path,
                ledger_path=ledger_path,
                limit=1,
            )[0]

        self.assertEqual(result["total_uses"], 1)
        self.assertEqual(result["recent_uses_90d"], 1)
        self.assertFalse(result["overused"])

    def test_selector_uses_overuse_baseline_when_ledger_rows_are_removed(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            index_path = root / "customer-proof-index.json"
            ledger_path = root / "customer-proof-usage-ledger.json"
            index_path.write_text(
                json.dumps(
                    {
                        "version": 1,
                        "proof": [
                            {
                                "proof_id": "case-study-bge-digital",
                                "customer": "BGE Digital",
                                "source_type": "case_study",
                                "workflow_fit": ["quoting", "estimating"],
                                "themes": ["quote speed"],
                                "public_url": "https://www.simprogroup.com/case-studies/bge-digital",
                                "approval_status": "approved",
                                "public_copy_allowed": True,
                            },
                            {
                                "proof_id": "quote-matrix-zebra-plumbing-onsite-quoting",
                                "customer": "Zebra Plumbing",
                                "source_type": "quote_matrix",
                                "workflow_fit": ["quoting", "invoicing", "payments"],
                                "themes": ["onsite quotes", "same-day payment"],
                                "public_url": "https://www.simprogroup.com/case-studies/zebra-plumbing",
                                "approval_status": "approved",
                                "public_copy_allowed": True,
                            },
                        ],
                    }
                ),
                encoding="utf-8",
            )
            ledger_path.write_text(
                json.dumps(
                    {
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
                ),
                encoding="utf-8",
            )

            results = select_customer_proofs(
                "quoting software",
                index_path=index_path,
                ledger_path=ledger_path,
                limit=2,
            )

        bge = next(result for result in results if result["proof_id"] == "case-study-bge-digital")
        self.assertEqual(bge["recent_uses_90d"], 3)
        self.assertEqual(bge["total_uses"], 3)
        self.assertEqual(bge["baseline_recent_uses_90d"], 3)
        self.assertTrue(bge["overused"])

    def test_review_story_intent_prioritizes_review_site_over_quote_matrix(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            index_path = root / "customer-proof-index.json"
            ledger_path = root / "customer-proof-usage-ledger.json"
            index_path.write_text(
                json.dumps(
                    {
                        "version": 1,
                        "proof": [
                            {
                                "proof_id": "quote-matrix-small-trade-quote-invoice",
                                "customer": "Small Trade Case",
                                "source_type": "quote_matrix",
                                "industry": ["electrical", "small business"],
                                "workflow_fit": ["quoting", "invoicing", "small trade business"],
                                "themes": ["quote-to-invoice workflow", "customer review story"],
                                "approval_status": "approved",
                                "public_copy_allowed": True,
                                "evidence": "Approved Quote Matrix customer review story proof for quote-to-invoice workflows.",
                            },
                            {
                                "proof_id": "review-g2-small-trade-quote-invoice",
                                "customer": "G2 small trade review",
                                "source_type": "review_site",
                                "industry": ["electrical", "small business"],
                                "workflow_fit": ["quoting", "invoicing", "small trade business"],
                                "themes": ["quote-to-invoice workflow", "customer review story"],
                                "approval_status": "approved",
                                "public_copy_allowed": True,
                                "evidence": "Referenceable G2 review story for quote-to-invoice workflows.",
                            },
                        ],
                    }
                ),
                encoding="utf-8",
            )
            ledger_path.write_text(json.dumps({"version": 1, "uses": []}), encoding="utf-8")

            results = select_customer_proofs(
                "best job quoting and invoicing software customer review story",
                index_path=index_path,
                ledger_path=ledger_path,
                limit=2,
            )

        self.assertEqual(results[0]["proof_id"], "review-g2-small-trade-quote-invoice")
        self.assertGreater(results[0]["score"], results[1]["score"])

    def test_require_eeat_story_excludes_anonymous_review_rows(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            index_path = root / "customer-proof-index.json"
            ledger_path = root / "customer-proof-usage-ledger.json"
            index_path.write_text(
                json.dumps(
                    {
                        "version": 1,
                        "proof": [
                            {
                                "proof_id": "review-g2-role-only-quote-invoice",
                                "customer": "G2 electrical administrator review",
                                "source_type": "review_site",
                                "workflow_fit": ["quoting", "invoicing", "small trade business"],
                                "themes": ["quote-to-invoice workflow"],
                                "public_url": "https://www.g2.com/products/simpro/reviews/example",
                                "approval_status": "approved",
                                "public_copy_allowed": True,
                                "review_story": {
                                    "story_allowed": False,
                                    "identity_type": "none",
                                    "identity_display": "",
                                    "business_name": "",
                                    "person_name": "",
                                    "role_title": "Administrator",
                                    "platform": "G2",
                                    "source_row_ref": "G2 row 1",
                                    "public_url": "https://www.g2.com/products/simpro/reviews/example",
                                    "workflow_story": "Role-only review discusses quote-to-invoice workflow.",
                                    "objective_fit": ["quote-to-invoice"],
                                    "copy_use": "research only",
                                    "verification_status": "anonymous",
                                },
                            },
                            {
                                "proof_id": "review-capterra-megan-qbo-quotes",
                                "customer": "Capterra owner review with QBO integration",
                                "source_type": "review_site",
                                "workflow_fit": ["quoting", "invoicing", "QBO", "small trade business"],
                                "themes": ["service jobs", "quotes", "invoices"],
                                "public_url": "https://www.capterra.com/p/10529/Simpro-Enterprise/reviews/",
                                "approval_status": "ready",
                                "public_copy_allowed": True,
                                "review_story": {
                                    "story_allowed": True,
                                    "identity_type": "person",
                                    "identity_display": "Megan B",
                                    "business_name": "",
                                    "person_name": "Megan B",
                                    "role_title": "Owner",
                                    "platform": "Capterra",
                                    "source_row_ref": "Capterra row 50",
                                    "public_url": "https://www.capterra.com/p/10529/Simpro-Enterprise/reviews/",
                                    "workflow_story": "Owner describes service jobs, recurring jobs, quotes, invoices, and QBO integration.",
                                    "objective_fit": ["quote-to-cash", "small trade business"],
                                    "copy_use": "paraphrased E-E-A-T story with same-paragraph source link",
                                    "verification_status": "brand-captured public review source",
                                },
                            },
                        ],
                    }
                ),
                encoding="utf-8",
            )
            ledger_path.write_text(json.dumps({"version": 1, "uses": []}), encoding="utf-8")

            results = select_customer_proofs(
                "customer review story for quote and invoice workflow",
                index_path=index_path,
                ledger_path=ledger_path,
                limit=5,
                require_eeat_story=True,
            )

        self.assertEqual([result["proof_id"] for result in results], ["review-capterra-megan-qbo-quotes"])

    def test_require_eeat_story_excludes_review_rows_without_public_url(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            index_path = root / "customer-proof-index.json"
            ledger_path = root / "customer-proof-usage-ledger.json"
            index_path.write_text(
                json.dumps(
                    {
                        "version": 1,
                        "proof": [
                            {
                                "proof_id": "review-google-business-no-url",
                                "customer": "Kingson Electrical Google review",
                                "source_type": "review_site",
                                "workflow_fit": ["quoting", "invoicing"],
                                "themes": ["quote-to-invoice workflow"],
                                "public_url": "",
                                "approval_status": "candidate",
                                "public_copy_allowed": False,
                                "review_story": {
                                    "story_allowed": False,
                                    "identity_type": "business",
                                    "identity_display": "Kingson Electrical",
                                    "business_name": "Kingson Electrical",
                                    "person_name": "",
                                    "role_title": "",
                                    "platform": "Google Review",
                                    "source_row_ref": "Google Review Quotes row 2",
                                    "public_url": "",
                                    "workflow_story": "Business review describes quote-to-invoice visibility.",
                                    "objective_fit": ["quote-to-invoice"],
                                    "copy_use": "internal research only",
                                    "verification_status": "missing public URL",
                                },
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            ledger_path.write_text(json.dumps({"version": 1, "uses": []}), encoding="utf-8")

            results = select_customer_proofs(
                "Google review story quote invoice",
                index_path=index_path,
                ledger_path=ledger_path,
                limit=5,
                require_eeat_story=True,
            )

        self.assertEqual(results, [])

    def test_capterra_theme_row_ranks_for_quoting_invoicing_objective(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            index_path = root / "customer-proof-index.json"
            ledger_path = root / "customer-proof-usage-ledger.json"
            index_path.write_text(
                json.dumps(
                    {
                        "version": 1,
                        "proof": [
                            {
                                "proof_id": "case-study-generic-payments",
                                "customer": "Generic Payments Case",
                                "source_type": "case_study",
                                "workflow_fit": ["payments", "cash flow"],
                                "themes": ["payment collection"],
                                "public_url": "https://www.simprogroup.com/case-studies/generic-payments",
                                "approval_status": "approved",
                                "public_copy_allowed": True,
                                "evidence": "Generic payment collection proof.",
                            },
                            {
                                "proof_id": "review-capterra-qbo-service-jobs-quotes-invoices",
                                "customer": "Capterra owner review with QBO integration",
                                "source_type": "review_site",
                                "workflow_fit": ["service jobs", "recurring jobs", "quoting", "invoicing", "QBO"],
                                "themes": ["service jobs", "quotes", "invoices", "QuickBooks Online integration"],
                                "public_url": "https://www.capterra.com/p/10529/Simpro-Enterprise/reviews/",
                                "approval_status": "ready",
                                "public_copy_allowed": True,
                                "evidence": "Capterra row describes an owner using Simpro for service jobs, recurring jobs, invoicing, quotes, and QuickBooks Online integration.",
                                "review_story": {
                                    "story_allowed": True,
                                    "identity_type": "person",
                                    "identity_display": "Megan B",
                                    "business_name": "",
                                    "person_name": "Megan B",
                                    "role_title": "Owner",
                                    "platform": "Capterra",
                                    "source_row_ref": "Capterra tab row 50",
                                    "public_url": "https://www.capterra.com/p/10529/Simpro-Enterprise/reviews/",
                                    "workflow_story": "Owner describes service jobs, recurring jobs, quotes, invoices, and QBO integration.",
                                    "objective_fit": ["quote-to-cash", "small trade business"],
                                    "copy_use": "paraphrased theme or E-E-A-T story with same-paragraph source link",
                                    "verification_status": "brand-captured public review source",
                                },
                            },
                        ],
                    }
                ),
                encoding="utf-8",
            )
            ledger_path.write_text(json.dumps({"version": 1, "uses": []}), encoding="utf-8")

            results = select_customer_proofs(
                "best job quoting and invoicing software",
                index_path=index_path,
                ledger_path=ledger_path,
                title="Best job quoting and invoicing software",
                objective="help field service buyers evaluate quote-to-cash tools with Capterra review themes",
                proof_role="theme",
                limit=2,
            )

        self.assertEqual(results[0]["proof_id"], "review-capterra-qbo-service-jobs-quotes-invoices")
        self.assertEqual(results[0]["source_type"], "review_site")

    def test_cli_json_output_remains_default_without_slate_flag(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            index_path, ledger_path = write_selector_fixture(root)
            buffer = StringIO()

            with redirect_stdout(buffer):
                exit_code = _main(
                    [
                        "best job quoting and invoicing software",
                        "--index",
                        str(index_path),
                        "--ledger",
                        str(ledger_path),
                        "--proof-role",
                        "metric",
                        "--limit",
                        "1",
                    ]
                )

            payload = json.loads(buffer.getvalue())

        self.assertEqual(exit_code, 0)
        self.assertEqual(payload["topic"], "best job quoting and invoicing software")
        self.assertEqual(payload["results"][0]["proof_id"], "quote-matrix-zebra-plumbing-onsite-quoting")

    def test_cli_slate_output_emits_customer_proof_slate_for_roles(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            index_path, ledger_path = write_selector_fixture(root)
            buffer = StringIO()

            with redirect_stdout(buffer):
                exit_code = _main(
                    [
                        "best job quoting and invoicing software",
                        "--title",
                        "Best job quoting and invoicing software",
                        "--objective",
                        "help field service buyers evaluate quote-to-cash software",
                        "--index",
                        str(index_path),
                        "--ledger",
                        str(ledger_path),
                        "--slate",
                        "--roles",
                        "metric,quote,theme,experience_story",
                        "--require-eeat-story",
                        "--limit",
                        "3",
                    ]
                )

            output = buffer.getvalue()

        self.assertEqual(exit_code, 0)
        self.assertIn("Customer Proof Slate", output)
        self.assertIn(
            '- Selector command: python data_sources/modules/customer_proof_selector.py "best job quoting and invoicing software"',
            output,
        )
        self.assertIn(
            "- Role: metric | Top candidates: [quote-matrix-zebra-plumbing-onsite-quoting]",
            output,
        )
        self.assertIn(
            "Selected: [quote-matrix-zebra-plumbing-onsite-quoting]",
            output,
        )
        self.assertIn(
            "- Role: quote | Top candidates: [quote-matrix-bwe-engineering-job-to-invoice]",
            output,
        )
        self.assertIn(
            "- Role: experience_story | Top candidates: [review-capterra-qbo-service-jobs-quotes-invoices]",
            output,
        )

    def test_cli_slate_output_honors_selected_and_reject_overrides(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            index_path, ledger_path = write_selector_fixture(root)
            buffer = StringIO()

            with redirect_stdout(buffer):
                exit_code = _main(
                    [
                        "best job quoting and invoicing software",
                        "--index",
                        str(index_path),
                        "--ledger",
                        str(ledger_path),
                        "--slate",
                        "--roles",
                        "metric,theme",
                        "--selected",
                        "theme=review-capterra-qbo-service-jobs-quotes-invoices",
                        "--reject",
                        "theme=quote-matrix-zebra-plumbing-onsite-quoting:metric proof fits a different section",
                        "--limit",
                        "3",
                    ]
                )

            output = buffer.getvalue()

        self.assertEqual(exit_code, 0)
        self.assertIn(
            "- Role: theme | Top candidates: [quote-matrix-zebra-plumbing-onsite-quoting, review-capterra-qbo-service-jobs-quotes-invoices",
            output,
        )
        self.assertIn("Selected: [review-capterra-qbo-service-jobs-quotes-invoices]", output)
        self.assertIn(
            "Rejected stronger candidates: [quote-matrix-zebra-plumbing-onsite-quoting: metric proof fits a different section]",
            output,
        )


if __name__ == "__main__":
    unittest.main()
