"""Static inputs for the PR-led field-service visibility rewrite artifacts."""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

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

PLAN_SECTIONS = [
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
]
