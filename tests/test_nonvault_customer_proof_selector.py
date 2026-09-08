import hashlib
import json
from contextlib import redirect_stderr, redirect_stdout
from datetime import date
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory

from data_sources.modules.customer_proof_evidence import verify_selector_evidence_roles
from data_sources.modules.nonvault_customer_proof_selector import (
    _main,
    select_nonvault_customer_proofs,
)
from tests.nonvault_proof_fixture import write_nonvault_proof_inputs


def test_selector_keeps_clockshark_customer_stories_and_excludes_reviews_and_cross_brand_rows():
    with TemporaryDirectory() as temp_dir:
        root = Path(temp_dir)
        index_path, ledger_path = write_nonvault_proof_inputs(root)

        results = select_nonvault_customer_proofs(
            "employee time theft buddy punching",
            brand="ClockShark",
            index_path=index_path,
            ledger_path=ledger_path,
            title="Employee Time Theft: Examples, Warning Signs, and Prevention",
            objective="Prevent inaccurate field time records fairly.",
            proof_role="experience_story",
            require_eeat_story=True,
            limit=10,
            reference_date=date(2026, 8, 28),
        )

    assert [row["proof_id"] for row in results] == [
        "clockshark-customer-story-mabrys-electrical-service",
        "clockshark-customer-story-bear-down-builders",
    ]


def test_selector_returns_no_metric_or_quote_candidates_without_approved_rows():
    with TemporaryDirectory() as temp_dir:
        root = Path(temp_dir)
        index_path, ledger_path = write_nonvault_proof_inputs(root)

        metric = select_nonvault_customer_proofs(
            "employee time theft",
            brand="ClockShark",
            index_path=index_path,
            ledger_path=ledger_path,
            proof_role="metric",
            reference_date=date(2026, 8, 28),
        )
        quote = select_nonvault_customer_proofs(
            "employee time theft",
            brand="ClockShark",
            index_path=index_path,
            ledger_path=ledger_path,
            proof_role="quote",
            reference_date=date(2026, 8, 28),
        )

    assert metric == []
    assert quote == []


def test_selector_counts_recent_ledger_uses_from_canonical_date_used_field():
    with TemporaryDirectory() as temp_dir:
        root = Path(temp_dir)
        index_path, ledger_path = write_nonvault_proof_inputs(root)
        ledger_path.write_text(
            json.dumps(
                {
                    "version": 1,
                    "uses": [
                        {
                            "proof_id": "clockshark-customer-story-mabrys-electrical-service",
                            "date_used": "2026-08-28",
                        }
                    ],
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )

        results = select_nonvault_customer_proofs(
            "employee time theft buddy punching",
            brand="ClockShark",
            index_path=index_path,
            ledger_path=ledger_path,
            proof_role="experience_story",
            require_eeat_story=True,
            limit=10,
            reference_date=date(2026, 8, 28),
        )

    mabry = next(
        row
        for row in results
        if row["proof_id"] == "clockshark-customer-story-mabrys-electrical-service"
    )
    assert mabry["recent_uses_90d"] == 1


def test_cli_writes_hash_bound_nonvault_evidence_and_verifier_replays_roles():
    with TemporaryDirectory() as temp_dir:
        root = Path(temp_dir)
        index_path, ledger_path = write_nonvault_proof_inputs(root)
        evidence_path = root / "nonvault-evidence.json"
        sidecar_path = root / "validation.md"
        stdout = StringIO()
        stderr = StringIO()
        args = [
            "employee time theft",
            "--brand",
            "ClockShark",
            "--title",
            "Employee Time Theft: Examples, Warning Signs, and Prevention",
            "--objective",
            "Prevent inaccurate field time records fairly.",
            "--article-slug",
            "employee-time-theft",
            "--index",
            str(index_path),
            "--ledger",
            str(ledger_path),
            "--roles",
            "metric,quote,theme,experience_story",
            "--require-eeat-story",
            "--selected",
            "theme=clockshark-customer-story-mabrys-electrical-service",
            "--selected",
            "experience_story=clockshark-customer-story-mabrys-electrical-service",
            "--rejected",
            (
                "experience_story=clockshark-customer-story-bear-down-builders:"
                "Mabry directly supports buddy punching in the selected section"
            ),
            "--limit",
            "10",
            "--reference-date",
            "2026-08-28",
            "--slate",
            "--evidence-output",
            str(evidence_path),
        ]

        with redirect_stdout(stdout), redirect_stderr(stderr):
            exit_code = _main(args)

        payload = json.loads(evidence_path.read_text(encoding="utf-8"))
        digest = hashlib.sha256(evidence_path.read_bytes()).hexdigest()
        sidecar_path.write_text(
            "Customer Proof Slate\n"
            + stdout.getvalue().split("Customer Proof Slate\n", 1)[1]
            + f"\n- Selector evidence: {evidence_path} | SHA-256: {digest}\n",
            encoding="utf-8",
        )
        sidecar_content = sidecar_path.read_text(encoding="utf-8")
        verified = verify_selector_evidence_roles(sidecar_content, str(sidecar_path))

    assert exit_code == 0
    assert stderr.getvalue() == ""
    assert payload["schema"] == "simpro-nonvault-customer-proof-selector-evidence/v1"
    assert payload["inputs"]["brand"] == "ClockShark"
    assert set(payload["artifacts"]) == {"index", "ledger"}
    assert verified is not None
    assert verified["metric"]["selected_id"] == "none"
    assert verified["quote"]["selected_id"] == "none"
    assert verified["theme"]["selected_id"] == "clockshark-customer-story-mabrys-electrical-service"
    assert verified["experience_story"]["selected_candidate"]["identity"] == "Mabry's Electrical Service"
