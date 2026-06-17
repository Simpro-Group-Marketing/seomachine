# AEO/GEO Blog Strategy

**Purpose:** Canonical AEO/GEO workflow for Simpro blog research, writing, analysis, and rewrites.
**Use when:** Planning or checking blog content that needs PAA, source mapping, Customer Proof Pack, E-E-A-T proof, or AEO/GEO gates.
**Owns:** AEO/GEO variables, PAA workflow, proof-pack shape, draft rules, and publish gates.
**Does not own:** Brand voice, feature claims, competitor battlecards, keyword metrics, or internal-link inventories.
**Source boundary:** Workflow contract only; evidence still needs current public or approved context-backed sources.
**Refresh cadence:** Review when blog workflow gates, proof policy, or AEO/GEO scoring changes.
**Reference detail:** No separate reference file; operating guidance remains here.

---

This file is the canonical blog-writing strategy for AEO and GEO. In this repo, GEO means Generative Engine Optimization: structuring content so generative answer systems can understand, extract, cite, and recommend it.

Use this file for blog workflows only. It supports `/research`, `/research-serp`, `/article`, `/write`, `/analyze-existing`, and `/rewrite`; it does not replace marketing skills.

## Required Variable Resolution

Before drafting with `/article`, `/write`, or `/rewrite`, resolve these variables from the user prompt, research brief, and repo context files. `/analyze-existing` must audit which inputs are present, missing, or blocked before a rewrite proceeds.

| Variable | First source | Fallback |
|---|---|---|
| `topic` | User prompt or topic file | Ask the user |
| `audience` | `context/brand-voice.md` audience and fit guidance | Ask only if multiple audiences fit |
| `main_question` | SERP/PAA intent, title, or brief | Ask if no clear primary question exists |
| `related_questions` | AnswerSocrates PAA artifact, SERP, Reddit, YouTube | Ask for PAA/FAQ CSV if AnswerSocrates is blocked |
| `tone` | `context/brand-voice.md` and `context/style-guide.md` | Ask only if user requests a non-standard tone |
| `expertise` | `context/features.md`, customer proof, expert quotes | Ask if a named author/reviewer is required and missing |
| `length` | SERP/content brief | Default to competitive length from `/research-serp` |

Do not synthesize facts, search volume, PAA questions, customer claims, or expert quotes. If the repo and live research do not provide an input, ask for it or mark it as missing.

## Existing-Content Rewrite Use

For `/analyze-existing`, audit whether the current post has the strategy inputs needed for a safe rewrite: main answer target, related-question provenance, source-backed claims, Source Map, E-E-A-T proof, direct-answer opportunities, capsule opportunities, schema notes, and quality-gate risks.

For `/rewrite`, resolve the same variables before drafting. Reuse existing strategy artifacts only when they match the post topic and current rewrite direction. If the rewrite brief lacks sourced questions, source-backed claims, or proof, collect them or mark the blocker before writing.

Do not invent replacement questions, customer proof, author names, reviewer names, search-volume data, ranking data, or external claims to fill rewrite gaps.

## E-E-A-T Proof Map

Every `/article`, `/write`, and `/rewrite` plan must resolve an E-E-A-T Proof Map before drafting. `/analyze-existing` must report Experience proof present/missing, Expertise proof present/missing, case-study proof candidates, Review-site VoC candidates, review-site experience evidence candidates, and claims that must stay out because proof is missing.

| Dimension | Approved inputs | Public-copy rule |
|---|---|---|
| Experience | Customer case studies, customer outcomes, identity-backed Review Story Selection rows, review-site experience evidence / VoC themes, implementation/support themes, user pain, and field workflow examples | Cite the public case-study URL, approved review-site/source URL, or verified source page. Review-derived E-E-A-T stories need a public review URL in the same paragraph as the paraphrase. Do not cite internal context language. |
| Expertise | Product/feature knowledge, source-backed workflow explanations, expert quotes, author/reviewer metadata, and Simpro workflow specificity | Use Simpro product/workflow links and source-backed explanations. Do not invent author, reviewer, or expert claims. |
| Authority/Trust | Public research, case-study URLs, review-site/source links, limitations, caveats, and no invented proof | Tie each claim to a public-facing source link or keep it out. |

Required proof sources:
- Pull case-study URLs and internal proof routes from `context/internal-links-map.md`.
- Pull approved metrics and proof candidates from `context/features.md`.
- Pull review-site experience evidence / VoC themes and competitor experience themes from `context/competitor-analysis.md` or any future review-context file.
- Context-backed metrics are valid only when the context pack carries the approved metric, proof path, and a source-visible Evidence snippet. Public copy must link to the public case study, review site, or source URL, not to internal context files.
- Metric-sensitive topics must include a Metric Proof Pack before drafting or publish readiness. The pack requires a Search log, each Approved metric, public proof URL or local proof artifact, source-visible Evidence, Status: approved, intended Use, and rejected candidates.
- The source support guard requires each high-risk claim to map to a strict proof row with Claim, URL, Evidence, and Status: approved. The Evidence snippet must be visible in the cited public source or local proof artifact.
- The PAA provenance guard requires each FAQ question to map to a saved AnswerSocrates, SERP, Reddit, YouTube, or user PAA/FAQ CSV artifact. Proof links alone do not prove question provenance.
- Do not write source/proof meta-commentary in public copy, such as "that case study is useful for this topic" or "this source is relevant for the article." Translate proof into audience-facing takeaways, outcomes, or workflow lessons.

## Metric Proof Pack

Every `/research`, `/article`, `/write`, `/analyze-existing`, and `/rewrite` workflow for software, comparison, pricing, cost, ROI, KPI, profit, margin, guide, or vs topics must resolve a Metric Proof Pack before numbers enter public copy.

Required Metric Proof Pack shape:

```markdown
## Metric Proof Pack
- **Metric requirement**: required / not applicable
- **Reason**: [required only when not applicable]
- **Search log**: [public pages and local proof artifacts checked for usable numbers]
- **Approved metric**: [metric claim] | URL: [public proof URL or local proof artifact] | Evidence: "[source-visible Evidence]" | Status: approved | Use: [intended use]
- **Rejected metrics**: [candidate metric, source checked, reason excluded]
```

Run `python data_sources/modules/metric_proof_pack_guard.py [file] --proof-sidecar research/validation-[topic-slug]-[YYYY-MM-DD].md --fail-on error` before scoring or `/optimize`. The guard blocks metric-free software-selection, buyer-guide, comparison, pricing, cost, ROI, KPI, profit, margin, guide, and vs topics unless `Metric requirement: not applicable` is documented with a reason and search log. Numeric claim source guard and source support guard still prove any numbers that appear in the final article.

## Review-Site Experience Evidence and VoC Routing

Public review sites are approved for sourced review-site experience evidence, VoC themes, and competitor-review themes. Approved surfaces include G2, Capterra, Software Advice, GetApp, TrustRadius, Gartner/Gartner Digital Markets, Trustpilot, app stores, and Google reviews.

Review narratives are first-hand customer experience when reviewers describe product use, implementation, support, switching, pains, outcomes, or workflows. Review-site themes can inform VoC research, but they do not satisfy E-E-A-T story proof unless the sidecar contains an identity-backed `Review Story Selection` with a real person or business, a usable public review URL, Status: approved, and an article link requirement that places the source link in the same paragraph as the paraphrase.

For Capterra rows that fit a blog topic but do not need an E-E-A-T story, use `Review Site Theme Selection` in the validation sidecar. It must include `Platform: Capterra`, `Source row ref: Capterra tab row [n]`, `Public review-site URL: https://www.capterra.com/p/10529/Simpro-Enterprise/reviews/`, `Workflow theme`, and `Status: approved for paraphrased review-theme use`. Public copy may paraphrase the theme only when the same paragraph links to the Capterra review-site URL. Limits: no exact quote, reviewer-name claim, rating, ranking, or metric unless separately approved.

Use review sites for sourced VoC themes, objections, switching triggers, implementation or support themes, competitor-review themes, and first-hand customer experience patterns. Default to theme-level citation: cite the theme and link to the relevant review, profile, category, or comparison page.

When a brief uses review-site experience evidence, capture platform, URL, date checked, product/competitor, experience pattern, evidence summary, and whether any exact quote/rating claim was approved. When public copy uses a review-derived experience story, add this sidecar block:

```markdown
## Review Story Selection
- **Article title**: [title]
- **Content objective**: [objective]
- **Selector command**: python data_sources/modules/customer_proof_selector.py "[topic]" --title "[title]" --objective "[objective]" --slate --roles experience_story --require-eeat-story --limit 10
- **Selected story**: [proof_id] | Identity: [person or business] | Platform: [G2/Capterra/Google] | URL: [public review URL] | Workflow story: [short paraphrase] | Status: approved | Use: E-E-A-T experience story
- **Why selected**: [fit to article objective/title]
- **Article link requirement**: same paragraph as review-derived paraphrase must link to the selected public review URL
- **Exact quote use**: not approved unless listed under Approved quote
```

```markdown
## Review Site Theme Selection
- **Article title**: [title]
- **Content objective**: [objective]
- **Platform**: Capterra
- **Source row ref**: Capterra tab row [n]
- **Public review-site URL**: https://www.capterra.com/p/10529/Simpro-Enterprise/reviews/
- **Workflow theme**: [short paraphrase]
- **Status**: approved for paraphrased review-theme use
- **Article link requirement**: same paragraph must link to the Capterra review-site URL
- **Limits**: no exact quote, reviewer-name claim, rating, ranking, or metric unless separately approved
```

Exact quotes, named reviewers, star ratings, badges, rankings, aggregate ratings, and category-leadership claims are Trust/Authority claims; they require current source verification and brief-level approval.

### Optional Story and Scenario Policy

E-E-A-T stories are optional, and E-E-A-T story usage is optional in public copy. experience_story consideration is required whenever customer proof appears in public copy. Use a proof-backed customer/review POV only when it improves the article objective. A named public POV must be an actual person or business POV from approved customer proof, a public case study, Quote Matrix route, reference, customer story, or review-site row, with proof in the validation sidecar and a public source link when used in copy.

Review-theme evidence is VoC only unless it is identity-backed and link-backed through `Review Story Selection`. Unnamed workflow scenarios are explanatory only and do not count as E-E-A-T proof; fictional named personas are prohibited.

## Customer Proof Pack

Every `/research`, `/article`, `/write`, `/analyze-existing`, and `/rewrite` workflow must resolve a task-specific Customer Proof Pack before placing direct quotes, named customer proof, approved metrics, or review-derived Experience patterns in public copy. Keep the Quote Matrix external; do not bulk-load it into repo context.

Use the Global Customer Quote Matrix first for exact customer quotes. Use Customer Stories, References, and public case studies to verify the story path and publishability. Use review sites for first-hand Experience patterns by default, not unverified testimonial harvesting. Metrics from `context/features.md` must pair with public proof paths from `context/internal-links-map.md`.

Before selecting customer proof, run or consult `python data_sources/modules/customer_proof_selector.py "[topic]" --title "[title]" --objective "[objective]" --slate --roles metric,quote,theme,experience_story --require-eeat-story --limit 10`. The selector uses `customer-proof-index.json` and `customer-proof-usage-ledger.json` to choose the most relevant approved proof, then penalizes overused proof. Do not pick the easiest mapped case study when a better-fit Quote Matrix, Reference, Customer Story, or review-site proof route exists. Generate a `Customer Proof Slate` before drafting so the writer can compare metric, quote, theme, and optional story candidates; edit selected/rejected rows only when editorial judgment requires it. If no story fits, use `Selected: [none]` with section-specific rejection reasons. If a repeated case study is still the best proof, add a `Customer Proof Selection Decision` with a source-specific `Reuse reason` plus selector-backed proof that no stronger underused approved proof fits the same role.

Selector chooses proof candidates; proof mining reads the selected public URL before the writer decides quote, metric, POV/story, theme, or omit use. When public copy uses selected customer proof, the validation sidecar must include `Selected Customer Proof Mining`. This block proves the selected source was checked for stronger quote, metric, POV/story, and theme evidence before the final copy used only the selected proof role.

Required Selected Customer Proof Mining shape:

```text
Selected Customer Proof Mining
- Proof: [proof_id] | Customer: [customer] | URL: [public URL]
- Checked for: exact quotes, customer metrics, POV story, workflow themes
- Usable quotes found: [exact approved quote rows or none found]
- Usable metrics found: [approved metric rows or none found]
- Usable POV/story found: [identity-backed POV summary or none found]
- Recommended use: [theme / paraphrased POV / exact quote / metric / omit]
- Final use in copy: [what the article actually uses]
- Excluded proof: [quote/metric/POV and section-specific reason]
- Status: approved
```

If `Approved quotes: none used` or `Approved metrics: none used` appears in the Customer Proof Pack, the mining block must still document whether usable quotes or metrics were found and why they were omitted. When usable quote or POV evidence is found but omitted, add a section-specific reason under `Excluded proof`.

### proof-index intake and health

The proof-index health report is `python data_sources/modules/customer_proof_index_health.py --index context/customer-proof-index.json --ledger context/customer-proof-usage-ledger.json`; use it to inspect source mix, approval status, public-copy gaps, and overused proof before expanding the index.

New customer proof candidates must enter `context/customer-proof-index.json` through `context/customer-proof-intake-template.csv` and `data_sources/modules/customer_proof_index_intake.py` before a writer relies on them in selector slates. Use:

```powershell
python data_sources/modules/customer_proof_index_intake.py validate [input.csv] --index context/customer-proof-index.json
python data_sources/modules/customer_proof_index_intake.py merge [input.csv] --index context/customer-proof-index.json --out context/customer-proof-index.json
```

The intake row must state source type, source ref, approval status, public-copy boundary, evidence summary, restrictions, and verification date. Exact quotes, metrics, review-story identity claims, reviewer-name claims, ratings, rankings, and badges need explicit source-visible evidence before approval. Google review rows stay candidate and `public_copy_allowed: false` unless a usable public review URL is captured.

Required Customer Proof Slate shape:

```text
Customer Proof Slate
- Selector command: python data_sources/modules/customer_proof_selector.py "[topic]" --title "[title]" --objective "[objective]" --slate --roles metric,quote,theme,experience_story --require-eeat-story --limit 10
- Role: metric | Top candidates: [proof_id, proof_id, proof_id] | Selected: [proof_id] | Rejected stronger candidates: [proof_id: reason]
- Role: quote | Top candidates: [proof_id, proof_id, proof_id] | Selected: [proof_id or none] | Rejected stronger candidates: [proof_id: reason]
- Role: theme | Top candidates: [proof_id, proof_id, proof_id] | Selected: [proof_id or none] | Rejected stronger candidates: [proof_id: reason]
- Role: experience_story | Top candidates: [proof_id, proof_id, proof_id] | Selected: [proof_id or none] | Rejected stronger candidates: [proof_id: reason]
```

Required Customer Proof Pack shape:

```markdown
## Customer Proof Pack
- **Pack status**: ready / partial / blocked
- **Topic or page fit**: [topic, audience, region, trade, funnel stage]
- **Quote Matrix candidates**: [customer, trade, region, theme, exact quote or summary, source row/link, approval status]
- **Case-study proof paths**: [customer, public URL, supported non-numeric theme]
- **Review-site experience evidence**: [platform, URL, date checked, product/competitor, experience pattern, evidence summary, exact quote/rating approval status]
- **Customer Proof Slate**: [selector command plus metric, quote, theme, and experience_story role rows; story usage optional]
- **Selected Customer Proof Mining**: [selected public URL checked for exact quotes, customer metrics, POV story, workflow themes, recommended use, final use, excluded proof, and Status: approved]
- **Customer Proof Selection Decision**: [selector command, selected proof IDs, rejected stronger candidates, final use in copy]
- **Reuse reason**: [source-specific; required when selected proof appears 3+ times in the last 90 days or is already marked overused in the ledger; must include selector-backed proof that no stronger underused approved proof fits the same role]
- **Approved quotes**: [exact quote/testimonial, customer/brand/reviewer, source type, public proof URL, Evidence, approval status]
- **Approved metrics**: [named customer metric, customer/brand, public proof URL, Evidence, approval status]
- **Use in copy**: [exact quote / paraphrased theme / named metric / omit]
- **Claims excluded**: [claim and missing proof reason]
```

Example strict proof rows:

```markdown
- Claim: Shaffer Beacon Mechanical can process twice the amount of business with the same resources | URL: https://www.simprogroup.com/case-studies/schaffer-beacon-mechanical | Evidence: "We can process twice the amount of business with the same amount of resources" | Status: approved | Use: paraphrased customer outcome
- Approved quote: "The system gives our technicians one place to work from." | Customer/brand: Shaffer Beacon Mechanical | Source type: case study | URL: https://www.simprogroup.com/case-studies/schaffer-beacon-mechanical | Evidence: "The system gives our technicians one place to work from." | Status: approved | Use: exact quote
- Approved metric: Simpro 24,000+ trade businesses | Customer/brand: Simpro | URL: https://www.simprogroup.com/company/press/simpro-group-unveils-lightning | Evidence: "More than 24,000 trade businesses" | Status: approved
```

Case-study proof paths and Review-site experience evidence may support non-numeric E-E-A-T PoV and paraphrased themes only. Exact quotes or testimonial wording must appear under Approved quotes with customer/brand or reviewer, source type, public URL, source-visible Evidence, and Status: approved. Any named customer metric must appear under Approved metrics with Customer/brand, public URL, source-visible Evidence, and Status: approved. Source Map alone is insufficient for quotes, testimonials, or named metrics.

## AnswerSocrates PAA Workflow

For every new `/article` run, collect People Also Ask style questions from `https://answersocrates.com` with Playwright MCP.

Required browser flow:

1. Open AnswerSocrates with `browser_navigate`.
2. Use `browser_snapshot` to identify the query input and submit action.
3. Enter the inferred `main_question`; if no main question exists, enter `topic`.
4. Submit with snapshot-derived targets only. Do not hard-code selectors.
5. Wait for results and extract visible questions with `browser_evaluate`.
6. Save the result to `research/paa-questions-[topic-slug]-[YYYY-MM-DD].md`.

If AnswerSocrates is blocked, unavailable, or requires login/CAPTCHA, record the blocker in the artifact and ask the user for a PAA/FAQ CSV export. Do not invent replacement questions.

For `/rewrite`, an existing AnswerSocrates artifact, SERP PAA set, Reddit/YouTube question set, or user PAA/FAQ CSV may satisfy this requirement if the artifact is cited in the analysis or change summary. If none exists, collect a new artifact or record the blocker.

## PAA Artifact Format

```markdown
# PAA Questions: [Topic]

**Date:** [YYYY-MM-DD]
**Source:** AnswerSocrates via Playwright MCP
**Query Used:** [main_question or topic]
**Status:** [collected / blocked / user-export-needed]

## Raw Questions
- [question]

## Closest Related Questions
1. [question]
2. [question]
3. [question]

## Intent Breakdown
- [How-to / Understanding / Comparative / Future-Trends / Commercial]: [brief note]

## Insight Summary
[2-3 sentences explaining what these questions reveal about user intent.]

## Suggested Blog Focus
[1-2 sentences that should guide the article.]

## Section Assignment
| Question | Intent | Article Section | Answer Format |
|---|---|---|---|
| [question] | [intent] | [H2/FAQ] | [capsule/list/table/FAQ] |
```

## Question Relevance Selection

When a PAA/FAQ CSV or raw question set is available, select the 3-5 closest questions to the main concept. Group them by search intent such as How-to, Understanding, Comparative, Future-Trends, or Commercial. Summarize what the questions reveal about user intent, write a suggested blog focus, and assign each selected question to an article section and answer format.

## Drafting Rules

- Open with a direct answer in the first 1-2 sentences. The answer comes before the hook.
- Use the Capsule Method below the H1 and at least 60% of major H2s: 50-60 words, complete answer, no preamble.
- Include a Key Takeaways block after the introduction with 3-5 standalone conclusions.
- Use one clear idea per H2/H3 section.
- Integrate at least three credible external sources naturally inside sentences.
- Use only 1 link per paragraph. Move the second link to a separate paragraph or remove it.
- Feature and solution links must use function-bearing anchor text that explains the workflow, category, or outcome behind the destination. A feature or solution name alone is not enough.
- Context files are an internal source of truth for voice, positioning, approved claims, proof candidates, and approved metrics. Use public sources and context-backed proof when available, but do not write phrases like "repo context," "context/features.md," "Source Map," "PAA artifact," "change summary," or internal proof-path notes in the public article body.
- Use context-backed metrics only with public-facing source links, such as case-study URLs, review-site URLs, or public research sources.
- Include a Metric Proof Pack when the topic calls for metrics, with a Search log and at least one Approved metric carrying source-visible Evidence before numeric claims are placed in the draft.
- Include 3-5 selected PAA/FAQ questions from research.
- Write FAQ answers as 40-60 word direct answers before any supporting context.
- FAQ proof is required for each claim-bearing answer: include a public proof link inside the answer, or map the exact question to a question-specific Source Map / FAQ Proof Map entry with a public URL. Context file paths alone do not count. Run `python data_sources/modules/faq_proof_guard.py [file] --proof-sidecar research/validation-[topic-slug]-[YYYY-MM-DD].md --fail-on error` before scoring or `/optimize`.
- PAA provenance is required for each FAQ question: include `PAA/FAQ Provenance` with Source, Artifact, and exact Selected questions. Run `python data_sources/modules/paa_provenance_guard.py [file] --proof-sidecar research/validation-[topic-slug]-[YYYY-MM-DD].md --fail-on error` before scoring or `/optimize`.
- Add schema notes for `BlogPosting`, `FAQPage`, `Author`, and `VideoObject` when relevant.

## AEO/GEO Map

Every `/article` plan and every moderate, major, or complete `/rewrite` plan must include:

| Field | Requirement |
|---|---|
| Main answer target | The core question the article answers |
| Capsule targets | H1 plus 60%+ major H2s |
| Selected PAA questions | 3-5 questions from AnswerSocrates or user export |
| PAA/FAQ provenance | Source label, artifact path, and exact selected questions from a saved source artifact |
| Source map | Source, claim, anchor text, target section |
| Metric Proof Pack | Metric requirement, Search log, Approved metric rows, public URL or local proof artifact, source-visible Evidence, Status: approved, intended Use, rejected candidates |
| E-E-A-T Proof Map | Experience proof, Expertise proof, Authority/Trust proof, case-study candidates, review-site VoC candidates, omitted unsupported claims |
| Customer Proof Pack | Pack status, Quote Matrix candidates, Case-study proof paths, Review-site experience evidence, Approved metrics, Use in copy, Claims excluded, approval status |
| Review Story Selection | Required only when public copy paraphrases a review-derived E-E-A-T story; must include identity-backed selected story, public review URL, same paragraph link requirement, and exact quote boundary |
| Review Site Theme Selection | Required when public copy paraphrases a Capterra review-site theme without using an E-E-A-T story; must include Capterra tab row, public Capterra review-site URL, approved workflow theme, same paragraph link requirement, and exact quote/rating boundary |
| AI citation target | Snippet, PAA, FAQ, comparison table, definition, or list |

## Publish Gates

A draft is publish-ready only when both gates pass:

- General content quality score: 85/100 or higher.
- AEO/GEO score: 90/100 or higher.
- Validation sidecar: proof-only blocks must live in `research/validation-[topic-slug]-[YYYY-MM-DD].md`, not in public copy. Public artifacts must pass `data_sources/modules/public_artifact_guard.py --fail-on error` and must not contain an `Editorial Validation Appendix`, `PAA/FAQ Provenance`, `Metric Proof Pack`, `Source Map`, `Customer Proof Pack`, `FAQ Proof Map`, or structured data plan.
- AI copy linting: `data_sources/modules/ai_copy_linter.py --profile simpro-web --fail-on error` blocks copy avoid-rule errors before publish readiness. Copy avoid-rule errors include modal verbs, passive voice, repeated starts, vague generalizations, filler words, and long sentences.
- Publish readiness runner: use `/publish-readiness [file] --proof-sidecar research/validation-[topic-slug]-[YYYY-MM-DD].md` as the default execution command. Use the individual gates below for debugging and policy-specific failures.
- URL validation gate: `data_sources/modules/url_validator.py --fail-on unresolved` must pass before scoring, `/optimize`, handoff, or publish. URL validation confirms destinations resolve; it does not prove the page supports the claim.
- Metric Proof Pack guard: `data_sources/modules/metric_proof_pack_guard.py --fail-on error` must pass before scoring or `/optimize`. Required topics need a Search log and at least one Approved metric with public URL or local proof artifact, source-visible Evidence, Status: approved, and intended Use.
- FAQ proof gate: `data_sources/modules/faq_proof_guard.py --fail-on error` must pass when FAQ answers are present. Each claim-bearing FAQ answer needs a public proof link or question-specific Source Map / FAQ Proof Map entry with a public URL. Context file paths alone do not count.
- PAA provenance guard: `data_sources/modules/paa_provenance_guard.py --fail-on error` must pass when FAQ questions are present. Each FAQ question must match the `PAA/FAQ Provenance` selected-question list and saved source artifact.
- Source support guard: `data_sources/modules/source_support_guard.py --fail-on error` must pass before scoring or `/optimize`. Evidence snippets must be visible in the cited source, and named customer metric claims must be approved in Customer Proof Pack Approved metrics.
- Customer proof diversity guard: `data_sources/modules/customer_proof_diversity_guard.py --fail-on error` must pass before scoring or `/optimize`. It verifies that case-study proof is not the only checked source route, that repeated customer proof has a source-specific `Reuse reason`, that the sidecar includes `Customer Proof Selection Decision`, and that `customer_proof_selector.py` inputs from `customer-proof-index.json` and `customer-proof-usage-ledger.json` were respected, including selector-backed proof that no stronger underused approved proof fits the same role.
- Selected customer proof mining: the customer proof diversity guard also requires `Selected Customer Proof Mining` whenever public copy uses customer proof, so selected proof is mined for quotes, metrics, POV/story, and workflow themes before final use is documented.
- Review story identity guard: `data_sources/modules/review_story_identity_guard.py --fail-on error` must pass before scoring or `/optimize`. It verifies that review-derived E-E-A-T story copy has an identity-backed `Review Story Selection`, a usable public review URL, and a same paragraph public link. It also verifies that Capterra review-theme copy has `Review Site Theme Selection`, `Source row ref: Capterra tab row [n]`, `Public review-site URL: https://www.capterra.com/p/10529/Simpro-Enterprise/reviews/`, same paragraph source link, and no exact quote, reviewer-name claim, rating, ranking, or metric unless separately approved.

Use `--proof-sidecar research/validation-[topic-slug]-[YYYY-MM-DD].md` with Metric Proof Pack, numeric claim, FAQ proof, PAA provenance, source support, customer proof diversity, review story identity, and content scorer commands so proof maps stay out of the article copy artifact.

The validation sidecar is the only approved place for proof maps and proof packs that are not publishable article copy.

Below-threshold drafts route to revision or `review-required/` with notes explaining failed checks.
