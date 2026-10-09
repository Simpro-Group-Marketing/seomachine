"""Write the frozen v2 editorial plan for the new What Is Simpro blog."""
from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from data_sources.modules.blog_assembly_contract import atomic_write_json  # noqa: E402


SLUG = "what-is-simpro"
DATE = "2026-10-05"
TITLE = "What Is Simpro? What Sets It Apart for Trade Businesses"
PRIMARY = "what is simpro"
SECONDARIES = ["simpro reviews", "simpro software reviews", "simpro app", "simpro features"]
PILLAR = "https://www.simprogroup.com/"
MOBILE = "https://www.simprogroup.com/features/field-service-mobile-app"
REPORTING = "https://www.simprogroup.com/features/reporting"
LIGHTNING = "https://www.simprogroup.com/lightning"
DEMO = "https://www.simprogroup.com/demo"
PRICING = "https://www.simprogroup.com/pricing"

SECTION_SPECS = [
    # number, type, heading, words, snippet, links, cta, question, payoff, angle
    (1, "intro", TITLE, 75, True, [], None,
     "What is Simpro, in one plain sentence?",
     "A direct definition plus the trades and job types it covers.",
     "Answer the query in the first sentence with vault-aligned category language."),
    (2, "body_list", "What is Simpro, stage by stage", 95, True, [], None,
     "Which part of a trade job does Simpro handle, and who uses it?",
     "A filled table that maps each job stage to what Simpro handles and the role that uses it.",
     "Give the evaluator a usable artifact inside the first 300 body words."),
    (3, "body_how_to", "How Simpro runs a job from quote to payment", 230, True, [PILLAR, MOBILE], None,
     "How does a job move through Simpro from first quote to final payment?",
     "A stage-by-stage walkthrough of quote, dispatch, field work, invoice and reporting.",
     "Explain the shared job record, the theme buyers weigh most in product fit."),
    (4, "body_explanation", "One system for service, maintenance and project work", 110, False, [], None,
     "Does Simpro handle the mix of repairs, maintenance and projects a trade business runs?",
     "A clear view of how service calls, recurring maintenance and phased projects share one record.",
     "Address multi-trade and mixed job-type fit without vertical or outcome claims."),
    (5, "body_list", "What sets Simpro apart, in users' own words", 305, False, [REPORTING], None,
     "What do people who run Simpro every day value about it?",
     "Six attributed, linked user quotes on accountability, office-to-field contact, paper-free work, owner visibility, one source of truth and quotes, jobs and invoices in one place.",
     "Answer the what-sets-it-apart question with approved review evidence instead of brand superlatives."),
    (6, "body_how_to", "What to expect from implementation and support", 140, False, [], None,
     "How much work does moving onto Simpro take?",
     "A three-stage setup, pilot and rollout table with what to prepare at each stage.",
     "Turn the implementation objection into an honest, practical plan."),
    (7, "body_list", "Is Simpro the right fit? A quick checklist", 135, False, [], None,
     "Is Simpro a fit for my business today?",
     "A fit checklist that names when Simpro fits and when a lighter tool or a later rollout fits better.",
     "Frame missing-fit and timing signals honestly so the reader self-qualifies."),
    (8, "body_how_to", "How to evaluate Simpro for your business", 150, False, [LIGHTNING, DEMO, PRICING], "commercial_conversion",
     "How do I test Simpro against my own jobs?",
     "A five-item demo-prep checklist, a walkthrough test, and the demo and pricing next steps.",
     "Move the qualified reader to a demo built around real jobs."),
    (9, "faq", "FAQs", 110, True, [], None,
     "Is Simpro a CRM, and is it a good system?",
     "Two direct answers from recorded AnswerSocrates questions, framed as a definition and a recommendation.",
     "Close common definition and evaluation questions with direct, proof-safe answers."),
    (10, "conclusion", "Find out if Simpro fits your jobs", 50, False, [], None,
     "What is the next step?",
     "A short recap and a demo next step.",
     "Restate the one-record idea and prompt a demo with real jobs."),
]


def section(spec: tuple, last: int) -> dict[str, object]:
    number, kind, heading, words, snippet, links, cta, question, payoff, angle = spec
    return {
        "section_number": number,
        "type": kind,
        "heading": heading,
        "word_target": words,
        "strategic_angle": angle,
        "engagement_hook": "The reader leaves each section with a concrete fact, quote or checklist to use in an evaluation.",
        "knowledge_gaps": [
            "What Simpro covers across a trade job and who uses each part",
            "What users who run Simpro daily value, in their own linked words",
        ],
        "unique_data": [
            "Authenticated Semrush US desktop evidence dated 2026-10-05",
            "Receipt-approved exact_quote review claims from G2 and Capterra",
        ],
        "internal_links": links,
        "cta": cta,
        "next_action": cta,
        "mini_story": False,
        "featured_snippet": snippet,
        "reader_question": question,
        "section_payoff": payoff,
        "bridge_from_previous": None if number == 1 else "Carry the previous answer into the next evaluation question.",
        "bridge_to_next": None if number == last else "Move from this answer to the next part of the evaluation.",
    }


SECTIONS = [section(spec, len(SECTION_SPECS)) for spec in SECTION_SPECS]

PLAN = {
    "schema": "simpro-blog-editorial-plan/v2",
    "brand": "Simpro",
    "topic": PRIMARY,
    "date": DATE,
    "meta": {
        "title_options": [TITLE],
        "meta_title": "What Is Simpro? How It Works and What Users Value | Simpro",
        "meta_description": "What is Simpro? See how it runs a trade job from quote to payment, what users on G2 and Capterra value, and how to judge if it fits your trade business.",
        "url_slug": SLUG,
        "primary_keyword": PRIMARY,
        "secondary_keywords": SECONDARIES,
    },
    "total_word_target": sum(spec[3] for spec in SECTION_SPECS),
    "sections": SECTIONS,
    "engagement_map": {
        "mini_stories": [],
        "ctas": {"commercial_conversion": 8},
        "featured_snippets": [1, 2, 3, 9],
        "next_actions": {"commercial_conversion": 8},
        "cta_exception_reason": None,
    },
    "gap_mapping": {
        "no ranking page explains what Simpro does across the job lifecycle": 3,
        "review-site profiles list opinions without a job-stage frame": 5,
        "buyers lack an honest fit and implementation view": 7,
    },
    "insight_mapping": {
        "the shared job record is the core idea buyers weigh": 3,
        "user evidence answers what sets Simpro apart better than brand claims": 5,
        "honest fit and setup expectations build trust before a demo": 6,
    },
    "reader_contract": {
        "primary_reader": "US trade business owners, operations leaders and office managers evaluating field service management software",
        "sophistication_level": "Commercial investigator who knows the trade business and is checking what Simpro is before a demo.",
        "trigger_problem": "Quotes, schedules, field notes and invoices sit in separate tools, and the buyer wants to know what Simpro is and why people choose it.",
        "existing_belief": "Field service software is a scheduling tool with a long feature list.",
        "decision_task_helped": "Decide whether Simpro deserves a demo built around the reader's own jobs.",
        "distinctive_angle": "A Simpro-only explainer that answers what sets it apart with linked user evidence, an honest fit checklist and an implementation plan.",
        "promised_payoff": "A job-stage table, linked user quotes, a setup plan, a fit checklist and a demo-prep list.",
        "funnel_stage": "mofu",
        "exclusions": [
            "competitor names or comparison language",
            "leader, best, better, ranking or superlative claims in Simpro's voice",
            "customer metrics, ratings or star counts",
            "case-study stories without approved claims",
            "Simpro Lightning capability or availability claims",
            "named author",
            "em dashes",
            "editorial-process language",
        ],
    },
    "original_contributions": [
        {
            "contribution_id": "job-stage-table",
            "planned_contribution": "A filled table mapping each job stage to what Simpro handles and who uses it.",
            "purpose": "Give the evaluator an early, usable artifact that defines the product by workflow.",
            "evidence_source": "Validated vault product positioning and trade services datasheet guidance.",
            "target_section": "What is Simpro, stage by stage",
        },
        {
            "contribution_id": "linked-user-quotes",
            "planned_contribution": "Six attributed user quotes, each with a same-paragraph public review link.",
            "purpose": "Answer what sets Simpro apart with first-hand user evidence.",
            "evidence_source": "Receipt-approved exact_quote claims MET-1809, MET-1816, MET-1302, MET-1849, MET-1755 and MET-1271.",
            "target_section": "What sets Simpro apart, in users' own words",
        },
        {
            "contribution_id": "implementation-stage-plan",
            "planned_contribution": "A three-stage setup, pilot and rollout table with what to prepare.",
            "purpose": "Set honest implementation expectations before a buying decision.",
            "evidence_source": "Vault implementation guidance and recurring setup themes in public reviews, used as private context.",
            "target_section": "What to expect from implementation and support",
        },
        {
            "contribution_id": "fit-checklist",
            "planned_contribution": "A fit checklist that names both strong-fit signals and when to wait or choose a lighter tool.",
            "purpose": "Help the reader self-qualify without overselling.",
            "evidence_source": "Internal Hindsight strategy themes used for framing only.",
            "target_section": "Is Simpro the right fit? A quick checklist",
        },
        {
            "contribution_id": "demo-prep-checklist",
            "planned_contribution": "A five-item demo-prep list and a walkthrough test.",
            "purpose": "Make the demo a test against the reader's own jobs.",
            "evidence_source": "Operational evaluation guidance.",
            "target_section": "How to evaluate Simpro for your business",
        },
    ],
    "entity_map": {
        "primary": [PRIMARY, *SECONDARIES, "field service management software", "trade businesses"],
        "supporting": ["quote", "scheduling", "mobile app", "invoicing", "job costing", "implementation"],
    },
    "internal_link_plan": [
        {"target": PILLAR, "role": "down_funnel", "rationale": "Verified US homepage commercial pillar for field service management software."},
        {"target": MOBILE, "role": "down_funnel", "rationale": "Feature page for the mobile app described in the field work stage."},
        {"target": REPORTING, "role": "down_funnel", "rationale": "Feature page for the reporting dashboards tied to owner visibility."},
        {"target": LIGHTNING, "role": "supporting", "rationale": "Navigation-only product context for Simpro Lightning with no capability or availability claim."},
        {"target": DEMO, "role": "down_funnel", "rationale": "Demo conversion step after the evaluation checklist."},
        {"target": PRICING, "role": "down_funnel", "rationale": "Pricing page for plan options, linked instead of stating prices."},
    ],
    "industry_cluster_link_policy": None,
    "link_policy_override": None,
    "rewrite_decisions": None,
    "audience_language_research": {
        "status": "not_applicable",
        "rationale": "The task supplies the ICP, the validated vault context supplies current US Simpro voice, and approved review claims carry user language.",
        "source_urls": [],
        "observations": [],
        "intended_section_use": [],
    },
    "keyword_decision": {
        "status": "resolved",
        "artifact_schema": "simpro-semrush-keyword-decision/v1",
        "source": "semrush_chrome_ui",
        "database": "us",
        "selected_primary_keyword": PRIMARY,
        "selected_secondary_keywords": SECONDARIES,
        "selection_rationale": "Authenticated Semrush US desktop evidence dated 2026-10-05 shows what is simpro at 90 US volume and KD 22 with informational and navigational intent. Simpro reviews and simpro software reviews support review-backed sections, while simpro software, simpro job management software and simpro pricing stay with existing commercial pages.",
    },
    "faq_policy": {
        "status": "required",
        "rationale": "The AnswerSocrates artifact supplies four questions; two have direct, proof-safe answers that fit the objective. The pricing and company-size questions lack an allowed non-owned source and are omitted.",
    },
    "paa_policy": {
        "source_kind": "answersocrates",
        "query": "simpro",
        "selected_questions": [
            "Is Simpro a CRM system?",
            "Is Simpro a good system?",
        ],
    },
    "search_strategy": {
        "primary_query": PRIMARY,
        "searcher_task": "Understand what Simpro is, how it works across a trade job, and what users value, before deciding on a demo.",
        "intent_class": "informational",
        "funnel_stage": "mofu",
        "serp_evidence_artifact": f"research/serp-evidence-{SLUG}-{DATE}.json",
        "dominant_content_type": "General Article",
        "selected_content_type": "General Article",
        "observed_serp_features": ["Sitelinks", "AI Overview", "Reviews", "People also ask"],
        "related_query_paa_artifact": f"research/paa-evidence-{SLUG}-{DATE}.json",
        "format_decision": "match_dominant",
        "exception_reason": "The general-article format matches the observed results; the explainer adds the job-stage frame and linked user evidence the ranking pages lack.",
        "status": "ready",
    },
    "commercial_strategy": {
        "article_title": TITLE,
        "article_primary_keyword": PRIMARY,
        "article_intent": "informational",
        "destination_id": "simpro-us-homepage-field-service-management-software",
        "commercial_pillar_url": PILLAR,
        "planned_anchor_text": "field service management software",
        "planned_h2_section": "How Simpro runs a job from quote to payment",
        "existing_overlapping_urls_checked": [
            PILLAR,
            "https://www.simprogroup.com/blog/best-field-service-management-software",
            "https://www.simprogroup.com/solutions/job-management-software",
            PRICING,
        ],
        "pillar_versus_blog_intent_difference": "The homepage owns the navigational brand query and the general field service management software category. This blog owns the informational what-is explainer with a job-stage walkthrough, linked user evidence, a fit checklist and an implementation plan.",
        "cannibalization_decision": "create_new",
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
        "next_review_date": "2027-01-03",
        "review_command": f"/performance-review drafts/{SLUG}-{DATE}.md",
        "gsc_lane": "unavailable: this is a new article with no first-party query-performance history",
        "ga4_lane": "unavailable: this is a new article with no engagement history",
        "semrush_lane": "available: authenticated US desktop Semrush UI evidence dated 2026-10-05",
        "ai_citation_lane": "unavailable: no AI-citation sample was collected for this assembly",
        "decision": "retain",
        "status": "scheduled",
    },
}


if __name__ == "__main__":
    output = ROOT / "research" / f"editorial-plan-{SLUG}-{DATE}.json"
    atomic_write_json(output, PLAN)
    print(f"wrote {output.relative_to(ROOT).as_posix()} total_word_target={PLAN['total_word_target']}")
