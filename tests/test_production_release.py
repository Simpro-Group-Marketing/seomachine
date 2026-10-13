"""Tests for the one-pass release command: refresh, rebuild, check, score, record."""

from __future__ import annotations

import copy
import inspect
import json
import threading
from datetime import date
from unittest.mock import patch

import pytest
from data_sources.modules.blog_assembly_contract import atomic_write_json
from data_sources.modules.customer_proof.connector_evidence import verify_connector_selector_evidence
from data_sources.modules.customer_proof.contracts import CustomerProofDataError
from data_sources.modules.customer_proof.nonconnector_persistence import write_nonvault_selector_evidence
from data_sources.modules.customer_proof.selector_cli import _main as connector_selector_main
from data_sources.modules.production import bom_build, release, selector_refresh
from data_sources.modules.production.bom_selector import bind_selector_evidence
from data_sources.modules.production.layout import Layout
from data_sources.modules.production.record import file_sha256, latest_record, verify_publishable
from data_sources.modules.production.scoring import ScoringPreflightError, score_gates
from data_sources.modules.production.truth_text import Finding
from tests import production_scoring_support as scoring_fixture
from tests.production_bom_support import (
    ARTICLE,
    NONVAULT_ID,
    TODAY,
    good_transport,
    make_workspace,
    nonconnector_spec,
    response,
    write_json,
)
from tests.production_scoring_support import make_scoring_workspace, scorer_result
from tests.test_customer_proof_selector import proof_claims, write_ledger
from tests.vault_context_fixture import load_validated_claim_set_for_unit_test, write_connector_context_fixture

ARTICLE_TEXT = "# Crew Time Tracking Guide\n\nCrews log time from any phone.\n"
VAULT_PATCH = "data_sources.modules.customer_proof.connector_inputs.load_validated_claim_set"


@pytest.fixture(autouse=True)
def _environment(monkeypatch):
    monkeypatch.setenv("SEOMACHINE_TEST_CURRENT_UTC_DATE", TODAY)
    monkeypatch.delenv(release.ENV_WORKERS, raising=False)


def _workspace(root):
    """A nonconnector workspace with an article and a BOM built from its spec."""
    layout = make_workspace(root, spec=nonconnector_spec())
    layout.article.parent.mkdir(parents=True, exist_ok=True)
    layout.article.write_text(ARTICLE_TEXT, encoding="utf-8", newline="\n")
    atomic_write_json(layout.bom, bom_build.build_bom(layout, transport=good_transport()))
    return layout


class Checks:
    """Stand-ins for truth, coverage, and scoring that record how they were called."""

    def __init__(self, monkeypatch):
        self.calls: list[tuple] = []
        self.truth_findings: list[Finding] = []
        self.coverage_findings: list[Finding] = []
        self.scores = score_gates(scorer_result())
        self.on_score = None
        self.on_truth = None
        monkeypatch.setattr(release, "check_truth", self.truth)
        monkeypatch.setattr(release, "check_coverage", self.coverage)
        monkeypatch.setattr(release, "score_article", self.score)

    def truth(self, article, bom, *, transport):
        self.calls.append(("truth", transport))
        if self.on_truth:
            self.on_truth()
        return list(self.truth_findings)

    def coverage(self, article, bom):
        self.calls.append(("coverage",))
        return list(self.coverage_findings)

    def score(self, article_path, bom, *, workers):
        self.calls.append(("score", workers))
        if self.on_score:
            self.on_score(article_path)
        return copy.deepcopy(self.scores)


@pytest.fixture
def checks(monkeypatch):
    return Checks(monkeypatch)


@pytest.fixture
def layout(tmp_path):
    return _workspace(tmp_path)


def _noop_refresher(layout, bom):
    return None


def _run(layout, *, workers=2, refresher=_noop_refresher, transport=None, **kwargs):
    return release.run_release(
        ARTICLE, layout.root, workers=workers, transport=transport or good_transport(),
        refresher=refresher, **kwargs,
    )


def _release_dirs(layout):
    folder = layout.root / "research" / "releases"
    return sorted(folder.iterdir()) if folder.is_dir() else []


# ---- pass and block ------------------------------------------------------------------


def test_passing_release_writes_one_record_and_exits_zero(layout, checks, capsys):
    assert _run(layout) == 0
    assert len(_release_dirs(layout)) == 1
    record = latest_record(layout)
    assert record["passed"] is True and record["blocks"] == 0
    assert record["article"]["sha256"] == file_sha256(layout.article)
    assert record["bom"]["sha256"] == file_sha256(layout.bom)
    assert verify_publishable(layout.article, layout.root)["run_id"] == record["run_id"]
    out = capsys.readouterr().out
    assert "content 95.0 (min 85)" in out and "seo 95.0 (min 90" in out and "aeo_geo 95.0 (min 90)" in out


def test_block_findings_exit_one_and_print_each_block_and_the_scores(layout, checks, capsys):
    checks.truth_findings = [Finding("fact_quote", "block", "fact f1 gone", None), Finding("lint", "warn", "w", 3)]
    checks.coverage_findings = [Finding("coverage_section", "block", "section missing", 7)]
    assert _run(layout) == 1
    out = capsys.readouterr().out
    blocks = [line for line in out.splitlines() if "BLOCK " in line]
    assert len(blocks) == 2 and "fact f1 gone" in blocks[0] and "section missing" in blocks[1]
    assert "content 95.0 (min 85)" in out and "aeo_geo 95.0 (min 90)" in out
    record = latest_record(layout)
    assert (record["blocks"], record["warns"], record["passed"]) == (2, 1, False)


def test_failed_scores_exit_one(layout, checks, capsys):
    checks.scores = score_gates(scorer_result(seo=70))
    assert _run(layout) == 1
    assert "seo 70.0 (min 90" in capsys.readouterr().out
    assert latest_record(layout)["passed"] is False


def test_release_rebuilds_the_bom_from_the_spec(layout, checks):
    layout.bom.write_text("{}", encoding="utf-8")
    assert _run(layout) == 0
    rebuilt = json.loads(layout.bom.read_text(encoding="utf-8"))
    assert rebuilt["schema"] == "simpro-production-bom/v1"
    assert latest_record(layout)["bom"]["sha256"] == file_sha256(layout.bom)


# ---- concurrency and workers ---------------------------------------------------------


def test_truth_coverage_and_scoring_share_one_thread_pool(layout, checks, monkeypatch):
    sizes = []

    class Pool(release.ThreadPoolExecutor):
        def __init__(self, max_workers):
            sizes.append(max_workers)
            super().__init__(max_workers=max_workers)

    monkeypatch.setattr(release, "ThreadPoolExecutor", Pool)
    barrier = threading.Barrier(2, timeout=10)
    checks.on_score = lambda _path: barrier.wait()
    checks.on_truth = barrier.wait
    assert _run(layout, workers=2) == 0
    assert sizes == [2]
    assert ("score", 2) in checks.calls and ("coverage",) in checks.calls


def test_one_worker_runs_without_pools(layout, checks, monkeypatch):
    def no_pool(*_args, **_kwargs):
        raise AssertionError("workers=1 must not start a pool")

    monkeypatch.setattr(release, "ThreadPoolExecutor", no_pool)
    assert _run(layout, workers=1) == 0
    assert ("score", 1) in checks.calls
    assert latest_record(layout)["workers"] == 1


def _cli(monkeypatch, layout, *extra):
    class FakePublicTransport:
        instances: list = []

        def __init__(self):
            self.inner = good_transport()
            FakePublicTransport.instances.append(self)

        def request_many(self, *args, **kwargs):
            return self.inner.request_many(*args, **kwargs)

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

    monkeypatch.setattr(release, "PublicHttpTransport", FakePublicTransport)
    monkeypatch.setattr(release, "refresh_selector_evidence", _noop_refresher)
    code = release.main([ARTICLE, "--workspace-root", str(layout.root), *extra])
    return code, FakePublicTransport.instances


def test_env_var_sets_the_default_worker_count(layout, checks, monkeypatch):
    monkeypatch.setenv(release.ENV_WORKERS, "3")
    assert _cli(monkeypatch, layout)[0] == 0
    assert latest_record(layout)["workers"] == 3 and ("score", 3) in checks.calls


def test_default_worker_count_is_two(layout, checks, monkeypatch):
    assert _cli(monkeypatch, layout)[0] == 0
    assert latest_record(layout)["workers"] == 2


def test_workers_flag_overrides_the_env_var(layout, checks, monkeypatch):
    monkeypatch.setenv(release.ENV_WORKERS, "3")
    assert _cli(monkeypatch, layout, "--workers", "1")[0] == 0
    assert latest_record(layout)["workers"] == 1


@pytest.mark.parametrize("value", ["zero", "0", "-2"])
def test_invalid_worker_count_exits_two(layout, checks, monkeypatch, value):
    monkeypatch.setenv(release.ENV_WORKERS, value)
    assert _cli(monkeypatch, layout)[0] == 2
    assert _release_dirs(layout) == []


def test_cli_shares_one_public_transport_across_rebuild_and_truth(layout, checks, monkeypatch):
    code, instances = _cli(monkeypatch, layout)
    assert code == 0 and len(instances) == 1
    assert [call[1] for call in checks.calls if call[0] == "truth"] == [instances[0]]


# ---- refresh and rebuild -------------------------------------------------------------


def test_refresher_runs_before_the_rebuild(layout, checks, monkeypatch):
    order = []
    real_build = release.build_bom

    def build(*args, **kwargs):
        order.append("build")
        return real_build(*args, **kwargs)

    monkeypatch.setattr(release, "build_bom", build)
    assert _run(layout, refresher=lambda _layout, bom: order.append(("refresh", bom["proof"][0]["claim_id"]))) == 0
    assert order == [("refresh", NONVAULT_ID), "build"]


def test_refresh_is_skipped_when_the_bom_has_no_proof_and_no_evidence(layout, checks):
    bom = json.loads(layout.bom.read_text(encoding="utf-8"))
    bom["proof"] = []
    del bom["customer_proof"]
    write_json(layout.bom, bom)
    calls = []
    assert _run(layout, refresher=lambda *args: calls.append(args)) == 0
    assert calls == []


def _reselect_nothing(layout, bom):
    """A refresh whose selector now selects nothing for any role."""
    evidence = json.loads(layout.nonvault_customer_proof_evidence.read_text(encoding="utf-8"))
    inputs = evidence["inputs"]
    write_nonvault_selector_evidence(
        layout.nonvault_customer_proof_evidence, topic=inputs["topic"], brand=inputs["brand"],
        title=inputs["title"], objective=inputs["objective"], article_slug=inputs["article_slug"],
        roles=inputs["roles"], require_eeat_story=True, limit=inputs["limit"],
        reference_date=date.fromisoformat(TODAY), selected_overrides={}, rejected_overrides={},
        index_path=evidence["artifacts"]["index"]["path"], ledger_path=evidence["artifacts"]["ledger"]["path"],
    )


def test_refresh_that_changes_the_selection_refuses_the_rebuild_with_exit_one(layout, checks, capsys):
    assert _run(layout, refresher=_reselect_nothing) == 1
    err = capsys.readouterr().err
    assert NONVAULT_ID in err and "not a selected candidate" in err
    assert not layout.bom.exists() and layout.bom.with_name(layout.bom.name + ".refused").exists()
    assert _release_dirs(layout) == [] and checks.calls == []


def test_refused_rebuild_names_every_reason(layout, checks, capsys):
    spec = json.loads(layout.bom_spec.read_text(encoding="utf-8"))
    spec["proof"][0]["claim_id"] = "claim-nope"
    spec["paa_questions"][0]["question"] = "Invented?"
    write_json(layout.bom_spec, spec)
    assert _run(layout) == 1
    err = capsys.readouterr().err
    assert "claim-nope" in err and "Invented?" in err
    assert layout.bom.with_name(layout.bom.name + ".refused").exists()


def test_refresh_failure_such_as_a_vault_outage_exits_two(layout, checks, capsys):
    before = layout.bom.read_bytes()

    def outage(_layout, _bom):
        raise CustomerProofDataError("Customer proof context receipt is invalid: live connector could not validate")

    assert _run(layout, refresher=outage) == 2
    assert "live connector could not validate" in capsys.readouterr().err
    assert layout.bom.read_bytes() == before and _release_dirs(layout) == []


def test_scoring_preflight_error_exits_two(layout, checks, capsys):
    def stale(_path):
        raise ScoringPreflightError("connector selector evidence is stale; re-run")

    checks.on_score = stale
    assert _run(layout) == 2
    assert "stale" in capsys.readouterr().err and _release_dirs(layout) == []


def test_unexpected_exception_exits_two_without_a_traceback(layout, checks, capsys):
    def boom():
        raise RuntimeError("socket exploded")

    checks.on_truth = boom
    assert _run(layout) == 2
    err = capsys.readouterr().err
    assert "socket exploded" in err and "Traceback" not in err


# ---- article integrity -----------------------------------------------------------------


def test_article_edited_mid_run_exits_two_and_records_nothing(layout, checks, capsys):
    checks.on_score = lambda path: path.write_text(ARTICLE_TEXT + "\nEdited.\n", encoding="utf-8")
    assert _run(layout) == 2
    assert "article changed during release" in capsys.readouterr().err
    assert _release_dirs(layout) == []


# ---- ledger ----------------------------------------------------------------------------


def test_release_never_writes_the_usage_ledger_pass_or_fail(layout, checks):
    assert "ledger_writer" not in inspect.signature(release.run_release).parameters
    ledger = layout.root / "config" / "customer-proof-usage-ledger.json"
    before = ledger.read_bytes()
    refresh = selector_refresh.refresh_selector_evidence
    assert _run(layout, refresher=refresh) == 0
    checks.truth_findings = [Finding("fact_quote", "block", "gone", None)]
    assert _run(layout, refresher=refresh) == 1
    assert ledger.read_bytes() == before and len(_release_dirs(layout)) == 2


# ---- missing inputs ------------------------------------------------------------------------


def test_missing_bom_spec_exits_two_with_the_expected_path(layout, checks, capsys):
    layout.bom_spec.unlink()
    assert _run(layout) == 2
    assert str(layout.bom_spec) in capsys.readouterr().err
    assert layout.bom.exists() and _release_dirs(layout) == []


def test_missing_bom_exits_two_with_the_expected_path_and_the_build_command(layout, checks, capsys):
    layout.bom.unlink()
    assert _run(layout) == 2
    err = capsys.readouterr().err
    assert str(layout.bom) in err and "refused" not in err
    assert f"python -m data_sources.modules.production.bom_build {ARTICLE}" in err


def test_bom_refused_at_the_last_build_gets_an_actionable_message(layout, checks, capsys):
    refused = layout.bom.with_name(layout.bom.name + ".refused")
    layout.bom.replace(refused)
    assert _run(layout) == 2
    err = capsys.readouterr().err
    assert f"production BOM was refused at the last build ({refused})" in err
    assert "fix the BOM spec or research inputs" in err
    assert f"python -m data_sources.modules.production.bom_build {ARTICLE}" in err


def test_missing_article_exits_two(layout, checks, capsys):
    layout.article.unlink()
    assert _run(layout) == 2
    assert str(layout.article) in capsys.readouterr().err


def test_layout_error_exits_two(tmp_path, checks, capsys):
    assert release.run_release("notes/elsewhere.md", tmp_path, workers=1, refresher=_noop_refresher) == 2
    assert "drafts" in capsys.readouterr().err


# ---- default refresher -------------------------------------------------------------------


def _stale(path, *, reference_date="2026-01-02"):
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["inputs"]["reference_date"] = reference_date
    path.write_text(json.dumps(payload), encoding="utf-8")
    return payload


def test_default_refresher_reruns_the_nonvault_selector_with_its_recorded_inputs(layout):
    path = layout.nonvault_customer_proof_evidence
    before = _stale(path)
    bom = json.loads(layout.bom.read_text(encoding="utf-8"))
    assert selector_refresh.refresh_selector_evidence(layout, bom) == path
    after = json.loads(path.read_text(encoding="utf-8"))
    assert after["inputs"]["reference_date"] == date.today().isoformat()
    assert {k: v for k, v in after["inputs"].items() if k != "reference_date"} == {
        k: v for k, v in before["inputs"].items() if k != "reference_date"}
    assert after["roles"] == before["roles"]
    bind_selector_evidence(layout, bom["proof"], True)


def test_default_refresher_reruns_the_connector_selector_with_its_recorded_inputs(tmp_path):
    layout = Layout.for_article(ARTICLE, tmp_path)
    for folder in ("config", "research"):
        (tmp_path / folder).mkdir()
    ledger = write_ledger(tmp_path / "config")
    pack, receipt = write_connector_context_fixture(tmp_path / "research", proof_claims())
    output = layout.customer_proof_evidence
    with patch(VAULT_PATCH, new=load_validated_claim_set_for_unit_test):
        assert connector_selector_main([
            "quoting invoicing review story", "--ledger", str(ledger), "--context-pack", str(pack),
            "--context-receipt", str(receipt), "--article-slug", layout.slug, "--slate",
            "--roles", "metric,quote,theme,experience_story", "--require-eeat-story",
            "--selected", "metric=claim-zebra-metric", "--evidence-output", str(output),
        ]) == 0
        before = _stale(output)
        bom = {"proof": [{"claim_id": "claim-zebra-metric"}],
               "customer_proof": {"evidence": {"path": output.relative_to(tmp_path).as_posix(), "sha256": "0" * 64}}}
        assert selector_refresh.refresh_selector_evidence(layout, bom) == output
        after = json.loads(output.read_text(encoding="utf-8"))
        assert verify_connector_selector_evidence(after) is not None
    assert after["inputs"]["reference_date"] == date.today().isoformat()
    assert after["inputs"]["selected_overrides"] == {"metric": "claim-zebra-metric"}
    assert after["roles"] == before["roles"] and after["artifacts"] == before["artifacts"]


def test_default_refresher_rejects_unknown_evidence(layout):
    write_json(layout.nonvault_customer_proof_evidence, {"schema": "something-else/v9"})
    bom = json.loads(layout.bom.read_text(encoding="utf-8"))
    with pytest.raises(ValueError, match="something-else/v9"):
        selector_refresh.refresh_selector_evidence(layout, bom)


# ---- end to end with real scoring ------------------------------------------------------------


class AnyPage:
    """Every URL answers 200 with a page carrying the fixture fact quote."""

    page = "<html><body><p>BigChange field service management software for teams.</p></body></html>"

    def request_many(self, method, urls, **kwargs):
        return [response(url, 200, self.page) for url in urls]

    def request(self, method, url, **kwargs):
        return response(url, 200, self.page)


def test_end_to_end_release_with_real_scoring_on_the_nonconnector_fixture(tmp_path, monkeypatch):
    monkeypatch.setenv("SEOMACHINE_TEST_CURRENT_UTC_DATE", scoring_fixture.TODAY)
    article, bom = make_scoring_workspace(tmp_path)
    article.write_text(
        article.read_text(encoding="utf-8").replace("title: Scheduling guide\n", "title: Field Service Scheduling Guide\n", 1),
        encoding="utf-8", newline="\n",
    )
    layout = Layout.for_article(article, tmp_path)
    write_json(layout.bom_spec, {"spec": "stand-in; the builder below binds the fixture BOM"})
    write_json(layout.bom, bom)

    def build(build_layout, *, transport, claim_loader):
        rebuilt = copy.deepcopy(bom)
        rebuilt["customer_proof"] = bind_selector_evidence(build_layout, rebuilt["proof"], True)
        return rebuilt

    monkeypatch.setattr(release, "build_bom", build)
    code = release.run_release(article, tmp_path, workers=2, transport=AnyPage())
    record = latest_record(layout)
    assert code == 0, record
    assert record["scores"]["passed"] is True and record["blocks"] == 0
    assert record["scores"]["aeo_geo"] >= 90 and record["scores"]["seo_critical"] == 0
    evidence = json.loads(layout.nonvault_customer_proof_evidence.read_text(encoding="utf-8"))
    assert evidence["inputs"]["reference_date"] == date.today().isoformat()
    assert record["evidence"]["customer_proof.evidence"]["sha256"] == file_sha256(layout.nonvault_customer_proof_evidence)
    assert verify_publishable(article, tmp_path)["passed"] is True
