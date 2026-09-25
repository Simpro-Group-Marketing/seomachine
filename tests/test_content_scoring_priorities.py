from types import SimpleNamespace

from data_sources.modules.content_scoring.priorities import build_priority_fixes


def test_hard_gate_blockers_precede_soft_dimension_advice_in_gate_order():
    dimensions = [
        (
            "readability",
            {
                "score": 20,
                "issues": [{"issue": "Improve readability", "fix": "Use shorter sentences."}],
            },
        ),
        (
            "seo",
            {
                "score": 30,
                "issues": [{"issue": "Add metadata", "fix": "Add a meta description."}],
            },
        ),
    ]
    gate_context = {
        "aeo_geo": {"issues": [{"check": "direct_answer", "issue": "Missing direct answer."}]},
        "aeo_geo_passed": False,
        "source_support_findings": [{"line": 12}],
        "source_support_passed": False,
        "paa_provenance_check": {"details": {"findings": [{"question": "What is it?"}]}},
        "paa_provenance_passed": False,
        "faq_proof_check": {"details": {"findings": [{"question": "How much?"}]}},
        "faq_proof_passed": False,
        "metric_proof_pack_findings": [],
        "metric_proof_pack_passed": True,
        "customer_proof_findings": [],
        "customer_proof_passed": True,
        "review_story_findings": [],
        "review_story_passed": True,
        "url_validation": SimpleNamespace(
            passed=False,
            blockers=[SimpleNamespace(url="https://example.com/unresolved")],
        ),
        "minimum_visible_words": {"threshold": 300, "word_count": 100},
        "minimum_visible_words_passed": True,
    }

    fixes = build_priority_fixes(
        dimensions,
        gate_context,
        weights={"readability": 0.15, "seo": 0.25},
    )

    assert [fix["dimension"] for fix in fixes] == [
        "aeo_geo",
        "source_support",
        "paa_provenance",
        "faq_proof",
        "url_validation",
    ]
    assert len(fixes) == 5
    assert all(fix["dimension"] not in {"readability", "seo"} for fix in fixes)


def test_eeat_only_aeo_geo_failure_precedes_soft_dimension_advice():
    dimensions = [
        ("readability", {"score": 20, "issues": [{"issue": "Improve readability"}]}),
        ("seo", {"score": 30, "issues": [{"issue": "Add metadata"}]}),
    ]
    gate_context = _passing_gate_context()
    gate_context.update(
        {
            "aeo_geo": {"issues": [{"check": "eeat_proof", "issue": "Add experience proof."}]},
            "aeo_geo_passed": False,
        }
    )

    fixes = build_priority_fixes(
        dimensions,
        gate_context,
        weights={"readability": 0.15, "seo": 0.25},
    )

    assert [fix["dimension"] for fix in fixes] == ["aeo_geo", "seo", "readability"]


def test_metric_review_and_customer_proof_blockers_precede_soft_advice_in_order():
    dimensions = [
        ("readability", {"score": 20, "issues": [{"issue": "Improve readability"}]}),
        ("seo", {"score": 30, "issues": [{"issue": "Add metadata"}]}),
    ]
    gate_context = _passing_gate_context()
    gate_context.update(
        {
            "metric_proof_pack_findings": [{"line": 8}],
            "metric_proof_pack_passed": False,
            "review_story_findings": [{"line": 15}],
            "review_story_passed": False,
            "customer_proof_findings": [{"line": 21}],
            "customer_proof_passed": False,
        }
    )

    fixes = build_priority_fixes(
        dimensions,
        gate_context,
        weights={"readability": 0.15, "seo": 0.25},
    )

    assert [fix["dimension"] for fix in fixes] == [
        "metric_proof_pack",
        "review_story_identity",
        "customer_proof_diversity",
        "seo",
        "readability",
    ]


def _passing_gate_context():
    return {
        "aeo_geo": {"issues": []},
        "aeo_geo_passed": True,
        "source_support_findings": [],
        "source_support_passed": True,
        "paa_provenance_check": {"details": {"findings": []}},
        "paa_provenance_passed": True,
        "faq_proof_check": {"details": {"findings": []}},
        "faq_proof_passed": True,
        "metric_proof_pack_findings": [],
        "metric_proof_pack_passed": True,
        "customer_proof_findings": [],
        "customer_proof_passed": True,
        "review_story_findings": [],
        "review_story_passed": True,
        "url_validation": None,
        "minimum_visible_words": {"threshold": 300, "word_count": 300},
        "minimum_visible_words_passed": True,
    }
