"""Freeze the simpro-blog-editorial-plan/v2 for the BigChange COSHH regulations rewrite.

Every strategy value traces to the Pheonix brief, the authenticated Semrush UI
read, the Chrome SERP capture, Search Console, or primary-source reads recorded
in research/content-brief-coshh-regulations-2026-09-24.md. Python writes this
governance artifact only; the article itself is written natively.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from data_sources.modules.blog_assembly_contract import atomic_write_json
from data_sources.modules.editorial_plan.plan_validation import check_plan

SLUG = "coshh-regulations"
DATE = "2026-09-24"
OUT = ROOT / "research" / f"editorial-plan-{SLUG}-{DATE}.json"
BRIEF = f"research/content-brief-{SLUG}-{DATE}.md"
SERP = f"research/serp-evidence-{SLUG}-{DATE}.json"
KEYWORDS = json.loads((ROOT / "research" / f"semrush-keyword-decision-{SLUG}-{DATE}.json").read_text(encoding="utf-8"))

TITLE = "COSHH Regulations Explained: 3 Key Rules and How to Complete a COSHH Assessment"
PRIMARY = "coshh regulations"
SECONDARIES = KEYWORDS["selected_secondary_keywords"]
PILLAR = "https://www.bigchange.com/features/risk-assessment"
PILLAR_H2 = "How can field service businesses manage COSHH compliance across multiple jobs and sites?"
FAQ_QUESTIONS = [
    "Is a COSHH assessment a legal requirement?",
    "Is a safety data sheet the same as a COSHH assessment?",
    "Does COSHH apply to cleaning products?",
    "Does COSHH training need to be provided to employees?",
]


def section(n, kind, heading, words, *, question, payoff, prev, nxt, hook, angle, gaps, data,
            snippet=False, cta=None, next_action=None, links=None, story=False):
    return {
        "bridge_from_previous": prev,
        "bridge_to_next": nxt,
        "cta": cta,
        "engagement_hook": hook,
        "featured_snippet": snippet,
        "heading": heading,
        "internal_links": links or [],
        "knowledge_gaps": gaps,
        "mini_story": story,
        "next_action": next_action,
        "reader_question": question,
        "section_number": n,
        "section_payoff": payoff,
        "strategic_angle": angle,
        "type": kind,
        "unique_data": data,
        "word_target": words,
    }


SECTIONS = [
    section(1, "intro", TITLE, 140,
            question="What is COSHH, and what do the regulations make an employer do?",
            payoff="A standalone COSHH answer, then a filled at-a-glance table of duties and records.",
            prev=None, nxt="Into the fuller definition and why it matters.",
            hook="Every chemical, dust, and fume an engineer meets on a job falls under one set of rules.",
            angle="Answer the query in the first 60 words, then hand over a usable artifact.",
            gaps=["what COSHH stands for", "which duties matter most"],
            data=["COSHH at a glance table mapping regulations to on-site actions and records."],
            snippet=True),
    section(2, "body_explanation", "What is COSHH, and why is it important?", 200,
            question="What does COSHH mean, and why should a field service employer care?",
            payoff="A liftable definition plus the current HSE ill-health and penalty picture.",
            prev="The table shows the duties.", nxt="Into which substances count.",
            hook="HSE links 11,000 lung disease deaths a year to past exposures at work.",
            angle="Define first, then show the stakes with current primary sources.",
            gaps=["current HSE ill-health figures", "what a breach can cost"],
            data=["HSE causdis statistics updated 2026-01-07.", "Sentencing Council unlimited fine range."],
            snippet=True),
    section(3, "body_list", "What substances are covered by COSHH?", 190,
            question="Which substances does COSHH cover on a field job?",
            payoff="A direct answer, the HSE list, the exclusions, and the hazard-symbol test.",
            prev="COSHH covers substances hazardous to health.", nxt="Into the regulations employers lean on most.",
            hook="If the label carries a hazard symbol, COSHH applies.",
            angle="Give field examples by trade alongside the HSE categories.",
            gaps=["lead, asbestos and radioactive exclusions", "field examples by trade"],
            data=["HSE substance list and exclusions."], snippet=True),
    section(4, "body_explanation", "What are the 3 main COSHH regulations?", 130,
            question="What are the 3 main regulations of COSHH?",
            payoff="The direct answer and a comparison table of Regulations 6, 7 and 12.",
            prev="Now the duties behind the substances.", nxt="Into each regulation in turn.",
            hook="Three regulations carry most of the day-to-day employer workload.",
            angle="State that COSHH has more than three regulations before listing the core three.",
            gaps=["which three regulations", "that COSHH contains more than three"],
            data=["Regulation 6, 7 and 12 comparison table."], snippet=True),
    section(5, "body_how_to", "1. Regulation 6: Assess the risk to health", 160,
            question="What does Regulation 6 require?",
            payoff="The assessment duty, the review triggers, and the 5-employee recording rule.",
            prev="Regulation 6 comes first.", nxt="Into prevention and control.",
            hook="No suitable and sufficient assessment means the work does not start.",
            angle="Quote the legal test, then translate it into a job-level action.",
            gaps=["recording threshold"], data=["Regulation 6(3) and 6(4) text."]),
    section(6, "body_how_to", "2. Regulation 7: Prevent or control exposure", 180,
            question="What does Regulation 7 require?",
            payoff="Prevention first, then the control order through to PPE.",
            prev="An assessment feeds the controls.", nxt="Into information and training.",
            hook="PPE is the last control, not the first.",
            angle="Order the controls the way an engineer applies them on site.",
            gaps=["control hierarchy", "substitution"], data=["Regulation 7(1) to 7(3) text."]),
    section(7, "body_how_to", "3. Regulation 12: Provide information, instruction and training", 150,
            question="What does Regulation 12 require?",
            payoff="What employees must be told, including assessment findings and safety data sheet access.",
            prev="Controls only work when people understand them.", nxt="Into the remaining duties.",
            hook="Training is a legal duty, not a nice-to-have.",
            angle="List what each engineer needs before starting a job.",
            gaps=["what the training must cover"], data=["Regulation 12 text."]),
    section(8, "body_list", "What other COSHH requirements do employers need to follow?", 210,
            question="What else does COSHH require beyond the core three?",
            payoff="A table of Regulations 8 to 11 and 13 with Schedule 2A, including record periods.",
            prev="The core three are only part of the law.", nxt="Into the assessment itself.",
            hook="Local exhaust ventilation needs a thorough examination at least every 14 months.",
            angle="Rebuild the old eight-steps material around the actual regulations.",
            gaps=["14-month LEV examination", "record retention periods"],
            data=["Regulations 8 to 13 and Schedule 2A table."]),
    section(9, "body_explanation", "What is a COSHH assessment?", 130,
            question="What is a COSHH assessment?",
            payoff="A standalone definition before any instructions.",
            prev="Regulation 6 makes the assessment a legal duty.", nxt="Into how to complete one.",
            hook="A safety data sheet is not a risk assessment.",
            angle="Definition first, then how it differs from a safety data sheet.",
            gaps=["assessment versus safety data sheet"], data=["HSE assessment and datasheet guidance."],
            snippet=True),
    section(10, "body_how_to", "How do you carry out a COSHH assessment?", 340,
            question="How do I carry out a COSHH assessment for field work?",
            payoff="Five steps and a filled field-job checklist table.",
            prev="The definition sets the target.", nxt="Into how often to review it.",
            hook="Five steps turn a legal duty into a repeatable job routine.",
            angle="Condense HSE guidance into steps an operations manager can run for every job type.",
            gaps=["field-job version of the steps", "a usable checklist"],
            data=["Five-step process.", "Filled field-job COSHH checklist table."], snippet=True),
    section(11, "body_explanation", "How often should a COSHH assessment be reviewed?", 130,
            question="How often should a COSHH assessment be reviewed?",
            payoff="Regularly, and immediately after any of three legal triggers.",
            prev="An assessment ages as the work changes.", nxt="Into who owns the duty.",
            hook="The law sets triggers, not a fixed calendar interval.",
            angle="Give the clean legal answer, then a practical review rhythm.",
            gaps=["review triggers"], data=["Regulation 6(3) triggers."], snippet=True),
    section(12, "body_explanation", "Who is responsible for COSHH compliance?", 180,
            question="Who is responsible for COSHH compliance?",
            payoff="Employer duties first, then employee duties and assessor competence.",
            prev="Reviews need an owner.", nxt="Into running this across many jobs.",
            hook="No qualification is required to assess, but competence is.",
            angle="Focus on the employer, then show what engineers owe in return.",
            gaps=["assessor competence"], data=["HSE FAQ competence answer."], snippet=True),
    section(13, "body_explanation", PILLAR_H2, 280,
            question="How do I keep COSHH compliance consistent across engineers, jobs and sites?",
            payoff="A job-level workflow with digital risk assessments, worksheets, asset records and customer experience.",
            prev="Responsibility is clear; consistency is the hard part.", nxt="Into the closing action.",
            hook="Paper assessments stay in the office while the chemicals travel in the van.",
            angle="Show the workflow before the product, with customer experience proof.",
            gaps=["how to apply COSHH across many sites", "what good field evidence looks like"],
            data=["Clearground dynamic risk assessment experience.", "Capterra review experience."],
            cta="commercial_contextual", links=[PILLAR], story=True),
    section(14, "conclusion", "Make COSHH compliance easier to manage in the field", 100,
            question="What should I do next?",
            payoff="One concrete next action and the demo route.",
            prev="The workflow is set out.", nxt="Into the remaining questions.",
            hook="Start with the job type your engineers do most often.",
            angle="Close on one action, then the CTA.",
            gaps=["the single next step"], data=["Close on the checklist rather than a product pitch."],
            cta="soft_resource_action"),
    section(15, "faq", "Frequently Asked Questions", 240,
            question="What else do employers ask about COSHH?",
            payoff="Four answer-first responses to the brief's pre-picked questions.",
            prev="The main guide is complete.", nxt=None,
            hook="Legal requirement, data sheets, cleaning products and training.",
            angle="Answer-first, each inside the 40 to 60 word band with an HSE link.",
            gaps=["legal status", "cleaning products", "training duty"],
            data=["Brief-supplied FAQ set answered against HSE sources."]),
]

PLAN = {
    "schema": "simpro-blog-editorial-plan/v2",
    "brand": "BigChange",
    "date": DATE,
    "topic": PRIMARY,
    "total_word_target": sum(s["word_target"] for s in SECTIONS),
    "meta": {
        "meta_title": "COSHH Regulations: Key Rules & Assessment Guide",
        "meta_description": "Understand COSHH regulations, the 3 key rules employers need to know, and how to carry out a COSHH assessment step by step.",
        "primary_keyword": PRIMARY,
        "secondary_keywords": SECONDARIES,
        "title_options": [TITLE],
        "url_slug": SLUG,
    },
    "keyword_decision": {
        "artifact_schema": "simpro-semrush-keyword-decision/v1",
        "database": "uk",
        "selected_primary_keyword": PRIMARY,
        "selected_secondary_keywords": SECONDARIES,
        "selection_rationale": KEYWORDS["selection_rationale"],
        "source": "semrush_connector",
        "status": "resolved",
    },
    "search_strategy": {
        "primary_query": PRIMARY,
        "searcher_task": "Understand what COSHH requires of an employer and complete a compliant COSHH assessment for the work their engineers do.",
        "intent_class": "informational",
        "funnel_stage": "tofu",
        "serp_evidence_artifact": SERP,
        "dominant_content_type": "General Article",
        "selected_content_type": "General Article",
        "observed_serp_features": ["AI Overview", "People also ask", "Videos", "Short videos", "Images", "People also search for"],
        "related_query_paa_artifact": BRIEF,
        "format_decision": "match_dominant",
        "exception_reason": "none",
        "status": "ready",
    },
    "commercial_strategy": {
        "article_title": TITLE,
        "article_primary_keyword": PRIMARY,
        "article_intent": "informational",
        "destination_id": "bigchange-uk-feature-risk-assessment",
        "commercial_pillar_url": PILLAR,
        "planned_anchor_text": "digital risk assessment software for field engineers",
        "planned_h2_section": PILLAR_H2,
        "existing_overlapping_urls_checked": [
            "https://www.bigchange.com/blog/cleaning-chemicals-safety-your-guide-to-the-coshh-regulations",
            "https://www.bigchange.com/blog/why-are-risk-assessments-important",
            "https://www.bigchange.com/blog/how-to-improve-compliance-in-field-service-operations",
        ],
        "pillar_versus_blog_intent_difference": "The article is informational regulatory guidance on COSHH duties and assessments. The risk assessment feature page is the commercial destination for readers who need to run those assessments digitally on every job, and it remains the conversion owner.",
        "cannibalization_decision": "update_existing",
        "incoming_link_candidates": [
            "https://www.bigchange.com/blog/why-are-risk-assessments-important",
            "https://www.bigchange.com/blog/how-to-improve-compliance-in-field-service-operations",
        ],
        "status": "aligned",
    },
    "lifecycle": {
        "last_updated_date": DATE,
        "volatility": "high",
        "next_review_date": "2026-12-23",
        "review_command": "/performance-review https://www.bigchange.com/blog/coshh-regulations",
        "gsc_lane": "available: the original URL's top 25 queries show 232 impressions and 0 clicks over the trailing 480 days",
        "ga4_lane": "unavailable: no BigChange GA4 property is configured in this workspace",
        "semrush_lane": "available: bound keyword decision read from the authenticated Semrush UI on 2026-09-24; original URL ranks for 0 UK keywords on 2026-09-23",
        "ai_citation_lane": "not_applicable: no AI citation tracking is configured for BigChange",
        "decision": "update",
        "status": "scheduled",
    },
    "reader_contract": {
        "primary_reader": "UK owners, managing directors, and operations or service managers of small and medium field service businesses who carry health and safety duties without a dedicated H&S team.",
        "trigger_problem": "Engineers handle cleaning chemicals, dusts, and fumes across many customer sites and the business is unsure its COSHH paperwork would satisfy an inspector.",
        "existing_belief": "COSHH means keeping safety data sheets on file and handing out PPE.",
        "sophistication_level": "Practical operator who knows COSHH exists but has never mapped the regulations to a job-level routine.",
        "decision_task_helped": "Identify which COSHH duties apply, complete and record an assessment, and set review triggers for every job type.",
        "distinctive_angle": "Treat COSHH as a job-level routine that travels with the engineer rather than an office file, and map each regulation to the record it creates.",
        "promised_payoff": "A filled COSHH at a glance table, the three core regulations explained, a five-step assessment process, and a field-job checklist.",
        "funnel_stage": "tofu",
        "exclusions": [
            "legal advice",
            "competitor product comparisons",
            "the unsourced average fine figure from the original article",
            "asbestos, lead, and radioactive substance regimes beyond noting their exclusion",
            "Northern Ireland COSHH (NI) 2003 detail",
            "ratings or star claims from review sites",
        ],
    },
    "entity_map": {
        "primary": ["COSHH regulations", "Control of Substances Hazardous to Health Regulations 2002", "COSHH assessment", "Health and Safety Executive"],
        "supporting": [
            "hazardous substance", "safety data sheet", "workplace exposure limit", "local exhaust ventilation",
            "health surveillance", "personal protective equipment", "hierarchy of control", "ACOP L5",
            "Sentencing Council", "risk assessment", "point of work risk assessment",
        ],
    },
    "original_contributions": [
        {
            "contribution_id": "coshh-at-a-glance-table",
            "planned_contribution": "A filled table mapping the core COSHH regulations to the on-site action and the record each one creates.",
            "purpose": "Give the reader a usable artifact inside the first 300 words.",
            "evidence_source": "COSHH Regulations 2002 on legislation.gov.uk, each regulation read and cited.",
            "target_section": TITLE,
        },
        {
            "contribution_id": "lev-and-record-retention",
            "planned_contribution": "The 14-month thorough examination interval for local exhaust ventilation and the 5-year and 40-year record retention periods.",
            "purpose": "Close a gap the checked ranking pages leave open.",
            "evidence_source": "Regulations 9, 10 and 11 on legislation.gov.uk.",
            "target_section": "What other COSHH requirements do employers need to follow?",
        },
        {
            "contribution_id": "sds-is-not-an-assessment",
            "planned_contribution": "Why a safety data sheet informs but never replaces a COSHH assessment.",
            "purpose": "Correct the most common shortcut small employers take.",
            "evidence_source": "HSE safety data sheet guidance and HSE COSHH FAQ.",
            "target_section": "What is a COSHH assessment?",
        },
        {
            "contribution_id": "field-job-checklist",
            "planned_contribution": "A filled field-job COSHH checklist table covering what to check before, during and after each job.",
            "purpose": "Turn the five HSE-based steps into a routine an engineer can follow on site.",
            "evidence_source": "Original editorial checklist built on HSE assessment guidance, not a sourced metric.",
            "target_section": "How do you carry out a COSHH assessment?",
        },
        {
            "contribution_id": "review-triggers",
            "planned_contribution": "The three legal triggers that force an immediate assessment review, plus the recording threshold.",
            "purpose": "Replace a guessed review interval with the legal test.",
            "evidence_source": "Regulation 6(3) and 6(4) on legislation.gov.uk.",
            "target_section": "How often should a COSHH assessment be reviewed?",
        },
    ],
    "gap_mapping": {
        "field service application across engineers and sites": 13,
        "14-month local exhaust ventilation examination": 8,
        "five-or-more-employees recording threshold": 5,
        "regulations 6, 7 and 12 named by number": 4,
    },
    "insight_mapping": {
        "COSHH contains more than three regulations": 4,
        "a safety data sheet is not a risk assessment": 9,
        "the law sets review triggers rather than a fixed interval": 11,
        "no qualification is required but competence is": 12,
        "PPE is the final control option": 6,
    },
    "internal_link_plan": [
        {"target": PILLAR, "role": "down_funnel",
         "rationale": "Commercial destination for running point-of-work risk assessments digitally on every job."},
        {"target": "https://www.bigchange.com/blog/ppm-schedule", "role": "supporting",
         "rationale": "Brief link; planned preventive maintenance scheduling carries the Regulation 9 control-measure maintenance duty."},
        {"target": "https://www.bigchange.com/blog/field-service-excellence-bigchange-lightning", "role": "supporting",
         "rationale": "Brief link for field service documentation behind recorded assessments."},
        {"target": "https://www.bigchange.com/blog/how-to-grow-facilities-management-business", "role": "supporting",
         "rationale": "Brief link for facilities management compliance, a core COSHH sector."},
        {"target": "https://www.bigchange.com/industries/cleaning-software-crm", "role": "supporting",
         "rationale": "Industry page that names a digital library for COSHH sheets for cleaning businesses."},
    ],
    "rewrite_decisions": {
        "preserve": [
            {"decision": "Assess the risks and prevent or control exposure, rebuilt as Regulations 6 and 7"},
            {"decision": "Ensure control measures are maintained, rebuilt as Regulations 8 and 9"},
            {"decision": "Prepare plans and procedures, rebuilt as Regulation 13"},
            {"decision": "Ensure employees are informed, trained and supervised, rebuilt as Regulation 12"},
            {"decision": "The existing featured image, re-exported under a keyword filename with new alt text"},
            {"decision": "The digital COSHH sheets and risk assessment forms idea, moved into the field compliance section"},
        ],
        "update": [
            {"decision": "H1, meta title, meta description and URL slug per the brief"},
            {"decision": "Work-related ill-health statistic replaced with the current HSE figure"},
            {"decision": "Penalty framing changed to the Sentencing Council unlimited fine"},
            {"decision": "Health and safety product link moved to the risk assessment feature page"},
        ],
        "add": [
            {"decision": "Standalone COSHH definition and substances section with exclusions"},
            {"decision": "The 3 main COSHH regulations with a table and one section each"},
            {"decision": "COSHH assessment definition, five-step process and field-job checklist"},
            {"decision": "Review frequency and responsibility sections"},
            {"decision": "COSHH at a glance table as the early artifact"},
            {"decision": "FAQ section from the brief's pre-picked questions"},
        ],
        "remove": [
            {"decision": "The unsourced average fine of 150,000 pounds and its dead enforcement PDF link"},
            {"decision": "The outdated 1.6 million work-related ill-health figure"},
            {"decision": "The cleaning-chemicals-only framing in the H1"},
        ],
    },
    "paa_policy": {"query": PRIMARY, "selected_questions": FAQ_QUESTIONS, "source_kind": "brief_paa"},
    "faq_policy": {"status": "required",
                   "rationale": "The supplied brief carries a dedicated FAQ set, which for a rewrite is the pre-picked brief section and takes precedence over SERP collection."},
    "industry_cluster_link_policy": {"status": "not_applicable",
                                     "rationale": "The single-trade Simpro industry cluster policy applies to Simpro-branded articles only. This is a BigChange article with no Simpro signal, so no Simpro industry cluster link is required or permitted."},
    "audience_language_research": {
        "status": "required",
        "rationale": "Capterra UK reviews from BigChange users with health and safety roles describe building health and safety worksheets in house and keeping compliance documents together, which sharpens the field compliance section.",
        "observations": [
            "An HSEQ manager in construction describes designing policies, procedures and health and safety worksheets in house.",
            "A transport manager describes keeping documents together from fault report to completion to stay compliant.",
        ],
        "source_urls": ["https://www.capterra.co.uk/software/149479/jobwatch-powered-by-bigchange"],
        "intended_section_use": [PILLAR_H2],
    },
    "engagement_map": {
        "cta_exception_reason": None,
        "ctas": {"commercial_contextual": 13, "soft_resource_action": 14},
        "featured_snippets": [1, 2, 3, 4, 9, 10, 11, 12],
        "mini_stories": [13],
        "next_actions": {"educational_next_step": 10},
    },
    "sections": SECTIONS,
}
SECTIONS[9]["next_action"] = "educational_next_step"


def main() -> int:
    findings = check_plan(PLAN)
    for finding in findings:
        print("PLAN FINDING:", finding)
    atomic_write_json(OUT, PLAN)
    print(f"plan: {OUT.relative_to(ROOT).as_posix()} words={PLAN['total_word_target']} findings={len(findings)}")
    return 1 if findings else 0


if __name__ == "__main__":
    raise SystemExit(main())
