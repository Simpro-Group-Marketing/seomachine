from __future__ import annotations

import pytest

from data_sources.modules.proof_link_policy import analyze_proof_links


def test_start_with_vendor_best_fit_is_editorial_buyer_guidance():
    article = (
        "# Buyer guide\n\n"
        "**Best fit:** Start with Example FSM if the buying case includes service and project work.\n"
    )

    report = analyze_proof_links(article, brand="Simpro")

    assert len(report.requirements) == 1
    assert report.requirements[0].mode == "proof_not_required"
    assert report.requirements[0].reason == "navigation_or_nonfactual_advice"


def test_start_with_vendor_best_fit_does_not_hide_pricing_claim():
    article = (
        "# Buyer guide\n\n"
        "**Best fit:** Start with Example FSM if the buying case includes service work. "
        "Pricing starts at $100 per month.\n"
    )

    report = analyze_proof_links(article, brand="Simpro")

    assert any(row.mode == "inline_required" for row in report.requirements)


@pytest.mark.parametrize(
    "advice",
    (
        "Begin with a real inbound call and a dispatch exception.",
        "Run the same job and report with every candidate before choosing.",
    ),
)
def test_buyer_test_actions_are_proof_not_required(advice):
    report = analyze_proof_links(f"# Buyer guide\n\n{advice}\n", brand="Simpro")

    assert len(report.requirements) == 1
    assert report.requirements[0].mode == "proof_not_required"
