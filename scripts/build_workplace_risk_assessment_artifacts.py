"""Build proof-sensitive planning artifacts for the BigChange risk-assessment rewrite."""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from data_sources.modules.semrush_keyword_decision_guard import (
    SOURCE_BOUNDARY,
    build_keyword_decision as build_semrush_keyword_decision,
)


from scripts.workplace_risk_assessment_common import (  # noqa: E402
    ARTICLE,
    BRIEF,
    DATE,
    FULFILLMENT,
    KEYWORD,
    PLAN,
    PRIMARY,
    SECONDARY,
    SEMRUSH_UI,
    SERP_BLOCKER,
    SIDECAR,
    SLUG,
    TITLE,
    section,
    sha256,
    write_json,
)
from scripts.workplace_risk_assessment_sidecar import build_sidecar  # noqa: E402


def build_brief() -> str:
    return f"""# BigChange workplace risk assessment rewrite brief

Date: {DATE}
Market: UK
Workflow mode: rewrite
Canonical URL: https://www.bigchange.com/blog/how-to-conduct-a-workplace-risk-assessment
Primary keyword: {PRIMARY}
Target length: 2,200 to 2,500 words

## Objective

Replace the dated COVID-led article with a practical HSE-backed guide for owners, operations managers, service managers, office managers and health-and-safety leads in service businesses. Keep the existing URL and move from education into a restrained point-of-work software transition.

## Required content

- Give the definition immediately and place a five-step checklist inside the first 300 words.
- Explain hazard versus risk, UK requirements and who can complete the assessment.
- Teach the HSE five-step workflow.
- Include a self-contained ladder-at-a-customer-site example mapped to all five steps.
- Add a direct answer to what a workplace risk assessment should include.
- Use Clearground only as a narrow, source-linked experience story.
- Use four brief-approved FAQs with direct 40 to 60 word first paragraphs.

## Pre-picked PAA Questions

- What is a risk assessment in the workplace?
- What are the 5 steps of a workplace risk assessment?
- How often should a workplace risk assessment be reviewed?
- Does a workplace risk assessment need to be written down?

## Commercial route

Link the exact anchor `risk assessment software` to https://www.bigchange.com/features/risk-assessment in the H2 `How to make workplace risk assessments easier to manage`. The article teaches the assessment process; the feature page presents software for managing that process.
"""


def build_keyword_decision() -> dict[str, object]:
    evidence_hash = sha256(SEMRUSH_UI)
    common = {
        "execution_surface": "semrush_ui_chrome_main_browser",
        "database": "uk",
        "device": "desktop",
        "collection_date": DATE,
        "ui_evidence_path": SEMRUSH_UI.relative_to(ROOT).as_posix(),
        "ui_evidence_sha256": evidence_hash,
    }
    connector_reports = [
        {"report": "_keyword_research", "parameters": {**common, "query": PRIMARY}, "status": "completed"},
        {"report": "_get_report_schema", "parameters": {**common, "report": "phrase_this"}, "status": "completed"},
        {"report": "phrase_these", "parameters": {**common, "keywords": [PRIMARY, *SECONDARY, "workplace risk assessment example", "risk assessment software"]}, "status": "completed"},
        {"report": "phrase_related", "parameters": {**common, "phrase": PRIMARY}, "status": "completed"},
        {"report": "phrase_questions", "parameters": {**common, "phrase": PRIMARY}, "status": "completed"},
        {"report": "phrase_organic", "parameters": {**common, "phrase": PRIMARY, "display_limit": 10}, "status": "completed"},
        {"report": "phrase_this", "parameters": {**common, "phrase": PRIMARY}, "status": "completed"},
    ]
    return build_semrush_keyword_decision(
        brand="BigChange",
        market="UK",
        database="uk",
        collection_date=DATE,
        source_boundary=SOURCE_BOUNDARY,
        seed_terms=[PRIMARY, "what is a risk assessment", "risk assessment example", "risk assessment software"],
        connector_reports=connector_reports,
        candidate_metrics=[
            {"keyword": PRIMARY, "volume": 720, "keyword_difficulty": 33, "intent": "informational"},
            {"keyword": "workplace risk assessments", "volume": 590, "keyword_difficulty": 29, "intent": "informational"},
            {"keyword": "what is a risk assessment", "volume": 4400, "keyword_difficulty": 27, "intent": "informational"},
            {"keyword": "risk assessment example", "volume": 1900, "keyword_difficulty": 22, "intent": "informational"},
            {"keyword": "risk assessment meaning", "volume": 1300, "keyword_difficulty": 60, "intent": "informational"},
            {"keyword": "workplace risk assessment example", "volume": 20, "keyword_difficulty": None, "intent": "informational"},
            {"keyword": "risk assessment software", "volume": 1300, "keyword_difficulty": 19, "intent": "informational"},
        ],
        serp_finalists=[
            {
                "keyword": PRIMARY,
                "database": "uk",
                "results": [
                    {"position": 1, "position_type": "organic", "domain": "hse.gov.uk", "url": "https://www.hse.gov.uk/risk/", "triggered_serp_features": []},
                    {"position": 2, "position_type": "organic", "domain": "acas.org.uk", "url": "https://www.acas.org.uk/health-and-safety-at-work/risk-assessments", "triggered_serp_features": []},
                    {"position": 3, "position_type": "organic", "domain": "hse.gov.uk", "url": "https://www.hse.gov.uk/simple-health-safety/risk/risk-assessment-template-and-examples.htm", "triggered_serp_features": []},
                ],
            }
        ],
        question_candidates=[
            {"keyword": "how to conduct a fire risk assessment in the workplace", "volume": 50, "keyword_difficulty": None, "intent": "informational"},
            {"keyword": "why do we have risk assessments in the workplace", "volume": 40, "keyword_difficulty": None, "intent": "informational"},
            {"keyword": "what is a fire risk assessment in the workplace", "volume": 30, "keyword_difficulty": None, "intent": "informational"},
            {"keyword": "who should carry out a risk assessment of the workplace", "volume": 30, "keyword_difficulty": None, "intent": "informational"},
            {"keyword": "how to assess risks in the workplace", "volume": 20, "keyword_difficulty": None, "intent": "informational"},
        ],
        related_candidates=[
            {"keyword": "workplace risk assessments", "volume": 590, "keyword_difficulty": 29, "intent": "informational"},
            {"keyword": "workplace fire risk assessment", "volume": 480, "keyword_difficulty": 22, "intent": "informational"},
            {"keyword": "workplace stress risk assessment", "volume": 480, "keyword_difficulty": 9, "intent": "informational"},
        ],
        selected_primary_keyword=PRIMARY,
        selected_secondary_keywords=SECONDARY,
        rejected_keywords=[
            {"keyword": "risk assessment software", "reason": "Owned by the separate BigChange feature page and used only as the commercial transition."},
            {"keyword": "risk assessment meaning", "reason": "Higher difficulty and less specific to the workplace workflow; retained as semantic support only."},
        ],
        selection_rationale="Workplace risk assessment is the closest match to the existing URL and educational task, with UK volume 720 and keyword difficulty 33. The higher-volume definition and example terms are covered in dedicated sections without changing the page's ownership.",
        workspace_root=ROOT,
    )


def build_plan() -> dict[str, object]:
    return {
        "schema": "simpro-blog-editorial-plan/v2",
        "brand": "BigChange",
        "date": DATE,
        "topic": "Workplace risk assessment for UK service businesses",
        "total_word_target": 2730,
        "meta": {
            "meta_title": "Workplace Risk Assessment: 5 Steps + Example | BigChange",
            "meta_description": "Learn how to carry out a workplace risk assessment in five steps, understand requirements, and see a practical risk assessment example.",
            "primary_keyword": PRIMARY,
            "secondary_keywords": SECONDARY,
            "title_options": [TITLE],
            "url_slug": "how-to-conduct-a-workplace-risk-assessment",
        },
        "reader_contract": {
            "primary_reader": "UK owner, operations manager, service manager, office manager or health-and-safety lead in a small or midsize service business",
            "sophistication_level": "Understands the work but needs a practical, defensible process that connects office planning with site conditions",
            "existing_belief": "A risk assessment is primarily a form completed before a job or copied from a generic template",
            "trigger_problem": "Assessments become stale, site hazards are discovered too late, and corrective actions separate from the job record",
            "decision_task_helped": "Identify, control, record and review risks for one real task using the HSE five-step process",
            "promised_payoff": "A compact checklist, a worked ladder example and a field-service workflow that can be applied to the next recurring job",
            "distinctive_angle": "Treat the assessment as a live point-of-work decision and action route rather than a paperwork exercise",
            "funnel_stage": "tofu",
            "exclusions": ["legal advice", "COVID-era statistics", "software comparison", "ratings or review claims", "unsupported safety outcomes"],
        },
        "search_strategy": {
            "primary_query": PRIMARY,
            "searcher_task": "Learn what a workplace risk assessment is, the UK requirements, the five steps and what a completed example should contain.",
            "intent_class": "informational",
            "funnel_stage": "tofu",
            "serp_evidence_artifact": f"research/serp-evidence-{SLUG}-{DATE}.json",
            "dominant_content_type": "General Article",
            "selected_content_type": "How-To Guide",
            "observed_serp_features": [
                "AI Overview",
                "Five-step answer list",
                "Template result",
            ],
            "related_query_paa_artifact": f"research/content-brief-{SLUG}-{DATE}.md",
            "format_decision": "documented_exception",
            "exception_reason": "The current results include definitions, general articles and templates. A five-step how-to with a worked field-service example answers the same task while closing the gap between generic guidance and point-of-work execution.",
            "status": "ready",
        },
        "commercial_strategy": {
            "article_title": TITLE,
            "article_primary_keyword": PRIMARY,
            "article_intent": "informational",
            "destination_id": "bigchange-uk-feature-risk-assessment-software",
            "commercial_pillar_url": "https://www.bigchange.com/features/risk-assessment",
            "planned_anchor_text": "risk assessment software",
            "planned_h2_section": "How to make workplace risk assessments easier to manage",
            "existing_overlapping_urls_checked": [
                "https://www.bigchange.com/blog/how-to-conduct-a-workplace-risk-assessment",
                "https://www.bigchange.com/features/risk-assessment",
            ],
            "pillar_versus_blog_intent_difference": "The blog teaches readers how to perform and document an assessment. The feature page presents software for delivering assessments and RAMS at the point of work.",
            "cannibalization_decision": "update_existing",
            "incoming_link_candidates": ["https://www.bigchange.com/features/risk-assessment"],
            "status": "aligned",
        },
        "lifecycle": {
            "last_updated_date": DATE,
            "volatility": "standard",
            "next_review_date": "2027-03-24",
            "review_command": "/research-performance rewrites/workplace-risk-assessment-rewrite-2026-09-25.md",
            "gsc_lane": "unavailable: no first-party Search Console export was supplied for this rewrite",
            "ga4_lane": "unavailable: no first-party analytics export was supplied for this rewrite",
            "semrush_lane": "UK desktop UI evidence dated 2026-09-25: primary volume 720 and keyword difficulty 33",
            "ai_citation_lane": "unavailable: no dated AI-citation baseline was supplied for the existing URL",
            "decision": "update",
            "status": "scheduled",
        },
        "keyword_decision": {
            "artifact_schema": "simpro-semrush-keyword-decision/v1",
            "database": "uk",
            "selected_primary_keyword": PRIMARY,
            "selected_secondary_keywords": SECONDARY,
            "selection_rationale": "The exact workplace query best matches the existing URL and the approved UK how-to objective; broader definition and example terms become section targets.",
            "source": "semrush_connector",
            "status": "resolved",
        },
        "paa_policy": {
            "query": PRIMARY,
            "source_kind": "brief_paa",
            "selected_questions": [
                "What is a risk assessment in the workplace?",
                "What are the 5 steps of a workplace risk assessment?",
                "How often should a workplace risk assessment be reviewed?",
                "Does a workplace risk assessment need to be written down?",
            ],
        },
        "faq_policy": {"status": "required", "rationale": "The approved brief supplies four exact questions that can be answered directly with HSE or British Safety Council support."},
        "industry_cluster_link_policy": None,
        "link_policy_override": None,
        "audience_language_research": None,
        "entity_map": {
            "primary": [PRIMARY, "hazard", "risk", "control", "significant findings"],
            "supporting": ["competent person", "dynamic risk assessment", "point of work", "near miss", "ladder safety", "RAMS"],
        },
        "gap_mapping": {
            "generic guidance does not show how office planning changes at a customer site": 5,
            "blank templates do not demonstrate a completed five-step decision": 4,
            "software transitions often replace operational guidance with promotion": 5,
        },
        "insight_mapping": {
            "a completed form is not the same as a controlled risk": 3,
            "the assessment should produce proceed, add controls, or stop and escalate": 1,
            "corrective actions belong in the same workflow as the job": 5,
        },
        "engagement_map": {
            "mini_stories": [6],
            "ctas": {"contextual_product": 6},
            "featured_snippets": [1, 2, 3, 4, 5, 8],
            "next_actions": {"educational_next_step": 7},
            "cta_exception_reason": "none",
        },
        "original_contributions": [
            {
                "contribution_id": "five-step-field-checklist",
                "planned_contribution": "A compact five-step workplace risk assessment checklist inside the first 300 words.",
                "purpose": "Give the reader a usable artifact before the detailed explanation.",
                "evidence_source": "HSE five-step risk-management guidance read on 2026-09-25.",
                "target_section": TITLE,
            },
            {
                "contribution_id": "ladder-customer-site-example",
                "planned_contribution": "A completed ladder-at-a-customer-site example mapped across all five assessment steps.",
                "purpose": "Turn the process into one coherent field-service decision rather than disconnected advice.",
                "evidence_source": "HSE ladder guidance and risk-assessment template guidance read on 2026-09-25.",
                "target_section": "Workplace risk assessment example: an engineer using a ladder",
            },
            {
                "contribution_id": "point-of-work-action-route",
                "planned_contribution": "A field-to-office workflow that sends missing controls into owned corrective action.",
                "purpose": "Show how assessment findings stay attached to the job without turning the guide into a product pitch.",
                "evidence_source": "Editorial synthesis supported by the approved Clearground customer story and BigChange feature page.",
                "target_section": "How to make workplace risk assessments easier to manage",
            },
        ],
        "internal_link_plan": [
            {"role": "down_funnel", "target": "https://www.bigchange.com/features/risk-assessment", "rationale": "Approved commercial pillar in the digital-management H2."},
            {"role": "supporting", "target": "https://www.bigchange.com/blog/work-orders-what-are-they-and-best-practices", "rationale": "Supports assignment and closeout of corrective actions."},
            {"role": "supporting", "target": "https://www.bigchange.com/blog/ppm-schedule", "rationale": "Supports planned review cadence for recurring asset work."},
            {"role": "supporting", "target": "https://www.bigchange.com/blog/job-tracking-for-field-services-tips", "rationale": "Supports the shared job record in the digital workflow."},
            {"role": "supporting", "target": "https://www.bigchange.com/success-stories/bigchange-helps-clearground-clean-up-on-workforce-health-and-safety", "rationale": "Approved zero-recent-use point-of-work experience story."},
        ],
        "rewrite_decisions": {
            "preserve": [{"decision": "The existing canonical URL and core workplace-risk-assessment topic."}],
            "update": [{"decision": "The title, metadata, update date and UK process guidance."}],
            "add": [{"decision": "An early checklist, hazard-risk table, five-step workflow, worked ladder example, direct answer box and four FAQs."}],
            "remove": [{"decision": "COVID framing, unsupported statistics, emoji headings, unrelated hero image and generic promotion."}],
        },
        "sections": [
            section(1, "intro", TITLE, 220, "Define the assessment immediately and provide the five-step checklist before any long explanation.", "The reader gets the complete process before scrolling.", "What is the process and what will this guide help me do?", "A concise definition and a reusable five-step checklist.", None, "The checklist names the steps; the next sections define the decisions inside them.", data=["five-step-field-checklist"], featured_snippet=True),
            section(2, "body_explanation", "What is a workplace risk assessment?", 310, "Define hazard, risk and control in practical field-service terms, then explain the UK duty.", "A vague hazard creates a vague control.", "What does an assessment examine and what must a UK employer record?", "A clear hazard-risk-control distinction and a source-backed legal summary.", "Move from the checklist to the concepts it depends on.", "Responsibility comes next because a process only works when somebody competent owns it.", featured_snippet=True),
            section(3, "body_explanation", "Who should carry out a workplace risk assessment?", 190, "Explain competence and retained employer responsibility without legal overreach.", "External help does not transfer the employer's duty.", "Who is competent to complete the assessment?", "A proportionate choice between internal competence and outside help.", "The legal duty establishes why the assessment exists.", "With ownership settled, the reader can work through the five steps.", featured_snippet=True),
            section(4, "body_how_to", "How to carry out a workplace risk assessment in 5 steps", 760, "Translate each HSE step into a mobile service-business action and decision.", "Every step hands useful information to the next person.", "How do I carry out the assessment from hazard identification through review?", "Five operational steps with owners, deadlines, stop conditions and review triggers.", "The responsible person now needs a sequence to follow.", "The worked example then shows the sequence as one connected decision.", links=["https://www.bigchange.com/blog/work-orders-what-are-they-and-best-practices", "https://www.bigchange.com/blog/ppm-schedule"], featured_snippet=True),
            section(5, "body_how_to", "Workplace risk assessment example: an engineer using a ladder", 410, "Use one customer-site ladder task to map hazards, affected people, controls, actions and review.", "A completed example reveals what generic templates leave blank.", "What does a completed workplace risk assessment example look like?", "A self-contained table mapped to all five steps plus an inclusion checklist.", "The five-step instructions become concrete in one field task.", "After the example, the guide moves from document content to ongoing management.", data=["ladder-customer-site-example"], featured_snippet=True),
            section(6, "body_explanation", "How to make workplace risk assessments easier to manage", 390, "Connect point-of-work checks, evidence and corrective action without overstating product outcomes.", "Digitising a form matters only if the decision stays connected to the job.", "How can a mobile team keep assessments current and actionable?", "A practical job-linked workflow, the Clearground experience story and the approved commercial transition.", "The worked example identifies the information that now needs a durable route.", "The conclusion returns the software discussion to one operational next step.", data=["point-of-work-action-route"], links=["https://www.bigchange.com/blog/job-tracking-for-field-services-tips", "https://www.bigchange.com/features/risk-assessment", "https://www.bigchange.com/success-stories/bigchange-helps-clearground-clean-up-on-workforce-health-and-safety"], cta="contextual_product", mini_story=True),
            section(7, "conclusion", "Keep workplace risk assessments part of the job, not extra admin", 150, "Close with one recurring-task implementation route rather than a sales CTA.", "Start with one recurring task the team performs this week.", "What should I do first?", "A specific, low-friction next action.", "The digital workflow makes the assessment retrievable.", "The FAQs settle four brief-approved questions.", next_action="educational_next_step"),
            section(8, "faq", "Frequently Asked Questions", 300, "Answer all four brief-approved questions directly in 40 to 60 words with first-paragraph support where factual or legal.", "Direct answers make the page reusable after the first read.", "What are the concise answers to the most common assessment questions?", "Four standalone answers with compliant source links.", "The conclusion gives the action; the FAQ gives quick reference answers.", None, featured_snippet=True),
        ],
    }


def build_fulfillment() -> dict[str, object]:
    article = ARTICLE.read_text(encoding="utf-8")
    excerpts = [
        ("five-step-field-checklist", "| 1. Identify hazards | What presents a risk of injury or ill health here? |"),
        ("ladder-customer-site-example", "| Identify hazards | Fall from height, damaged or unsuitable ladder, unstable surface, people entering the work area | Confirm whether another method avoids work at height, then inspect the site and equipment before setup |"),
        ("point-of-work-action-route", "A practical digital process gives the business a way to:"),
    ]
    for _, excerpt in excerpts:
        if excerpt not in article:
            raise ValueError(f"Fulfillment excerpt is not visible in the article: {excerpt}")
    return {
        "schema": "simpro-blog-plan-fulfillment/v1",
        "editorial_plan_sha256": sha256(PLAN),
        "article_sha256": sha256(ARTICLE),
        "contributions": [
            {"contribution_id": contribution_id, "actual_excerpt": excerpt}
            for contribution_id, excerpt in excerpts
        ],
    }


def main() -> int:
    if not ARTICLE.exists():
        raise FileNotFoundError(ARTICLE)
    BRIEF.write_text(build_brief(), encoding="utf-8")
    write_json(KEYWORD, build_keyword_decision())
    write_json(
        SERP_BLOCKER,
        {
            "schema": "simpro-serp-evidence-blocker/v1",
            "query": PRIMARY,
            "market": "UK",
            "date": DATE,
            "attempts": 2,
            "blockers": [
                "DataForSEO credentials are unavailable.",
                "Playwright CLI did not retain the required default browser session after browser installation and explicit open attempts.",
            ],
            "supplemental_research": "A current web search confirmed HSE guidance and general-article/template result patterns but is not represented as an approved attested SERP collector artifact.",
            "required_recovery": "Generate an attested simpro-serp-evidence/v1 artifact with an approved repository collector, then regenerate the frozen plan and downstream hashes.",
            "status": "blocked",
        },
    )
    write_json(PLAN, build_plan())
    SIDECAR.write_text(build_sidecar(), encoding="utf-8")
    write_json(FULFILLMENT, build_fulfillment())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
