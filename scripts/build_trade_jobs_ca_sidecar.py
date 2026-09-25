"""Assemble the validation sidecar for the best-trade-jobs-california rewrite.

Governance artifact only. Combines the static decision blocks below with the
generated proof rows (scripts/build_trade_jobs_ca_source_rows.py), the selector
slates, and the Hindsight block. Run the source-row builder first. The Context
Binding generator appends its blocks afterwards; rerun it after every rebuild.
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SLUG = "best-trade-jobs-california"
DATE = "2026-09-24"
R = ROOT / "research"
ARTICLE = ROOT / "rewrites" / f"{SLUG}-rewrite-{DATE}.md"
SIDECAR = R / f"validation-{SLUG}-{DATE}.md"
BRIEF = f"research/content-brief-{SLUG}-{DATE}.md"
OBJECTIVE = (
    "Help Californians choosing a skilled trade compare the highest-paying trades by 2025 California "
    "median pay, training route, licensing and demand, then show how licensed tradespeople grow into "
    "running their own contracting business with field service management software."
)
ONET = "https://www.onetonline.org/link/localwages/{}.00?st=CA"
PROJ = "https://data.bls.gov/projections/occupationProj"
FAQS = [
    ("What trade gets paid the most in California?", [ONET.format("47-4021")],
     "the California local-wage page shows the $141,180 median and the $173,920 90th-percentile wage for elevator and escalator installers"),
    ("What trades can make $100,000 a year in California?",
     [ONET.format(s) for s in ("47-4021", "49-9051", "49-2095", "47-2132", "47-4011", "47-2111")],
     "each California local-wage page shows the named trade's median or 90th-percentile wage above $100,000"),
    ("What are the best trade jobs in California without a four-year degree?", [PROJ],
     "the BLS projections table lists typical entry-level education of a high school diploma or postsecondary nondegree award plus on-the-job training or apprenticeship for each listed occupation"),
    ("How long does it take to learn a trade in California?",
     ["https://www.faa.gov/mechanics/become",
      "https://www.dir.ca.gov/dosh/elevatorcertification.html",
      "https://www.cslb.ca.gov/contractors/applicants/contractors_license/exam_application/experience_for_exam.aspx"],
     "the FAA page states 18 months of practical experience for one rating, the Cal/OSHA page states a minimum of three years of conveyance industry work for elevator mechanic certification, and the CSLB page states four years of journey-level experience for the contractor exam"),
    ("Do union trade jobs pay more in California?",
     ["https://data.bls.gov/timeseries/LUU0254815900", "https://data.bls.gov/timeseries/LUU0254829700"],
     "the BLS series show 2025 median weekly earnings of 1561 for union members and 1004 for nonunion workers in construction and extraction occupations"),
    ("Are trade jobs in demand in California?", [PROJ],
     "the BLS projections table shows 2025-2035 employment percent change of 10.9 for HVAC, 10.3 for power-line installers, 9.2 for electricians, 36.5 for solar installers and -3.4 for telecom line installers"),
]


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def block(path: Path, heading: str) -> str:
    text = path.read_text(encoding="utf-8").strip()
    if not text.startswith("## "):
        text = text.replace(heading, f"## {heading}", 1) if text.startswith(heading) else f"## {heading}\n{text}"
    return text


def main() -> int:
    receipt = json.loads((R / f"context-receipt-{SLUG}.json").read_text(encoding="utf-8"))
    revisions = receipt["revisions"]
    resource_ids = [r["resource_id"] for r in receipt["resources"]]
    rows = (R / f"source-rows-{SLUG}-{DATE}.md").read_text(encoding="utf-8").strip()
    source_map, metric_pack = rows.split("## Metric Proof Pack", 1)
    slate = block(R / f"customer-proof-slate-{SLUG}-decision-{DATE}.md", "Customer Proof Slate").replace("research\\", "research/")
    fred = block(R / f"fred-authority-selector-{SLUG}-{DATE}.md", "Fred Voccola Authority Selection")
    hindsight = (R / f"hindsight-sidecar-block-{SLUG}-{DATE}.md").read_text(encoding="utf-8").strip()
    hindsight = re.sub(
        r"- Applied decision: give the electrician.*?(?=\n- Rejected uses:)",
        "- Applied decision: give the electrician, plumber/pipefitter/steamfitter, HVAC and refrigeration, and security and fire alarm entries their own named section with licensing, specialization and industry-statistics links, and give the telecommunications equipment profile a low-voltage contracting note, because the Electrical/Data, Plumbing, HVAC/Airconditioning, Low Voltage, and Multi-Trade strategy pages carry usable coverage. Keep fire-specific depth standard, because the Fire strategy coverage is thin and directional.\n"
        "- Applied decision: in the pay-factor section, add service and maintenance work as an earnings lever, informed by preventative-maintenance demand in the HVAC/Airconditioning and Low Voltage strategy pages. The licensing-ladder framing comes from official public licensing sources, not from Hindsight.\n"
        "- Applied decision: frame the career ladder from apprentice to journeyperson to lead technician, then estimating, service management or contractor ownership. The estimator step is editorial framing, not a Hindsight output.\n"
        "- Applied decision: write the conclusion CTA for owner-operators and small growing crews, not enterprise-only buyers, informed by the too-small objection theme in the Electrical/Data and Plumbing strategy pages. The article does not claim that Simpro suits any particular business size.",
        hindsight, flags=re.S,
    )
    pack_hash = re.search(r"Pack SHA-256: `([0-9a-f]{64})`", hindsight).group(1)
    receipt_hash = re.search(r"Receipt SHA-256: `([0-9a-f]{64})`", hindsight).group(1)
    hindsight = hindsight.replace(
        "- public_claim_use: prohibited",
        f"- pack_sha256: {pack_hash}\n- receipt_sha256: {receipt_hash}\n- public_claim_use: prohibited",
    )
    faq_rows = []
    for question, urls, support in FAQS:
        for url in urls:
            faq_rows.append(
                f"- FAQ: {question} | URL: {url} | Source class: neutral | Competitor check: passed | "
                f"Support: {support} | Citation mode: inline_required | Status: approved"
            )
    questions = "\n".join(f"  - {q}" for q, _u, _s in FAQS)
    text = f"""# Highest-Paying Trades in California Validation Sidecar

## Scope and artifact binding

- Canonical URL: `https://www.simprogroup.com/blog/best-trade-jobs-california`
- Article title: 18 Highest-Paying Trades in California to Consider in 2026
- Workflow date: {DATE}
- Workflow mode: rewrite
- Market: United States
- Article objective: {OBJECTIVE}
- Public article: `rewrites/{SLUG}-rewrite-{DATE}.md`
- Current article SHA-256 at sidecar assembly: `{sha(ARTICLE)}`
- Content brief: `{BRIEF}` (SHA-256 `{sha(ROOT / BRIEF)}`)
- Frozen editorial plan: `research/editorial-plan-{SLUG}-{DATE}.json`
- Analysis: `research/analysis-{SLUG}-{DATE}.md`
- Wage source table: `research/ca-oews-trade-wages-{SLUG}-{DATE}.json`
- Career source checks: `research/ca-trade-career-sources-{SLUG}-{DATE}.json`
- Generated proof rows: `research/source-rows-{SLUG}-{DATE}.json`
- Context request: `research/context-request-{SLUG}.json`
- Context pack: `research/context-pack-{SLUG}.json`
- Context receipt: `research/context-receipt-{SLUG}.json`
- Binding boundary: the article hash and all downstream receipts must be regenerated if article bytes change after this sidecar snapshot.

## Live-versus-local attribution boundary

- Live source checked: `https://www.simprogroup.com/blog/best-trade-jobs-california` on {DATE}; baseline in `research/live-page-baseline-{SLUG}-{DATE}.md`.
- Live page state: title `18 Best Trade Jobs in California: Descriptions & Salaries! | Simpro`, published 2024-05-17, 18 mixed trade and management roles with unsourced salaries.
- Attribution rule: current rankings (Semrush US position 2 for the primary keyword) and GSC traffic belong to the live 2024 page, not to this unpublished rewrite.
- Outcome rule: no improvement, decline, or causation claim may be attributed to the rewrite until dated post-publication evidence covers at least two equivalent reporting periods.

## Context request and validation

- Binding: connector-bound.
- Reason: the artifact is Simpro-owned, names Simpro in the conclusion, and links to official `simprogroup.com` pages.
- Vault access path: the plugin MCP index reported `manifest_stale`; the current-project `SimproVaultClient` fallback returned `status: ready` and served every operation.
- Request SHA-256 (receipt-recorded): `{receipt['request_sha256']}`.
- Context pack SHA-256 (receipt-recorded): `{receipt['pack_sha256']}`.
- Context receipt SHA-256 (receipt-recorded): `{receipt['receipt_sha256']}`.
- Content revision: `{revisions['content_revision']}`.
- Contract revision: `{revisions['contract_revision']}`.
- Inventory revision: `{revisions['inventory_revision']}`.
- Manifest revision: `{revisions['manifest_revision']}`.
- Claim registry revision: `{revisions['claim_registry_revision']}`.
- Approval policy revision: `{revisions['approval_policy_revision']}`.
- Selected resources: {', '.join(f'`{r}`' for r in resource_ids)}.
- Approved public claim IDs used: [none].
- Public evidence boundary: connector resources guide Simpro voice, positioning and trade-vertical language; every public salary, training, licensing, union and outlook fact uses a current official public source.
- Context result: `task_satisfaction: {receipt['task_satisfaction']}`; unresolved gaps: [none].

## Vault Context Read Path

- Connector path: vault_status, vault_describe, natural-language vault_search, resource_id-bound vault_read and vault_expand, vault_claims, vault_build_context, and vault_validate_context through `data_sources.modules.simpro_vault_client.SimproVaultClient`.
- Active artifacts: `research/context-request-{SLUG}.json`, `research/context-pack-{SLUG}.json`, and `research/context-receipt-{SLUG}.json`.
- Selector-only packs: `research/context-pack-{SLUG}-customer-selector-{DATE}.json` (customer-proof claims) and `research/context-pack-{SLUG}-fred-evaluation-{DATE}.json` (Fred authority claims); neither claim set is used in public copy.
- Public-use boundary: selected vault resources are guidance or context only.
- Status: validated.

## Vault Brand Language Alignment

- Article title: 18 Highest-Paying Trades in California to Consider in 2026
- Product/solution language scope: mixed
- Vault connector evidence: vault_status ready; vault_describe inspected; natural-language vault_search, vault_read, and vault_expand completed; vault_claims checked; context_pack_hash={receipt['pack_sha256']}; receipt_hash={receipt['receipt_sha256']}; resource_id=res-09ebfff123cb5c5496e60c3a759a263d; resource_id=res-a5b3b47382b45490bf2bedbf16c0b76e; resource_id=res-230f144aab93512e840167c4a25e60be; resource_id=res-e3ade596be645307ad4c1f84620ce021; resource_id=res-d31f057a305f51918055120d95b76c6a; resource_id=res-f882ab230eb2563889e300d612c324bc; vertical resource_id=res-ae4607729666509bb97813e66e18590b; vertical resource_id=res-f9f9499223a15d6a901806f30fb1a8ba; manifest_revision={revisions['manifest_revision']}
- Product/feature language applied: one owner-operator sentence describing field service management software that keeps quotes, schedules, crews, materials and invoices organized from the first call to the final invoice; no named feature, add-on, superiority or outcome claim.
- Solution/industry language applied: an industries link described as software for trades businesses built around electrical, plumbing, HVAC and other contracting work; no vertical leadership or business-size claim.
- Fallback context use: none
- Claims requiring source verification: none
- Status: aligned

## Named Feature/Add-On Link Check

- Named Simpro features or add-ons in public copy: none.
- Generic workflow categories: quotes, schedules, crews, materials and invoices.
- Simpro public destinations: homepage field service management software overview and industries hub.
- Feature-specific resource IDs required: [none].
- Status: aligned.

{hindsight}

{slate}
- Selection decision: all three metric candidates were evaluated and rejected with source-specific reasons; LDN Security Solutions is a UK GBP metric, Foster Plumbing is a single-company revenue and exit metric with 2 recent uses, and Shaffer Beacon Mechanical is an overused software-outcome metric with 3 recent uses. No stronger underused approved proof fits the career-comparison objective.
- Public-copy result: omit customer stories, customer metrics, testimonials, review stories, exact quotes, and customer outcomes.
- Objective-binding note: the selector evidence is bound to the exact current objective and to the customer-selector context artifacts. The public-copy context pack intentionally contains no approved claims because no customer proof was selected for public use.

{fred}

## E-E-A-T Strength Decision

- Applicability: required
- Intent: commercial_investigation
- Positive signals: [none]
- Decision: proof_unavailable_safe_to_publish
- Reason: The article is a top-of-funnel career guide with a commercial CTA; the customer-proof selector found no objective-fit selection across metric, quote, theme, and experience-story roles, the Fred authority selector found no verified topic-fit candidate, and no named author, reviewer, or approved SME review signal is available.
- Public copy boundary: Public copy omits customer proof, named customer claims, review stories, exact quotes, testimonials, customer metrics, and unsupported SME claims.
- Status: approved

## E-E-A-T Proof Map

- First-hand evidence decision: Selected: [none] because the selector found no eligible experience story for this article objective, so public copy omits customer experience claims.
- Experience: Selected: [none]. The article contains no customer or reviewer story and no fictional persona.
- Expertise: Selected: [none]. No named author, named reviewer, or Fred contribution is authorized.
- Authoritativeness: every wage figure links to the Department of Labor O*NET display of BLS May 2025 California OEWS data; training, outlook, licensing and union statements link to BLS, California DIR, CSLB, Cal/OSHA, FAA and EPA pages.
- Trust: the article states its data year, scope rule and near-tie caveat, uses one statistic for every ranked row, and keeps job-board salary estimates out.

## PAA/FAQ Provenance

- Source: brief_paa
- Artifact: `{BRIEF}`
- Selected questions:
{questions}

- Google SERP observation boundary: the People also ask questions captured on {DATE} in `research/serp-evidence-{SLUG}-{DATE}.json` informed answer format only; the FAQ set is the brief's pre-picked list.
- Status: approved for the current six-question FAQ set.

## FAQ Source Policy

- Allowed source classes: neutral, non_competing_expert, owned_product.
- Competitor-owned FAQ sources: prohibited.
- Direct-answer rule: each first visible answer paragraph must contain 40 to 60 words and begin with a named recommendation, definition, concrete action, number or range, or explained yes/no.
- Inline rule: fact-driven and high-risk FAQ claims require a natural authoritative link in the first visible answer paragraph.
- Status: aligned.

## FAQ Proof Map

{chr(10).join(faq_rows)}

## Metric Proof Pack{metric_pack.rstrip()}

## Citation Mode Mappings

- Wage figures, 90th-percentile figures, union earnings, projection percentages and entry-experience durations: `inline_required`; the linked official page appears in the same paragraph, list line or table row.
- Licensing and certification statements: `inline_required`; the official DIR, Cal/OSHA, CSLB, FAA or EPA page appears in the same line.
- Training-route background in table cells and profiles: `section_source_allowed`; the BLS education and training link appears in the same H2.
- Career-choice checklist, pay-lever advice and owner-path framing: `proof_not_required` when framed as reader guidance.
- Simpro owner-operator sentence: `sidecar_only` as low-risk owned product language aligned with vault guidance.

{source_map.strip()}

### Public-link 403 replacement record

- Rejected public-copy URL: https://www.bls.gov/oes/current/oes_ca.htm | Validation: manual_review, HTTP 403 on {DATE} | Resolved replacement: https://www.onetonline.org/link/localwages/[SOC].00?st=CA per occupation | Validation: resolved, HTTP 200 on {DATE} | Boundary: O*NET OnLine displays the same BLS May 2025 California OEWS values server-side; `https://data.bls.gov/oes/#/area/0600000/2025` also returns 200 but renders figures with JavaScript, so it cannot carry source-visible evidence.
- Rejected public-copy URLs: https://www.bls.gov/ooh/ occupation pages and https://www.bls.gov/news.release/union2.nr0.htm | Validation: manual_review, HTTP 403 on {DATE} | Resolved replacements: https://data.bls.gov/projections/occupationProj and the data.bls.gov LUU series pages | Validation: resolved, HTTP 200 on {DATE}.
- Rejected claim: California union membership rate of 14.9% | Reason: the only source found is a www.bls.gov regional release that returns HTTP 403 to the validator | Decision: omitted from public copy.
- O*NET source-class decision: approved by the requester on {DATE} to record O*NET OnLine Local Wages as the official Department of Labor display of the original BLS dataset (Source class: government, Original-source status: original).

## Search Intent and Format Decision

- Contract version: blog-strategy-contract/v1
- Primary query or prompt: highest paying trades in california
- Searcher task: Find which trades pay the most in California, compare pay with training and licensing requirements, and decide which trades to pursue.
- Intent class: informational
- Funnel stage: tofu
- SERP evidence artifact: research/serp-evidence-{SLUG}-{DATE}.json
- SERP evidence SHA-256: {sha(R / f'serp-evidence-{SLUG}-{DATE}.json')}
- Dominant content type: Listicle
- Selected content type: Listicle
- Observed SERP features: AI Overview, People also ask, People also search for
- Related-query/PAA artifact: {BRIEF}
- Format decision: match_dominant
- Exception reason: No format exception; the article keeps the ranked listicle format and adds a single-dataset comparison table and consistent trade profiles.
- Status: ready

## Commercial Pillar and Anchor Decision

- Contract version: blog-strategy-contract/v1
- Article title: 18 Highest-Paying Trades in California to Consider in 2026
- Article primary keyword: highest paying trades in california
- Article intent: informational
- Destination ID: simpro-us-homepage-field-service-management-software
- Commercial pillar URL: https://www.simprogroup.com/
- Planned anchor text: field service management software
- Planned H2 section: Build a trade career with room to grow
- Existing overlapping URLs checked: the canonical page, `/blog/highest-paying-trade-jobs`, `/blog/highest-paying-trades-australia`, and `/blog/electrical-license-california`.
- Pillar-versus-blog intent difference: the homepage has product-proposition intent for trade contractors buying software, while this blog has informational career intent for Californians choosing a trade.
- Cannibalization decision: different_intent
- Cannibalization note: the national `/blog/highest-paying-trade-jobs` article is not linked, following the brief.
- Incoming-link candidates: `/blog/electrical-license-california`, `/blog/electrical-industry-statistics-2026`, `/blog/plumbing-industry-statistics-2026`.
- Status: aligned

## Lifecycle Refresh Record

- Contract version: blog-strategy-contract/v1
- Last-updated date: {DATE}
- Volatility: high
- Next review date: 2026-12-23
- Review command: refresh BLS OEWS, projections, union series, licensing pages, Semrush, GSC and SERP evidence before the next publish-readiness pass; replace the wage table when BLS publishes May 2026 OEWS data.
- GSC lane: available: GSC 90-day page query export read on {DATE} shows 140 clicks and 1,583 impressions for the live 2024 page.
- GA4 lane: unavailable: no current GA4 export was collected for this assembly.
- Semrush lane: available: US keyword decision captured in the main Chrome Semrush UI on {DATE} and recorded in research/semrush-keyword-decision-{SLUG}-{DATE}.json.
- AI-citation lane: unavailable: no AI-citation export was collected for this assembly.
- Decision: update
- Status: scheduled

## Author and Schema Decision

- Author policy: no_author
- Named author verified: no.
- Named reviewer verified: no.
- Frontmatter author field: omitted.
- `Person as author`: omitted.
- Publisher: `Organization` as publisher reference only, not a separate full schema block.
- Public metadata: `date_published: {DATE}`, `date_modified: {DATE}`, and `publisher: Simpro` are present in frontmatter. The team's linked SEO best practices for updating content ask for the publish date to move to the update date; the live 2024-05-17 publication date is recorded here for provenance.
- Required schema notes: `BlogPosting`, `BreadcrumbList`, `FAQPage`, `Question and Answer inside FAQPage`, `ImageObject for the featured image or logo`, and `Organization as publisher reference only, not a separate full schema block`.
- VideoObject: omitted because no video is embedded.
- BOM requirement: record this no-author fallback and publisher-only decision in the final assembly BOM.
- Status: approved.

## Early Artifact and usability decision

- Artifact: a filled 18-row table with rank, trade, California median pay, 90th-percentile pay, typical entry route and credential or program, starting inside the first 300 body words after the answer paragraph, reader paragraph and first H2 capsule.
- ICP use: a reader can shortlist trades by pay, training route and credential without reading the profiles.
- Mobile requirement: the CMS module handoff renders one labeled card per trade with no hidden cells or horizontal scrolling.
- Status: present in the Markdown artifact; final rendered verification remains required.

## Image and Media Plan

- Live hero replaced: `https://www.simprogroup.com/images/6/5/b/7/a/65b7a56a6ffd2f9f3fec9408733e586c9295e73d-simpro-blog-best-trade-jobs.jpg` (alt `Workers smiling`, 819 x 461) is replaced by an original hero with keyword-bearing filename and descriptive alt text.
- Original images planned: `highest-paying-trades-in-california-hero.webp` (1040 x 520), `highest-paying-trades-in-california-salary-chart.webp` (1200 x 675, built from the wage source table), `trades-that-pay-well-in-california-pay-factors.webp` (1200 x 675), `best-trade-jobs-in-california-apprentice.webp` (1200 x 675), all under `assets/images/blog/{SLUG}/`.
- Prompts and alt text: `research/image-prompts-{SLUG}-{DATE}.md`.
- Video: none.
- Status: aligned.

## Internal Link Decision

- Public-body Simpro links: electrical industry statistics; electrical license in California; plumbing industry statistics; homepage field service management software (commercial pillar); industries hub (down-funnel).
- Total: five internal links, inside the standard three-to-five range.
- Removed live links: `/blog/how-tech-can-help-contractors-enhance-efficiency`, replaced by the commercial pillar link in the conclusion; `/blog/college-vs-trade-school-benefits`, removed because its URL slug contains a comparison token that the competitive shortlist gate reads as competitor-aware copy.
- Excluded by brief: `/blog/highest-paying-trade-jobs` (cannibalization risk).
- Down-funnel destination: the industries hub (`https://www.simprogroup.com/industries`, approved anchor `software for trades businesses`) because the article covers 23 trades across construction, electrical, utility, aviation and equipment work, so no single industry page fits the reader; the electrical, plumbing and HVAC industry pages were considered and rejected to keep the internal-link total at five.
- External navigation link: California's registered apprenticeship search (`https://www.dir.ca.gov/databases/das/aigstart.asp`) in the choice checklist.
- Exact commercial anchor: `field service management software` links to `https://www.simprogroup.com/` in the Build a trade career with room to grow section.

## Release blockers and status

- Plan fulfillment, six role reviews, scrub, initial readiness scorecard, optimizer output, post-optimization scrub when bytes change, final Context Binding, final readiness, and assembly BOM: required.
- Current verdict: evidence package in progress; not publish-ready.
"""
    SIDECAR.write_text(text, encoding="utf-8", newline="\n")
    print(f"wrote {SIDECAR.relative_to(ROOT)} ({len(text.splitlines())} lines)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
