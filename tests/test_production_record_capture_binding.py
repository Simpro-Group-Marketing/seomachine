"""The release record binds each fact's Chrome capture receipt, so an edited receipt blocks publishing."""

from __future__ import annotations

import json

import pytest
from data_sources.modules.production import release
from data_sources.modules.production.record import bom_bindings, verify_publishable
from tests.production_bom_support import TODAY
from tests.production_capture_support import BLOCKED, CAPTURE_RECEIPT, build_blocked, capture_workspace
from tests.production_release_support import Checks, run


@pytest.fixture(autouse=True)
def _environment(monkeypatch):
    monkeypatch.setenv("SEOMACHINE_TEST_CURRENT_UTC_DATE", TODAY)
    monkeypatch.delenv(release.ENV_WORKERS, raising=False)


def test_bom_bindings_include_each_fact_capture(tmp_path):
    bom = build_blocked(capture_workspace(tmp_path))
    capture = bom["facts"][0]["capture"]
    assert bom_bindings(bom)["facts.f1.capture"] == {"path": capture["path"], "sha256": capture["sha256"]}


def test_edited_capture_receipt_after_a_passing_release_refuses_publishing(tmp_path, monkeypatch):
    layout = capture_workspace(tmp_path)
    build_blocked(layout)
    Checks(monkeypatch, real_truth=True)
    assert run(layout, transport=BLOCKED) == 0
    assert verify_publishable(layout.article, layout.root)["passed"] is True
    receipt = tmp_path / CAPTURE_RECEIPT
    payload = json.loads(receipt.read_text(encoding="utf-8"))
    payload["page_title"] = "Edited title"
    receipt.write_text(json.dumps(payload), encoding="utf-8", newline="\n")
    with pytest.raises(ValueError, match=r"source-captures.*changed since the passing release"):
        verify_publishable(layout.article, layout.root)
