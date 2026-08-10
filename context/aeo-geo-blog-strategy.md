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

## Obsidian Vault Source Rule

For every blog, SEO, AEO, competitor, proof, product, audience, partner, or workflow decision, use the Simpro vault connector as the active context source. The only configured content location is the vault root; prompts, guards, selectors, and workflow docs must not prescribe vault hubs, filenames, or internal directories.

Required connector workflow: run vault health first, describe available roles/topics/entities, search in the task's natural language, read and expand results by `resource_id`, query approved claims only when public proof-sensitive language is needed, then build and validate a context pack.

Do not use Google Workspace or old marketing-portal URLs as the active read path. Use them only as historical provenance when the vault connector exposes them as source evidence.

The repo-local context files are downstream mirrors or operational state only. They cannot override the vault connector when the vault is available. If fallback is used because the vault is unavailable, document the explicit vault-unavailable blocker in the validation sidecar.

Required validation evidence: generated vault context binding and `Fred Voccola Authority Selection` for every new or changed Simpro blog workflow; `Vault Brand Language Alignment` when product, feature, add-on, solution, industry, or related Simpro product URL language appears; `Competitive Shortlist Decision` for competitor-aware posts; `Named Feature/Add-On Link Check` when named Simpro features/add-ons appear. These sections must cite connector `context_pack_hash`, `receipt_hash`, `resource_id`, `claim_id`, use mode, public URL when required, and relevant revisions. Context Binding plus claim-specific gates enforce the source policy. Missing required evidence blocks `/publish-readiness`, `/optimize`, and dev-ready handoff.

## Author-Led Blog Voice

For every Simpro blog, retrieve current voice and tone guidance through the vault connector by semantic search and `resource_id` reads. Named-author Simpro blogs and thought leadership may use first-person judgment, contractions, operational scenes, decisive opinions, and short punchlines. Author opinion must remain distinguishable from empirical fact. Metrics, market comparisons, product status, roadmap statements, and commercial claims remain proof gated. Em dashes are prohibited. Product pages and landing pages retain their existing restrained channel treatment.

## Named Feature Status And Commercial Treatment

When public copy names Lightning, RAIN, a current role agent, Intelligent AI Scheduler, or a roadmap specialist, the validation sidecar must contain exactly one row per detected name under `Named Feature Status and Commercial Treatment`.

```markdown
## Named Feature Status and Commercial Treatment

| Name | Capability claim ID | Commercial claim ID | Release status | Commercial treatment | Region or account boundary | Public wording decision |
|---|---|---|---|---|---|---|
```

Allowed release statuses are `current_public_context`, `preview`, `target_timed`, `roadmap`, and `not_publicly_available`. Allowed commercial treatments are `included`, `package_required`, `add_on_or_upsell`, `mixed`, and `not_asserted`. Supplied claim IDs must resolve uniquely through current connector claim results and the validated context receipt. Internal-only, expired, superseded, missing, and do-not-use evidence blocks public use. Commercial treatment requires a usable commercial claim ID. `not_asserted` is valid only when public copy makes no inclusion, package, price, upgrade, or upsell statement. Unusable current evidence requires `omit`. Intelligent AI Scheduler requires its current capability claim, `target_timed` qualification, and the RAIN Lightning requirement claim. Pulse remains blocked until a current usable claim supports its public roadmap name and treatment.

The blocking `Named Feature Status` gate runs through `data_sources/modules/named_feature_status_guard.py` inside `/publish-readiness`.

The routing policy is enforced through Context Binding plus claim-specific gates, without a duplicate routing sidecar block. Brand, audience, ICP, product, feature, add-on, solution, industry, Lightning, competitor, Hindsight, and Customer proof, quotes, metrics, review stories, approval status data must be connector-first. Repo `context/` owns SEO mechanics, AEO/GEO workflow, schema notes, publish gates, internal links, keyword snapshots, AI citation targets, CRO, Reddit, writing examples, style mechanics, and operational proof-selector inputs.

## Vault-Backed Competitor and Feature Guardrails

- `Competitive Shortlist Decision`: competitor-aware posts must document selected competitors, rejected competitors, connector-discovered competitive-context resources, approved claim IDs where public proof is used, and why the shortlist fits the article objective.
- Public competitor pages may shape SERP/article format, but cannot decide named competitors for Simpro public copy.
- `Hindsight Boundary`: Hindsight/deal intelligence can inform internal strategy, but cannot be published as proof, rankings, metrics, or claims unless separately approved and source-verified through the claim registry. Keep raw deal counts out of public copy.
- `Named Feature/Add-On Link Check`: first meaningful mentions of Simpro features/add-ons must be checked through connector-discovered product and feature resources before link decisions. Document the selected `resource_id` values, link decision, and reason in the validation sidecar.
- `Vault Brand Language Alignment`: product, feature, add-on, solution, and industry language must be drafted from connector-discovered vault guidance first. Use semantic search/read/expand for messaging, positioning, feature, solution, and vertical context. When a named feature/add-on appears, include feature-specific `resource_id` evidence; when solution/industry language is used, include solution or vertical `resource_id` evidence. Document connector evidence, language applied, fallback context use, source-verification boundary, and `Status: aligned` in `Vault Brand Language Alignment`. The `vault_brand_language_guard.py` publish gate runs inside `/publish-readiness`; keep this block in the validation sidecar, not public copy. The repo-local `context/brand-voice.md` and `context/style-guide.md` are fallback mirrors only when the vault is unavailable.

Required `Vault Brand Language Alignment` sidecar block:

```markdown
## Vault Brand Language Alignment
- Article title: [title]
- Product/solution language scope: product/feature | solution/industry | mixed
- Vault connector evidence: [vault_status/vault_describe/vault_search/vault_read/vault_expand operations used; context_pack_hash; receipt_hash; messaging/positioning resource_id values; feature resource_id values when named features/add-ons appear; solution or vertical resource_id values when solution/industry language is used; claim_id values for proof-sensitive public language; manifest/revision values]
- Product/feature language applied: [category, product naming, value pillar, workflow phrase, avoided terms]
- Solution/industry language applied: [vertical profile, audience, work environment, guardrails, or not applicable]
- Fallback context use: none | [repo-local fallback plus vault-unavailable blocker]
- Claims requiring source verification: none | mapped in Source Map / Customer Proof Pack / Metric Proof Pack
- Status: aligned
```

This block validates vault language alignment only. It does not approve claims, pricing, metrics, proof, customer outcomes, competitive statements, quotes, rankings, or ratings; those still route through Source Map, Customer Proof Pack, Metric Proof Pack, and the existing proof gates.

Use this file for blog workflows only. It supports `/research`, `/research-serp`, `/article`, `/write`, `/analyze-existing`, and `/rewrite`; it does not replace marketing skills.

## Required Variable Resolution

Before drafting with `/article`, `/write`, or `/rewrite`, resolve these variables from the user prompt, research brief, generated vault context binding, and repo context files only as fallback/mirror inputs. `/analyze-existing` must audit which inputs are present, missing, or blocked before a rewrite proceeds.

| Variable | First source | Fallback |
|---|---|---|
| `topic` | User prompt or topic file | Ask the user |
| `audience` | Connector-discovered messaging and vertical resources | `context/brand-voice.md` fallback mirror if the vault is unavailable |
| `main_question` | SERP/PAA intent, title, or brief | Ask if no clear primary question exists |
| `related_questions` | AnswerSocrates PAA artifact, SERP, Reddit, YouTube | Ask for PAA/FAQ CSV if AnswerSocrates is blocked |
| `tone` | Connector semantic search and `resource_id` reads for current messaging and style guidance | `context/brand-voice.md` and `context/style-guide.md` fallback mirrors if the connector is unavailable |
| `expertise` | Connector-discovered product/workflow resources and approved claims, plus verified expert sources | Ask if a named author/reviewer is required and missing |
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
- Discover customer, review, product, competitor, and expert evidence through connector search/read/expand by `resource_id`.
- Use `vault_claims` for every public metric, quote, review theme, customer outcome, or other proof-sensitive passage; the selected claim must be present in the validated context pack and receipt.
- Use the claim registry's public URL and source-visibility decision for public citations. Repo-local proof indexes and ledgers are operational selection and reuse state only; they cannot approve a claim or override the connector.
- Context-backed metrics are valid only when the context pack carries an approved claim, permitted use mode, public proof URL, and source-visible evidence anchor. Public copy must link to the public case study, review site, or source URL, not to internal context files.
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

When a brief uses review-site experience evidence, capture platform, URL, date checked, product/competitor, experience pattern, evidence summary, and whether any exact quote/rating claim was approved. When public copy uses a review-derived experience story, the command workflow must automatically run the selector before drafting story copy and add this sidecar block:

```markdown
## Review Story Selection
- **Article title**: [title]
- **Content objective**: [objective]
- **Selector command**: automatically run python data_sources/modules/customer_proof_selector.py "[topic]" --title "[title]" --objective "[objective]" --context-pack "research/context-pack-[topic-slug].json" --context-receipt "research/context-receipt-[topic-slug].json" --evidence-output "research/customer-proof-selector-evidence-[topic-slug].json" --slate --roles experience_story --require-eeat-story --limit 10
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

Before selecting customer proof, the command workflow must resolve `topic`, `title`, and `objective`, automatically run `python data_sources/modules/customer_proof_selector.py "[topic]" --title "[title]" --objective "[objective]" --context-pack "research/context-pack-[topic-slug].json" --context-receipt "research/context-receipt-[topic-slug].json" --evidence-output "research/customer-proof-selector-evidence-[topic-slug].json" --slate --roles metric,quote,theme,experience_story --require-eeat-story --limit 10`, and write the generated selector-first `Customer Proof Slate` to the validation sidecar before drafting customer proof. "Consult" means reviewing generated selector output, not skipping execution. If inputs are missing, resolve them from the brief/context or stop before drafting customer proof. If the selector fails, write the failure or blocker into the validation sidecar and do not invent proof. The selector uses `customer-proof-index.json` and `customer-proof-usage-ledger.json` to choose the most relevant approved proof, then penalizes proof with `recent_uses_90d` above 0 and overused proof. Before claiming a proof source is underused, inspect the usage ledger and run a live repo scan across `drafts/`, `rewrites/`, `research/`, and `published/` for the proof ID, public URL, and customer name. If the live repo scan finds public-copy usage missing from the ledger, backfill `context/customer-proof-usage-ledger.json`, rerun proof health and selector checks, and document the backfill in the validation sidecar. Do not pick the easiest mapped case study when a better-fit Quote Matrix, Reference, Customer Story, or review-site proof route exists. experience_story consideration is required and E-E-A-T story usage is optional; if no story fits, use `Selected: [none]` with section-specific rejection reasons. Edit selected/rejected rows only when editorial judgment requires it. If a recently used or overused proof source is still the best proof, add a `Customer Proof Selection Decision` with a source-specific `Reuse reason` plus selector-backed proof that no stronger underused approved proof fits the same role.

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

The proof-index health report is `python data_sources/modules/customer_proof_index_health.py --index context/customer-proof-index.json --ledger context/customer-proof-usage-ledger.json`; use it to inspect source mix, approval status, public-copy gaps, `recent_uses_90d`, recently used or overused proof, and ledger backfill needs before expanding the index.

New customer proof candidates must enter `context/customer-proof-index.json` through `context/customer-proof-intake-template.csv` and `data_sources/modules/customer_proof_index_intake.py` before a writer relies on them in selector slates. Use:

```powershell
python data_sources/modules/customer_proof_index_intake.py validate [input.csv] --index context/customer-proof-index.json
python data_sources/modules/customer_proof_index_intake.py merge [input.csv] --index context/customer-proof-index.json --out context/customer-proof-index.json
```

The intake row must state source type, source ref, approval status, public-copy boundary, evidence summary, restrictions, and verification date. Exact quotes, metrics, review-story identity claims, reviewer-name claims, ratings, rankings, and badges need explicit source-visible evidence before approval. Google review rows stay candidate and `public_copy_allowed: false` unless a usable public review URL is captured.

Required Customer Proof Slate shape:

```text
Customer Proof Slate
- Selector command: automatically run python data_sources/modules/customer_proof_selector.py "[topic]" --title "[title]" --objective "[objective]" --context-pack "research/context-pack-[topic-slug].json" --context-receipt "research/context-receipt-[topic-slug].json" --evidence-output "research/customer-proof-selector-evidence-[topic-slug].json" --slate --roles metric,quote,theme,experience_story --require-eeat-story --limit 10
- Selector evidence: research/customer-proof-selector-evidence-[topic-slug].json | SHA-256: [generated digest]
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
- **Reuse reason**: [source-specific; required when selected proof has `recent_uses_90d` above 0 or is already marked recently used or overused in the ledger; must include selector-backed proof that no stronger underused approved proof fits the same role]
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

## Fred Voccola Authority Selection

Every `/research`, `/article`, `/write`, `/rewrite`, `/analyze-existing`, and `/optimize` workflow for a new or changed Simpro blog must resolve `topic`, `title`, and `objective`, automatically run:

```powershell
python data_sources/modules/fred_authority_selector.py "[topic]" --title "[title]" --objective "[objective]" --context-pack "research/context-pack-[topic-slug].json" --context-receipt "research/context-receipt-[topic-slug].json" --slate --limit 5
```

Write the complete selector evaluation to `research/validation-[topic-slug]-[YYYY-MM-DD].md` before drafting or changing public Fred content. Evaluation is mandatory; public use is optional and must materially support the article subject and target section. The selector defaults to `Selected: none`; selection requires an explicit editorial decision after the source is reviewed. If the selector, vault, manifest, or required inventory is unavailable or stale, set `Evaluation status: blocked`, document the blocker, and do not invent, infer, quote, paraphrase, cite, or embed Fred evidence.

The Simpro vault connector and claim registry are the sole eligibility source for Fred media eligibility and status. The selector resolves only the configured vault root, validates current connector revisions, resource hashes, and claim decisions, and fails closed when the manifest, claim registry, context receipt, or selected evidence is unavailable or stale. Only current usable authority records and public playlist assets are candidates. Internal assets, blocked rows, syndicated-placement-only rows, non-Simpro evidence, and any row outside its allowed-use status are excluded.

Fred's source-backed industry observations supplement E-E-A-T Expertise and Authority by default. They count as Experience only when the source explicitly supports Fred's first-hand personal or operating experience. Fred evidence is additive: it does not replace customer Experience proof, customer stories, the Customer Proof Pack, or authoritative independent evidence. No usage ledger or frequency penalty applies in v1; direct topical support is the primary selection criterion.

Required sidecar block:

```markdown
## Fred Voccola Authority Selection
- Selector command: [...]
- Evaluation status: completed | blocked
- Top candidates: [FVMI IDs or none]
- Selected: [FVMI ID or none]
- Fit decision: [specific article relevance or rejection reason]
- Intended use: none | embed | inline_citation | paraphrased_industry_observation | exact_quote | embed_and_paraphrase | embed_and_quote
- Target section: [heading or not applicable]
- Authority row: [AUTH ID or none]
- Public URL: [URL or not applicable]
- Evidence status: [vault status or not applicable]
- Verification method: not_applicable | source_visible_article_text | transcript_and_playback | paraphrase_evidence
- Evidence excerpt: [source text or not applicable]
- Timestamp or locator: [timestamp, article locator, or not applicable]
- Playback verified: yes | not_applicable
- Exact quote: [text or not applicable]
- Embed decision: yes | no
- VideoObject: required | not_applicable
```

`Selected: none` passes only when `Fit decision` gives a substantive, article-specific topical rejection reason. A generic statement such as "not relevant" does not pass. For a selected row, the sidecar must match the fields it carries: selected ID, authority ID, public URL, and evidence status. The guard must also confirm that the current manifest-backed inventory and authority rows agree on title, URL, recommended brand, evidence status, public-use status, and allowed-use eligibility.

Public-use rules:

- Exact article quotations require source-visible article text, `Verification method: source_visible_article_text`, an evidence excerpt, and an article locator. Exact video or audio quotations require source-visible transcript or caption evidence, a timestamp, `Verification method: transcript_and_playback`, and `Playback verified: yes`. If those checks are incomplete, paraphrase or omit the observation.
- An exact quote or paraphrased industry observation must include a contextual public source link in the same paragraph. The source must directly support the surrounding statement; a sidecar URL alone does not satisfy this requirement.
- playlist-only rows may be used for discovery or an eligible embed, but never as independent earned-media authority. Do not present a curated playlist entry as third-party validation.
- Embedding is content-first and optional. Embed only a selected, public, embeddable YouTube source that materially supports the target section. Use the existing responsive 16:9 handoff: a privacy-enhanced `https://www.youtube-nocookie.com/embed/[video-id]` URL, visible public fallback link, descriptive iframe title, `loading="lazy"`, no autoplay, verified video metadata, and responsive dimensions.
- Frontmatter must include `VideoObject` when a Fred video is embedded and must omit `VideoObject` when no video is embedded. The internal selection block alone never earns AEO or E-E-A-T credit; only source-backed public content counts.

Existing articles and sidecars are not bulk-backfilled. This block becomes mandatory when an existing Simpro article is next rewritten, optimized, or passed through `/publish-readiness`.

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
- Place a usable artifact within the first 300 words of body copy: a filled data table, a download link (PDF, Excel, Doc, or template), a checklist deliverable, or a calculator/tool reference. Key Takeaways bullets, plain lists, and image placeholders do not count. If no artifact fits the topic, mark `Early artifact requirement: not applicable` with a Reason in the `Early Artifact Plan` block of the validation sidecar.
- If the target query implies a number, range, or template, supply a concrete version in the article with disclaimers as needed. Placeholder-only table cells such as `Enter lender-approved value`, `TBD`, or `varies` withhold the answer and block publish; fill tables with concrete sourced values or delete them. Non-scaffold exemptions go in the `Concrete Answer Check` block of the validation sidecar with a Reason.
- Use one clear idea per H2/H3 section.
- Integrate at least three credible external sources naturally inside sentences.
- Use only 1 link per paragraph. Move the second link to a separate paragraph or remove it.
- Feature and solution links must use function-bearing anchor text that explains the workflow, category, or outcome behind the destination. A feature or solution name alone is not enough.
- Context files are an internal source of truth for voice, positioning, approved claims, proof candidates, and approved metrics only when the Obsidian vault is unavailable; otherwise they are repo-local mirrors/fallbacks. Use public sources and context-backed proof when available, but do not write phrases like "repo context," "context/features.md," "Source Map," "PAA artifact," "change summary," or internal proof-path notes in the public article body.
- Use context-backed metrics only with public-facing source links, such as case-study URLs, review-site URLs, or public research sources.
- 403 replacement rule: if a source URL returns 401, 403, or `manual_review`, do not remove the public citation unless an equivalent resolved public source link replaces it in public copy or the supported claim is removed. DOL, Capterra, G2, Trustpilot, Google Play, and other review or authority-site 403s are URL-validity blockers, not permission to hide the source in the validation sidecar. Source Map notes must document the rejected 403 URL and the replacement URL.
- Include a Metric Proof Pack when the topic calls for metrics, with a Search log and at least one Approved metric carrying source-visible Evidence before numeric claims are placed in the draft.
- Include 3-5 selected PAA/FAQ questions from research.
- Write FAQ answers as 40-60 word direct answers before any supporting context.
- FAQ answer quality is mandatory: use a 40-60 word first visible paragraph and lead with a supported number or range, named recommendation, definition, concrete action, or explained yes/no response. Do not open with `There is no`, `It depends`, `Pricing depends`, `Costs vary`, `We do not know`, `It is unclear`, `No source ranks`, or an equivalent deflection. Put limitations after the direct answer. Replace or remove a question when no defensible answer exists. Run `python data_sources/modules/faq_answer_quality_guard.py [file] --fail-on error` before scoring or `/optimize`.
- FAQ proof is required for every answer: include at least 1 authoritative non-owned public evidence link inside the visible answer. A question-specific Source Map / FAQ Proof Map row may document the same evidence but cannot replace the reader-facing link. Context file paths and owned product links alone do not count. Run `python data_sources/modules/faq_proof_guard.py [file] --proof-sidecar research/validation-[topic-slug]-[YYYY-MM-DD].md --fail-on error` before scoring or `/optimize`.
- **FAQ Source Policy**: Every visible non-owned FAQ URL needs one exact `FAQ Proof Map` row with `FAQ`, `URL`, `Source class`, `Competitor check`, and source-grounded `Support`.
  - Allowed source classes: neutral, non_competing_expert.
  - Competitor-owned FAQ sources: prohibited.
  - Use regulators, standards bodies, universities, trade associations, independent research/editorial, or non-competing expert sources.
  - Simpro-owned links can be additional reader resources but never satisfy the non-owned FAQ-proof requirement.
  - If no compliant source supports a vendor-specific question, remove or reframe the FAQ and retain vendor evidence in a comparison or vendor-specific body section.
  - Add `- Status: aligned.` in the `FAQ Source Policy` sidecar block.

- PAA provenance is required for each FAQ question: include `PAA/FAQ Provenance` with Source, Artifact, and exact Selected questions. Run `python data_sources/modules/paa_provenance_guard.py [file] --proof-sidecar research/validation-[topic-slug]-[YYYY-MM-DD].md --fail-on error` before scoring or `/optimize`.
- Add schema notes for standard blog posts with FAQs: primary schemas are `BlogPosting`, `BreadcrumbList`, and `FAQPage`; nested entities include `Question and Answer inside FAQPage`, `ImageObject for the featured image or logo`, and `Organization as publisher reference only, not a separate full schema block`. For public Markdown blog artifacts, place this as a `schema_notes` field in the top YAML frontmatter block, between the opening and closing --- delimiters. If a named author is present, include `author` in frontmatter and map it to `Person as author`. If no named author is available, omit `author`, omit `Person as author`, keep `Organization` as publisher reference only, and record the no-author decision in the blog assembly BOM and validation sidecar. Use `VideoObject` only when a video is embedded.
- Evaluate Fred authority evidence for every new or changed Simpro blog, but add Fred content only when a selected source directly supports the section. Keep `Fred Voccola Authority Selection` in the validation sidecar, not public copy.

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
| Fred Voccola Authority Selection | Mandatory selector evaluation, ranked FVMI candidates, explicit selected-or-none decision, topical fit, intended use, source verification, embed decision, and VideoObject decision |
| Named Feature Status and Commercial Treatment | Exactly one current claim-status row per detected Lightning, RAIN, role-agent, scheduler, or roadmap specialist name |
| Review Story Selection | Required only when public copy paraphrases a review-derived E-E-A-T story; must include identity-backed selected story, public review URL, same paragraph link requirement, and exact quote boundary |
| Review Site Theme Selection | Required when public copy paraphrases a Capterra review-site theme without using an E-E-A-T story; must include Capterra tab row, public Capterra review-site URL, approved workflow theme, same paragraph link requirement, and exact quote/rating boundary |
| Early usable artifact | Filled data table, download link, checklist deliverable, or calculator reference planned within the first 300 words of body copy, or a documented not-applicable reason |
| AI citation target | Snippet, PAA, FAQ, comparison table, definition, or list |

## Publish Gates

A draft is publish-ready only when both gates pass:

- General content quality score: 85/100 or higher.
- AEO/GEO score: 90/100 or higher.
- Validation sidecar: proof-only blocks must live in `research/validation-[topic-slug]-[YYYY-MM-DD].md`, not in public copy. Public artifacts must pass `data_sources/modules/public_artifact_guard.py --fail-on error` and must not contain an `Editorial Validation Appendix`, `PAA/FAQ Provenance`, `Metric Proof Pack`, `Source Map`, `Customer Proof Pack`, `FAQ Proof Map`, `Fred Voccola Authority Selection`, `Named Feature Status and Commercial Treatment`, `Vault Brand Language Alignment`, `Early Artifact Plan`, `Concrete Answer Check`, bracketed editorial labels, publication confirmation notes, unresolved availability notes, standalone TODO/TBD/TK markers, or structured data plan. Fenced examples, quoted source text, production image placeholders, and reader instructions remain allowed.
- AI copy linting: `data_sources/modules/ai_copy_linter.py --profile simpro-web --fail-on error` blocks copy avoid-rule errors before publish readiness. Copy avoid-rule errors include modal verbs, passive voice, repeated starts, vague generalizations, filler words, and long sentences.
- Publish readiness runner: use `/publish-readiness [file] --proof-sidecar research/validation-[topic-slug]-[YYYY-MM-DD].md --context-request research/context-request-[topic-slug].json --context-pack research/context-pack-[topic-slug].json --context-receipt research/context-receipt-[topic-slug].json --assembly-bom research/blog-assembly-bom-[topic-slug]-[YYYY-MM-DD].json` as the default execution command. Use the individual gates below for debugging and policy-specific failures.
- URL validation gate: `data_sources/modules/url_validator.py --fail-on unresolved` must pass before scoring, `/optimize`, handoff, or publish. URL validation confirms destinations resolve; it does not prove the page supports the claim.
- Public research link guard: `data_sources/modules/public_research_link_guard.py --fail-on error` must pass before scoring or `/optimize`. It blocks sidecar-only handling of public research, compliance, legal, regulatory, or statistical proof, treats `manual_review` URLs as replacement-rule blockers, and requires visible resolved non-owned public research links in the relevant article section or FAQ answer.
- Optimization scoring expectation: `seo_quality_rater.py --validate-urls` and `/optimize` require at least 2 resolved non-owned public research links unless the validation sidecar marks `External research requirement: not applicable` with a reason. Owned Simpro and ClockShark product links do not count as external research links.
- Metric Proof Pack guard: `data_sources/modules/metric_proof_pack_guard.py --fail-on error` must pass before scoring or `/optimize`. Required topics need a Search log and at least one Approved metric with public URL or local proof artifact, source-visible Evidence, Status: approved, and intended Use.
- Numeric claim source guard: `data_sources/modules/numeric_claim_source_guard.py --fail-on error` must pass before scoring or `/optimize`. In addition to numeric claims, it blocks unsupported source-sensitive verbal quantities and comparisons such as single-digit or double-digit performance, number-word business sizes, average/most/majority business claims, and operator-group performance comparisons. A visible public evidence link or matching Source Map row with the claim phrase and a public URL is required.
- FAQ answer quality gate: `data_sources/modules/faq_answer_quality_guard.py --fail-on error` must pass when FAQ answers are present. The first visible paragraph must answer the question directly; generic deflections, missing answers, and unexplained binary answers block publish readiness. This is a mandatory AEO/GEO condition but does not reweight the existing 100-point score.
- FAQ proof gate: `data_sources/modules/faq_proof_guard.py --fail-on error` must pass when FAQ answers are present. Every FAQ answer needs an authoritative non-owned public evidence link in visible copy. A Source Map or FAQ Proof Map can document the same evidence but cannot replace the inline link.
- PAA provenance guard: `data_sources/modules/paa_provenance_guard.py --fail-on error` must pass when FAQ questions are present. Each FAQ question must match the `PAA/FAQ Provenance` selected-question list and saved source artifact.
- Source support guard: `data_sources/modules/source_support_guard.py --fail-on error` must pass before scoring or `/optimize`. Evidence snippets must be visible in the cited source, and named customer metric claims must be approved in Customer Proof Pack Approved metrics.
- Customer proof diversity guard: `data_sources/modules/customer_proof_diversity_guard.py --fail-on error` must pass before scoring or `/optimize`. It verifies that case-study proof is not the only checked source route, that recently used or overused customer proof has a source-specific `Reuse reason`, that the sidecar includes `Customer Proof Selection Decision`, and that `customer_proof_selector.py` inputs from `customer-proof-index.json` and `customer-proof-usage-ledger.json` were respected, including selector-backed proof that no stronger underused approved proof fits the same role.
- Selected customer proof mining: the customer proof diversity guard also requires `Selected Customer Proof Mining` whenever public copy uses customer proof, so selected proof is mined for quotes, metrics, POV/story, and workflow themes before final use is documented.
- Review story identity guard: `data_sources/modules/review_story_identity_guard.py --fail-on error` must pass before scoring or `/optimize`. It verifies that review-derived E-E-A-T story copy has an identity-backed `Review Story Selection`, a usable public review URL, and a same paragraph public link. It also verifies that Capterra review-theme copy has `Review Site Theme Selection`, `Source row ref: Capterra tab row [n]`, `Public review-site URL: https://www.capterra.com/p/10529/Simpro-Enterprise/reviews/`, same paragraph source link, and no exact quote, reviewer-name claim, rating, ranking, or metric unless separately approved.
- Fred authority guard: `data_sources/modules/fred_authority_guard.py --fail-on error` is a blocking `/publish-readiness` gate for Simpro blogs. It requires the complete `Fred Voccola Authority Selection` sidecar block, validates selected inventory and authority fields against the current manifest-backed vault, enforces exact quote and same-paragraph link evidence, restricts playlist assets to discovery or embedding, validates the privacy-enhanced responsive YouTube handoff, and requires `VideoObject` if and only if a video is embedded. A completed selection block without source-backed public use receives no AEO or E-E-A-T score credit.
- Early artifact guard: `data_sources/modules/early_artifact_guard.py --fail-on error` must pass before scoring or `/optimize`. A usable artifact — a filled data table, a download link, a checklist deliverable, or a calculator/tool reference — must start within the first 300 words of body copy. The only exemption is an `Early Artifact Plan` block in the validation sidecar with `Early artifact requirement: not applicable` and a Reason.
- Answer withholding guard: `data_sources/modules/answer_withholding_guard.py --fail-on error` must pass before scoring or `/optimize`. Placeholder table scaffolds block publish unconditionally with no exemption. When the target query implies a number, range, or template, the article must supply a concrete numeric answer early or a filled data table or download; a `Concrete Answer Check` block with `Concrete answer requirement: not applicable` and a Reason exempts only the numeric/template answer requirement, never scaffolds.
- Vault brand language guard: `data_sources/modules/vault_brand_language_guard.py --fail-on error` must pass before scoring or `/optimize` when Simpro product, feature, add-on, solution, industry, or related Simpro product URL language appears. It requires `Vault Brand Language Alignment` in the validation sidecar with connector evidence, context pack and receipt hashes, feature-specific `resource_id` values when named features/add-ons appear, solution or vertical `resource_id` values when solution/industry language appears, fallback blocker details if fallback mirrors were used, and `Status: aligned`.
- Named feature status guard: `data_sources/modules/named_feature_status_guard.py --fail-on error` is the blocking `Named Feature Status` gate. It requires `Named Feature Status and Commercial Treatment`, resolves current claim IDs through the vault, rejects unusable status or commercial evidence, and fails closed on unsupported public wording.

Use `--proof-sidecar research/validation-[topic-slug]-[YYYY-MM-DD].md` with Metric Proof Pack, numeric claim, FAQ proof, PAA provenance, source support, customer proof diversity, review story identity, Fred authority, vault brand language, Named Feature Status, and content scorer commands so proof maps stay out of the article copy artifact.

The validation sidecar is the only approved place for proof maps and proof packs that are not publishable article copy.

## AEO/GEO Recovery Loop

An AEO/GEO score below 90/100 is a repair trigger, not a reporting endpoint. Unless the user explicitly requested a read-only audit, the LLM must continue in the same workflow:

1. Review every failed check in `aeo_geo.checks` and the scorer's `priority_fixes`.
2. Classify each failure as a public-copy gap, validation-sidecar/proof gap, or scorer or parser false negative.
3. If the article visibly satisfies the written requirement but scoring misses it, add a regression test and fix the scorer or parser false negative. Do not distort accurate, brief-approved copy to satisfy brittle matching.
4. Apply the top 3-5 fixes that address root causes. Do not invent PAA questions, claims, proof, metrics, quotes, or customer experience to gain points.
5. Rerun `/scrub`, the AI copy linter, URL validation, regenerate Context Binding with `context_binding_generator.py`, update the blog assembly BOM, and rerun `/publish-readiness [file] --proof-sidecar [sidecar] --context-request [request] --context-pack [pack] --context-receipt [receipt] --assembly-bom [bom]`.
6. Repeat once if needed. If AEO/GEO remains below 90/100 after 2 iterations, route the artifact to `review-required/` with the score, failed checks, attempted fixes, and any external evidence or authority blocker.

`/optimize` is allowed inside this recovery loop when all proof, source, URL, and public-artifact gates pass but content quality or AEO/GEO does not. Final handoff still requires content quality of at least 85/100, AEO/GEO of at least 90/100, and every blocking gate to pass.

Below-threshold drafts route to revision or `review-required/` with notes explaining failed checks.
