from copy import deepcopy

import pytest

from data_sources.modules.editorial_plan.plan_validation import check_plan
from data_sources.modules.editorial_plan.orchestration import _check_loaded_plan
from data_sources.modules.editorial_plan.v2 import check_search_evidence_binding
from tests.test_editorial_plan_guard import article_plan


def v2_plan() -> dict:
    plan = deepcopy(article_plan())
    plan["schema"] = "simpro-blog-editorial-plan/v2"
    plan["sections"][0].update(
        {
            "reader_question": "How should I prioritize competing scheduling constraints?",
            "section_payoff": "A constraint-first sequence the reader can apply.",
            "bridge_from_previous": None,
            "bridge_to_next": None,
        }
    )
    plan["original_contributions"] = [
        {
            "contribution_id": "constraint-first-checklist",
            "planned_contribution": "A constraint-first scheduling checklist",
            "purpose": "Help the reader prioritize dispatch decisions consistently.",
            "evidence_source": "Bound SERP evidence and approved operational guidance.",
            "target_section": "Scheduling constraints",
        }
    ]
    plan["search_strategy"] = {
        "primary_query": "field service scheduling",
        "searcher_task": "Choose a practical scheduling workflow.",
        "intent_class": "informational",
        "funnel_stage": "tofu",
        "serp_evidence_artifact": "research/serp-field-service-scheduling-2026-08-05.json",
        "dominant_content_type": "guide",
        "selected_content_type": "guide",
        "observed_serp_features": ["People also ask"],
        "related_query_paa_artifact": "research/paa-field-service-scheduling-2026-08-05.md",
        "format_decision": "match_dominant",
        "exception_reason": "none",
        "status": "ready",
    }
    plan["commercial_strategy"] = {
        "article_title": "Field Service Scheduling Guide",
        "article_primary_keyword": "field service scheduling",
        "article_intent": "informational",
        "destination_id": "simpro-us-homepage-field-service-management-software",
        "commercial_pillar_url": "https://www.simprogroup.com/",
        "planned_anchor_text": "field service management software",
        "planned_h2_section": "Scheduling constraints",
        "existing_overlapping_urls_checked": [
            "https://www.simprogroup.com/blog/field-service-scheduling"
        ],
        "pillar_versus_blog_intent_difference": (
            "The article teaches a scheduling method while the pillar is commercial."
        ),
        "cannibalization_decision": "different_intent",
        "incoming_link_candidates": [
            "https://www.simprogroup.com/blog/what-is-field-service-management"
        ],
        "status": "aligned",
    }
    plan["lifecycle"] = {
        "last_updated_date": "2026-08-05",
        "volatility": "standard",
        "next_review_date": "2027-02-01",
        "review_command": "/performance-review published/field-service-scheduling-guide.md",
        "gsc_lane": "unavailable: new article has no post-publication data",
        "ga4_lane": "unavailable: new article has no post-publication data",
        "semrush_lane": "available: bound keyword and destination evidence",
        "ai_citation_lane": "unavailable: new article has no post-publication data",
        "decision": "retain",
        "status": "scheduled",
    }
    del plan["serp_strategy"]
    del plan["query_ownership"]
    return plan


def rule_ids(findings: list[dict]) -> set[str]:
    return {str(finding["rule_id"]) for finding in findings}


def test_v2_plan_is_valid_and_v1_remains_archive_readable() -> None:
    assert check_plan(v2_plan()) == []
    assert check_plan(article_plan()) == []


def test_v2_search_decisions_bind_to_verified_serp_observations() -> None:
    evidence = {
        "observations": {
            "content_types": ["guide"],
            "serp_features": ["People also ask"],
        }
    }

    assert check_search_evidence_binding(v2_plan()["search_strategy"], evidence) == []


def test_v2_search_binding_rejects_unobserved_decisions() -> None:
    strategy = v2_plan()["search_strategy"]
    strategy["dominant_content_type"] = "comparison"
    strategy["observed_serp_features"] = ["video carousel"]
    evidence = {
        "observations": {
            "content_types": ["guide"],
            "serp_features": ["People also ask"],
        }
    }

    findings = check_search_evidence_binding(strategy, evidence)
    assert sum(
        finding["rule_id"] == "editorial_plan_serp_decision_unbound"
        for finding in findings
    ) == 2


@pytest.mark.parametrize(
    ("mutate", "expected"),
    [
        (
            lambda plan: plan["original_contributions"][0].update(
                {"contribution_id": "Invalid ID"}
            ),
            "editorial_plan_contribution_id_invalid",
        ),
        (
            lambda plan: plan["original_contributions"].append(
                dict(plan["original_contributions"][0])
            ),
            "editorial_plan_contribution_id_duplicate",
        ),
        (
            lambda plan: plan["original_contributions"][0].update(
                {"planned_contribution": "TBD"}
            ),
            "editorial_plan_placeholder",
        ),
        (
            lambda plan: plan["sections"][0].update({"reader_question": ""}),
            "editorial_plan_field_invalid",
        ),
        (
            lambda plan: plan["search_strategy"].update({"status": "blocked"}),
            "editorial_plan_search_strategy_blocked",
        ),
        (
            lambda plan: plan["commercial_strategy"].update({"status": "blocked"}),
            "editorial_plan_commercial_strategy_blocked",
        ),
        (
            lambda plan: plan["lifecycle"].update({"status": "blocked"}),
            "editorial_plan_lifecycle_blocked",
        ),
        (
            lambda plan: plan["lifecycle"].update({"next_review_date": "2026-01-01"}),
            "editorial_plan_lifecycle_date_invalid",
        ),
    ],
)
def test_v2_rejects_invalid_contract_values(mutate, expected: str) -> None:
    plan = v2_plan()
    mutate(plan)
    assert expected in rule_ids(check_plan(plan))


@pytest.mark.parametrize(
    "mutate",
    [
        lambda plan: plan["search_strategy"].update({"primary_query": "another query"}),
        lambda plan: plan["commercial_strategy"].update(
            {"article_primary_keyword": "another query"}
        ),
        lambda plan: plan["commercial_strategy"].update({"article_title": "Another title"}),
        lambda plan: plan["commercial_strategy"].update({"article_intent": "commercial"}),
        lambda plan: plan["commercial_strategy"].update({"planned_h2_section": "Missing"}),
        lambda plan: plan["lifecycle"].update({"last_updated_date": "2026-08-04"}),
    ],
)
def test_v2_rejects_cross_field_strategy_disagreement(mutate) -> None:
    plan = v2_plan()
    mutate(plan)
    assert "editorial_plan_strategy_mismatch" in rule_ids(check_plan(plan))


def test_v2_rejects_legacy_strategy_and_contribution_fields() -> None:
    plan = v2_plan()
    plan["serp_strategy"] = article_plan()["serp_strategy"]
    plan["original_contributions"][0]["visible_evidence"] = "Prewritten public wording"

    ids = rule_ids(check_plan(plan))

    assert "editorial_plan_unknown_field" in ids


def test_v2_interior_sections_require_both_bridges() -> None:
    plan = v2_plan()
    second = deepcopy(plan["sections"][0])
    second.update(
        {
            "section_number": 2,
            "heading": "Applying the sequence",
            "bridge_from_previous": "Now apply the priority order.",
            "bridge_to_next": None,
        }
    )
    plan["sections"][0]["bridge_to_next"] = "Next, apply the priority order."
    plan["sections"].append(second)
    plan["total_word_target"] = 550

    assert check_plan(plan) == []

    plan["sections"][1]["bridge_from_previous"] = None
    assert "editorial_plan_section_bridge_missing" in rule_ids(check_plan(plan))


def final_article(**replacements: str) -> str:
    fields: dict[str, object] = {
        "title": "Field Service Scheduling Guide",
        "meta_title": "Field Service Scheduling Guide for Teams | Simpro",
        "meta_description": (
            "Field service scheduling guidance for teams balancing job priority, "
            "technician skills, travel constraints, and customer commitments."
        ),
        "url_slug": "field-service-scheduling-guide",
        "primary_keyword": "field service scheduling",
        "secondary_keywords": ["dispatch workflow"],
        "last_updated": "2026-08-05",
    }
    fields.update(replacements)
    yaml_lines: list[str] = []
    for key, value in fields.items():
        if isinstance(value, list):
            yaml_lines.append(f"{key}:")
            yaml_lines.extend(f"  - {item}" for item in value)
        else:
            yaml_lines.append(f"{key}: {value}")
    return (
        "---\n"
        + "\n".join(yaml_lines)
        + "\n---\n# Field Service Scheduling Guide\n\n"
        "## Scheduling constraints\n\n"
        "Use a field service scheduling sequence to make each dispatch workflow explicit. "
        "Review [field service software](/field-service-management-software/).\n"
    )


def article_rule_ids(plan: dict, article: str) -> set[str]:
    findings = _check_loaded_plan(
        plan,
        article_path=None,
        article_content=article,
        serp_evidence_path=None,
        assembly_date="2026-08-05",
    )
    return rule_ids(findings)


def test_v2_final_article_metadata_matches_plan() -> None:
    assert article_rule_ids(v2_plan(), final_article()) == set()


@pytest.mark.parametrize(
    "article",
    [
        final_article(title="Another title"),
        final_article(meta_title="Another meta title"),
        final_article(meta_description="Another description"),
        final_article(primary_keyword="another keyword"),
        final_article(secondary_keywords="another keyword"),
        final_article(url_slug="another-slug"),
        final_article().replace("# Field Service Scheduling Guide", "# Another heading"),
    ],
)
def test_v2_final_article_rejects_metadata_drift(article: str) -> None:
    assert "editorial_plan_metadata_mismatch" in article_rule_ids(v2_plan(), article)


def test_v2_accepts_equivalent_legacy_slug_alias() -> None:
    article = final_article().replace(
        "url_slug: field-service-scheduling-guide",
        "slug: field-service-scheduling-guide",
    )
    assert article_rule_ids(v2_plan(), article) == set()


def test_v2_rejects_conflicting_slug_aliases() -> None:
    article = final_article().replace(
        "url_slug: field-service-scheduling-guide",
        "url_slug: field-service-scheduling-guide\nslug: another-slug",
    )
    assert "editorial_plan_slug_alias_conflict" in article_rule_ids(v2_plan(), article)
