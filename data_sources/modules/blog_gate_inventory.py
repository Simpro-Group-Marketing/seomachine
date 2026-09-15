"""Canonical ordered publish-readiness gate inventory."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence


@dataclass(frozen=True, slots=True)
class BlogGateDescriptor:
    name: str
    condition: str = "always"


BLOG_GATE_DESCRIPTORS = (
    BlogGateDescriptor("artifact_identity"),
    BlogGateDescriptor("context_binding"),
    BlogGateDescriptor("blog_assembly_bom"),
    BlogGateDescriptor("public_artifact"),
    BlogGateDescriptor("ai_copy_linter"),
    BlogGateDescriptor("url_validator"),
    BlogGateDescriptor("public_research_links"),
    BlogGateDescriptor("industry_cluster_link_policy"),
    BlogGateDescriptor("metric_proof_pack"),
    BlogGateDescriptor("numeric_claim_source"),
    BlogGateDescriptor("faq_answer_quality", "visible_faq"),
    BlogGateDescriptor("faq_proof", "visible_faq"),
    BlogGateDescriptor("paa_provenance"),
    BlogGateDescriptor("editorial_plan"),
    BlogGateDescriptor("semrush_keyword_decision"),
    BlogGateDescriptor("blog_strategy", "current_strategy"),
    BlogGateDescriptor("competitive_shortlist"),
    BlogGateDescriptor("hindsight_boundary"),
    BlogGateDescriptor("source_support"),
    BlogGateDescriptor("source_quality"),
    BlogGateDescriptor("customer_proof_diversity"),
    BlogGateDescriptor("review_story_identity"),
    BlogGateDescriptor("eeat_strength"),
    BlogGateDescriptor("early_artifact"),
    BlogGateDescriptor("answer_withholding"),
    BlogGateDescriptor("schema_handoff", "current_strategy"),
    BlogGateDescriptor("vault_brand_language", "connector_required"),
    BlogGateDescriptor("named_feature_status", "connector_required"),
    BlogGateDescriptor("fred_authority", "connector_required"),
    BlogGateDescriptor("content_scorer"),
    BlogGateDescriptor("input_seal"),
)


def expected_blog_gate_inventory(
    *,
    visible_faq: bool,
    connector_required: bool,
    current_strategy: bool = False,
) -> list[str]:
    return [
        descriptor.name
        for descriptor in BLOG_GATE_DESCRIPTORS
        if _enabled(
            descriptor,
            visible_faq=visible_faq,
            connector_required=connector_required,
            current_strategy=current_strategy,
        )
    ]


def order_blog_gate_results(
    gates: Sequence[Mapping[str, Any]],
    *,
    visible_faq: bool,
    connector_required: bool,
    current_strategy: bool = False,
) -> list[Mapping[str, Any]]:
    expected = expected_blog_gate_inventory(
        visible_faq=visible_faq,
        connector_required=connector_required,
        current_strategy=current_strategy,
    )
    by_name: dict[str, Mapping[str, Any]] = {}
    for row in gates:
        name = row.get("name") if isinstance(row, Mapping) else None
        if not isinstance(name, str) or not name or name in by_name:
            raise ValueError("blog gate results contain an invalid or duplicate name")
        by_name[name] = row
    if set(by_name) != set(expected):
        raise ValueError("blog gate results do not match the expected conditional inventory")
    return [by_name[name] for name in expected]


def _enabled(
    descriptor: BlogGateDescriptor,
    *,
    visible_faq: bool,
    connector_required: bool,
    current_strategy: bool,
) -> bool:
    if descriptor.condition == "always":
        return True
    if descriptor.condition == "visible_faq":
        return visible_faq
    if descriptor.condition == "connector_required":
        return connector_required
    if descriptor.condition == "current_strategy":
        return current_strategy
    raise ValueError(f"unsupported blog gate condition: {descriptor.condition}")


__all__ = [
    "BLOG_GATE_DESCRIPTORS",
    "BlogGateDescriptor",
    "expected_blog_gate_inventory",
    "order_blog_gate_results",
]
