"""Write the frozen v2 editorial plan for the AI field service rewrite."""
from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from data_sources.modules.blog_assembly_contract import atomic_write_json  # noqa: E402


SLUG = "ai-for-field-service"
DATE = "2026-09-29"
TITLE = "AI in Field Service Management: How to Run Smarter, Faster, More Proactive Operations"
PRIMARY = "AI in field service management"
SECONDARIES = [
    "best AI-powered field service management software",
    "best AI-powered software for trades and field service companies",
]
PILLAR = "https://www.simprogroup.com/"


def section(
    number: int,
    kind: str,
    heading: str,
    words: int,
    snippet: bool,
    *,
    internal_links: list[str] | None = None,
    cta: str | None = None,
    next_action: str | None = None,
) -> dict[str, object]:
    return {
        "section_number": number,
        "type": kind,
        "heading": heading,
        "word_target": words,
        "strategic_angle": "Help a trade-business buyer test operational fit, connected workflows, human control, adoption, and measurable value without declaring a universal winner.",
        "engagement_hook": "The reader can convert each section into a demo question, pilot check, or purchase decision.",
        "knowledge_gaps": [
            "How to distinguish embedded operational AI from a disconnected feature list",
            "What a buyer should verify with representative jobs and baseline measures",
        ],
        "unique_data": [
            "Authenticated Semrush US desktop evidence dated 2026-09-29",
            "Receipt-validated Simpro feature and timing claims",
        ],
        "internal_links": internal_links or [],
        "cta": cta,
        "next_action": next_action,
        "mini_story": False,
        "featured_snippet": snippet,
        "reader_question": "What can I verify or decide after reading this section?",
        "section_payoff": "A concrete software-evaluation action grounded in the reader's own workflows.",
        "bridge_from_previous": None if number == 1 else "Move from the previous evaluation decision to the next operating test.",
        "bridge_to_next": None if number == 10 else "Carry the result into the next evaluation step.",
    }


SECTIONS = [
    section(1, "intro", "Opening workflow-fit frame", 90, True),
    section(2, "body_comparison", "What is the best AI-powered field service management software?", 650, True, internal_links=[PILLAR]),
    section(3, "body_explanation", "What is AI in field service management?", 220, True),
    section(4, "body_explanation", "Where AI fits across the field service job lifecycle", 480, False),
    section(5, "body_list", "Seven practical AI use cases for field service operations", 260, True),
    section(6, "body_how_to", "How to measure AI in field service management", 300, True),
    section(7, "body_list", "Six rollout gaps to resolve before purchase", 300, True),
    section(8, "body_explanation", "A practical standard for connected, supervised AI", 180, False),
    section(9, "faq", "Frequently Asked Questions", 170, True, internal_links=[PILLAR, "https://www.simprogroup.com/blog/best-field-service-management-software"]),
    section(10, "conclusion", "Run smarter with a workflow-first AI decision", 120, False, cta="commercial_conversion", next_action="commercial_conversion"),
]


PLAN = {
    "schema": "simpro-blog-editorial-plan/v2",
    "brand": "Simpro",
    "topic": PRIMARY,
    "date": DATE,
    "meta": {
        "title_options": [TITLE],
        "meta_title": "AI in Field Service Management: Practical Guide | Simpro",
        "meta_description": "Compare AI-powered field service management software, learn the criteria that matter and see where Simpro fits for trade and field service companies.",
        "url_slug": SLUG,
        "primary_keyword": PRIMARY,
        "secondary_keywords": SECONDARIES,
    },
    "total_word_target": 2770,
    "sections": SECTIONS,
    "engagement_map": {
        "mini_stories": [],
        "ctas": {"commercial_conversion": 10},
        "featured_snippets": [1, 2, 3, 5, 6, 7, 9],
        "next_actions": {"commercial_conversion": 10},
        "cta_exception_reason": None,
    },
    "gap_mapping": {
        "broad guides delay the software-selection answer": 2,
        "feature lists rarely provide equal demo tests": 2,
        "implementation and baseline measurement are separated from selection": 6,
    },
    "insight_mapping": {
        "operational fit matters more than a universal best label": 2,
        "trade buyers need an office-to-field lifecycle test": 2,
        "human oversight and measurable baselines belong in the buying decision": 6,
    },
    "reader_contract": {
        "primary_reader": "US trade-business owners, operations leaders, dispatch leaders, and software evaluators across HVAC, electrical, plumbing, fire and security, and mixed field-service operations.",
        "sophistication_level": "Commercial investigator who knows the operation and needs a defensible AI software evaluation process.",
        "trigger_problem": "AI claims are difficult to compare against the actual jobs, handoffs, users, and controls in the business.",
        "existing_belief": "The platform with the longest AI feature list is the best choice.",
        "decision_task_helped": "Decide which platforms deserve a demo and test them against the same representative workflows.",
        "distinctive_angle": "A workflow-first buying guide that adds two early buyer answers, a demo table, and a qualified Simpro fit section to the established educational page.",
        "promised_payoff": "A reusable selection table, demo questions, pilot measures, rollout checks, and a defensible shortlist decision.",
        "funnel_stage": "mofu",
        "exclusions": [
            "universal best-product claims",
            "vendor rankings",
            "unsupported customer, competitor, metric, or availability claims",
            "autonomous-action language",
            "named author",
            "em dashes",
            "editorial-process language",
        ],
    },
    "original_contributions": [
        {
            "contribution_id": "early-buyer-answer",
            "planned_contribution": "Two direct, non-duplicative selection answers before the first evaluation table.",
            "purpose": "Satisfy broad software-selection intent while preserving the page's educational ownership.",
            "evidence_source": "Current Semrush US keyword evidence, current Google SERP evidence, and operational buyer guidance.",
            "target_section": "What is the best AI-powered field service management software?",
        },
        {
            "contribution_id": "demo-selection-table",
            "planned_contribution": "A three-column table covering workflow fit, job context, field use, oversight, integrations, adoption, and value measurement.",
            "purpose": "Give buyers an equal, practical test to use across shortlisted platforms.",
            "evidence_source": "Operational evaluation framework and current authoritative AI risk-management guidance.",
            "target_section": "What is the best AI-powered field service management software?",
        },
        {
            "contribution_id": "qualified-simpro-fit",
            "planned_contribution": "A conditional Simpro shortlist explanation that stays within current receipt-approved product language.",
            "purpose": "Explain product fit without an unsupported superlative, ranking, package, or availability claim.",
            "evidence_source": "Validated Simpro vault context and approved claims LCUR-0028 and LCUR-0030.",
            "target_section": "What is the best AI-powered field service management software?",
        },
        {
            "contribution_id": "restored-faq",
            "planned_contribution": "A short FAQ section using selected AnswerSocrates questions and proof-safe answers.",
            "purpose": "Restore the FAQ lane requested by the user without adding unsupported rankings or replacement claims.",
            "evidence_source": "AnswerSocrates artifact dated 2026-09-29 and FAQ proof map.",
            "target_section": "Frequently Asked Questions",
        },
    ],
    "entity_map": {
        "primary": [PRIMARY, *SECONDARIES, "field service management software", "trade businesses"],
        "supporting": ["scheduling", "field documentation", "human oversight", "integrations", "implementation", "baseline metrics"],
    },
    "internal_link_plan": [
        {"target": PILLAR, "role": "down_funnel", "rationale": "Verified US homepage commercial pillar for field service management software."},
        {"target": "https://www.simprogroup.com/lightning", "role": "supporting", "rationale": "Current navigation-only product context for Simpro Lightning."},
        {"target": "https://www.simprogroup.com/blog/ai-features-field-service-software", "role": "supporting", "rationale": "Capability-level AI evaluation guidance."},
        {"target": "https://www.simprogroup.com/demo", "role": "down_funnel", "rationale": "Final demo CTA after the reader has a selection framework."},
        {"target": "https://www.simprogroup.com/blog/best-field-service-management-software", "role": "supporting", "rationale": "User-requested FAQ restoration needs proof-safe support for list-style FSM research."},
    ],
    "industry_cluster_link_policy": None,
    "link_policy_override": None,
    "rewrite_decisions": {
        "preserve": [
            {"item": "canonical URL and H1", "decision": "Keep accumulated ownership for AI in field service management."},
            {"item": "educational lifecycle, use-case, measurement, rollout, future-state, and conclusion sections", "decision": "Retain and tighten the useful workflow-first guidance."},
            {"item": "four existing image sources and placements", "decision": "Retain as standalone placeholders with keyword-bearing filenames and accurate alt text."},
        ],
        "update": [
            {"item": "opening", "decision": "Replace unsupported metric-led copy with an evidence-safe operational-fit frame."},
            {"item": "software-selection intent", "decision": "Add both exact prompt headings, direct answers, the evaluation table, and qualified Simpro fit near the top."},
            {"item": "claim treatment", "decision": "Remove or qualify unsupported performance, outcome, and autonomy statements."},
        ],
        "add": [
            {"item": "buyer answer block", "decision": "Place a usable checklist table within the first 300 public body words."},
            {"item": "schema notes", "decision": "Declare BlogPosting, BreadcrumbList, FAQPage, Question and Answer inside FAQPage, ImageObject, and Organization as publisher reference only."},
            {"item": "FAQ section", "decision": "Restore a short FAQ section from eligible AnswerSocrates questions after the user requested the original FAQ lane."},
        ],
        "remove": [
            {"item": "unsupported benchmarks and projections", "decision": "Do not retain profit, speed, first-time-fix, paperwork, payment, dispute, or autonomous-action claims without qualifying evidence."},
        ],
    },
    "audience_language_research": {
        "status": "not_applicable",
        "rationale": "The user supplied the ICP, and current vault resources supplied approved Simpro editorial and product language.",
        "source_urls": [],
        "observations": [],
        "intended_section_use": [],
    },
    "keyword_decision": {
        "status": "resolved",
        "artifact_schema": "simpro-semrush-keyword-decision/v1",
        "source": "semrush_connector",
        "database": "us",
        "selected_primary_keyword": PRIMARY,
        "selected_secondary_keywords": SECONDARIES,
        "selection_rationale": "Fresh authenticated Semrush US desktop evidence dated 2026-09-29 confirms 260 volume, KD 34, and informational intent for the established primary. The requested software-selection prompts are secondary commercial-investigation targets because direct exact-query demand is limited or unavailable.",
    },
    "faq_policy": {
        "status": "required",
        "rationale": "The required AnswerSocrates artifact was collected and the user requested restoring the FAQ lane after live-page backup.",
    },
    "paa_policy": {
        "source_kind": "answersocrates",
        "query": "AI-powered field service management software",
        "selected_questions": [
            "What is the best software for field service management?",
            "What are the top 10 field service management software?",
            "Will CRM be replaced by AI?",
        ],
    },
    "search_strategy": {
        "primary_query": PRIMARY,
        "searcher_task": "Understand AI in field service management, compare AI-powered FSM options, and decide which products deserve a workflow-based demo.",
        "intent_class": "informational",
        "funnel_stage": "mofu",
        "serp_evidence_artifact": "research/serp-evidence-ai-for-field-service-2026-09-29.json",
        "dominant_content_type": "General Article",
        "selected_content_type": "General Article",
        "observed_serp_features": ["Ads", "AI Overview", "People also ask"],
        "related_query_paa_artifact": "research/paa-evidence-ai-for-field-service-2026-09-29.json",
        "format_decision": "match_dominant",
        "exception_reason": "The established guide format remains dominant; early commercial-selection answers improve buyer utility without turning the page into a vendor ranking.",
        "status": "ready",
    },
    "commercial_strategy": {
        "article_title": TITLE,
        "article_primary_keyword": PRIMARY,
        "article_intent": "informational",
        "destination_id": "simpro-us-homepage-field-service-management-software",
        "commercial_pillar_url": PILLAR,
        "planned_anchor_text": "field service management software",
        "planned_h2_section": "What is the best AI-powered field service management software?",
        "existing_overlapping_urls_checked": [
            "https://www.simprogroup.com/blog/ai-for-field-service",
            "https://www.simprogroup.com/blog/best-field-service-management-software",
            "https://www.simprogroup.com/blog/ai-features-field-service-software",
            "https://www.simprogroup.com/blog/ai-scheduling-dispatch-field-service",
            "https://www.simprogroup.com/blog/agentic-ai-for-field-service",
            PILLAR,
        ],
        "pillar_versus_blog_intent_difference": "The homepage owns the broad field service management software category. This blog owns AI-in-FSM education and broad AI-powered software evaluation. The generic comparison keeps non-AI best-software selection, while feature, scheduling, and agent articles keep narrower capability intents.",
        "cannibalization_decision": "update_existing",
        "incoming_link_candidates": [
            "https://www.simprogroup.com/blog/best-field-service-management-software",
            "https://www.simprogroup.com/blog/ai-features-field-service-software",
            PILLAR,
        ],
        "status": "aligned",
    },
    "lifecycle": {
        "last_updated_date": DATE,
        "volatility": "high",
        "next_review_date": "2026-12-28",
        "review_command": "/performance-review https://www.simprogroup.com/blog/ai-for-field-service",
        "gsc_lane": "available: current internal baseline supplied as 27.4K impressions and average position 8.8; verify the same page and query set at 30, 60, and 90 days without claiming causation",
        "ga4_lane": "unavailable: no fresh GA4 export was collected for this rewrite; do not infer engagement performance",
        "semrush_lane": "available: authenticated US desktop Semrush UI and current US Google SERP capture dated 2026-09-29",
        "ai_citation_lane": "unavailable: no current live AI-surface sample was collected; historical prompt observations and the request-supplied Peec baseline remain internal context only",
        "decision": "update",
        "status": "scheduled",
    },
}


if __name__ == "__main__":
    output = ROOT / "research" / f"editorial-plan-{SLUG}-{DATE}.json"
    atomic_write_json(output, PLAN)
    print(f"wrote {output.relative_to(ROOT).as_posix()}")
