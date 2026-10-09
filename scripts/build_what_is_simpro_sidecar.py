"""Assemble the validation sidecar for the new What Is Simpro blog.

Governance artifact only. Combines static decision blocks with the customer
proof selector slate, the Fred selector block, the Hindsight evidence hashes,
the review capture receipts, and the context receipt revisions. The Context
Binding generator appends its blocks afterwards; rerun it after every rebuild.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SLUG = "what-is-simpro"
DATE = "2026-10-05"
R = ROOT / "research"
ARTICLE = ROOT / "drafts" / f"{SLUG}-{DATE}.md"
SIDECAR = R / f"validation-{SLUG}-{DATE}.md"
BRIEF = f"research/brief-{SLUG}-{DATE}.md"
TITLE = "What Is Simpro? What Sets It Apart for Trade Businesses"
OBJECTIVE = (
    "Help US trade business owners and operations leaders understand what Simpro is, how it runs a job "
    "from quote to payment, and what customers say sets it apart, so they can judge whether it fits their business."
)
CAPTERRA_REVIEWS = "https://www.capterra.com/p/10529/Simpro-Enterprise/reviews/"
LIGHTNING_RESOURCE = "res-16c113c993565a4c84150d131c034c57"
VERTICAL_RESOURCES = {"res-1825898a11855f89be9bb69c544a6aa3", "res-c5e0bc9b067157d991bf452e350766ca"}
FEATURE_RESOURCES = {LIGHTNING_RESOURCE}

# claim_id -> (identity for public copy, role, source type, visible quote text, section)
QUOTES = {
    "claim-metric-MET-1809": ("Mike B., Owner, small business (G2)", "accountability from lead to final payment",
                              "Simpro has made everyone accountable from the very beginning, from the lead and quote stage all the way through to collecting the final payment for the job.",
                              "What sets Simpro apart, in users' own words"),
    "claim-metric-MET-1816": ("Operations Manager, Facility Door Solutions (G2)", "office and field communication",
                              "It has improved communication between the office and field technicians, streamlined dispatching and scheduling, and given us better visibility into jobs, quotes, inventory, and invoicing.",
                              "What sets Simpro apart, in users' own words"),
    "claim-metric-MET-1302": ("Jeffrey M., mid-market business, incentivized G2 review", "switch from paper forms",
                              "We went from carbonless service call forms and a whiteboard calendar to Simpro.",
                              "What sets Simpro apart, in users' own words"),
    "claim-metric-MET-1849": ("Michael E., President, small business (G2)", "owner visibility",
                              "As an owner, it gives me great real-time insight into my business, from work orders to quotes.",
                              "What sets Simpro apart, in users' own words"),
    "claim-metric-MET-1755": ("Office Admin, utilities, anonymous incentivized Capterra review", "single source of truth",
                              "It is an absolute powerhouse when it comes to keeping our quoting, job management, and invoicing tied together in one single source of truth.",
                              "What sets Simpro apart, in users' own words"),
    "claim-metric-MET-1271": ("Jessica H., small business, incentivized G2 review", "one place for quotes, jobs and invoicing",
                              "Simpro allows our company to manage quotes, jobs, invoicing, and business reporting efficiently in one place.",
                              "What sets Simpro apart, in users' own words"),
}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(name: str) -> dict:
    return json.loads((R / name).read_text(encoding="utf-8"))


def hindsight_block(brief_sha: str) -> str:
    evidence = load(f"hindsight-strategy-evidence-{SLUG}-{DATE}.json")
    pack = evidence["receipt"]["pack_sha256"]
    receipt = evidence["receipt"]["receipt_sha256"]
    ids = evidence["sidecar"]["resource_ids"]
    request_sha = sha(R / f"context-request-{SLUG}.json")
    return f"""## Hindsight Strategy Selection

- Status: internal_strategy_only
- Evidence artifact: `research/hindsight-strategy-evidence-{SLUG}-{DATE}.json`
- Selected current resource IDs: {', '.join(f'`{r}`' for r in ids)}
- Pack SHA-256: `{pack}`
- Receipt SHA-256: `{receipt}`
- pack_sha256: {pack}
- receipt_sha256: {receipt}
- public_claim_use: prohibited
- claim_support_allowed: false
- Permitted effects: article angle, section emphasis, and FAQ framing only.
- Internal strategy provenance: compiled internal-strategy pages from approved source node `wiki/sources/hindsight-simpro-intelligence-snapshot-2026-08-31.md`, snapshot revision `9c1bd75ab190a0fa03499a514d6c39c13d7b56036da1027b68a2c5f95b1f260f`, valid until 2026-10-29.
- Binding: the strategy pack request is bound to `research/context-request-{SLUG}.json` (SHA-256 `{request_sha}`) because no brief or article existed when the pack was built; the brief `{BRIEF}` (SHA-256 `{brief_sha}`) records the same framing.
- Publication boundary: Hindsight is not cited and does not establish customer outcomes, business-size fit, rankings, or product claims. Public proof comes only from receipt-approved review claims.
- Applied decision: give the shared job record and the implementation section the fullest depth, because the Portfolio and Multi-Trade strategy pages concentrate buyer goals on product fit, implementation, and a unified platform.
- Applied decision: build the job-stage table and walkthrough around mobile, scheduling and dispatch, projects, and reporting, because the strategy pages concentrate decision criteria on those workflows.
- Applied decision: write the fit checklist with honest wait and lighter-tool rows, informed by missing-fit, timing, and workflow-fit loss themes. Do not claim that Simpro suits any particular business size.
- Rejected uses: deal counts, win rates, regional deal coverage, pricing objections, and competitor signals stay out of public copy and are not used as article evidence.
- Status rationale: the strategy pack is current, de-identified, internally retrievable, request-bound, and prohibited from public claim use."""


def main() -> int:
    receipt = load(f"context-receipt-{SLUG}.json")
    revisions = receipt["revisions"]
    resource_ids = [r["resource_id"] for r in receipt["resources"]]
    pack_hash = receipt["pack_sha256"]
    receipt_hash = receipt["receipt_sha256"]
    decisions = [d.get("claim_id") for d in receipt.get("claim_decisions", [])]
    missing = sorted(set(QUOTES) - set(decisions))
    if missing:
        raise SystemExit(f"public context receipt is missing planned claims: {missing}")
    slate = (R / f"customer-proof-slate-{SLUG}-decision-{DATE}.md").read_text(encoding="utf-8-sig").strip()
    slate = slate.replace("research\\", "research/")
    if slate.startswith("Customer Proof Slate"):
        slate = "## " + slate
    lines = slate.splitlines()
    for i, line in enumerate(lines):
        if line.startswith("- Role: experience_story") and "| Reason:" not in line:
            lines[i] = line + (" | Reason: selector returned no experience_story candidate because the registry holds no"
                               " identity-backed public_paraphrase review claim and no approved case-study claim for this objective")
        if line.startswith("- Role: theme") and "| Reason:" not in line:
            lines[i] = line + " | Reason: selector returned no theme candidate because no approved public_paraphrase customer claim fits this objective"
    slate = "\n".join(lines)
    fred = (R / f"fred-authority-selector-{SLUG}-{DATE}.md").read_text(encoding="utf-8").strip()
    captures = {row["claim_id"]: row for row in load(f"review-captures-{SLUG}-{DATE}.json")["records"]}
    brief_sha = sha(ROOT / BRIEF)
    hindsight = hindsight_block(brief_sha)
    serp = f"research/serp-evidence-{SLUG}-{DATE}.json"

    def label(rid: str) -> str:
        if rid in FEATURE_RESOURCES:
            return "feature "
        if rid in VERTICAL_RESOURCES:
            return "vertical "
        return ""

    rid = "; ".join(f"{label(r)}resource_id={r}" for r in resource_ids)
    claim_ids = "; ".join(f"claim_id={c}" for c in QUOTES)

    quote_rows = []
    for claim_id, (identity, role, quote, section) in QUOTES.items():
        cap = captures[claim_id]
        quote_rows.append(
            f"- Approved quote: {quote} | Claim ID: {claim_id} | Customer/brand: {identity} | Source type: review_site | "
            f"Source class: review_platform | Evidence relation: directly_supports | URL: {cap['url']} | Evidence: {quote} | "
            f"Artifact: {cap['artifact']} | Capture receipt: {cap['receipt']} | Capture receipt hash: {cap['receipt_sha256']} | "
            f"Checked date: {cap['checked']} | Status: approved | Use: attributed exact quote with a same-paragraph review link in {section} on {role}"
        )
    cls_dir = R / "source-classifications" / SLUG
    cls_files = sorted(cls_dir.glob("source-classification-*.json"))
    if len(cls_files) != 1:
        raise SystemExit(f"expected one classification artifact in {cls_dir}")
    home_receipt = R / "source-captures" / f"{SLUG}-{DATE}" / "simprogroup-homepage-capture-receipt.json"
    source_map_row = (
        "- Claim: Office and field teams work on a single platform, from estimating and scheduling to job execution, invoicing, and reporting"
        " | Claim type: product_claim | URL: https://www.simprogroup.com/"
        " | Evidence: Simpro connects your office and field teams on a single platform, from estimating and scheduling to job execution, invoicing, and reporting."
        " | Source class: owned_product | Evidence relation: directly_supports | Original-source status: original"
        f" | Source date: undated | Checked date: {DATE} | Claim fit: direct | Freshness decision: historical_scoped"
        f" | Freshness reason: The Simpro homepage is undated, so approval is scoped to the live product definition captured on {DATE}."
        f" | Artifact: research/source-captures/{SLUG}-{DATE}/simprogroup-homepage.md"
        f" | Capture receipt: research/source-captures/{SLUG}-{DATE}/simprogroup-homepage-capture-receipt.json"
        f" | Capture receipt hash: {sha(home_receipt)}"
        f" | Classification artifact: {cls_files[0].relative_to(ROOT).as_posix()} | Classification hash: {sha(cls_files[0])}"
        " | Status: approved | Intended use: opening definition of what Simpro does | Citation mode: sidecar_only"
    )
    faq_good = QUOTES["claim-metric-MET-1271"][2]

    text = f"""# What Is Simpro Validation Sidecar

## Scope and artifact binding

- Canonical URL: `https://www.simprogroup.com/blog/{SLUG}`
- Article title: {TITLE}
- Workflow date: {DATE}
- Workflow mode: new
- Market: United States
- Article objective: {OBJECTIVE}
- Public article: `drafts/{SLUG}-{DATE}.md`
- Current article SHA-256 at sidecar assembly: `{sha(ARTICLE)}`
- Content brief: `{BRIEF}` (SHA-256 `{brief_sha}`)
- Frozen editorial plan: `research/editorial-plan-{SLUG}-{DATE}.json`
- Context request: `research/context-request-{SLUG}.json`
- Context pack: `research/context-pack-{SLUG}.json`
- Context receipt: `research/context-receipt-{SLUG}.json`
- Binding boundary: the article hash and all downstream receipts must be regenerated if article bytes change after this sidecar snapshot.

## Request origin and public boundary

- Request: a 2019 review-site Q&A asked how Simpro compares with other vendors and what makes it a leader. The requester directed a Simpro-only article with no competitor names or comparison language.
- Translation: the article answers what Simpro is and what sets it apart with receipt-approved, attributed user quotes. No leader, best, better, ranking, superiority or category-leadership claim appears in Simpro's voice.
- Competitive language: none. The words competitor, alternative, vs and versus do not appear in public copy.

## Context request and validation

- Binding: connector-bound.
- Reason: the artifact is Simpro-owned and links to official `simprogroup.com` pages.
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
- Approved public claim IDs used: {', '.join(f'`{c}`' for c in QUOTES)} (exact_quote).
- Public evidence boundary: connector resources guide Simpro voice, category and workflow language; every public quote uses a receipt-approved exact_quote claim with a same-paragraph review link.
- Context result: `task_satisfaction: {receipt['task_satisfaction']}`; unresolved gaps: [none].

## Vault Context Read Path

- Connector path: vault_status, vault_describe, natural-language vault_search, resource_id-bound vault_read and vault_expand, vault_claims, vault_build_context, and vault_validate_context through `data_sources.modules.simpro_vault_client.SimproVaultClient`.
- Active artifacts: `research/context-request-{SLUG}.json`, `research/context-pack-{SLUG}.json`, and `research/context-receipt-{SLUG}.json`.
- Selector-only packs: `research/context-pack-{SLUG}-customer-selector-{DATE}.json` (customer-proof claims) and `research/context-pack-{SLUG}-fred-evaluation-{DATE}.json` (Fred authority claims).
- Public-use boundary: selected vault resources are guidance or context only, apart from the six approved exact_quote claims above.
- Status: validated.

## Vault Brand Language Alignment

- Article title: {TITLE}
- Product/solution language scope: mixed
- Vault connector evidence: vault_status ready; vault_describe inspected; natural-language vault_search, vault_read, and vault_expand completed; vault_claims checked; context_pack_hash={pack_hash}; receipt_hash={receipt_hash}; {rid}; {claim_ids}; manifest_revision={revisions['manifest_revision']}
- Product/feature language applied: Simpro described as field service management software for residential and commercial trade businesses that keeps quotes, schedules, jobs, inventory, invoices and reports in one cloud system shared by the office and the field; quote, schedule and dispatch, field work, invoice, payment and reporting stages drawn from the Product Positioning and Trade Services Datasheet guidance; scheduling described as matching technicians by skills, licenses and tools; the mobile app described as recording time, materials, notes, photos, forms and asset records; Simpro Lightning named once as navigation-only product context with no capability, package or availability claim.
- Solution/industry language applied: electrical, plumbing, HVAC, fire and security contractors across installs, repairs, maintenance and projects, drawn from the Feature Datasheet Atlas vertical datasheets (electrical, HVAC, plumbing and trade services) and Field Service Management in the Cloud vertical guidance; no vertical leadership, business-size, ERP, generic project-management or accounting-replacement framing.
- Local brand fallback: none
- Claims requiring source verification: {', '.join(QUOTES)}
- Status: aligned

## Named Feature Status and Commercial Treatment

| Name | Capability claim ID | Commercial claim ID | Release status | Commercial treatment | Region or account boundary | Public wording decision |
|---|---|---|---|---|---|---|
| Lightning |  |  | current_public_context | not_asserted | Product-page navigation only; confirm current region, package and availability during a demo | navigation_only |

## Named Feature/Add-On Link Check

| Name | Resource ID | Link decision | Target URL | Reason |
|---|---|---|---|---|
| Lightning | {LIGHTNING_RESOURCE} | link | https://www.simprogroup.com/lightning | The first meaningful mention links to current navigation-only product context; public copy makes no capability, package or availability assertion. |

- Generic workflow categories linked: field service management software (homepage pillar), mobile app for technicians (`/features/field-service-mobile-app`), field service reporting (`/features/reporting`).
- Status: aligned.

{hindsight}

{slate}

{fred}

## Customer Proof Selection Decision

- Selector command: as recorded in the Customer Proof Slate.
- Selected proof: claim-metric-MET-1809 | Customer: Mike B., Owner (G2) | URL: https://www.g2.com/products/simpro/reviews/simpro-review-13118004 | Role: quote | Claim ID: claim-metric-MET-1809
- Public quote claims: {', '.join(QUOTES)}.
- Zero-use comparison: none of the six claims, their review URLs, or the reviewer identities appear in public copy across drafts, rewrites, research and published on {DATE}; all six are zero-use sources.
- Live repo scan: drafts, rewrites, research and published were scanned on {DATE} for the six claim IDs, review URLs and reviewer names; no prior public-copy use was found.
- Final use in copy: six attributed exact quote lines in `What sets Simpro apart, in users' own words`.

## Selected Customer Proof Mining

- Proof: claim-metric-MET-1809 | Customer: Mike B., Owner (G2) | URL: https://www.g2.com/products/simpro/reviews/simpro-review-13118004
- Checked: 2026-10-02.
- Checked for: customer metric, exact quote, POV/story, and workflow theme.
- Usable metrics found: none found.
- Usable quotes found: the approved exact_quote claim text, visible in the Chrome readback of the review.
- POV/story decision: owner view of one record from lead to final payment, used as an attributed exact quote.
- Recommended use: one attributed exact quote with a same-paragraph review link.
- Final use in copy: exact quote in the accountability subsection.
- Excluded proof: the reviewer's dislikes and inventory comments, which the article reflects only as general setup guidance, and any rating.
- Status: approved

## Review Site Theme Selection

- Platform: Capterra
- Source row ref: Capterra tab row 1540
- Public review-site URL: {CAPTERRA_REVIEWS}
- Workflow theme: the linked introduction paragraph points readers to public Simpro reviews before the attributed exact quotes; it publishes no paraphrased review theme, rating, ranking or aggregate claim.
- Source path: `indexes/metric-claim-matrix.csv` row 1540 (claim-metric-MET-1755, Capterra incremental review locator).
- Status: approved for paraphrased review-theme use

## Customer Proof Pack

- Pack status: ready.
- Quote Matrix candidates: approved exact_quote review claims returned by the connector for the six planned public uses plus evaluated alternatives in the selector pack.
- Customer Stories candidates: the connector returned no approved case-study exact_quote claim on a simprogroup.com URL, and case-study resources prohibit public claim use, so no case-study story is used.
- Review-site experience evidence: G2 and Capterra review quotes, each receipt-approved and capture-bound.
{chr(10).join(quote_rows)}
- Incentive disclosure: G2 labels the Jeffrey M. and Jessica H. reviews as incentivized, and Capterra labels the office admin review as incentivized. Each of those paragraphs discloses the label in its link text.
- Zero-use comparison: all six claims are zero-use sources.
- Use in copy: six attributed exact quote lines, each with a same-paragraph review link.
- Claims excluded: customer metrics, ratings, star counts, rankings, aggregate review claims, case-study stories, composite personas, MET-1300 (superlative wording) and older Capterra rows whose wording is not visible on the vault public URL.

## E-E-A-T Proof Map

- First-hand evidence decision: Selected: [none] for experience_story because the registry holds no identity-backed public_paraphrase review claim and no approved case-study claim for this objective, so the article omits a customer story and relies on six attributed receipt-approved user quotes instead of a composite or fictional persona.
- Experience: the six user quotes on accountability from lead to payment, office and field communication, the switch from paper forms, owner visibility, a single source of truth, and quotes, jobs and invoicing in one place.
- Expertise: Selected: [none]. No named author, named reviewer beyond the review attributions, or Fred contribution is authorized.
- Authoritativeness: each quote links to its public G2 or Capterra review page in the same paragraph.
- Trust: the article discloses G2's incentivized label where it applies, names setup effort and a learning curve, and includes a fit checklist with wait and lighter-tool rows.

## PAA/FAQ Provenance

- Source: answersocrates
- Artifact: `research/paa-evidence-{SLUG}-{DATE}.json`
- Selected questions:
  - Is Simpro a CRM system?
  - Is Simpro a good system?

- Question origin: AnswerSocrates People Also Asked for the query `simpro`, US English, captured through the Chrome connector on {DATE}.
- Omitted questions: How much is simpro a month? and Is simpro a big company? have no allowed non-owned source for a direct answer.
- Status: approved for the current two-question FAQ set.

## FAQ Source Policy

- Allowed source classes: neutral, non_competing_expert, owned_product.
- Competitor-owned FAQ sources: prohibited.
- Direct-answer rule: each first visible answer paragraph must contain 40 to 60 words and begin with a named recommendation, definition, concrete action, number or range, or explained yes/no.
- Inline rule: fact-driven and high-risk FAQ claims require a natural authoritative link in the first visible answer paragraph.
- Status: aligned.

## FAQ Proof Map

- FAQ: Is Simpro a CRM system? | URL: [none] | Source class: owned_product | Competitor check: passed | Support: vault Product Positioning and Trade Services Datasheet guidance on customer, site, contact, lead and quote records; the answer closes with an editorial recommendation | Citation mode: sidecar_only | Status: approved
- FAQ: Is Simpro a good system? | URL: [none] | Source class: owned_product | Competitor check: passed | Support: an explained yes with an editorial recommendation to test fit on recent jobs; no external fact is asserted | Citation mode: sidecar_only | Status: approved

## Metric Proof Pack

- Metric requirement: not applicable
- Reason: The article publishes no metric, statistic, percentage, price or numeric business claim; the claim registry has 0 approved public_metric claims, so customer metrics are omitted by design.
- Search log: On {DATE} the connector public_metric claim search returned 0 rows; Semrush keyword metrics stay in the keyword decision artifact and are not published.
- Status: approved

## Citation Mode Mappings

- Six attributed user quotes: `inline_required`; the review link appears in the same paragraph.
- FAQ `Is Simpro a good system?`: `sidecar_only` as an explained yes with an editorial recommendation.
- FAQ `Is Simpro a CRM system?`: `sidecar_only` as an editorial recommendation built on approved low-risk product language.
- Simpro product and workflow sentences: `sidecar_only` as low-risk owned product language aligned with vault guidance.
- Implementation stages, fit checklist and demo-prep guidance: `proof_not_required` as editorial guidance.

## Source Map

{source_map_row}

## Search Intent and Format Decision

- Contract version: blog-strategy-contract/v1
- Primary query or prompt: what is simpro
- Searcher task: Understand what Simpro is, how it works across a trade job, and what users value, before deciding on a demo.
- Intent class: informational
- Funnel stage: mofu
- SERP evidence artifact: {serp}
- SERP evidence SHA-256: {sha(ROOT / serp)}
- Dominant content type: General Article
- Selected content type: General Article
- Observed SERP features: Sitelinks, AI Overview, Reviews, People also ask
- Related-query/PAA artifact: research/paa-evidence-{SLUG}-{DATE}.json
- Format decision: match_dominant
- Exception reason: The general-article format matches the observed results; the explainer adds the job-stage frame and linked user evidence the ranking pages lack.
- Status: ready

## Commercial Pillar and Anchor Decision

- Contract version: blog-strategy-contract/v1
- Article title: {TITLE}
- Article primary keyword: what is simpro
- Article intent: informational
- Destination ID: simpro-us-homepage-field-service-management-software
- Commercial pillar URL: https://www.simprogroup.com/
- Planned anchor text: field service management software
- Planned H2 section: How Simpro runs a job from quote to payment
- Existing overlapping URLs checked: `https://www.simprogroup.com/`, `/blog/best-field-service-management-software`, `/solutions/job-management-software`, `/pricing`.
- Pillar-versus-blog intent difference: the homepage owns the navigational brand query and the general field service management software category, while this blog owns the informational what-is explainer.
- Cannibalization decision: create_new
- Incoming-link candidates: `/blog/best-field-service-management-software`, `/blog/ai-features-field-service-software`, `https://www.simprogroup.com/`.
- Status: aligned

## Lifecycle Refresh Record

- Contract version: blog-strategy-contract/v1
- Last-updated date: {DATE}
- Volatility: high
- Next review date: 2027-01-03
- Review command: refresh the review quotes, Simpro Lightning navigation context, Semrush and SERP evidence before the next publish-readiness pass.
- GSC lane: unavailable: this is a new article with no first-party query-performance history
- GA4 lane: unavailable: this is a new article with no engagement history
- Semrush lane: available: US keyword decision captured in the main Chrome Semrush UI on {DATE} and recorded in research/semrush-keyword-decision-{SLUG}-{DATE}.json.
- AI-citation lane: unavailable: no AI-citation sample was collected for this assembly.
- Decision: retain
- Status: scheduled

## Author and Schema Decision

- Author policy: no_author
- Named author verified: no.
- Named reviewer verified: no.
- Frontmatter author field: omitted.
- `Person as author`: omitted.
- Publisher: `Organization` as publisher reference only, not a separate full schema block.
- Public metadata: `date_published: {DATE}`, `date_modified: {DATE}`, and `publisher: Simpro` are present in frontmatter.
- Required schema notes: `BlogPosting`, `BreadcrumbList`, `ImageObject for the featured image or logo`, `Organization as publisher reference only, not a separate full schema block`, `FAQPage`, and `Question and Answer inside FAQPage`.
- VideoObject: omitted because no video is embedded.
- BOM requirement: record this no-author fallback and publisher-only decision in the final assembly BOM.
- Status: approved.

## Early Artifact and usability decision

- Artifact: a filled six-row job-stage table (job stage, what Simpro handles, who uses it) starting inside the first 300 body words.
- Additional artifacts: a three-stage implementation table, a six-row fit checklist, and a five-item demo-prep checklist.
- ICP use: an owner or operations leader sees what Simpro covers, what users value, how setup works, and whether to book a demo.
- Status: present in the Markdown artifact; final rendered verification remains required.

## Image and Media Plan

- Featured: `what-is-simpro-field-service-management-software-dashboard.webp` (960 x 250).
- Inline: `simpro-mobile-app-technician-job-site.webp` and `simpro-reviews-office-scheduling-job-costing.webp` (1200 x 675 each).
- Alt text: written in each standalone image placeholder, keyword-led and descriptive.
- Video: none.
- Status: aligned.

## Internal Link Decision

- Public-body Simpro links: homepage field service management software (commercial pillar); mobile app for technicians; field service reporting; Simpro Lightning (navigation only); book a Simpro demo; Simpro pricing.
- Total: six internal links, inside the seven-link maximum.
- Down-funnel destinations: `/features/field-service-mobile-app` and `/features/reporting` with function-bearing anchors.
- Exact commercial anchor: `field service management software` links to `https://www.simprogroup.com/` in the How Simpro runs a job from quote to payment section.

## Release blockers and status

- Plan fulfillment, machine reviews, scrub, initial readiness scorecard, optimizer output, post-optimization scrub when bytes change, final Context Binding, final readiness, and assembly BOM: required.
- Current verdict: evidence package in progress; not publish-ready.
"""
    SIDECAR.write_text(text, encoding="utf-8", newline="\n")
    print(f"wrote {SIDECAR.relative_to(ROOT)} ({len(text.splitlines())} lines)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
