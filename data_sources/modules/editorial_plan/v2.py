"""Version 2 editorial-plan structure and cross-field validation."""

from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from typing import Any
import re

from .contracts import TOP_LEVEL_FIELDS
from .contracts import Finding
from .contracts import _check_string_list
from .contracts import _finding
from .contracts import _invalid_field
from .contracts import _parse_iso_date
from .contracts import _require_nonempty_string
from .contracts import _unknown_fields


EDITORIAL_PLAN_SCHEMA_V2 = "simpro-blog-editorial-plan/v2"
V2_TOP_LEVEL_FIELDS = frozenset(
    (TOP_LEVEL_FIELDS - {"serp_strategy", "query_ownership"})
    | {"search_strategy", "commercial_strategy", "lifecycle"}
)
THROUGHLINE_FIELDS = frozenset(
    {"reader_question", "section_payoff", "bridge_from_previous", "bridge_to_next"}
)
CONTRIBUTION_FIELDS = frozenset(
    {
        "contribution_id",
        "planned_contribution",
        "purpose",
        "evidence_source",
        "target_section",
    }
)
SEARCH_FIELDS = frozenset(
    {
        "primary_query",
        "searcher_task",
        "intent_class",
        "funnel_stage",
        "serp_evidence_artifact",
        "dominant_content_type",
        "selected_content_type",
        "observed_serp_features",
        "related_query_paa_artifact",
        "format_decision",
        "exception_reason",
        "status",
    }
)
COMMERCIAL_FIELDS = frozenset(
    {
        "article_title",
        "article_primary_keyword",
        "article_intent",
        "destination_id",
        "commercial_pillar_url",
        "planned_anchor_text",
        "planned_h2_section",
        "existing_overlapping_urls_checked",
        "pillar_versus_blog_intent_difference",
        "cannibalization_decision",
        "incoming_link_candidates",
        "status",
    }
)
LIFECYCLE_FIELDS = frozenset(
    {
        "last_updated_date",
        "volatility",
        "next_review_date",
        "review_command",
        "gsc_lane",
        "ga4_lane",
        "semrush_lane",
        "ai_citation_lane",
        "decision",
        "status",
    }
)
INTENTS = frozenset({"informational", "commercial", "transactional", "navigational", "mixed"})
FUNNELS = frozenset({"tofu", "mofu", "bofu", "thought_leadership"})
CONTRIBUTION_ID_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
PLACEHOLDER_RE = re.compile(
    r"(?:\b(?:tbd|todo|placeholder|fill[ -]?in|insert here|unknown)\b|\[(?:insert|add|describe)[^]]*])",
    re.IGNORECASE,
)


def adapt_to_v1(value: Mapping[str, Any]) -> dict[str, Any]:
    """Return a v1-shaped copy so common legacy field checks stay shared."""
    adapted = deepcopy(dict(value))
    adapted["schema"] = "simpro-blog-editorial-plan/v1"
    adapted.pop("search_strategy", None)
    adapted.pop("commercial_strategy", None)
    adapted.pop("lifecycle", None)
    adapted["serp_strategy"] = {
        "status": "unresolved_no_verified_serp_context",
        "content_type": {"observed": None, "selected": None, "status": "not_claimed"},
        "serp_features": {},
        "serp_structure": {},
        "competitor_gaps": {},
        "exception_reasons": {
            "content_type": {},
            "serp_features": {},
            "serp_structure": {},
            "competitor_gaps": {},
        },
    }
    adapted["query_ownership"] = {
        "decision": "clear",
        "rationale": "Validated by the v2 commercial strategy.",
    }
    adapted["sections"] = [
        {key: item for key, item in section.items() if key not in THROUGHLINE_FIELDS}
        if isinstance(section, Mapping)
        else section
        for section in adapted.get("sections", [])
    ]
    adapted["original_contributions"] = [
        {
            "description": row.get("planned_contribution", ""),
            "final_section": row.get("target_section", ""),
            "visible_evidence": "Validated later by plan fulfillment evidence.",
        }
        if isinstance(row, Mapping)
        else row
        for row in adapted.get("original_contributions", [])
    ]
    return adapted


def check_v2(value: Mapping[str, Any]) -> list[Finding]:
    findings = _unknown_fields(value, V2_TOP_LEVEL_FIELDS, "")
    findings.extend(_check_sections(value.get("sections")))
    findings.extend(_check_contributions(value.get("original_contributions")))
    findings.extend(_check_search(value.get("search_strategy")))
    findings.extend(_check_commercial(value.get("commercial_strategy")))
    findings.extend(_check_lifecycle(value.get("lifecycle")))
    findings.extend(_check_agreement(value))
    return findings


def check_search_evidence_binding(
    strategy: Mapping[str, Any],
    evidence: Mapping[str, Any],
) -> list[Finding]:
    """Bind v2 search decisions to observations in verified SERP evidence."""
    observations = evidence.get("observations")
    if not isinstance(observations, Mapping):
        return []
    evidence_types = _normalized_strings(observations.get("content_types"))
    evidence_features = _normalized_strings(observations.get("serp_features"))
    findings: list[Finding] = []
    dominant = _normalized(strategy.get("dominant_content_type"))
    if not dominant or dominant not in evidence_types:
        findings.append(_unbound("dominant_content_type"))
    planned_features = _normalized_strings(strategy.get("observed_serp_features"))
    if not planned_features.issubset(evidence_features):
        findings.append(_unbound("observed_serp_features"))
    selected = _normalized(strategy.get("selected_content_type"))
    if strategy.get("format_decision") == "match_dominant" and selected != dominant:
        findings.append(_mismatch("/search_strategy/selected_content_type"))
    return findings


def _check_sections(value: Any) -> list[Finding]:
    if not isinstance(value, list):
        return []
    findings: list[Finding] = []
    last = len(value) - 1
    for index, row in enumerate(value):
        if not isinstance(row, Mapping):
            continue
        location = f"/sections/{index}"
        allowed = frozenset(set(row) - THROUGHLINE_FIELDS) | THROUGHLINE_FIELDS
        findings.extend(_unknown_fields(row, allowed, location))
        for key in ("reader_question", "section_payoff"):
            _require_nonempty_string(row, key, findings, f"{location}/{key}")
        if index > 0 and not _nonempty(row.get("bridge_from_previous")):
            findings.append(_bridge_finding(location, "bridge_from_previous"))
        elif index == 0:
            findings.extend(_nullable_string(row.get("bridge_from_previous"), f"{location}/bridge_from_previous"))
        if index < last and not _nonempty(row.get("bridge_to_next")):
            findings.append(_bridge_finding(location, "bridge_to_next"))
        elif index == last:
            findings.extend(_nullable_string(row.get("bridge_to_next"), f"{location}/bridge_to_next"))
    return findings


def _check_contributions(value: Any) -> list[Finding]:
    location = "/original_contributions"
    if not isinstance(value, list) or not value:
        return [_invalid_field(location, "must be a non-empty list")]
    findings: list[Finding] = []
    seen: set[str] = set()
    for index, row in enumerate(value):
        row_location = f"{location}/{index}"
        if not isinstance(row, Mapping):
            findings.append(_invalid_field(row_location, "must be an object"))
            continue
        findings.extend(_unknown_fields(row, CONTRIBUTION_FIELDS, row_location))
        for key in CONTRIBUTION_FIELDS:
            _require_nonempty_string(row, key, findings, f"{row_location}/{key}")
        contribution_id = row.get("contribution_id")
        if isinstance(contribution_id, str):
            if CONTRIBUTION_ID_RE.fullmatch(contribution_id) is None:
                findings.append(_finding(
                    "editorial_plan_contribution_id_invalid",
                    "Contribution IDs must be lowercase kebab-case identifiers.",
                    f"{row_location}/contribution_id",
                    "Assign a stable lowercase kebab-case contribution ID.",
                ))
            elif contribution_id in seen:
                findings.append(_finding(
                    "editorial_plan_contribution_id_duplicate",
                    f"Contribution ID is duplicated: {contribution_id}.",
                    f"{row_location}/contribution_id",
                    "Assign one unique ID to every planned contribution.",
                ))
            seen.add(contribution_id)
        findings.extend(_placeholder_findings(row, row_location))
    return findings


def _check_search(value: Any) -> list[Finding]:
    findings = _object_shape(value, SEARCH_FIELDS, "/search_strategy")
    if not isinstance(value, Mapping):
        return findings
    findings.extend(_enum(value, "intent_class", INTENTS, "/search_strategy"))
    findings.extend(_enum(value, "funnel_stage", FUNNELS, "/search_strategy"))
    findings.extend(_enum(value, "format_decision", {"match_dominant", "documented_exception"}, "/search_strategy"))
    findings.extend(_check_string_list(value.get("observed_serp_features"), "/search_strategy/observed_serp_features"))
    if value.get("status") != "ready":
        findings.append(_blocked("search", "/search_strategy/status"))
    if value.get("format_decision") == "documented_exception" and _normalized(value.get("exception_reason")) == "none":
        findings.append(_invalid_field("/search_strategy/exception_reason", "must explain a documented exception"))
    findings.extend(_placeholder_findings(value, "/search_strategy"))
    return findings


def _check_commercial(value: Any) -> list[Finding]:
    findings = _object_shape(value, COMMERCIAL_FIELDS, "/commercial_strategy")
    if not isinstance(value, Mapping):
        return findings
    findings.extend(_enum(value, "article_intent", INTENTS, "/commercial_strategy"))
    findings.extend(_enum(value, "cannibalization_decision", {"create_new", "different_intent", "update_existing", "consolidate"}, "/commercial_strategy"))
    for key in ("existing_overlapping_urls_checked", "incoming_link_candidates"):
        findings.extend(_check_string_list(value.get(key), f"/commercial_strategy/{key}", required=True))
    if value.get("status") != "aligned":
        findings.append(_blocked("commercial", "/commercial_strategy/status"))
    findings.extend(_placeholder_findings(value, "/commercial_strategy"))
    return findings


def _check_lifecycle(value: Any) -> list[Finding]:
    findings = _object_shape(value, LIFECYCLE_FIELDS, "/lifecycle")
    if not isinstance(value, Mapping):
        return findings
    findings.extend(_enum(value, "volatility", {"high", "standard"}, "/lifecycle"))
    findings.extend(_enum(value, "decision", {"retain", "refresh", "update", "consolidate"}, "/lifecycle"))
    if value.get("status") != "scheduled":
        findings.append(_blocked("lifecycle", "/lifecycle/status"))
    updated = _parse_iso_date(value.get("last_updated_date"))
    review = _parse_iso_date(value.get("next_review_date"))
    if updated is None or review is None or review <= updated:
        findings.append(_finding(
            "editorial_plan_lifecycle_date_invalid",
            "Lifecycle dates must be canonical ISO dates with review after last update.",
            "/lifecycle/next_review_date",
            "Schedule a future review from the verified last-updated date.",
        ))
    findings.extend(_placeholder_findings(value, "/lifecycle"))
    return findings


def _check_agreement(plan: Mapping[str, Any]) -> list[Finding]:
    meta = plan.get("meta") if isinstance(plan.get("meta"), Mapping) else {}
    reader = plan.get("reader_contract") if isinstance(plan.get("reader_contract"), Mapping) else {}
    search = plan.get("search_strategy") if isinstance(plan.get("search_strategy"), Mapping) else {}
    commercial = plan.get("commercial_strategy") if isinstance(plan.get("commercial_strategy"), Mapping) else {}
    lifecycle = plan.get("lifecycle") if isinstance(plan.get("lifecycle"), Mapping) else {}
    headings = {
        str(row.get("heading")).strip().casefold()
        for row in plan.get("sections", [])
        if isinstance(row, Mapping) and _nonempty(row.get("heading"))
    }
    comparisons = (
        (_normalized(search.get("primary_query")), _normalized(meta.get("primary_keyword")), "/search_strategy/primary_query"),
        (_normalized(search.get("funnel_stage")).replace(" ", "_"), _normalized(reader.get("funnel_stage")).replace(" ", "_"), "/search_strategy/funnel_stage"),
        (_normalized(commercial.get("article_primary_keyword")), _normalized(meta.get("primary_keyword")), "/commercial_strategy/article_primary_keyword"),
        (_normalized(commercial.get("article_intent")), _normalized(search.get("intent_class")), "/commercial_strategy/article_intent"),
        (_normalized(lifecycle.get("last_updated_date")), _normalized(plan.get("date")), "/lifecycle/last_updated_date"),
    )
    findings = [_mismatch(location) for left, right, location in comparisons if left and right and left != right]
    titles = meta.get("title_options") if isinstance(meta.get("title_options"), list) else []
    if commercial.get("article_title") not in titles:
        findings.append(_mismatch("/commercial_strategy/article_title"))
    planned_h2 = _normalized(commercial.get("planned_h2_section"))
    if planned_h2 and planned_h2 not in headings:
        findings.append(_mismatch("/commercial_strategy/planned_h2_section"))
    for index, contribution in enumerate(plan.get("original_contributions", [])):
        if isinstance(contribution, Mapping):
            target = _normalized(contribution.get("target_section"))
            if target and target not in headings:
                findings.append(_mismatch(f"/original_contributions/{index}/target_section"))
    return findings


def _object_shape(value: Any, fields: frozenset[str], location: str) -> list[Finding]:
    if not isinstance(value, Mapping):
        return [_invalid_field(location, "must be an object")]
    findings = _unknown_fields(value, fields, location)
    for key in fields - {"observed_serp_features", "existing_overlapping_urls_checked", "incoming_link_candidates"}:
        _require_nonempty_string(value, key, findings, f"{location}/{key}")
    return findings


def _enum(value: Mapping[str, Any], key: str, allowed: set[str] | frozenset[str], location: str) -> list[Finding]:
    return [] if value.get(key) in allowed else [_invalid_field(f"{location}/{key}", f"must be one of {', '.join(sorted(allowed))}")]


def _placeholder_findings(value: Mapping[str, Any], location: str) -> list[Finding]:
    return [
        _finding(
            "editorial_plan_placeholder",
            f"Editorial plan field contains placeholder content: {key}.",
            f"{location}/{key}",
            "Replace the placeholder with a verified planning decision.",
        )
        for key, item in value.items()
        if isinstance(item, str) and PLACEHOLDER_RE.search(item)
    ]


def _blocked(name: str, location: str) -> Finding:
    return _finding(
        f"editorial_plan_{name}_strategy_blocked" if name != "lifecycle" else "editorial_plan_lifecycle_blocked",
        f"The {name} strategy is not release-ready.",
        location,
        "Return to the owning planning command and create a new plan hash.",
    )


def _mismatch(location: str) -> Finding:
    return _finding(
        "editorial_plan_strategy_mismatch",
        "Structured strategy decisions disagree with the rest of the editorial plan.",
        location,
        "Regenerate the plan so metadata, sections, and strategy decisions agree.",
    )


def _bridge_finding(location: str, key: str) -> Finding:
    return _finding(
        "editorial_plan_section_bridge_missing",
        "Adjacent planned sections require an explicit narrative bridge.",
        f"{location}/{key}",
        "Describe the transition without prescribing final article wording.",
    )


def _nullable_string(value: Any, location: str) -> list[Finding]:
    return [] if value is None or _nonempty(value) else [_invalid_field(location, "must be null or a non-empty string")]


def _nonempty(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _normalized(value: Any) -> str:
    return re.sub(r"\s+", " ", value.strip()).casefold() if isinstance(value, str) else ""


def _normalized_strings(value: Any) -> set[str]:
    if not isinstance(value, list):
        return set()
    return {_normalized(item) for item in value if _normalized(item)}


def _unbound(field: str) -> Finding:
    return _finding(
        "editorial_plan_serp_decision_unbound",
        "The structured search decision is not present in bound SERP evidence.",
        f"/search_strategy/{field}",
        "Regenerate the plan from the current verified SERP evidence.",
    )


__all__ = [
    "EDITORIAL_PLAN_SCHEMA_V2",
    "adapt_to_v1",
    "check_search_evidence_binding",
    "check_v2",
]
