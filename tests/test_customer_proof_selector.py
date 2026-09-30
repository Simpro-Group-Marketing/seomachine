import hashlib
import json
import unittest
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from data_sources.modules.customer_proof_selector import (
    LEGACY_INDEX_ERROR,
    CustomerProofDataError,
    _main,
    select_customer_proofs,
)
from tests.vault_context_fixture import (
    load_validated_claim_set_for_unit_test,
    write_connector_context_fixture,
)


def canonical_json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_json(value: object) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def write_ledger(root: Path, uses: list[dict[str, object]] | None = None) -> Path:
    ledger_path = root / "customer-proof-usage-ledger.json"
    ledger_path.write_text(
        json.dumps({"version": 1, "uses": uses or []}),
        encoding="utf-8",
    )
    return ledger_path


def write_selector_fixture(root: Path) -> tuple[Path, Path]:
    index_path = root / "customer-proof-index.json"
    index_path.write_text(
        json.dumps(
            {
                "version": 1,
                "proof": [
                    {
                        "proof_id": "case-study-schaffer-beacon-mechanical",
                        "customer": "Schaffer Beacon Mechanical",
                        "source_type": "case_study",
                        "workflow_fit": ["hvac scheduling", "field service"],
                        "themes": ["connected scheduling workflows"],
                        "public_url": "https://www.simprogroup.com/case-studies/schaffer-beacon-mechanical",
                        "approval_status": "approved",
                        "public_copy_allowed": True,
                        "approved_metrics": [
                            {
                                "claim": "Schaffer Beacon Mechanical improved operational control with connected workflows.",
                                "status": "approved",
                            }
                        ],
                    },
                    {
                        "proof_id": "quote-matrix-bwe-engineering-job-to-invoice",
                        "customer": "BWE Engineering",
                        "source_type": "quote_matrix",
                        "workflow_fit": ["job cards", "invoicing", "cash flow"],
                        "themes": ["job-to-invoice workflow"],
                        "public_url": "https://www.simprogroup.com/case-studies/bwe-engineering",
                        "approval_status": "approved",
                        "public_copy_allowed": True,
                        "approved_quotes": [
                            {
                                "quote": "Approved quote about job-to-invoice workflow.",
                                "status": "approved",
                            }
                        ],
                    },
                    {
                        "proof_id": "review-capterra-qbo-service-jobs-quotes-invoices",
                        "customer": "Megan B",
                        "source_type": "review_site",
                        "workflow_fit": [
                            "service jobs",
                            "quoting",
                            "invoicing",
                            "QuickBooks Online",
                        ],
                        "themes": [
                            "service jobs",
                            "quotes",
                            "invoices",
                            "QuickBooks Online integration",
                        ],
                        "public_url": "https://www.capterra.com/p/10529/Simpro-Enterprise/reviews/",
                        "approval_status": "approved",
                        "public_copy_allowed": True,
                        "review_story": {
                            "story_allowed": True,
                            "identity_type": "person",
                            "identity_display": "Megan B",
                            "person_name": "Megan B",
                            "platform": "Capterra",
                            "public_url": "https://www.capterra.com/p/10529/Simpro-Enterprise/reviews/",
                            "workflow_story": "Megan B describes service jobs, quotes, invoices, and QuickBooks Online integration.",
                        },
                    },
                ],
            }
        ),
        encoding="utf-8",
    )
    return index_path, write_ledger(root)


def write_context_receipt_fixture(root: Path, index_path: Path) -> tuple[Path, Path]:
    index = json.loads(index_path.read_text(encoding="utf-8"))
    rows: list[dict[str, object]] = []
    for item in index.get("proof", []):
        if not isinstance(item, dict):
            continue
        proof_id = str(item.get("proof_id") or "").strip()
        if not proof_id:
            continue
        source_type = str(item.get("source_type") or "")
        base = {
            "claim_id": proof_id,
            "brand_scope": ["Simpro"],
            "source_hash": proof_id,
            "public_url": str(item.get("public_url") or ""),
            "approval_source": "connector_claim_result",
            "source_type": source_type,
            "customer": str(item.get("customer") or ""),
            "workflow_fit": item.get("workflow_fit") or [],
            "themes": item.get("themes") or [],
        }
        if source_type == "review_site":
            story = item.get("review_story") if isinstance(item.get("review_story"), dict) else {}
            rows.append(
                {
                    **base,
                    "assertion": str(
                        story.get("workflow_story")
                        or " ".join(str(value) for value in item.get("themes") or [])
                        or proof_id
                    ),
                    "use_mode": "public_paraphrase",
                    "claim_type": "review_theme",
                    "identity_type": str(story.get("identity_type") or "person"),
                    "identity_display": str(
                        story.get("identity_display")
                        or item.get("customer")
                        or proof_id
                    ),
                    "person_name": str(story.get("person_name") or ""),
                    "business_name": str(story.get("business_name") or ""),
                    "workflow_story": str(story.get("workflow_story") or ""),
                }
            )
            continue
        quotes = item.get("approved_quotes") if isinstance(item.get("approved_quotes"), list) else []
        if quotes:
            quote = quotes[0]
            rows.append(
                {
                    **base,
                    "assertion": str(quote.get("quote") if isinstance(quote, dict) else quote),
                    "use_mode": "exact_quote",
                    "claim_type": "customer_quote",
                }
            )
            continue
        metrics = item.get("approved_metrics") if isinstance(item.get("approved_metrics"), list) else []
        if metrics:
            metric = metrics[0]
            rows.append(
                {
                    **base,
                    "assertion": str(
                        (metric.get("claim") or metric.get("metric"))
                        if isinstance(metric, dict)
                        else metric
                    ),
                    "use_mode": "public_metric",
                    "claim_type": "customer_metric",
                }
            )
            continue
        rows.append(
            {
                **base,
                "assertion": " ".join(str(value) for value in item.get("themes") or []) or proof_id,
                "use_mode": "public_paraphrase",
                "claim_type": "customer_theme",
            }
        )
    return write_connector_context_fixture(
        root,
        rows,
        claim_search_modes=["exact_quote", "public_metric", "public_paraphrase"],
    )


def proof_claims() -> list[dict[str, object]]:
    return [
        {
            "claim_id": "claim-zebra-metric",
            "assertion": "Zebra Plumbing reduced quote-to-cash cycle time with Simpro.",
            "use_mode": "public_metric",
            "claim_type": "customer_metric",
            "brand_scope": ["Simpro"],
            "source_hash": "zebra-metric",
            "public_url": "https://www.simprogroup.com/case-studies/zebra-plumbing",
            "approval_source": "connector_claim_result",
            "source_type": "quote_matrix",
            "customer": "Zebra Plumbing",
            "workflow_fit": ["quoting", "invoicing"],
            "themes": ["quote-to-cash"],
        },
        {
            "claim_id": "claim-bwe-quote",
            "assertion": "Approved public quote text for BWE Engineering.",
            "use_mode": "exact_quote",
            "claim_type": "customer_quote",
            "brand_scope": ["Simpro"],
            "source_hash": "bwe-quote",
            "public_url": "https://www.simprogroup.com/case-studies/bwe-engineering",
            "approval_source": "connector_claim_result",
            "source_type": "quote_matrix",
            "customer": "BWE Engineering",
            "workflow_fit": ["job cards", "invoicing"],
            "themes": ["job-to-invoice workflow"],
        },
        {
            "claim_id": "claim-capterra-story",
            "assertion": "Owner describes service jobs, quotes, invoices, and QBO integration.",
            "use_mode": "public_paraphrase",
            "claim_type": "review_theme",
            "brand_scope": ["Simpro"],
            "source_hash": "capterra-story",
            "public_url": "https://www.capterra.com/p/10529/Simpro-Enterprise/reviews/",
            "approval_source": "connector_claim_result",
            "source_type": "review_site",
            "identity_type": "person",
            "identity_display": "Megan B",
            "person_name": "Megan B",
            "workflow_story": "Owner describes service jobs, quotes, invoices, and QBO integration.",
            "workflow_fit": ["service jobs", "quoting", "invoicing", "QBO"],
            "themes": ["quotes", "invoices", "QuickBooks Online integration"],
        },
    ]


class CustomerProofSelectorTests(unittest.TestCase):
    def setUp(self) -> None:
        validation_patch = patch(
            "data_sources.modules.customer_proof.connector_inputs.load_validated_claim_set",
            new=load_validated_claim_set_for_unit_test,
        )
        validation_patch.start()
        self.addCleanup(validation_patch.stop)

    def test_legacy_index_interface_fails_closed(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            ledger_path = write_ledger(root)

            with self.assertRaisesRegex(CustomerProofDataError, "Local customer proof indexes"):
                select_customer_proofs(
                    "quoting and invoicing",
                    index_path=root / "customer-proof-index.json",
                    ledger_path=ledger_path,
                    proof_role="metric",
                )

    def test_claim_id_is_selector_candidate_identifier(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            ledger_path = write_ledger(root)
            pack_path, receipt_path = write_connector_context_fixture(root, proof_claims())

            results = select_customer_proofs(
                "quoting invoicing quote-to-cash",
                ledger_path=ledger_path,
                context_pack=pack_path,
                context_receipt=receipt_path,
                proof_role="metric",
                limit=3,
            )

        self.assertEqual(results[0]["proof_id"], "claim-zebra-metric")
        self.assertEqual(results[0]["candidate_id"], "claim-zebra-metric")
        self.assertEqual(results[0]["claim_id"], "claim-zebra-metric")
        self.assertEqual(results[0]["binding_source"], "claim_id")
        self.assertEqual(results[0]["authority_resource_id"][:4], "res-")

    def test_cli_writes_v2_evidence_from_vault_claims(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            ledger_path = write_ledger(root)
            pack_path, receipt_path = write_connector_context_fixture(root, proof_claims())
            evidence_path = root / "selector-evidence.json"
            stdout = StringIO()
            stderr = StringIO()

            with redirect_stdout(stdout), redirect_stderr(stderr):
                exit_code = _main(
                    [
                        "quoting invoicing review story",
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
                        "--evidence-output",
                        str(evidence_path),
                    ]
                )

            evidence = json.loads(evidence_path.read_text(encoding="utf-8"))

        self.assertEqual(exit_code, 0)
        self.assertEqual(stderr.getvalue(), "")
        self.assertEqual(evidence["schema"], "simpro-customer-proof-selector-evidence/v2")
        self.assertEqual(
            set(evidence["artifacts"]),
            {"ledger", "context_pack", "context_receipt"},
        )
        self.assertNotIn("index", evidence["artifacts"])
        roles = {row["role"]: row for row in evidence["roles"]}
        self.assertEqual(roles["metric"]["candidate_ids"], ["claim-zebra-metric"])
        self.assertEqual(roles["quote"]["candidate_ids"], ["claim-bwe-quote"])
        self.assertEqual(roles["experience_story"]["selected_id"], "claim-capterra-story")
        self.assertIn("Approval source: connector_claim_result", stdout.getvalue())

    def test_no_fit_requires_complete_claim_searches(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            ledger_path = write_ledger(root)
            pack_path, receipt_path = write_connector_context_fixture(
                root,
                [],
                claim_search_modes=[
                    "exact_quote",
                    "public_metric",
                    "public_paraphrase",
                ],
            )
            evidence_path = root / "selector-evidence.json"
            stdout = StringIO()
            stderr = StringIO()

            with redirect_stdout(stdout), redirect_stderr(stderr):
                exit_code = _main(
                    [
                        "topic with no customer proof",
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
                        "--allow-no-proof",
                        "--evidence-output",
                        str(evidence_path),
                    ]
                )

            evidence = json.loads(evidence_path.read_text(encoding="utf-8"))

        self.assertEqual(exit_code, 0)
        self.assertEqual(stderr.getvalue(), "")
        self.assertEqual(evidence["selection_outcome"], "no_fit_customer_proof")
        self.assertIn("- Selection outcome: no_fit_customer_proof", stdout.getvalue())
        for row in evidence["roles"]:
            self.assertEqual(row["candidate_ids"], [])
            self.assertEqual(row["claim_ids"], [])
            self.assertEqual(row["selected_id"], "none")
            self.assertIn("complete, non-truncated claim searches", row["no_fit_reason"])

    def test_no_fit_accepts_hash_bound_claim_lookup_artifact(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            ledger_path = write_ledger(root)
            pack_path, receipt_path = write_connector_context_fixture(root, [])
            lookup_path = root / "claim-lookup.json"
            lookup_path.write_text(
                json.dumps(
                    {
                        "schema": "simpro-customer-proof-claim-lookup/v1",
                        "source": "SimproVaultClient.claims",
                        "lookups": [
                            {
                                "query": "metric query",
                                "use_mode": "public_metric",
                                "brand_scope": "Simpro",
                                "status": "complete",
                                "truncated": False,
                                "result_count": 0,
                            },
                            {
                                "query": "quote query",
                                "use_mode": "exact_quote",
                                "brand_scope": "Simpro",
                                "status": "complete",
                                "truncated": False,
                                "result_count": 0,
                            },
                            {
                                "query": "theme query",
                                "use_mode": "public_paraphrase",
                                "brand_scope": "Simpro",
                                "status": "complete",
                                "truncated": False,
                                "result_count": 0,
                            },
                        ],
                    }
                ),
                encoding="utf-8",
            )
            evidence_path = root / "selector-evidence.json"
            stdout = StringIO()
            stderr = StringIO()

            with redirect_stdout(stdout), redirect_stderr(stderr):
                exit_code = _main(
                    [
                        "topic with no customer proof",
                        "--ledger",
                        str(ledger_path),
                        "--context-pack",
                        str(pack_path),
                        "--context-receipt",
                        str(receipt_path),
                        "--claim-lookup-evidence",
                        str(lookup_path),
                        "--slate",
                        "--roles",
                        "metric,quote,theme,experience_story",
                        "--require-eeat-story",
                        "--allow-no-proof",
                        "--evidence-output",
                        str(evidence_path),
                    ]
                )

            evidence = json.loads(evidence_path.read_text(encoding="utf-8"))

        self.assertEqual(exit_code, 0)
        self.assertEqual(stderr.getvalue(), "")
        self.assertEqual(evidence["selection_outcome"], "no_fit_customer_proof")
        self.assertIn("claim_lookup", evidence["artifacts"])
        self.assertIn("- Selection outcome: no_fit_customer_proof", stdout.getvalue())

    def test_cli_json_mode_accepts_claim_lookup_evidence(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            ledger_path = write_ledger(root)
            pack_path, receipt_path = write_connector_context_fixture(root, proof_claims())
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
            receipt.pop("receipt_sha256", None)
            receipt.pop("claim_searches", None)
            receipt["receipt_sha256"] = sha256_json(receipt)
            receipt_path.write_text(json.dumps(receipt, indent=2), encoding="utf-8")
            lookup_path = root / "claim-lookup.json"
            lookup_path.write_text(
                json.dumps(
                    {
                        "schema": "simpro-customer-proof-claim-lookup/v1",
                        "source": "SimproVaultClient.claims",
                        "lookups": [
                            {
                                "query": "metric query",
                                "use_mode": "public_metric",
                                "brand_scope": "Simpro",
                                "status": "complete",
                                "truncated": False,
                                "result_count": 1,
                                "result_ids": ["claim-zebra-metric"],
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            stdout = StringIO()
            stderr = StringIO()

            with redirect_stdout(stdout), redirect_stderr(stderr):
                exit_code = _main(
                    [
                        "quoting invoicing",
                        "--ledger",
                        str(ledger_path),
                        "--context-pack",
                        str(pack_path),
                        "--context-receipt",
                        str(receipt_path),
                        "--claim-lookup-evidence",
                        str(lookup_path),
                        "--proof-role",
                        "metric",
                        "--limit",
                        "1",
                    ]
                )

            payload = json.loads(stdout.getvalue())

        self.assertEqual(exit_code, 0)
        self.assertEqual(stderr.getvalue(), "")
        self.assertEqual(payload["results"][0]["claim_id"], "claim-zebra-metric")

    def test_truncated_claim_search_blocks_selector(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            ledger_path = write_ledger(root)
            pack_path, receipt_path = write_connector_context_fixture(root, proof_claims())
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
            receipt.pop("receipt_sha256", None)
            receipt["claim_searches"][0]["truncated"] = True
            receipt["receipt_sha256"] = sha256_json(receipt)
            receipt_path.write_text(json.dumps(receipt, indent=2), encoding="utf-8")

            with self.assertRaisesRegex(CustomerProofDataError, "claim search.*truncated"):
                select_customer_proofs(
                    "quoting invoicing",
                    ledger_path=ledger_path,
                    context_pack=pack_path,
                    context_receipt=receipt_path,
                    proof_role="metric",
                    limit=1,
                )

    def test_cli_rejects_legacy_index_argument(self) -> None:
        stderr = StringIO()
        with redirect_stderr(stderr), self.assertRaises(SystemExit) as raised:
            _main(["quoting", "--index", "legacy-proof-index.json"])

        self.assertEqual(raised.exception.code, 2)
        self.assertIn(LEGACY_INDEX_ERROR, stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
