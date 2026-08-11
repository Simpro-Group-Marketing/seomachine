# Rewrite Command

## Context Binding Regeneration (MANDATORY)

After the final content mutation, regenerate the machine-owned binding before `/publish-readiness`:

```bash
python data_sources/modules/context_binding_generator.py "$FILE_PATH" --proof-sidecar "$PROOF_SIDECAR" --context-request "$CONTEXT_REQUEST" --context-pack "$CONTEXT_PACK" --context-receipt "$CONTEXT_RECEIPT"
```

Run this again after every scrub, optimization, or editorial change that modifies public copy. A stale article hash blocks handoff.

### After Optimization Mutations

All optimizer outputs and manual edits are content mutations. After optimization mutations, rerun `/scrub`, regenerate Context Binding with `context_binding_generator.py`, update `research/blog-assembly-bom-[topic-slug]-[YYYY-MM-DD].json`, then rerun `/publish-readiness [file] --proof-sidecar research/validation-[topic-slug]-[YYYY-MM-DD].md --context-request research/context-request-[topic-slug].json --context-pack research/context-pack-[topic-slug].json --context-receipt research/context-receipt-[topic-slug].json --assembly-bom research/blog-assembly-bom-[topic-slug]-[YYYY-MM-DD].json`.

Use this command to update and improve existing blog posts based on analysis findings.

For every Simpro blog, retrieve current voice and tone guidance through the vault connector by semantic search and `resource_id` reads. Named-author Simpro blogs and thought leadership may use first-person judgment, contractions, operational scenes, decisive opinions, and short punchlines. Author opinion must remain distinguishable from empirical fact. Metrics, market comparisons, product status, roadmap statements, and commercial claims remain proof gated. Em dashes are prohibited. Product pages and landing pages retain their existing restrained channel treatment.

## Usage
`/rewrite [topic or analysis file]`

## What This Command Does
1. Takes existing blog post content and improvement recommendations
2. Rewrites content with updated information and SEO optimization
3. Maintains original article structure where effective
4. Adds new sections to fill content gaps
5. Updates outdated statistics, examples, and references

## Process

### Obsidian Vault Source Rule

For every blog, SEO, AEO, competitor, proof, product, audience, partner, or workflow decision, use the Simpro vault connector as the active context source. The only configured content location is the vault root; do not prescribe vault hubs, filenames, or internal directories.

Required connector workflow: run vault health first, describe available roles/topics/entities, search in the task's natural language, read and expand results by `resource_id`, query approved claims only when public proof-sensitive language is needed, then build and validate a context pack.

Do not use Google Workspace or old marketing-portal URLs as the active read path. Use them only as historical provenance when the vault connector exposes them as source evidence.

The repo-local context files are downstream mirrors or operational state only. They cannot override the vault connector when the vault is available. If fallback is used because the vault is unavailable, document the explicit vault-unavailable blocker in the validation sidecar.

Required validation sidecar evidence: generated vault context binding for every workflow; `Vault Brand Language Alignment` when product, feature, add-on, solution, industry, or related Simpro product URL language appears; `Competitive Shortlist Decision` for competitor-aware posts; `Named Feature/Add-On Link Check` when named Simpro features/add-ons appear. These sections must cite connector `context_pack_hash`, `receipt_hash`, `resource_id`, `claim_id`, use mode, public URL when required, and relevant revisions. Missing required evidence blocks `/publish-readiness`, `/optimize`, and dev-ready handoff.

### Vault-Backed Competitor and Feature Guardrails

- `Competitive Shortlist Decision`: competitor-aware posts must document selected competitors, rejected competitors, connector-discovered competitive-context resources, approved claim IDs where public proof is used, and why the shortlist fits the article objective.
- Public competitor pages may shape SERP/article format, but cannot decide named competitors for Simpro public copy.
- `Hindsight Boundary`: Hindsight/deal intelligence can inform internal strategy, but cannot be published as proof, rankings, metrics, or claims unless separately approved and source-verified through the claim registry. Keep raw deal counts out of public copy.
- `Named Feature/Add-On Link Check`: first meaningful mentions of Simpro features/add-ons must be checked through connector-discovered product and feature resources before link decisions. Document the selected `resource_id` values, link decision, and reason in the validation sidecar.
- `Vault Brand Language Alignment`: product, feature, add-on, solution, and industry language must be drafted from connector-discovered vault guidance first. Use semantic search/read/expand for messaging, positioning, feature, solution, and vertical context. When a named feature/add-on appears, include feature-specific `resource_id` evidence; when solution/industry language is used, include solution or vertical `resource_id` evidence. Document connector evidence, language applied, fallback context use, source-verification boundary, and `Status: aligned` in `Vault Brand Language Alignment`. The `vault_brand_language_guard.py` publish gate runs inside `/publish-readiness`; keep this block in the validation sidecar, not public copy. The repo-local `context/brand-voice.md` and `context/style-guide.md` are fallback mirrors only when the vault is unavailable.

### Pre-Rewrite Review
- **Original Content**: Read the existing article thoroughly
- **Analysis Report**: Review findings from `/analyze-existing` if available
- **Research Brief**: Check if new research brief exists for updated angles
- **Brand Voice**: Verify alignment through connector semantic search and current `resource_id` reads; @context/brand-voice.md is a fallback mirror only when the connector is unavailable
- **SEO Guidelines**: Apply latest requirements from @context/seo-guidelines.md
- **AEO/GEO Strategy**: Apply @context/aeo-geo-blog-strategy.md before drafting
- **Competitive Context**: Understand what's changed in SERP since original publication
- **Lightning Overlay**: If the article, topic, or analysis mentions Simpro Lightning, AroFlo Lightning, BigChange Lightning, Simpro Group Lightning, JustAsk, Cooper, FieldReady, JobReady, JobScribe, JobBrief, Price Lock, AI tax, TrueTime, DirectLine, Coming Specialists, or any named roadmap specialist, search the vault connector in the task's natural language, read and expand the selected Lightning `resource_id` values, and correct the copy against that scoped guidance. Use @context/lightning-positioning.md only as a fallback mirror when the connector is unavailable and the sidecar records the blocker.

### AEO/GEO Rewrite Requirements

Before drafting, complete AEO/GEO variable resolution from the analysis report, current article, generated vault context binding, repo context fallback, target keyword, and sourced research:
- `topic`
- `audience`
- `main_question`
- `related_questions`
- `tone`
- **FAQ Source Policy**: Each visible non-owned FAQ URL needs an exact `FAQ Proof Map` row with `FAQ`, `URL`, `Source class`, `Competitor check`, and `Support`; source class must be `neutral` or `non_competing_expert`. Competitor-owned FAQ sources: prohibited.
- **Permitted FAQ evidence**: regulators, standards bodies, universities, trade associations, independent research/editorial, and non-competing experts. Simpro-owned links are optional reader resources, not proof.
- **Vendor-specific FAQs**: remove or reframe the question when compliant evidence is unavailable and leave vendor evidence in comparison or vendor-specific body copy.
- `expertise`
- `length`: set an intent/evidence-complete word target from the Reader Contract, search intent, source depth, and useful competitor context

Required rewrite inputs:
- **PAA/FAQ provenance**: Cite the source for selected questions: AnswerSocrates, SERP, Reddit, YouTube, or a user PAA/FAQ CSV. If using AnswerSocrates, save or cite `research/paa-questions-[topic-slug]-[YYYY-MM-DD].md`. If no sourced question set exists, collect one or record the blocker before writing.
- **Question selection**: Select 3-5 closest questions, label intent, write an insight summary, write a suggested blog focus, and assign each question to an H2, H3, or FAQ answer format.
- **FAQ quality gate**: Run `python data_sources/modules/faq_answer_quality_guard.py [file] --fail-on error`; `/publish-readiness` runs it automatically.
- **FAQ answer quality**: Each visible answer starts with a 40-60 word direct-answer paragraph and includes at least 1 authoritative non-owned public evidence link. A Source Map or FAQ Proof Map can document the same evidence but cannot replace that reader-facing link.
- **Source Map**: Document each external source, the claim it supports, the natural anchor text, and the target section.
- **E-E-A-T Proof Map**: Resolve E-E-A-T proof details, Experience, Expertise, and Authority/Trust before drafting. Experience includes customer case studies, customer outcomes, review-site experience evidence / VoC themes, implementation/support themes, user pain, and field workflow examples. Review narratives count as first-hand customer experience when reviewers describe product use, implementation, support, switching, pains, outcomes, or workflows. Expertise includes product/feature knowledge, source-backed workflow explanations, expert quotes, author/reviewer metadata, and Simpro workflow specificity. Authority/Trust includes public research, case-study URLs, review-site/source links, limitations, caveats, and no invented proof.
- **Proof routing**: Start with connector-approved claims for the intended public use mode and read the supporting `resource_id` values. Bind public metrics, quotes, and proof themes to their `claim_id` and public URL. Receipt-bound context-backed metrics are valid only when public copy uses public-facing source links. Use @context/internal-links-map.md, @context/features.md, @context/competitor-analysis.md, or future review-context files only as downstream fallback mirrors when the connector is unavailable and the sidecar records the blocker. For review-site evidence, capture platform, URL, date checked, product/competitor, experience pattern, evidence summary, and whether any exact quote or rating claim was approved. Use review-derived stories as paraphrased, source-backed experience patterns by default. Exact quotes, named reviewers, star ratings, badges, rankings, aggregate ratings, and category claims require current source verification and claim-level approval. Never publish a metric or quote solely because it appears in a repo-local file.
- **403 replacement rule**: If a DOL, Capterra, G2, Trustpilot, Google Play, or other public research/source URL returns 401, 403, or `manual_review`, do not remove the citation unless an equivalent resolved public source link replaces it in public copy or the supported claim is removed. Source Map notes must document both the rejected 403 URL and the replacement URL. Full policy and the `public_research_link_guard.py` gate live in `context/aeo-geo-blog-strategy.md`.
- **Review proof routing**: For review-derived E-E-A-T stories, automatically run `customer_proof_selector.py` with `--slate --roles experience_story --require-eeat-story`, then run the review story identity gate from the required stack below. Use `context/aeo-geo-blog-strategy.md` for Review Story Selection, Review Site Theme Selection, Capterra theme use, exact-quote, rating, and metric boundaries.
- **Reader Contract**: Before rewrite planning, document Primary reader, Sophistication level, Trigger problem, Existing belief, Decision or task helped, Distinctive angle, Promised payoff, Funnel stage, and Exclusions. Use it to set an intent/evidence-complete word target, natural terminology coverage, critical keyword placement, semantic variations, keyword-stuffing detection, CTA treatment, and section order.

## SERP Strategy Decision

After the Reader Contract, record the verified SERP observation source, dominant observed content type, every observed feature, recurring extracted structure, and qualified must-fill gaps. Match the dominant observed content type and target every applicable feature by default. Any deviation requires a documented Reader Contract exception. If verified SERP context is unavailable, mark the decision unresolved and do not invent observations or silently waive the handoff.
- **Optional proof-backed customer/review POV**: Use a proof-backed customer/review POV only when it improves the rewrite objective. Editorial scenes: 0-2 editorial scenes when they materially improve understanding. Named people or businesses require approved proof; Unnamed workflow scenarios are explanatory only; invented names, dates, metrics, quotes, and outcomes are prohibited.
- **Customer proof selection governance**: Before selecting or drafting proof, resolve `topic`, `title`, and `objective`, automatically run `python data_sources/modules/customer_proof_selector.py "[topic]" --title "[title]" --objective "[objective]" --context-pack "research/context-pack-[topic-slug].json" --context-receipt "research/context-receipt-[topic-slug].json" --evidence-output "research/customer-proof-selector-evidence-[topic-slug].json" --slate --roles metric,quote,theme,experience_story --require-eeat-story --limit 10`, and write the generated selector-first `Customer Proof Slate` to the validation sidecar. If inputs are missing, resolve them from the brief/context or stop before drafting customer proof. If the selector fails, write the blocker into the sidecar and do not invent proof. experience_story consideration is required and E-E-A-T story usage is optional. If no story fits, use `Selected: [none]` with section-specific rejection reasons. Full policy lives in `context/aeo-geo-blog-strategy.md`.
- **Fred Voccola authority evaluation**: Resolve `topic`, `title`, and `objective`, then automatically run `python data_sources/modules/fred_authority_selector.py "[topic]" --title "[title]" --objective "[objective]" --context-pack "research/context-pack-[topic-slug].json" --context-receipt "research/context-receipt-[topic-slug].json" --slate --limit 5` and write the complete `Fred Voccola Authority Selection` block from `context/aeo-geo-blog-strategy.md` to the validation sidecar. Evaluation is mandatory and public use is optional. The selector defaults to `Selected: none`; select a source explicitly only after reviewing it and confirming direct topical support. If the selector, connector, context pack, or receipt validation fails, record `Evaluation status: blocked` and the blocker; do not invent Fred evidence or continue to Fred public use.
- **Recent-use proof diversity**: Treat any `recent_uses_90d` value above 0 as a proof-diversity warning, not only sources marked `overused`. Before claiming a proof source is underused, inspect the usage ledger and run a live repo scan across `drafts/`, `rewrites/`, `research/`, and `published/` for the proof ID, public URL, and customer name. If the live repo scan finds public-copy usage missing from the ledger, backfill `context/customer-proof-usage-ledger.json`, rerun proof health and selector checks, and document the backfill in the validation sidecar. Prefer an approved zero-recent-use source when one fits the same role, or document why no stronger underused approved proof fits. If a recently used or overused proof source is still selected, document why no stronger underused approved proof fits.
- **Selected customer proof mining**: When selected customer proof appears in public copy, add `Selected Customer Proof Mining` to the validation sidecar. Selector chooses candidates; proof mining reads the selected public URL before the writer decides quote, metric, POV/story, theme, or omit use. Full policy lives in `context/aeo-geo-blog-strategy.md`.
- **Proof-index health**: Run `python data_sources/modules/customer_proof_index_health.py --index context/customer-proof-index.json --ledger context/customer-proof-usage-ledger.json` before adding proof candidates, and review both recently used and overused proof rows.
- **Proof-index intake**: Add new proof candidates through `context/customer-proof-intake-template.csv` and validate with `python data_sources/modules/customer_proof_index_intake.py validate [input.csv] --index context/customer-proof-index.json` before relying on them in selector slates.
- **Customer Proof Pack**: Resolve selected proof, approved quotes/metrics, and excluded claims before placing customer proof. If the pack is partial or blocked, omit unsupported claims.
- **Proof routing**: Proof infrastructure belongs only in the validation sidecar. The rewrite and change summary record only the sidecar path and status so there is one authoritative proof state.
- **down-funnel internal link**: Every rewrite must include at least 1 contextual body link to `/industries`, `/industries/...`, `/solutions/...`, or `/features/...` from @context/internal-links-map.md. Prefer the specific industry page when industry intent is clear, the `https://www.simprogroup.com/industries` hub for broad trades or general industry topics, the relevant solution page for category/workflow topics, and the relevant feature page for feature/workflow topics. Anchor text must match the destination keyword or an approved anchor example from @context/internal-links-map.md.
- **Functional feature/solution anchors**: Feature and solution links must use function-bearing anchor text that explains the workflow, category, or outcome behind the destination. A feature or solution name alone is not enough. Use anchors like "field service payments," "accounts receivable follow-up with Fast Cash," or "field service management software" instead of "Simpro Payments," "Fast Cash," or "Simpro Premium."
- **Simpro web copy rules**: Use numerals for cardinal numbers, including 1-9. Do not block source-visible metric wording when a public proof source spells out the number; preserve the supported claim wording and rely on Metric Proof Pack, numeric claim source guard, and source support guard for proof. Because comma decisions are grammar/context dependent. No comma when the because clause is essential to the sentence meaning. Use a comma when the because clause is nonessential, contrastive, or needed to prevent misreading. Review negative constructions carefully because comma placement can change meaning. Only 1 link per paragraph. Move the second link to a separate paragraph or remove it. Do not write source/proof meta-commentary such as "that case study is useful for this topic" or "this source is relevant for the article." Translate proof into audience-facing takeaways, outcomes, or workflow lessons.
- **Schema notes**: For standard blog posts, include BlogPosting and BreadcrumbList. Add FAQPage and nested Question and Answer inside FAQPage only when visible FAQs exist. Include ImageObject for the featured image or logo, and Organization as publisher reference only, not a separate full schema block. For public Markdown blog artifacts, place this as a `schema_notes` field in the top YAML frontmatter block, between the opening and closing --- delimiters. If a named author is present, include `author` in frontmatter and map it to `Person as author`. If no named author is available, omit `author`, omit `Person as author`, keep `Organization` as publisher reference only, and record the no-author decision in the blog assembly BOM and validation sidecar. Use VideoObject only when a video is embedded.

Do not invent PAA questions, customer proof, author names, reviewer names, search volume, ranking data, or source-backed claims. If proof is missing, mark it as missing and keep the claim out of the rewrite.

### Rewrite Strategy

#### Determine Scope
Based on analysis, classify the rewrite level:
- **Light Update (20-30% changes)**: Fix stats, add keywords, improve meta
- **Moderate Refresh (40-60% changes)**: Restructure sections, expand content, update examples
- **Major Rewrite (70-90% changes)**: New outline, significant expansion, fresh angle
- **Complete Overhaul (90%+ changes)**: Essentially new article on same topic

#### What to Keep
- Sections that are still accurate and comprehensive
- Unique insights or perspectives that remain valuable
- Well-performing structure or formatting
- Examples or case studies that are still relevant
- Internal links that remain appropriate

#### What to Update
- Outdated statistics with current data (note date/source)
- Old screenshots or examples with current versions
- Deprecated terminology or processes
- Missing keywords in headings and body
- Weak or missing meta title/description
- Insufficient internal links

#### What to Add
- New sections only where competitive research exposes a reader-payoff, evidence, or task-completion gap
- Recent industry trends or developments
- Additional examples or use cases
- Better introduction hook if current one is weak
- Conclusion that closes the Reader Contract with an intent-appropriate next action
- Missing SEO elements (keywords, links, structure)

#### What to Remove
- Deprecated information that's no longer accurate
- Redundant or repetitive sections
- Overly promotional language (if inconsistent with current brand)
- Outdated examples or references
- Fluff or filler that doesn't add value

### Content Structure
Follow same structure as `/write` command:

#### 1. Updated Headline (H1)
- Optimize with primary keyword if not already present
- Refresh if original title is dated or weak
- Maintain original if it's strong and still optimized

#### 2. Refreshed Introduction
- Update hook with current statistics or trends
- Clarify value proposition if needed
- Ensure primary keyword appears in first 100 words
- Put the direct answer in the first 1-2 sentences before the hook
- Make it compelling for today's reader

#### 3. Improved Body
- **Maintain**: Keep effective sections that are still accurate
- **Expand**: Deepen shallow sections only where more detail improves reader payoff, evidence support, or task completion
- **Add**: Insert new sections to cover content gaps
- **Update**: Refresh stats, examples, and references throughout
- **Restructure**: Reorganize if flow can be improved
- **Optimize**: Integrate natural terminology coverage, critical keyword placement, semantic variations, and keyword-stuffing detection
- **AEO/GEO**: Add 50-60 word direct-answer capsules below the H1 and at least 60% of major H2s
- **Early usable artifact**: Place a filled data table, download link, checklist deliverable, or calculator reference within the first 300 words of body copy, or document a not-applicable reason in the sidecar; policy in `context/aeo-geo-blog-strategy.md`
- **Concrete answers**: If the target query implies a number, range, or template, supply a concrete version with disclaimers as needed; placeholder table scaffolds block publish

#### 4. Strengthened Conclusion
- Update takeaways to reflect new/expanded content
- Re-evaluate the next action using intent-sensitive CTA rules from the Reader Contract; do not add a CTA when none is called for
- End with forward-looking perspective

### SEO Enhancement

#### Keyword Optimization
- **Primary Keyword**: Confirm natural placement in key reader-visible locations
- **Keyword Placement**: Add to H2s if missing
- **Semantic Variations**: Use related keywords naturally
- **First 100 Words**: Confirm primary keyword appears early
- **Natural Integration**: Never force keywords unnaturally

#### Intent-Sensitive CTA Plan
- **ToFu**: ToFu: 0-1 soft resource/action CTA
- **MoFu**: MoFu: one educational next step plus one contextual product CTA
- **BoFu**: BoFu: 2-3 contextual commercial CTAs
- **Thought leadership**: Thought leadership: discussion, reflection, or evidence resource

#### Continuity Pass
- Every section must advance the headline promise from the Reader Contract.
- Each section answers a question created by the previous section.
- No section restarts the article, repeats the introduction, or creates repeated resets.
- Transitions explain a logical relationship, not just a transition word.
- The conclusion must complete the introduction, resolve open loops, and add a useful next action.
- remove or justify any section that does not increase the promised payoff.

#### Internal Linking
- **Review Existing**: Ensure all internal links still work and are relevant
- **Add New Links**: Reference newer content published since original
- **Strategic Placement**: Link to pillar content and related articles
- **Anchor Text**: Use keyword-rich, descriptive anchor text
- **Quantity**: Aim for 3-5+ quality internal links

#### External Linking
- **Update Broken Links**: Replace any dead external links
- **Fresher Sources**: Replace old statistics with recent data
- **Authority**: Ensure external links are to credible sources
- **Relevance**: Remove outdated external references
- **Source Mapping**: Keep each external link tied to the specific claim it supports

#### Meta Elements
- **Meta Title**: Rewrite if not optimized, compelling, or missing the required final `| Brand` suffix
- **Meta Description**: Refresh to highlight updated content
- **URL Slug**: Generally keep original to preserve any rankings
- **Featured Snippet**: Optimize for snippet opportunity if identified

### Quality Assurance

#### Content Accuracy
- Verify all updated statistics and data points
- Ensure technical information is current
- Confirm examples reflect current industry landscape
- Check that product references are up-to-date
- Confirm the public rewrite body does not mention "repo context," context file paths, Source Maps, PAA artifacts, change summaries, or internal proof-path notes. Repo-local context remains editorial fallback or operational state only when the connector is unavailable; it never becomes public-claim approval authority. Record the connector-unavailable blocker and omit unsupported public claims.
- Confirm PAA/FAQ provenance, Source Map, E-E-A-T Proof Map, direct-answer capsules, and schema notes are present for moderate, major, and complete rewrites
- Confirm every context-backed metric uses a public-facing source link, such as a case-study URL, review-site URL, or public research source.

#### Brand Alignment
- Maintain brand voice from the vault first; @context/brand-voice.md is fallback mirror context only
- Follow vault terminology first; @context/style-guide.md is fallback mirror context only
- Ensure messaging aligns with current positioning
- Keep focus on target audience needs
- For Lightning-specific rewrites, use connector-discovered Lightning `resource_id` guidance to fix unprefixed customer-facing Lightning references, JustAsk-as-agent errors, Cooper role confusion, incorrect agent names, first-reference "the trades" category wording, unsupported proof claims, and stale pricing or competitor claims. Public Lightning claims require receipt approval.

#### Readability
- Improve sentence structure if needed
- Break up long paragraphs
- Add subheadings for better scannability
- Use formatting (bold, lists) to enhance clarity

## Output
Provides updated article with change tracking:

### 1. Rewritten Article
Complete markdown article with all improvements:
- Updated headline if changed
- Refreshed introduction
- Improved and expanded body sections
- Strengthened conclusion
- All new meta elements

### 2. Change Summary
```
---
Original Publication Date: [if known]
Rewrite Date: [YYYY-MM-DD]
Rewrite Scope: Light / Moderate / Major / Complete
Word Count Change: [original count] → [new count]
Primary Keyword: [keyword]
SEO Score Improvement: [estimated improvement]

Reader Contract:
- Primary reader: [role, business type, region, or maturity level]
- Sophistication level: [beginner / intermediate / expert / mixed, plus what the reader already understands]
- Trigger problem: [moment, decision, or operational pressure]
- Existing belief: [what they already believe, worry about, or tried]
- Decision or task helped: [decision, task, or understanding the rewrite helps complete]
- Distinctive angle: [why this rewrite exists beyond matching the SERP]
- Promised payoff: [concrete reader payoff the headline and intro must deliver]
- Funnel stage: [ToFu / MoFu / BoFu / thought leadership]
- Exclusions: [what the rewrite will not cover, rank, quantify, or claim]

Continuity Pass:
- Every section advances the headline promise.
- Each section answers a question created by the previous section.
- Repeated resets were removed.
- Transitions explain a logical relationship.
- The conclusion completes the introduction.
- remove or justify any weak section that does not increase the promised payoff.

Major Changes:
- [Summary of significant updates]
- [New sections added]
- [Content removed/consolidated]

SEO Improvements:
- [Natural terminology coverage, semantic variations, critical keyword placement, and stuffing checks]
- [Internal links added]
- [Meta element updates]

Content Updates:
- [Statistics refreshed]
- [Examples updated]
- [New industry trends added]

Validation and AEO/GEO Status:
- Validation sidecar path and status: [research/validation-[topic-slug]-[YYYY-MM-DD].md; ready / partial / blocked]
- PAA artifact path: [research/paa-questions-[topic-slug]-[YYYY-MM-DD].md or not available]
- FAQ quality gate: [pass / blocked]
- Schema notes: [present in public frontmatter; VideoObject only when a video is embedded]
---
```

### 3. Before/After Comparison
For major changes, note key differences:
- Original headline vs. new headline
- Original intro vs. new intro
- Sections added or removed
- Sections completed to their caller-supplied intent/evidence targets without padding
- SEO element improvements

## File Management
After completing the rewrite, save to:
- **File Location**: `rewrites/[topic-slug]-rewrite-[YYYY-MM-DD].md`
- **File Format**: Markdown with change summary frontmatter
- **Naming Convention**: Use original slug + "rewrite" + current date

Example: `rewrites/content-marketing-guide-rewrite-2025-10-15.md`

Also save the change summary separately:
- **File Location**: `rewrites/changes-[topic-slug]-[YYYY-MM-DD].md`

## Validation Sidecar

Proof infrastructure belongs only in the validation sidecar at `research/validation-[topic-slug]-[YYYY-MM-DD].md`; the rewrite and change summary retain only its sidecar path and status. Do not put an `Editorial Validation Appendix`, `PAA/FAQ Provenance`, `Metric Proof Pack`, `Source Map`, `Customer Proof Pack`, `FAQ Proof Map`, or structured data plan in the publishable rewrite.

Preferred publish readiness command:
```bash
/publish-readiness [file] --proof-sidecar research/validation-[topic-slug]-[YYYY-MM-DD].md --context-request research/context-request-[topic-slug].json --context-pack research/context-pack-[topic-slug].json --context-receipt research/context-receipt-[topic-slug].json --assembly-bom research/blog-assembly-bom-[topic-slug]-[YYYY-MM-DD].json
```

Run `/publish-readiness [file] --proof-sidecar research/validation-[topic-slug]-[YYYY-MM-DD].md --context-request research/context-request-[topic-slug].json --context-pack research/context-pack-[topic-slug].json --context-receipt research/context-receipt-[topic-slug].json --assembly-bom research/blog-assembly-bom-[topic-slug]-[YYYY-MM-DD].json` to confirm the rewrite is clean and all proof, Context Binding, BOM, URL validation, source support, content score, and AEO/GEO gates pass. The command reads the validation sidecar without exposing proof infrastructure in public copy.

## Automatic Scrub, Publish Readiness, And Optimize

**CRITICAL**: Immediately after saving the rewritten article file, automatically invoke the content scrubber, run `/publish-readiness`, then run `/optimize`.

### Why This Matters
AI-generated content often contains invisible Unicode marks and characteristic punctuation patterns. Scrubbing handles cleanup. The linter handles AI-writing detection and Simpro style enforcement.

### Scrub, Publish Readiness, And Optimize Process
1. **Invoke Scrubber**: Run `/scrub [file-path]` on the saved rewritten article file
2. **Invoke Publish Readiness**: Run `/publish-readiness [file-path] --proof-sidecar research/validation-[topic-slug]-[YYYY-MM-DD].md --context-request research/context-request-[topic-slug].json --context-pack research/context-pack-[topic-slug].json --context-receipt research/context-receipt-[topic-slug].json --assembly-bom research/blog-assembly-bom-[topic-slug]-[YYYY-MM-DD].json`
3. **Check Gates**: General content quality must be 85/100 or higher, AEO/GEO must be 90/100 or higher, and all blocking gates must pass
4. **Invoke Optimizer**: Run `/optimize [file-path]` after all non-scoring gates pass. If content quality or AEO/GEO fails, use `/optimize` inside the AEO/GEO Recovery Loop and rerun `/publish-readiness`.
5. **Automatic Execution**: This should happen automatically, not require user action
6. **Timing**: Must occur immediately after file save, before optimization agents
7. **Scope**: Scrub and publish-readiness checks apply to the main rewritten article file only; proof maps live in the validation sidecar.
8. **Error Handling**: If `/publish-readiness` fails, fix the highest-severity gate it reports. Use `context/aeo-geo-blog-strategy.md` for proof policy and individual module debugging. Review `because` grammar in context during each revision loop, fix the sentence when comma placement changes or clarifies meaning, and rerun `/scrub` plus `/publish-readiness`. If score gates fail after 2 iterations, route to `review-required/` with scoring details.
9. **AI copy avoid-rule errors**: Fix copy avoid-rule errors before `/optimize` or handoff. The linter blocks modal verbs, passive voice, repeated starts, vague generalizations, filler words, and long sentences in Simpro web copy.

## AEO/GEO Recovery Loop

An AEO/GEO score below 90/100 is a repair trigger, not a reporting endpoint. Unless the user explicitly requested a read-only audit, the LLM must continue in the same workflow:

1. Review every failed check in `aeo_geo.checks` and the scorer's `priority_fixes`.
2. Classify each failure as a public-copy gap, validation-sidecar/proof gap, or scorer or parser false negative.
3. If the article visibly satisfies the written requirement but scoring misses it, add a regression test and fix the scorer or parser false negative. Do not distort accurate, brief-approved copy to satisfy brittle matching.
4. Apply the top 3-5 fixes that address root causes. Do not invent PAA questions, claims, proof, metrics, quotes, or customer experience to gain points.
5. Rerun `/scrub`, the AI copy linter, URL validation, regenerate Context Binding with `context_binding_generator.py`, update the blog assembly BOM, and rerun `/publish-readiness [file] --proof-sidecar [sidecar] --context-request [request] --context-pack [pack] --context-receipt [receipt] --assembly-bom [bom]`.
6. Repeat once if needed. If AEO/GEO remains below 90/100 after 2 iterations, route the artifact to `review-required/` with the score, failed checks, attempted fixes, and any external evidence or authority blocker.

`/optimize` is allowed inside this recovery loop when all proof, source, URL, and public-artifact gates pass but content quality or AEO/GEO does not. Final handoff still requires content quality of at least 85/100, AEO/GEO of at least 90/100, and every blocking gate to pass.

### What Gets Cleaned
- Invisible Unicode watermarks (zero-width spaces, BOMs, format-control characters)
- Em-dashes replaced with contextually appropriate punctuation (commas or periods)
- Whitespace normalization and formatting cleanup
- All changes preserve content meaning and markdown structure

### Verification
The scrubber will display statistics:
- Unicode watermarks removed
- Format-control characters removed
- Em-dashes replaced

The AI copy linter will display:
- Error count
- Warning count
- Line-level findings with suggested fixes

The content scorer will display:
- General content quality score
- AEO/GEO score
- Failed checks and priority fixes

URL validation will display:
- Resolved URL count
- Unresolved URL count
- Manual-review URL count

The Metric Proof Pack guard will display:
- Metric Proof Pack blocker count
- Line-level findings for missing `Search log`, missing `Approved metric` rows, or Evidence not found in the proof source

The numeric claim source guard will display:
- Unsupported metric, statistic, or numeric business claim count
- Line-level findings for claims missing a public URL or local proof artifact

The FAQ proof guard will display:
- FAQ proof blocker count
- Line-level findings for generic FAQ openers and FAQ answers missing an authoritative non-owned public evidence link in visible copy

The PAA provenance guard will display:
- PAA provenance blocker count
- Line-level findings for FAQ questions missing exact saved source-artifact provenance

The source support guard will display:
- Source support blocker count
- Line-level findings for claims whose Evidence is not visible in the cited source
- Named customer metric blockers when metrics are not in Customer Proof Pack Approved metrics
- Exact quote/testimonial blockers when quotes are not in Customer Proof Pack Approved quotes

URL validation confirms destinations resolve; it does not prove the page supports the claim. Use `context/aeo-geo-blog-strategy.md` for proof, source support, metric, FAQ, PAA, quote, testimonial, and customer metric boundaries.

### Example Workflow
1. Rewrite article and save to `rewrites/article-name-rewrite-2025-10-31.md`.
2. Run `/scrub`, then `/publish-readiness rewrites/article-name-rewrite-2025-10-31.md --proof-sidecar research/validation-article-name-2025-10-31.md --context-request research/context-request-article-name.json --context-pack research/context-pack-article-name.json --context-receipt research/context-receipt-article-name.json --assembly-bom research/blog-assembly-bom-article-name-2025-10-31.json`.
3. Confirm 85/100 general content quality, 90/100 AEO/GEO, and passing proof gates.
4. Then run `/optimize rewrites/article-name-rewrite-2025-10-31.md`.
5. If blockers remain, revise once, review `because` grammar in context, and rerun the same stack.

This keeps cleanup separate from AI copy detection and scoring before optimization.

## Automatic Agent Execution
After saving, scrubbing, linting, scoring, and optimizing the rewritten article, run optimization agents:

### 1. SEO Optimizer Agent
- Review rewritten content for SEO improvements
- Compare against original SEO metrics
- Provide optimization score

### 2. Meta Creator Agent
- Generate fresh meta title/description options
- Test multiple variations for click-through optimization

### 3. Internal Linker Agent
- Ensure all internal links are current and relevant
- Suggest additional linking opportunities from newer content

### 4. Keyword Mapper Agent
- Verify keyword integration improvements
- Confirm critical keyword placement, semantic coverage, reported density, and stuffing risk

## Next Steps
After rewrite completion:
1. Review change summary and ensure all updates are intentional
2. Compare to original to verify improvements
3. Run `/optimize` for final polish if needed
4. Move to `/published` when ready
5. Note original URL to ensure proper redirect/replacement

This ensures every rewritten article is significantly improved while maintaining what worked in the original version.
