"""The bom_build CLI carries a fact forward only from the BOM the pipeline last wrote."""

from __future__ import annotations

import json

import pytest

from data_sources.modules.production import bom_build
from tests.production_bom_support import ARTICLE, FACT_PAGE, FACT_URL, TODAY, make_workspace, nonconnector_spec, write_json
from tests.production_release_support import PageTransport, workspace


@pytest.fixture(autouse=True)
def _environment(monkeypatch):
    monkeypatch.setenv("SEOMACHINE_TEST_CURRENT_UTC_DATE", TODAY)


@pytest.fixture
def cli(monkeypatch):
    """Run the CLI with the fact page answering ``status``."""
    def invoke(root, status=403):
        class Transport(PageTransport):
            def __init__(self):
                super().__init__({FACT_URL: (status, FACT_PAGE if status == 200 else "")})

            def __enter__(self):
                return self

            def __exit__(self, *exc):
                return False

        monkeypatch.setattr(bom_build, "PublicHttpTransport", Transport)
        return bom_build.main([ARTICLE, "--workspace-root", str(root)])

    return invoke


def _fact(path):
    return json.loads(path.read_text(encoding="utf-8"))["facts"][0]


def _set_paa(layout, question):
    spec = json.loads(layout.bom_spec.read_text(encoding="utf-8"))
    spec["paa_questions"][0]["question"] = question
    write_json(layout.bom_spec, spec)


def test_cli_rebuild_after_a_spec_fix_carries_an_unreachable_fact_forward(tmp_path, cli, capsys):
    layout = workspace(tmp_path)
    original = _fact(layout.bom)["verified_at"]
    good = json.loads(layout.bom_spec.read_text(encoding="utf-8"))["paa_questions"][0]["question"]
    _set_paa(layout, "Invented?")
    assert cli(tmp_path) == 1
    refused = layout.bom.with_name(layout.bom.name + ".refused")
    assert not layout.bom.exists() and refused.exists()
    _set_paa(layout, good)
    assert cli(tmp_path) == 0, capsys.readouterr().err
    fact = _fact(layout.bom)
    assert fact["carried_forward"] is True and fact["verified_at"] == original


def test_cli_rebuild_over_the_pipeline_bom_carries_an_unreachable_fact_forward(tmp_path, cli):
    layout = workspace(tmp_path)
    assert cli(tmp_path) == 0
    assert _fact(layout.bom)["carried_forward"] is True


def test_hand_edited_bom_is_not_carried_forward(tmp_path, cli, capsys):
    layout = workspace(tmp_path)
    bom = json.loads(layout.bom.read_text(encoding="utf-8"))
    bom["facts"][0]["check_detail"] = "edited by hand"
    write_json(layout.bom, bom)
    assert cli(tmp_path) == 1
    assert "f1" in capsys.readouterr().err


def test_hand_edited_refused_bom_is_not_carried_forward(tmp_path, cli):
    layout = workspace(tmp_path)
    refused = layout.bom.with_name(layout.bom.name + ".refused")
    bom = json.loads(layout.bom.read_text(encoding="utf-8"))
    bom["facts"][0]["check_detail"] = "edited by hand"
    write_json(refused, bom)
    layout.bom.unlink()
    assert cli(tmp_path) == 1


def test_first_build_without_a_prior_bom_refuses_an_unreachable_page(tmp_path, cli, capsys):
    layout = make_workspace(tmp_path, spec=nonconnector_spec())
    assert cli(tmp_path) == 1
    assert "unreachable" in capsys.readouterr().err and not layout.bom.exists()
