"""Apply the commercial strategy guard from structured editorial-plan v2 data."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import date
from pathlib import Path
from typing import Any

from . import blog_strategy_guard as legacy_guard
from .commercial_pillar_index import CommercialPillarIndex
from .editorial_plan.v2 import EDITORIAL_PLAN_SCHEMA_V2
from .guard_common import Finding
from .url_validator import UrlValidationSummary


def check_content(
    content: str,
    *,
    editorial_plan: Mapping[str, Any] | None,
    index: CommercialPillarIndex,
    today: date,
    url_summary: UrlValidationSummary | None = None,
    context_request: Mapping[str, Any] | None = None,
    article_path: str | Path | None = None,
    artifact_root: str | Path | None = None,
) -> list[Finding]:
    brand = legacy_guard.extract_frontmatter(content).get("brand", "").strip()
    if brand and brand.casefold() != "simpro" and "simprogroup.com" not in content.casefold():
        return []
    if not isinstance(editorial_plan, Mapping) or editorial_plan.get("schema") != EDITORIAL_PLAN_SCHEMA_V2:
        return [legacy_guard._finding(
            "blog_strategy_editorial_plan_invalid",
            1,
            f"Current blog strategy requires {EDITORIAL_PLAN_SCHEMA_V2}.",
        )]
    search = editorial_plan.get("search_strategy")
    commercial = editorial_plan.get("commercial_strategy")
    lifecycle = editorial_plan.get("lifecycle")
    if not all(isinstance(row, Mapping) for row in (search, commercial, lifecycle)):
        return [legacy_guard._finding(
            "blog_strategy_editorial_plan_invalid",
            1,
            "Editorial plan is missing structured search, commercial, or lifecycle strategy.",
        )]
    findings = _context_findings(context_request, content)
    findings.extend(legacy_guard.check_content(
        content,
        proof_content=_legacy_projection(search, commercial, lifecycle),
        index=index,
        today=today,
        url_summary=url_summary,
        context_request=None,
        article_path=article_path,
        artifact_root=artifact_root,
        require_strategy=True,
    ))
    return legacy_guard._sort_findings(findings)


def _legacy_projection(
    search: Mapping[str, Any],
    commercial: Mapping[str, Any],
    lifecycle: Mapping[str, Any],
) -> str:
    def text(value: Any) -> str:
        if isinstance(value, list):
            return " | ".join(str(item) for item in value)
        return str(value)

    search_fields = (
        ("Contract version", "blog-strategy-contract/v1"),
        ("Primary query or prompt", search.get("primary_query")),
        ("Searcher task", search.get("searcher_task")),
        ("Intent class", search.get("intent_class")),
        ("Funnel stage", search.get("funnel_stage")),
        ("SERP evidence artifact", search.get("serp_evidence_artifact")),
        ("Dominant content type", search.get("dominant_content_type")),
        ("Selected content type", search.get("selected_content_type")),
        ("Observed SERP features", search.get("observed_serp_features")),
        ("Related-query/PAA artifact", search.get("related_query_paa_artifact")),
        ("Format decision", search.get("format_decision")),
        ("Exception reason", search.get("exception_reason")),
        ("Status", search.get("status")),
    )
    commercial_fields = (
        ("Contract version", "blog-strategy-contract/v1"),
        ("Article title", commercial.get("article_title")),
        ("Article primary keyword", commercial.get("article_primary_keyword")),
        ("Article intent", commercial.get("article_intent")),
        ("Destination ID", commercial.get("destination_id")),
        ("Commercial pillar URL", commercial.get("commercial_pillar_url")),
        ("Planned anchor text", commercial.get("planned_anchor_text")),
        ("Planned H2 section", commercial.get("planned_h2_section")),
        ("Existing overlapping URLs checked", commercial.get("existing_overlapping_urls_checked")),
        ("Pillar-versus-blog intent difference", commercial.get("pillar_versus_blog_intent_difference")),
        ("Cannibalization decision", commercial.get("cannibalization_decision")),
        ("Incoming-link candidates", commercial.get("incoming_link_candidates")),
        ("Status", commercial.get("status")),
    )
    lifecycle_fields = (
        ("Contract version", "blog-strategy-contract/v1"),
        ("Last-updated date", lifecycle.get("last_updated_date")),
        ("Volatility", lifecycle.get("volatility")),
        ("Next review date", lifecycle.get("next_review_date")),
        ("Review command", lifecycle.get("review_command")),
        ("GSC lane", lifecycle.get("gsc_lane")),
        ("GA4 lane", lifecycle.get("ga4_lane")),
        ("Semrush lane", lifecycle.get("semrush_lane")),
        ("AI-citation lane", lifecycle.get("ai_citation_lane")),
        ("Decision", lifecycle.get("decision")),
        ("Status", lifecycle.get("status")),
    )
    blocks = []
    for heading, fields in (
        ("Search Intent and Format Decision", search_fields),
        ("Commercial Pillar and Anchor Decision", commercial_fields),
        ("Lifecycle Refresh Record", lifecycle_fields),
    ):
        blocks.append("## " + heading + "\n" + "\n".join(f"- {key}: {text(value)}" for key, value in fields))
    return "\n\n".join(blocks) + "\n"


def _context_findings(
    request: Mapping[str, Any] | None,
    content: str,
) -> list[Finding]:
    if request is None:
        return []
    frontmatter = legacy_guard.extract_frontmatter(content)
    scope = request.get("scope")
    if not isinstance(scope, Mapping):
        return [legacy_guard._finding("blog_strategy_context_request_invalid", 1, "Context request scope must be an object.")]
    findings: list[Finding] = []
    brand = str(frontmatter.get("brand") or "").strip()
    market = str(frontmatter.get("market") or frontmatter.get("region") or "").strip().upper()
    request_brand = str(scope.get("brand") or "").strip()
    request_market = str(scope.get("region") or scope.get("market") or "").strip().upper()
    if request_brand and request_brand.casefold() != brand.casefold():
        findings.append(legacy_guard._finding("blog_strategy_context_brand_mismatch", 1, "Context request brand does not match article Brand."))
    if request_market and request_market != market:
        findings.append(legacy_guard._finding("blog_strategy_context_market_mismatch", 1, "Context request region does not match article Market."))
    return findings


__all__ = ["check_content"]
