import hashlib
import json
import os
import unittest
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from data_sources.modules.customer_proof_selector import (
    CustomerProofDataError,
    _main,
    build_customer_proof_slate,
    select_customer_proofs as _select_customer_proofs,
)
from tests.vault_context_fixture import (
    load_validated_claim_set_for_unit_test,
    write_connector_context_fixture,
)


def write_context_receipt_fixture(root: Path, index_path: Path) -> tuple[Path, Path]:
    index = json.loads(index_path.read_text(encoding="utf-8"))
    evidence = []
    for candidate in index.get("proof", []):
        proof_id = str(candidate.get("proof_id") or "").strip()
        public_url = str(candidate.get("public_url") or "").strip()
        if not proof_id or not public_url.startswith(("http://", "https://")):
            continue
        modes = {"public_paraphrase"}
        if candidate.get("approved_metrics"):
            modes.add("public_metric")
        if candidate.get("approved_quotes"):
            modes.add("exact_quote")
        for mode in sorted(modes):
            source_hash = f"hash-{proof_id}-{mode}"
            row = {
                "claim_id": f"claim-customer-proof-{proof_id}-{mode}",
                "selector_id": proof_id,
                "assertion": str(
                    candidate.get("evidence") or candidate.get("customer") or proof_id
                ),
                "use_mode": mode,
                "brand_scope": ["Simpro"],
                "source_hash": source_hash,
                "support_resource_hashes": {f"res-{proof_id}-{mode}": source_hash},
                "public_url": public_url,
                "approval_source": "connector_claim_result",
            }
            evidence.append(row)
    return write_connector_context_fixture(root, evidence)


def select_customer_proofs(*args, **kwargs):
    if not kwargs.get("context_pack") and not kwargs.get("context_receipt"):
        index_path = Path(kwargs.get("index_path", "context/customer-proof-index.json"))
        ledger_path = Path(kwargs.get("ledger_path", index_path))
        root = ledger_path.parent if ledger_path.parent != Path("") else Path(".")
        pack_path, receipt_path = write_context_receipt_fixture(root, index_path)
        kwargs["context_pack"] = pack_path
        kwargs["context_receipt"] = receipt_path
    return _select_customer_proofs(*args, **kwargs)


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
                        "themes": [
                            "quotes",
                            "invoices",
                            "QuickBooks Online integration",
                        ],
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
    def setUp(self):
        validation_patch = patch(
            "data_sources.modules.customer_proof_selector.load_validated_claim_set",
            new=load_validated_claim_set_for_unit_test,
        )
        validation_patch.start()
        self.addCleanup(validation_patch.stop)

    def test_public_customer_proof_requires_context_receipt(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            index_path, ledger_path = write_selector_fixture(root)

            with self.assertRaisesRegex(
                RuntimeError,
                "context receipt is unavailable.*context pack and receipt are required",
            ):
                _select_customer_proofs(
                    "best job quoting and invoicing software",
                    index_path=index_path,
                    ledger_path=ledger_path,
                    proof_role="metric",
                    limit=1,
                )

    def test_selector_fails_closed_when_receipt_has_no_customer_inventory_bindings(
        self,
    ):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            index_path, ledger_path = write_selector_fixture(root)
            pack_path, receipt_path = write_connector_context_fixture(root, [])

            with self.assertRaisesRegex(
                RuntimeError,
                "no approved claims bound to the customer proof inventory",
            ):
                _select_customer_proofs(
                    "best job quoting and invoicing software",
                    index_path=index_path,
                    ledger_path=ledger_path,
                    context_pack=pack_path,
                    context_receipt=receipt_path,
                    proof_role="experience_story",
                    require_eeat_story=True,
                    limit=10,
                )

    def test_selector_fails_closed_when_usage_ledger_is_missing(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            index_path, ledger_path = write_selector_fixture(root)
            ledger_path.unlink()
            pack_path, receipt_path = write_context_receipt_fixture(root, index_path)

            with self.assertRaisesRegex(
                RuntimeError,
                "customer proof ledger is unavailable",
            ):
                _select_customer_proofs(
                    "field service proof",
                    index_path=index_path,
                    ledger_path=ledger_path,
                    context_pack=pack_path,
                    context_receipt=receipt_path,
                    proof_role="experience_story",
                    require_eeat_story=True,
                )

    def test_selector_fails_closed_when_public_customer_inventory_is_empty(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            index_path = root / "customer-proof-index.json"
            ledger_path = root / "customer-proof-usage-ledger.json"
            index_path.write_text(
                json.dumps({"version": 1, "proof": []}),
                encoding="utf-8",
            )
            ledger_path.write_text(
                json.dumps({"version": 1, "uses": []}),
                encoding="utf-8",
            )
            pack_path, receipt_path = write_connector_context_fixture(root, [])

            with self.assertRaisesRegex(
                RuntimeError,
                "no usable public customer proof inventory",
            ):
                _select_customer_proofs(
                    "field service proof",
                    index_path=index_path,
                    ledger_path=ledger_path,
                    context_pack=pack_path,
                    context_receipt=receipt_path,
                    proof_role="experience_story",
                    require_eeat_story=True,
                )

    def test_selector_rejects_missing_non_file_and_invalid_index(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            valid_index, ledger_path = write_selector_fixture(root)
            pack_path, receipt_path = write_context_receipt_fixture(root, valid_index)
            missing_index = root / "missing-index.json"
            directory_index = root / "index-directory"
            directory_index.mkdir()
            malformed_index = root / "malformed-index.json"
            malformed_index.write_text("{not-json", encoding="utf-8")
            non_object_index = root / "non-object-index.json"
            non_object_index.write_text("[]", encoding="utf-8")

            cases = (
                (missing_index, "customer proof index is unavailable"),
                (directory_index, "customer proof index is not a regular file"),
                (malformed_index, "customer proof index is invalid JSON"),
                (non_object_index, "customer proof index is invalid JSON object"),
            )
            for index_path, message in cases:
                with (
                    self.subTest(index_path=index_path),
                    self.assertRaisesRegex(
                        CustomerProofDataError,
                        message,
                    ),
                ):
                    _select_customer_proofs(
                        "field service proof",
                        index_path=index_path,
                        ledger_path=ledger_path,
                        context_pack=pack_path,
                        context_receipt=receipt_path,
                    )

    def test_selector_rejects_missing_non_file_and_invalid_ledger(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            index_path, _valid_ledger = write_selector_fixture(root)
            pack_path, receipt_path = write_context_receipt_fixture(root, index_path)
            missing_ledger = root / "missing-ledger.json"
            directory_ledger = root / "ledger-directory"
            directory_ledger.mkdir()
            malformed_ledger = root / "malformed-ledger.json"
            malformed_ledger.write_text("[not-an-object]", encoding="utf-8")
            non_object_ledger = root / "non-object-ledger.json"
            non_object_ledger.write_text("[]", encoding="utf-8")

            cases = (
                (missing_ledger, "customer proof ledger is unavailable"),
                (directory_ledger, "customer proof ledger is not a regular file"),
                (malformed_ledger, "customer proof ledger is invalid JSON"),
                (non_object_ledger, "customer proof ledger is invalid JSON object"),
            )
            for ledger_path, message in cases:
                with (
                    self.subTest(ledger_path=ledger_path),
                    self.assertRaisesRegex(
                        CustomerProofDataError,
                        message,
                    ),
                ):
                    _select_customer_proofs(
                        "field service proof",
                        index_path=index_path,
                        ledger_path=ledger_path,
                        context_pack=pack_path,
                        context_receipt=receipt_path,
                    )

    def test_cli_returns_nonzero_when_context_receipt_is_missing(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            index_path, ledger_path = write_selector_fixture(root)
            stdout = StringIO()
            stderr = StringIO()

            with redirect_stdout(stdout), redirect_stderr(stderr):
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

        self.assertEqual(exit_code, 1)
        self.assertEqual(stdout.getvalue(), "")
        self.assertIn(
            "ERROR: Customer proof context receipt is unavailable", stderr.getvalue()
        )

    def test_slate_rejects_selected_override_outside_verified_candidates(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            index_path, ledger_path = write_selector_fixture(root)
            pack_path, receipt_path = write_context_receipt_fixture(root, index_path)

            with self.assertRaisesRegex(
                RuntimeError,
                "Selected customer proof ID is not in the verified metric candidate slate",
            ):
                build_customer_proof_slate(
                    "best job quoting and invoicing software",
                    index_path=index_path,
                    ledger_path=ledger_path,
                    context_pack=pack_path,
                    context_receipt=receipt_path,
                    roles=("metric",),
                    selected_overrides={"metric": "unapproved-proof"},
                )

    def test_cli_writes_hash_bound_selector_evidence_and_references_it_in_slate(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            index_path, ledger_path = write_selector_fixture(root)
            pack_path, receipt_path = write_context_receipt_fixture(root, index_path)
            evidence_path = root / "selector-evidence.json"
            stdout = StringIO()
            stderr = StringIO()

            with redirect_stdout(stdout), redirect_stderr(stderr):
                exit_code = _main(
                    [
                        "job quoting and invoicing",
                        "--index",
                        str(index_path),
                        "--ledger",
                        str(ledger_path),
                        "--context-pack",
                        str(pack_path),
                        "--context-receipt",
                        str(receipt_path),
                        "--title",
                        "Job quoting proof",
                        "--objective",
                        "Evaluate customer experience fit",
                        "--slate",
                        "--roles",
                        "experience_story",
                        "--require-eeat-story",
                        "--limit",
                        "10",
                        "--evidence-output",
                        str(evidence_path),
                    ]
                )

            evidence_bytes = evidence_path.read_bytes()
            evidence = json.loads(evidence_bytes)
            digest = hashlib.sha256(evidence_bytes).hexdigest()
            expected_artifacts = {
                key: {
                    "path": str(path.resolve()),
                    "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                }
                for key, path in {
                    "index": index_path,
                    "ledger": ledger_path,
                    "context_pack": pack_path,
                    "context_receipt": receipt_path,
                }.items()
            }

        self.assertEqual(exit_code, 0)
        self.assertEqual(stderr.getvalue(), "")
        self.assertEqual(
            evidence["schema"],
            "simpro-customer-proof-selector-evidence/v1",
        )
        self.assertEqual(evidence["inputs"]["roles"], ["experience_story"])
        self.assertEqual(
            evidence["roles"][0]["candidate_ids"],
            ["review-capterra-qbo-service-jobs-quotes-invoices"],
        )
        self.assertIn(
            f"- Selector evidence: {evidence_path} | SHA-256: {digest}",
            stdout.getvalue(),
        )
        self.assertEqual(evidence["artifacts"], expected_artifacts)

    def test_cli_fails_closed_if_input_changes_after_ranking_before_evidence_write(
        self,
    ):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            index_path, ledger_path = write_selector_fixture(root)
            pack_path, receipt_path = write_context_receipt_fixture(root, index_path)
            evidence_path = root / "selector-evidence.json"
            stdout = StringIO()
            stderr = StringIO()
            real_build = build_customer_proof_slate

            def mutate_after_ranking(*args, **kwargs):
                slate = real_build(*args, **kwargs)
                index_path.unlink()
                return slate

            with (
                patch(
                    "data_sources.modules.customer_proof_selector.build_customer_proof_slate",
                    side_effect=mutate_after_ranking,
                ),
                redirect_stdout(stdout),
                redirect_stderr(stderr),
            ):
                exit_code = _main(
                    [
                        "job quoting and invoicing",
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
                        "experience_story",
                        "--evidence-output",
                        str(evidence_path),
                    ]
                )

        self.assertEqual(exit_code, 1)
        self.assertEqual(stdout.getvalue(), "")
        self.assertIn(
            "Selector evidence input changed during selection", stderr.getvalue()
        )
        self.assertFalse(evidence_path.exists())

    def test_cli_removes_evidence_if_input_changes_during_atomic_write(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            index_path, ledger_path = write_selector_fixture(root)
            pack_path, receipt_path = write_context_receipt_fixture(root, index_path)
            evidence_path = root / "selector-evidence.json"
            stdout = StringIO()
            stderr = StringIO()
            real_write_bytes = Path.write_bytes

            def mutate_during_write(path, payload):
                written = real_write_bytes(path, payload)
                if path.name == f"{evidence_path.name}.tmp":
                    ledger_path.write_text(
                        json.dumps(
                            {
                                "version": 1,
                                "uses": [{"proof_id": "unexpected-post-selection-use"}],
                            }
                        ),
                        encoding="utf-8",
                    )
                return written

            with (
                patch.object(Path, "write_bytes", new=mutate_during_write),
                redirect_stdout(stdout),
                redirect_stderr(stderr),
            ):
                exit_code = _main(
                    [
                        "job quoting and invoicing",
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
                        "experience_story",
                        "--evidence-output",
                        str(evidence_path),
                    ]
                )

        self.assertEqual(exit_code, 1)
        self.assertEqual(stdout.getvalue(), "")
        self.assertIn(
            "Selector evidence input changed during selection", stderr.getvalue()
        )
        self.assertFalse(evidence_path.exists())

    def test_cli_rejects_output_and_temp_aliases_without_modifying_any_input(self):
        artifact_names = ("index", "ledger", "context_pack", "context_receipt")
        alias_modes = ("direct", "hardlink", "temp_hardlink")

        for artifact_name in artifact_names:
            for alias_mode in alias_modes:
                with self.subTest(artifact=artifact_name, alias_mode=alias_mode):
                    with TemporaryDirectory() as temp_dir:
                        root = Path(temp_dir)
                        index_path, ledger_path = write_selector_fixture(root)
                        pack_path, receipt_path = write_context_receipt_fixture(
                            root, index_path
                        )
                        artifacts = {
                            "index": index_path,
                            "ledger": ledger_path,
                            "context_pack": pack_path,
                            "context_receipt": receipt_path,
                        }
                        original_bytes = {
                            name: path.read_bytes() for name, path in artifacts.items()
                        }
                        target = artifacts[artifact_name]
                        if alias_mode == "direct":
                            evidence_path = target
                        else:
                            evidence_path = root / "selector-evidence.json"
                            alias_path = (
                                evidence_path
                                if alias_mode == "hardlink"
                                else evidence_path.with_name(f"{evidence_path.name}.tmp")
                            )
                            os.link(target, alias_path)

                        stdout = StringIO()
                        stderr = StringIO()
                        with redirect_stdout(stdout), redirect_stderr(stderr):
                            exit_code = _main(
                                [
                                    "job quoting and invoicing",
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
                                    "experience_story",
                                    "--evidence-output",
                                    str(evidence_path),
                                ]
                            )

                        self.assertEqual(exit_code, 1)
                        self.assertEqual(stdout.getvalue(), "")
                        self.assertIn(
                            "Selector evidence output aliases selector input",
                            stderr.getvalue(),
                        )
                        self.assertEqual(
                            {
                                name: path.read_bytes()
                                for name, path in artifacts.items()
                            },
                            original_bytes,
                        )
    def test_evidence_output_requires_slate_mode(self):
        with TemporaryDirectory() as temp_dir:
            evidence_path = Path(temp_dir) / "selector-evidence.json"
            stderr = StringIO()

            with self.assertRaises(SystemExit), redirect_stderr(stderr):
                _main(["topic", "--evidence-output", str(evidence_path)])

        self.assertIn("--evidence-output requires --slate", stderr.getvalue())

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
                                "workflow_fit": [
                                    "quoting",
                                    "invoicing",
                                    "field service",
                                ],
                                "themes": [
                                    "quote-to-cash",
                                    "small trade business",
                                    "invoice generation",
                                ],
                                "internal_source_ref": "References sheet 1tWlR0WNDRRnvA5b-2fdBdjC7rwaQQs1CYCc48pD62HE",
                                "public_url": "https://www.simprogroup.com/references/alarmquest",
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

    def test_single_recent_reuse_demotes_proof_below_strong_unused_alternative(self):
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
                                "proof_id": "quote-matrix-kiely-plumbing-estimates-invoicing",
                                "customer": "Kiely Plumbing",
                                "source_type": "quote_matrix",
                                "industry": ["plumbing"],
                                "workflow_fit": [
                                    "estimating",
                                    "invoicing",
                                    "scheduling",
                                    "admin reduction",
                                ],
                                "themes": [
                                    "estimate speed",
                                    "invoicing speed",
                                    "admin reduction",
                                ],
                                "public_url": "https://www.simprogroup.com/case-studies/kiely-plumbing",
                                "approval_status": "approved",
                                "public_copy_allowed": True,
                                "approved_metrics": [
                                    {
                                        "claim": "10x faster estimates",
                                        "status": "approved",
                                    }
                                ],
                            },
                            {
                                "proof_id": "quote-matrix-bop-plumbing-multibranch-invoicing",
                                "customer": "BOP Plumbing and Gas",
                                "source_type": "quote_matrix",
                                "industry": ["plumbing", "gas"],
                                "workflow_fit": [
                                    "invoicing",
                                    "scheduling",
                                    "job tracking",
                                    "mobile job data",
                                ],
                                "themes": [
                                    "invoice speed",
                                    "centralized operations",
                                    "mobile job closeout",
                                ],
                                "public_url": "https://www.simprogroup.com/case-studies/bop-plumbing-and-gas",
                                "approval_status": "approved",
                                "public_copy_allowed": True,
                                "approved_metrics": [
                                    {
                                        "claim": "invoices within 24 hours",
                                        "status": "approved",
                                    }
                                ],
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
                                "proof_id": "quote-matrix-kiely-plumbing-estimates-invoicing",
                                "customer": "Kiely Plumbing",
                                "source_url": "https://www.simprogroup.com/case-studies/kiely-plumbing",
                                "recent_uses_90d": 1,
                                "total_uses": 1,
                            }
                        ],
                        "uses": [],
                    }
                ),
                encoding="utf-8",
            )

            results = select_customer_proofs(
                "plumbing job sheet template",
                index_path=index_path,
                ledger_path=ledger_path,
                title="Free Plumbing Job Sheet Template",
                objective="help plumbing teams move from paper job sheets to connected mobile job data and invoicing",
                proof_role="metric",
                limit=2,
            )

        self.assertEqual(
            "quote-matrix-bop-plumbing-multibranch-invoicing", results[0]["proof_id"]
        )
        self.assertEqual(0, results[0]["recent_uses_90d"])
        self.assertEqual(
            "quote-matrix-kiely-plumbing-estimates-invoicing", results[1]["proof_id"]
        )
        self.assertEqual(1, results[1]["recent_uses_90d"])

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

        bge = next(
            result
            for result in results
            if result["proof_id"] == "case-study-bge-digital"
        )
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
                                "workflow_fit": [
                                    "quoting",
                                    "invoicing",
                                    "small trade business",
                                ],
                                "themes": [
                                    "quote-to-invoice workflow",
                                    "customer review story",
                                ],
                                "public_url": "https://www.simprogroup.com/case-studies/small-trade-case",
                                "approval_status": "approved",
                                "public_copy_allowed": True,
                                "evidence": "Approved Quote Matrix customer review story proof for quote-to-invoice workflows.",
                            },
                            {
                                "proof_id": "review-g2-small-trade-quote-invoice",
                                "customer": "G2 small trade review",
                                "source_type": "review_site",
                                "industry": ["electrical", "small business"],
                                "workflow_fit": [
                                    "quoting",
                                    "invoicing",
                                    "small trade business",
                                ],
                                "themes": [
                                    "quote-to-invoice workflow",
                                    "customer review story",
                                ],
                                "public_url": "https://www.g2.com/products/simpro/reviews/small-trade",
                                "approval_status": "approved",
                                "public_copy_allowed": True,
                                "evidence": "Referenceable G2 review story for quote-to-invoice workflows.",
                            },
                        ],
                    }
                ),
                encoding="utf-8",
            )
            ledger_path.write_text(
                json.dumps({"version": 1, "uses": []}), encoding="utf-8"
            )

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
                                "workflow_fit": [
                                    "quoting",
                                    "invoicing",
                                    "small trade business",
                                ],
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
                                "workflow_fit": [
                                    "quoting",
                                    "invoicing",
                                    "QBO",
                                    "small trade business",
                                ],
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
                                    "objective_fit": [
                                        "quote-to-cash",
                                        "small trade business",
                                    ],
                                    "copy_use": "paraphrased E-E-A-T story with same-paragraph source link",
                                    "verification_status": "brand-captured public review source",
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

            results = select_customer_proofs(
                "customer review story for quote and invoice workflow",
                index_path=index_path,
                ledger_path=ledger_path,
                limit=5,
                require_eeat_story=True,
            )

        self.assertEqual(
            [result["proof_id"] for result in results],
            ["review-capterra-megan-qbo-quotes"],
        )

    def test_require_eeat_story_blocks_inventory_with_only_missing_public_urls(self):
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
            ledger_path.write_text(
                json.dumps({"version": 1, "uses": []}), encoding="utf-8"
            )

            with self.assertRaisesRegex(
                RuntimeError,
                "no usable public customer proof inventory",
            ):
                select_customer_proofs(
                    "Google review story quote invoice",
                    index_path=index_path,
                    ledger_path=ledger_path,
                    limit=5,
                    require_eeat_story=True,
                )

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
                                "workflow_fit": [
                                    "service jobs",
                                    "recurring jobs",
                                    "quoting",
                                    "invoicing",
                                    "QBO",
                                ],
                                "themes": [
                                    "service jobs",
                                    "quotes",
                                    "invoices",
                                    "QuickBooks Online integration",
                                ],
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
                                    "objective_fit": [
                                        "quote-to-cash",
                                        "small trade business",
                                    ],
                                    "copy_use": "paraphrased theme or E-E-A-T story with same-paragraph source link",
                                    "verification_status": "brand-captured public review source",
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

            results = select_customer_proofs(
                "best job quoting and invoicing software",
                index_path=index_path,
                ledger_path=ledger_path,
                title="Best job quoting and invoicing software",
                objective="help field service buyers evaluate quote-to-cash tools with Capterra review themes",
                proof_role="theme",
                limit=2,
            )

        self.assertEqual(
            results[0]["proof_id"], "review-capterra-qbo-service-jobs-quotes-invoices"
        )
        self.assertEqual(results[0]["source_type"], "review_site")

    def test_cli_json_output_remains_default_without_slate_flag(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            index_path, ledger_path = write_selector_fixture(root)
            pack_path, receipt_path = write_context_receipt_fixture(root, index_path)
            buffer = StringIO()

            with redirect_stdout(buffer):
                exit_code = _main(
                    [
                        "best job quoting and invoicing software",
                        "--index",
                        str(index_path),
                        "--ledger",
                        str(ledger_path),
                        "--context-pack",
                        str(pack_path),
                        "--context-receipt",
                        str(receipt_path),
                        "--proof-role",
                        "metric",
                        "--limit",
                        "1",
                    ]
                )

            payload = json.loads(buffer.getvalue())

        self.assertEqual(exit_code, 0)
        self.assertEqual(payload["topic"], "best job quoting and invoicing software")
        self.assertEqual(
            payload["results"][0]["proof_id"],
            "quote-matrix-zebra-plumbing-onsite-quoting",
        )

    def test_cli_slate_output_emits_customer_proof_slate_for_roles(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            index_path, ledger_path = write_selector_fixture(root)
            pack_path, receipt_path = write_context_receipt_fixture(root, index_path)
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
                        "--context-pack",
                        str(pack_path),
                        "--context-receipt",
                        str(receipt_path),
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
            pack_path, receipt_path = write_context_receipt_fixture(root, index_path)
            buffer = StringIO()

            with redirect_stdout(buffer):
                exit_code = _main(
                    [
                        "best job quoting and invoicing software",
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
        self.assertIn(
            "Selected: [review-capterra-qbo-service-jobs-quotes-invoices]", output
        )
        self.assertIn(
            "Rejected stronger candidates: [quote-matrix-zebra-plumbing-onsite-quoting: metric proof fits a different section]",
            output,
        )

    def test_default_index_contains_only_public_web_url_proof_routes(self):
        index = json.loads(
            Path("context/customer-proof-index.json").read_text(encoding="utf-8")
        )
        deleted_internal_ids = {
            "quote-matrix-alarmquest-positive-feedback",
            "customer-stories-source-register",
            "references-source-register",
            "review-google-kingson-electrical-quote-to-invoice",
            "review-google-plumbing-material-labor-cost-field-story",
            "review-site-simpro-google-review-themes",
            "customer-story-all-round-security",
            "customer-story-roam",
            "customer-story-rilmac",
            "customer-story-fords",
            "customer-story-queenstown-plumbing",
            "customer-story-heron-plumbing-simprosium",
            "customer-story-obrien-electrical-plumbing-simprosium",
            "customer-story-second-nature-simprosium",
        }
        proof_by_id = {row["proof_id"]: row for row in index["proof"]}
        reference_ids = [
            row["proof_id"]
            for row in index["proof"]
            if row.get("source_type") == "reference"
        ]

        self.assertFalse(deleted_internal_ids.intersection(proof_by_id))
        self.assertGreaterEqual(len(reference_ids), 8)
        self.assertIn("reference-excel-refrigeration-hvac-operations", reference_ids)
        self.assertTrue(proof_by_id["case-study-alarmquest"]["public_copy_allowed"])
        self.assertTrue(
            proof_by_id["case-study-norberg-electric"]["public_copy_allowed"]
        )
        self.assertTrue(proof_by_id["review-site-simpro-g2"]["public_copy_allowed"])

    def test_default_index_ranks_topic_fit_reference_for_reference_intent(self):
        with TemporaryDirectory() as temp_dir:
            ledger_path = Path(temp_dir) / "customer-proof-usage-ledger.json"
            ledger_path.write_text(
                json.dumps({"version": 1, "uses": []}), encoding="utf-8"
            )

            results = select_customer_proofs(
                "hvac refrigeration reference field service operations",
                index_path=Path("context/customer-proof-index.json"),
                ledger_path=ledger_path,
                title="HVAC field service operations proof",
                objective="find a reference customer for HVAC refrigeration field service operations",
                proof_role="theme",
                limit=5,
            )

        self.assertEqual(
            "reference-excel-refrigeration-hvac-operations", results[0]["proof_id"]
        )
        self.assertEqual("reference", results[0]["source_type"])


if __name__ == "__main__":
    unittest.main()
