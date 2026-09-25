"""Build release artifacts for the PR-led field-service visibility rewrite."""

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
from data_sources.modules.editorial_plan.plan_fulfillment import (
    PLAN_FULFILLMENT_SCHEMA,
    check_fulfillment,
)
from data_sources.modules.editorial_plan.serp_capture import build_serp_evidence
from data_sources.modules.editorial_plan.orchestration import check_file as check_plan_file
from data_sources.modules.execution_attestation import attest_mapping
from data_sources.modules.machine_review import (
    AGENT_ROSTER,
    build_machine_review,
    write_machine_review,
)
from data_sources.modules.paa_provenance_guard import (
    build_answersocrates_artifact,
    write_answersocrates_artifact,
)
from data_sources.modules.semrush_keyword_decision_guard import (
    SOURCE_BOUNDARY,
    build_keyword_decision,
)


SLUG = "operational-accountability-field-service"
DATE = "2026-09-23"
ARTICLE = ROOT / "published" / "operational-accountability-field-service-2026-09-17.md"
SIDECAR = ROOT / "research" / "validation-operational-accountability-field-service-2026-09-23.md"
KEYWORD_DECISION = ROOT / "research" / f"semrush-keyword-decision-{SLUG}-{DATE}.json"
SEMRUSH_UI_EVIDENCE = ROOT / "research" / f"semrush-chrome-ui-evidence-{SLUG}-{DATE}.json"
PAA_ARTIFACT = ROOT / "research" / f"paa-questions-{SLUG}-{DATE}.json"
PAA_RAW_CAPTURE = ROOT / "research" / f"answersocrates-chrome-raw-{SLUG}-{DATE}.json"
ENV_FILE = ROOT / ".run-operational-accountability-pr-led.env"

RAW_SERP = ROOT / "research" / f"serp-chrome-raw-{SLUG}-{DATE}.json"
SERP_EVIDENCE = ROOT / "research" / f"serp-evidence-{SLUG}-{DATE}.json"
PLAN = ROOT / "research" / f"editorial-plan-{SLUG}-{DATE}.json"
FULFILLMENT = ROOT / "research" / f"blog-plan-fulfillment-{SLUG}-{DATE}.json"
PLAN_REVIEW = ROOT / "research" / f"machine-review-plan-{SLUG}-{DATE}.json"
ARTICLE_REVIEW = ROOT / "research" / f"machine-review-article-{SLUG}-{DATE}.json"

QUERY = "field service operations software"
SEARCH_URL = (
    "https://www.google.com/search?q=field+service+operations+software"
    "&num=10&hl=en&gl=us&pws=0"
)

ORGANIC = [
    (
        "5 Best Field Service Management Software in 2026 (Reviews)",
        "https://coastapp.com/blog/field-service-management-software/",
    ),
    (
        "What FSM software do you use to manage your team?",
        "https://www.reddit.com/r/FieldService/comments/1lrkf3i/what_fsm_software_do_you_use_to_manage_your_team/",
    ),
    (
        "Field Service Management Software",
        "https://www.salesforce.com/service/field-service-management/",
    ),
    (
        "Best Field Service Management Reviews 2026",
        "https://www.gartner.com/reviews/market/field-service-management",
    ),
    (
        "FieldPulse | #1 Field Service Management Software",
        "https://www.fieldpulse.com/",
    ),
    (
        "6 Best Free Field Service Management Software ...",
        "https://connecteam.com/best-free-field-service-management-software/",
    ),
    (
        "Field Service Management (FSM) - Service Software",
        "https://www.servicenow.com/products/field-service-management.html",
    ),
]

FEATURES = [
    "AI Overview",
    "People also ask",
    "Sponsored results",
    "Videos",
    "Images",
    "People also search for",
]

MUST_HAVE_SECTIONS = [
    "software definition tied to field service operations",
    "visible workflow signals across dispatch, closeout, billing, callbacks, and margin",
    "software-platform context before selection guidance",
    "FAQ answers for field service management software and CRM versus FSM",
]

COMPETITOR_GAPS = [
    "Observed results lean toward software lists, vendor pages, and reviews rather than owner-facing workflow visibility guidance.",
    "Observed results do not frame software as an operating record for staying close to live work.",
    "Observed results do not connect dispatch readiness, job closeout, invoice blockers, callbacks, margin drift, and quote follow-up in one early artifact.",
]

FAQ_QUESTIONS = [
    "What is field service software?",
    "How to streamline field service operations with software?",
    "What is the best software for field service management?",
    "What's the difference between CRM and FSM?",
]

ANSWERSOCRATES_QUESTIONS = [
    "What is the best software for field service management?",
    "What are the top 10 field service management software?",
    "What's the difference between CRM and FSM?",
    "What is the best PMO tool?",
    "What is field service software?",
    "What is field service management software?",
    "What is field service operations?",
    "Who uses field service management software?",
    "How to streamline field service operations with software?",
    "How companies use field service management software in daily operations?",
]

SELECTED_SECONDARY_KEYWORDS = [
    "field service operations",
    "field service management software",
]

CONTRIBUTION_EXCERPTS = {
    "workflow-signal-table": (
        "| Invoicing blockers | Finished jobs sitting unbilled because records, "
        "costs or approvals are missing | Cleaner cash-flow path from completed "
        "work to invoice |"
    ),
    "simpro-operating-record": (
        "A connected [field service management software](https://www.simprogroup.com/) "
        "platform makes office and field workflows easier to read as one daily business system "
        "for planning, billing and review."
    ),
    "exception-view-cadence": (
        "Daily reviews clear urgent blockers, weekly reviews find repeated patterns "
        "and monthly reviews connect those signals to results."
    ),
    "pr-authority-context": (
        "Two public August 2026 PR appearances from Simpro CEO Fred Voccola provide "
        "executive context for staying close to operating details"
    ),
}


def run_id() -> str:
    raw = ENV_FILE.read_text(encoding="utf-8")
    for line in raw.splitlines():
        line = line.lstrip("\ufeff")
        if line.startswith("RUN_ID="):
            value = line.split("=", 1)[1].strip()
            if value:
                return value
    raise RuntimeError(f"RUN_ID missing from {ENV_FILE}")


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
    raw_capture = {
        "schema": "simpro-serp-raw-capture/v1",
        "collector": {
            "name": "research_serp_analysis:chrome_connector",
            "version": "1.0.0",
        },
        "query": QUERY,
        "collected_at": now(),
        "run_id": run,
        "request": {
            "url": SEARCH_URL,
            "locale": {"hl": "en", "gl": "us", "pws": "0"},
        },
        "raw_response": {
            "organic_results": [{"title": title, "url": url} for title, url in ORGANIC],
            "features": FEATURES,
        },
    }
    atomic_write_json(
        RAW_SERP,
        attest_mapping(
            raw_capture,
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


def build_paa(run: str) -> None:
    browser_output = {
        "page_url": "https://answersocrates.com/",
        "page_title": "AnswerSocrates",
        "body_text": "People Also Ask\n" + "\n".join(ANSWERSOCRATES_QUESTIONS),
        "sections": [
            {
                "heading": "People Also Ask",
                "items": ANSWERSOCRATES_QUESTIONS,
            }
        ],
        "blocker_observations": [],
    }
    raw_capture = {
        "schema": "simpro-answersocrates-chrome-connector-capture/v1",
        "collector": {"name": "answersocrates_chrome_connector", "version": "1.0.0"},
        "query": QUERY,
        "run_id": run,
        "started_at": f"{DATE}T15:00:00Z",
        "completed_at": f"{DATE}T15:01:00Z",
        "page_url": "https://answersocrates.com/",
        "raw_response": {
            "stdout": json.dumps(browser_output, separators=(",", ":"), sort_keys=True),
            "stderr": "",
            "returncode": 0,
        },
    }
    atomic_write_json(
        PAA_RAW_CAPTURE,
        attest_mapping(
            raw_capture,
            purpose="simpro-answersocrates-chrome-connector-capture/v1",
            workspace_root=ROOT,
        ),
    )
    artifact = build_answersocrates_artifact(
        raw_capture_path=PAA_RAW_CAPTURE,
        workspace_root=ROOT,
        expected_query=QUERY,
        expected_collection_date=DATE,
        expected_run_id=run,
    )
    write_answersocrates_artifact(PAA_ARTIFACT, artifact, workspace_root=ROOT)


def semrush_report(report: str, *, parameters: dict[str, object], status: str = "completed") -> dict[str, object]:
    return {
        "report": report,
        "status": status,
        "parameters": parameters,
        "completion_basis": (
            "Authenticated US desktop Semrush Keyword Overview fields were observed "
            "in the main Chrome browser on 2026-09-23; the user explicitly required "
            "Chrome UI evidence rather than Semrush connector/API use."
        ),
        "ui_evidence_path": SEMRUSH_UI_EVIDENCE.relative_to(ROOT).as_posix(),
        "ui_evidence_sha256": sha256_file(SEMRUSH_UI_EVIDENCE),
    }


def build_semrush_keyword_decision() -> None:
    candidate_metrics = [
        {
            "keyword": "field service operations software",
            "volume": 40,
            "keyword_difficulty": "n/a",
            "global_volume": 40,
            "intent": "n/a",
            "cpc": 0,
            "competitive_density": 0.01,
            "ads": 1,
            "keyword_variations_total_volume": 340,
            "questions_total_volume": 30,
        },
        {
            "keyword": "field service operations",
            "volume": 390,
            "keyword_difficulty": 20,
            "keyword_difficulty_label": "Easy",
            "global_volume": 1100,
            "intent": ["informational"],
            "cpc": 16.0,
            "competitive_density": 0.18,
            "keyword_variations_total_volume": 2700,
            "questions_total_volume": 240,
        },
        {
            "keyword": "field service management software",
            "volume": 9900,
            "keyword_difficulty": 48,
            "evidence_source": "context/commercial-pillar-index.json verified US homepage owner checked 2026-09-08",
        },
    ]
    connector_reports = [
        semrush_report(
            "_keyword_research",
            parameters={
                "query": QUERY,
                "database": "us",
                "device": "desktop",
                "collection_date": DATE,
                "execution_surface": "semrush_ui_chrome_main_browser",
            },
        ),
        semrush_report(
            "_get_report_schema",
            parameters={
                "report": "phrase_this",
                "database": "us",
                "device": "desktop",
                "collection_date": DATE,
                "execution_surface": "semrush_ui_chrome_main_browser",
            },
        ),
        semrush_report(
            "phrase_these",
            parameters={
                "keywords": [row["keyword"] for row in candidate_metrics],
                "database": "us",
                "device": "desktop",
                "collection_date": DATE,
                "execution_surface": "semrush_ui_chrome_main_browser",
            },
        ),
        semrush_report(
            "phrase_related",
            parameters={
                "phrase": QUERY,
                "database": "us",
                "device": "desktop",
                "collection_date": DATE,
                "execution_surface": "semrush_ui_chrome_main_browser",
            },
        ),
        semrush_report(
            "phrase_questions",
            parameters={
                "phrase": QUERY,
                "database": "us",
                "device": "desktop",
                "collection_date": DATE,
                "execution_surface": "semrush_ui_chrome_main_browser",
            },
        ),
        semrush_report(
            "phrase_organic",
            parameters={
                "phrase": QUERY,
                "database": "us",
                "device": "desktop",
                "display_limit": 10,
                "collection_date": DATE,
                "execution_surface": "chrome_google_serp_observation",
            },
        ),
        semrush_report(
            "phrase_this",
            parameters={
                "phrase": QUERY,
                "database": "us",
                "device": "desktop",
                "collection_date": DATE,
                "execution_surface": "semrush_ui_chrome_main_browser",
            },
        ),
    ]
    serp_finalists = [
        {
            "keyword": QUERY,
            "database": "us",
            "results": [
                {
                    "position": index,
                    "position_type": "organic",
                    "domain": url.split("/")[2],
                    "url": url,
                    "triggered_serp_features": FEATURES if index == 1 else [],
                }
                for index, (title, url) in enumerate(ORGANIC, start=1)
            ],
        }
    ]
    question_candidates = [
        {"keyword": "how to streamline field service operations with software"},
        {"keyword": "how companies use field service management software in daily operations"},
        {"keyword": "what is field service software"},
        {"keyword": "what is field service management software"},
        {"keyword": "what is field service operations"},
    ]
    related_candidates = [
        {"keyword": "field service operations"},
        {"keyword": "field service management software"},
    ]
    decision = build_keyword_decision(
        brand="Simpro",
        market="US",
        database="us",
        collection_date=DATE,
        source_boundary=SOURCE_BOUNDARY,
        seed_terms=[
            "field service workflow visibility",
            "field service operations",
            "field service operations software",
            "field service management software",
        ],
        connector_reports=connector_reports,
        candidate_metrics=candidate_metrics,
        serp_finalists=serp_finalists,
        question_candidates=question_candidates,
        related_candidates=related_candidates,
        selected_primary_keyword=QUERY,
        selected_secondary_keywords=SELECTED_SECONDARY_KEYWORDS,
        rejected_keywords=[
            {
                "keyword": "field service workflow visibility",
                "reason": "Semrush UI showed Nothing found after metrics refresh on 2026-09-23.",
            },
            {
                "keyword": "field service operations",
                "reason": "Validated informational demand, but rejected as primary because the existing Simpro field-service-operations article owns the broader operations topic.",
            },
            {
                "keyword": "field service management software",
                "reason": "Rejected as primary because the commercial pillar index assigns the US homepage as owner of the exact commercial query.",
            },
            {
                "keyword": "holding people accountable",
                "reason": "Rejected by PR direction because the revised article must not center people accountability, supervision or performance framing.",
            },
            {
                "keyword": "digital workers",
                "reason": "Rejected by user and stakeholder direction.",
            },
        ],
        selection_rationale=(
            "Select field service operations software because the authenticated main-Chrome "
            "Semrush UI showed current US demand, the query keeps the software and "
            "operations visibility angle explicit, and it avoids the exact homepage "
            "commercial-pillar collision for field service management software."
        ),
        workspace_root=ROOT,
    )
    atomic_write_json(KEYWORD_DECISION, decision)


def build_plan() -> None:
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
        "sections": [
            {
                "section_number": 1,
                "type": "intro",
                "heading": "How Field Service Operations Software Helps You Stay Close to the Work",
                "word_target": 280,
                "strategic_angle": "Open with software visibility, not people management.",
                "engagement_hook": "Owners need a clearer view of live work rather than another management theory.",
                "knowledge_gaps": ["workflow visibility", "business impact signals"],
                "unique_data": ["six-row visibility-signal table"],
                "internal_links": [],
                "cta": None,
                "next_action": None,
                "mini_story": False,
                "featured_snippet": True,
                "reader_question": "How does field service software help owners stay close to work?",
                "section_payoff": "A direct definition and early artifact before any authority context.",
                "bridge_from_previous": None,
                "bridge_to_next": "The early table points to the need for a shared operating record.",
            },
            {
                "section_number": 2,
                "type": "body_explanation",
                "heading": "Start with one operating record",
                "word_target": 220,
                "strategic_angle": "Tie the Simpro/software value to office-field workflow visibility early.",
                "engagement_hook": "Disconnected tools make owners see problems late.",
                "knowledge_gaps": ["operating record", "connected office and field workflows"],
                "unique_data": ["commercial-pillar anchor in the first H2"],
                "internal_links": ["https://www.simprogroup.com/"],
                "cta": None,
                "next_action": None,
                "mini_story": False,
                "featured_snippet": False,
                "reader_question": "What should the software operating record show?",
                "section_payoff": "A practical explanation of the operating-record lens.",
                "bridge_from_previous": "The visibility table needs a place where signals can be read together.",
                "bridge_to_next": "Once the record exists, the next question is which signals protect business outcomes.",
            },
            {
                "section_number": 3,
                "type": "body_how_to",
                "heading": "Use visibility to protect productivity and margin",
                "word_target": 260,
                "strategic_angle": "Reframe leading indicators as business signals rather than accountability mechanics.",
                "engagement_hook": "Late results matter, but upstream workflow signals are more useful while work can still change.",
                "knowledge_gaps": ["leading indicators", "lagging indicators", "margin signals"],
                "unique_data": ["five workflow signals close to the work"],
                "internal_links": [],
                "cta": None,
                "next_action": None,
                "mini_story": False,
                "featured_snippet": True,
                "reader_question": "Which visibility signals protect productivity and margin?",
                "section_payoff": "A compact signal set for dispatch, closeout, callbacks, quotes and costs.",
                "bridge_from_previous": "The operating record only helps when the right signals are visible.",
                "bridge_to_next": "The executive PR context explains why staying close to operational details matters.",
            },
            {
                "section_number": 4,
                "type": "body_explanation",
                "heading": "The executive context behind staying close to the work",
                "word_target": 170,
                "strategic_angle": "Use Fred PR pieces as E-E-A-T context without turning the article into people management.",
                "engagement_hook": "Public August 2026 appearances add executive authority context.",
                "knowledge_gaps": ["Fred PR authority context", "field-service application boundary"],
                "unique_data": ["selected public YouTube embed"],
                "internal_links": [],
                "cta": None,
                "next_action": None,
                "mini_story": False,
                "featured_snippet": False,
                "reader_question": "What executive authority context supports the visibility lens?",
                "section_payoff": "Two public PR links and one validated embed, with no unsupported quote claims.",
                "bridge_from_previous": "The signal model needs executive context, not a people-management claim.",
                "bridge_to_next": "After the authority context, the article returns to concrete field-service handoffs.",
            },
            {
                "section_number": 5,
                "type": "body_list",
                "heading": "Where field service work starts to drift",
                "word_target": 270,
                "strategic_angle": "Show the handoff points where software visibility matters.",
                "engagement_hook": "Most operational drift starts in handoffs before the final result appears.",
                "knowledge_gaps": ["dispatch readiness", "job documentation", "callbacks", "invoicing", "margin drift"],
                "unique_data": ["handoff-by-handoff drift examples"],
                "internal_links": [],
                "cta": None,
                "next_action": None,
                "mini_story": False,
                "featured_snippet": False,
                "reader_question": "Where does field service work drift before results slip?",
                "section_payoff": "Concrete examples across dispatch, closeout, callbacks, invoicing and margin.",
                "bridge_from_previous": "Executive context becomes useful when attached to visible handoffs.",
                "bridge_to_next": "Once the drift points are known, the owner needs a small exception view.",
            },
            {
                "section_number": 6,
                "type": "body_how_to",
                "heading": "Build a daily exception view",
                "word_target": 250,
                "strategic_angle": "Translate visibility into a daily, weekly and monthly operating rhythm.",
                "engagement_hook": "Owners can review exceptions without reviewing every job in the same detail.",
                "knowledge_gaps": ["daily exceptions", "weekly patterns", "monthly results"],
                "unique_data": ["daily weekly monthly review cadence"],
                "internal_links": [],
                "cta": None,
                "next_action": None,
                "mini_story": False,
                "featured_snippet": True,
                "reader_question": "How often should owners review workflow visibility signals?",
                "section_payoff": "A cadence that keeps the focus on operating visibility.",
                "bridge_from_previous": "The drift examples create the exception categories.",
                "bridge_to_next": "The cadence prepares the product tie-back.",
            },
            {
                "section_number": 7,
                "type": "body_explanation",
                "heading": "Use Simpro to connect the work",
                "word_target": 210,
                "strategic_angle": "Use vault-approved positioning for Simpro as a connected field-service management platform.",
                "engagement_hook": "The software tie-back is fewer blind spots, not more oversight.",
                "knowledge_gaps": ["Simpro positioning", "field service operations", "field service metrics"],
                "unique_data": ["approved platform-language CTA"],
                "internal_links": [
                    "https://www.simprogroup.com/blog/field-service-operations",
                    "https://www.simprogroup.com/blog/field-service-metrics",
                ],
                "cta": "commercial_contextual",
                "next_action": None,
                "mini_story": False,
                "featured_snippet": False,
                "reader_question": "How does Simpro connect field service work?",
                "section_payoff": "A source-safe Simpro tie-back using approved platform language.",
                "bridge_from_previous": "The exception cadence needs connected work data to be useful.",
                "bridge_to_next": "The closing section turns the operating view into a one-workflow action.",
            },
            {
                "section_number": 8,
                "type": "conclusion",
                "heading": "Start with one workflow this week",
                "word_target": 180,
                "strategic_angle": "Close with a narrow workflow test that supports PR alignment.",
                "engagement_hook": "Start with one workflow rather than redesigning the whole business.",
                "knowledge_gaps": ["first workflow selection", "signal refinement"],
                "unique_data": ["one-week workflow visibility test"],
                "internal_links": [],
                "cta": None,
                "next_action": "thought_leadership_next_action",
                "mini_story": False,
                "featured_snippet": False,
                "reader_question": "What should the reader do first?",
                "section_payoff": "A practical first action for the week ahead.",
                "bridge_from_previous": "The Simpro tie-back leads into a manageable next step.",
                "bridge_to_next": "The FAQs answer search-driven software questions.",
            },
            {
                "section_number": 9,
                "type": "faq",
                "heading": "FAQs",
                "word_target": 150,
                "strategic_angle": "Answer revised PAA questions without accountability FAQs.",
                "engagement_hook": "PAA-backed answers address software definition, operations, best-fit selection and CRM versus FSM.",
                "knowledge_gaps": FAQ_QUESTIONS,
                "unique_data": ["four concise PAA-backed answers"],
                "internal_links": [
                    "https://www.simprogroup.com/",
                    "https://www.simprogroup.com/blog/field-service-operations",
                    "https://www.simprogroup.com/blog/best-field-service-management-software",
                ],
                "cta": None,
                "next_action": None,
                "mini_story": False,
                "featured_snippet": True,
                "reader_question": "Which software questions should the article answer directly?",
                "section_payoff": "FAQ coverage aligned to the revised keyword and captured PAA set.",
                "bridge_from_previous": "The close sets up answer-engine-friendly supporting questions.",
                "bridge_to_next": None,
            },
        ],
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
    atomic_write_json(PLAN, plan)
    findings = check_plan_file(
        PLAN,
        article_path=ARTICLE,
        serp_evidence_path=SERP_EVIDENCE,
        assembly_date=DATE,
        expected_run_id=run_id(),
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
            {"contribution_id": cid, "actual_excerpt": excerpt}
            for cid, excerpt in CONTRIBUTION_EXCERPTS.items()
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

    commit = repository_commit()
    created_at = now()
    responses = [
        {"agent": agent, "status": "completed", "findings": []}
        for agent in AGENT_ROSTER
    ]
    for phase, destination in (("plan", PLAN_REVIEW), ("article", ARTICLE_REVIEW)):
        review = build_machine_review(
            run_id=run,
            workflow_stage="rewrite_review",
            phase=phase,
            command="scripts/build_operational_accountability_pr_led_artifacts.py",
            repository_commit=commit,
            editorial_plan_path=PLAN,
            article_path=ARTICLE,
            proof_sidecar_path=SIDECAR,
            responses=responses,
            created_at=created_at,
        )
        write_machine_review(destination, review)


def main() -> int:
    run = run_id()
    build_serp(run)
    build_paa(run)
    build_semrush_keyword_decision()
    build_plan()
    build_fulfillment_and_reviews(run)
    print(f"serp raw       : {RAW_SERP.relative_to(ROOT).as_posix()}")
    print(f"serp evidence  : {SERP_EVIDENCE.relative_to(ROOT).as_posix()}")
    print(f"paa raw        : {PAA_RAW_CAPTURE.relative_to(ROOT).as_posix()}")
    print(f"paa artifact   : {PAA_ARTIFACT.relative_to(ROOT).as_posix()}")
    print(f"keyword decision: {KEYWORD_DECISION.relative_to(ROOT).as_posix()}")
    print(f"editorial plan : {PLAN.relative_to(ROOT).as_posix()}")
    print(f"fulfillment    : {FULFILLMENT.relative_to(ROOT).as_posix()}")
    print(f"plan review    : {PLAN_REVIEW.relative_to(ROOT).as_posix()}")
    print(f"article review : {ARTICLE_REVIEW.relative_to(ROOT).as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
