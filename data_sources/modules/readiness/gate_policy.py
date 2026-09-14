"""Small gate-selection policies shared by readiness orchestration."""

from __future__ import annotations

from typing import Any, Dict, List

from .common import SIMPRO_CONTEXT_GATE_NAMES


def missing_gate_finding(
    rule_id: str,
    message: str,
    suggestion: str,
) -> List[Dict[str, Any]]:
    return [{
        "rule_id": rule_id,
        "severity": "error",
        "line": 1,
        "column": 1,
        "message": message,
        "suggestion": suggestion,
    }]


def skip_article_gate(
    name: str,
    *,
    artifact_kind: str,
    visible_faq: bool,
    simpro_context_required: bool,
) -> bool:
    blog_only = artifact_kind != "blog" and name in {
        "industry_cluster_link_policy",
        "paa_provenance",
        "editorial_plan",
        "semrush_keyword_decision",
    }
    faq_skipped = name in {"faq_answer_quality", "faq_proof"} and not visible_faq
    context_skipped = name in SIMPRO_CONTEXT_GATE_NAMES and not simpro_context_required
    fred_skipped = name == "fred_authority" and not simpro_context_required
    return blog_only or faq_skipped or context_skipped or fred_skipped


def artifact_kind_rule_id(message: str) -> str:
    normalized = message.casefold()
    if "unsupported" in normalized:
        return "artifact_kind_unsupported"
    if "conflict" in normalized:
        return "artifact_kind_conflict"
    return "artifact_kind_missing"


__all__ = ["artifact_kind_rule_id", "missing_gate_finding", "skip_article_gate"]
