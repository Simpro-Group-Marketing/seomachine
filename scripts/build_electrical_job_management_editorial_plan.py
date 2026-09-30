"""Write the frozen v2 editorial plan for the electrical software rewrite."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from data_sources.modules.blog_assembly_contract import atomic_write_json

SLUG = "best-electrical-job-management-software"
DATE = "2026-09-28"
TITLE = "Best Electrical Job Management Software by Job Type (2026)"
PRIMARY = "electrical job management software"
PILLAR = "https://www.simprogroup.com/industries/electrical-software"
PAA = [
    "What is the best CRM for electrical contractors?",
    "What scheduling software is best for electricians?",
    "What is the best app for electrical contractors?",
    "What is the best software for electricians to use for takeoffs?",
]
HEADINGS = [
    (1, "intro", "Opening answer and job-mix decision table", 280, True),
    (2, "body_explanation", "Which electrical job management software fits your job mix?", 180, True),
    (3, "body_explanation", "How we compared the 10 platforms", 130, False),
    (4, "body_list", "10 electrical job management software tools to compare", 1450, True),
    (5, "body_comparison", "Compare workflows, pricing and implementation", 300, True),
    (6, "body_how_to", "Score every demo against the same criteria", 350, True),
    (7, "body_how_to", "Run the same three electrical job scenarios", 380, False),
    (8, "body_how_to", "Check implementation, integrations and total cost", 350, False),
    (9, "body_how_to", "Avoid these electrical software buying mistakes", 280, False),
    (10, "faq", "Frequently asked questions", 300, True),
    (11, "conclusion", "Make your shortlist", 100, False),
]


def section(number, kind, heading, words, snippet):
    return {"section_number": number, "type": kind, "heading": heading, "word_target": words,
        "strategic_angle": "Route the buying decision by service, maintenance and project job mix, then require equal live proof from every vendor.",
        "engagement_hook": "A contractor can turn the section into a shortlist, score or demo test.",
        "knowledge_gaps": ["How job mix changes platform fit", "What the vendor must prove live"],
        "unique_data": ["Current official vendor sources checked 2026-09-28", "Job-mix evaluation framework"],
        "internal_links": [PILLAR] if number == 2 else [], "cta": "commercial_contextual" if number == 11 else None,
        "next_action": "commercial_conversion" if number == 11 else None, "mini_story": False,
        "featured_snippet": snippet, "reader_question": "What decision can I make after this section?",
        "section_payoff": "A defensible next step based on demonstrated workflow fit.",
        "bridge_from_previous": None if number == 1 else "Move from the previous decision to the next buying test.",
        "bridge_to_next": None if number == 11 else "Use the result in the next comparison step."}


SECTIONS = [section(*row) for row in HEADINGS]
PLAN = {
    "schema": "simpro-blog-editorial-plan/v2", "brand": "Simpro", "topic": PRIMARY, "date": DATE,
    "meta": {"title_options": [TITLE, "10 Best Electrical Job Management Software Tools by Job Type (2026)"], "meta_title": TITLE,
        "meta_description": "Compare 10 electrical job management software tools by service, maintenance and project fit, pricing, implementation, integrations and live demo requirements.",
        "url_slug": SLUG, "primary_keyword": PRIMARY,
        "secondary_keywords": ["electrical contractor job management software", "job management software for electrical contractors"]},
    "total_word_target": 4100, "sections": SECTIONS,
    "engagement_map": {"mini_stories": [], "ctas": {"commercial_contextual": 11},
        "featured_snippets": [1, 2, 4, 5, 6, 10], "next_actions": {"commercial_conversion": 11},
        "cta_exception_reason": None},
    "gap_mapping": {"job-mix routing instead of a universal winner": 1, "equal live-demo tests": 7,
        "implementation and total-cost diligence": 8, "verified exact PAA answers": 10},
    "insight_mapping": {"service maintenance and project fit is the primary route": 2,
        "pricing and implementation uncertainty belong in demo questions": 5,
        "mobile integrations scheduling projects and reporting require workflow proof": 6},
    "reader_contract": {"primary_reader": "A US electrical contractor owner or operations leader evaluating job-management software.",
        "sophistication_level": "Commercial investigator who understands the work but needs a defensible software buying process.",
        "trigger_problem": "Service, maintenance and project work no longer moves cleanly across office, field and finance systems.",
        "existing_belief": "A universal best-product list can decide the purchase.",
        "decision_task_helped": "Select two or three demos and evaluate them against the same operating scenarios.",
        "distinctive_angle": "A 10-product, job-mix-led comparison with symmetric vendor cards and must-prove demo questions.",
        "promised_payoff": "A shortlist, weighted scorecard, three demo scenarios and implementation checks.",
        "funnel_stage": "mofu", "exclusions": ["universal winner claims", "unverified vendor claims", "Hindsight as public proof",
        "customer or Fred proof without direct selector fit", "named author", "em dashes", "editorial-process language"]},
    "original_contributions": [
        {"contribution_id": "job-mix-router", "planned_contribution": "Five-route decision table inside 300 words.",
         "purpose": "Turn a broad comparison into a usable first demo list.", "evidence_source": "Official vendor pages and editorial workflow analysis.",
         "target_section": "Which electrical job management software fits your job mix?"},
        {"contribution_id": "weighted-demo-scorecard", "planned_contribution": "Nine-criterion weighted demo scorecard.",
         "purpose": "Keep evaluation criteria fixed across vendors.", "evidence_source": "Buyer guidance informed by internal strategy, not public claims.",
         "target_section": "Score every demo against the same criteria"},
        {"contribution_id": "three-electrical-scenarios", "planned_contribution": "Urgent service, planned maintenance and commercial project demo scripts.",
         "purpose": "Make vendors prove job-mix fit in live product screens.", "evidence_source": "Editorial workflow framework.",
         "target_section": "Run the same three electrical job scenarios"}],
    "entity_map": {"primary": [PRIMARY, "electrical contractors", "job management", "dispatch", "job costing"],
        "supporting": ["service calls", "planned maintenance", "commercial project work", "takeoffs", "QuickBooks", "implementation", "total cost"]},
    "internal_link_plan": [
        {"target": PILLAR, "role": "down_funnel", "rationale": "Verified electrical commercial pillar and cluster requirement."},
        {"target": "https://www.simprogroup.com/solutions/job-management-software", "role": "supporting", "rationale": "Defines the broader operating workflow."},
        {"target": "https://www.simprogroup.com/solutions/project-management-software", "role": "supporting", "rationale": "Supports project-control evaluation."},
        {"target": "https://www.simprogroup.com/blog/best-field-service-management-software", "role": "supporting", "rationale": "Provides a broader field-service comparison for buyers expanding beyond the electrical shortlist."},
        {"target": "https://www.simprogroup.com/features/takeoffs", "role": "supporting", "rationale": "Clarifies takeoff versus job-management scope."}],
    "industry_cluster_link_policy": {"status": "required", "industry": "electrical", "target": PILLAR,
        "anchor": "electrical contractor software", "placement": "intro_first_300_words",
        "vault_vertical_query": "Simpro electrical contractor software industry vertical profile",
        "required_resource_ids": ["res-10b97eee1de25395bbf8b904111ca4b0", "res-f9f9499223a15d6a901806f30fb1a8ba"],
        "rationale": "A single-trade Simpro blog requires the verified electrical industry commercial pillar."},
    "rewrite_decisions": {"preserve": [{"item": "slug and canonical", "decision": "Keep accumulated comparison ownership."},
        {"item": "four image slots", "decision": "Keep all original source references and positions; add planned keyword filenames and conservative alt text because sources return 404."}],
        "update": [{"item": "title and angle", "decision": "Use a job-type buying guide instead of a generic ranking."},
        {"item": "vendor cards", "decision": "Use a symmetric 120-160-word fit, limitation, pricing and demo format."}],
        "add": [{"item": "Knowify", "decision": "Add fourth for project costing and construction administration fit."},
        {"item": "PAA FAQ", "decision": "Use only four exact questions captured in AnswerSocrates."}],
        "remove": [{"item": "repetitive card language", "decision": "Tighten to keep the article within 3,800-4,300 words."},
        {"item": "unsupported proof", "decision": "Omit customer and Fred evidence when no directly relevant approved selection fits."}]},
    "audience_language_research": {"status": "not_applicable", "rationale": "The task supplies the ICP and the vault supplies current electrical and editorial language.",
        "source_urls": [], "observations": [], "intended_section_use": []},
    "keyword_decision": {"status": "resolved", "artifact_schema": "simpro-semrush-keyword-decision/v1",
        "source": "semrush_connector", "database": "us", "selected_primary_keyword": PRIMARY,
        "selected_secondary_keywords": ["electrical contractor job management software", "job management software for electrical contractors"],
        "selection_rationale": "Fresh authenticated Semrush US desktop UI evidence dated 2026-09-28 confirms commercial intent, US volume 320 and KD 26. The broader electrical contractor software query remains assigned to the verified industry pillar."},
    "faq_policy": {"status": "required", "rationale": "AnswerSocrates returned four exact People also ask questions for the query."},
    "paa_policy": {"source_kind": "answersocrates", "query": PRIMARY, "selected_questions": PAA},
    "search_strategy": {"primary_query": PRIMARY,
        "searcher_task": "Compare electrical job-management platforms and decide which two or three deserve a live demo for the contractor's job mix.",
        "intent_class": "commercial", "funnel_stage": "mofu",
        "serp_evidence_artifact": "research/serp-evidence-best-electrical-job-management-software-2026-09-28.json",
        "dominant_content_type": "General Article",
        "selected_content_type": "Commercial software comparison and buyer guide", "observed_serp_features": ["Sitelinks", "AI Overview", "Reviews", "Video"],
        "related_query_paa_artifact": "research/paa-evidence-best-electrical-job-management-software-2026-09-28.json",
        "format_decision": "documented_exception", "exception_reason": "Semrush exposes result URLs rather than result titles in the authenticated SERP Analysis table, so the verified collector conservatively classifies the observed rows as General Article. The visible top ten is dominated by vendor category pages, while the existing Simpro comparison ranks eighth. A job-mix buying guide preserves commercial-investigation intent and adds a consistent shortlisting and demo format that the category pages do not provide.", "status": "ready"},
    "commercial_strategy": {"article_title": TITLE, "article_primary_keyword": PRIMARY, "article_intent": "commercial",
        "destination_id": "simpro-us-industry-electrical-software", "commercial_pillar_url": PILLAR,
        "planned_anchor_text": "electrical contractor software", "planned_h2_section": "Which electrical job management software fits your job mix?",
        "existing_overlapping_urls_checked": ["https://www.simprogroup.com/blog/best-electrical-job-management-software", PILLAR,
            "https://www.simprogroup.com/solutions/job-management-software", "https://www.simprogroup.com/solutions/project-management-software"],
        "pillar_versus_blog_intent_difference": "The blog owns comparison, shortlisting and purchase evaluation for electrical job management software. The industry page owns product/category intent for electrical contractor software.",
        "cannibalization_decision": "different_intent", "incoming_link_candidates": [PILLAR], "status": "aligned"},
    "lifecycle": {"last_updated_date": DATE, "volatility": "high", "next_review_date": "2026-12-27",
        "review_command": "/performance-review published/best-electrical-job-management-software-2026-09-02.md",
        "gsc_lane": "unavailable: no fresh GSC export was collected for this rewrite; do not infer query performance",
        "ga4_lane": "unavailable: no fresh GA4 export was collected for this rewrite; do not infer engagement performance",
        "semrush_lane": "available: authenticated US desktop Semrush UI capture dated 2026-09-28",
        "ai_citation_lane": "unavailable: no current AI-citation export was collected; do not infer citation performance",
        "decision": "update", "status": "scheduled"}}


if __name__ == "__main__":
    out = ROOT / "research" / f"editorial-plan-{SLUG}-{DATE}.json"
    atomic_write_json(out, PLAN); print(f"wrote {out.relative_to(ROOT).as_posix()}")
