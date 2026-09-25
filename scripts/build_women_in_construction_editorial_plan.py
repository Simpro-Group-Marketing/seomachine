"""Write the frozen simpro-blog-editorial-plan/v2 for the women-in-construction rewrite.

Governance artifact only. Decisions come from the Asana brief, the live-page
baseline, the analysis, the Semrush keyword decision, the Chrome SERP evidence,
and the brief's pre-picked PAA section. Rerunning changes the plan hash, so any
change routes back through /analyze-existing and every downstream receipt.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from data_sources.modules.blog_assembly_contract import atomic_write_json  # noqa: E402

SLUG = "women-in-construction"
DATE = "2026-09-26"
OUT = ROOT / "research" / f"editorial-plan-{SLUG}-{DATE}.json"
TITLE = "Bridging the Trades Labor Gap: A Contractor's Guide to Attracting and Retaining Women in Construction"
PRIMARY = "women in construction"
SECONDARY = ["woman in construction", "women construction workers"]
PAA = [
    "What percentage of the construction industry is women?",
    "Is construction a good job for women?",
    "Why are women in construction important?",
    "What are the challenges faced by women in construction?",
    "How to recognize women in construction?",
]
HOME = "https://www.simprogroup.com/"
SCHEDULING = "https://www.simprogroup.com/features/scheduling-software"
MOBILE = "https://www.simprogroup.com/features/field-service-mobile-app"
SHORTAGE = "https://www.simprogroup.com/blog/skilled-trades-shortage"
WOMEN_GUIDE = "https://www.simprogroup.com/blog/women-in-skilled-trades-the-ultimate-guide"
FOSTER = "https://www.simprogroup.com/case-studies/foster-plumbing"


def section(number, kind, heading, words, angle, hook, gaps, data, links, reader_q, payoff,
            bridge_from, bridge_to, *, cta=None, next_action=None, snippet=False):
    return {
        "section_number": number,
        "type": kind,
        "heading": heading,
        "word_target": words,
        "strategic_angle": angle,
        "engagement_hook": hook,
        "knowledge_gaps": gaps,
        "unique_data": data,
        "internal_links": links,
        "cta": cta,
        "next_action": next_action,
        "mini_story": False,
        "featured_snippet": snippet,
        "reader_question": reader_q,
        "section_payoff": payoff,
        "bridge_from_previous": bridge_from,
        "bridge_to_next": bridge_to,
    }


SECTIONS = [
    section(1, "intro", "Opening paragraph before first H2", 180,
            "Open evergreen: women remain a small share of the field workforce, and that gap is a hiring opportunity for trade contractors short of skilled labor. Frame recruiting women as an operating decision, not a diversity campaign.",
            "Two BLS figures in the first paragraph show the size of the untapped pool before any scrolling.",
            ["Answer who women in construction are by share of jobs in the first 60 words.",
             "Drop the March Women in Construction Week framing from the opening."],
            ["BLS CPS 2025 industry share and construction-and-extraction share with same-paragraph links.",
             "Key takeaways blockquote summarizing the five operating levers."],
            [], "How big is the gap for women in construction, and why should a contractor care?",
            "A direct, sourced answer that frames women as a practical labor-capacity lever.",
            None, "Break the headline figures out by role.", snippet=True),
    section(2, "body_comparison", "Women in construction by the numbers", 290,
            "Give the reader a filled, sourced table of women's share by construction role, then explain the office-versus-field gap and the 20-year trend.",
            "An 11-row table from one official 2025 dataset inside the first 300 words.",
            ["Explain the Table 18 industry versus Table 11 occupation scope difference.",
             "Warn against year-over-year comparison of the 11-month 2025 BLS averages."],
            ["BLS CPS 2025 Tables 11 and 18 women's shares by role.",
             "NAHB 20-year-high tabulation and the 78 percent office-support share."],
            [], "Where do women work in construction today, by role?",
            "A role-level view that shows field trades are the gap and office roles are a bench.",
            "Expand the headline figures into a role table.", "Explain why the gap is an operating risk.", snippet=True),
    section(3, "body_explanation", "Why the trades labor gap is an operations problem", 175,
            "Tie the labor gap to backlog, overtime, service delays and passed-over bids, then position recruiting women as a capacity plan with the same hiring bar.",
            "Two current industry figures on workers needed and hard-to-fill roles.",
            ["Link to the existing skilled-trades shortage article instead of re-covering shortage causes.",
             "Keep the frame operational, not a diversity campaign."],
            ["ABC 2026 net new worker estimate.", "AGC and NCCER 2026 hard-to-fill share."],
            [SHORTAGE], "Why does a small share of women on crews matter to my schedule and margins?",
            "A clear operational case for widening the hiring pool.",
            "Move from who works in construction to what open seats cost.", "Start with the jobsite changes that widen the pool."),
    section(4, "body_how_to", "Modernize jobsite technology to lower physical barriers", 190,
            "Show how lift assist, prefabrication, lighter tools, fitted PPE and mobile job information reduce the physical and information barriers that keep candidates out.",
            "Concrete equipment and workflow changes a contractor applies this quarter.",
            ["Cite the OSHA construction PPE fit requirement and effective date in the same paragraph.",
             "Frame field technology as support for technicians, not surveillance."],
            ["OSHA 29 CFR 1926.95 fit requirement and the January 13, 2025 final rule."],
            [MOBILE], "Which jobsite changes make the trades workable for more people?",
            "A practical list of equipment, PPE and information changes.",
            "Turn the capacity case into jobsite action.", "Show new hires where the job leads."),
    section(5, "body_how_to", "Build transparent career pathways from apprentice to leader", 240,
            "Use registered apprenticeship data to show the pipeline, then give a filled five-stage career ladder checklist a contractor publishes.",
            "A five-stage ladder table with duties, published details and evidence to move up.",
            ["Keep the all-industry DOL share and the construction-specific IWPR share clearly scoped.",
             "Avoid state-specific licensing claims."],
            ["DOL FY2024 women apprentice count and share.", "IWPR 2024 construction apprentice share in 37 states."],
            [], "How do I show women a real path from apprentice to leadership?",
            "A publishable career ladder that answers where the job leads.",
            "Move from jobsite changes to long-term progression.", "Show how connected systems open leadership roles."),
    section(6, "body_how_to", "Use connected systems to open flexible leadership roles", 200,
            "Show that scheduling, estimating and service management roles run on information, cite one approved Foster Plumbing growth metric with its owner, and connect scheduling software to flexible, fixed-hours leadership roles.",
            "One approved customer growth metric plus three concrete moves.",
            ["Use only the vault-approved Foster Plumbing revenue metric (claim-metric-MET-0178) with a same-paragraph case-study link.",
             "Use a function-bearing anchor for the scheduling feature link."],
            ["Foster Plumbing revenue growth from $1 million to $10 million, attributed to the case study with Amy Carnrick named as former CEO."],
            [FOSTER, SCHEDULING], "Which leadership roles open up when office and field share the same data?",
            "A path from office support into operations leadership with flexible hours.",
            "Extend the ladder into office and operations leadership.", "Cover the recruiting and retention basics.", snippet=False),
    section(7, "body_how_to", "Recruit and retain women on your crews", 285,
            "Give an eight-row recruiting and retention checklist, the OSHA sanitation check, stay interviews and four quarterly measures.",
            "A filled checklist table plus a short measurement block.",
            ["Cite the OSHA construction sanitation standard in the same paragraph.",
             "Keep advice framed as employer guidance without unsupported outcome claims."],
            ["OSHA 29 CFR 1926.51 toilet provision by crew size.", "Four quarterly retention measures."],
            [], "What do I change in hiring and on site so women join and stay?",
            "A checklist and measures a hiring manager uses immediately.",
            "Move from roles to the people practices behind them.", "Turn every lever into a 90-day plan."),
    section(8, "conclusion", "A 90-day roadmap for trade business owners", 165,
            "Close with a three-phase 90-day roadmap table, introduce field service management software as the shared system that keeps office and field on the same facts, and point candidates to the women-in-trades career guide.",
            "A filled 30-60-90 table with an owner check per phase.",
            ["Use the exact commercial pillar anchor once.", "Keep the product mention to shared schedules, jobs and invoices."],
            ["Three-phase roadmap with actions and owner checks."],
            [HOME, WOMEN_GUIDE], "What do I do first, and in what order?",
            "A time-bound plan and a relevant next step.",
            "Collect every lever into one plan.", "Answer the common follow-up questions.",
            cta="commercial_contextual"),
    section(9, "faq", "FAQs", 350,
            "Answer the five brief pre-picked Google PAA questions with 40-to-60-word first paragraphs led by a number, explained yes, named reason, concrete list or action.",
            "Every answer opens with the answer and an authoritative link.",
            ["Fact-driven answers need a non-owned authoritative link in the first visible paragraph.",
             "Reuse the same BLS, DOL, ABC, OSHA and NAWIC facts as the body."],
            ["BLS shares, DOL apprentice count, ABC worker estimate, OSHA PPE fit date, NAWIC WIC Week timing."],
            [], "What quick answers do searchers want about women in construction?",
            "Five short, sourced answers matching Google PAA.",
            "Resolve the questions left after the roadmap.", None, snippet=True),
]

PLAN = {
    "schema": "simpro-blog-editorial-plan/v2",
    "brand": "Simpro",
    "topic": PRIMARY,
    "date": DATE,
    "meta": {
        "title_options": [
            TITLE,
            "Women in Construction: A Contractor's Guide to Hiring and Keeping Skilled Women",
        ],
        "meta_title": "Women in Construction: Hiring and Retention Guide | Simpro",
        "meta_description": "Women in construction hold 11.3 percent of industry jobs. Get BLS role data, a career ladder, a retention checklist and a 90-day plan for trade contractors.",
        "url_slug": SLUG,
        "primary_keyword": PRIMARY,
        "secondary_keywords": SECONDARY,
    },
    "total_word_target": sum(s["word_target"] for s in SECTIONS),
    "sections": SECTIONS,
    "engagement_map": {
        "mini_stories": [],
        "ctas": {"commercial_contextual": 8},
        "featured_snippets": [s["section_number"] for s in SECTIONS if s["featured_snippet"]],
        "next_actions": {},
        "cta_exception_reason": None,
    },
    "gap_mapping": {
        "employer-side guide for contractors instead of association pages and statistics roundups": 3,
        "role-level women's share table from one official 2025 dataset": 2,
        "publishable career ladder from apprentice to operations leader": 5,
        "recruiting and retention checklist with measures": 7,
        "time-bound owner roadmap": 8,
        "direct answers to Google PAA questions": 9,
    },
    "insight_mapping": {
        "the NAHB office-support share makes office staff a leadership bench": 2,
        "field trades are the gap while inspection and management roles sit higher": 2,
        "better equipment and fitted PPE widen who stays in a trade for a full career": 4,
        "shared scheduling and job data make fixed-hours leadership roles workable": 6,
    },
    "reader_contract": {
        "primary_reader": "A US trade contractor owner or operations leader short of skilled field staff.",
        "sophistication_level": "Experienced operator who knows hiring pain but has not built a structured plan to recruit and keep women.",
        "trigger_problem": "Open field seats cause backlog, overtime and lost bids, and current hiring reaches only part of the available workforce.",
        "existing_belief": "Recruiting women is a diversity or awareness-week initiative rather than a capacity plan.",
        "decision_task_helped": "Decide which jobsite, career-path, systems and retention changes to make first, and in what order.",
        "distinctive_angle": "An employer playbook built on 2025 BLS role data, official OSHA and DOL sources, and filled checklists and a 90-day roadmap.",
        "promised_payoff": "A practical, sourced plan to attract, develop and retain women across field and office roles.",
        "funnel_stage": "tofu",
        "exclusions": [
            "event-dated Women in Construction Week framing as the core thesis",
            "job-seeker trade-choice guidance owned by the women-in-skilled-trades guide",
            "unapproved customer quotes, including the removed Carnrick, Lawrie and Paku lines",
            "Hindsight or deal data presented as proof",
            "named author or Person schema without approved authorship evidence",
            "first-person authority language, editorial-process commentary, or em dashes in public copy",
        ],
    },
    "original_contributions": [
        {
            "contribution_id": "women-share-by-role-table",
            "planned_contribution": "An 11-row table of women's share of US workers by construction role from BLS CPS 2025.",
            "purpose": "Answer the share question by role in one extractable table.",
            "evidence_source": "BLS CPS 2025 annual averages Tables 11 and 18.",
            "target_section": "Women in construction by the numbers",
        },
        {
            "contribution_id": "career-ladder-checklist",
            "planned_contribution": "A five-stage career ladder checklist with duties, published details and evidence to move up.",
            "purpose": "Give contractors a publishable career path for new hires.",
            "evidence_source": "Editorially framed employer guidance anchored to DOL and IWPR apprenticeship data.",
            "target_section": "Build transparent career pathways from apprentice to leader",
        },
        {
            "contribution_id": "retention-checklist",
            "planned_contribution": "An eight-row recruiting and retention checklist with the action and reason for each area.",
            "purpose": "Turn retention into concrete hiring-manager actions.",
            "evidence_source": "Editorial employer guidance plus OSHA PPE and sanitation standards.",
            "target_section": "Recruit and retain women on your crews",
        },
        {
            "contribution_id": "ninety-day-roadmap",
            "planned_contribution": "A three-phase 90-day roadmap with actions and an owner check per phase.",
            "purpose": "Sequence the levers into a plan an owner runs.",
            "evidence_source": "Editorially framed guidance tied to the article's checklists.",
            "target_section": "A 90-day roadmap for trade business owners",
        },
    ],
    "entity_map": {
        "primary": ["women in construction", "Bureau of Labor Statistics", "Current Population Survey",
                    "construction and extraction occupations", "registered apprenticeship", "OSHA",
                    "trade contractors", "skilled labor shortage"],
        "supporting": ["National Association of Women in Construction", "WIC Week",
                       "Associated Builders and Contractors", "Associated General Contractors", "NCCER",
                       "Department of Labor", "IWPR", "NAHB", "personal protective equipment",
                       "career ladder", "field service management software", "scheduling software",
                       "field service mobile app", "Foster Plumbing"],
    },
    "internal_link_plan": [
        {"target": SHORTAGE, "role": "supporting", "rationale": "Existing labor-shortage article owns shortage causes, so the operations section links to it instead of targeting construction labor shortage."},
        {"target": MOBILE, "role": "down_funnel", "rationale": "Mobile job notes, forms and photos support the information-barrier point in the jobsite section with a function-bearing anchor."},
        {"target": FOSTER, "role": "supporting", "rationale": "Same-paragraph public source for the approved Foster Plumbing revenue metric."},
        {"target": SCHEDULING, "role": "down_funnel", "rationale": "Scheduling that balances crew workloads supports flexible leadership roles with a function-bearing anchor."},
        {"target": HOME, "role": "supporting", "rationale": "Commercial pillar link with the exact anchor field service management software in the roadmap conclusion."},
        {"target": WOMEN_GUIDE, "role": "supporting", "rationale": "Sibling job-seeker guide for candidates and school partners, keeping the cluster connected without competing for its keyword."},
    ],
    "rewrite_decisions": {
        "preserve": [
            {"item": "women in construction topic and hero image", "decision": "Keep the women in construction subject and the original live feature image as the hero placeholder, renamed with a keyword filename and new alt text."},
            {"item": "workforce statistics theme", "decision": "Keep the women's representation and field-trade share theme, refreshed to BLS CPS 2025 figures."},
            {"item": "useful internal links", "decision": "Keep the skilled-trades shortage and scheduling software links."},
            {"item": "technology widens access argument", "decision": "Keep the argument that modern equipment and digital tools broaden who works in the trades, reframed as jobsite actions."},
        ],
        "update": [
            {"item": "title, H1, slug and metadata", "decision": "Replace the event title with the evergreen H1 from the brief, move to the women-in-construction slug with a recommended 301, and update the meta title and description."},
            {"item": "statistics", "decision": "Replace the NCCER 11 percent (December 2023) and IWPR roughly 3 percent (2024) figures with BLS CPS 2025 figures and linked original sources."},
            {"item": "leadership proof", "decision": "Replace the unverifiable Carnrick, Lawrie and Paku quotes with the single vault-approved Foster Plumbing revenue metric and its case-study link."},
            {"item": "thesis", "decision": "Pivot from a seasonal observance to an employer guide on solving the skilled labor gap by recruiting and retaining women."},
        ],
        "add": [
            {"item": "early artifact and checklists", "decision": "Add a role-level share table in the first 300 words, a career ladder checklist, a retention checklist and a 90-day roadmap."},
            {"item": "FAQs and schema notes", "decision": "Add five answer-first FAQs from the brief's pre-picked Google PAA questions and FAQPage schema notes."},
            {"item": "original images", "decision": "Add jobsite technology, career pathway and scheduling images with keyword filenames and alt text."},
            {"item": "commercial pillar and cluster links", "decision": "Add the homepage field service management software link, the mobile app feature link, and the women-in-trades guide link."},
        ],
        "remove": [
            {"item": "event-dated framing", "decision": "Remove the March 1 to 7 opening and the WIC Week-led H2s, keeping WIC Week only as a recognition FAQ."},
            {"item": "unverifiable quotes", "decision": "Remove the three live quotes because none appears verbatim on its linked source page."},
            {"item": "story blog links", "decision": "Remove the toolbox-tech-webinar, heroes-of-the-trade-dawn-lawrie and heroes-of-the-trade-vertac links, which only supported the removed quotes."},
            {"item": "NAWIC 2026 theme link", "decision": "Replace the event-year NAWIC announcement link with the evergreen NAWIC WIC Week page in the FAQ."},
        ],
    },
    "audience_language_research": {
        "status": "not_applicable",
        "rationale": "The brief does not request community language research. The article is an employer guide built on official data; plain contractor language from vault voice guidance fits without community quotes.",
        "source_urls": [], "observations": [], "intended_section_use": [],
    },
    "keyword_decision": {
        "status": "resolved",
        "artifact_schema": "simpro-semrush-keyword-decision/v1",
        "source": "semrush_connector",
        "database": "us",
        "selected_primary_keyword": PRIMARY,
        "selected_secondary_keywords": SECONDARY,
        "selection_rationale": f"Authenticated Semrush US desktop UI evidence dated {DATE} confirms women in construction as the informational head term with the two close variants as secondaries. Labor-shortage terms stay with the existing shortage articles and job-seeker terms with the women-in-skilled-trades guide. Bound artifact: research/semrush-keyword-decision-{SLUG}-{DATE}.json.",
    },
    "faq_policy": {"status": "required", "rationale": "Google PAA for women in construction supplies five adjacent questions, each answerable with official sources."},
    "paa_policy": {"source_kind": "brief_paa", "query": PRIMARY, "selected_questions": PAA},
    "search_strategy": {
        "primary_query": PRIMARY,
        "searcher_task": "Understand where women work in construction and how a contractor attracts, develops and keeps women to close skilled labor gaps.",
        "intent_class": "informational",
        "funnel_stage": "tofu",
        "serp_evidence_artifact": f"research/serp-evidence-{SLUG}-{DATE}.json",
        "dominant_content_type": "General Article",
        "selected_content_type": "How-To Guide",
        "observed_serp_features": ["AI Overview", "People also ask"],
        "related_query_paa_artifact": f"research/content-brief-{SLUG}-{DATE}.md",
        "format_decision": "documented_exception",
        "exception_reason": "The page-one SERP is dominated by association homepages, news and statistics roundups classed as general articles, and none serves the contractor who has to recruit and keep women. The guide format answers the statistics intent with an early role table and adds the missing employer playbook.",
        "status": "ready",
    },
    "commercial_strategy": {
        "article_title": TITLE,
        "article_primary_keyword": PRIMARY,
        "article_intent": "informational",
        "destination_id": "simpro-us-homepage-field-service-management-software",
        "commercial_pillar_url": HOME,
        "planned_anchor_text": "field service management software",
        "planned_h2_section": "A 90-day roadmap for trade business owners",
        "existing_overlapping_urls_checked": [
            "https://www.simprogroup.com/blog/women-in-construction-week",
            WOMEN_GUIDE,
            "https://www.simprogroup.com/blog/women-breaking-barriers-in-field-service",
            SHORTAGE,
            "https://www.simprogroup.com/blog/trades-labor-shortage",
        ],
        "pillar_versus_blog_intent_difference": "The homepage has product-proposition intent for trade contractors buying software, while this blog has informational employer intent about recruiting and retaining women. The women-in-skilled-trades guide serves job seekers and the shortage articles own labor-shortage terms. The legacy week URL is replaced by this article with a recommended 301.",
        "cannibalization_decision": "different_intent",
        "incoming_link_candidates": [WOMEN_GUIDE, "https://www.simprogroup.com/blog/women-breaking-barriers-in-field-service", SHORTAGE],
        "status": "aligned",
    },
    "lifecycle": {
        "last_updated_date": DATE,
        "volatility": "high",
        "next_review_date": "2026-12-24",
        "review_command": "/performance-review published/women-in-construction.md",
        "gsc_lane": "available: GSC URL Inspection for the legacy week URL reported Crawled - currently not indexed with no 90-day query data, per the intake receipt dated 2026-08-18",
        "ga4_lane": "available: GA4 2026-02-20 to 2026-05-20 shows 378 sessions and 0 key events for the legacy week URL",
        "semrush_lane": f"available: US keyword decision captured in the main Chrome Semrush UI on {DATE} and verified homepage commercial-pillar record",
        "ai_citation_lane": "unavailable: no AI-citation export was collected for this assembly; do not infer citation performance from missing observations",
        "decision": "update",
        "status": "scheduled",
    },
}


def main() -> int:
    atomic_write_json(OUT, PLAN)
    print(f"wrote {OUT.relative_to(ROOT).as_posix()} total_word_target={PLAN['total_word_target']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
