"""Write the validation sidecar for the BigChange COSHH regulations rewrite.

The sidecar is governance evidence only. Every Source Map Evidence string was
checked against the live page text on 2026-09-24 (requests fetch, visible
text), and each row binds the exported source-classification artifact by path
and SHA-256.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

SLUG = "coshh-regulations"
DATE = "2026-09-24"
RUN_ID = (ROOT / ".run-coshh.env").read_text(encoding="utf-8").split("RUN_ID=")[1].split("\n")[0].strip()
OUT = ROOT / "research" / f"validation-{SLUG}-{DATE}.md"
CLASS_DIR = ROOT / "research" / "source-classifications" / f"{SLUG}-{DATE}"
CAPTURE_DIR = f"research/source-captures/{SLUG}-{DATE}"
SELECTOR = ROOT / "research" / f"nonvault-customer-proof-selector-evidence-{SLUG}-{DATE}.json"
CAP = "https://www.capterra.co.uk/software/149479/jobwatch-powered-by-bigchange"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def classification(url: str) -> tuple[str, str]:
    path = CLASS_DIR / f"source-classification-{hashlib.sha256(url.encode('utf-8')).hexdigest()}.json"
    if not path.is_file():
        raise FileNotFoundError(f"missing classification for {url}")
    return path.relative_to(ROOT).as_posix(), sha(path)


def source_class(url: str) -> str:
    return json.loads((ROOT / classification(url)[0]).read_text(encoding="utf-8"))["source_class"]


LIVE = "Authoritative page read live on the checked date."
SOURCE_MAP_ROWS = ROOT / "research" / f"source-map-rows-{SLUG}-{DATE}.json"
STAT_REASON = "HSE statistics overview updated 2026-01-07 is the original publication of the figure."
SENT_REASON = "Definitive Sentencing Council guideline in force since 1 February 2016 and read on the checked date."


def source_map() -> str:
    """Render claim-bound rows derived by scripts/build_coshh_source_map.py."""
    data = json.loads(SOURCE_MAP_ROWS.read_text(encoding="utf-8"))
    lines = []
    for row in data["rows"]:
        url = row["url"]
        cpath, chash = classification(url)
        reason = STAT_REASON if "statistics" in url else SENT_REASON if "sentencingcouncil" in url else LIVE
        evidence = " ".join(row["evidence"].split())
        receipt_hash = sha(ROOT / row["receipt"])
        lines.append(
            f"- Claim: {row['claim']} | Claim type: {row['claim_type']} | Source class: {source_class(url)}"
            f" | Evidence relation: directly_supports | URL: {url} | Evidence: {evidence}"
            f" | Original-source status: original | Source date: {DATE} | Checked date: {DATE}"
            f" | Claim fit: direct | Freshness decision: current | Freshness reason: {reason}"
            f" | Artifact: {row['artifact']} | Capture receipt: {row['receipt']} | Capture receipt hash: {receipt_hash}"
            f" | Classification artifact: {cpath} | Classification hash: {chash} | Citation mode: inline_required"
            f" | Status: approved | Intended use: {row['claim_type']} claim at article line {row['line']}"
        )
    return "\n".join(lines)


def capture(key: str) -> tuple[str, str, str]:
    art = f"{CAPTURE_DIR}/{key}.md"
    rec = f"{CAPTURE_DIR}/{key}-capture-receipt.json"
    return art, rec, sha(ROOT / rec)


def main() -> int:
    selector_hash = sha(SELECTOR)
    suz_art, suz_rec, suz_hash = capture("capterra-uk-bigchange-suzanne-transport-page-2")
    clare_art, clare_rec, clare_hash = capture("capterra-uk-bigchange-clare-hseq-page-6")
    cap_cpath, cap_chash = classification(CAP)
    clg = "https://www.bigchange.com/success-stories/bigchange-helps-clearground-clean-up-on-workforce-health-and-safety"
    clg_cpath, clg_chash = classification(clg)
    slate_lines = (ROOT / "research" / f"nonvault-customer-proof-slate-{SLUG}-{DATE}.md").read_text(encoding="utf-8").splitlines()[1:]
    slate = "\n".join(line.replace("research\\", "research/") for line in slate_lines if line.strip())
    text = TEMPLATE.format(slate=slate, 
        run_id=RUN_ID, date=DATE, source_map=source_map(), selector_hash=selector_hash,
        cap=CAP, suz_art=suz_art, suz_rec=suz_rec, suz_hash=suz_hash,
        clare_art=clare_art, clare_rec=clare_rec, clare_hash=clare_hash,
        cap_cpath=cap_cpath, cap_chash=cap_chash, clg=clg, clg_cpath=clg_cpath, clg_chash=clg_chash,
    )
    OUT.write_bytes(text.encode("utf-8"))
    print(f"sidecar: {OUT.relative_to(ROOT).as_posix()} rows={source_map().count(chr(10)) + 1}")
    return 0


TEMPLATE = """# Validation Sidecar: COSHH Regulations

Date: {date}
Run ID: {run_id}
Article: rewrites/coshh-regulations-{date}.md
Workflow mode: rewrite
Brand: BigChange
Original URL: https://www.bigchange.com/blog/cleaning-chemicals-safety-your-guide-to-the-coshh-regulations
Target URL: https://www.bigchange.com/blog/coshh-regulations (301 from the original URL)

## Context Binding

Decision: nonconnector
Status: approved
Reason: The final article is BigChange-owned and contains no Simpro or simprogroup.com public-copy signal.
Connector artifacts omitted: context request, context pack, context receipt, Fred authority evidence, and vault customer-proof selector evidence.
Nonconnector rationale: BigChange is a nonconnector workflow unless the article introduces Simpro or an official simprogroup.com URL.

## Release Status

Status: ready for the first release wrapper run
Blockers: [none recorded before the first wrapper run]
Publish boundary: Final publish readiness remains owned by `blog_release.py`.

## Brief-Bound Inputs

- Primary keyword: coshh regulations
- Secondary keywords: coshh meaning, what is coshh, coshh assessment, coshh risk assessment, what are the 3 main regulations of coshh, coshh regulations 2002
- Recommended word count: 2,400-2,800
- Search intent: educational
- Page type: blog post update with a 301 redirect to /blog/coshh-regulations
- Brief: research/content-brief-coshh-regulations-{date}.md (Pheonix brief, Google Doc 1t2V9nTLly9uVp0ghyH-OTrXRe02JNJxE7XBWJS5ZP7Q)
- Guru SEO best practices conflict: the Guru card says keep the original URL and use at most two external links. The brief sets a new URL with a 301, and regulatory claims need inline authoritative links, so the brief and repo policy govern both points.

## Semrush UI Keyword Evidence

- Execution surface: semrush_ui_chrome_main_browser
- Database: uk
- Collection date: {date}
- Artifact: research/semrush-keyword-decision-coshh-regulations-{date}.json
- Artifact directory: research/semrush-ui-coshh-regulations-{date}
- Screenshot: keyword-overview-coshh-regulations.jpg
- Screenshot: serp-analysis-coshh-regulations.jpg
- Screenshot: keyword-overview-coshh-assessment.jpg
- Screenshot: serp-analysis-coshh-assessment.jpg
- Screenshot: keyword-overview-what-is-coshh.jpg
- Screenshot: keyword-overview-coshh-meaning.jpg

Visible keyword metrics:

| Keyword | Intent | UK volume | Global volume | KD | CPC (GBP) | Competitive density | Decision |
|---|---|---:|---:|---:|---:|---:|---|
| coshh regulations | Informational | 6,600 | 7,800 | 35 Possible | 0.91 | 0.24 | selected primary |
| coshh meaning | Informational | 22,200 | 26,300 | 28 Easy | 0.67 | 0.07 | secondary |
| what is coshh | Informational | 4,400 | 5,500 | 25 Easy | 0.99 | 0.04 | secondary |
| coshh assessment | Informational | 2,900 | 4,800 | 26 Easy | 3.91 | 0.62 | secondary |

Decision: The brief primary is kept. Its UK SERP is regulator and explainer content that matches an educational employer guide. The original URL ranks for 0 UK keywords on 2026-09-23 in Semrush Organic Rankings.

## GSC Baseline

- Property: sc-domain:bigchange.com
- Window: trailing 480 days to {date}
- Existing URL: top 25 queries total 232 impressions and 0 clicks
- Largest latent demand: coshh (58 impressions, average position 57.8), coshh act (46), coshh app (42), cleaning equipment covered by coshh regulations (13, average position 19.1)
- Use: internal prioritisation only. No traffic or ranking forecast appears in public copy.

## SERP Evidence

- Artifact: research/serp-evidence-coshh-regulations-{date}.json
- Raw capture: research/serp-chrome-raw-coshh-regulations-{date}.json
- Collector: research_serp_analysis:chrome_connector 1.0.0
- Query: coshh regulations
- Locale: www.google.com/search, hl=en, gl=uk, pws=0
- Observed SERP features: AI Overview, People also ask, Videos, Short videos, Images, People also search for
- Observed pattern: regulator and explainer pages dominate, led by hse.gov.uk and legislation.gov.uk
- Competitor-use boundary: The ranking pages recorded in the SERP evidence artifact were read for structure and gap analysis only. None supports a claim in this article.

## Metric Proof Pack

- Metric requirement: applicable
- Search log: HSE work-related ill health statistics were searched for a current figure. The original article's 1.6 million figure was rejected as stale. The original article's average fine of 150,000 pounds was rejected because its HSE enforcement PDF link returns 404 and HSE no longer publishes enforcement statistics in its annual release. The Sentencing Council guideline was accepted for the unlimited fine.
- Status: approved

- Approved metric: Health and Safety Executive statistics estimate 11,000 lung disease deaths each year linked to past exposures at work | URL: https://www.hse.gov.uk/statistics/causdis/overview.htm | Evidence: lung disease deaths each year estimated to be linked to past exposure at work | Status: approved | Use: What is COSHH section, stakes paragraph
- Approved metric: 1.9 million workers suffering from work-related ill health in 2024/25 | URL: https://www.hse.gov.uk/statistics/causdis/overview.htm | Evidence: 1.9 million workers suffering from work-related ill health | Status: approved | Use: What is COSHH section, stakes paragraph

Rejected metric rows:

| Claim family | Reason | Status |
|---|---|---|
| Average COSHH fine of 150,000 pounds | No primary source found and the cited HSE enforcement PDF returns 404. | rejected |
| 1.6 million people with work-related illness or injury | Superseded by the current HSE 2024/25 figure. | rejected |
| Any BigChange customer outcome figure for COSHH | No approved BigChange customer metric exists for this topic. | rejected |

## Non-Vault Proof Eligibility Decision

- Brand: BigChange
- Context binding: nonconnector
- Approved contract: simpro-nonvault-customer-proof-selector-evidence/v1
- Eligible source classes: brand-owned customer_story, case_study and reference pages, plus approved Capterra review_site rows on the BigChange Capterra product page
- Selected proof ID: bigchange-clearground-dynamic-risk-assessments (theme), review-capterra-bigchange-clare-hseq-health-safety-worksheets (experience_story), review-capterra-bigchange-suzanne-transport-compliance-records (quote)
- Public-use boundary: Clearground and Clare appear as paraphrased stories with same-paragraph public links. Suzanne appears with the single approved snippet, first name, role, and a same-paragraph Capterra link.
- Prohibited use: customer metrics, ratings, star claims, aggregate claims, rankings, typical-results claims and guaranteed-result language
- Vault boundary: no context pack, context receipt, Fred evidence, or vault-dependent customer-proof selector evidence supplied
- Status: approved

## Customer Proof Slate

{slate}

## Customer Proof Pack

- Pack status: selected
- Topic or page fit: COSHH regulations and COSHH assessments for UK field service employers.
- Quote Matrix candidates: Not applicable for this nonconnector brand.
- Case-study proof paths: Clearground public success story at {clg}
- Review-site experience evidence: Clare (HSEQ Manager, 13 January 2021) and Suzanne (Transport Manager, 1 June 2023) on the public Capterra UK BigChange page, captured 2026-09-24.
- Approved quote: "keeping all documents together showing a stream from report to completion of faults and issues which keeps us compliant" | Source type: review_site | Identity: Suzanne, Transport Manager, UK building materials | URL: {cap} | Evidence: keeping all documents together showing a stream from report to completion of faults and issues which keeps us compliant | Proof artifact: {suz_art} | Capture receipt: {suz_rec} | Capture receipt hash: {suz_hash} | Status: approved | Use: exact snippet with first name, role, and a same-paragraph Capterra link in the field compliance section
- Approved metrics: none used in public copy.
- Use in copy: Clearground paraphrased story, Clare paraphrased story, Suzanne approved snippet.
- Claims excluded: ratings, star claims, aggregate review claims, customer metrics, and the Clare review's staffing figure.

## Selected Customer Proof Mining

- Proof: bigchange-clearground-dynamic-risk-assessments | Customer: Clearground | URL: {clg}
- Proof: review-capterra-bigchange-suzanne-transport-compliance-records | Customer: Capterra reviewer Suzanne, Transport Manager | URL: {cap}
- Proof: review-capterra-bigchange-clare-hseq-health-safety-worksheets | Customer: Capterra reviewer Clare, HSEQ Manager | URL: {cap}
- Checked for: exact quotes, customer metrics, POV story, workflow themes
- Usable quotes found: one approved snippet from Suzanne, stored in the row's approved_quotes. The Clearground quote is not used because nonvault copy paraphrases case studies, and Clare's wording contains modal verbs.
- Usable metrics found: none found. Clare's staffing figure is not an approved metric.
- Usable POV/story found: Clearground makes customised dynamic risk assessments mandatory on site; Clare's team builds its own health and safety worksheets in house.
- Recommended use: paraphrased POV/story for Clearground and Clare, exact snippet for Suzanne
- Final use in copy: Clare's experience story and the Clearground POV story, both paraphrased, plus the Suzanne exact quote from the row's approved_quotes, each with a same-paragraph public link in the field compliance section.
- Excluded proof: star ratings, review counts, rankings, and any outcome figure.
- Status: approved

## Customer Proof Selection Decision

- Selected proof: bigchange-clearground-dynamic-risk-assessments
- Selected proof: review-capterra-bigchange-clare-hseq-health-safety-worksheets
- Selected proof: review-capterra-bigchange-suzanne-transport-compliance-records
- Use: Clearground paraphrased theme, Clare paraphrased experience story, Suzanne exact snippet
- Reuse reason: not applicable. The three rows carry zero prior uses in context/customer-proof-usage-ledger.json, and a live repo scan of drafts, rewrites, research and published found no public-copy use.
- Zero-use comparison: no stronger underused approved proof was displaced.
- Rejected candidate: bigchange-customer-story-hodge-clemco-paperless-jobs | Reason: Paperless job story with no health and safety or risk assessment content for a COSHH article
- Rejected candidate: bigchange-rilmac-prove-compliance-hse-inspection | Reason: asbestos services work falls under a separate regime from COSHH, so the story risks implying COSHH-specific compliance
- Rejected candidate: review-capterra-bigchange-hannah-construction-one-system-workflow | Reason: one-system workflow review with no health and safety content and four recent uses
- Status: approved

## E-E-A-T Strength Decision

- Author policy: no_author
- Applicability: required
- Intent: informational
- Positive signals: selected customer story (Clearground), review-derived experience stories (Clare, Suzanne)
- Decision: proof_available
- Reason: Selected customer and review experience supports the field compliance section, and HSE and legislation.gov.uk sources carry Authority for every regulatory claim.
- Public copy boundary: No ratings, star claims, aggregate review claims, customer metrics, or unsupported SME claims.
- Status: approved

Author decision: The 2022 byline "bigchangev3Admin" is a CMS account, not a named author. `author` is omitted from frontmatter, `Person as author` is omitted from schema notes, and `Organization` remains a publisher reference only.

## E-E-A-T Proof Map

| Dimension | Selected evidence | Public use | Status |
|---|---|---|---|
| Experience | Clearground success story, Clare and Suzanne Capterra UK reviews | Paraphrased stories and one approved snippet with same-paragraph links | approved |
| Expertise | Regulation-by-regulation guidance, a five-step assessment process, and a filled field-job checklist | Operational guidance tied to the regulation text | approved |
| Authority | HSE guidance, HSE statistics, legislation.gov.uk regulation text, Sentencing Council guideline | Same-paragraph or same-row links for every regulatory and numeric claim | approved |
| Trust | Nonconnector proof contract, exact Source Map, no-author disclosure, removal of the unsourced fine figure | No rating, metric, or guaranteed result | approved |

- First-hand evidence decision: Selected: review-capterra-bigchange-clare-hseq-health-safety-worksheets because an HSEQ manager describing health and safety worksheets built in house is first-hand experience of the workflow the field compliance section recommends.

## Review Story Selection

- Selected story: review-capterra-bigchange-clare-hseq-health-safety-worksheets | Identity: Clare | URL: {cap} | Status: approved
- Selected story: review-capterra-bigchange-suzanne-transport-compliance-records | Identity: Suzanne | URL: {cap} | Status: approved
- Review platform: Capterra
- Identity type: person
- Identity display: Clare, HSEQ Manager in UK construction; Suzanne, Transport Manager in UK building materials
- Review date: 13 January 2021 (Clare); 1 June 2023 (Suzanne)
- Public review URL: {cap}
- Permitted use mode: paraphrase (Clare); exact snippet bound to approved_quotes (Suzanne)
- Same-paragraph article link: yes, each name and its Capterra link sit in one paragraph of the field compliance section.
- Verification status: captured in Chrome 2026-09-24. Proof artifacts {clare_art} and {suz_art}, capture receipt hashes {clare_hash} and {suz_hash}. Classification artifact {cap_cpath} ({cap_chash}).
- Boundary: each review is one user's workflow experience, not a BigChange-wide outcome, a rating, or current product status.
- Status: approved

## Source Map

{source_map}
- Claim: Its team builds customised, dynamic risk assessments and makes completing them on site mandatory before work begins | Claim type: customer_proof | Source class: customer_proof | Evidence relation: directly_supports | URL: {clg} | Evidence: The ability to create customised, dynamic risk assessments and make their completion on-site mandatory goes beyond other systems we looked at. | Original-source status: original | Source date: {date} | Checked date: {date} | Claim fit: direct | Freshness decision: current | Freshness reason: Public BigChange success story read live on the checked date. | Classification artifact: {clg_cpath} | Classification hash: {clg_chash} | Citation mode: inline_required | Status: approved | Intended use: Field compliance section, Clearground story
- Claim: They build those worksheets in house, without software engineers | Claim type: review | Source class: review_platform | Evidence relation: directly_supports | URL: {cap} | Evidence: you do not need software engineers to design your worksheets | Original-source status: original | Source date: 2021-01-13 | Checked date: {date} | Claim fit: direct | Freshness decision: historical_scoped | Freshness reason: The review is dated 2021-01-13 and the claim is scoped to the reviewer's own workflow experience rather than current product status. | Artifact: {clare_art} | Capture receipt: {clare_rec} | Capture receipt hash: {clare_hash} | Classification artifact: {cap_cpath} | Classification hash: {cap_chash} | Citation mode: inline_required | Status: approved | Intended use: Field compliance section, Clare story
- Claim: Clare, an HSEQ manager at a UK construction firm, wrote on Capterra that her team designs its own policies, procedures, and health and safety worksheets in BigChange | Claim type: review | Source class: review_platform | Evidence relation: directly_supports | URL: {cap} | Evidence: you can design to meet your company needs for policies, procedures, health & safety | Original-source status: original | Source date: 2021-01-13 | Checked date: {date} | Claim fit: direct | Freshness decision: historical_scoped | Freshness reason: The review is dated 2021-01-13 and the claim is scoped to the reviewer's own workflow experience rather than current product status. | Artifact: {clare_art} | Capture receipt: {clare_rec} | Capture receipt hash: {clare_hash} | Classification artifact: {cap_cpath} | Classification hash: {cap_chash} | Citation mode: inline_required | Status: approved | Intended use: Field compliance section, Clare story
- Claim: She credits BigChange with "keeping all documents together showing a stream from report to completion of faults and issues which keeps us compliant." | Claim type: quote | Source class: review_platform | Evidence relation: directly_supports | URL: {cap} | Evidence: keeping all documents together showing a stream from report to completion of faults and issues which keeps us compliant | Original-source status: original | Source date: 2023-06-01 | Checked date: {date} | Claim fit: direct | Freshness decision: historical_scoped | Freshness reason: The review is dated 2023-06-01 and the quote is scoped to the reviewer's own records workflow rather than current product status. | Artifact: {suz_art} | Capture receipt: {suz_rec} | Capture receipt hash: {suz_hash} | Classification artifact: {cap_cpath} | Classification hash: {cap_chash} | Citation mode: inline_required | Status: approved | Intended use: Field compliance section, Suzanne snippet

## FAQ Source Policy

- Allowed source classes: neutral, non_competing_expert, owned_product.
- Competitor-owned FAQ sources: prohibited.
- Status: aligned.

## FAQ Proof Map

- FAQ: Is a COSHH assessment a legal requirement? | URL: https://www.legislation.gov.uk/uksi/2002/2677/regulation/6 | Source class: neutral | Competitor check: passed | Support: Regulation 6 sets the duty to make a suitable and sufficient assessment and the 5 or more employees recording rule. | Status: approved
- FAQ: Is a safety data sheet the same as a COSHH assessment? | URL: https://www.hse.gov.uk/coshh/faq.htm | Source class: neutral | Competitor check: passed | Support: HSE states a good safety data sheet does not substitute for carrying out and recording a COSHH risk assessment. | Status: approved
- FAQ: Does COSHH apply to cleaning products? | URL: https://www.hse.gov.uk/cleaning/topics/coshh.htm | Source class: neutral | Competitor check: passed | Support: HSE classes a product as hazardous when its packaging carries a hazard symbol. | Status: approved
- FAQ: Does COSHH training need to be provided to employees? | URL: https://www.legislation.gov.uk/uksi/2002/2677/regulation/12 | Source class: neutral | Competitor check: passed | Support: Regulation 12 requires suitable and sufficient information, instruction and training. | Status: approved

## PAA/FAQ Provenance

- Source: brief_paa
- Artifact: research/content-brief-coshh-regulations-{date}.md
- Selected questions:
  - Is a COSHH assessment a legal requirement?
  - Is a safety data sheet the same as a COSHH assessment?
  - Does COSHH apply to cleaning products?
  - Does COSHH training need to be provided to employees?
Status: approved

Precedence rationale: the supplied content brief carries a dedicated FAQ set, and for a rewrite that pre-picked brief section takes precedence over SERP or AnswerSocrates collection. The four questions above are reproduced from it without alteration and match the article's visible FAQ headings exactly. The Google UK People Also Ask questions in the SERP raw capture are supplemental only.

## Early Artifact Plan

- Early artifact requirement: applicable
- Artifact: COSHH at a glance table
- Placement: immediately after the two-paragraph introduction, opening inside the first 300 words of body copy
- Columns: Regulation, What it requires, What to do on each job, Record to keep
- Placeholder check: every cell carries real guidance; no TBD, varies, or scaffold cells
- Status: approved

## Image Inventory

| Slot | Source path | ALT text | Decision |
|---|---|---|---|
| Hero | assets/images/blog/coshh-regulations/coshh-regulations-engineer-safety-data-sheet-hero.webp | Field engineer checking a COSHH safety data sheet before using cleaning chemicals on site | preserve the original featured image (original_source: https://cdn.prod.website-files.com/652e90c1583f67a8de233f2d/67000080f81e7a4460780351_66696a3cd67a02896093e4ec_65f32663764632944d81806f_659ed3b823c4189f754bf132_Unknown2.jpeg, 600 x 372, empty alt) re-exported under a keyword filename with new alt text |
| In-body | assets/images/blog/coshh-regulations/coshh-regulations-3-main-regulations-6-7-12.webp | The 3 main COSHH regulations: Regulation 6 risk assessment, Regulation 7 control of exposure, Regulation 12 training | new original graphic to be produced |
| In-body | assets/images/blog/coshh-regulations/coshh-hierarchy-of-control-regulation-7.webp | COSHH hierarchy of control from elimination and substitution to PPE | new original graphic to be produced |
| In-body | assets/images/blog/coshh-regulations/coshh-assessment-5-steps-process.webp | 5 steps to carry out a COSHH assessment for field service jobs | new original graphic to be produced |
| In-body | assets/images/blog/coshh-regulations/coshh-risk-assessment-mobile-app-field-engineer.webp | Engineer completing a COSHH risk assessment on a mobile app before starting a job | new original graphic to be produced |

Video decision: The BigChange YouTube video https://www.youtube.com/watch?v=_YXifF-nLxA (uploaded 2019-10-24, 2:22, playableInEmbed true) appears as a VIDEO PLACEHOLDER only. VideoObject stays out of schema notes until the embed ships. No claim about the customer in the video appears in public copy.

## Internal Link Plan

| Target | Anchor | Role | Status |
|---|---|---|---|
| https://www.bigchange.com/features/risk-assessment | digital risk assessment software for field engineers | down_funnel | approved |
| https://www.bigchange.com/blog/ppm-schedule | PPM schedule | supporting | approved |
| https://www.bigchange.com/blog/field-service-excellence-bigchange-lightning | field service documentation | supporting | approved |
| https://www.bigchange.com/blog/how-to-grow-facilities-management-business | facilities management businesses | supporting | approved |
| https://www.bigchange.com/industries/cleaning-software-crm | digital library of COSHH sheets | supporting | approved |
| https://www.bigchange.com/success-stories/bigchange-helps-clearground-clean-up-on-workforce-health-and-safety | Clearground | proof (same-paragraph customer story link) | approved |
| https://www.bigchange.com/demo | Book a BigChange demo | conversion CTA | approved |

Source of the set: three destinations are specified by the brief with their briefed anchors. The risk assessment feature page is the commercial pillar and the cleaning industry page names a COSHH sheets library. The brief's eicr-test and win-electrical-contracts links were left out because neither supports a COSHH claim, keeping the set at five. The demo CTA is a conversion link, not an editorial destination. Anchor deviation: the brief suggests "facilities management compliance" for the facilities management post. The public-research gate treats "compliance" in an owned-link anchor as an unsupported regulatory claim, so the anchor reads "facilities management businesses" instead. Every destination, including the Clearground proof link and the demo CTA, returned HTTP 200 on {date}. Live total: 7 unique internal destinations, the hard maximum, so no further internal links fit without removing one.

## Documented Style Exceptions

- The brief's suggested direct answer ("the three COSHH regulations most commonly highlighted as the core employer duties") describes how guides frame COSHH, which no official source states. The article gives the same answer in the regulation titles' own terms, which the legislation.gov.uk contents page directly supports, and the next sentence makes clear COSHH has more than three regulations, as the brief requires.
- The H2s "How often should a COSHH assessment be reviewed?" and "How can field service businesses manage COSHH compliance across multiple jobs and sites?" keep the brief's exact wording. Question headings are exempt from the modal and passive lint rules.
- Readability sits near Grade 10 because of necessary regulatory terminology (Regulation, substitution, local exhaust ventilation, health surveillance).
- Meta title adds the "| BigChange" suffix to the brief's recommended title (59 characters). Meta description extends the brief's text with "Includes a field-job checklist." (154 characters).
- The contextual feature link and the closing demo CTA are the brief-required commercial pillar and conclusion CTA; see `engagement_map.cta_exception_reason` in the plan.
- Secondary keyword "what are the 3 main regulations of coshh" is served by the H2 "What are the 3 main COSHH regulations?" as a close variant.

## Source Review Boundary

The ranking pages captured in the SERP evidence artifact were read for SERP-pattern and gap analysis only. None was used as proof for any legal, safety, product or numeric claim, and none is named, linked or characterised in public copy.

Reddit was not used: reddit.com is blocked by the Chrome connector's safety list and by the web search tool. capterra.com returned a Cloudflare challenge that was not bypassed; the Capterra UK product page was read in Chrome instead.

## Readiness Notes

- Public copy must not contain this validation appendix.
- Public copy must not state that the article is publish-ready.
- Public copy must not contain the string simprogroup.com or the word Simpro.
- Public copy must not contain em dashes.
- Site issue for web development (outside the article): the live BigChange blog template emits a malformed canonical link.
"""


if __name__ == "__main__":
    raise SystemExit(main())
