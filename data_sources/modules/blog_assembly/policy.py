"""Policy responsibilities."""
import copy
from datetime import date
from pathlib import Path
from typing import Any, Mapping

from .common import (
    PublishableMarkdown,
    blog_identity_guard,
    context_binding_guard,
    detect_faq_structure,
    inspect_item_list_schema,
    inspect_video_embeds,
    is_named_person,
)
from ..editorial_plan.plan_validation import check_plan as check_editorial_plan
from .contracts import (
    _required_article_scalar,
    _required_mapping,
    _required_string,
    _string_list,
)


def _validate_article_identity(article: PublishableMarkdown, assembled: date) -> None:
    kind = context_binding_guard.require_artifact_kind(
        article.raw,
        article_path=article.path,
    )
    if kind != "blog":
        raise ValueError("blog assembly BOM can only bind artifact_type blog")
    findings = blog_identity_guard.check_article(article.raw, assembly_date=assembled)
    if findings:
        raise ValueError(
            "blog identity is invalid: "
            + ", ".join(str(finding["rule_id"]) for finding in findings)
        )

def _identity_from_article(article: PublishableMarkdown) -> dict[str, str]:
    return {
        field: _required_article_scalar(article, field)
        for field in (
            "artifact_type",
            "brand",
            "title",
            "objective",
            "audience",
            "region",
            "last_updated",
        )
    }

def _author_policy(article: PublishableMarkdown) -> dict[str, Any]:
    author = article.scalar("author")
    named = bool(author)
    if named and not is_named_person(author):
        raise ValueError(
            "article.author must identify a named person, not an organization, team, or role byline"
        )
    return {
        "status": "named_author" if named else "no_author",
        "name": author if named else "",
        "frontmatter_author_required": named,
        "schema_person_required": named,
        "named_author_voice_allowed": named,
    }

def _schema_policy(article: PublishableMarkdown) -> dict[str, Any]:
    declared = article.values("schema_notes")
    item_list = inspect_item_list_schema(declared, article.metadata)
    if item_list.errors:
        raise ValueError(
            "invalid ItemList schema metadata: " + "; ".join(item_list.errors)
        )
    faq = detect_faq_structure(article.raw)
    if faq.unsupported_lines:
        raise ValueError(
            "FAQ-like details or bold-question markup is unsupported; use a recognized FAQ H2 with question headings"
        )
    questions = [entry.question for entry in faq.entries]
    video_inspection = inspect_video_embeds(article.raw)
    if video_inspection.errors:
        raise ValueError("invalid video embed: " + "; ".join(video_inspection.errors))
    video = video_inspection.has_supported_embed
    author = is_named_person(article.scalar("author"))
    required = [
        "BlogPosting",
        "BreadcrumbList",
        "ImageObject for the featured image or logo",
        "Organization as publisher reference only, not a separate full schema block",
    ]
    if faq.heading_present:
        required.extend(("FAQPage", "Question and Answer inside FAQPage"))
    if author:
        required.append("Person as author")
    if video:
        required.append("VideoObject")
    if item_list.note:
        required.append(item_list.note)
    return {
        "declared_entities": declared,
        "required_entities": required,
        "visible_faq": faq.heading_present,
        "faq_questions": questions,
        "video_embed": video,
    }

def _derive_paa_policy(
    plan: Mapping[str, Any],
    *,
    workflow_mode: str,
    paa_artifact_path: str | Path | None,
    content_brief_path: str | Path | None,
    user_paa_csv_path: str | Path | None,
    answersocrates_blocker_path: str | Path | None,
) -> dict[str, Any]:
    declared = _required_mapping(plan.get("paa_policy"), "editorial_plan.paa_policy")
    source_kind = _required_string(declared.get("source_kind"), "paa_policy.source_kind")
    if source_kind not in {"answersocrates", "brief_paa", "user_csv"}:
        raise ValueError(
            "paa_policy.source_kind must be answersocrates, brief_paa, or user_csv"
        )
    selected = _string_list(declared.get("selected_questions"), "paa_policy.selected_questions")
    query = _required_string(declared.get("query"), "paa_policy.query")
    if workflow_mode == "new" and source_kind not in {"answersocrates", "user_csv"}:
        raise ValueError("new blog PAA policy must bind AnswerSocrates or a blocked-state user CSV")
    if workflow_mode == "rewrite" and source_kind == "brief_paa" and not content_brief_path:
        raise ValueError("rewrite brief_paa policy requires content_brief_path")
    if source_kind == "answersocrates" and not paa_artifact_path:
        raise ValueError("answersocrates PAA policy requires paa_artifact_path")
    if source_kind == "user_csv" and (
        not user_paa_csv_path or not answersocrates_blocker_path
    ):
        raise ValueError(
            "user_csv PAA policy requires both user_paa_csv_path and "
            "answersocrates_blocker_path"
        )
    return {
        "source_kind": source_kind,
        "query": query,
        "selected_questions": selected,
    }

def _connector_binding(
    result: context_binding_guard.ContextValidationResult | None,
    *,
    not_applicable_reason: str | None,
) -> dict[str, Any]:
    if result is None:
        return {
            "status": "not_applicable",
            "reason": not_applicable_reason,
            "context": context_binding_guard.ContextValidationResult(
                required=False,
                findings=(),
            ).context_summary(),
        }
    return {
        "status": "required",
        "context": result.context_summary(),
    }

def _editorial_plan_summary(plan: Mapping[str, Any]) -> dict[str, Any]:
    if plan.get("schema") == "simpro-blog-editorial-plan/v2":
        return {
            "schema": plan["schema"],
            "meta": copy.deepcopy(plan["meta"]),
            "reader_contract": copy.deepcopy(plan["reader_contract"]),
            "search_strategy": copy.deepcopy(plan["search_strategy"]),
            "commercial_strategy": copy.deepcopy(plan["commercial_strategy"]),
            "lifecycle": copy.deepcopy(plan["lifecycle"]),
            "keyword_decision": copy.deepcopy(plan["keyword_decision"]),
            "original_contributions": copy.deepcopy(plan["original_contributions"]),
            "entity_map": copy.deepcopy(plan["entity_map"]),
            "internal_link_plan": copy.deepcopy(plan["internal_link_plan"]),
            "industry_cluster_link_policy": copy.deepcopy(
                plan.get(
                    "industry_cluster_link_policy",
                    {
                        "status": "not_applicable",
                        "reason": "No single-trade Simpro industry cluster link is required.",
                    },
                )
            ),
        }
    return {
        "schema": plan["schema"],
        "reader_contract": copy.deepcopy(plan["reader_contract"]),
        "serp_strategy": copy.deepcopy(plan["serp_strategy"]),
        "keyword_decision": copy.deepcopy(plan["keyword_decision"]),
        "original_contributions": copy.deepcopy(plan["original_contributions"]),
        "entity_map": copy.deepcopy(plan["entity_map"]),
        "query_ownership": copy.deepcopy(plan["query_ownership"]),
        "internal_link_plan": copy.deepcopy(plan["internal_link_plan"]),
        "industry_cluster_link_policy": copy.deepcopy(
            plan.get(
                "industry_cluster_link_policy",
                {
                    "status": "not_applicable",
                    "reason": (
                        "No single-trade Simpro industry cluster link is required."
                    ),
                },
            )
        ),
    }


def _editorial_fulfillment(
    plan: Mapping[str, Any],
    fulfillment: Mapping[str, Any],
) -> list[dict[str, str]]:
    excerpts = {
        str(row["contribution_id"]): str(row["actual_excerpt"])
        for row in fulfillment.get("contributions", [])
        if isinstance(row, Mapping)
        and isinstance(row.get("contribution_id"), str)
        and isinstance(row.get("actual_excerpt"), str)
    }
    return [
        {
            "contribution_id": str(row["contribution_id"]),
            "planned_contribution": str(row["planned_contribution"]),
            "purpose": str(row["purpose"]),
            "evidence_source": str(row["evidence_source"]),
            "target_section": str(row["target_section"]),
            "actual_excerpt": excerpts[str(row["contribution_id"])],
        }
        for row in plan.get("original_contributions", [])
        if isinstance(row, Mapping) and str(row.get("contribution_id")) in excerpts
    ]

def _validate_editorial_plan(plan: Mapping[str, Any]) -> None:
    findings = check_editorial_plan(plan)
    if findings:
        rule_ids = ", ".join(
            sorted({str(finding.get("rule_id") or "") for finding in findings})
        )
        raise ValueError(f"editorial plan is invalid: {rule_ids}")


__all__ = ['_author_policy', '_connector_binding', '_derive_paa_policy', '_editorial_fulfillment', '_editorial_plan_summary', '_identity_from_article', '_schema_policy', '_validate_article_identity', '_validate_editorial_plan']
