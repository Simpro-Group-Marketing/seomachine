"""Closed mapping between declared readiness gates and execution phases."""

from __future__ import annotations

from collections.abc import Iterable

from ..blog_gate_inventory import BLOG_GATE_DESCRIPTORS


NON_ARTICLE_EXECUTORS = frozenset(
    {
        "artifact_identity",
        "context_binding",
        "blog_assembly_bom",
        "public_artifact",
        "ai_copy_linter",
        "url_validator",
        "public_research_links",
        "content_scorer",
        "input_seal",
    }
)
SPECIAL_ARTICLE_EXECUTORS = frozenset(
    {"editorial_plan", "semrush_keyword_decision"}
)


def assert_gate_executor_invariant(
    article_gate_names: Iterable[str],
    content_gate_names: Iterable[str],
) -> None:
    declared = {descriptor.name for descriptor in BLOG_GATE_DESCRIPTORS}
    articles = set(article_gate_names)
    content = set(content_gate_names)
    missing = declared - NON_ARTICLE_EXECUTORS - content - SPECIAL_ARTICLE_EXECUTORS
    extra = (NON_ARTICLE_EXECUTORS | articles) - declared
    adapter_drift = articles - content - SPECIAL_ARTICLE_EXECUTORS
    if missing or extra or adapter_drift:
        raise RuntimeError(
            "readiness gate executor registry drift: "
            f"missing={sorted(missing)}, extra={sorted(extra)}, adapters={sorted(adapter_drift)}"
        )


__all__ = ["NON_ARTICLE_EXECUTORS", "SPECIAL_ARTICLE_EXECUTORS", "assert_gate_executor_invariant"]
