"""Closed landing-page readiness gate inventory and its import-time invariant."""

from __future__ import annotations

from collections.abc import Iterable


ALWAYS = "always"
CONNECTOR_REQUIRED = "connector_required"
LEADING_GATES = (
    "artifact_identity",
    "context_binding",
    "public_artifact",
    "ai_copy_linter",
    "url_validator",
    "public_research_links",
)
ARTICLE_GATE_INVENTORY = (
    ("context_boundary", ALWAYS),
    ("metric_proof_pack", ALWAYS),
    ("numeric_claim_source", ALWAYS),
    ("faq_answer_quality", ALWAYS),
    ("faq_proof", ALWAYS),
    ("competitive_shortlist", ALWAYS),
    ("hindsight_boundary", ALWAYS),
    ("source_support", ALWAYS),
    ("source_quality", ALWAYS),
    ("customer_proof_diversity", ALWAYS),
    ("review_story_identity", ALWAYS),
    ("eeat_strength", ALWAYS),
    ("early_artifact", ALWAYS),
    ("answer_withholding", ALWAYS),
    ("vault_brand_language", CONNECTOR_REQUIRED),
    ("named_feature_status", CONNECTOR_REQUIRED),
    ("fred_authority", CONNECTOR_REQUIRED),
)
SCORER_GATE = "landing_page_scorer"
CONNECTOR_GATE_NAMES = frozenset(
    name for name, condition in ARTICLE_GATE_INVENTORY if condition == CONNECTOR_REQUIRED
)


def expected_landing_gate_inventory(*, connector_required: bool) -> list[str]:
    """Ordered gate names of a landing page that clears every blocking gate."""
    articles = [
        name
        for name, condition in ARTICLE_GATE_INVENTORY
        if condition == ALWAYS or connector_required
    ]
    return [*LEADING_GATES, *articles, SCORER_GATE]


def assert_landing_gate_invariant(
    article_gate_names: Iterable[str],
    content_gate_names: Iterable[str],
) -> None:
    """Fail at import when the gate table, the inventory, and the content adapters drift."""
    articles = list(article_gate_names)
    declared = [name for name, _ in ARTICLE_GATE_INVENTORY]
    adapters = set(content_gate_names)
    if articles != declared or set(articles) != adapters:
        raise RuntimeError(
            "readiness gate registry drift: "
            f"articles={articles}, declared={declared}, adapters={sorted(adapters)}"
        )


__all__ = [
    "ARTICLE_GATE_INVENTORY",
    "CONNECTOR_GATE_NAMES",
    "LEADING_GATES",
    "SCORER_GATE",
    "assert_landing_gate_invariant",
    "expected_landing_gate_inventory",
]
