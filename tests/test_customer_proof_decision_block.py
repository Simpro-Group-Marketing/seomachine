"""The selector can prefill a Customer Proof Selection Decision that matches its slate."""
from __future__ import annotations

from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from unittest.mock import patch

import pytest

from data_sources.modules.customer_proof.diversity_parsing import (
    _extract_customer_proof_slate,
    _extract_selection_decision,
    _parse_slate_roles,
    _selected_proof_ids,
    _slate_selected_ids,
)
from data_sources.modules.customer_proof.selector_cli import _main
from tests.test_customer_proof_selector import (
    write_context_receipt_fixture,
    write_selector_fixture,
)
from tests.vault_context_fixture import load_validated_claim_set_for_unit_test


@pytest.fixture(autouse=True)
def _validated_claims():
    with patch(
        "data_sources.modules.customer_proof.connector_inputs.load_validated_claim_set",
        new=load_validated_claim_set_for_unit_test,
    ):
        yield


def _run(tmp_path: Path, *extra: str) -> tuple[int, str]:
    index_path, ledger_path = write_selector_fixture(tmp_path)
    pack, receipt = write_context_receipt_fixture(tmp_path, index_path)
    out = StringIO()
    with redirect_stdout(out):
        code = _main(
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
                str(pack),
                "--context-receipt",
                str(receipt),
                "--slate",
                "--roles",
                "metric,quote,theme,experience_story",
                "--require-eeat-story",
                "--evidence-output",
                str(tmp_path / "evidence.json"),
                *extra,
            ]
        )
    return code, out.getvalue()


def test_decision_block_selected_proof_is_in_slate(tmp_path: Path) -> None:
    code, text = _run(tmp_path, "--decision-block")
    assert code == 0
    selected = _selected_proof_ids(_extract_selection_decision(text))
    slate_ids = _slate_selected_ids(_parse_slate_roles(_extract_customer_proof_slate(text)))
    assert selected and set(selected) <= slate_ids
    assert "- Selected proof: quote-matrix-bwe-engineering-job-to-invoice | Customer: " in text
    assert "- Selector command: python data_sources/modules/customer_proof_selector.py" in text


def test_decision_block_is_opt_in(tmp_path: Path) -> None:
    code, text = _run(tmp_path)
    assert code == 0
    assert "## Customer Proof Selection Decision" not in text


def test_decision_block_requires_slate(tmp_path: Path) -> None:
    with pytest.raises(SystemExit):
        _main(["topic", "--decision-block"])
