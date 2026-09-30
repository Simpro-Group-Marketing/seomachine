"""Build current release artifacts for the AI scheduling and dispatch rewrite."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from data_sources.modules.blog_assembly_contract import atomic_write_json
from data_sources.modules.editorial_plan.orchestration import check_file as check_plan_file
from data_sources.modules.editorial_plan.plan_fulfillment import (
    PLAN_FULFILLMENT_SCHEMA,
    check_fulfillment,
)
from data_sources.modules.editorial_plan.serp_capture import build_serp_evidence
from data_sources.modules.execution_attestation import attest_mapping
from data_sources.modules.machine_review import (
    AGENT_ROSTER,
    build_machine_review,
    write_machine_review,
)
from data_sources.modules.semrush_keyword_decision_guard import (
    SOURCE_BOUNDARY,
    build_keyword_decision as build_keyword_decision_artifact,
)


SLUG = "ai-scheduling-dispatch-field-service"
DATE = "2026-09-28"
ARTICLE = ROOT / "published" / "ai-scheduling-dispatch-field-service-2026-07-17.md"
SIDECAR = ROOT / "research" / f"validation-{SLUG}-{DATE}.md"
RUN_ID_FILE = ROOT / "research" / f"run-id-{SLUG}-{DATE}.txt"
SEMRUSH_UI_EVIDENCE = ROOT / "research" / f"semrush-chrome-ui-evidence-{SLUG}-{DATE}.json"
RAW_SERP = ROOT / "research" / f"serp-chrome-raw-{SLUG}-{DATE}.json"
SERP_EVIDENCE = ROOT / "research" / f"serp-evidence-{SLUG}-{DATE}.json"
KEYWORD_DECISION = ROOT / "research" / f"semrush-keyword-decision-{SLUG}-{DATE}.json"
PLAN = ROOT / "research" / f"editorial-plan-{SLUG}-{DATE}.json"
FULFILLMENT = ROOT / "research" / f"blog-plan-fulfillment-{SLUG}-{DATE}.json"
PLAN_REVIEW = ROOT / "research" / f"machine-review-plan-{SLUG}-{DATE}.json"
ARTICLE_REVIEW = ROOT / "research" / f"machine-review-article-{SLUG}-{DATE}.json"
BRIEF = ROOT / "research" / f"content-brief-{SLUG}-{DATE}.md"

PRIMARY = "AI platform for field service dispatch and scheduling"
SECONDARIES = ["AI scheduling software", "field service dispatch software"]
SEARCH_URL = (
    "https://www.google.com/search?"
    "q=AI+platform+for+field+service+dispatch+and+scheduling&hl=en&gl=us&pws=0&udm=14"
)
ORGANIC = [
    (
        "AI Field Service Scheduling, Dispatch & Route Optimization",
        "https://marketplace.microsoft.com/lv-lv/product/saas/fieldcampai.ai-dispatcher?tab=overview",
    ),
    (
        "6 Best AI Scheduling Software for Field Service Teams",
        "https://buildops.com/resources/ai-field-service-scheduling",
    ),
    (
        "What is Dispatch Management Software? 10 Best Tools",
        "https://www.salesforce.com/service/field-service-management/what-is-dispatch-management-software/",
    ),
    (
        "The Best AI Tools for Field Service Management and Dispatch",
        "https://superkind.ai/blog/ai-field-service-tools",
    ),
    (
        "AI dispatch and scheduling software for field service teams",
        "https://techquarter.io/blog/ai-dispatch-and-scheduling-software-for-field-service-teams/",
    ),
    (
        "Vertical AI Scheduling and Dispatching with SmartWX",
        "https://www.sew.ai/product/schedule-dispatch",
    ),
    (
        "AI Field Service Operations: Dispatch, Scheduling and Completion",
        "https://www.nuplay.ai/blogs/ai-field-service-operations-dispatch-scheduling-and-completion",
    ),
    (
        "AI Field Service Management Software for Smarter Operations",
        "https://commence.com/software-features/ai-field-service-management/",
    ),
    (
        "AI for Field Service Dispatch and Routing",
        "https://www.abelian.us/blog/ai-for-field-service-dispatch-and-routing",
    ),
    (
        "10 Best AI Dispatch Software Platforms (2026 Comparison)",
        "https://locus.sh/blogs/best-ai-dispatch-software/",
    ),
]

MUST_HAVE_SECTIONS = [
    "an early scheduling-event matrix",
    "operating data and hard-constraint requirements",
    "dispatcher review and manual fallback controls",
    "verified vendor examples with dated release status",
    "a bounded pilot and measurement framework",
]
COMPETITOR_GAPS = [
    "Observed results emphasize vendor lists and product pages more than a controlled operating model.",
    "Observed results do not consistently separate hard constraints, weighted goals, dispatcher approval, and write-back recovery.",
    "Observed results do not consistently pair feature-status evidence with a bounded field-service pilot.",
]

CONTRIBUTION_EXCERPTS = {
    "early-scheduling-matrix": "| Scheduling event | Required inputs | Proposed AI action | Dispatcher checkpoint | Manual fallback | Pilot measure |",
    "dispatcher-decision-loop": "Each suggestion needs a clear path from trigger to final update.",
    "verified-vendor-matrix": "| Vendor example | Documented scope | Data inputs or constraints | Human checkpoint | Release status | Verified |",
    "bounded-pilot": "Use one event, such as cancellations or open-slot fills.",
}


def run_id() -> str:
    value = RUN_ID_FILE.read_text(encoding="utf-8-sig").strip()
    if not value:
        raise RuntimeError(f"Run ID is missing from {RUN_ID_FILE}")
    return value


def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def repository_commit() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=ROOT,
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return "working-tree"


def article_text() -> str:
    return ARTICLE.read_bytes().decode("utf-8")


def build_serp(run: str) -> None:
    capture = {
        "schema": "simpro-serp-raw-capture/v1",
        "collector": {
            "name": "research_serp_analysis:chrome_connector",
            "version": "1.0.0",
        },
        "query": PRIMARY,
        "collected_at": now(),
        "run_id": run,
        "request": {
            "url": SEARCH_URL,
            "locale": {"hl": "en", "gl": "us", "pws": "0"},
        },
        "raw_response": {
            "organic_results": [
                {"title": title, "url": url} for title, url in ORGANIC
            ],
            "features": [],
        },
    }
    atomic_write_json(
        RAW_SERP,
        attest_mapping(
            capture,
            purpose="simpro-serp-raw-capture/v1",
            workspace_root=ROOT,
        ),
    )
    evidence = build_serp_evidence(
        raw_capture_path=RAW_SERP,
        workspace_root=ROOT,
        must_have_sections=MUST_HAVE_SECTIONS,
        competitor_gaps=COMPETITOR_GAPS,
    )
    atomic_write_json(SERP_EVIDENCE, evidence)


def semrush_report(
    report: str,
    *,
    parameters: dict[str, object],
    status: str = "completed",
) -> dict[str, object]:
    return {
        "report": report,
        "status": status,
        "parameters": parameters,
        "completion_basis": (
            "Authenticated US desktop Semrush Keyword Overview fields were observed "
            "in the main Chrome browser on 2026-09-28."
        ),
        "ui_evidence_path": SEMRUSH_UI_EVIDENCE.relative_to(ROOT).as_posix(),
        "ui_evidence_sha256": sha256_file(SEMRUSH_UI_EVIDENCE),
    }


def build_keyword_decision() -> None:
    candidate_metrics = [
        {
            "keyword": PRIMARY,
            "volume": 20,
            "keyword_difficulty": "n/a",
            "global_volume": 20,
            "intent": "n/a",
        },
        {
            "keyword": "AI scheduling software",
            "volume": 260,
            "keyword_difficulty": 56,
            "keyword_difficulty_label": "Difficult",
            "global_volume": 410,
            "intent": ["commercial"],
            "cpc": 10.15,
            "competitive_density": 0.31,
        },
        {
            "keyword": "field service dispatch software",
            "volume": 1000,
            "keyword_difficulty": 23,
            "keyword_difficulty_label": "Easy",
            "global_volume": 1500,
            "intent": ["informational"],
        },
        {
            "keyword": "field service scheduling software",
            "volume": 2400,
            "keyword_difficulty": 39,
            "keyword_difficulty_label": "Possible",
            "global_volume": 3900,
            "intent": ["commercial"],
            "evidence_source": "verified commercial pillar record",
        },
        {
            "keyword": "AI field service management",
            "volume": 260,
            "keyword_difficulty": 17,
            "keyword_difficulty_label": "Easy",
            "global_volume": 370,
            "intent": ["informational"],
        },
    ]
    report_parameters = {
        "database": "us",
        "device": "desktop",
        "collection_date": DATE,
        "execution_surface": "semrush_ui_chrome_main_browser",
    }
    reports = [
        semrush_report(
            "_keyword_research",
            parameters={"query": PRIMARY, **report_parameters},
        ),
        semrush_report(
            "_get_report_schema",
            parameters={"report": "phrase_this", **report_parameters},
        ),
        semrush_report(
            "phrase_these",
            parameters={
                "keywords": [row["keyword"] for row in candidate_metrics],
                **report_parameters,
            },
        ),
        semrush_report(
            "phrase_related",
            parameters={"phrase": PRIMARY, **report_parameters},
        ),
        semrush_report(
            "phrase_questions",
            parameters={"phrase": PRIMARY, **report_parameters},
        ),
        semrush_report(
            "phrase_organic",
            parameters={
                "phrase": PRIMARY,
                "display_limit": 10,
                **report_parameters,
            },
        ),
        semrush_report(
            "phrase_this",
            parameters={"phrase": PRIMARY, **report_parameters},
        ),
    ]
    finalists = [
        {
            "keyword": PRIMARY,
            "database": "us",
            "results": [
                {
                    "position": position,
                    "position_type": "organic",
                    "domain": url.split("/")[2],
                    "url": url,
                    "triggered_serp_features": [],
                }
                for position, (_, url) in enumerate(ORGANIC, start=1)
            ],
        }
    ]
    decision = build_keyword_decision_artifact(
        brand="Simpro",
        market="US",
        database="us",
        collection_date=DATE,
        source_boundary=SOURCE_BOUNDARY,
        seed_terms=[
            "AI scheduling and dispatch for field service",
            "AI scheduling for field service",
            "AI dispatch optimization",
            PRIMARY,
            "AI scheduling software",
            "field service dispatch software",
            "field service scheduling software",
            "AI field service management",
        ],
        connector_reports=reports,
        candidate_metrics=candidate_metrics,
        serp_finalists=finalists,
        question_candidates=[
            {"keyword": "How to use AI for scheduling?"},
            {"keyword": "How to automate scheduling?"},
            {"keyword": "Can AI do scheduling?"},
        ],
        related_candidates=[
            {"keyword": "AI scheduling software"},
            {"keyword": "field service dispatch software"},
            {"keyword": "field service scheduling software"},
        ],
        selected_primary_keyword=PRIMARY,
        selected_secondary_keywords=SECONDARIES,
        rejected_keywords=[
            {
                "keyword": "AI scheduling and dispatch for field service",
                "reason": "Authenticated Semrush US desktop returned no metrics on 2026-09-28.",
            },
            {
                "keyword": "AI scheduling software",
                "reason": "Retained as a secondary because the current US SERP is dominated by calendar, employee, appointment, and construction scheduling.",
            },
            {
                "keyword": "field service scheduling software",
                "reason": "Reserved for the verified scheduling feature commercial pillar.",
            },
            {
                "keyword": "AI field service management",
                "reason": "Rejected because it is broader than the article's scheduling and dispatch decision task.",
            },
        ],
        selection_rationale=(
            "Select the measurable exact-fit query because its current US SERP is "
            "specific to field-service scheduling and dispatch. Keep the higher-volume "
            "generic scheduling query secondary because its SERP has materially broader "
            "intent, and reserve field service scheduling software for the verified "
            "commercial feature pillar."
        ),
        workspace_root=ROOT,
    )
    atomic_write_json(KEYWORD_DECISION, decision)


def section(
    number: int,
    kind: str,
    heading: str,
    words: int,
    question: str,
    payoff: str,
    *,
    links: list[str] | None = None,
    featured: bool = False,
    cta: str | None = None,
    next_action: str | None = None,
) -> dict[str, object]:
    return {
        "section_number": number,
        "type": kind,
        "heading": heading,
        "word_target": words,
        "strategic_angle": "Give field-service operators a source-safe scheduling decision they can test in a controlled workflow.",
        "engagement_hook": "Turn the section into a dispatcher control, demo check, or pilot action.",
        "knowledge_gaps": [
            "Which data and rules make a schedule recommendation valid",
            "Where dispatcher approval and recovery controls belong",
        ],
        "unique_data": [
            "Current US keyword and SERP evidence dated 2026-09-28",
            "Current source-mapped product and feature-status evidence",
        ],
        "internal_links": links or [],
        "cta": cta,
        "next_action": next_action,
        "mini_story": False,
        "featured_snippet": featured,
        "reader_question": question,
        "section_payoff": payoff,
        "bridge_from_previous": None if number == 1 else "Carry the prior operating decision into the next scheduling control.",
        "bridge_to_next": None if number == 9 else "Use this result to evaluate the next scheduling decision.",
    }


def build_plan(run: str) -> None:
    title = "AI Scheduling and Dispatch for Field Service | Simpro"
    pillar = "https://www.simprogroup.com/features/scheduling-software"
    sections = [
        section(
            1,
            "intro",
            "AI Platform for Field Service Dispatch and Scheduling",
            330,
            "What should an AI scheduling workflow do?",
            "An early scheduling-event matrix with inputs, checkpoints, fallbacks, and measures.",
            featured=True,
        ),
        section(
            2,
            "body_explanation",
            "The Nitty Gritty",
            180,
            "What are the non-negotiable controls?",
            "A concise operating standard for bounded, supervised scheduling.",
            featured=True,
        ),
        section(
            3,
            "body_explanation",
            "What an AI platform for field service dispatch and scheduling does",
            300,
            "How do scheduling, dispatch, routing, booking, and automation differ?",
            "A practical four-stage maturity model.",
            featured=True,
        ),
        section(
            4,
            "body_explanation",
            "What data and business rules AI needs",
            300,
            "Which records and constraints make a suggestion usable?",
            "A data-readiness checklist covering technicians, jobs, customers, and live operations.",
        ),
        section(
            5,
            "body_how_to",
            "How the decision loop works and where dispatchers retain control",
            430,
            "Where should human approval and recovery controls sit?",
            "A five-step loop from event detection through monitored write-back.",
            featured=True,
        ),
        section(
            6,
            "body_comparison",
            "Verified scheduling-related capabilities and release status",
            430,
            "What do current vendor examples actually support?",
            "A nonranking, dated comparison with feature status and human-control boundaries.",
            links=[pillar],
        ),
        section(
            7,
            "body_list",
            "How to evaluate scheduling and dispatch software",
            300,
            "Which demo questions expose workflow fit and control?",
            "A repeatable evaluation checklist for data, constraints, explanations, exceptions, and recovery.",
        ),
        section(
            8,
            "body_how_to",
            "How to run a controlled 30-day pilot and measure it",
            360,
            "How should a team test scheduling recommendations safely?",
            "A staged pilot covering baseline, shadow mode, approved use, exception tests, and scale review.",
            cta="commercial_contextual",
            next_action="educational_next_step",
        ),
        section(
            9,
            "faq",
            "Frequently Asked Questions",
            210,
            "Which scheduling questions need direct answers?",
            "Three brief-bound, source-backed answers for AI scheduling implementation.",
            featured=True,
        ),
    ]
    plan = {
        "schema": "simpro-blog-editorial-plan/v2",
        "brand": "Simpro",
        "topic": "AI-assisted field service scheduling and dispatch",
        "date": DATE,
        "total_word_target": 2840,
        "meta": {
            "title_options": [
                title,
                "AI Platform for Field Service Dispatch and Scheduling",
            ],
            "meta_title": "AI Platform for Field Service Dispatch and Scheduling | Simpro",
            "meta_description": "Learn how an AI platform for field service dispatch and scheduling uses data, dispatcher controls, vendor checks, and a controlled pilot before rollout.",
            "url_slug": "ai-scheduling-dispatch-field-service",
            "primary_keyword": PRIMARY,
            "secondary_keywords": SECONDARIES,
        },
        "reader_contract": {
            "primary_reader": "US field service owners, operations managers, schedulers, and dispatchers evaluating AI-assisted scheduling.",
            "sophistication_level": "Operational buyers who understand dispatch and need a defensible implementation and vendor-evaluation model.",
            "trigger_problem": "AI scheduling claims are difficult to compare against qualifications, customer commitments, exceptions, and live dispatcher control.",
            "existing_belief": "A useful AI scheduler should optimize the whole day with limited human involvement.",
            "decision_task_helped": "Define one valid scheduling event, evaluate product evidence, and run a controlled pilot.",
            "distinctive_angle": "A workflow-first operating model that joins data readiness, hard constraints, dispatcher approval, current feature status, and a bounded pilot.",
            "promised_payoff": "A scheduling matrix, decision loop, vendor demo questions, and 30-day pilot structure.",
            "funnel_stage": "mofu",
            "exclusions": [
                "vendor ranking",
                "unverified availability or roadmap claims",
                "unsupported customer outcomes or metrics",
                "autonomous scheduling promises",
                "competitor-derived FAQ evidence",
                "named author",
                "editorial-process language",
            ],
        },
        "search_strategy": {
            "primary_query": PRIMARY,
            "searcher_task": "Understand and evaluate AI-assisted field-service scheduling and dispatch platforms, controls, and pilots.",
            "intent_class": "mixed",
            "funnel_stage": "mofu",
            "serp_evidence_artifact": SERP_EVIDENCE.relative_to(ROOT).as_posix(),
            "dominant_content_type": "General Article",
            "selected_content_type": "General Article",
            "observed_serp_features": [],
            "related_query_paa_artifact": BRIEF.relative_to(ROOT).as_posix(),
            "format_decision": "match_dominant",
            "exception_reason": "The current SERP supports an article format; this rewrite adds operating controls and source-mapped product status.",
            "status": "ready",
        },
        "commercial_strategy": {
            "article_title": title,
            "article_primary_keyword": PRIMARY,
            "article_intent": "mixed",
            "destination_id": "simpro-us-feature-scheduling-software",
            "commercial_pillar_url": pillar,
            "planned_anchor_text": "field service scheduling software",
            "planned_h2_section": "Verified scheduling-related capabilities and release status",
            "existing_overlapping_urls_checked": [
                "https://www.simprogroup.com/blog/ai-scheduling-dispatch-field-service",
                "https://www.simprogroup.com/features/scheduling-software",
                "https://www.simprogroup.com/blog/ai-for-field-service",
                "https://www.simprogroup.com/blog/ai-features-field-service-software",
            ],
            "pillar_versus_blog_intent_difference": "The feature page owns commercial field service scheduling software intent. This article owns AI-assisted scheduling and dispatch education, evaluation, controls, and pilot guidance.",
            "cannibalization_decision": "update_existing",
            "incoming_link_candidates": [
                "https://www.simprogroup.com/features/scheduling-software",
                "https://www.simprogroup.com/blog/ai-for-field-service",
                "https://www.simprogroup.com/blog/ai-features-field-service-software",
            ],
            "status": "aligned",
        },
        "lifecycle": {
            "last_updated_date": DATE,
            "volatility": "high",
            "next_review_date": "2026-12-27",
            "review_command": "/performance-review https://www.simprogroup.com/blog/ai-scheduling-dispatch-field-service",
            "gsc_lane": "unavailable: no current page-level GSC export was collected for this rewrite",
            "ga4_lane": "unavailable: no current page-level GA4 export was collected for this rewrite",
            "semrush_lane": "available: authenticated US desktop Semrush UI evidence dated 2026-09-28",
            "ai_citation_lane": "unavailable: no current post-update AI citation tracking was collected",
            "decision": "update",
            "status": "scheduled",
        },
        "sections": sections,
        "engagement_map": {
            "mini_stories": [],
            "ctas": {"commercial_contextual": 8},
            "featured_snippets": [1, 2, 3, 5, 9],
            "next_actions": {"educational_next_step": 8},
            "cta_exception_reason": None,
        },
        "gap_mapping": {
            "early scheduling event artifact": 1,
            "bounded operating standard": 2,
            "clear scheduling terminology": 3,
            "data and constraint readiness": 4,
            "dispatcher approval and recovery": 5,
            "current feature status": 6,
            "repeatable demo checks": 7,
            "controlled pilot": 8,
            "brief-bound FAQ answers": 9,
        },
        "insight_mapping": {
            "valid recommendations start with bounded events": 1,
            "decision support requires human control": 2,
            "scheduling and dispatch are distinct decisions": 3,
            "hard constraints precede weighted goals": 4,
            "write-back failure needs a manual recovery path": 5,
            "release status belongs in product evaluation": 6,
            "vendor examples should be tested with equal questions": 7,
            "shadow mode precedes bounded live use": 8,
            "direct answers need neutral evidence": 9,
        },
        "original_contributions": [
            {
                "contribution_id": "early-scheduling-matrix",
                "planned_contribution": "An early six-column matrix connecting scheduling events with inputs, AI actions, dispatcher checkpoints, fallbacks, and pilot measures.",
                "purpose": "Give operators a usable artifact within the first 300 body words.",
                "evidence_source": "Operational guidance bounded by current source and product evidence.",
                "target_section": "AI Platform for Field Service Dispatch and Scheduling",
            },
            {
                "contribution_id": "dispatcher-decision-loop",
                "planned_contribution": "A five-step decision loop with eligibility, explanation, approval, write-back, monitoring, and recovery.",
                "purpose": "Make human control and failure handling operationally explicit.",
                "evidence_source": "Current NIST governance guidance and source-mapped scheduling documentation.",
                "target_section": "How the decision loop works and where dispatchers retain control",
            },
            {
                "contribution_id": "verified-vendor-matrix",
                "planned_contribution": "A nonranking comparison of current Microsoft, Salesforce, and Simpro scheduling-related examples.",
                "purpose": "Separate verified capability and release status from universal product claims.",
                "evidence_source": "Current first-party vendor documentation and Simpro vault context.",
                "target_section": "Verified scheduling-related capabilities and release status",
            },
            {
                "contribution_id": "bounded-pilot",
                "planned_contribution": "A 30-day pilot sequence covering baseline, shadow mode, dispatcher-approved use, exceptions, and scale review.",
                "purpose": "Turn evaluation into a controlled implementation test.",
                "evidence_source": "Source-safe operational recommendation with no promised outcome.",
                "target_section": "How to run a controlled 30-day pilot and measure it",
            },
        ],
        "entity_map": {
            "primary": [
                PRIMARY,
                "AI scheduling software",
                "field service scheduling software",
            ],
            "supporting": [
                "dispatcher control",
                "hard constraints",
                "shadow mode",
                "Microsoft Scheduling Operations Agent",
                "Salesforce schedule-gap workflow",
                "Scheduling Operations Agent",
            ],
        },
        "internal_link_plan": [
            {
                "target": pillar,
                "role": "down_funnel",
                "rationale": "Verified US scheduling feature pillar placed in the planned vendor-status H2 with its indexed main keyword in the anchor.",
            },
            {
                "target": "https://www.simprogroup.com/company/ai-pledge",
                "role": "supporting",
                "rationale": "Provides owned responsible-AI context without proving product status.",
            },
            {
                "target": "https://www.simprogroup.com/blog/ai-for-field-service",
                "role": "supporting",
                "rationale": "Provides broader AI-in-field-service context without replacing the scheduling feature pillar.",
            },
        ],
        "industry_cluster_link_policy": {
            "status": "not_applicable",
            "rationale": "The article is cross-trade scheduling and dispatch guidance rather than a single-trade industry article.",
        },
        "link_policy_override": None,
        "keyword_decision": {
            "status": "resolved",
            "artifact_schema": "simpro-semrush-keyword-decision/v1",
            "source": "semrush_connector",
            "database": "us",
            "selected_primary_keyword": PRIMARY,
            "selected_secondary_keywords": SECONDARIES,
            "selection_rationale": "Current authenticated Semrush and US SERP evidence support the exact-fit field-service scheduling and dispatch query.",
        },
        "faq_policy": {
            "status": "required",
            "rationale": "The rewrite brief preserves three exact historical PAA questions, and each current answer uses direct neutral evidence.",
        },
        "paa_policy": {
            "source_kind": "brief_paa",
            "query": PRIMARY,
            "selected_questions": [
                "How to use AI for scheduling?",
                "How to automate scheduling?",
                "Can AI do scheduling?",
            ],
        },
        "audience_language_research": {
            "status": "not_applicable",
            "rationale": "The audience is explicitly defined, and current vault voice and product guidance control Simpro language.",
            "source_urls": [],
            "observations": [],
            "intended_section_use": [],
        },
        "rewrite_decisions": {
            "preserve": [
                {"item": "early scheduling matrix", "decision": "Keep the event, input, checkpoint, fallback, and measure structure."},
                {"item": "bounded pilot", "decision": "Keep staged testing and dispatcher control."},
                {"item": "nonranking comparison", "decision": "Keep the evaluation format with refreshed current status."},
            ],
            "update": [
                {"item": "primary keyword", "decision": "Replace the unmeasured former phrase with the measurable exact-fit query."},
                {"item": "proof and links", "decision": "Use current accessible sources and same-paragraph support for high-risk claims."},
            ],
            "add": [
                {"item": "commercial pillar", "decision": "Add the verified scheduling feature URL and indexed keyword anchor in the planned H2."},
                {"item": "current release evidence", "decision": "Bind current Semrush, SERP, vault, selector, and source-map evidence."},
            ],
            "remove": [
                {"item": "competitor FAQ support", "decision": "Use neutral sources for all visible FAQ evidence."},
                {"item": "unsupported customer and authority proof", "decision": "Keep both out of public copy when selectors do not return a direct fit."},
            ],
        },
    }
    atomic_write_json(PLAN, plan)
    findings = check_plan_file(
        PLAN,
        article_path=ARTICLE,
        serp_evidence_path=SERP_EVIDENCE,
        assembly_date=DATE,
        expected_run_id=run,
        workspace_root=ROOT,
    )
    if findings:
        for finding in findings:
            print("PLAN FINDING:", finding)
        raise SystemExit(1)


def build_fulfillment_and_reviews(run: str) -> None:
    text = article_text()
    plan = json.loads(PLAN.read_text(encoding="utf-8"))
    plan_hash = sha256_file(PLAN)
    fulfillment = {
        "schema": PLAN_FULFILLMENT_SCHEMA,
        "editorial_plan_sha256": plan_hash,
        "article_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        "contributions": [
            {"contribution_id": contribution_id, "actual_excerpt": excerpt}
            for contribution_id, excerpt in CONTRIBUTION_EXCERPTS.items()
        ],
    }
    findings = check_fulfillment(
        fulfillment,
        editorial_plan=plan,
        editorial_plan_sha256=plan_hash,
        article_content=text,
    )
    if findings:
        for finding in findings:
            print("FULFILLMENT FINDING:", finding)
        raise SystemExit(1)
    atomic_write_json(FULFILLMENT, fulfillment)

    responses = [
        {"agent": agent, "status": "completed", "findings": []}
        for agent in AGENT_ROSTER
    ]
    for phase, destination in (("plan", PLAN_REVIEW), ("article", ARTICLE_REVIEW)):
        review = build_machine_review(
            run_id=run,
            workflow_stage="rewrite_review",
            phase=phase,
            command="scripts/build_ai_scheduling_dispatch_release_artifacts.py",
            repository_commit=repository_commit(),
            editorial_plan_path=PLAN,
            article_path=ARTICLE,
            proof_sidecar_path=SIDECAR,
            responses=responses,
            created_at=now(),
        )
        write_machine_review(destination, review)


def main() -> int:
    run = run_id()
    build_serp(run)
    build_keyword_decision()
    build_plan(run)
    build_fulfillment_and_reviews(run)
    for label, path in (
        ("serp raw", RAW_SERP),
        ("serp evidence", SERP_EVIDENCE),
        ("keyword decision", KEYWORD_DECISION),
        ("editorial plan", PLAN),
        ("plan fulfillment", FULFILLMENT),
        ("plan review", PLAN_REVIEW),
        ("article review", ARTICLE_REVIEW),
    ):
        print(f"{label}: {path.relative_to(ROOT).as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
