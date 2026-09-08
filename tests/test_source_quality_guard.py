from datetime import date

import pytest

from data_sources.modules.source_quality_guard import (
    check_content,
    check_source_map,
)


def source_row(**overrides: str) -> str:
    fields = {
        "Claim": "BLS recorded 8,000 electricians in the selected occupation table",
        "Claim type": "statistic",
        "URL": "https://www.bls.gov/oes/current/oes472111.htm",
        "Evidence": "8,000 electricians",
        "Source class": "government",
        "Original-source status": "original",
        "Source date": "2026-04-01",
        "Checked date": "2026-08-01",
        "Claim fit": "direct",
        "Freshness decision": "current",
        "Freshness reason": "Current annual occupational table for the scoped claim",
        "Status": "approved",
        "Intended use": "Body statistic with visible source link",
    }
    fields.update(overrides)
    return "- " + " | ".join(f"{key}: {value}" for key, value in fields.items())


def strategy_sidecar(*, volatility: str = "standard", next_review: str = "2027-02-01", lanes: dict[str, str] | None = None) -> str:
    lane_values = {
        "GSC lane": "unavailable: new article has no post-publication data",
        "GA4 lane": "unavailable: new article has no post-publication data",
        "Semrush lane": "available: destination evidence checked 2026-08-01",
        "AI-citation lane": "not_applicable: no tracked prompt set is assigned",
    }
    lane_values.update(lanes or {})
    return f"""## Search Intent and Format Decision
- Contract version: blog-strategy-contract/v1
- Primary query or prompt: electrical hiring plan
- Searcher task: Build a hiring plan.
- Intent class: informational
- Funnel stage: MOFU
- SERP evidence artifact: research/serp-electrical-hiring-plan-2026-08-06.md
- Dominant content type: guide
- Selected content type: guide
- Observed SERP features: People also ask
- Related-query/PAA artifact: research/paa-electrical-hiring-plan-2026-08-06.md
- Format decision: match_dominant
- Exception reason: none
- Status: ready

## Commercial Pillar and Anchor Decision
- Contract version: blog-strategy-contract/v1
- Article title: Electrical Hiring Plan
- Article primary keyword: electrical hiring plan
- Article intent: informational
- Destination ID: simpro-us-industry-electrical-software
- Commercial pillar URL: https://www.simprogroup.com/industries/electrical-software
- Planned anchor text: electrical contractor software
- Planned H2 section: Plan the operating system
- Existing overlapping URLs checked: https://www.simprogroup.com/blog/electrical-contractor-guide
- Pillar-versus-blog intent difference: The article has different intent and different content type from the commercial page.
- Cannibalization decision: different_intent
- Incoming-link candidates: https://www.simprogroup.com/blog/electrical-contractor-guide
- Status: aligned

## Lifecycle Refresh Record
- Contract version: blog-strategy-contract/v1
- Last-updated date: 2026-08-06
- Volatility: {volatility}
- Next review date: {next_review}
- Review command: /performance-review published/electrical-hiring-plan.md
- GSC lane: {lane_values['GSC lane']}
- GA4 lane: {lane_values['GA4 lane']}
- Semrush lane: {lane_values['Semrush lane']}
- AI-citation lane: {lane_values['AI-citation lane']}
- Decision: retain
- Status: scheduled
"""


def article() -> str:
    return """---
title: Electrical Hiring Plan
brand: Simpro
market: US
primary_keyword: electrical hiring plan
last_updated: 2026-08-06
---
# Electrical Hiring Plan

Use the cited occupational table to scope the claim.
"""


def non_simpro_article() -> str:
    return """---
title: ClockShark Scheduling Guide
brand: ClockShark
market: US
primary_keyword: construction scheduling
last_updated: 2026-08-06
---
# ClockShark Scheduling Guide

Use the cited occupational table to scope the claim.
"""


def rule_ids(findings: list[dict[str, object]]) -> set[str]:
    return {str(finding["rule_id"]) for finding in findings}


def test_complete_direct_original_source_row_passes() -> None:
    proof = "## Source Map\n" + source_row()

    assert check_source_map(proof, today=date(2026, 8, 6)) == []


def test_complete_markdown_table_source_map_passes() -> None:
    headers = [
        "Claim", "Claim type", "URL", "Evidence", "Source class",
        "Original-source status", "Source date", "Checked date", "Claim fit",
        "Freshness decision", "Freshness reason", "Status", "Intended use",
    ]
    values = [
        "BLS recorded 8,000 electricians", "statistic",
        "https://www.bls.gov/oes/current/oes472111.htm", "8,000 electricians",
        "government", "original", "2026-04-01", "2026-08-01", "direct",
        "current", "Current annual table", "approved", "Body statistic",
    ]
    proof = (
        "## Source Map\n| " + " | ".join(headers) + " |\n| "
        + " | ".join("---" for _ in headers) + " |\n| "
        + " | ".join(values) + " |\n"
    )

    assert check_source_map(proof, today=date(2026, 8, 6)) == []


def test_source_map_rows_inside_fenced_examples_are_ignored() -> None:
    proof = "```markdown\n## Source Map\n" + source_row(**{"Claim fit": "partial"}) + "\n```\n"

    assert check_source_map(proof, today=date(2026, 8, 6)) == []


def test_bare_sidecar_heading_ends_source_map_scope() -> None:
    proof = (
        "Source Map\n"
        + source_row(
            **{
                "Claim": "BLS publishes an occupational profile for electricians",
                "Claim type": "factual",
                "Evidence": "Electricians occupational profile",
                "Original-source status": "not_applicable",
            }
        )
        + "\n\nCustomer Proof Pack\n"
        "- Claim: selected customer proof is governed by the customer proof pack, not Source Map parsing\n"
    )

    assert check_source_map(proof, today=date(2026, 8, 6)) == []


def test_markdown_table_cannot_hide_missing_source_quality_columns() -> None:
    proof = """## Source Map
| Claim | URL | Evidence |
|---|---|---|
| A current claim | https://example.com/source | Direct evidence |
"""

    findings = check_source_map(proof, today=date(2026, 8, 6))

    assert "source_quality_required_field_missing" in rule_ids(findings)


def test_missing_required_source_map_field_fails() -> None:
    proof = "## Source Map\n" + source_row(**{"Claim fit": ""})

    findings = check_source_map(proof, today=date(2026, 8, 6))

    assert "source_quality_required_field_missing" in rule_ids(findings)


@pytest.mark.parametrize(
    ("overrides", "expected_rule"),
    [
        ({"Claim fit": "partial"}, "source_quality_claim_fit_not_direct"),
        ({"Original-source status": "secondary"}, "source_quality_statistic_not_original"),
        ({"Source class": "secondary"}, "source_quality_original_status_conflict"),
        ({"Claim type": "regulation", "Source class": "neutral"}, "source_quality_official_source_required"),
        ({"Claim type": "recommendation", "Source class": "competitor_owned"}, "source_quality_competitor_neutral_proof"),
        ({"Source date": "undated", "Freshness decision": "current"}, "source_quality_undated_unscoped"),
        ({"Freshness decision": "refresh_required"}, "source_quality_refresh_required"),
        ({"Claim type": "customer_metric"}, "source_quality_stricter_proof_required"),
        ({"Claim type": "feature_claim"}, "source_quality_stricter_proof_required"),
        ({"Claim type": "faq"}, "source_quality_faq_proof_map_required"),
    ],
)
def test_source_quality_hard_rules(overrides: dict[str, str], expected_rule: str) -> None:
    proof = "## Source Map\n" + source_row(**overrides)

    findings = check_source_map(proof, today=date(2026, 8, 6))

    assert expected_rule in rule_ids(findings)


def test_source_map_supplements_but_does_not_replace_a_stricter_proof_pack() -> None:
    proof = (
        "## Source Map\n"
        + source_row(**{"Claim type": "customer_metric"})
        + "\n\n## Customer Proof Pack\n- Pack status: ready\n"
    )

    assert check_source_map(proof, today=date(2026, 8, 6)) == []


def test_historical_scope_requires_a_substantive_freshness_reason() -> None:
    proof = "## Source Map\n" + source_row(
        **{
            "Claim type": "historical",
            "Source date": "historical",
            "Freshness decision": "historical_scoped",
            "Freshness reason": "none",
            "Original-source status": "not_applicable",
        }
    )

    findings = check_source_map(proof, today=date(2026, 8, 6))

    assert "source_quality_freshness_reason_missing" in rule_ids(findings)


def test_duplicate_and_conflicting_rows_fail() -> None:
    duplicate = source_row()
    conflict = source_row(**{"Status": "blocked"})
    proof = f"## Source Map\n{duplicate}\n{duplicate}\n{conflict}\n"

    findings = check_source_map(proof, today=date(2026, 8, 6))

    assert "source_quality_row_duplicate" in rule_ids(findings)
    assert "source_quality_row_conflict" in rule_ids(findings)


def test_faq_source_row_passes_with_exact_faq_proof_map_url() -> None:
    url = "https://www.bls.gov/oes/current/oes472111.htm"
    proof = (
        "## Source Map\n"
        + source_row(**{"Claim type": "faq", "Intended use": "FAQ answer evidence"})
        + "\n\n## FAQ Proof Map\n"
        + f"- FAQ: How many electricians are recorded? | URL: {url} | Source class: neutral | Competitor check: clear | Support: Direct table support\n"
    )

    assert check_source_map(proof, today=date(2026, 8, 6)) == []


def test_bare_section_after_faq_proof_map_cannot_supply_its_url() -> None:
    source_url = "https://www.bls.gov/oes/current/oes472111.htm"
    proof = (
        "Source Map\n"
        + source_row(**{"Claim type": "faq", "Intended use": "FAQ answer evidence"})
        + "\n\nFAQ Proof Map\n"
        "- FAQ: What source supports the workflow? | URL: https://example.org/other "
        "| Source class: neutral | Competitor check: clear | Support: Other support\n\n"
        "Customer Proof Pack\n"
        f"- Claim: unrelated proof route | URL: {source_url} | Status: approved\n"
    )

    findings = check_source_map(proof, today=date(2026, 8, 6))

    assert "source_quality_faq_proof_map_required" in rule_ids(findings)


def test_standard_lifecycle_with_separate_unavailable_lanes_passes() -> None:
    proof = strategy_sidecar() + "\n## Source Map\n" + source_row(
        **{
            "Claim": "BLS publishes an occupational profile for electricians",
            "Claim type": "factual",
            "Evidence": "Electricians occupational profile",
            "Original-source status": "not_applicable",
        }
    )

    findings = check_content(article(), proof_content=proof, today=date(2026, 8, 6))

    assert findings == []


def test_simpro_lifecycle_contract_requires_at_least_one_source_map_row() -> None:
    findings = check_content(article(), proof_content=strategy_sidecar(), today=date(2026, 8, 6))

    assert "source_quality_source_map_missing" in rule_ids(findings)


def test_non_simpro_article_without_strategy_contract_skips_lifecycle_contract() -> None:
    findings = check_content(non_simpro_article(), proof_content="", today=date(2026, 8, 6))

    assert findings == []


def test_simpro_article_missing_strategy_contract_fails_lifecycle_contract() -> None:
    findings = check_content(article(), proof_content="## Source Map\n", today=date(2026, 8, 6))

    assert "blog_strategy_contract_section_missing" in rule_ids(findings)


def test_statistics_led_article_requires_high_volatility_and_ninety_day_review() -> None:
    proof = strategy_sidecar(volatility="standard", next_review="2027-02-01") + "\n## Source Map\n" + source_row()

    findings = check_content(article(), proof_content=proof, today=date(2026, 8, 6))

    assert "lifecycle_high_volatility_required" in rule_ids(findings)
    assert "lifecycle_review_cadence_exceeded" in rule_ids(findings)


def test_high_volatility_review_within_ninety_days_passes() -> None:
    proof = strategy_sidecar(volatility="high", next_review="2026-11-04") + "\n## Source Map\n" + source_row()

    findings = check_content(article(), proof_content=proof, today=date(2026, 8, 6))

    assert findings == []


@pytest.mark.parametrize(
    ("lanes", "expected_rule"),
    [
        ({"GSC lane": "unavailable"}, "lifecycle_lane_reason_missing"),
        ({"GA4 lane": "0"}, "lifecycle_lane_status_invalid"),
        ({"Semrush lane": "unavailable: 0 rows"}, "lifecycle_unavailable_as_zero"),
        ({"AI-citation lane": "improved 25%"}, "lifecycle_performance_claim_unproved"),
    ],
)
def test_lifecycle_lanes_never_synthesize_missing_or_improved_performance(
    lanes: dict[str, str],
    expected_rule: str,
) -> None:
    proof = strategy_sidecar(volatility="high", next_review="2026-11-04", lanes=lanes)

    findings = check_content(article(), proof_content=proof, today=date(2026, 8, 6))

    assert expected_rule in rule_ids(findings)


def test_lifecycle_dates_must_match_article_and_be_future_bounded() -> None:
    proof = strategy_sidecar(volatility="high", next_review="2026-08-05")

    findings = check_content(article(), proof_content=proof, today=date(2026, 8, 6))

    assert "lifecycle_next_review_not_after_update" in rule_ids(findings)


def test_lifecycle_next_review_cannot_already_be_overdue() -> None:
    proof = strategy_sidecar(volatility="high", next_review="2026-08-10").replace(
        "- Last-updated date: 2026-08-06",
        "- Last-updated date: 2026-05-01",
    )
    content = article().replace("last_updated: 2026-08-06", "last_updated: 2026-05-01")

    findings = check_content(content, proof_content=proof, today=date(2026, 8, 11))

    assert "lifecycle_next_review_overdue" in rule_ids(findings)


def test_pricing_topic_requires_high_volatility_even_without_source_rows() -> None:
    proof = strategy_sidecar(volatility="standard", next_review="2027-02-01").replace(
        "- Article title: Electrical Hiring Plan",
        "- Article title: Field Service Software Pricing Guide",
    )
    content = article().replace("title: Electrical Hiring Plan", "title: Field Service Software Pricing Guide")

    findings = check_content(content, proof_content=proof, today=date(2026, 8, 6))

    assert "lifecycle_high_volatility_required" in rule_ids(findings)


def test_lifecycle_performance_language_catches_traffic_click_and_ranking_claims() -> None:
    proof = strategy_sidecar(
        volatility="high",
        next_review="2026-11-04",
        lanes={
            "GSC lane": "available: traffic is up 25 percent",
            "GA4 lane": "available: clicks rose 25 percent",
            "Semrush lane": "available: rankings jumped from 12 to 4",
        },
    )

    findings = check_content(article(), proof_content=proof, today=date(2026, 8, 6))

    assert "lifecycle_performance_claim_unproved" in rule_ids(findings)
