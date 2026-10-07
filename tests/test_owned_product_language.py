from __future__ import annotations

import pytest

from data_sources.modules.owned_product_language import (
    is_approved_product_language,
    product_language_kind,
)


@pytest.mark.parametrize(
    ("sentence", "kind"),
    [
        ("Simpro is a software platform for trade contractors.", "definitional"),
        ("Simpro works by linking each quote to the job it becomes.", "process"),
        ("Simpro connects scheduling, job costing, and invoicing in one record.", "factual"),
        ("Simpro allows dispatchers to drag jobs onto the scheduling board.", "capability"),
        ("Simpro enables office staff to assign a technician from the job card.", "capability"),
        ("Simpro's scheduling board shows technician availability for the day.", "factual"),
    ],
)
def test_low_risk_simpro_product_sentences_are_product_language(sentence, kind):
    assert product_language_kind(sentence) == kind


@pytest.mark.parametrize(
    "sentence",
    [
        "Simpro helps teams cut admin time across the office.",
        "Simpro reduces the time dispatchers spend on the phone.",
        "Simpro streamlines scheduling for growing contractors.",
        "Simpro Fast Cash is available on Enterprise plans.",
        "Simpro costs $49 per user each month.",
        "Simpro serves 8,000 customers across four countries.",
        "Simpro is better than spreadsheets for scheduling.",
        "Simpro is the leading field service platform for electricians.",
        "Simpro ensures every job is invoiced on time.",
        "Simpro tracks licensing compliance for each technician.",
        "Simpro pricing includes onboarding support.",
        'Simpro is described by one customer as "the backbone of our whole operation."',
        "Teams should choose Simpro when they run multiple crews.",
    ],
)
def test_outcome_risk_and_specialist_sentences_are_not_product_language(sentence):
    assert product_language_kind(sentence) is None


def test_sentence_without_simpro_subject_is_not_product_language():
    assert product_language_kind("The scheduling board shows technician availability.") is None


def test_approval_requires_owned_product_row_typed_as_product_or_feature_claim():
    sentence = "Simpro connects scheduling, job costing, and invoicing in one record."

    assert is_approved_product_language(
        sentence, source_class="owned_product", claim_type="product_claim"
    )
    assert is_approved_product_language(
        sentence, source_class="owned_product", claim_type="feature_claim"
    )
    assert not is_approved_product_language(
        sentence, source_class="owned_product", claim_type="factual"
    )
    assert not is_approved_product_language(
        sentence, source_class="primary_authority", claim_type="product_claim"
    )
    assert not is_approved_product_language(
        "Simpro reduces scheduling time.",
        source_class="owned_product",
        claim_type="product_claim",
    )
