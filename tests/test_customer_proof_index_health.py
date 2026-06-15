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
                    "proof_assets",
                    "total_rows",
                    "workflow_coverage",
                ],
                sorted(payload.keys()),
            )
            self.assertEqual(before_index, index_path.read_text(encoding="utf-8"))
            self.assertEqual(before_ledger, ledger_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
