"""The layout CLI prints the article layout and mints the production run id."""

import json

import pytest

from data_sources.modules.production.layout import Layout, load_or_create_run_id, main

PATH_KEYS = {
    "article", "run_state", "bom", "bom_spec", "serp_evidence", "serp_coverage", "keyword_decision",
    "keyword_shortlist", "paa_artifact", "context_pack", "context_receipt", "customer_proof_evidence",
    "nonvault_customer_proof_evidence",
}


def _run(capsys, *argv):
    code = main([*argv])
    captured = capsys.readouterr()
    return code, captured.out, captured.err


def test_prints_identity_and_mints_a_persisted_run_id(tmp_path, capsys):
    code, out, err = _run(capsys, "drafts/fleet-tips-2026-10-14.md", "--workspace-root", str(tmp_path))
    assert (code, err) == (0, "")
    payload = json.loads(out)
    assert (payload["slug"], payload["date"], payload["workflow_mode"]) == ("fleet-tips", "2026-10-14", "new")
    layout = Layout.for_article("drafts/fleet-tips-2026-10-14.md", tmp_path)
    assert payload["run_id"] == load_or_create_run_id(layout)
    assert set(payload["paths"]) == PATH_KEYS
    assert payload["paths"]["run_state"] == "research/runs/fleet-tips-2026-10-14.json"
    assert payload["paths"]["paa_artifact"] == "research/paa-evidence-fleet-tips-2026-10-14.json"
    assert payload["paths"]["bom"] == "research/production-bom-fleet-tips-2026-10-14.json"


def test_reuses_the_stored_run_id(tmp_path, capsys):
    layout = Layout.for_article("rewrites/fleet-tips-2026-10-14.md", tmp_path)
    stored = load_or_create_run_id(layout, run_id="run-already-stored")
    code, out, _err = _run(capsys, "rewrites/fleet-tips-2026-10-14.md", "--workspace-root", str(tmp_path))
    payload = json.loads(out)
    assert code == 0
    assert payload["run_id"] == stored
    assert payload["workflow_mode"] == "rewrite"
    assert payload["paths"]["article"] == "rewrites/fleet-tips-2026-10-14.md"


def test_two_calls_print_the_same_run_id(tmp_path, capsys):
    article = "drafts/fleet-tips-2026-10-14.md"
    first = json.loads(_run(capsys, article, "--workspace-root", str(tmp_path))[1])
    second = json.loads(_run(capsys, article, "--workspace-root", str(tmp_path))[1])
    assert first["run_id"] == second["run_id"]


@pytest.mark.parametrize("article", ["notes/fleet-tips-2026-10-14.md", "drafts/Fleet_Tips.md", "drafts/x-2026-13-40.md"])
def test_bad_article_path_exits_2_without_writing_run_state(tmp_path, capsys, article):
    code, out, err = _run(capsys, article, "--workspace-root", str(tmp_path))
    assert code == 2
    assert out == ""
    assert err.startswith("layout: ")
    assert not (tmp_path / "research").exists()


def test_corrupt_run_state_exits_2(tmp_path, capsys):
    state = tmp_path / "research" / "runs" / "fleet-tips-2026-10-14.json"
    state.parent.mkdir(parents=True)
    state.write_text("{not json", encoding="utf-8")
    code, out, err = _run(capsys, "drafts/fleet-tips-2026-10-14.md", "--workspace-root", str(tmp_path))
    assert (code, out) == (2, "")
    assert "run state" in err
    assert state.read_text(encoding="utf-8") == "{not json"


def test_missing_article_argument_exits_2(capsys):
    assert main([]) == 2
