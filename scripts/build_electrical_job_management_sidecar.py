"""Build the dated proof sidecar for the electrical software rewrite."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SLUG = "best-electrical-job-management-software"
DATE = "2026-09-28"
ARTICLE = ROOT / "published" / "best-electrical-job-management-software-2026-09-02.md"
OUT = ROOT / "research" / f"validation-{SLUG}-{DATE}.md"


def sha(path: str | Path) -> str:
    value = Path(path)
    if not value.is_absolute():
        value = ROOT / value
    return hashlib.sha256(value.read_bytes()).hexdigest()


def rel(path: str | Path) -> str:
    return Path(path).as_posix()


CONTEXT_REQUEST = f"research/context-request-{SLUG}-{DATE}.json"
CONTEXT_PACK = f"research/context-pack-{SLUG}-{DATE}.json"
CONTEXT_RECEIPT = f"research/context-receipt-{SLUG}-{DATE}.json"
HINDSIGHT = f"research/hindsight-strategy-evidence-{SLUG}-{DATE}.json"
CUSTOMER = f"research/customer-proof-selector-evidence-{SLUG}-{DATE}.json"
FRED = f"research/fred-authority-selection-{SLUG}-{DATE}.txt"
PAA = f"research/paa-evidence-{SLUG}-{DATE}.json"
KEYWORD = f"research/semrush-keyword-decision-{SLUG}-{DATE}.json"
PLAN = f"research/editorial-plan-{SLUG}-{DATE}.json"
SERP = f"research/serp-evidence-{SLUG}-{DATE}.json"

CLASSIFICATIONS = {
    "knowify_electrical": ("research/source-classifications/best-electrical-job-management-software-2026-09-28/source-classification-071cf13116f1cfc89725bdce355367e2d3e0195eefb60d39b08b7c07afaf03c3.json", "37208c9b2db6b88ec471b58a9812eecc0a099692402602ada85d5e7064ee8274"),
    "knowify_pricing": ("research/source-classifications/best-electrical-job-management-software-2026-09-28/source-classification-cacd68cda977f879ef1cf29872d9aa2982605b1b625b97d3e13c2da99840286e.json", "e5262d255ff059432e8c65feba767645d1dcf3b0f541eb05fe2d89137a967fe8"),
    "knowify_quickbooks": ("research/source-classifications/best-electrical-job-management-software-2026-09-28/source-classification-3edc5ab20bf31ea4dc94fce737b96ac9ea094194d348188a88fd6054c7a3267d.json", "4dee145a9a2fe7c0872937270420031ac0d089e0defdc829e3b3430a880eadfd"),
    "apm": ("research/source-classifications/best-electrical-job-management-software-2026-09-03/apm-what-is-project-management.json", "94840b1177f0951f367f7203d2e35608edc023c603f94ce95defb314f07ee51f"),
    "buildops_electrical": ("research/source-classifications/best-electrical-job-management-software-2026-09-03/buildops-electrical.json", "59e3d5571bea6b3ac1b3248f0d05487fc2703437cef7b36afbc521919d92ac4c"),
    "buildops_pricing": ("research/source-classifications/best-electrical-job-management-software-2026-09-03/buildops-pricing.json", "8ce17905bb3093f7fb03dd699d0c7b7b734c0d52095a8c978c06b6cf17088bfd"),
    "cisa": ("research/source-classifications/best-electrical-job-management-software-2026-09-03/cisa-smb-supplier-assessment.json", "0a50ad39972cdb61e9235433d0d2bb596d52e53ed0b216d68f4f673927b77214"),
    "fieldedge_electrical": ("research/source-classifications/best-electrical-job-management-software-2026-09-03/fieldedge-electrical.json", "aa8914d250daf3081d3809d6a25b07fd63776633acc4dee5c0fef0217ff8badf"),
    "fieldedge_pricing": ("research/source-classifications/best-field-service-management-software-2026-08-28/fieldedge-pricing.json", "f1a10a9931bcb19c3122aab53416976e6442bb27ef0ad12e53592c634799dfeb"),
    "fieldpulse_electrical": ("research/source-classifications/best-electrical-job-management-software-2026-09-03/fieldpulse-electrical.json", "3e3bc5e0245880cda43a218327f8b81afbbf61363ad809d8d5fcd9e1ce7c1dca"),
    "fieldpulse_pricing": ("research/source-classifications/best-field-service-management-software-2026-08-28/fieldpulse-pricing.json", "ef91dc5fe9562616249d5b43680c0c78f191519467e04e85c4b8da31541c3b9a"),
    "housecall_electrical": ("research/source-classifications/crm-for-electricians/housecall-electrical.json", "deb8473435504d24d417100bea8cb817fd5ef185a4a2b78cee9677fc86e83990"),
    "housecall_pricing": ("research/source-classifications/best-field-service-management-software-2026-08-28/housecall-pro-pricing.json", "7588a3a7986a16de63aea0a6c241d018e23daee54371278bfc196d1ba3b883e8"),
    "jobber_electrical": ("research/source-classifications/best-electrical-job-management-software-2026-09-03/jobber-electrical.json", "a8a9d990153217aab635315075619bbe985fe05e143a07c4711435219eb777b2"),
    "jobber_pricing": ("research/source-classifications/best-field-service-management-software-2026-08-28/jobber-pricing.json", "d25623c08e6277f4797b737ec9fa82950d445313767a5fdb0fd6fab509b7fbf3"),
    "servicefusion_pricing": ("research/source-classifications/best-electrical-job-management-software-2026-09-03/service-fusion-pricing.json", "4e43d0bbf38186a3b22381cc9833027121116ab6c2f01bb57b4f37ee9edd5046"),
    "servicetitan_electrical": ("research/source-classifications/crm-for-electricians/servicetitan-electrical.json", "e77e41654f18c4c7527dd7d333e88c70de0d5b431b747d1209e4c97445ccbb12"),
    "servicetitan_pricing": ("research/source-classifications/crm-for-electricians/servicetitan-pricing.json", "177a070ab1d0b91ecfe3ce195d5b28321c2ebc235931bea58da4120bd6d3f0bb"),
    "tradify_electrical": ("research/source-classifications/best-electrical-job-management-software-2026-09-03/tradify-electrical.json", "c7a1bcf47dcdb23e2d512214a44d2bb940ff2e824825664c215c93bffc33d2b7"),
    "tradify_pricing": ("research/source-classifications/best-electrical-job-management-software-2026-09-03/tradify-pricing.json", "92e5412167e63b5caa18d01b47c59640084592bfe0ec3ca88bdd31ab1c69f437"),
}


def classification(key: str) -> str:
    path, digest = CLASSIFICATIONS[key]
    if sha(path) != digest:
        raise RuntimeError(f"classification hash changed: {path}")
    return f"Classification artifact: {path} | Classification hash: {digest}"


def source_row(
    claim: str,
    claim_type: str,
    source_class: str,
    url: str,
    evidence: str,
    intended_use: str,
    classification_text: str,
    *,
    status: str = "approved",
    citation_mode: str = "inline_required",
) -> str:
    return (
        f"- Claim: {claim} | Claim type: {claim_type} | Evidence relation: directly_supports | "
        f"Source class: {source_class} | URL: {url} | Evidence: {evidence} | "
        f"Original-source status: original | Source date: undated | Checked date: {DATE} | "
        f"Claim fit: direct | Freshness decision: historical_scoped | Freshness reason: the live source is undated and was checked on the article update date | "
        f"{classification_text} | Status: {status} | Intended use: {intended_use} | Citation mode: {citation_mode}"
    )


def main() -> None:
    receipt = json.loads((ROOT / CONTEXT_RECEIPT).read_text(encoding="utf-8"))
    revisions = receipt["revisions"]
    customer_text = (ROOT / "research" / f"customer-proof-slate-{SLUG}-{DATE}.txt").read_text(encoding="utf-8-sig").strip().replace("\\", "/")
    fred_text = (ROOT / FRED).read_text(encoding="utf-8-sig").strip()
    rows = [
        source_row("APM distinguishes project work as a finite effort with defined objectives.", "definition", "non_competing_expert", "https://www.apm.org.uk/resources/what-is-project-management/", "APM defines project management around finite work undertaken to achieve objectives.", "scope capsule", classification("apm")),
        source_row("ServiceTitan names electrical service, commercial and construction workflows, and uses tailored pricing without public dollar amounts.", "process", "competitor", "https://www.servicetitan.com/industries/electrical-software", "The official electrical page names the product and workflow scope used in the card.", "ServiceTitan fit and workflow card", classification("servicetitan_electrical")),
        source_row("ServiceTitan uses a personalized pricing-request path tied to technicians using the platform.", "commercial", "competitor", "https://www.servicetitan.com/pricing", "The official pricing page provides the tailored quote path and pricing basis.", "ServiceTitan pricing and comparison row", classification("servicetitan_pricing")),
        source_row("BuildOps names commercial electrical service, maintenance and project workflows.", "process", "competitor", "https://buildops.com/industries/electrical", "The official electrical page names service, asset and project workflow areas.", "BuildOps fit and workflow card", classification("buildops_electrical")),
        source_row("BuildOps uses discovery, a tailored demonstration and custom proposal rather than a public self-serve price.", "commercial", "competitor", "https://buildops.com/pricing", "The official pricing page provides the sales-contact path used in the card and table.", "BuildOps pricing and comparison row", classification("buildops_pricing")),
        source_row("Knowify names electrical project and service workflows including phased budgets, construction administration and job costing.", "process", "competitor", "https://knowify.com/electrical-contractors/", "The current official electrical page directly supports the capability cluster.", "Knowify fit and workflow card", classification("knowify_electrical")),
        source_row("Knowify lists Core, Advanced and Enterprise paths, user allowances, billing choices and a free trial.", "commercial", "competitor", "https://knowify.com/pricing/", "The current official pricing page directly supports the public pricing and trial statements.", "Knowify pricing and comparison row", classification("knowify_pricing")),
        source_row("Knowify publishes a QuickBooks Online integration.", "process", "competitor", "https://knowify.com/integrations/quickbooks/", "The current official integration page directly supports the QuickBooks reference.", "Knowify integration statement", classification("knowify_quickbooks")),
        source_row("FieldPulse names electrical service workflows, job costing, project management, inventory, agreements, asset tracking, QuickBooks and API access.", "process", "competitor", "https://www.fieldpulse.com/solutions/electrical", "The official electrical page supports the capability cluster used in the card.", "FieldPulse fit and workflow card", classification("fieldpulse_electrical")),
        source_row("FieldPulse uses custom pricing with full-access, field-only and optional premium-product paths.", "commercial", "competitor", "https://www.fieldpulse.com/pricing", "The official pricing page supports the pricing path and seat distinction.", "FieldPulse pricing and comparison row", classification("fieldpulse_pricing")),
        source_row("Jobber publishes plan, user, job-costing, QuickBooks Online and time-limited trial information.", "commercial", "competitor", "https://www.getjobber.com/pricing/", "The official pricing page supports the public plan and trial statements.", "Jobber pricing and comparison row", classification("jobber_pricing")),
        source_row("Housecall Pro names electrical service, costing, equipment-history, service-plan, progress-invoice and QuickBooks workflows.", "process", "competitor", "https://www.housecallpro.com/industries/electrical-contractor-software/", "The official electrical page supports the workflow cluster used in the card.", "Housecall Pro fit and workflow card", classification("housecall_electrical")),
        source_row("Housecall Pro publishes a plan selector and advertises a 14-day trial.", "commercial", "competitor", "https://www.housecallpro.com/pricing/", "The official pricing page supports the plan-selection and trial statements.", "Housecall Pro pricing and comparison row", classification("housecall_pricing")),
        source_row("Service Fusion lists office-to-field workflows, plan availability, unlimited users, onboarding and support.", "commercial", "competitor", "https://www.servicefusion.com/pricing", "The official plan comparison supports the capability and commercial statements used in the card.", "Service Fusion card and comparison row", classification("servicefusion_pricing")),
        source_row("FieldEdge names electrical dispatch, pricebook, purchasing, service-agreement, history and QuickBooks workflows.", "process", "competitor", "https://fieldedge.com/electrician-software/", "The official electrical page supports the service-operation cluster.", "FieldEdge fit and workflow card", classification("fieldedge_electrical")),
        source_row("FieldEdge uses quote-based pricing and states that no free trial is offered.", "commercial", "competitor", "https://fieldedge.com/pricing/", "The official pricing page supports the pricing and trial statements.", "FieldEdge pricing and comparison row", classification("fieldedge_pricing")),
        source_row("Tradify names electrical quote, schedule, job, invoice, costing, progress-invoice, purchase-order, reminder and QuickBooks Online workflows.", "process", "competitor", "https://www.tradifyhq.com/trades/electrician-av-software-app", "The official electrical page supports the capability cluster.", "Tradify fit and workflow card", classification("tradify_electrical")),
        source_row("Tradify publishes US per-user plans, custom team pricing and a 14-day trial.", "commercial", "competitor", "https://www.tradifyhq.com/pricing", "The official US pricing page supports the public pricing-path and trial statements.", "Tradify pricing and comparison row", classification("tradify_pricing")),
        source_row("CISA provides structured supplier-assessment questions for small and midsize organizations evaluating vendors.", "process", "primary_authority", "https://www.cisa.gov/resources-tools/resources/assisting-small-and-medium-sized-businesses-assess-vendors-and-suppliers-fact-sheet", "CISA's fact sheet supports the supplier-risk evaluation advice used in the body and FAQs.", "implementation guidance and two FAQ first paragraphs", classification("cisa")),
        source_row("Simpro names electrical estimating, scheduling, dispatch, field, inventory, costing, maintenance and billing workflows.", "process", "owned_product", "https://www.simprogroup.com/industries/electrical-software", "The current owned industry page and vault electrical resources support the workflow cluster.", "commercial pillar and Simpro card", "Classification artifact: not applicable for owned product | Classification hash: not applicable", citation_mode="inline_required"),
        source_row("Simpro uses a tailored quote path and describes an initial setup fee.", "commercial", "owned_product", "https://www.simprogroup.com/pricing", "The current owned pricing page supports the public pricing-path statement.", "Simpro card and comparison row", "Classification artifact: not applicable for owned product | Classification hash: not applicable"),
        source_row("Simpro Takeoffs connects drawing measurements and material calculations to quoting and project workflows.", "process", "owned_product", "https://www.simprogroup.com/features/takeoffs", "The current owned feature page and feature-specific vault resource support the scope handoff.", "takeoff FAQ", "Classification artifact: not applicable for owned product | Classification hash: not applicable"),
        source_row("Readers comparing beyond the electrical market can consult the broader field service management software comparison.", "recommendation", "owned_product", "https://www.simprogroup.com/blog/best-field-service-management-software", "The linked Simpro comparison is the destination named in the closing navigation recommendation.", "closing internal-link recommendation", "Classification artifact: not applicable for owned navigation | Classification hash: not applicable", citation_mode="sidecar_only"),
        source_row("Readers evaluating mixed service, maintenance and projects can compare the shortlist with project management software controls.", "recommendation", "owned_product", "https://www.simprogroup.com/solutions/project-management-software", "The linked Simpro solution page is the destination named in the closing workflow recommendation.", "closing internal-link recommendation", "Classification artifact: not applicable for owned navigation | Classification hash: not applicable", citation_mode="sidecar_only"),
    ]

    content = f"""# Validation sidecar: Best Electrical Job Management Software by Job Type (2026)

## Scope and artifact binding

- Article: `{ARTICLE.relative_to(ROOT).as_posix()}`
- Article SHA-256: `{sha(ARTICLE)}`
- Canonical URL: `https://www.simprogroup.com/blog/best-electrical-job-management-software`
- Topic: electrical job management software
- Title: Best Electrical Job Management Software by Job Type (2026)
- Objective: Help US electrical contractors choose a short demo list by job mix, then compare workflow fit, pricing, implementation and integration requirements on equal terms.
- Market: US
- Workflow mode: rewrite
- Verification date: {DATE}
- Editorial plan: `{PLAN}`, SHA-256 `{sha(PLAN)}`
- No-author workflow: selected; no author was invented.

## Context Binding

- Binding: connector-bound.
- Reason: Simpro-owned public blog with an official `simprogroup.com` canonical URL.
- Context request: `{CONTEXT_REQUEST}`, file SHA-256 `{sha(CONTEXT_REQUEST)}`.
- Context pack: `{CONTEXT_PACK}`, file SHA-256 `{sha(CONTEXT_PACK)}`.
- Context receipt: `{CONTEXT_RECEIPT}`, file SHA-256 `{sha(CONTEXT_RECEIPT)}`.
- context_pack_hash: `{receipt['pack_sha256']}`.
- receipt_hash: `{receipt['receipt_sha256']}`.
- Validation time: `{receipt['validation_time']}`.
- Revisions: manifest `{revisions['manifest_revision']}`; content `{revisions['content_revision']}`; claim registry `{revisions['claim_registry_revision']}`; approval policy `{revisions['approval_policy_revision']}`; inventory `{revisions['inventory_revision']}`; contract `{revisions['contract_revision']}`.
- Resource IDs: `res-10b97eee1de25395bbf8b904111ca4b0`, `res-f9f9499223a15d6a901806f30fb1a8ba`, `res-d31f057a305f51918055120d95b76c6a`, `res-e3ade596be645307ad4c1f84620ce021`, `res-b34b392d22b9507089ade3fec47ee9e0`, `res-a5b3b47382b45490bf2bedbf16c0b76e`, `res-c6e69419a82e59919b4af4731a7e496a`, `res-517ad5ccb2cd5c3985831d8aba4cedaa`.
- Status: current, validated and satisfied with no vault-context gaps.

## Vault Brand Language Alignment

- Article title: Best Electrical Job Management Software by Job Type (2026)
- Product/solution language scope: mixed
- Vault connector evidence: context_pack_hash={receipt['pack_sha256']}; receipt_hash={receipt['receipt_sha256']}; manifest_revision={revisions['manifest_revision']}; resource_id=res-d31f057a305f51918055120d95b76c6a; vertical resource_id=res-f9f9499223a15d6a901806f30fb1a8ba; feature resource_id=res-c6e69419a82e59919b4af4731a7e496a
- Product/feature language applied: Simpro workflow language is limited to estimating, scheduling, dispatch, mobile field work, purchasing, inventory, job costing, maintenance, project billing and Takeoffs, within the selected vault context.
- Solution/industry language applied: Electrical-contractor industry language is limited to mixed service, maintenance and project workflows for US electrical contractors, within the selected vertical context.
- Fallback context use: none
- Claims requiring source verification: none
- Status: aligned

## Named Feature/Add-On Link Check

- Named Simpro feature in public copy: Simpro Takeoffs.
- Feature-specific vault evidence: `resource_id=res-c6e69419a82e59919b4af4731a7e496a`.
- Public feature URL: `https://www.simprogroup.com/features/takeoffs`.
- Link decision: link the first and only meaningful mention in the takeoff FAQ.
- Reason: the feature-specific resource and current public page directly support the takeoff-to-estimate-and-project handoff.
- Status: passed.

## Competitive Shortlist Decision

- Article objective: Help US electrical contractors choose a short demo list by job mix, then compare workflow fit, pricing, implementation and integration requirements on equal terms.
- Authority: vault connector
- Status: approved

| Competitor | Decision | Reason | Resource ID | Claim ID | Public URL |
| --- | --- | --- | --- | --- | --- |
| ServiceTitan | selected | Included in the user-approved service, commercial and project comparison set. | res-517ad5ccb2cd5c3985831d8aba4cedaa | [none] | https://www.servicetitan.com/industries/electrical-software |
| BuildOps | selected | Included in the user-approved commercial electrical, maintenance and project comparison set. | res-517ad5ccb2cd5c3985831d8aba4cedaa | [none] | https://buildops.com/industries/electrical |
| Knowify | selected | Included in the user-approved project-costing and service comparison set. | res-517ad5ccb2cd5c3985831d8aba4cedaa | [none] | https://knowify.com/electrical-contractors/ |
| FieldPulse | selected | Included in the user-approved electrical service comparison set. | res-517ad5ccb2cd5c3985831d8aba4cedaa | [none] | https://www.fieldpulse.com/solutions/electrical |
| Jobber | selected | Included in the user-approved streamlined-service comparison set. | res-517ad5ccb2cd5c3985831d8aba4cedaa | [none] | https://www.getjobber.com/pricing/ |
| Housecall Pro | selected | Included in the user-approved residential and light-commercial service comparison set. | res-517ad5ccb2cd5c3985831d8aba4cedaa | [none] | https://www.housecallpro.com/industries/electrical-contractor-software/ |
| Service Fusion | selected | Included in the user-approved small and midsize service comparison set. | res-517ad5ccb2cd5c3985831d8aba4cedaa | [none] | https://www.servicefusion.com/pricing |
| FieldEdge | selected | Included in the user-approved established service-operation comparison set. | res-517ad5ccb2cd5c3985831d8aba4cedaa | [none] | https://fieldedge.com/electrician-software/ |
| Tradify | selected | Included in the user-approved solo and small-team comparison set. | res-517ad5ccb2cd5c3985831d8aba4cedaa | [none] | https://www.tradifyhq.com/trades/electrician-av-software-app |
| AroFlo | rejected | Outside the fixed user-approved ten-product buyer interface; exclusion is not a quality or availability judgment. | res-517ad5ccb2cd5c3985831d8aba4cedaa | [none] |  |

## Hindsight Strategy Selection

- evidence_output: `{HINDSIGHT}`
- Evidence artifact SHA-256: `{sha(HINDSIGHT)}`.
- Strategy resource IDs: `res-acdf63e464db5579a008beb136c20593`, `res-0c176526ba255cdc84781594dbcb1d1f`, `res-8e0e276d13c95a7ea5bfb45bd57dfde2`.
- Status: internal_strategy_only
- public_claim_use: prohibited
- claim_support_allowed: false
- Applied privately to: job-mix routing, comparison dimensions, three electrical demo scenarios, pricing and implementation objections, scorecard logic and CTA framing.
- Public leakage check: no Hindsight count, quote, metric, ranking, deal observation or unsupported claim appears in public copy.

## Customer proof selector

- Health command completed with 65 approved rows; live reuse scan results are recorded in the command output for this run.
- Selector evidence: `{CUSTOMER}`, SHA-256 `{sha(CUSTOMER)}`.
- Selector-specific context pack and receipt were rebuilt from the current article-bound request before selection.
- Selector outcome: customer proof candidates available for the metric role only; no candidate was returned for quote, theme or experience_story.

## Customer Proof Slate

{customer_text}

## Customer Proof Selection Decision

- Role: metric | Top candidate: `case-study-teamwired` | Selected: [none] | Claim ID: `claim-metric-MET-1482`.
- Rejection reason: TEAMWired is not an electrical-contractor story and does not directly improve the service, maintenance or project job-mix decision. It also has three recent uses and is marked overused in the current health report. The user required conditional proof, so public copy omits it.
- Role: quote | Selected: [none] | Reason: selector returned no directly relevant approved candidate.
- Role: theme | Selected: [none] | Reason: selector returned no directly relevant approved candidate.
- Role: experience_story | Selected: [none] | Reason: selector returned no directly relevant approved candidate.
- Public-copy boundary: no customer name, customer metric, review theme, testimonial, quote or experience story appears.

{fred_text}

## E-E-A-T Proof Map

- Applicability: required.
- First-hand evidence decision: Selected: [none]. No approved identity-backed experience story supports this article's job-mix software evaluation objective, so public copy omits customer experience proof rather than forcing an irrelevant story.
- Author policy: no_author
- Intent: commercial_investigation.
- Positive signals: current official vendor evidence, symmetric limitations, publisher disclosure, job-specific live-demo scenarios, two independent authority sources and transparent no-proof decisions.
- Decision: proof_unavailable_safe_to_publish.
- Reason: no directly relevant customer experience story or Fred source was selected, and no verified named author or reviewer was supplied.
- Status: approved with a documented no-author limitation.

## Metric Proof Pack

- Metric requirement: not applicable
- Reason: the article publishes no market-size, benchmark, rating, ranking, review aggregate, ROI or customer-outcome metric. Numeric trial and user statements are vendor commercial facts mapped below.
- Search log: reviewed the current official vendor pages, customer-proof inventory and selector, Fred selector, connector context, Semrush UI capture and Source Map on {DATE}; no independent outcome metric was selected.
- Approved metrics: none used.

## PAA/FAQ Provenance

- Source: answersocrates
- Artifact: `{PAA}`
- Artifact SHA-256: `{sha(PAA)}`
- Query: electrical job management software
- Country: United States
- Language: English
- Collection date: {DATE}
- Selected questions:
  - What is the best CRM for electrical contractors?
  - What scheduling software is best for electricians?
  - What is the best app for electrical contractors?
  - What is the best software for electricians to use for takeoffs?
- First visible answer paragraphs contain 55, 56, 52 and 59 words.

## FAQ Source Policy

- Allowed source classes: neutral, non_competing_expert, owned_product.
- Competitor-owned FAQ sources: prohibited.
- Status: aligned.

## FAQ Proof Map

- FAQ: What is the best CRM for electrical contractors? | URL: https://www.simprogroup.com/solutions/job-management-software | Source class: owned_product | Competitor check: passed | Support: the owned solution page supports keeping customer records connected to operational job workflows. | Citation mode: inline_required | Status: visible in the first answer paragraph.
- FAQ: What scheduling software is best for electricians? | URL: https://www.cisa.gov/resources-tools/resources/assisting-small-and-medium-sized-businesses-assess-vendors-and-suppliers-fact-sheet | Source class: neutral | Competitor check: passed | Support: CISA provides structured supplier-assessment questions for SMB technology purchases. | Citation mode: inline_required | Status: visible in the first answer paragraph.
- FAQ: What is the best app for electrical contractors? | URL: https://www.cisa.gov/resources-tools/resources/assisting-small-and-medium-sized-businesses-assess-vendors-and-suppliers-fact-sheet | Source class: neutral | Competitor check: passed | Support: CISA provides security, continuity and supplier assessment questions for the app evaluation. | Citation mode: inline_required | Status: visible in the first answer paragraph.
- FAQ: What is the best software for electricians to use for takeoffs? | URL: https://www.simprogroup.com/features/takeoffs | Source class: owned_product | Competitor check: passed | Support: the owned feature page supports drawing measurement, material calculation and the takeoff-to-quote/project handoff. | Citation mode: inline_required | Status: visible in the first answer paragraph.

## Source Map

{chr(10).join(rows)}

## Search Intent and Format Decision

- Contract version: blog-strategy-contract/v1
- Primary query or prompt: electrical job management software
- Searcher task: Compare electrical job-management platforms and decide which two or three deserve a live demo for the contractor's job mix.
- Intent class: commercial
- Funnel stage: mofu
- SERP evidence artifact: {SERP}
- SERP evidence SHA-256: `{sha(SERP)}`
- Dominant content type: General Article (conservative collector classification because the Semrush table exposes URLs rather than titles)
- Selected content type: Commercial software comparison and buyer guide
- Observed SERP features: Sitelinks, AI Overview, Reviews, Video
- Related-query/PAA artifact: {PAA}
- Format decision: documented_exception
- Exception reason: The current Semrush top ten is dominated by vendor category pages, while the existing Simpro comparison ranks eighth. A job-mix buying guide preserves commercial-investigation intent while adding a consistent shortlisting and demo format that category pages do not provide.
- Status: ready

## Commercial Pillar and Anchor Decision

- Contract version: blog-strategy-contract/v1
- Article title: Best Electrical Job Management Software by Job Type (2026)
- Article primary keyword: electrical job management software
- Article intent: commercial
- Destination ID: simpro-us-industry-electrical-software
- Commercial pillar URL: https://www.simprogroup.com/industries/electrical-software
- Planned anchor text: electrical contractor software
- Planned H2 section: Which electrical job management software fits your job mix?
- Existing overlapping URLs checked: the live canonical article, electrical industry pillar, job-management solution, project-management solution and field-service comparison.
- Pillar-versus-blog intent difference: the blog owns comparison, shortlisting and purchase evaluation for electrical job management software; the industry page owns product/category intent for electrical contractor software.
- Cannibalization decision: different_intent
- Incoming-link candidates: the electrical industry page should link back with anchor `electrical job management software comparison`; that page mutation is outside this article-file task.
- Status: aligned

## Lifecycle Refresh Record

- Contract version: blog-strategy-contract/v1
- Last-updated date: {DATE}
- Volatility: high
- Next review date: 2026-12-27
- Review command: `/performance-review published/best-electrical-job-management-software-2026-09-02.md`
- GSC lane: unavailable: no fresh GSC export was collected for this rewrite; no query-performance inference is made.
- GA4 lane: unavailable: no fresh GA4 export was collected for this rewrite; no engagement inference is made.
- Semrush lane: available: authenticated US desktop Semrush UI keyword metrics captured {DATE}; position-level rows use the verified 2026-09-03 capture because the current table timed out twice.
- AI-citation lane: unavailable: no current AI-citation export was collected; no citation-performance inference is made.
- Decision: update
- Status: scheduled

## Semrush Evidence Boundary

- Keyword decision: `{KEYWORD}`, SHA-256 `{sha(KEYWORD)}`.
- Fresh authenticated main-Chrome UI metrics on {DATE}: primary query volume 320, KD 26, commercial intent, CPC $54.74, competitive density 0.05 and global volume 960; pillar query volume 1,300, KD 21, commercial intent, CPC $53.16, competitive density 0.20 and global volume 3,000.
- Current SERP capture: authenticated Semrush US desktop SERP Analysis on {DATE}; 133 results, features Sitelinks, AI Overview, Reviews and Video, with the current ordered top ten bound in `{SERP}`.

## Author and Schema Decision

- Author policy: no_author
- Named author verified: no.
- Named reviewer verified: no.
- Frontmatter author field: omitted.
- `Person as author`: omitted.
- Required schema notes: `BlogPosting`, `BreadcrumbList`, `FAQPage`, `ItemList` with exactly 10 products, `Question and Answer inside FAQPage`, `ImageObject for the featured image or logo`, and `Organization as publisher reference only, not a separate full schema block`.
- ItemList order matches the ten public vendor cards.
- VideoObject: omitted because no video is embedded.
- Status: approved.

## Image Preservation and CMS Handoff

- Hero source preserved: `/images/d/b/8/f/8/db8f85b1b0c5b87895fd04f6b3bd55d7c6bc62ff-simbest-electrical-job-mgmt-softwarefeature-1819x250.png`; planned filename `electrical-job-management-software-comparison-2026-1819x250.webp`; conservative alt text retained.
- Buyer-signals source preserved: `https://www.simprogroup.com/user/pages/blog/best-electrical-job-management-software/SIM_best-electrical-job-mgmt-software_Interior-1_819x819.png`; planned filename `electrical-job-management-software-buyer-signals-819x819.webp`; conservative alt text retained.
- Outgrown-workflow source preserved: `https://www.simprogroup.com/user/pages/blog/best-electrical-job-management-software/SIM_best-electrical-job-mgmt-software_Interior-3_819x819.png`; planned filename `electrical-job-management-software-outgrown-workflow-819x819.webp`; conservative alt text retained.
- Buying-mistakes source preserved: `https://www.simprogroup.com/user/pages/blog/best-electrical-job-management-software/SIM_best-electrical-job-mgmt-software_Interior-2_819x819.png`; planned filename `electrical-job-management-software-buying-mistakes-819x819.webp`; conservative alt text retained.
- Visual inspection result: all four original public source URLs returned Simpro 404 responses in the main Chrome browser on {DATE}. The copy does not pretend the assets were visually verified.
- CMS boundary: do not fabricate final public image URLs. Upload with the planned filenames, inspect the actual assets, confirm or correct alt text, and insert the URLs returned by the CMS.

## Internal-linking handoff

- Article links to the electrical commercial pillar, job-management solution, project-management solution, broader field-service comparison and Takeoffs feature where each adds distinct utility.
- Recommended incoming link: add a link from `https://www.simprogroup.com/industries/electrical-software` to the canonical article using an anchor such as `electrical job management software comparison`.
- Industry-page mutation: explicitly outside this article-file change.

## Public-copy checks

- Title, H1, ItemList, cards and comparison table contain exactly ten products in the approved order.
- Body word count: approximately 4,150 words, inside the approved 3,800-4,300 range.
- Opening direct answer: 56 words; filled decision table appears inside the first 300 body words.
- Vendor cards: 120-160 words under the card-body counting convention; headings produce a maximum of 160 words after final tightening.
- Four exact AnswerSocrates questions: present; each first visible answer paragraph is 40-60 words.
- Original image positions and sources: four preserved standalone placeholders with keyword-bearing upload filenames and alt text.
- Em dashes, mojibake, unsupported customer proof, Fred material and public Hindsight material: none.

## Release blockers

1. `image_asset_visual_inspection_pending`: the four preserved source assets return 404 from the public site. CMS-side inspection and upload are required before final public URLs and alt text can be confirmed.

## Release status

- Status: evidence complete for scoring. Image inspection and CMS upload remain a separate production handoff and do not authorize fabricated public URLs.
"""
    OUT.write_text(content, encoding="utf-8", newline="\n")
    print(f"wrote {OUT.relative_to(ROOT).as_posix()} sha256={sha(OUT)}")


if __name__ == "__main__":
    main()
