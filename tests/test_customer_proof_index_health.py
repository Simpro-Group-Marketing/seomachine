import json
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory

from data_sources.modules.customer_proof_index_health import analyze_proof_index, main


def write_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


class CustomerProofIndexHealthTests(unittest.TestCase):
    def test_analyze_proof_index_summarizes_counts_and_proof_assets(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            index_path = root / "customer-proof-index.json"
            ledger_path = root / "customer-proof-usage-ledger.json"
            write_json(
                index_path,
                {
                    "version": 1,
                    "proof": [
                        {
                            "proof_id": "case-study-teamwired",
                            "customer": "TEAMWired",
                            "source_type": "case_study",
                            "workflow_fit": ["invoicing", "payments"],
                            "approval_status": "approved",
                            "public_copy_allowed": True,
                            "public_url": "https://www.simprogroup.com/case-studies/teamwired",
                            "approved_metrics": [
                                {
                                    "claim": "TEAMWired manual invoicing time fell by 90%",
                                    "status": "approved",
                                }
                            ],
                        },
                        {
                            "proof_id": "quote-matrix-bwe-engineering-job-to-invoice",
                            "customer": "BWE Engineering",
                            "source_type": "quote_matrix",
                            "workflow_fit": ["job cards", "invoicing"],
                            "approval_status": "approved",
                            "public_copy_allowed": True,
                            "public_url": "https://www.simprogroup.com/case-studies/bwe-engineering",
                            "approved_quotes": [
                                {
                                    "quote": "Approved short quote",
                                    "status": "approved",
                                }
                            ],
                        },
                        {
                            "proof_id": "customer-story-internal-only",
                            "customer": "Internal Customer Story",
                            "source_type": "customer_story",
                            "workflow_fit": ["quoting"],
                            "approval_status": "ready",
                            "public_copy_allowed": False,
                            "restrictions": ["Internal story route only"],
                        },
                    ],
                },
            )
            write_json(ledger_path, {"version": 1, "uses": []})

            report = analyze_proof_index(index_path=index_path, ledger_path=ledger_path)

            self.assertEqual(3, report["total_rows"])
            self.assertEqual(
                {"case_study": 1, "customer_story": 1, "quote_matrix": 1},
                report["counts"]["source_type"],
            )
            self.assertEqual({"approved": 2, "ready": 1}, report["counts"]["approval_status"])
            self.assertEqual({"false": 1, "true": 2}, report["counts"]["public_copy_allowed"])
            self.assertEqual(1, report["proof_assets"]["rows_with_approved_quotes"])
            self.assertEqual(1, report["proof_assets"]["approved_quote_count"])
            self.assertEqual(1, report["proof_assets"]["rows_with_approved_metrics"])
            self.assertEqual(1, report["proof_assets"]["approved_metric_count"])
            invoicing = next(row for row in report["workflow_coverage"] if row["workflow"] == "invoicing")
            self.assertEqual(2, invoicing["total_rows"])
            self.assertEqual(2, invoicing["approved_public_rows"])
            blocked = report["blocked_from_public_copy"]
            self.assertEqual("customer-story-internal-only", blocked[0]["proof_id"])
            self.assertIn("public_copy_allowed false", blocked[0]["reasons"])

    def test_analyze_proof_index_flags_overused_rows_from_ledger_baselines(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            index_path = root / "customer-proof-index.json"
            ledger_path = root / "customer-proof-usage-ledger.json"
            write_json(
                index_path,
                {
                    "version": 1,
                    "proof": [
                        {
                            "proof_id": "case-study-teamwired",
                            "customer": "TEAMWired",
                            "source_type": "case_study",
                            "workflow_fit": ["invoicing"],
                            "approval_status": "approved",
                            "public_copy_allowed": True,
                            "public_url": "https://www.simprogroup.com/case-studies/teamwired",
                        }
                    ],
                },
            )
            write_json(
                ledger_path,
                {
                    "version": 1,
                    "overuse_baselines": [
                        {
                            "proof_id": "case-study-teamwired",
                            "customer": "TEAMWired",
                            "source_url": "https://www.simprogroup.com/case-studies/teamwired",
                            "recent_uses_90d": 3,
                            "total_uses": 3,
                        }
                    ],
                    "uses": [],
                },
            )

            report = analyze_proof_index(index_path=index_path, ledger_path=ledger_path)

            self.assertEqual(1, len(report["overused_proof"]))
            overused = report["overused_proof"][0]
            self.assertEqual("case-study-teamwired", overused["proof_id"])
            self.assertEqual(3, overused["recent_uses_90d"])
            self.assertTrue(overused["overused"])

    def test_json_cli_outputs_stable_keys_and_does_not_mutate_files(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            index_path = root / "customer-proof-index.json"
            ledger_path = root / "customer-proof-usage-ledger.json"
            write_json(
                index_path,
                {
                    "version": 1,
                    "proof": [
                        {
                            "proof_id": "review-capterra-quote-theme",
                            "customer": "Capterra review theme",
                            "source_type": "review_site",
                            "workflow_fit": ["quoting", "invoicing"],
                            "approval_status": "ready",
                            "public_copy_allowed": True,
                        }
                    ],
                },
            )
            write_json(ledger_path, {"version": 1, "uses": []})
            before_index = index_path.read_text(encoding="utf-8")
            before_ledger = ledger_path.read_text(encoding="utf-8")

            output = StringIO()
            with redirect_stdout(output):
                exit_code = main(
                    [
                        "--index",
                        str(index_path),
                        "--ledger",
                        str(ledger_path),
                        "--json",
                    ]
                )
            payload = json.loads(output.getvalue())

            self.assertEqual(0, exit_code)
            self.assertEqual(
                [
                    "blocked_from_public_copy",
                    "counts",
                    "gaps",
                    "index_path",
                    "ledger_path",
                    "overused_proof",
                    "priority_intake_targets",
                    "priority_workflow_gaps",
                    "proof_assets",
                    "rows_without_public_web_url",
                    "total_rows",
                    "workflow_coverage",
                ],
                sorted(payload.keys()),
            )
            self.assertEqual(before_index, index_path.read_text(encoding="utf-8"))
            self.assertEqual(before_ledger, ledger_path.read_text(encoding="utf-8"))

    def test_priority_intake_targets_rank_ready_public_references_first(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            index_path = root / "customer-proof-index.json"
            ledger_path = root / "customer-proof-usage-ledger.json"
            write_json(
                index_path,
                {
                    "version": 1,
                    "proof": [
                        {
                            "proof_id": "customer-story-internal-service-workflow",
                            "customer": "Internal Story",
                            "source_type": "customer_story",
                            "workflow_fit": ["service workflow"],
                            "approval_status": "ready",
                            "public_copy_allowed": False,
                            "internal_source_ref": "Customer Story folder row 2",
                        },
                        {
                            "proof_id": "reference-level-group-quote-operations-visibility",
                            "customer": "Level Group",
                            "source_type": "reference",
                            "workflow_fit": ["quoting", "operations visibility"],
                            "approval_status": "ready",
                            "public_copy_allowed": True,
                            "public_url": "https://www.simprogroup.com/resources/videos/level-group",
                        },
                        {
                            "proof_id": "review-google-no-public-url",
                            "customer": "Google review candidate",
                            "source_type": "review_site",
                            "workflow_fit": ["field notes"],
                            "approval_status": "candidate",
                            "public_copy_allowed": False,
                            "internal_source_ref": "Google Review Quotes tab row 9",
                        },
                    ],
                },
            )
            write_json(ledger_path, {"version": 1, "uses": []})

            report = analyze_proof_index(index_path=index_path, ledger_path=ledger_path)

            self.assertEqual(
                "reference-level-group-quote-operations-visibility",
                report["priority_intake_targets"][0]["proof_id"],
            )
            self.assertEqual("approve_theme_only", report["priority_intake_targets"][0]["recommended_action"])
            self.assertGreater(
                report["priority_intake_targets"][0]["priority_score"],
                report["priority_intake_targets"][1]["priority_score"],
            )

    def test_priority_intake_targets_skip_source_register_placeholders(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            index_path = root / "customer-proof-index.json"
            ledger_path = root / "customer-proof-usage-ledger.json"
            write_json(
                index_path,
                {
                    "version": 1,
                    "proof": [
                        {
                            "proof_id": "references-source-register",
                            "customer": "Simpro References source register",
                            "source_type": "reference",
                            "workflow_fit": ["reference matching", "customer proof"],
                            "approval_status": "ready",
                            "public_copy_allowed": False,
                            "public_url": "https://docs.google.com/presentation/d/example/edit",
                            "restrictions": [
                                "Selection and governance source only; public copy requires approved proof."
                            ],
                        },
                        {
                            "proof_id": "review-site-simpro-g2",
                            "customer": "Simpro G2 review themes",
                            "source_type": "review_site",
                            "workflow_fit": ["implementation", "workflow pain"],
                            "approval_status": "ready",
                            "public_copy_allowed": False,
                            "public_url": "https://www.g2.com/products/simpro/reviews",
                        },
                    ],
                },
            )
            write_json(ledger_path, {"version": 1, "uses": []})

            report = analyze_proof_index(index_path=index_path, ledger_path=ledger_path)
            target_ids = {row["proof_id"] for row in report["priority_intake_targets"]}

            self.assertNotIn("references-source-register", target_ids)
            self.assertIn("review-site-simpro-g2", target_ids)

    def test_approved_internal_routes_use_public_copy_or_url_actions(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            index_path = root / "customer-proof-index.json"
            ledger_path = root / "customer-proof-usage-ledger.json"
            write_json(
                index_path,
                {
                    "version": 1,
                    "proof": [
                        {
                            "proof_id": "review-site-simpro-g2",
                            "customer": "Simpro G2 review themes",
                            "source_type": "review_site",
                            "workflow_fit": ["implementation", "workflow pain"],
                            "approval_status": "approved",
                            "public_copy_allowed": False,
                            "public_url": "https://www.g2.com/products/simpro/reviews",
                        },
                        {
                            "proof_id": "customer-story-queenstown-plumbing",
                            "customer": "Queenstown Plumbing",
                            "source_type": "customer_story",
                            "workflow_fit": ["quote-to-cash"],
                            "approval_status": "approved",
                            "public_copy_allowed": False,
                            "internal_source_ref": "Customer Story folder row",
                        },
                    ],
                },
            )
            write_json(ledger_path, {"version": 1, "uses": []})

            report = analyze_proof_index(index_path=index_path, ledger_path=ledger_path)
            targets = {row["proof_id"]: row for row in report["priority_intake_targets"]}

            self.assertEqual("resolve_public_copy_permission", targets["review-site-simpro-g2"]["recommended_action"])
            self.assertNotIn("approval_status approved", targets["review-site-simpro-g2"]["blocking_reasons"])
            self.assertEqual("remove_from_active_index", targets["customer-story-queenstown-plumbing"]["recommended_action"])
            self.assertNotIn(
                "approval_status approved",
                targets["customer-story-queenstown-plumbing"]["blocking_reasons"],
            )
            self.assertEqual(
                ["customer-story-queenstown-plumbing"],
                [row["proof_id"] for row in report["rows_without_public_web_url"]],
            )

    def test_priority_workflow_gaps_group_and_rank_useful_gap_candidates(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            index_path = root / "customer-proof-index.json"
            ledger_path = root / "customer-proof-usage-ledger.json"
            write_json(
                index_path,
                {
                    "version": 1,
                    "proof": [
                        {
                            "proof_id": "reference-mekhane-roofing-project-visibility",
                            "customer": "Mekhane Roofing",
                            "source_type": "reference",
                            "workflow_fit": ["project visibility", "job costing"],
                            "approval_status": "ready",
                            "public_copy_allowed": True,
                            "public_url": "https://www.simprogroup.com/resources/videos/mekhane-roofing",
                        },
                        {
                            "proof_id": "customer-story-obrien-electrical-plumbing-simprosium",
                            "customer": "O'Brien Electrical & Plumbing",
                            "source_type": "customer_story",
                            "workflow_fit": ["electrical workflow", "plumbing workflow"],
                            "approval_status": "ready",
                            "public_copy_allowed": False,
                            "internal_source_ref": "2023 Simprosium Quotes tab row 10",
                        },
                    ],
                },
            )
            write_json(ledger_path, {"version": 1, "uses": []})

            report = analyze_proof_index(index_path=index_path, ledger_path=ledger_path)

            self.assertEqual("job costing", report["priority_workflow_gaps"][0]["workflow"])
            self.assertEqual(
                "reference-mekhane-roofing-project-visibility",
                report["priority_workflow_gaps"][0]["best_candidate"],
            )
            electrical_gap = next(
                gap for gap in report["priority_workflow_gaps"] if gap["workflow"] == "electrical workflow"
            )
            self.assertEqual("remove_from_active_index", electrical_gap["recommended_action"])

    def test_priority_workflow_gaps_do_not_select_source_register_as_best_candidate(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            index_path = root / "customer-proof-index.json"
            ledger_path = root / "customer-proof-usage-ledger.json"
            write_json(
                index_path,
                {
                    "version": 1,
                    "proof": [
                        {
                            "proof_id": "customer-stories-source-register",
                            "customer": "Simpro Customer Stories source register",
                            "source_type": "customer_story",
                            "workflow_fit": ["quote-to-cash"],
                            "approval_status": "ready",
                            "public_copy_allowed": False,
                            "public_url": "https://docs.google.com/presentation/d/example/edit",
                            "restrictions": [
                                "Selection source only; individual quotes and metrics still need row-level approval."
                            ],
                        },
                        {
                            "proof_id": "customer-story-queenstown-plumbing",
                            "customer": "Queenstown Plumbing",
                            "source_type": "customer_story",
                            "workflow_fit": ["quote-to-cash"],
                            "approval_status": "candidate",
                            "public_copy_allowed": False,
                        },
                    ],
                },
            )
            write_json(ledger_path, {"version": 1, "uses": []})

            report = analyze_proof_index(index_path=index_path, ledger_path=ledger_path)
            quote_to_cash_gap = next(
                gap for gap in report["priority_workflow_gaps"] if gap["workflow"] == "quote-to-cash"
            )

            self.assertEqual("customer-story-queenstown-plumbing", quote_to_cash_gap["best_candidate"])
            self.assertNotIn("customer-stories-source-register", quote_to_cash_gap["candidate_proof_ids"])

    def test_default_index_contains_only_public_web_url_rows(self):
        report = analyze_proof_index(
            index_path="context/customer-proof-index.json",
            ledger_path="context/customer-proof-usage-ledger.json",
        )

        self.assertEqual([], report["rows_without_public_web_url"])
        self.assertFalse(any(row["recommended_action"] == "remove_from_active_index" for row in report["priority_intake_targets"]))

    def test_text_report_prints_priority_sections(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            index_path = root / "customer-proof-index.json"
            ledger_path = root / "customer-proof-usage-ledger.json"
            write_json(
                index_path,
                {
                    "version": 1,
                    "proof": [
                        {
                            "proof_id": "reference-rcr-infrastructure-field-service-system",
                            "customer": "RCR Infrastructure",
                            "source_type": "reference",
                            "workflow_fit": ["field service management"],
                            "approval_status": "ready",
                            "public_copy_allowed": True,
                            "public_url": "https://www.simprogroup.com/resources/videos/rcr-infrastructure",
                        }
                    ],
                },
            )
            write_json(ledger_path, {"version": 1, "uses": []})

            output = StringIO()
            with redirect_stdout(output):
                exit_code = main(["--index", str(index_path), "--ledger", str(ledger_path)])

            self.assertEqual(0, exit_code)
            text = output.getvalue()
            self.assertIn("Priority intake targets", text)
            self.assertIn("Priority workflow gaps", text)
            self.assertIn("reference-rcr-infrastructure-field-service-system", text)


if __name__ == "__main__":
    unittest.main()
