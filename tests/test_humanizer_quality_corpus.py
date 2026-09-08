import json
from pathlib import Path

from data_sources.modules.ai_copy_linter import lint_content


ROOT = Path(__file__).resolve().parents[1]


def _load(relative: str):
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def test_corpus_and_policy_cover_exact_upstream_inventory():
    """Losing any upstream pattern from policy or eval coverage must make this fail."""
    manifest = _load("vendor/blader-humanizer/UPSTREAM.json")
    policy = _load("config/humanizer-policy.json")
    corpus = _load("tests/fixtures/humanizer_quality_corpus.json")

    manifest_ids = [entry["id"] for entry in manifest["patterns"]]
    policy_ids = [entry["upstream_id"] for entry in policy["patterns"]]
    corpus_ids = [entry["upstream_pattern"] for entry in corpus["cases"]]

    assert manifest_ids == list(range(1, 36))
    assert sorted(policy_ids) == manifest_ids
    assert sorted(corpus_ids) == manifest_ids
    assert len(set(policy_ids)) == len(policy_ids)
    assert len(set(corpus_ids)) == len(corpus_ids)


def test_corpus_dispositions_match_reviewed_policy():
    """Changing a disposition without updating its evaluation must make this fail."""
    policy = _load("config/humanizer-policy.json")
    corpus = _load("tests/fixtures/humanizer_quality_corpus.json")
    expected = {
        entry["upstream_id"]: entry["disposition"]
        for entry in policy["patterns"]
    }

    assert {
        entry["upstream_pattern"]: entry["disposition"]
        for entry in corpus["cases"]
    } == expected


def test_deterministic_corpus_examples_exercise_expected_release_rules():
    """Disconnecting a reviewed blocker from the shared linter must make this fail."""
    corpus = _load("tests/fixtures/humanizer_quality_corpus.json")

    for case in corpus["cases"]:
        expected = set(case["expected_rule_ids"])
        if not expected:
            continue
        actual = {finding["rule_id"] for finding in lint_content(case["positive"])}
        assert expected <= actual, case["case_id"]


def test_corpus_counterexamples_do_not_trigger_mapped_release_rules():
    """Broadening deterministic patterns across valid exceptions must make this fail."""
    corpus = _load("tests/fixtures/humanizer_quality_corpus.json")

    for case in corpus["cases"]:
        expected = set(case["expected_rule_ids"])
        actual = {finding["rule_id"] for finding in lint_content(case["counterexample"])}
        assert expected.isdisjoint(actual), case["case_id"]


def test_contextual_patterns_never_create_namespaced_release_findings():
    """Compiling advisory, proof-routed, or excluded prose must make this fail."""
    corpus = _load("tests/fixtures/humanizer_quality_corpus.json")

    for case in corpus["cases"]:
        if case["upstream_pattern"] == 20:
            continue
        findings = lint_content(case["positive"])
        assert not [
            finding
            for finding in findings
            if str(finding["rule_id"]).startswith("humanizer.")
        ], case["case_id"]
