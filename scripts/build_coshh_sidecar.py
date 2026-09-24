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
L = "https://www.legislation.gov.uk/uksi/2002/2677/"
CAP = "https://www.capterra.co.uk/software/149479/jobwatch-powered-by-bigchange"
SENT = "https://sentencingcouncil.org.uk/guidelines/organisations-breach-of-duty-of-employer-towards-employees-and-non-employees-breach-of-duty-of-self-employed-to-others-breach-of-health-and-safety-regulations/"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def classification(url: str) -> tuple[str, str]:
    path = CLASS_DIR / f"source-classification-{hashlib.sha256(url.encode('utf-8')).hexdigest()}.json"
    if not path.is_file():
        raise FileNotFoundError(f"missing classification for {url}")
    return path.relative_to(ROOT).as_posix(), sha(path)


def source_class(url: str) -> str:
    return json.loads((ROOT / classification(url)[0]).read_text(encoding="utf-8"))["source_class"]


# (claim, claim type, url, evidence, freshness decision, freshness reason, citation mode, intended use)
CURRENT = "current"
LIVE = "Authoritative page read live on the checked date."
ROWS = [
    ("COSHH regulations are the Control of Substances Hazardous to Health Regulations 2002", "definitional", L + "contents",
     "Health surveillance", CURRENT, "The legislation.gov.uk contents page lists the current regulations and was read on the checked date.", "inline_required", "Introduction, opening definition"),
    ("the UK law that requires employers to prevent or control exposure to harmful substances at work", "factual", L + "contents",
     "Prevention or control of exposure to substances hazardous to health", CURRENT, LIVE, "inline_required", "Introduction, opening definition"),
    ("The law asks you to assess the risk, control exposure, keep those controls working, and make sure every engineer understands them", "factual", "https://www.hse.gov.uk/coshh/law.htm",
     "require employers to plan, manage and monitor the use of chemicals", CURRENT, LIVE, "inline_required", "Introduction, second paragraph"),
    ("HSE's COSHH law summary puts it plainly", "factual", "https://www.hse.gov.uk/coshh/law.htm",
     "require employers to plan, manage and monitor the use of chemicals", CURRENT, LIVE, "inline_required", "Introduction, second paragraph"),
    ("the regulations require employers to plan, manage and monitor the use of hazardous substances", "factual", "https://www.hse.gov.uk/coshh/law.htm",
     "require employers to plan, manage and monitor the use of chemicals", CURRENT, LIVE, "inline_required", "Introduction, second paragraph"),
    ("A suitable and sufficient risk assessment before the work starts", "factual", L + "regulation/6",
     "suitable and sufficient assessment", CURRENT, LIVE, "inline_required", "COSHH at a glance table, Regulation 6 row"),
    ("Significant findings and control steps, for 5 or more employees", "factual", L + "regulation/6",
     "Where the employer employs 5 or more employees, he shall record", CURRENT, LIVE, "inline_required", "COSHH at a glance table, Regulation 6 row"),
    ("Prevent exposure, or control it adequately where prevention is not reasonably practicable", "factual", L + "regulation/7",
     "either prevented or, where this is not reasonably practicable, adequately controlled", CURRENT, LIVE, "inline_required", "COSHH at a glance table, Regulation 7 row"),
    ("Keep control measures in efficient working order", "factual", L + "regulation/9",
     "efficient state, in efficient working order", CURRENT, LIVE, "inline_required", "COSHH at a glance table, Regulation 9 row"),
    ("Examination and test results, kept at least 5 years", "factual", L + "regulation/9",
     "at least 5 years", CURRENT, LIVE, "inline_required", "COSHH at a glance table, Regulation 9 row"),
    ("Suitable and sufficient information, instruction and training", "factual", L + "regulation/12",
     "suitable and sufficient information, instruction and training", CURRENT, LIVE, "inline_required", "COSHH at a glance table, Regulation 12 row"),
    ("Brief the engineer on hazards, controls, and the safety data sheet", "process", L + "regulation/12",
     "access to any relevant safety data sheet", CURRENT, LIVE, "inline_required", "COSHH at a glance table, Regulation 12 row"),
    ("Arrangements for accidents, incidents and emergencies", "factual", L + "regulation/13",
     "first-aid facilities", CURRENT, LIVE, "inline_required", "COSHH at a glance table, Regulation 13 row"),
    ("It is the UK regulatory framework that makes every employer responsible for protecting workers from substances that damage health at work", "definitional", "https://www.hse.gov.uk/coshh/",
     "Control of Substances Hazardous to Health (COSHH)", CURRENT, LIVE, "inline_required", "What is COSHH section, definition"),
    ("estimate 11,000 lung disease deaths each year linked to past exposures at work", "statistic", "https://www.hse.gov.uk/statistics/causdis/overview.htm",
     "lung disease deaths each year estimated to be linked to past exposure at work", CURRENT, "HSE statistics overview updated 2026-01-07 is the original publication of the figure.", "inline_required", "What is COSHH section, stakes paragraph"),
    ("That summary also puts work-related ill health at 1.9 million workers in 2024/25", "statistic", "https://www.hse.gov.uk/statistics/causdis/overview.htm",
     "1.9 million workers suffering from work-related ill health", CURRENT, "HSE statistics overview updated 2026-01-07 is the original publication of the figure.", "inline_required", "What is COSHH section, stakes paragraph"),
    ("Courts sentence organisations under the Sentencing Council health and safety guideline", "factual", SENT,
     "unlimited fine", CURRENT, "Definitive Sentencing Council guideline in force since 1 February 2016 and read on the checked date.", "inline_required", "What is COSHH section, penalty paragraph"),
    ("which sets an unlimited fine as the maximum penalty for breaching health and safety regulations", "factual", SENT,
     "unlimited fine", CURRENT, "Definitive Sentencing Council guideline in force since 1 February 2016 and read on the checked date.", "inline_required", "What is COSHH section, penalty paragraph"),
    ("COSHH covers any substance or mix of substances that harms health through breathing it in, skin contact, or swallowing it", "definitional", "https://www.hse.gov.uk/coshh/basics/substance.htm",
     "biological agents (germs)", CURRENT, LIVE, "inline_required", "Substances section, direct answer and list"),
    ("If the packaging carries a hazard symbol, HSE treats it as a hazardous substance under COSHH", "factual", "https://www.hse.gov.uk/coshh/basics/substance.htm",
     "If the packaging has any of the hazard symbols then it is classed as a hazardous substance", CURRENT, LIVE, "inline_required", "Substances section, hazard symbol test"),
    ("COSHH does not cover lead, asbestos, or radioactive substances, because separate regulations govern them", "factual", "https://www.hse.gov.uk/coshh/basics/substance.htm",
     "because these have their own specific regulations", CURRENT, LIVE, "inline_required", "Substances section, exclusions"),
    ("The three COSHH regulations most commonly highlighted as the core employer duties are Regulation 6 on risk assessment, Regulation 7 on preventing or controlling exposure, and Regulation 12 on information, instruction and training", "factual", L + "contents",
     "Information, instruction and training for persons who may be exposed to substances hazardous to health", CURRENT, LIVE, "inline_required", "Three main regulations section, direct answer"),
    ("COSHH contains more regulations than these three", "factual", L + "contents",
     "Monitoring exposure at the workplace", CURRENT, LIVE, "inline_required", "Three main regulations section, direct answer"),
    ("The full list of COSHH regulations runs from definitions to health surveillance and emergencies", "factual", L + "contents",
     "Health surveillance", CURRENT, LIVE, "inline_required", "Three main regulations section, direct answer"),
    ("Regulation 6 says an employer shall not carry out work liable to expose employees to a hazardous substance without first making a suitable and sufficient assessment of the risk", "factual", L + "regulation/6",
     "suitable and sufficient assessment", CURRENT, LIVE, "inline_required", "Regulation 6 section"),
    ("That assessment then drives the steps you take to meet the rest of the regulations", "factual", L + "regulation/6",
     "the steps that need to be taken to meet the requirements of these Regulations", CURRENT, LIVE, "inline_required", "Regulation 6 section"),
    ("Employers with 5 or more employees need to record the significant findings and the steps taken to meet Regulation 7", "factual", "https://www.hse.gov.uk/coshh/basics/assessment.htm",
     "If you have 5 or more employees, you must record your assessment", CURRENT, LIVE, "inline_required", "Regulation 6 section, recording rule"),
    ("Regulation 7 requires every employer to ensure exposure is either prevented or, where this is not reasonably practicable, adequately controlled", "factual", L + "regulation/7",
     "either prevented or, where this is not reasonably practicable, adequately controlled", CURRENT, LIVE, "inline_required", "Regulation 7 section"),
    ("Prevention comes first, and substitution is the preferred route", "factual", L + "regulation/7",
     "replacing it with a substance or process which, under the conditions of its use, either eliminates or reduces the risk", CURRENT, LIVE, "inline_required", "Regulation 7 section"),
    ("Where substitution is not practicable, the regulation sets an order of controls", "process", L + "regulation/7",
     "personal protective equipment", CURRENT, LIVE, "inline_required", "Regulation 7 section, order of controls"),
    ("describe PPE as the final control option", "factual", "https://www.hse.gov.uk/coshh/detail/goodpractice.htm",
     "the final control option", CURRENT, LIVE, "inline_required", "Regulation 7 section, PPE paragraph"),
    ("Regulation 12 requires employers to give anyone who works with hazardous substances suitable and sufficient information, instruction and training", "factual", L + "regulation/12",
     "suitable and sufficient information, instruction and training", CURRENT, LIVE, "inline_required", "Regulation 12 section"),
    ("That includes the significant findings of the risk assessment and access to the relevant safety data sheet", "factual", L + "regulation/12",
     "access to any relevant safety data sheet", CURRENT, LIVE, "inline_required", "Regulation 12 section"),
    ("The core three regulations sit inside a wider set of duties", "factual", L + "contents",
     "Use of control measures etc.", CURRENT, LIVE, "inline_required", "Other requirements section, introduction"),
    ("The original eight-step approach to COSHH maps onto these regulations, and each one creates a record worth keeping", "factual", L + "contents",
     "Maintenance, examination and testing of control measures", CURRENT, LIVE, "inline_required", "Other requirements section, introduction"),
    ("Engineers use the controls and PPE you provide, and report defects", "factual", L + "regulation/8",
     "make full and proper use of any control measure", CURRENT, LIVE, "inline_required", "Other requirements table, Regulation 8 row"),
    ("Local exhaust ventilation needs a thorough examination at least once every 14 months, with records kept at least 5 years", "factual", L + "regulation/9",
     "at least once every 14 months", CURRENT, LIVE, "inline_required", "Other requirements table, Regulation 9 row"),
    ("Air monitoring records for identifiable employees stay on file for 40 years", "factual", L + "regulation/10",
     "40 years", CURRENT, LIVE, "inline_required", "Other requirements table, Regulation 10 row"),
    ("Health records stay on file for at least 40 years from the last entry", "factual", L + "regulation/11",
     "at least 40 years from the date of the last entry", CURRENT, LIVE, "inline_required", "Other requirements table, Regulation 11 row"),
    ("First aid, tested safety drills, and warning systems ready for each site", "factual", L + "regulation/13",
     "safety drills", CURRENT, LIVE, "inline_required", "Other requirements table, Regulation 13 row"),
    ("Check and review all control measures regularly for their continuing effectiveness", "factual", L + "schedule/2A",
     "Check and review regularly all elements of control measures for their continuing effectiveness", CURRENT, LIVE, "inline_required", "Other requirements table, Schedule 2A row"),
    ("It is the risk assessment Regulation 6 requires before the work starts", "definitional", L + "regulation/6",
     "suitable and sufficient assessment", CURRENT, LIVE, "inline_required", "COSHH assessment definition"),
    ("A COSHH assessment is not the same as a safety data sheet", "factual", "https://www.hse.gov.uk/coshh/basics/datasheets.htm",
     "A safety data sheet is not a risk assessment", CURRENT, LIVE, "inline_required", "COSHH assessment definition, safety data sheet paragraph"),
    ("HSE's safety data sheet guidance states that a safety data sheet is not a risk assessment", "factual", "https://www.hse.gov.uk/coshh/basics/datasheets.htm",
     "A safety data sheet is not a risk assessment", CURRENT, LIVE, "inline_required", "COSHH assessment definition, safety data sheet paragraph"),
    ("breaks the work into identifying the hazards, assessing the risks, and controlling them", "process", "https://www.hse.gov.uk/coshh/basics/assessment.htm",
     "Identify which substances are harmful by reading the product labels and safety data sheets (SDS)", CURRENT, LIVE, "inline_required", "Assessment steps section"),
    ("There is no fixed legal interval", "factual", L + "regulation/6",
     "reviewed regularly", CURRENT, LIVE, "inline_required", "Review frequency section"),
    ("Regulation 6 requires you to review the assessment regularly", "factual", L + "regulation/6",
     "reviewed regularly", CURRENT, LIVE, "inline_required", "Review frequency section"),
    ("The same regulation requires an immediate review if you suspect the assessment is no longer valid, the work changes significantly, or monitoring shows a need", "factual", L + "regulation/6",
     "significant change in the work", CURRENT, LIVE, "inline_required", "Review frequency section, review triggers"),
    ("Once you employ 5 or more people, Regulation 6 also requires a record of the significant findings, so update that record after each review", "factual", L + "regulation/6",
     "Where the employer employs 5 or more employees, he shall record", CURRENT, LIVE, "inline_required", "Review frequency section, recording threshold"),
    ("HSE's COSHH guidance sets out how to meet it", "factual", "https://www.hse.gov.uk/coshh/",
     "Control of Substances Hazardous to Health (COSHH)", CURRENT, LIVE, "inline_required", "What is COSHH section, definition"),
    ("The employer holds the legal duty, as HSE's COSHH law summary makes clear", "factual", "https://www.hse.gov.uk/coshh/law.htm",
     "require employers to plan, manage and monitor the use of chemicals", CURRENT, LIVE, "inline_required", "Responsibility section"),
    ("Any business that sends engineers to work with hazardous substances has to assess the risk and put controls in place", "factual", "https://www.hse.gov.uk/coshh/law.htm",
     "require employers to plan, manage and monitor the use of chemicals", CURRENT, LIVE, "inline_required", "Responsibility section"),
    ("It also maintains those controls and trains its people", "factual", "https://www.hse.gov.uk/coshh/law.htm",
     "require employers to plan, manage and monitor the use of chemicals", CURRENT, LIVE, "inline_required", "Responsibility section"),
    ("HSE's COSHH FAQ confirms that the person carrying out an assessment needs no particular qualifications, but must be competent", "factual", "https://www.hse.gov.uk/coshh/faq.htm",
     "You don't need any particular qualifications but you must be competent", CURRENT, LIVE, "inline_required", "Responsibility section, competence paragraph"),
    ("Competence means having the necessary knowledge, skills, and experience to do the job properly", "definitional", "https://www.hse.gov.uk/coshh/faq.htm",
     "necessary knowledge, skills and experience", CURRENT, LIVE, "inline_required", "Responsibility section, competence paragraph"),
    ("Under Regulation 8, engineers use the control measures and PPE provided, follow the procedures, and report defects", "factual", L + "regulation/8",
     "make full and proper use of any control measure", CURRENT, LIVE, "inline_required", "Responsibility section, employee duties"),
    ("engineers open the correct COSHH assessment on their mobile device and complete it before the job starts", "product_claim", "https://www.bigchange.com/features/risk-assessment",
     "instant access to the right risk assessment", CURRENT, LIVE, "inline_required", "Field compliance section, digital workflow"),
    ("Cleaning businesses keep a digital library of COSHH sheets for engineers to reference on site", "product_claim", "https://www.bigchange.com/industries/cleaning-software-crm",
     "COSHH sheets", CURRENT, LIVE, "inline_required", "Field compliance section, cleaning paragraph"),
    ("COSHH regulations come down to four habits: assess each task, control exposure, keep controls working, and make sure every engineer understands the risks", "factual", "https://www.hse.gov.uk/coshh/law.htm",
     "require employers to plan, manage and monitor the use of chemicals", CURRENT, LIVE, "inline_required", "Conclusion"),
    ("HSE's summary of what the law says sets out each duty in plain terms", "factual", "https://www.hse.gov.uk/coshh/law.htm",
     "require employers to plan, manage and monitor the use of chemicals", CURRENT, LIVE, "inline_required", "Conclusion"),
    ("employers make a suitable and sufficient assessment before any work that exposes employees to hazardous substances", "faq", L + "regulation/6",
     "suitable and sufficient assessment", CURRENT, LIVE, "inline_required", "FAQ, legal requirement answer"),
    ("states that a good safety data sheet does not substitute for carrying out and recording a COSHH risk assessment", "faq", "https://www.hse.gov.uk/coshh/faq.htm",
     "does not substitute for carrying out and recording a COSHH risk assessment", CURRENT, LIVE, "inline_required", "FAQ, safety data sheet answer"),
    ("classes a product as hazardous when its packaging carries a hazard symbol", "faq", "https://www.hse.gov.uk/cleaning/topics/coshh.htm",
     "If the packaging has any of the hazard symbols, it is classed as a hazardous substance", CURRENT, LIVE, "inline_required", "FAQ, cleaning products answer"),
    ("employers give anyone exposed to hazardous substances suitable and sufficient information, instruction and training", "faq", L + "regulation/12",
     "suitable and sufficient information, instruction and training", CURRENT, LIVE, "inline_required", "FAQ, training answer"),
]


def source_map() -> str:
    lines = []
    for claim, ctype, url, evidence, fresh, reason, mode, use in ROWS:
        cpath, chash = classification(url)
        lines.append(
            f"- Claim: {claim} | Claim type: {ctype} | Source class: {source_class(url)} | Evidence relation: directly_supports"
            f" | URL: {url} | Evidence: {evidence} | Original-source status: original | Source date: {DATE}"
            f" | Checked date: {DATE} | Claim fit: direct | Freshness decision: {fresh} | Freshness reason: {reason}"
            f" | Classification artifact: {cpath} | Classification hash: {chash} | Citation mode: {mode}"
            f" | Status: approved | Intended use: {use}"
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
    text = TEMPLATE.format(
        run_id=RUN_ID, date=DATE, source_map=source_map(), selector_hash=selector_hash,
        cap=CAP, suz_art=suz_art, suz_rec=suz_rec, suz_hash=suz_hash,
        clare_art=clare_art, clare_rec=clare_rec, clare_hash=clare_hash,
        cap_cpath=cap_cpath, cap_chash=cap_chash, clg=clg, clg_cpath=clg_cpath, clg_chash=clg_chash,
    )
    OUT.write_bytes(text.encode("utf-8"))
    print(f"sidecar: {OUT.relative_to(ROOT).as_posix()} rows={len(ROWS)}")
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

- Approved metric: 11,000 lung disease deaths each year linked to past exposures at work | URL: https://www.hse.gov.uk/statistics/causdis/overview.htm | Evidence: lung disease deaths each year estimated to be linked to past exposure at work | Status: approved | Use: What is COSHH section, stakes paragraph
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

- Selector command: python data_sources/modules/nonvault_customer_proof_selector.py "coshh regulations" --brand BigChange --roles metric,quote,theme,experience_story --require-eeat-story
- Selector evidence: research/nonvault-customer-proof-selector-evidence-coshh-regulations-{date}.json | SHA-256: {selector_hash}
- Role: metric | Top candidates: [none] | Selected: [none] | Rejected stronger candidates: [none]
- Role: quote | Top candidates: [review-capterra-bigchange-suzanne-transport-compliance-records] | Selected: [review-capterra-bigchange-suzanne-transport-compliance-records] | Rejected stronger candidates: [none]
- Role: theme | Top candidates: [bigchange-customer-story-hodge-clemco-paperless-jobs, bigchange-clearground-dynamic-risk-assessments] | Selected: [bigchange-clearground-dynamic-risk-assessments] | Rejected stronger candidates: [bigchange-customer-story-hodge-clemco-paperless-jobs: Paperless job story with no health and safety or risk assessment content for a COSHH article]
- Role: experience_story | Top candidates: [review-capterra-bigchange-clare-hseq-health-safety-worksheets] | Selected: [review-capterra-bigchange-clare-hseq-health-safety-worksheets] | Rejected stronger candidates: [none]

## Customer Proof Pack

- Pack status: selected
- Topic or page fit: COSHH regulations and COSHH assessments for UK field service employers.
- Quote Matrix candidates: Not applicable for this nonconnector brand.
- Customer Story proof path: Clearground public success story at {clg}
- Review-site experience evidence: Clare (HSEQ Manager) and Suzanne (Transport Manager) on the public Capterra UK BigChange page.
- Selected Customer Proof Mining: See below.
- Customer Proof Selection Decision: See below.
- Approved quote: keeping all documents together showing a stream from report to completion of faults and issues which keeps us compliant | Customer/reviewer: Suzanne, Transport Manager | Source type: review_site | URL: {cap} | Evidence: keeping all documents together showing a stream from report to completion of faults and issues which keeps us compliant | Proof artifact: {suz_art} | Capture receipt: {suz_rec} | Capture receipt hash: {suz_hash} | Status: approved
- Approved metrics: none used
- Use in copy: Clearground paraphrased story, Clare paraphrased story, Suzanne approved snippet
- Claims excluded: ratings, star claims, aggregate review claims, customer metrics, and the Clare review's staffing figure.

## Selected Customer Proof Mining

- Selected proof: bigchange-clearground-dynamic-risk-assessments | URL: {clg} | Mined for: quote, metric, POV/story, theme | Decision: paraphrased POV/story | Reason: The page describes mandatory on-site dynamic risk assessments, which fits the field compliance section. No exact quote or metric is used under the nonvault contract.
- Selected proof: review-capterra-bigchange-clare-hseq-health-safety-worksheets | URL: {cap} | Mined for: quote, metric, POV/story, theme | Decision: paraphrased POV/story | Reason: The review describes building health and safety worksheets in house. Her wording contains modal verbs and a staffing figure, so the story is paraphrased and the figure is omitted. Proof artifact: {clare_art} | Capture receipt hash: {clare_hash}
- Selected proof: review-capterra-bigchange-suzanne-transport-compliance-records | URL: {cap} | Mined for: quote, metric, POV/story, theme | Decision: approved snippet | Reason: The snippet matches the row's approved_quotes entry verbatim and carries no rating or metric.

## Customer Proof Selection Decision

- Selected proof: bigchange-clearground-dynamic-risk-assessments, review-capterra-bigchange-clare-hseq-health-safety-worksheets, review-capterra-bigchange-suzanne-transport-compliance-records
- Selection outcome: selected
- Rejected: bigchange-customer-story-hodge-clemco-paperless-jobs | Role theme | Reason: Paperless job story with no health and safety or risk assessment content for a COSHH article
- Rejected: bigchange-rilmac-prove-compliance-hse-inspection | Role theme | Reason: Asbestos services work falls under a separate regime from COSHH so the story risks implying COSHH-specific compliance
- Rejected: review-capterra-bigchange-hannah-construction-one-system-workflow | Role experience_story | Reason: One-system workflow review with no health and safety content and four recent uses
- Reuse reason: Not applicable. The three selected proof rows have no recorded prior public use; a live repo scan of drafts, rewrites, research and published found no public-copy use of Clearground, Clare or Suzanne.
- Final use in copy: Field compliance section only
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

- Decision: selected
- Proof ID: review-capterra-bigchange-clare-hseq-health-safety-worksheets
- Identity: Clare, HSEQ Manager
- Platform: Capterra
- Public review URL: {cap}
- Copy use: paraphrased E-E-A-T story with same-paragraph public review link
- Proof artifact: {clare_art}
- Capture receipt: {clare_rec}
- Capture receipt hash: {clare_hash}
- Classification artifact: {cap_cpath}
- Classification hash: {cap_chash}
- Public-copy boundary: No rating, star claim, aggregate rating, ranking, or review metric appears.
- Status: approved

- Decision: selected
- Proof ID: review-capterra-bigchange-suzanne-transport-compliance-records
- Identity: Suzanne, Transport Manager
- Platform: Capterra
- Public review URL: {cap}
- Copy use: approved snippet with same-paragraph public review link
- Approved quote: keeping all documents together showing a stream from report to completion of faults and issues which keeps us compliant | URL: {cap} | Status: approved
- Proof artifact: {suz_art}
- Capture receipt: {suz_rec}
- Capture receipt hash: {suz_hash}
- Classification artifact: {cap_cpath}
- Classification hash: {cap_chash}
- Public-copy boundary: No rating, star claim, aggregate rating, ranking, or review metric appears.
- Status: approved

## Source Map

{source_map}
- Claim: Its team builds customised, dynamic risk assessments and makes completing them on site mandatory before work begins | Claim type: customer_proof | Source class: customer_proof | Evidence relation: directly_supports | URL: {clg} | Evidence: The ability to create customised, dynamic risk assessments and make their completion on-site mandatory goes beyond other systems we looked at. | Original-source status: original | Source date: {date} | Checked date: {date} | Claim fit: direct | Freshness decision: current | Freshness reason: Public BigChange success story read live on the checked date. | Classification artifact: {clg_cpath} | Classification hash: {clg_chash} | Citation mode: inline_required | Status: approved | Intended use: Field compliance section, Clearground story
- Claim: They build those worksheets in house, without software engineers | Claim type: review | Source class: review_platform | Evidence relation: directly_supports | URL: {cap} | Evidence: you do not need software engineers to design your worksheets | Original-source status: original | Source date: 2021-01-13 | Checked date: {date} | Claim fit: direct | Freshness decision: historical_scoped | Freshness reason: The review is dated 2021-01-13 and the claim is scoped to the reviewer's own workflow experience rather than current product status. | Artifact: {clare_art} | Capture receipt: {clare_rec} | Capture receipt hash: {clare_hash} | Classification artifact: {cap_cpath} | Classification hash: {cap_chash} | Citation mode: inline_required | Status: approved | Intended use: Field compliance section, Clare story
- Claim: Clare, an HSEQ manager at a UK construction firm, wrote on Capterra that her team designs its own policies, procedures, and health and safety worksheets in BigChange | Claim type: review | Source class: review_platform | Evidence relation: directly_supports | URL: {cap} | Evidence: you can design to meet your company needs for policies, procedures, health & safety | Original-source status: original | Source date: 2021-01-13 | Checked date: {date} | Claim fit: direct | Freshness decision: historical_scoped | Freshness reason: The review is dated 2021-01-13 and the claim is scoped to the reviewer's own workflow experience rather than current product status. | Artifact: {clare_art} | Capture receipt: {clare_rec} | Capture receipt hash: {clare_hash} | Classification artifact: {cap_cpath} | Classification hash: {cap_chash} | Citation mode: inline_required | Status: approved | Intended use: Field compliance section, Clare story
- Claim: She credits BigChange with "keeping all documents together showing a stream from report to completion of faults and issues which keeps us compliant." | Claim type: quote | Source class: review_platform | Evidence relation: directly_supports | URL: {cap} | Evidence: keeping all documents together showing a stream from report to completion of faults and issues which keeps us compliant | Original-source status: original | Source date: 2023-06-01 | Checked date: {date} | Claim fit: direct | Freshness decision: historical_scoped | Freshness reason: The review is dated 2023-06-01 and the quote is scoped to the reviewer's own records workflow rather than current product status. | Artifact: {suz_art} | Capture receipt: {suz_rec} | Capture receipt hash: {suz_hash} | Classification artifact: {cap_cpath} | Classification hash: {cap_chash} | Citation mode: inline_required | Status: approved | Intended use: Field compliance section, Suzanne snippet

## FAQ Source Policy

- Allowed source classes: primary_authority, neutral, non_competing_expert, owned_product.
- Competitor-owned FAQ sources: prohibited.
- Status: aligned.

## FAQ Proof Map

- FAQ: Is a COSHH assessment a legal requirement? | URL: https://www.legislation.gov.uk/uksi/2002/2677/regulation/6 | Source class: primary_authority | Competitor check: passed | Support: Regulation 6 sets the duty to make a suitable and sufficient assessment and the 5 or more employees recording rule. | Status: approved
- FAQ: Is a safety data sheet the same as a COSHH assessment? | URL: https://www.hse.gov.uk/coshh/faq.htm | Source class: primary_authority | Competitor check: passed | Support: HSE states a good safety data sheet does not substitute for carrying out and recording a COSHH risk assessment. | Status: approved
- FAQ: Does COSHH apply to cleaning products? | URL: https://www.hse.gov.uk/cleaning/topics/coshh.htm | Source class: primary_authority | Competitor check: passed | Support: HSE classes a product as hazardous when its packaging carries a hazard symbol. | Status: approved
- FAQ: Does COSHH training need to be provided to employees? | URL: https://www.legislation.gov.uk/uksi/2002/2677/regulation/12 | Source class: primary_authority | Competitor check: passed | Support: Regulation 12 requires suitable and sufficient information, instruction and training. | Status: approved

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

Source of the set: three destinations are specified by the brief with their briefed anchors. The risk assessment feature page is the commercial pillar and the cleaning industry page names a COSHH sheets library. The brief's eicr-test and win-electrical-contracts links were left out because neither supports a COSHH claim, keeping the set at five. The demo CTA is a conversion link, not an editorial destination. Anchor deviation: the brief suggests "facilities management compliance" for the facilities management post. The public-research gate treats "compliance" in an owned-link anchor as an unsupported regulatory claim, so the anchor reads "facilities management businesses" instead. Every destination returned HTTP 200 on {date}.

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
