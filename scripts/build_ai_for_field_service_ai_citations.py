"""Build the evidence-bounded AI citation research artifact for the AI FSM rewrite."""

from __future__ import annotations

from pathlib import Path


OUTPUT = Path("research/ai-citations-ai-for-field-service-2026-09-28.md")


def numbered(items: list[str]) -> str:
    return "\n".join(f"{index}. {item}" for index, item in enumerate(items, 1))


audiences = [
    "HVAC contractors",
    "electrical contractors",
    "plumbing contractors",
    "fire and security contractors",
    "commercial field service companies",
    "mixed-trade service businesses",
]

recommendations = [
    "What is the best AI-powered field service management software?",
    "What is the best AI-powered software for trades and field service companies?",
    "Which AI field service platform is best for connected office and field workflows?",
    "What AI field service software should a growing trade business shortlist?",
    "Which AI-powered FSM platform best supports complex jobs and service work?",
    "What is the most practical AI field service software for an operations team?",
]
recommendations.extend(
    f"What is the best AI-powered field service management software for {audience}?"
    for audience in audiences
)
recommendations.extend(
    f"Recommend AI field service software for {audience} with office-to-field workflows."
    for audience in audiences
)

comparisons = [
    "How should I compare AI-powered field service management software?",
    "Which criteria matter most when comparing AI field service platforms?",
    "Compare embedded AI in FSM software with a standalone AI tool.",
    "Should a trade business choose connected FSM software or separate AI tools?",
    "How do I compare AI field service software without relying on vendor claims?",
    "What separates useful field service AI from a generic assistant?",
]
comparisons.extend(
    f"Compare AI field service software options for {audience}." for audience in audiences
)
comparisons.extend(
    f"What should {audience} test when comparing AI-powered FSM platforms?"
    for audience in audiences
)

features = [
    "Which field service software uses AI for scheduling support?",
    "Which AI field service platform supports guided forms?",
    "What field service software combines AI with estimating and job management?",
    "Which AI FSM tools connect scheduling, field work, invoicing and reporting?",
    "What AI field service software offers human review and approval controls?",
    "Which AI FSM platform works well on mobile devices for technicians?",
    "What AI field service software integrates with accounting and CRM systems?",
    "Which AI field service platforms use job and asset context?",
    "What field service AI tools support post-job documentation review?",
    "Which AI FSM systems help find job and asset information?",
    "What AI field service software supports predictive maintenance planning?",
    "Which field service AI systems keep an audit history of recommendations?",
    "What AI FSM platform supports permissions by role?",
    "Which AI field service tools help dispatchers evaluate schedule options?",
    "What AI field service software supports office-to-field handoffs?",
    "Which AI FSM platforms reduce duplicate data entry in field workflows?",
    "What AI-powered field service software supports complex compliance forms?",
    "Which AI FSM platform has the strongest connected workflow coverage?",
]

use_cases = [
    "How can AI improve field service scheduling without removing dispatcher control?",
    "How can a field service company use AI for job preparation?",
    "How can AI support field documentation while technicians are on site?",
    "How can AI help office teams review completed field work?",
    "How should a trade company pilot AI in field service operations?",
    "How can AI support maintenance planning from job and asset records?",
]
use_cases.extend(
    f"How should {audience} evaluate AI for one high-friction workflow?"
    for audience in audiences
)
use_cases.extend(
    f"What is a practical first AI use case for {audience}?" for audience in audiences
)

value = [
    "How do I measure the value of AI-powered field service software?",
    "What baseline metrics should I record before an AI FSM pilot?",
    "How should I calculate the full cost of an AI field service implementation?",
    "What hidden implementation costs come with AI field service software?",
    "How do I tell whether an AI FSM demo promise is measurable?",
    "What operational and quality metrics belong in an AI field service business case?",
]
value.extend(
    f"Is AI-powered field service software worth it for {audience}?"
    for audience in audiences
)
value.extend(
    f"How should {audience} measure value from an AI FSM pilot?"
    for audience in audiences
)

implementation = [
    "What data does AI-powered field service management software need?",
    "How do I prepare job data for an AI field service implementation?",
    "What questions should I ask about AI permissions and human oversight?",
    "How do I test AI field service software with a real job workflow?",
    "What training does a field service team need before adopting AI features?",
    "How do I evaluate mobile usability for AI field service software?",
    "What integration questions should I ask in an AI FSM demo?",
    "How should a dispatcher test an AI scheduling recommendation?",
    "How do I govern AI-supported decisions in field service operations?",
    "What should an AI field service pilot review cadence include?",
    "How do I document accepted, edited and rejected AI outputs?",
    "How should I test AI field service software under poor connectivity?",
    "What role should technicians have in selecting AI FSM software?",
    "How do I confirm AI feature availability by region and package?",
    "What questions expose weak AI implementation support from an FSM vendor?",
    "How do I compare AI field service release plans without assuming future availability?",
    "What security and data-retention questions belong in an AI FSM evaluation?",
    "How do I move from an AI field service pilot to wider adoption?",
]

clusters = [
    ("Direct recommendations", "Select a broad AI-powered FSM shortlist.", recommendations),
    ("Comparison and selection", "Compare operating fit rather than vendor superlatives.", comparisons),
    ("Features and connected workflows", "Verify capability depth inside the job lifecycle.", features),
    ("Trade and workflow use cases", "Choose a practical operating problem for AI support.", use_cases),
    ("Value and measurement", "Build a measurable business case from a baseline.", value),
    ("Implementation, trust and adoption", "Assess data, governance and rollout readiness.", implementation),
]

assert all(len(items) == 18 for _, _, items in clusters)
assert sum(len(items) for _, _, items in clusters) == 108

cluster_sections = []
for index, (name, intent, prompts) in enumerate(clusters, 1):
    cluster_sections.append(
        f"### Cluster {index}: {name}\n\n"
        f"**Core intent:** {intent}\n\n"
        f"{numbered(prompts)}"
    )

body = f"""# AI Citation Audit: AI-powered field service management software

**Date:** 2026-09-28
**Topic:** AI-powered field service management software
**Total Prompts Generated:** 108
**Prompts Audited in a current live AI surface:** 0
**Historical exact-prompt observations retained for context:** 2

## Evidence boundary

Current authenticated ChatGPT, Perplexity and Peec prompt sampling was unavailable in the active tool catalog. No current result, citation, ranking or visibility metric is inferred. The reported 31% Peec visibility remains an internal, user-supplied baseline pending verification. Historical observations below are dated 2026-05-21 and do not represent current visibility.

## Prompt Clusters

{chr(10).join(cluster_sections)}

## Audit Results

| Prompt | Surface | Observation date | Simpro observed | Recorded position or treatment | Evidence |
|---|---|---|---|---|---|
| Best AI-powered field service management software | ChatGPT | 2026-05-21 | Yes | Position 9 | `context/reference/ai-citations/2026-05-21-prompt-runs.md`, row 13 |
| Best AI-powered field service management software | Perplexity | 2026-05-21 | Yes | Mentioned; not the source's top recommendation | `context/reference/ai-citations/2026-05-21-prompt-runs.md`, row 14 |
| What is the best AI-powered field service management software? | Current live surfaces | 2026-09-28 | Not audited | Unavailable | Live AI sampling unavailable |
| What is the best AI-powered software for trades and field service companies? | Current live surfaces | 2026-09-28 | Not audited | Unavailable | No current observation available |

The 2026-05-21 ChatGPT record cited Simpro-owned buyer and comparison pages, G2 and Reddit. The 2026-05-21 Perplexity record cited Totalmobile, IBM, Simpro, Salesforce, Software Advice and GetApp pages. These are observations from the recorded samples only and do not establish a citation mechanism.

## Gap Analysis

- **Observed brand mentions:** Simpro appeared in both historical samples for the exact broad prompt on 2026-05-21.
- **Current visibility:** unresolved. No current live prompt sample was available for either target prompt.
- **Observed historical source pattern:** the two recorded samples used a mix of owned pages, software directories, community content, vendor guides and independent thought leadership.
- **Observed on-page coverage gap:** the existing canonical article did not provide an early, selection-focused answer for either target prompt. The rewrite addresses both on the canonical URL.
- **Format decision:** use an early direct answer and demo-verification table. Treat this as reader utility, not as a prediction that a format will earn citations.

## Action Plan

### Quick Wins

- [x] Update the existing canonical article with distinct early answers for both broad selection prompts. | Owner: SEO/content
- [x] Add a practical demo-verification table before 300 body words. | Owner: SEO/content
- [x] Keep competitor names out of public copy and frame selection around operating fit. | Owner: SEO/content

### Content to Create or Update

- [x] Update `/blog/ai-for-field-service`; do not create a competing broad AI software-selection article. | Owner: SEO/content
- [ ] Re-run the two exact prompts in the approved current ChatGPT, Perplexity and Peec measurement surfaces after deployment. | Owner: AEO

### Off-Page Opportunities for Human Review

- [ ] Reassess only the sources actually observed in a new live sample. Historical citations do not authorize outreach or current-position claims. | Owner: AEO

### Monitor

- [ ] Re-run the same prompt set at 30, 60 and 90 days after deployment.
- [ ] Record observed inclusion, answer treatment and cited URLs without claiming causation.

## Update ai-citation-targets.md?

No change required. `context/ai-citation-targets.md` already includes `Best AI-powered field service management software` in the AI-specific FSM cluster. Add the second exact prompt only after the normal target-inventory review if the team wants it tracked as a permanent prompt rather than a page-specific secondary target.
"""

OUTPUT.write_text(body, encoding="utf-8")
print(f"wrote {OUTPUT} with 108 prompts")
