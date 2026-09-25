"""Validation sidecar text for the workplace risk assessment rewrite."""

from __future__ import annotations

from scripts.workplace_risk_assessment_common import DATE, ROOT, SLUG, sha256


def build_sidecar() -> str:
    selector = ROOT / "research" / f"nonvault-customer-proof-selector-evidence-{SLUG}-{DATE}.json"
    pillar = ROOT / "context" / "commercial-pillar-index.json"
    proof_index = ROOT / "context" / "customer-proof-index.json"
    ledger = ROOT / "context" / "customer-proof-usage-ledger.json"
    return f"""# Validation sidecar: workplace risk assessment

Date: {DATE}
Article: `rewrites/{SLUG}-rewrite-{DATE}.md`
Workflow mode: rewrite

## Context Binding

- Decision: nonconnector
- Brand: BigChange
- Market: UK
- Reason: The final artifact is BigChange-owned and contains no Simpro signal.
- Vault context request, context pack, context receipt, Fred authority evidence and vault-dependent customer-proof evidence: omitted by policy.
- Status: aligned

## Release Status

- Article word target: 2,200 to 2,500 words.
- Canonical URL: https://www.bigchange.com/blog/how-to-conduct-a-workplace-risk-assessment
- Named author: none supplied. Public frontmatter omits `author`; schema notes omit `Person as author`.
- Displayed update date: {DATE}.
- Publication date retained separately as 2021-11-19.
- Status: pending deterministic release gates.

## Semrush UI Keyword Evidence

- Source: user-approved UK desktop Semrush UI evidence dated {DATE}.
- Primary: workplace risk assessment, volume 720, KD 33.
- Plural variation: workplace risk assessments, volume 590, KD 29.
- Definition target: what is a risk assessment, volume 4,400, KD 27.
- Example target: risk assessment example, volume 1,900, KD 22.
- Semantic support: risk assessment meaning, volume 1,300, KD 60.
- Commercial-pillar query: risk assessment software, volume 1,300, KD 19.
- Keyword decision: `research/semrush-keyword-decision-{SLUG}-{DATE}.json`.

## SERP Evidence

- Query: `workplace risk assessment`.
- Market/device: United Kingdom desktop.
- Collector: `research_serp_analysis:chrome_connector`.
- Raw capture: `research/serp-chrome-raw-workplace-risk-assessment-{DATE}.json`.
- Evidence: `research/serp-evidence-workplace-risk-assessment-{DATE}.json`.
- Observed pattern: HSE and Acas guidance lead the visible organic results; the page also shows an AI Overview, a five-step answer pattern and an HSE template result.
- Editorial use: immediate definition, early five-step checklist, current UK requirements, a worked example and reusable record-and-review workflow.
- Status: verified.

## Commercial Strategy

- Destination ID: `bigchange-uk-feature-risk-assessment-software`.
- URL: https://www.bigchange.com/features/risk-assessment
- Article intent: informational process guide.
- Destination intent: risk-assessment software feature page.
- Planned H2: `How to make workplace risk assessments easier to manage`.
- Required contiguous anchor: `risk assessment software`.
- Commercial-pillar index SHA-256: `{sha256(pillar)}`.
- Status: aligned.

## Non-Vault Proof Eligibility Decision

- Contract: `simpro-nonvault-customer-proof-selector-evidence/v1`.
- Evidence: `research/nonvault-customer-proof-selector-evidence-{SLUG}-{DATE}.json`.
- Evidence SHA-256: `{sha256(selector)}`.
- Customer-proof index SHA-256: `{sha256(proof_index)}`.
- Usage-ledger SHA-256: `{sha256(ledger)}`.
- Result: Clearground is approved for a paraphrased same-paragraph customer-story use.

## Customer Proof Slate

- Selector command: `python data_sources/modules/nonvault_customer_proof_selector.py "workplace risk assessment" --brand BigChange --title "Workplace Risk Assessment: How to Identify, Control and Record Risks in 5 Steps" --objective "Help UK service-business managers carry out, record, and review a practical workplace risk assessment, then show how digital risk-assessment software can keep the process inside the job workflow." --article-slug "how-to-conduct-a-workplace-risk-assessment" --roles metric,quote,theme,experience_story --require-eeat-story --selected "theme=bigchange-customer-story-clearground-dynamic-risk-assessments" --selected "experience_story=bigchange-customer-story-clearground-dynamic-risk-assessments" --limit 10 --reference-date 2026-09-25 --slate --evidence-output research/nonvault-customer-proof-selector-evidence-workplace-risk-assessment-2026-09-25.json`.
- Selector evidence: research/nonvault-customer-proof-selector-evidence-{SLUG}-{DATE}.json | SHA-256: {sha256(selector)}
- Role: metric | Top candidates: [none] | Selected: [none] | Rejected stronger candidates: [none]
- Role: quote | Top candidates: [none] | Selected: [none] | Rejected stronger candidates: [none]
- Role: theme | Top candidates: [bigchange-customer-story-clearground-dynamic-risk-assessments, bigchange-customer-story-hodge-clemco-paperless-jobs, review-capterra-bigchange-hannah-construction-one-system-workflow, bigchange-customer-story-htf-transport-job-scheduling, bigchange-customer-story-precision-fm-scheduling-sla, bigchange-customer-story-warmzilla-digital-job-sheet-lifecycle, bigchange-customer-story-blackhall-plumbing-job-lifecycle, bigchange-customer-story-cc-is-paperless-job-cards, bigchange-customer-story-trents-drains-digital-job-cards, review-capterra-bigchange-alexina-office-manager-job-lifecycle] | Selected: [bigchange-customer-story-clearground-dynamic-risk-assessments] | Rejected stronger candidates: [none]
- Role: experience_story | Top candidates: [bigchange-customer-story-clearground-dynamic-risk-assessments, review-capterra-bigchange-hannah-construction-one-system-workflow, bigchange-customer-story-warmzilla-digital-job-sheet-lifecycle, bigchange-customer-story-cc-is-paperless-job-cards, bigchange-customer-story-trents-drains-digital-job-cards, review-capterra-bigchange-alexina-office-manager-job-lifecycle] | Selected: [bigchange-customer-story-clearground-dynamic-risk-assessments] | Rejected stronger candidates: [none]

## Customer Proof Selection Decision

- Selector command: the hash-bound non-vault selector command recorded in Customer Proof Slate.
- Selected proof: `bigchange-customer-story-clearground-dynamic-risk-assessments` | Roles: theme, experience_story.
- Rejected stronger candidates: [none; Clearground is the selector's top-ranked candidate for both selected roles].
- Evaluated alternatives: Mardon was weaker because its strongest proof concerns vehicle checks and safety reporting; CC Infrastructure Services concerns paperless job cards and photographic records; GEM concerns compliance records and asset information; approved Capterra stories have recent repository use and weaker risk-assessment fit.
- Final use in copy: one restrained, same-paragraph paraphrase in `How to make workplace risk assessments easier to manage`.

## Selected Customer Proof Mining

- Proof: bigchange-customer-story-clearground-dynamic-risk-assessments | URL: https://www.bigchange.com/success-stories/bigchange-helps-clearground-clean-up-on-workforce-health-and-safety
- Source: https://www.bigchange.com/success-stories/bigchange-helps-clearground-clean-up-on-workforce-health-and-safety
- Checked: {DATE}.
- Checked for: exact quotes, metrics, customer POV or story, workflow theme, and measured outcomes.
- Usable quotes found: none used because the article does not need testimonial wording.
- Usable metrics found: none found for the selected workflow claim.
- Usable POV/story found: Clearground uses customised dynamic risk assessments which operatives complete on site before work.
- Recommended use: restrained paraphrase of the point-of-work workflow with a same-paragraph source link.
- Final use in copy: paraphrased experience story in `How to make workplace risk assessments easier to manage`.
- Excluded proof: exact customer quote, named-person attribution, metric, certification claim, comparison and measured safety outcome were excluded because they do not improve this section's practical workflow explanation.
- Status: approved

## Customer Proof Pack

- Proof ID: `bigchange-customer-story-clearground-dynamic-risk-assessments`.
- Customer: Clearground.
- URL: https://www.bigchange.com/success-stories/bigchange-helps-clearground-clean-up-on-workforce-health-and-safety
- Approved use: paraphrased point-of-work experience story only.
- Evidence: The public story describes customised dynamic risk assessments which operatives complete on site before work.
- Status: approved.

## Review Site Theme Selection

- Capterra page checked: https://www.capterra.com/p/149479/JobWatch-powered-by-BigChange/reviews/
- Research boundary: relevant four- and five-score snippets were reviewed as private audience language only.
- Public use: none.
- Reason: live snippets are not approved proof rows; approved Capterra stories are repeatedly used and weaker topical matches.
- Prohibited: ratings, aggregate score, exact snippet, named review claim and implied risk-assessment outcome.

## Video Review Decision

- Source: https://www.youtube.com/watch?v=_YXifF-nLxA
- Checked: {DATE}.
- Decision: reject embed.
- Reason: published in 2019 and no usable transcript or captions were available for claim verification.
- `VideoObject`: omitted because no video is embedded.

## Source Map

- Claim: The British Safety Council's risk assessment certificate specification frames the process around identifying, evaluating and controlling risks. In day-to-day service work, look beyond a standard job description. Access, equipment, other contractors, customers and changing site conditions all shape how the team performs the work. | Claim type: definitional | URL: https://www.britsafe.org/media/ddyfkihf/british-safety-council-certificate-in-risk-assessment.pdf | Evidence: identifying hazards, evaluating risks, and controlling risks | Evidence relation: directly_supports | Source class: non_competing_expert | Classification artifact: research/source-classifications/workplace-risk-assessment/source-classification-20a68a13abaab13c25ec1a7ce12532191166c91e1cc7e1b74e4fe7d7c3c42f3e.json | Classification hash: c7de304d8bd4e8c24254058ae7805283228bdc6b8bc2e5b19642809e272bd11d | Original-source status: original | Source date: historical | Checked date: {DATE} | Claim fit: direct | Freshness decision: historical_scoped | Freshness reason: The 2020 certificate specification supports stable process terminology while current legal claims remain sourced to HSE | Status: approved | Intended use: definition section
- Claim: Under the Health and Safety Executive's risk-management guidance, UK employers and self-employed people have a duty to assess risks created by their work and take suitable steps to control them. Its scope needs to be proportionate to the work and good enough to protect people from foreseeable harm. For an organisation with five or more people, the significant findings belong in a written record. | Claim type: regulation | URL: https://www.hse.gov.uk/simple-health-safety/risk/steps-needed-to-manage-risk.htm | Evidence: If you employ 5 or more people, you must record your significant findings | Source class: regulator | Original-source status: original | Source date: 2024-06-10 | Checked date: {DATE} | Claim fit: direct | Freshness decision: current | Freshness reason: HSE updated the live guidance on 2024-06-10 and it was checked on the article update date | Status: approved | Intended use: legal requirements
- Claim: The employer remains responsible for managing health and safety. The employer, a competent worker or an external adviser completes the assessment. That person's skills, knowledge and experience cover the relevant hazards, risk judgements and suitable controls. The actual task and conditions, not the job title alone, determine the competence required. | Claim type: regulation | URL: https://www.hse.gov.uk/simple-health-safety/gettinghelp/ | Evidence: They should have the skills, knowledge and experience to be able to recognise hazards in your business | Source class: regulator | Original-source status: original | Source date: 2024-06-04 | Checked date: {DATE} | Claim fit: direct | Freshness decision: current | Freshness reason: HSE updated the live guidance on 2024-06-04 and it was checked on the article update date | Status: approved | Intended use: competent-person section
- Claim: HSE guidance on appointing a competent person permits an employer to appoint themselves, one or more workers, or somebody from outside the business. Where suitable competence exists internally, HSE says to use it. Outside advice suits complex, unusual or high-risk work, but outsourcing the task does not transfer the employer's legal duty. | Claim type: regulation | URL: https://www.hse.gov.uk/simple-health-safety/gettinghelp/ | Evidence: But remember, as the employer, managing health and safety will still be your legal duty. | Source class: regulator | Original-source status: original | Source date: 2024-06-04 | Checked date: {DATE} | Claim fit: direct | Freshness decision: current | Freshness reason: HSE updated the live guidance on 2024-06-04 and it was checked on the article update date | Status: approved | Intended use: competent-person section
- Claim: Consider both likelihood and severity, taking existing precautions into account. Address the most serious risks first. The HSE five-step process advises redesigning the job, replacing materials, machinery or processes, organising work to limit exposure, introducing practical safety measures and using personal protective equipment when further controls apply. | Claim type: process | URL: https://www.hse.gov.uk/simple-health-safety/risk/steps-needed-to-manage-risk.htm | Evidence: If you need further controls, consider: redesigning the job, replacing the materials, machinery or process | Evidence relation: directly_supports | Source class: primary_authority | Classification artifact: research/source-classifications/workplace-risk-assessment/source-classification-bb64f0b75e50e538aa268d2160e5d749e12c48f0b966fa56ebb52f5a3170e276.json | Classification hash: 1b2414db4db730cd5cb38b8651f2e103f07948afeeda59e4797c59a63f5d513c | Original-source status: original | Source date: 2024-06-10 | Checked date: {DATE} | Claim fit: direct | Freshness decision: current | Freshness reason: HSE updated the live guidance on 2024-06-10 and it was checked on the article update date | Status: approved | Intended use: evaluate-risk step
- Claim: Use the fields in the HSE risk assessment template: significant hazards, affected groups, existing controls and further actions. Give every further action an owner and a deadline. If the job cannot proceed until the action is complete, make that stop condition explicit. A risk assessment that identifies a problem but leaves it unowned has not controlled the risk. | Claim type: process | URL: https://www.hse.gov.uk/simple-health-safety/risk/risk-assessment-template-and-examples.htm | Evidence: what further action you need to take to control the risks, who needs to carry out the action, when the action is needed by | Evidence relation: directly_supports | Source class: primary_authority | Classification artifact: research/source-classifications/workplace-risk-assessment/source-classification-dfae287164e5bd9a49d8a289fe5a1f78741f751c6a5d9e8479bdedf7fc8a7cfc.json | Classification hash: a4fa110402e079b778437bb7c315f9400cef98d795b937ea04dbe86fe4399b4b | Original-source status: original | Source date: 2024-06-10 | Checked date: {DATE} | Claim fit: direct | Freshness decision: current | Freshness reason: HSE updated the live guidance on 2024-06-10 and it was checked on the article update date | Status: approved | Intended use: recording step
- Claim: For ladder safety, the HSE ladder guidance says ladders are not automatically the first choice and sets out the right ladder and sensible precautions. When task duration, height or environment changes, reassess the equipment and controls. | Claim type: process | URL: https://www.hse.gov.uk/work-at-height/ladders/index.htm | Evidence: they should not automatically be your first choice. There are simple, sensible precautions you should take | Evidence relation: directly_supports | Source class: primary_authority | Classification artifact: research/source-classifications/workplace-risk-assessment/source-classification-38572b8f8da35c4763b3cb042056c56833f77690964a995817572360dcdb859a.json | Classification hash: 394196a6edef86ff8b01f8d2b66fa3a8e47a05361c060daf5e63ac2dad1e01f2 | Original-source status: original | Source date: 2024-06-05 | Checked date: {DATE} | Claim fit: direct | Freshness decision: current | Freshness reason: HSE updated the live guidance on 2024-06-05 and it was checked on the article update date | Status: approved | Intended use: worked example qualification
- Claim: What should a workplace risk assessment include? The HSE says you can use its risk assessment template to keep a simple record of who might be harmed and how. | Claim type: recommendation | URL: https://www.hse.gov.uk/simple-health-safety/risk/risk-assessment-template-and-examples.htm | Evidence: You can use a risk assessment template to help you keep a simple record of: who might be harmed and how | Evidence relation: directly_supports | Source class: primary_authority | Classification artifact: research/source-classifications/workplace-risk-assessment/source-classification-dfae287164e5bd9a49d8a289fe5a1f78741f751c6a5d9e8479bdedf7fc8a7cfc.json | Classification hash: a4fa110402e079b778437bb7c315f9400cef98d795b937ea04dbe86fe4399b4b | Original-source status: original | Source date: undated | Checked date: {DATE} | Claim fit: direct | Freshness decision: historical_scoped | Freshness reason: The live HSE guidance is undated and was checked on the article update date | Status: approved | Intended use: direct answer box
- Claim: A workplace risk assessment is a systematic way to identify hazards, identify the people at risk, judge the risk level and select controls. Its purpose is practical action. The work isn't complete simply because somebody filled in a form or selected a risk score. It turns observation into a clear work decision. | Claim type: process | URL: https://www.hse.gov.uk/simple-health-safety/risk/steps-needed-to-manage-risk.htm | Evidence: Risk management is a step-by-step process for controlling health and safety risks caused by hazards in the workplace. | Source class: primary_authority | Original-source status: original | Source date: 2024-06-10 | Checked date: {DATE} | Claim fit: direct | Freshness decision: current | Freshness reason: HSE updated the live guidance on 2024-06-10 and it was checked on the article update date | Status: approved | Intended use: definition section
- Claim: The British Safety Council's risk assessment certificate specification frames the process around identifying, evaluating and controlling risks. In day-to-day service work, that means looking beyond a standard job description. Access, equipment, other contractors, customers and changing site conditions all shape how the team performs the work. | Claim type: definitional | URL: https://www.britsafe.org/media/ddyfkihf/british-safety-council-certificate-in-risk-assessment.pdf | Evidence: The specification lists identifying, evaluating and controlling risks as learning outcomes | Source class: non_competing_expert | Original-source status: original | Source date: historical | Checked date: {DATE} | Claim fit: direct | Freshness decision: historical_scoped | Freshness reason: The 2020 certificate specification supports stable process terminology while current legal claims remain sourced to HSE | Status: approved | Intended use: definition section
- Claim: A hazard is something with the potential to cause harm. Risk combines the likelihood of harm with the outcome's possible severity. Keeping these ideas separate makes an assessment more useful because the hazard tells you what to examine, while the risk helps you prioritise action. Controls break that chain before harm occurs. | Claim type: definitional | URL: https://www.hse.gov.uk/simple-health-safety/risk/steps-needed-to-manage-risk.htm | Evidence: decide how likely it is that someone could be harmed and how serious it could be | Source class: primary_authority | Original-source status: original | Source date: undated | Checked date: {DATE} | Claim fit: direct | Freshness decision: historical_scoped | Freshness reason: The live HSE guidance is undated and was checked on the article update date | Status: approved | Intended use: hazard and risk comparison
- Claim: Under the Health and Safety Executive's risk-management guidance, UK employers and self-employed people must assess risks created by their work and take suitable steps to control them. Its scope needs to be proportionate to the work and good enough to protect people from foreseeable harm. If the organisation employs five or more people, it must record its significant findings. | Claim type: regulation | URL: https://www.hse.gov.uk/simple-health-safety/risk/steps-needed-to-manage-risk.htm | Evidence: If you employ 5 or more people, you must record your significant findings | Source class: regulator | Original-source status: original | Source date: undated | Checked date: {DATE} | Claim fit: direct | Freshness decision: historical_scoped | Freshness reason: The live HSE guidance is undated and was checked on the article update date | Status: approved | Intended use: legal requirements
- Claim: The Health and Safety Executive's risk-management guidance says the record covers the hazards, the people at risk and what the business is doing to control the risks. The priority remains controlling the risk in practice, not producing paperwork for its own sake. | Claim type: process | URL: https://www.hse.gov.uk/simple-health-safety/risk/steps-needed-to-manage-risk.htm | Evidence: Do not rely purely on paperwork as your main priority should be to control the risks in practice. | Source class: primary_authority | Original-source status: original | Source date: undated | Checked date: {DATE} | Claim fit: direct | Freshness decision: historical_scoped | Freshness reason: The live HSE guidance is undated and was checked on the article update date | Status: approved | Intended use: legal requirements
- Claim: The employer remains responsible for managing health and safety. The employer, a competent worker or an external adviser completes the assessment. That person needs enough skills, knowledge and experience to recognise the relevant hazards, judge the risks and recommend controls that fit the work. Competence must match the actual task and conditions. | Claim type: regulation | URL: https://www.hse.gov.uk/simple-health-safety/gettinghelp/ | Evidence: They should have the skills, knowledge and experience to be able to recognise hazards in your business | Source class: regulator | Original-source status: original | Source date: undated | Checked date: {DATE} | Claim fit: direct | Freshness decision: historical_scoped | Freshness reason: The live HSE guidance is undated and was checked on the article update date | Status: approved | Intended use: competent-person section
- Claim: HSE guidance on appointing a competent person permits an employer to appoint themselves, one or more workers, or somebody from outside the business. Where suitable competence exists internally, HSE recommends using it. External help suits complex, unusual or high-risk work, but outsourcing the task does not transfer the employer's legal duty. | Claim type: regulation | URL: https://www.hse.gov.uk/simple-health-safety/gettinghelp/ | Evidence: But remember, as the employer, managing health and safety will still be your legal duty. | Source class: regulator | Original-source status: original | Source date: undated | Checked date: {DATE} | Claim fit: direct | Freshness decision: historical_scoped | Freshness reason: The live HSE guidance is undated and was checked on the article update date | Status: approved | Intended use: competent-person section
- Claim: Consider both likelihood and severity, taking existing precautions into account. Address the most serious risks first. The HSE five-step process advises redesigning the job, replacing materials, machinery or processes, organising work to reduce exposure, introducing practical safety measures and using personal protective equipment when further controls apply. | Claim type: process | URL: https://www.hse.gov.uk/simple-health-safety/risk/steps-needed-to-manage-risk.htm | Evidence: If you need further controls, consider: | Source class: primary_authority | Original-source status: original | Source date: undated | Checked date: {DATE} | Claim fit: direct | Freshness decision: historical_scoped | Freshness reason: The live HSE guidance is undated and was checked on the article update date | Status: approved | Intended use: evaluate-risk step
- Claim: The HSE risk assessment template records the significant hazards, affected groups, existing controls and further actions. Give every further action an owner and a deadline. If the job cannot proceed until the action is complete, make that stop condition explicit. A risk assessment that identifies a problem but leaves it unowned has not controlled the risk. | Claim type: process | URL: https://www.hse.gov.uk/simple-health-safety/risk/risk-assessment-template-and-examples.htm | Evidence: You can use a risk assessment template to help you keep a simple record of: | Source class: primary_authority | Original-source status: original | Source date: undated | Checked date: {DATE} | Claim fit: direct | Freshness decision: historical_scoped | Freshness reason: The live HSE guidance is undated and was checked on the article update date | Status: approved | Intended use: recording step
- Claim: This example shows how the five steps connect for a maintenance engineer using a portable ladder at a customer site. It is an illustration, not a substitute for assessing the real job. HSE permits ladders for low-risk, short-duration work with the right equipment and precautions. Treat each visit as a fresh site decision. | Claim type: process | URL: https://www.hse.gov.uk/work-at-height/ladders/index.htm | Evidence: ladders can be a sensible and practical option for low-risk, short-duration tasks | Source class: primary_authority | Original-source status: original | Source date: undated | Checked date: {DATE} | Claim fit: direct | Freshness decision: historical_scoped | Freshness reason: The live HSE guidance is undated and was checked on the article update date | Status: approved | Intended use: worked example introduction
- Claim: For ladder safety, the HSE ladder guidance explains that ladders are not automatically the first choice and requires the right ladder and sensible precautions. Changes in task duration, height or environment require a fresh equipment and control decision. | Claim type: process | URL: https://www.hse.gov.uk/work-at-height/ladders/index.htm | Evidence: they should not automatically be your first choice | Source class: primary_authority | Original-source status: original | Source date: undated | Checked date: {DATE} | Claim fit: direct | Freshness decision: historical_scoped | Freshness reason: The live HSE guidance is undated and was checked on the article update date | Status: approved | Intended use: worked example qualification
- Claim: What should a workplace risk assessment include? | Claim type: recommendation | URL: https://www.hse.gov.uk/simple-health-safety/risk/risk-assessment-template-and-examples.htm | Evidence: You can use a risk assessment template to help you keep a simple record of: | Source class: primary_authority | Original-source status: original | Source date: undated | Checked date: {DATE} | Claim fit: direct | Freshness decision: historical_scoped | Freshness reason: The live HSE guidance is undated and was checked on the article update date | Status: approved | Intended use: direct answer box
- Claim: Clearground's BigChange story shows the workflow in practice: each operative completes a customised dynamic risk assessment on site, prompting them to consider the environment and its risks before working. That is the operational goal: the assessment changes the decision at the point of work. | Claim type: customer_proof | URL: https://www.bigchange.com/success-stories/bigchange-helps-clearground-clean-up-on-workforce-health-and-safety | Evidence: BigChange's public Clearground story describes the point-of-work assessment workflow | Source class: customer_proof | Original-source status: original | Source date: undated | Checked date: {DATE} | Claim fit: direct | Freshness decision: historical_scoped | Freshness reason: The public customer story is undated and was checked on the article update date | Status: approved | Intended use: paraphrased digital-workflow experience story

## FAQ Source Policy

- Allowed source classes: neutral, non_competing_expert, owned_product.
- Competitor-owned FAQ sources: prohibited.
- Status: aligned.

## FAQ Proof Map

- FAQ: What is a risk assessment in the workplace? | URL: https://www.hse.gov.uk/simple-health-safety/risk/steps-needed-to-manage-risk.htm | Source class: neutral | Competitor check: passed | Support: Hazard, people, evaluation, recording and review sequence.
- FAQ: What are the 5 steps of a workplace risk assessment? | URL: https://www.hse.gov.uk/simple-health-safety/risk/steps-needed-to-manage-risk.htm | Source class: neutral | Competitor check: passed | Support: Five-step sequence.
- FAQ: How often should a workplace risk assessment be reviewed? | URL: https://www.hse.gov.uk/simple-health-safety/risk/steps-needed-to-manage-risk.htm | Source class: neutral | Competitor check: passed | Support: Change, problem, accident and near-miss triggers.
- FAQ: Does a workplace risk assessment need to be written down? | URL: https://www.hse.gov.uk/simple-health-safety/risk/risk-assessment-template-and-examples.htm | Source class: neutral | Competitor check: passed | Support: Significant findings and record fields.

## PAA/FAQ Provenance

- Source: brief_paa
- Artifact: `research/content-brief-{SLUG}-{DATE}.md`
- Selected questions:
  - What is a risk assessment in the workplace?
  - What are the 5 steps of a workplace risk assessment?
  - How often should a workplace risk assessment be reviewed?
  - Does a workplace risk assessment need to be written down?

## Image Inventory

- `workplace-risk-assessment-5-steps.webp`: original five-step field-service safety illustration; standalone reader-visible marker present.
- `workplace-risk-assessment-example-ladder.webp`: original ladder example illustration; standalone reader-visible marker present.
- `digital-workplace-risk-assessment-field-service.webp`: original point-of-work mobile assessment illustration; standalone reader-visible marker present.
- Existing unrelated hero image: removed from the handoff.
- Upload boundary: create, resize and compress before CMS upload.

## Internal Link Plan

- https://www.bigchange.com/features/risk-assessment with exact anchor `risk assessment software`.
- https://www.bigchange.com/blog/work-orders-what-are-they-and-best-practices in corrective-action recording.
- https://www.bigchange.com/blog/ppm-schedule in planned review cadence.
- https://www.bigchange.com/blog/job-tracking-for-field-services-tips in digital management.
- Clearground public customer story in the E-E-A-T passage.
- EICR and building-maintenance-bid links rejected as not directly useful to this general guide.
- Legacy `/compliance` CTA rejected because it resolves to unrelated information-security content.

## Author and Schema Decision

- Author policy: no_author
- Named author supplied: no
- Public frontmatter author: omitted
- No named author was supplied.
- Public frontmatter omits `author`.
- Schema notes include `BlogPosting`, `BreadcrumbList`, `FAQPage`, nested `Question` and `Answer`, `ImageObject`, and `Organization` as publisher reference only.
- `Person as author` and `VideoObject` are omitted.

## Reader-Facing Boundary

- Public copy contains no workflow commentary, proof-selection rationale, schema instruction, score or release status.
- Reader-visible media markers follow the required normalized image format.
- No rating, aggregate review score, exact review snippet or named review claim is published.
"""
