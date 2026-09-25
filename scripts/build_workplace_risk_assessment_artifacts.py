"""Build proof-sensitive planning artifacts for the BigChange risk-assessment rewrite."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from data_sources.modules.semrush_keyword_decision_guard import (
    SOURCE_BOUNDARY,
    build_keyword_decision as build_semrush_keyword_decision,
)


DATE = "2026-09-25"
SLUG = "workplace-risk-assessment"
ARTICLE = ROOT / "rewrites" / f"{SLUG}-rewrite-{DATE}.md"
PLAN = ROOT / "research" / f"editorial-plan-{SLUG}-{DATE}.json"
KEYWORD = ROOT / "research" / f"semrush-keyword-decision-{SLUG}-{DATE}.json"
BRIEF = ROOT / "research" / f"content-brief-{SLUG}-{DATE}.md"
SIDECAR = ROOT / "research" / f"validation-{SLUG}-{DATE}.md"
FULFILLMENT = ROOT / "research" / f"blog-plan-fulfillment-{SLUG}-{DATE}.json"
SERP_BLOCKER = ROOT / "research" / f"serp-evidence-blocker-{SLUG}-{DATE}.json"
SEMRUSH_UI = ROOT / "research" / f"semrush-ui-{SLUG}-{DATE}.txt"

TITLE = "Workplace Risk Assessment: How to Identify, Control and Record Risks in 5 Steps"
PRIMARY = "workplace risk assessment"
SECONDARY = [
    "workplace risk assessments",
    "what is a risk assessment",
    "risk assessment example",
    "risk assessment meaning",
]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def section(
    number: int,
    kind: str,
    heading: str,
    words: int,
    angle: str,
    hook: str,
    question: str,
    payoff: str,
    previous: str | None,
    following: str | None,
    *,
    gaps: list[str] | None = None,
    data: list[str] | None = None,
    links: list[str] | None = None,
    cta: str | None = None,
    next_action: str | None = None,
    mini_story: bool = False,
    featured_snippet: bool = False,
) -> dict[str, object]:
    return {
        "section_number": number,
        "type": kind,
        "heading": heading,
        "word_target": words,
        "strategic_angle": angle,
        "engagement_hook": hook,
        "reader_question": question,
        "section_payoff": payoff,
        "bridge_from_previous": previous,
        "bridge_to_next": following,
        "knowledge_gaps": gaps or [],
        "unique_data": data or [],
        "internal_links": links or [],
        "cta": cta,
        "next_action": next_action,
        "mini_story": mini_story,
        "featured_snippet": featured_snippet,
    }


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


def build_sidecar() -> str:
    selector = ROOT / "research" / f"nonvault-customer-proof-selector-evidence-{SLUG}-{DATE}.json"
    pillar = ROOT / "context" / "commercial-pillar-index.json"
    proof_index = ROOT / "context" / "customer-proof-index.json"
    ledger = ROOT / "context" / "customer-proof-usage-ledger.json"
    return f"""# Validation sidecar: workplace risk assessment

Date: {DATE}
Article: `rewrites/{SLUG}-rewrite-{DATE}.md`
Workflow mode: rewrite

## Context Binding

- Decision: nonconnector
- Brand: BigChange
- Market: UK
- Reason: The final artifact is BigChange-owned and contains no Simpro signal.
- Vault context request, context pack, context receipt, Fred authority evidence and vault-dependent customer-proof evidence: omitted by policy.
- Status: aligned

## Release Status

- Article word target: 2,200 to 2,500 words.
- Canonical URL: https://www.bigchange.com/blog/how-to-conduct-a-workplace-risk-assessment
- Named author: none supplied. Public frontmatter omits `author`; schema notes omit `Person as author`.
- Displayed update date: {DATE}.
- Publication date retained separately as 2021-11-19.
- Status: pending deterministic release gates.

## Semrush UI Keyword Evidence

- Source: user-approved UK desktop Semrush UI evidence dated {DATE}.
- Primary: workplace risk assessment, volume 720, KD 33.
- Plural variation: workplace risk assessments, volume 590, KD 29.
- Definition target: what is a risk assessment, volume 4,400, KD 27.
- Example target: risk assessment example, volume 1,900, KD 22.
- Semantic support: risk assessment meaning, volume 1,300, KD 60.
- Commercial-pillar query: risk assessment software, volume 1,300, KD 19.
- Keyword decision: `research/semrush-keyword-decision-{SLUG}-{DATE}.json`.

## SERP Evidence

- Query: `workplace risk assessment`.
- Market/device: United Kingdom desktop.
- Collector: `research_serp_analysis:chrome_connector`.
- Raw capture: `research/serp-chrome-raw-workplace-risk-assessment-{DATE}.json`.
- Evidence: `research/serp-evidence-workplace-risk-assessment-{DATE}.json`.
- Observed pattern: HSE and Acas guidance lead the visible organic results; the page also shows an AI Overview, a five-step answer pattern and an HSE template result.
- Editorial use: immediate definition, early five-step checklist, current UK requirements, a worked example and reusable record-and-review workflow.
- Status: verified.

## Commercial Strategy

- Destination ID: `bigchange-uk-feature-risk-assessment-software`.
- URL: https://www.bigchange.com/features/risk-assessment
- Article intent: informational process guide.
- Destination intent: risk-assessment software feature page.
- Planned H2: `How to make workplace risk assessments easier to manage`.
- Required contiguous anchor: `risk assessment software`.
- Commercial-pillar index SHA-256: `{sha256(pillar)}`.
- Status: aligned.

## Non-Vault Proof Eligibility Decision

- Contract: `simpro-nonvault-customer-proof-selector-evidence/v1`.
- Evidence: `research/nonvault-customer-proof-selector-evidence-{SLUG}-{DATE}.json`.
- Evidence SHA-256: `{sha256(selector)}`.
- Customer-proof index SHA-256: `{sha256(proof_index)}`.
- Usage-ledger SHA-256: `{sha256(ledger)}`.
- Result: Clearground is approved for a paraphrased same-paragraph customer-story use.

## Customer Proof Slate

- Selector command: `python data_sources/modules/nonvault_customer_proof_selector.py "workplace risk assessment" --brand BigChange --title "Workplace Risk Assessment: How to Identify, Control and Record Risks in 5 Steps" --objective "Help UK service-business managers carry out, record, and review a practical workplace risk assessment, then show how digital risk-assessment software can keep the process inside the job workflow." --article-slug "how-to-conduct-a-workplace-risk-assessment" --roles metric,quote,theme,experience_story --require-eeat-story --selected "theme=bigchange-customer-story-clearground-dynamic-risk-assessments" --selected "experience_story=bigchange-customer-story-clearground-dynamic-risk-assessments" --limit 10 --reference-date 2026-09-25 --slate --evidence-output research/nonvault-customer-proof-selector-evidence-workplace-risk-assessment-2026-09-25.json`.
- Selector evidence: research/nonvault-customer-proof-selector-evidence-{SLUG}-{DATE}.json | SHA-256: {sha256(selector)}
- Role: metric | Top candidates: [none] | Selected: [none] | Rejected stronger candidates: [none]
- Role: quote | Top candidates: [none] | Selected: [none] | Rejected stronger candidates: [none]
- Role: theme | Top candidates: [bigchange-customer-story-clearground-dynamic-risk-assessments, bigchange-customer-story-hodge-clemco-paperless-jobs, review-capterra-bigchange-hannah-construction-one-system-workflow, bigchange-customer-story-htf-transport-job-scheduling, bigchange-customer-story-precision-fm-scheduling-sla, bigchange-customer-story-warmzilla-digital-job-sheet-lifecycle, bigchange-customer-story-blackhall-plumbing-job-lifecycle, bigchange-customer-story-cc-is-paperless-job-cards, bigchange-customer-story-trents-drains-digital-job-cards, review-capterra-bigchange-alexina-office-manager-job-lifecycle] | Selected: [bigchange-customer-story-clearground-dynamic-risk-assessments] | Rejected stronger candidates: [none]
- Role: experience_story | Top candidates: [bigchange-customer-story-clearground-dynamic-risk-assessments, review-capterra-bigchange-hannah-construction-one-system-workflow, bigchange-customer-story-warmzilla-digital-job-sheet-lifecycle, bigchange-customer-story-cc-is-paperless-job-cards, bigchange-customer-story-trents-drains-digital-job-cards, review-capterra-bigchange-alexina-office-manager-job-lifecycle] | Selected: [bigchange-customer-story-clearground-dynamic-risk-assessments] | Rejected stronger candidates: [none]

## Customer Proof Selection Decision

- Selector command: the hash-bound non-vault selector command recorded in Customer Proof Slate.
- Selected proof: `bigchange-customer-story-clearground-dynamic-risk-assessments` | Roles: theme, experience_story.
- Rejected stronger candidates: [none; Clearground is the selector's top-ranked candidate for both selected roles].
- Evaluated alternatives: Mardon was weaker because its strongest proof concerns vehicle checks and safety reporting; CC Infrastructure Services concerns paperless job cards and photographic records; GEM concerns compliance records and asset information; approved Capterra stories have recent repository use and weaker risk-assessment fit.
- Final use in copy: one restrained, same-paragraph paraphrase in `How to make workplace risk assessments easier to manage`.

## Selected Customer Proof Mining

- Proof: bigchange-customer-story-clearground-dynamic-risk-assessments | URL: https://www.bigchange.com/success-stories/bigchange-helps-clearground-clean-up-on-workforce-health-and-safety
- Source: https://www.bigchange.com/success-stories/bigchange-helps-clearground-clean-up-on-workforce-health-and-safety
- Checked: {DATE}.
- Checked for: exact quotes, metrics, customer POV or story, workflow theme, and measured outcomes.
- Usable quotes found: none used because the article does not need testimonial wording.
- Usable metrics found: none found for the selected workflow claim.
- Usable POV/story found: Clearground uses customised dynamic risk assessments which operatives complete on site before work.
- Recommended use: restrained paraphrase of the point-of-work workflow with a same-paragraph source link.
- Final use in copy: paraphrased experience story in `How to make workplace risk assessments easier to manage`.
- Excluded proof: exact customer quote, named-person attribution, metric, certification claim, comparison and measured safety outcome were excluded because they do not improve this section's practical workflow explanation.
- Status: approved

## Customer Proof Pack

- Proof ID: `bigchange-customer-story-clearground-dynamic-risk-assessments`.
- Customer: Clearground.
- URL: https://www.bigchange.com/success-stories/bigchange-helps-clearground-clean-up-on-workforce-health-and-safety
- Approved use: paraphrased point-of-work experience story only.
- Evidence: The public story describes customised dynamic risk assessments which operatives complete on site before work.
- Status: approved.

## Review Site Theme Selection

- Capterra page checked: https://www.capterra.com/p/149479/JobWatch-powered-by-BigChange/reviews/
- Research boundary: relevant four- and five-score snippets were reviewed as private audience language only.
- Public use: none.
- Reason: live snippets are not approved proof rows; approved Capterra stories are repeatedly used and weaker topical matches.
- Prohibited: ratings, aggregate score, exact snippet, named review claim and implied risk-assessment outcome.

## Video Review Decision

- Source: https://www.youtube.com/watch?v=_YXifF-nLxA
- Checked: {DATE}.
- Decision: reject embed.
- Reason: published in 2019 and no usable transcript or captions were available for claim verification.
- `VideoObject`: omitted because no video is embedded.

## Source Map

- Claim: The British Safety Council's risk assessment certificate specification frames the process around identifying, evaluating and controlling risks. In day-to-day service work, look beyond a standard job description. Access, equipment, other contractors, customers and changing site conditions all shape how the team performs the work. | Claim type: definitional | URL: https://www.britsafe.org/media/ddyfkihf/british-safety-council-certificate-in-risk-assessment.pdf | Evidence: identifying hazards, evaluating risks, and controlling risks | Evidence relation: directly_supports | Source class: non_competing_expert | Classification artifact: research/source-classifications/workplace-risk-assessment/source-classification-20a68a13abaab13c25ec1a7ce12532191166c91e1cc7e1b74e4fe7d7c3c42f3e.json | Classification hash: c7de304d8bd4e8c24254058ae7805283228bdc6b8bc2e5b19642809e272bd11d | Original-source status: original | Source date: historical | Checked date: {DATE} | Claim fit: direct | Freshness decision: historical_scoped | Freshness reason: The 2020 certificate specification supports stable process terminology while current legal claims remain sourced to HSE | Status: approved | Intended use: definition section
- Claim: Under the Health and Safety Executive's risk-management guidance, UK employers and self-employed people have a duty to assess risks created by their work and take suitable steps to control them. Its scope needs to be proportionate to the work and good enough to protect people from foreseeable harm. For an organisation with five or more people, the significant findings belong in a written record. | Claim type: regulation | URL: https://www.hse.gov.uk/simple-health-safety/risk/steps-needed-to-manage-risk.htm | Evidence: If you employ 5 or more people, you must record your significant findings | Source class: regulator | Original-source status: original | Source date: 2024-06-10 | Checked date: {DATE} | Claim fit: direct | Freshness decision: current | Freshness reason: HSE updated the live guidance on 2024-06-10 and it was checked on the article update date | Status: approved | Intended use: legal requirements
- Claim: The employer remains responsible for managing health and safety. The employer, a competent worker or an external adviser completes the assessment. That person's skills, knowledge and experience cover the relevant hazards, risk judgements and suitable controls. The actual task and conditions, not the job title alone, determine the competence required. | Claim type: regulation | URL: https://www.hse.gov.uk/simple-health-safety/gettinghelp/ | Evidence: They should have the skills, knowledge and experience to be able to recognise hazards in your business | Source class: regulator | Original-source status: original | Source date: 2024-06-04 | Checked date: {DATE} | Claim fit: direct | Freshness decision: current | Freshness reason: HSE updated the live guidance on 2024-06-04 and it was checked on the article update date | Status: approved | Intended use: competent-person section
- Claim: HSE guidance on appointing a competent person permits an employer to appoint themselves, one or more workers, or somebody from outside the business. Where suitable competence exists internally, HSE says to use it. Outside advice suits complex, unusual or high-risk work, but outsourcing the task does not transfer the employer's legal duty. | Claim type: regulation | URL: https://www.hse.gov.uk/simple-health-safety/gettinghelp/ | Evidence: But remember, as the employer, managing health and safety will still be your legal duty. | Source class: regulator | Original-source status: original | Source date: 2024-06-04 | Checked date: {DATE} | Claim fit: direct | Freshness decision: current | Freshness reason: HSE updated the live guidance on 2024-06-04 and it was checked on the article update date | Status: approved | Intended use: competent-person section
- Claim: Consider both likelihood and severity, taking existing precautions into account. Address the most serious risks first. The HSE five-step process advises redesigning the job, replacing materials, machinery or processes, organising work to limit exposure, introducing practical safety measures and using personal protective equipment when further controls apply. | Claim type: process | URL: https://www.hse.gov.uk/simple-health-safety/risk/steps-needed-to-manage-risk.htm | Evidence: If you need further controls, consider: redesigning the job, replacing the materials, machinery or process | Evidence relation: directly_supports | Source class: primary_authority | Classification artifact: research/source-classifications/workplace-risk-assessment/source-classification-bb64f0b75e50e538aa268d2160e5d749e12c48f0b966fa56ebb52f5a3170e276.json | Classification hash: 1b2414db4db730cd5cb38b8651f2e103f07948afeeda59e4797c59a63f5d513c | Original-source status: original | Source date: 2024-06-10 | Checked date: {DATE} | Claim fit: direct | Freshness decision: current | Freshness reason: HSE updated the live guidance on 2024-06-10 and it was checked on the article update date | Status: approved | Intended use: evaluate-risk step
- Claim: Use the fields in the HSE risk assessment template: significant hazards, affected groups, existing controls and further actions. Give every further action an owner and a deadline. If the job cannot proceed until the action is complete, make that stop condition explicit. A risk assessment that identifies a problem but leaves it unowned has not controlled the risk. | Claim type: process | URL: https://www.hse.gov.uk/simple-health-safety/risk/risk-assessment-template-and-examples.htm | Evidence: what further action you need to take to control the risks, who needs to carry out the action, when the action is needed by | Evidence relation: directly_supports | Source class: primary_authority | Classification artifact: research/source-classifications/workplace-risk-assessment/source-classification-dfae287164e5bd9a49d8a289fe5a1f78741f751c6a5d9e8479bdedf7fc8a7cfc.json | Classification hash: a4fa110402e079b778437bb7c315f9400cef98d795b937ea04dbe86fe4399b4b | Original-source status: original | Source date: 2024-06-10 | Checked date: {DATE} | Claim fit: direct | Freshness decision: current | Freshness reason: HSE updated the live guidance on 2024-06-10 and it was checked on the article update date | Status: approved | Intended use: recording step
- Claim: For ladder safety, the HSE ladder guidance says ladders are not automatically the first choice and sets out the right ladder and sensible precautions. When task duration, height or environment changes, reassess the equipment and controls. | Claim type: process | URL: https://www.hse.gov.uk/work-at-height/ladders/index.htm | Evidence: they should not automatically be your first choice. There are simple, sensible precautions you should take | Evidence relation: directly_supports | Source class: primary_authority | Classification artifact: research/source-classifications/workplace-risk-assessment/source-classification-38572b8f8da35c4763b3cb042056c56833f77690964a995817572360dcdb859a.json | Classification hash: 394196a6edef86ff8b01f8d2b66fa3a8e47a05361c060daf5e63ac2dad1e01f2 | Original-source status: original | Source date: 2024-06-05 | Checked date: {DATE} | Claim fit: direct | Freshness decision: current | Freshness reason: HSE updated the live guidance on 2024-06-05 and it was checked on the article update date | Status: approved | Intended use: worked example qualification
- Claim: What should a workplace risk assessment include? The HSE says you can use its risk assessment template to keep a simple record of who might be harmed and how. | Claim type: recommendation | URL: https://www.hse.gov.uk/simple-health-safety/risk/risk-assessment-template-and-examples.htm | Evidence: You can use a risk assessment template to help you keep a simple record of: who might be harmed and how | Evidence relation: directly_supports | Source class: primary_authority | Classification artifact: research/source-classifications/workplace-risk-assessment/source-classification-dfae287164e5bd9a49d8a289fe5a1f78741f751c6a5d9e8479bdedf7fc8a7cfc.json | Classification hash: a4fa110402e079b778437bb7c315f9400cef98d795b937ea04dbe86fe4399b4b | Original-source status: original | Source date: undated | Checked date: {DATE} | Claim fit: direct | Freshness decision: historical_scoped | Freshness reason: The live HSE guidance is undated and was checked on the article update date | Status: approved | Intended use: direct answer box
- Claim: A workplace risk assessment is a systematic way to identify hazards, identify the people at risk, judge the risk level and select controls. Its purpose is practical action. The work isn't complete simply because somebody filled in a form or selected a risk score. It turns observation into a clear work decision. | Claim type: process | URL: https://www.hse.gov.uk/simple-health-safety/risk/steps-needed-to-manage-risk.htm | Evidence: Risk management is a step-by-step process for controlling health and safety risks caused by hazards in the workplace. | Source class: primary_authority | Original-source status: original | Source date: 2024-06-10 | Checked date: {DATE} | Claim fit: direct | Freshness decision: current | Freshness reason: HSE updated the live guidance on 2024-06-10 and it was checked on the article update date | Status: approved | Intended use: definition section
- Claim: The British Safety Council's risk assessment certificate specification frames the process around identifying, evaluating and controlling risks. In day-to-day service work, that means looking beyond a standard job description. Access, equipment, other contractors, customers and changing site conditions all shape how the team performs the work. | Claim type: definitional | URL: https://www.britsafe.org/media/ddyfkihf/british-safety-council-certificate-in-risk-assessment.pdf | Evidence: The specification lists identifying, evaluating and controlling risks as learning outcomes | Source class: non_competing_expert | Original-source status: original | Source date: historical | Checked date: {DATE} | Claim fit: direct | Freshness decision: historical_scoped | Freshness reason: The 2020 certificate specification supports stable process terminology while current legal claims remain sourced to HSE | Status: approved | Intended use: definition section
- Claim: A hazard is something with the potential to cause harm. Risk combines the likelihood of harm with the outcome's possible severity. Keeping these ideas separate makes an assessment more useful because the hazard tells you what to examine, while the risk helps you prioritise action. Controls break that chain before harm occurs. | Claim type: definitional | URL: https://www.hse.gov.uk/simple-health-safety/risk/steps-needed-to-manage-risk.htm | Evidence: decide how likely it is that someone could be harmed and how serious it could be | Source class: primary_authority | Original-source status: original | Source date: undated | Checked date: {DATE} | Claim fit: direct | Freshness decision: historical_scoped | Freshness reason: The live HSE guidance is undated and was checked on the article update date | Status: approved | Intended use: hazard and risk comparison
- Claim: Under the Health and Safety Executive's risk-management guidance, UK employers and self-employed people must assess risks created by their work and take suitable steps to control them. Its scope needs to be proportionate to the work and good enough to protect people from foreseeable harm. If the organisation employs five or more people, it must record its significant findings. | Claim type: regulation | URL: https://www.hse.gov.uk/simple-health-safety/risk/steps-needed-to-manage-risk.htm | Evidence: If you employ 5 or more people, you must record your significant findings | Source class: regulator | Original-source status: original | Source date: undated | Checked date: {DATE} | Claim fit: direct | Freshness decision: historical_scoped | Freshness reason: The live HSE guidance is undated and was checked on the article update date | Status: approved | Intended use: legal requirements
- Claim: The Health and Safety Executive's risk-management guidance says the record covers the hazards, the people at risk and what the business is doing to control the risks. The priority remains controlling the risk in practice, not producing paperwork for its own sake. | Claim type: process | URL: https://www.hse.gov.uk/simple-health-safety/risk/steps-needed-to-manage-risk.htm | Evidence: Do not rely purely on paperwork as your main priority should be to control the risks in practice. | Source class: primary_authority | Original-source status: original | Source date: undated | Checked date: {DATE} | Claim fit: direct | Freshness decision: historical_scoped | Freshness reason: The live HSE guidance is undated and was checked on the article update date | Status: approved | Intended use: legal requirements
- Claim: The employer remains responsible for managing health and safety. The employer, a competent worker or an external adviser completes the assessment. That person needs enough skills, knowledge and experience to recognise the relevant hazards, judge the risks and recommend controls that fit the work. Competence must match the actual task and conditions. | Claim type: regulation | URL: https://www.hse.gov.uk/simple-health-safety/gettinghelp/ | Evidence: They should have the skills, knowledge and experience to be able to recognise hazards in your business | Source class: regulator | Original-source status: original | Source date: undated | Checked date: {DATE} | Claim fit: direct | Freshness decision: historical_scoped | Freshness reason: The live HSE guidance is undated and was checked on the article update date | Status: approved | Intended use: competent-person section
- Claim: HSE guidance on appointing a competent person permits an employer to appoint themselves, one or more workers, or somebody from outside the business. Where suitable competence exists internally, HSE recommends using it. External help suits complex, unusual or high-risk work, but outsourcing the task does not transfer the employer's legal duty. | Claim type: regulation | URL: https://www.hse.gov.uk/simple-health-safety/gettinghelp/ | Evidence: But remember, as the employer, managing health and safety will still be your legal duty. | Source class: regulator | Original-source status: original | Source date: undated | Checked date: {DATE} | Claim fit: direct | Freshness decision: historical_scoped | Freshness reason: The live HSE guidance is undated and was checked on the article update date | Status: approved | Intended use: competent-person section
- Claim: Consider both likelihood and severity, taking existing precautions into account. Address the most serious risks first. The HSE five-step process advises redesigning the job, replacing materials, machinery or processes, organising work to reduce exposure, introducing practical safety measures and using personal protective equipment when further controls apply. | Claim type: process | URL: https://www.hse.gov.uk/simple-health-safety/risk/steps-needed-to-manage-risk.htm | Evidence: If you need further controls, consider: | Source class: primary_authority | Original-source status: original | Source date: undated | Checked date: {DATE} | Claim fit: direct | Freshness decision: historical_scoped | Freshness reason: The live HSE guidance is undated and was checked on the article update date | Status: approved | Intended use: evaluate-risk step
- Claim: The HSE risk assessment template records the significant hazards, affected groups, existing controls and further actions. Give every further action an owner and a deadline. If the job cannot proceed until the action is complete, make that stop condition explicit. A risk assessment that identifies a problem but leaves it unowned has not controlled the risk. | Claim type: process | URL: https://www.hse.gov.uk/simple-health-safety/risk/risk-assessment-template-and-examples.htm | Evidence: You can use a risk assessment template to help you keep a simple record of: | Source class: primary_authority | Original-source status: original | Source date: undated | Checked date: {DATE} | Claim fit: direct | Freshness decision: historical_scoped | Freshness reason: The live HSE guidance is undated and was checked on the article update date | Status: approved | Intended use: recording step
- Claim: This example shows how the five steps connect for a maintenance engineer using a portable ladder at a customer site. It is an illustration, not a substitute for assessing the real job. HSE permits ladders for low-risk, short-duration work with the right equipment and precautions. Treat each visit as a fresh site decision. | Claim type: process | URL: https://www.hse.gov.uk/work-at-height/ladders/index.htm | Evidence: ladders can be a sensible and practical option for low-risk, short-duration tasks | Source class: primary_authority | Original-source status: original | Source date: undated | Checked date: {DATE} | Claim fit: direct | Freshness decision: historical_scoped | Freshness reason: The live HSE guidance is undated and was checked on the article update date | Status: approved | Intended use: worked example introduction
- Claim: For ladder safety, the HSE ladder guidance explains that ladders are not automatically the first choice and requires the right ladder and sensible precautions. Changes in task duration, height or environment require a fresh equipment and control decision. | Claim type: process | URL: https://www.hse.gov.uk/work-at-height/ladders/index.htm | Evidence: they should not automatically be your first choice | Source class: primary_authority | Original-source status: original | Source date: undated | Checked date: {DATE} | Claim fit: direct | Freshness decision: historical_scoped | Freshness reason: The live HSE guidance is undated and was checked on the article update date | Status: approved | Intended use: worked example qualification
- Claim: What should a workplace risk assessment include? | Claim type: recommendation | URL: https://www.hse.gov.uk/simple-health-safety/risk/risk-assessment-template-and-examples.htm | Evidence: You can use a risk assessment template to help you keep a simple record of: | Source class: primary_authority | Original-source status: original | Source date: undated | Checked date: {DATE} | Claim fit: direct | Freshness decision: historical_scoped | Freshness reason: The live HSE guidance is undated and was checked on the article update date | Status: approved | Intended use: direct answer box
- Claim: Clearground's BigChange story shows the workflow in practice: each operative completes a customised dynamic risk assessment on site, prompting them to consider the environment and its risks before working. That is the operational goal: the assessment changes the decision at the point of work. | Claim type: customer_proof | URL: https://www.bigchange.com/success-stories/bigchange-helps-clearground-clean-up-on-workforce-health-and-safety | Evidence: BigChange's public Clearground story describes the point-of-work assessment workflow | Source class: customer_proof | Original-source status: original | Source date: undated | Checked date: {DATE} | Claim fit: direct | Freshness decision: historical_scoped | Freshness reason: The public customer story is undated and was checked on the article update date | Status: approved | Intended use: paraphrased digital-workflow experience story

## FAQ Source Policy

- Allowed source classes: neutral, non_competing_expert, owned_product.
- Competitor-owned FAQ sources: prohibited.
- Status: aligned.

## FAQ Proof Map

- FAQ: What is a risk assessment in the workplace? | URL: https://www.hse.gov.uk/simple-health-safety/risk/steps-needed-to-manage-risk.htm | Source class: neutral | Competitor check: passed | Support: Hazard, people, evaluation, recording and review sequence.
- FAQ: What are the 5 steps of a workplace risk assessment? | URL: https://www.hse.gov.uk/simple-health-safety/risk/steps-needed-to-manage-risk.htm | Source class: neutral | Competitor check: passed | Support: Five-step sequence.
- FAQ: How often should a workplace risk assessment be reviewed? | URL: https://www.hse.gov.uk/simple-health-safety/risk/steps-needed-to-manage-risk.htm | Source class: neutral | Competitor check: passed | Support: Change, problem, accident and near-miss triggers.
- FAQ: Does a workplace risk assessment need to be written down? | URL: https://www.hse.gov.uk/simple-health-safety/risk/risk-assessment-template-and-examples.htm | Source class: neutral | Competitor check: passed | Support: Significant findings and record fields.

## PAA/FAQ Provenance

- Source: brief_paa
- Artifact: `research/content-brief-{SLUG}-{DATE}.md`
- Selected questions:
  - What is a risk assessment in the workplace?
  - What are the 5 steps of a workplace risk assessment?
  - How often should a workplace risk assessment be reviewed?
  - Does a workplace risk assessment need to be written down?

## Image Inventory

- `workplace-risk-assessment-5-steps.webp`: original five-step field-service safety illustration; standalone reader-visible marker present.
- `workplace-risk-assessment-example-ladder.webp`: original ladder example illustration; standalone reader-visible marker present.
- `digital-workplace-risk-assessment-field-service.webp`: original point-of-work mobile assessment illustration; standalone reader-visible marker present.
- Existing unrelated hero image: removed from the handoff.
- Upload boundary: create, resize and compress before CMS upload.

## Internal Link Plan

- https://www.bigchange.com/features/risk-assessment with exact anchor `risk assessment software`.
- https://www.bigchange.com/blog/work-orders-what-are-they-and-best-practices in corrective-action recording.
- https://www.bigchange.com/blog/ppm-schedule in planned review cadence.
- https://www.bigchange.com/blog/job-tracking-for-field-services-tips in digital management.
- Clearground public customer story in the E-E-A-T passage.
- EICR and building-maintenance-bid links rejected as not directly useful to this general guide.
- Legacy `/compliance` CTA rejected because it resolves to unrelated information-security content.

## Author and Schema Decision

- Author policy: no_author
- Named author supplied: no
- Public frontmatter author: omitted
- No named author was supplied.
- Public frontmatter omits `author`.
- Schema notes include `BlogPosting`, `BreadcrumbList`, `FAQPage`, nested `Question` and `Answer`, `ImageObject`, and `Organization` as publisher reference only.
- `Person as author` and `VideoObject` are omitted.

## Reader-Facing Boundary

- Public copy contains no workflow commentary, proof-selection rationale, schema instruction, score or release status.
- Reader-visible media markers follow the required normalized image format.
- No rating, aggregate review score, exact review snippet or named review claim is published.
"""


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
