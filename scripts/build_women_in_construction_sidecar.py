"""Assemble the validation sidecar for the women-in-construction rewrite.

Governance artifact only. Combines static decision blocks with the generated
Source Map and Metric Proof Pack rows (build_women_in_construction_source_rows.py),
the customer-proof decision slate, the Fred selector block, and a Hindsight block
regenerated from the current Hindsight evidence. The Context Binding generator
appends its blocks afterwards; rerun it after every rebuild.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SLUG = "women-in-construction"
DATE = "2026-09-28"
R = ROOT / "research"
ARTICLE = ROOT / "rewrites" / f"{SLUG}-rewrite-{DATE}.md"
SIDECAR = R / f"validation-{SLUG}-{DATE}.md"
BRIEF = f"research/content-brief-{SLUG}-{DATE}.md"
TITLE = "Bridging the Trades Labor Gap: A Contractor's Guide to Attracting and Retaining Women in Construction"
OBJECTIVE = (
    "Help US trade contractors close skilled-labor gaps by attracting, developing, and retaining women "
    "across field and office roles, using jobsite technology, transparent career pathways, and connected "
    "field service software."
)
BLS18 = "https://www.bls.gov/cps/cpsaat18.htm"
BLS11 = "https://www.bls.gov/cps/cpsaat11.htm"
DOL = "https://www.dol.gov/sites/dolgov/files/ETA/opder/DASP/Trendlines/posts/2024_11/Trendlines_November_2024.html"
ABC = "https://www.abc.org/News-Media/News-Releases/abc-construction-industry-must-attract-349000-workers-in-2026-despite-macroeconomic-headwinds"
OSHA_FR = "https://www.osha.gov/laws-regs/federalregister/2024-12-12"
NAWIC = "https://nawic.org/wic-week/"
FAQS = [
    ("What percentage of the construction industry is women?", [BLS18, BLS11],
     "BLS CPS 2025 Table 18 shows women at 11.3 percent of construction industry employment and Table 11 shows 4.3 percent of construction and extraction occupations"),
    ("Is construction a good job for women?", [DOL],
     "DOL Trendlines states that in FY2024 there were almost 100,000 women active in apprenticeship"),
    ("Why are women in construction important?", [ABC],
     "the ABC release states the industry needs to attract an estimated 349,000 net new workers in 2026"),
    ("What are the challenges faced by women in construction?", [OSHA_FR],
     "the OSHA final rule states it is effective January 13, 2025 and requires construction PPE to properly fit each affected employee"),
    ("How to recognize women in construction?", [NAWIC],
     "the NAWIC WIC Week page states the week is held annually during the first full week of March"),
]


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(name: str) -> dict:
    return json.loads((R / name).read_text(encoding="utf-8"))


def hindsight_block() -> str:
    evidence = load(f"hindsight-strategy-evidence-{SLUG}-{DATE}.json")
    template = (R / f"hindsight-sidecar-block-{SLUG}-{DATE}.md").read_text(encoding="utf-8").strip()
    text = json.dumps(evidence)
    pack = evidence.get("pack_sha256") or _find(evidence, "pack_sha256")
    receipt = evidence.get("receipt_sha256") or _find(evidence, "receipt_sha256")
    brief_sha = sha(ROOT / BRIEF)
    lines = []
    for line in template.splitlines():
        if line.startswith("- Pack SHA-256:"):
            line = f"- Pack SHA-256: `{pack}`"
        elif line.startswith("- Receipt SHA-256:"):
            line = f"- Receipt SHA-256: `{receipt}`"
        elif line.startswith("- pack_sha256:"):
            line = f"- pack_sha256: {pack}"
        elif line.startswith("- receipt_sha256:"):
            line = f"- receipt_sha256: {receipt}"
        elif line.startswith("- Binding:"):
            line = (f"- Binding: the pack request is bound to `{BRIEF}` (SHA-256 `{brief_sha}`) "
                    "because the rewrite article did not exist when the pack was built.")
        lines.append(line)
    if pack not in text or receipt not in text:
        raise ValueError("Hindsight evidence hashes could not be resolved")
    return "\n".join(lines)


def _find(value, key):
    if isinstance(value, dict):
        if key in value:
            return value[key]
        for item in value.values():
            found = _find(item, key)
            if found:
                return found
    if isinstance(value, list):
        for item in value:
            found = _find(item, key)
            if found:
                return found
    return None


def main() -> int:
    receipt = load(f"context-receipt-{SLUG}.json")
    revisions = receipt["revisions"]
    resource_ids = [r["resource_id"] for r in receipt["resources"]]
    pack_hash = receipt["pack_sha256"]
    receipt_hash = receipt["receipt_sha256"]
    source_map = (R / f"source-rows-{SLUG}-{DATE}.md").read_text(encoding="utf-8").strip()
    metric_pack = (R / f"metric-proof-pack-{SLUG}-{DATE}.md").read_text(encoding="utf-8").strip()
    slate = (R / f"customer-proof-slate-{SLUG}-decision-{DATE}.md").read_text(encoding="utf-8-sig").strip()
    slate = slate.replace("research\\", "research/")
    if slate.startswith("Customer Proof Slate"):
        slate = "## " + slate
    story_note = ("  - No-fit reason: The selector returned no experience_story candidate with an approved connector claim for this objective; the five story rows added on 2026-09-25 have no connector claim, so public copy omits customer stories, quotes and testimonials.")
    lines = slate.splitlines()
    for i, line in enumerate(lines):
        if line.startswith("- Role: experience_story"):
            if "| Reason:" not in line:
                lines[i] = line + " | Reason: selector returned no experience_story candidate with an approved connector claim for this objective"
            if i + 1 < len(lines) and lines[i + 1].strip().startswith("- No-fit reason:"):
                lines[i + 1] = story_note
    slate = "\n".join(lines)
    fred = (R / f"fred-authority-selector-{SLUG}-{DATE}.md").read_text(encoding="utf-8").strip()
    hindsight = hindsight_block()
    serp = f"research/serp-evidence-{SLUG}-{DATE}.json"
    faq_rows = []
    for question, urls, support in FAQS:
        for url in urls:
            faq_rows.append(
                f"- FAQ: {question} | URL: {url} | Source class: neutral | Competitor check: passed | "
                f"Support: {support} | Citation mode: inline_required | Status: approved"
            )
    questions = "\n".join(f"  - {q}" for q, _u, _s in FAQS)
    labels = {"res-33deaefa546b56358549b9dfe84f72c6": "feature ", "res-1825898a11855f89be9bb69c544a6aa3": "feature ", "res-f882ab230eb2563889e300d612c324bc": "feature ", "res-cb1c8e417b42532cb65e6e59893cf459": "vertical ", "res-ae4607729666509bb97813e66e18590b": "vertical "}
    rid = "; ".join(f"{labels.get(r, '')}resource_id={r}" for r in resource_ids)
    text = f"""# Women in Construction Validation Sidecar

## Scope and artifact binding

- Canonical URL: `https://www.simprogroup.com/blog/women-in-construction`
- Legacy URL: `https://www.simprogroup.com/blog/women-in-construction-week` (301 to the canonical URL recommended to Web Development task 1217606454968139)
- Article title: {TITLE}
- Workflow date: {DATE}
- Workflow mode: rewrite
- Market: United States
- Article objective: {OBJECTIVE}
- Public article: `rewrites/{SLUG}-rewrite-{DATE}.md`
- Current article SHA-256 at sidecar assembly: `{sha(ARTICLE)}`
- Content brief: `{BRIEF}` (SHA-256 `{sha(ROOT / BRIEF)}`)
- Frozen editorial plan: `research/editorial-plan-{SLUG}-{DATE}.json`
- Analysis: `research/analysis-{SLUG}-{DATE}.md`
- Live-page baseline: `research/live-page-baseline-{SLUG}-{DATE}.md`
- Generated proof rows: `research/source-rows-{SLUG}-{DATE}.json`
- Context request: `research/context-request-{SLUG}.json`
- Context pack: `research/context-pack-{SLUG}.json`
- Context receipt: `research/context-receipt-{SLUG}.json`
- Binding boundary: the article hash and all downstream receipts must be regenerated if article bytes change after this sidecar snapshot.

## Live-versus-local attribution boundary

- Live source checked: `https://www.simprogroup.com/blog/women-in-construction-week` on 2026-09-25; baseline in `research/live-page-baseline-{SLUG}-{DATE}.md`.
- Live page state: title `Women in Construction Week: Expanding the Workforce Powering the Trades | Simpro`, published 2026-03-03, 683 words, GSC `Crawled - currently not indexed` with no 90-day query data.
- Removed live quotes: the Carnrick, Lawrie and Paku quotes were not verbatim on their linked source pages on 2026-09-25 and have no approved connector claim, so they are removed. The Foster Plumbing metric is also omitted because its approved wording has no source-visible public evidence.
- Outcome rule: no indexing, ranking, traffic or engagement improvement may be attributed to the rewrite until dated post-publication evidence covers at least two equivalent reporting periods.

## Context request and validation

- Binding: connector-bound.
- Reason: the artifact is Simpro-owned, links to official `simprogroup.com` pages.
- Vault access path: the plugin MCP index reported `manifest_stale`; the current-project `SimproVaultClient` fallback returned `status: ready` and served every operation.
- Request SHA-256 (receipt-recorded): `{receipt['request_sha256']}`.
- Context pack SHA-256 (receipt-recorded): `{pack_hash}`.
- Context receipt SHA-256 (receipt-recorded): `{receipt_hash}`.
- Content revision: `{revisions['content_revision']}`.
- Contract revision: `{revisions['contract_revision']}`.
- Inventory revision: `{revisions['inventory_revision']}`.
- Manifest revision: `{revisions['manifest_revision']}`.
- Claim registry revision: `{revisions['claim_registry_revision']}`.
- Approval policy revision: `{revisions['approval_policy_revision']}`.
- Selected resources: {', '.join(f'`{r}`' for r in resource_ids)}.
- Approved public claim IDs used: [none].
- Public evidence boundary: connector resources guide Simpro voice, positioning and trade language; every public workforce, apprenticeship, labor-demand, safety and event fact uses a current authoritative public source.
- Context result: `task_satisfaction: {receipt['task_satisfaction']}`; unresolved gaps: [none].

## Vault Context Read Path

- Connector path: vault_status, vault_describe, natural-language vault_search, resource_id-bound vault_read and vault_expand, vault_claims, vault_build_context, and vault_validate_context through `data_sources.modules.simpro_vault_client.SimproVaultClient`.
- Active artifacts: `research/context-request-{SLUG}.json`, `research/context-pack-{SLUG}.json`, and `research/context-receipt-{SLUG}.json`.
- Selector-only packs: `research/context-pack-{SLUG}-customer-selector-{DATE}.json` (customer-proof claims) and `research/context-pack-{SLUG}-fred-evaluation-{DATE}.json` (Fred authority claims).
- Public-use boundary: selected vault resources are guidance or context only.
- Status: validated.

## Vault Brand Language Alignment

- Article title: {TITLE}
- Product/solution language scope: mixed
- Vault connector evidence: vault_status ready; vault_describe inspected; natural-language vault_search, vault_read, and vault_expand completed; vault_claims checked; context_pack_hash={pack_hash}; receipt_hash={receipt_hash}; {rid}; manifest_revision={revisions['manifest_revision']}
- Product/feature language applied: field service management software described as keeping quotes, schedules, jobs and invoices in one place for the office and the field; scheduling described as balancing crew workloads with capacity, travel and skills in one view; the field service mobile app described as carrying job notes, forms and photos for technicians; technology framed as support for technicians, not surveillance; no named feature or add-on, superiority, availability, or outcome claim.
- Solution/industry language applied: trade contractors who self-perform field work on construction and service jobs; no general contractor, infrastructure construction, vertical leadership, or business-size claim.
- Fallback context use: none
- Claims requiring source verification: none
- Status: aligned

## Named Feature/Add-On Link Check

- Named Simpro features or add-ons in public copy: none.
- Generic workflow categories: field service scheduling, field service mobile app, shared scheduling software, field service management software.
- Feature resources checked: Simpro Datasheet (NA) res-33deaefa546b56358549b9dfe84f72c6 (scheduling and dispatching; mobile forms and site notes); Feature Datasheet Atlas res-1825898a11855f89be9bb69c544a6aa3 (no standalone scheduling or mobile-app feature page in the vault); Simpro Customer Personas res-09b1f4509ed65855894bd5f481ec81b1 (scheduler and field-technician language).
- Simpro public destinations and link decisions: https://www.simprogroup.com/ with the planned anchor `field service management software`; https://www.simprogroup.com/features/scheduling-software with the function-bearing anchor `field service scheduling that balances crew workloads`; https://www.simprogroup.com/features/field-service-mobile-app with the function-bearing anchor `field service mobile app for job notes, forms and photos`.
- Reason: both feature destinations are generic feature pages from `context/internal-links-map.md`; vault feature collateral supports the workflow descriptions, and no guarded named feature appears.
- Feature-specific resource IDs required: [none].
- Status: aligned.

{hindsight}

{slate}
- Selection decision: all three metric candidates were evaluated and rejected with source-specific reasons. Foster Plumbing claim-metric-MET-0178 reads "a 10X increase in six years", but the public case study shows "Five years later" and never "10X", and the vault source node is not public-claim usable, so the approved wording has no source-visible public evidence. LDN Security Solutions is a UK security-business metric and Shaffer Beacon Mechanical is an overused software-outcome headcount metric; neither fits this US employer guide. Quote, theme and experience_story roles returned no connector-approved candidates.
- Public-copy result: omit customer stories, customer metrics, testimonials, review stories, exact quotes, and customer outcomes.
- Objective-binding note: the selector evidence is bound to the exact current objective and to the customer-selector context artifacts. The public-copy context pack intentionally contains no approved claims because no customer proof was selected for public use.

{fred}

## E-E-A-T Strength Decision

- Applicability: required
- Intent: commercial_investigation
- Positive signals: [none]
- Decision: proof_unavailable_safe_to_publish
- Reason: The article is a top-of-funnel employer guide with a commercial CTA; the customer-proof selector found no objective-fit selection with source-visible public evidence across metric, quote, theme, and experience-story roles, the Fred authority selector found no verified topic-fit candidate, and no named author, reviewer, or approved SME review signal is available.
- Public copy boundary: Public copy omits customer proof, named customer claims, review stories, exact quotes, testimonials, customer metrics, and unsupported SME claims.
- Status: approved

## E-E-A-T Proof Map

- First-hand evidence decision: Selected: [none] because the selector found no eligible experience story with source-visible public evidence for this article objective, so public copy omits customer experience claims.
- Experience: Selected: [none]. The article contains no customer or reviewer story and no fictional persona.
- Expertise: Selected: [none]. No named author, named reviewer, or Fred contribution is authorized.
- Authoritativeness: workforce shares link to BLS CPS 2025 Tables 11 and 18 and the NAHB tabulation; apprenticeship figures link to DOL and IWPR; labor demand links to ABC and the AGC and NCCER survey; PPE and sanitation link to OSHA; WIC Week timing links to NAWIC.
- Trust: the article states the data year and table scope, warns against comparing the 11-month 2025 averages with earlier years, and removes quotes that could not be verified.

## PAA/FAQ Provenance

- Source: brief_paa
- Artifact: `{BRIEF}`
- Selected questions:
{questions}

- Question origin: Google US SERP People also ask and Things to know prompts observed in Chrome on 2026-09-25, transcribed into the brief's `## Pre-picked PAA Questions` section at the requester's direction after AnswerSocrates showed a free-quota blocker.
- Google SERP observation boundary: the assembly-day SERP capture in `{serp}` records answer format and features only.
- Status: approved for the current five-question FAQ set.

## FAQ Source Policy

- Allowed source classes: neutral, non_competing_expert, owned_product.
- Competitor-owned FAQ sources: prohibited.
- Direct-answer rule: each first visible answer paragraph must contain 40 to 60 words and begin with a named recommendation, definition, concrete action, number or range, or explained yes/no.
- Inline rule: fact-driven and high-risk FAQ claims require a natural authoritative link in the first visible answer paragraph.
- Status: aligned.

## FAQ Proof Map

{chr(10).join(faq_rows)}

{metric_pack}

## Citation Mode Mappings

- Workforce shares, apprenticeship figures, labor-demand estimates, survey results and the NAHB trend: `inline_required`; the linked source appears in the same paragraph or table row.
- OSHA PPE fit and sanitation statements and the rule effective date: `inline_required`; the OSHA page appears in the same paragraph.
- WIC Week timing: `inline_required`; the NAWIC page appears in the same FAQ paragraph.
- Jobsite, career-ladder, recruiting, retention and roadmap guidance: `proof_not_required` when framed as employer guidance.
- Simpro product sentences: `sidecar_only` as low-risk owned product language aligned with vault guidance.

{source_map}

## Search Intent and Format Decision

- Contract version: blog-strategy-contract/v1
- Primary query or prompt: women in construction
- Searcher task: Understand where women work in construction and how a contractor attracts, develops and keeps women to close skilled labor gaps.
- Intent class: informational
- Funnel stage: tofu
- SERP evidence artifact: {serp}
- SERP evidence SHA-256: {sha(ROOT / serp)}
- Dominant content type: General Article
- Selected content type: How-To Guide
- Observed SERP features: People also ask, Things to know
- Related-query/PAA artifact: {BRIEF}
- Format decision: documented_exception
- Exception reason: The page-one SERP is dominated by association homepages, news and statistics roundups classed as general articles, and none serves the contractor who has to recruit and keep women. The guide format answers the statistics intent with an early role table and adds the missing employer playbook.
- Status: ready

## Commercial Pillar and Anchor Decision

- Contract version: blog-strategy-contract/v1
- Article title: {TITLE}
- Article primary keyword: women in construction
- Article intent: informational
- Destination ID: simpro-us-homepage-field-service-management-software
- Commercial pillar URL: https://www.simprogroup.com/
- Planned anchor text: field service management software
- Planned H2 section: A 90-day roadmap for trade business owners
- Existing overlapping URLs checked: the legacy week URL, `/blog/women-in-skilled-trades-the-ultimate-guide`, `/blog/women-breaking-barriers-in-field-service`, `/blog/skilled-trades-shortage`, and `/blog/trades-labor-shortage`.
- Pillar-versus-blog intent difference: the homepage has product-proposition intent for trade contractors buying software, while this blog has informational employer intent about recruiting and retaining women.
- Cannibalization decision: different_intent
- Cannibalization note: the women-in-skilled-trades guide keeps job-seeker intent and is linked as a sibling; shortage terms stay with the shortage articles.
- Incoming-link candidates: `/blog/women-in-skilled-trades-the-ultimate-guide`, `/blog/women-breaking-barriers-in-field-service`, `/blog/skilled-trades-shortage`.
- Status: aligned

## Lifecycle Refresh Record

- Contract version: blog-strategy-contract/v1
- Last-updated date: {DATE}
- Volatility: high
- Next review date: 2026-12-24
- Review command: refresh BLS CPS annual averages, DOL apprenticeship data, ABC and AGC workforce figures, OSHA pages, Semrush, GSC and SERP evidence before the next publish-readiness pass; replace the role table when BLS publishes 2026 annual averages.
- GSC lane: available: GSC URL Inspection for the legacy week URL reported Crawled - currently not indexed with no 90-day query data (intake receipt 2026-08-18).
- GA4 lane: available: GA4 2026-02-20 to 2026-05-20 shows 378 sessions and 0 key events for the legacy week URL.
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
- Public metadata: `date_published: {DATE}`, `date_modified: {DATE}`, and `publisher: Simpro` are present in frontmatter. The legacy page's 2026-03-03 publication date is recorded here for provenance.
- Required schema notes: `BlogPosting`, `BreadcrumbList`, `ImageObject for the featured image or logo`, `Organization as publisher reference only, not a separate full schema block`, `FAQPage`, and `Question and Answer inside FAQPage`.
- VideoObject: omitted because no video is embedded.
- BOM requirement: record this no-author fallback and publisher-only decision in the final assembly BOM.
- Status: approved.

## Early Artifact and usability decision

- Artifact: a filled 11-row table of women's share of US workers by construction role from BLS CPS 2025, starting inside the first 300 body words.
- Additional artifacts: a five-stage career ladder checklist, an eight-row recruiting and retention checklist, and a three-phase 90-day roadmap table.
- ICP use: an owner or operations leader sees where the gap sits and which actions to take in which order.
- Mobile requirement: each table has a CMS module handoff that renders one labeled card per row with no hidden cells or horizontal scrolling.
- Status: present in the Markdown artifact; final rendered verification remains required.

## Image and Media Plan

- Original hero preserved: `https://www.simprogroup.com/images/d/4/2/3/7/d4237615057396aafdd817565b501188e1f8d21e-wic-week-blog-post.jpg` (live alt `Feature image for article - Women in Construction Week: Expanding the Workforce Powering the Trades`) stays as the hero source, renamed on upload to `women-in-construction-contractor-guide.webp` with new descriptive alt text.
- Original images planned: `women-in-construction-jobsite-technology.webp`, `women-in-construction-career-pathway.webp`, `women-in-construction-field-service-scheduling.webp` (1200 x 675 each), under `assets/images/blog/{SLUG}/`.
- Prompts and alt text: `research/image-prompts-{SLUG}-{DATE}.md`.
- Video: none.
- Status: aligned.

## Internal Link Decision

- Public-body Simpro links: skilled trades shortage; field service mobile app; field service scheduling; homepage field service management software (commercial pillar); top trades for women guide.
- Total: five internal links, inside the standard three-to-five range.
- Removed live links: `/blog/toolbox-tech-webinar`, `/blog/heroes-of-the-trade-dawn-lawrie` and `/blog/heroes-of-the-trade-vertac`, which only supported the removed quotes.
- Down-funnel destinations: `/features/field-service-mobile-app` and `/features/scheduling-software` with function-bearing anchors.
- Exact commercial anchor: `field service management software` links to `https://www.simprogroup.com/` in the A 90-day roadmap for trade business owners section.

## Release blockers and status

- Plan fulfillment, six role reviews, scrub, initial readiness scorecard, optimizer output, post-optimization scrub when bytes change, final Context Binding, final readiness, and assembly BOM: required.
- Current verdict: evidence package in progress; not publish-ready.
"""
    SIDECAR.write_text(text, encoding="utf-8", newline="\n")
    print(f"wrote {SIDECAR.relative_to(ROOT)} ({len(text.splitlines())} lines)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
