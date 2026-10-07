"""The release sweep reports every blocker in one pass."""
from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from data_sources.modules import blog_release_sweep
from data_sources.modules.release_workflow import precheck_sweep


def test_sweep_records_crash_and_continues() -> None:
    def boom():
        raise RuntimeError("guard exploded")

    rows = precheck_sweep.run_check("broken", boom) + precheck_sweep.run_check(
        "ok", lambda: [{"rule_id": "r1", "severity": "error", "message": "m"}]
    )
    assert [(r["check"], r["rule_id"]) for r in rows] == [
        ("broken", "sweep_check_crashed"), ("ok", "r1"),
    ]
    assert "guard exploded" in rows[0]["message"]


def test_article_gates_receive_only_supported_kwargs() -> None:
    seen = {}

    def check_file(path, proof_sidecar=None, fail_on="error"):
        seen.update(path=path, proof_sidecar=proof_sidecar, fail_on=fail_on)
        return [{"rule_id": "x", "severity": "error", "message": "bad", "line": 3}]

    gates = (("demo_gate", "Demo", SimpleNamespace(check_file=check_file)),)
    rows = precheck_sweep.sweep_article_gates(
        gates, article="a.md",
        kwargs={"proof_sidecar": "s.md", "fail_on": "error", "context_pack": "p.json"},
        skip={},
    )
    assert seen == {"path": "a.md", "proof_sidecar": "s.md", "fail_on": "error"}
    assert rows[0]["check"] == "demo_gate" and rows[0]["line"] == 3


def test_skipped_gates_are_reported_not_run() -> None:
    called = []
    gates = (("url_validator", "URL", SimpleNamespace(check_file=lambda path: called.append(path) or [])),)
    rows = precheck_sweep.sweep_article_gates(
        gates, article="a.md", kwargs={}, skip={"url_validator": "offline"}
    )
    assert called == [] and rows == []


def test_scorer_findings_turn_failed_checks_into_errors() -> None:
    result = {"aeo_geo": {"checks": {
        "capsule_coverage": {"passed": False, "issue": "First paragraph must contain 50-60 words."},
        "schema": {"passed": True},
    }}}
    rows = precheck_sweep.scorer_findings(result)
    assert [r["rule_id"] for r in rows] == ["aeo_geo.capsule_coverage"]
    assert rows[0]["severity"] == "error"


def test_gate_without_file_entry_point_is_skipped_not_crashed() -> None:
    gates = (("content_only", "Content only", SimpleNamespace()),)
    rows = precheck_sweep.sweep_article_gates(gates, article="a.md", kwargs={}, skip={})
    assert rows == []


def test_per_gate_kwargs_provider_overrides_flat_kwargs() -> None:
    seen = {}

    def check_file(path, editorial_plan=None):
        seen["editorial_plan"] = editorial_plan
        return []

    gates = (("eeat_strength", "E-E-A-T", SimpleNamespace(check_file=check_file)),)
    precheck_sweep.sweep_article_gates(
        gates, article="a.md", kwargs={}, skip={},
        kwargs_for=lambda name: {"editorial_plan": "plan.json"},
    )
    assert seen == {"editorial_plan": "plan.json"}


def _args(**overrides):
    base = dict(
        article="a.md", proof_sidecar="s.md", context_request=None, context_pack=None,
        context_receipt=None, editorial_plan="plan.json", keyword_decision="k.json",
        serp_evidence="se.json", commercial_pillar_index="idx.json", assembly_date="2026-10-07",
        run_id="run-1", workflow_mode="new", paa_artifact="paa.json", content_brief=None,
        answersocrates_blocker=None, customer_proof_evidence="cp.json",
        fred_authority_evidence=None,
    )
    base.update(overrides)
    return SimpleNamespace(**base)


def test_runtime_policy_mirrors_the_release_runner_shape(tmp_path) -> None:
    policy = precheck_sweep._runtime_policy(_args(), article_text=None)
    assert policy["editorial_plan"] == "plan.json"
    assert policy["customer_proof_selector_evidence"] == "cp.json"
    assert policy["current_strategy"] is True and policy["visible_faq"] is True
    assert policy["paa_kwargs"]["workflow_mode"] == "new"
    assert policy["paa_kwargs"]["paa_artifact"] == "paa.json"
    assert policy["paa_kwargs"]["expected_run_id"] == "run-1"
    assert policy["paa_kwargs"]["expected_collection_date"] == "2026-10-07"


def test_runtime_policy_tolerates_missing_arguments() -> None:
    policy = precheck_sweep._runtime_policy(SimpleNamespace(article="a.md"), article_text=None)
    assert policy["editorial_plan"] is None and policy["paa_kwargs"]["paa_artifact"] is None


def test_report_collects_every_check_in_one_pass(monkeypatch, tmp_path) -> None:
    names = ["_pre_bom_rows", "_plan_rows", "_keyword_rows", "_faq_binding_rows", "_scorer_rows"]
    for name in names:
        monkeypatch.setattr(
            precheck_sweep, name,
            lambda *a, _n=name, **k: [{"rule_id": _n, "severity": "error", "message": _n}],
        )
    gate = SimpleNamespace(check_file=lambda path: [{"rule_id": "gate_rule", "severity": "error", "message": "g"}])
    monkeypatch.setattr(precheck_sweep, "ARTICLE_GATES", (("demo_gate", "Demo", gate),))
    args = SimpleNamespace(article="a.md", proof_sidecar="s.md", context_request=None,
                           context_pack=None, context_receipt=None)
    report = precheck_sweep.run_release_sweep(args, workspace_root=tmp_path, offline=True, include_slow=False)
    rules = {row["rule_id"] for row in report["findings"]}
    assert rules == set(names) | {"gate_rule"}
    assert report["passed"] is False and report["schema"] == precheck_sweep.SWEEP_SCHEMA


ROW_FUNCTIONS = (
    "_pre_bom_rows", "_plan_rows", "_keyword_rows", "_faq_binding_rows", "_scorer_rows",
    "_strategy_rows", "_source_quality_rows", "_public_artifact_rows", "_ai_copy_rows",
    "_url_validator_rows", "_research_link_rows", "_context_binding_rows", "_no_fit_rows",
)


def _stub_dedicated_checks(monkeypatch) -> None:
    for name in ROW_FUNCTIONS:
        monkeypatch.setattr(precheck_sweep, name, lambda *a, **k: [])


def _marker_gates():
    ran = []
    gates = tuple(
        (name, name, SimpleNamespace(check_file=lambda path, _n=name: ran.append(_n) or []))
        for name in (
            "source_support", "customer_proof_diversity", "fred_authority",
            "paa_provenance", "editorial_plan", "metric_proof_pack",
        )
    )
    return gates, ran


@pytest.mark.parametrize("offline, include_slow, expected_ran, expected_skipped", [
    (True, False, {"metric_proof_pack"},
     {"source_support", "customer_proof_diversity", "fred_authority", "paa_provenance"}),
    (False, True, {"source_support", "customer_proof_diversity", "fred_authority", "metric_proof_pack"},
     {"paa_provenance"}),
])
def test_skip_maps_cover_offline_slow_vault_and_dedicated(
    monkeypatch, tmp_path, offline, include_slow, expected_ran, expected_skipped
) -> None:
    _stub_dedicated_checks(monkeypatch)
    gates, ran = _marker_gates()
    monkeypatch.setattr(precheck_sweep, "ARTICLE_GATES", gates)
    args = SimpleNamespace(
        article="a.md", proof_sidecar="s.md", context_request="r.json",
        context_pack="p.json", context_receipt="c.json",
    )
    report = precheck_sweep.run_release_sweep(
        args, workspace_root=tmp_path, offline=offline, include_slow=include_slow
    )
    assert set(ran) == expected_ran
    assert expected_skipped <= {row["check"] for row in report["skipped"]}
    assert "editorial_plan" in report["checks_run"]
    assert all(row["reason"] for row in report["skipped"])
    assert report["passed"] is True


def test_offline_skips_url_checks_and_vault_context_binding(monkeypatch, tmp_path) -> None:
    _stub_dedicated_checks(monkeypatch)
    monkeypatch.setattr(precheck_sweep, "ARTICLE_GATES", ())
    article = tmp_path / "a.md"
    article.write_text("# Hi\n", encoding="utf-8")
    args = SimpleNamespace(article=str(article), proof_sidecar="s.md", editorial_plan="p.json")
    offline = precheck_sweep.run_release_sweep(
        args, workspace_root=tmp_path, offline=True, include_slow=False
    )
    reasons = {row["check"]: row["reason"] for row in offline["skipped"]}
    assert reasons["url_validator"] == "offline"
    assert reasons["public_research_links"] == "offline"
    assert reasons["context_binding"] == "needs vault connector"
    online = precheck_sweep.run_release_sweep(
        args, workspace_root=tmp_path, offline=False, include_slow=False
    )
    assert {"url_validator", "public_research_links", "context_binding"} <= set(online["checks_run"])


def test_every_gate_and_release_check_is_run_or_skipped_exactly_once(monkeypatch, tmp_path) -> None:
    _stub_dedicated_checks(monkeypatch)
    real_gates = precheck_sweep.ARTICLE_GATES
    stubs = tuple(
        (name, label, SimpleNamespace(check_file=lambda path: []))
        for name, label, _module in real_gates
    )
    monkeypatch.setattr(precheck_sweep, "ARTICLE_GATES", stubs)
    article = tmp_path / "a.md"
    article.write_text("# Hi\n", encoding="utf-8")
    args = SimpleNamespace(article=str(article), proof_sidecar="s.md", editorial_plan="p.json")
    for offline in (True, False):
        report = precheck_sweep.run_release_sweep(
            args, workspace_root=tmp_path, offline=offline, include_slow=False
        )
        ran = report["checks_run"]
        skipped = [row["check"] for row in report["skipped"]]
        expected = [name for name, _label, _module in real_gates] + list(precheck_sweep.RELEASE_CHECKS)
        for name in dict.fromkeys(expected):
            assert (name in ran) + (name in skipped) == 1, name
        assert len(ran) == len(set(ran)) and len(skipped) == len(set(skipped))
        assert set(precheck_sweep.RELEASE_ONLY) <= set(skipped)


def test_scorer_not_passed_row_reports_scores_and_thresholds() -> None:
    result = {
        "passed": False,
        "content_quality_score": 80.2,
        "aeo_geo": {"score": 70, "threshold": 90, "passed": False, "checks": {}},
    }
    rows = precheck_sweep.scorer_findings(result)
    assert [row["rule_id"] for row in rows] == ["content_scorer.not_passed"]
    assert rows[0]["severity"] == "error"
    assert "80.2" in rows[0]["message"] and "70/90" in rows[0]["message"]
    assert "content 85" in rows[0]["message"]


def test_scorer_passed_result_adds_no_not_passed_row() -> None:
    assert precheck_sweep.scorer_findings({"passed": True, "aeo_geo": {"checks": {}}}) == []


@pytest.mark.parametrize("kind, expected", [
    ("brief_paa", "brief.md"), ("user_csv", "paa.csv"), ("answersocrates", "paa.json"),
])
def test_runtime_policy_selects_paa_artifact_by_source_kind(kind, expected) -> None:
    args = _args(content_brief="brief.md", user_paa_csv="paa.csv", paa_artifact="paa.json")
    policy = precheck_sweep._runtime_policy(
        args, article_text=None, paa_policy={"source_kind": kind, "query": "q one"}
    )
    assert policy["paa_kwargs"]["paa_artifact"] == expected
    assert policy["paa_kwargs"]["expected_query"] == "q one"


def test_no_fit_customer_proof_check_runs_without_include_slow(monkeypatch, tmp_path) -> None:
    _stub_dedicated_checks(monkeypatch)
    monkeypatch.setattr(precheck_sweep, "ARTICLE_GATES", ())
    monkeypatch.setattr(
        precheck_sweep, "_no_fit_rows",
        lambda *a, **k: [{"rule_id": "no_fit_rule", "severity": "error", "message": "m"}],
    )
    article = tmp_path / "a.md"
    article.write_text("# Hi\n", encoding="utf-8")
    args = SimpleNamespace(article=str(article), proof_sidecar="s.md")
    report = precheck_sweep.run_release_sweep(
        args, workspace_root=tmp_path, offline=True, include_slow=False
    )
    assert [row["rule_id"] for row in report["findings"]] == ["no_fit_rule"]
    assert "customer_proof_no_fit" in report["checks_run"]


@pytest.mark.parametrize("passed, code", [(True, 0), (False, 1)])
def test_cli_exit_code_and_optional_output_dir(monkeypatch, tmp_path, passed, code) -> None:
    captured = {}

    def fake_sweep(args, **kwargs):
        captured["args"] = args
        return {"schema": "simpro-blog-release-sweep/v1", "passed": passed, "findings": [],
                "skipped": [], "checks_run": [], "elapsed_seconds": 0.1}

    monkeypatch.setattr(blog_release_sweep, "run_release_sweep", fake_sweep)
    argv = [
        "drafts/a.md", "--run-id", "r", "--proof-sidecar", "s.md", "--editorial-plan", "p.json",
        "--plan-review", "pr.json", "--article-review", "ar.json", "--keyword-decision", "k.json",
        "--scrub-receipt", "sc.json", "--serp-evidence", "se.json", "--plan-fulfillment", "pf.json",
        "--commercial-pillar-index", "context/commercial-pillar-index.json",
        "--stage-receipt", "st.json",
        "--workflow-mode", "new", "--assembly-date", "2026-10-07",
        "--sweep-output", str(tmp_path / "sweep.json"),
    ]
    assert blog_release_sweep.main(argv) == code
    written = json.loads((tmp_path / "sweep.json").read_text(encoding="utf-8"))
    assert written["passed"] is passed
    assert captured["args"].output_dir is None
