"""Editorial plan payload for the PR-led field-service visibility rewrite."""

from __future__ import annotations

from scripts.operational_accountability_pr_led_data import (
    DATE,
    FAQ_QUESTIONS,
    FEATURES,
    PAA_ARTIFACT,
    PLAN_SECTIONS,
    SELECTED_SECONDARY_KEYWORDS,
    SERP_EVIDENCE,
)


def plan_payload() -> dict[str, object]:
    plan = {
        "schema": "simpro-blog-editorial-plan/v2",
        "brand": "Simpro",
        "topic": "field service operations software visibility",
        "date": DATE,
        "total_word_target": 1990,
        "meta": {
            "title_options": [
                "How Field Service Operations Software Helps You Stay Close to the Work",
            ],
            "meta_title": "Stay Close to Field Service Work | Simpro",
            "meta_description": (
                "See how field service software gives owners visibility across dispatch, "
                "closeout, invoicing, callbacks, and margin so they can improve "
                "productivity and profitability."
            ),
            "url_slug": "operational-accountability-field-service",
            "primary_keyword": "field service operations software",
            "secondary_keywords": [
                *SELECTED_SECONDARY_KEYWORDS,
            ],
        },
        "reader_contract": {
            "primary_reader": (
                "US field-service owners, general managers, operations managers, "
                "service managers and dispatch leaders."
            ),
            "sophistication_level": (
                "Operational leaders who already manage dispatch, closeout, invoicing, "
                "callbacks, quote follow-up and margin review."
            ),
            "trigger_problem": (
                "Important work signals are spread across people, tools, inboxes and "
                "reports, so owners see problems after productivity, cash flow, margin "
                "or customer experience has already been affected."
            ),
            "existing_belief": (
                "Staying close to the work requires more status chasing or more people "
                "oversight."
            ),
            "decision_task_helped": (
                "Choose one workflow, define the signal that shows drift and review "
                "exceptions from a connected operating record."
            ),
            "distinctive_angle": (
                "Simpro helps owners stay close to live work through connected workflow "
                "visibility rather than people-management theory."
            ),
            "promised_payoff": (
                "A practical operating view for protecting productivity, profitability, "
                "cash flow, customer experience and margin."
            ),
            "funnel_stage": "thought leadership",
            "exclusions": [
                "people-accountability positioning",
                "supervision or employee-performance advice",
                "digital-worker framing",
                "AI-agent taxonomy",
                "unsupported Fred quotes or transcript paraphrases",
                "customer metrics or testimonials",
            ],
        },
        "search_strategy": {
            "primary_query": "field service operations software",
            "searcher_task": (
                "Understand how software supports field service operations and helps "
                "owners see work status, exceptions and workflow handoffs."
            ),
            "intent_class": "mixed",
            "funnel_stage": "thought_leadership",
            "serp_evidence_artifact": f"research/{SERP_EVIDENCE.name}",
            "dominant_content_type": "Listicle",
            "selected_content_type": "software visibility guide",
            "observed_serp_features": FEATURES,
            "related_query_paa_artifact": f"research/{PAA_ARTIFACT.name}",
            "format_decision": "documented_exception",
            "exception_reason": (
                "The live SERP shows software list, review and vendor-page intent, but "
                "the PR-led rewrite must answer a narrower owner problem: staying close "
                "to active field-service work through connected workflow visibility."
            ),
            "status": "ready",
        },
        "commercial_strategy": {
            "article_title": "How Field Service Operations Software Helps You Stay Close to the Work",
            "article_primary_keyword": "field service operations software",
            "article_intent": "mixed",
            "destination_id": "simpro-us-homepage-field-service-management-software",
            "commercial_pillar_url": "https://www.simprogroup.com/",
            "planned_anchor_text": "field service management software",
            "planned_h2_section": "Start with one operating record",
            "existing_overlapping_urls_checked": [
                "https://www.simprogroup.com/",
                "https://www.simprogroup.com/blog/field-service-operations",
                "https://www.simprogroup.com/blog/best-field-service-management-software",
                "https://www.simprogroup.com/blog/holding-people-accountable-without-micromanaging",
            ],
            "pillar_versus_blog_intent_difference": (
                "The homepage owns the broad commercial field service management "
                "software query. This article is a PR-led software visibility guide "
                "for field-service owners who need an operating view of active work."
            ),
            "cannibalization_decision": "different_intent",
            "incoming_link_candidates": [
                "https://www.simprogroup.com/",
                "https://www.simprogroup.com/blog/field-service-operations",
                "https://www.simprogroup.com/blog/field-service-metrics",
                "https://www.simprogroup.com/blog/best-field-service-management-software",
            ],
            "status": "aligned",
        },
        "lifecycle": {
            "last_updated_date": DATE,
            "volatility": "standard",
            "next_review_date": "2027-03-22",
            "review_command": (
                "/performance-review published/operational-accountability-field-service-2026-09-17.md"
            ),
            "gsc_lane": "unavailable: rewritten article has no post-publication query data for the revised PR-led angle",
            "ga4_lane": "unavailable: rewritten article has no post-publication engagement data for the revised PR-led angle",
            "semrush_lane": "available: current Semrush UI keyword decision captured on 2026-09-23",
            "ai_citation_lane": "unavailable: no post-publication AI citation tracking exists for this rewrite",
            "decision": "update",
            "status": "scheduled",
        },
        "sections": PLAN_SECTIONS,
        "engagement_map": {
            "mini_stories": [],
            "ctas": {"commercial_contextual": 7},
            "featured_snippets": [1, 3, 6, 9],
            "next_actions": {"thought_leadership_next_action": 8},
            "cta_exception_reason": None,
        },
        "gap_mapping": {
            "software visibility instead of people management": 1,
            "single operating record": 2,
            "leading workflow signals": 3,
            "public executive context": 4,
            "handoff drift examples": 5,
            "exception cadence": 6,
            "Simpro source-safe product tie-back": 7,
            "one-workflow next action": 8,
            "revised software FAQ set": 9,
        },
        "insight_mapping": {
            "connected software helps owners stay close to live work": 1,
            "the operating record reduces blind spots across office and field workflows": 2,
            "visibility protects productivity and margin before lagging results appear": 3,
            "Fred PR appears only as executive context": 4,
            "drift starts in handoffs": 5,
            "exceptions create a usable operating rhythm": 6,
            "Simpro connects the work through approved platform language": 7,
            "a narrow weekly test makes the guidance actionable": 8,
            "PAA answers reinforce software intent": 9,
        },
        "original_contributions": [
            {
                "contribution_id": "workflow-signal-table",
                "planned_contribution": (
                    "A six-row early artifact mapping field-service workflow areas to visibility signals and business impact."
                ),
                "purpose": "Give readers usable operating guidance within the first 300 words.",
                "evidence_source": "PR-led brief, live Semrush UI keyword decision, AnswerSocrates capture and current SERP evidence.",
                "target_section": "How Field Service Operations Software Helps You Stay Close to the Work",
            },
            {
                "contribution_id": "simpro-operating-record",
                "planned_contribution": (
                    "A first-H2 Simpro/software tie-back positioning connected office-field workflow visibility as the operating record."
                ),
                "purpose": "Address Millie's feedback by tying the leadership lens to software value immediately.",
                "evidence_source": "Vault-approved Simpro positioning and homepage commercial-pillar routing.",
                "target_section": "Start with one operating record",
            },
            {
                "contribution_id": "exception-view-cadence",
                "planned_contribution": (
                    "A daily, weekly and monthly exception-view cadence that avoids people-performance framing."
                ),
                "purpose": "Translate workflow visibility into an operating rhythm.",
                "evidence_source": "PR-led editorial direction and field-service workflow examples.",
                "target_section": "Build a daily exception view",
            },
            {
                "contribution_id": "pr-authority-context",
                "planned_contribution": (
                    "An executive authority section using the two Fred PR appearances as context without unsupported quotes."
                ),
                "purpose": "Preserve E-E-A-T while removing accountability and supervision as the article promise.",
                "evidence_source": "Fred authority selector and claim registry decisions claim-fred-FVMI-0015 and claim-fred-FVMI-0016.",
                "target_section": "The executive context behind staying close to the work",
            },
        ],
        "entity_map": {
            "primary": [
                "field service operations software",
                "field service software",
                "workflow visibility",
                "operating record",
                "field service operations",
            ],
            "supporting": [
                "dispatch readiness",
                "job closeout",
                "callbacks",
                "invoicing blockers",
                "margin drift",
                "quote follow-up",
                "cash flow",
                "customer experience",
                "Simpro",
                "Fred Voccola",
            ],
        },
        "internal_link_plan": [
            {
                "target": "https://www.simprogroup.com/",
                "role": "down_funnel",
                "rationale": (
                    "Homepage is the verified US commercial pillar for field service management software and appears in the planned first H2."
                ),
            },
            {
                "target": "https://www.simprogroup.com/blog/field-service-operations",
                "role": "supporting",
                "rationale": "Supports the broader operations lifecycle without taking over the revised software-visibility angle.",
            },
            {
                "target": "https://www.simprogroup.com/blog/field-service-metrics",
                "role": "supporting",
                "rationale": "Supports the distinction between workflow signals and business results.",
            },
            {
                "target": "https://www.simprogroup.com/blog/best-field-service-management-software",
                "role": "supporting",
                "rationale": "Supports the PAA question about selecting field service management software.",
            },
        ],
        "industry_cluster_link_policy": {
            "status": "not_applicable",
            "rationale": "The article is cross-trade field-service operations guidance rather than a single-trade industry article.",
        },
        "keyword_decision": {
            "status": "resolved",
            "artifact_schema": "simpro-semrush-keyword-decision/v1",
            "source": "semrush_connector",
            "database": "us",
            "selected_primary_keyword": "field service operations software",
            "selected_secondary_keywords": [
                *SELECTED_SECONDARY_KEYWORDS,
            ],
            "selection_rationale": (
                "Authenticated Semrush UI in the main Chrome browser selected field service operations software because it has current US demand, fits the software-visibility PR direction and avoids the exact commercial-pillar collision."
            ),
        },
        "faq_policy": {
            "status": "required",
            "rationale": "AnswerSocrates and visible Google PAA showed software definition, best-software and CRM-versus-FSM questions for the revised keyword.",
        },
        "paa_policy": {
            "source_kind": "answersocrates",
            "query": "field service operations software",
            "selected_questions": FAQ_QUESTIONS,
        },
        "rewrite_decisions": {
            "preserve": [
                {"item": "Fred PR context", "decision": "Preserved as executive E-E-A-T context only."},
                {"item": "no-gradient theme image", "decision": "Retained as the featured image placeholder source."},
            ],
            "update": [
                {"item": "H1 and metadata", "decision": "Updated to software visibility and staying close to the work."},
                {"item": "FAQs", "decision": "Replaced accountability FAQs with revised software/PAA questions."},
            ],
            "add": [
                {"item": "operating-record first H2", "decision": "Added immediate Simpro/software tie-back."},
                {"item": "daily exception view", "decision": "Added workflow visibility cadence."},
            ],
            "remove": [
                {"item": "people accountability promise", "decision": "Removed as a primary reader promise."},
                {"item": "digital-worker framing", "decision": "Removed by user direction."},
            ],
        },
    }
    return plan
