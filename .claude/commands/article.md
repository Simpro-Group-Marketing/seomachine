# Article Command

## Context Binding Regeneration (MANDATORY)

After the final content mutation, regenerate the machine-owned binding before `/publish-readiness`:

```bash
python data_sources/modules/context_binding_generator.py "$FILE_PATH" --proof-sidecar "$PROOF_SIDECAR" --context-request "$CONTEXT_REQUEST" --context-pack "$CONTEXT_PACK" --context-receipt "$CONTEXT_RECEIPT"
```

Run this again after every scrub, optimization, or editorial change that modifies public copy. A stale article hash blocks handoff.

### After Optimization Mutations

All optimizer outputs and manual edits are content mutations. After optimization mutations, rerun `/scrub`, regenerate Context Binding with `context_binding_generator.py`, update `research/blog-assembly-bom-[topic-slug]-[YYYY-MM-DD].json`, then rerun `/publish-readiness [file] --proof-sidecar research/validation-[topic-slug]-[YYYY-MM-DD].md --context-request research/context-request-[topic-slug].json --context-pack research/context-pack-[topic-slug].json --context-receipt research/context-receipt-[topic-slug].json --assembly-bom research/blog-assembly-bom-[topic-slug]-[YYYY-MM-DD].json`.

A unified content creation pipeline that produces comprehensive, SEO-optimized articles through mandatory research, strategic planning, and section-by-section writing.

For every Simpro blog, retrieve current voice and tone guidance through the vault connector by semantic search and `resource_id` reads. Named-author Simpro blogs and thought leadership may use first-person judgment, contractions, operational scenes, decisive opinions, and short punchlines. Author opinion must remain distinguishable from empirical fact. Metrics, market comparisons, product status, roadmap statements, and commercial claims remain proof gated. Em dashes are prohibited. Product pages and landing pages retain their existing restrained channel treatment.

## Usage
`/article [topic]`

**Examples:**
- `/article "Best Project Management Tools for Small Teams"`
- `/article "Content Marketing Strategy Guide 2025"`
- `/article "How to Migrate from Competitor to Your Product"`

## What This Command Does

Creates high-quality articles by enforcing a 5-step pipeline where **research is mandatory, not optional**:

```
STEP 0: AEO/GEO Setup          -> Resolve variables + collect AnswerSocrates PAA
STEP 1: SERP Analysis           → See what Google rewards TODAY
STEP 2: Social Research         → Mine Reddit + YouTube for real insights
STEP 3: Article Planning        → Section-by-section strategy
STEP 4: Section Writing         → Write/edit each section individually
```

This prevents the "AI knows everything" trap that produces generic content matching competitors instead of beating them.

## When to Use This vs /write

| Scenario | Command |
|----------|---------|
| Comprehensive new article | `/article` |
| Competitive topics | `/article` |
| Topics where you need to beat existing content | `/article` |
| Quick drafts from existing research | `/write` |
| Simple updates to existing content | `/write` |

---

## STEP 0: AEO/GEO Setup (MANDATORY)

**Every new `/article` run MUST collect AnswerSocrates PAA questions with Playwright MCP before planning.**

### Variable Resolution

Before opening the browser or drafting, resolve every variable except `length` from the user prompt, generated vault context binding, repo context fallback, existing research, and current SERP/PAA evidence. Resolve `length` only after the Reader Contract and verified research context are available:

| Variable | Resolution Rule |
|----------|-----------------|
| `topic` | Use the user prompt or topic file; ask if missing. |
| `audience` | Derive through connector semantic search and `resource_id` reads for audience and vertical context; @context/brand-voice.md is fallback mirror context only when the connector is unavailable. |
| `main_question` | Infer from target keyword, SERP intent, or user prompt; ask if no primary question is clear. |
| `related_questions` | Use AnswerSocrates PAA, SERP, Reddit, YouTube, or a user-provided PAA/FAQ CSV. |
| `tone` | Use connector semantic search and `resource_id` reads for current messaging and style guidance; @context/brand-voice.md and @context/style-guide.md are fallback mirrors only when the connector is unavailable. |
| `expertise` | Use connector semantic search and `resource_id` reads for product/feature knowledge, plus receipt-bound approved customer proof, expert quotes, and author/reviewer data. Repo-local context is fallback only when the vault is unavailable and the validation sidecar records the explicit vault-unavailable blocker. |
| `length` | Set an intent/evidence-complete word target from the Reader Contract, search intent, source depth, and useful competitor context. |

If a non-length variable cannot be answered by the repo or research, ask the user for only that missing variable. Leave `length` unresolved until Reader Contract planning rather than asking for a mechanical target. Do not synthesize PAA questions, expert quotes, customer claims, search volume, or ranking evidence.
Customer proof routing: before citing customer proof, the slash-command workflow must resolve `topic`, `title`, and `objective`, automatically run `python data_sources/modules/customer_proof_selector.py "[topic]" --title "[title]" --objective "[objective]" --context-pack "research/context-pack-[topic-slug].json" --context-receipt "research/context-receipt-[topic-slug].json" --evidence-output "research/customer-proof-selector-evidence-[topic-slug].json" --slate --roles metric,quote,theme,experience_story --require-eeat-story --limit 10`, and write a selector-first `Customer Proof Slate` to the validation sidecar so metric, quote, theme, and optional story options are compared before drafting. If inputs are missing or the selector fails, stop before drafting customer proof, record the blocker in the sidecar, and do not invent proof. experience_story consideration is required and E-E-A-T story usage is optional; if no story fits, use `Selected: [none]` with section-specific rejection reasons. Treat any `recent_uses_90d` value above 0 as a proof-diversity warning. Before claiming a proof source is underused, inspect the usage ledger and run a live repo scan across `drafts/`, `rewrites/`, `research/`, and `published/` for the proof ID, public URL, and customer name. If the live repo scan finds public-copy usage missing from the ledger, backfill `context/customer-proof-usage-ledger.json`, rerun proof health and selector checks, and document the backfill in the validation sidecar. If a recently used or overused proof source is still selected, document why no stronger underused approved proof fits. Run `python data_sources/modules/customer_proof_index_health.py --index context/customer-proof-index.json --ledger context/customer-proof-usage-ledger.json` before adding proof candidates. Add new proof candidates through `context/customer-proof-intake-template.csv` and validate with `python data_sources/modules/customer_proof_index_intake.py validate [input.csv] --index context/customer-proof-index.json` before relying on them in selector slates. Selected public proof must match a receipt-approved connector claim bound to its `claim_id`, `resource_id`, permitted use mode, and public URL. Repo-local proof indexes, usage ledgers, and link maps remain operational routing inputs only; when the vault is unavailable, record the vault-unavailable blocker and omit unsupported public claims. Use exact quotes only when the approved connector evidence and source-visible public page support the wording. Full policy lives in `context/aeo-geo-blog-strategy.md`.
Fred Voccola authority evaluation: resolve `topic`, `title`, and `objective`, then automatically run `python data_sources/modules/fred_authority_selector.py "[topic]" --title "[title]" --objective "[objective]" --context-pack "research/context-pack-[topic-slug].json" --context-receipt "research/context-receipt-[topic-slug].json" --slate --limit 5` and write the complete `Fred Voccola Authority Selection` block from `context/aeo-geo-blog-strategy.md` to the validation sidecar. Evaluation is mandatory and public use is optional. The selector defaults to `Selected: none`; select a source explicitly only after reviewing it and confirming direct topical support. If the selector, connector, context pack, or receipt validation fails, record `Evaluation status: blocked` and the blocker; do not invent Fred evidence or continue to Fred public use.
Review-site experience evidence / VoC routing: cite public review-site themes with source links when they show first-hand customer experience with product use, implementation, support, switching, pains, outcomes, or workflows. Capture platform, URL, date checked, product/competitor, experience pattern, evidence summary, and whether any exact quote/rating claim was approved. Use a proof-backed customer/review POV only when it improves the article objective; if no actual person or business POV fits, omit the story. Do not use fictional named personas, exact quotes, named reviewers, star ratings, badges, rankings, aggregate ratings, or category-leadership claims unless they have current source verification and brief-level approval.

### E-E-A-T Proof Map Inputs

Before planning or drafting, resolve an E-E-A-T Proof Map:
- **Experience**: Customer case studies, customer outcomes, review-site experience evidence / VoC themes, implementation/support themes, user pain, and field workflow examples.
- **Expertise**: Product/feature knowledge, source-backed workflow explanations, expert quotes, author/reviewer metadata, and Simpro workflow specificity.
- **Authority/Trust**: Public research, case-study URLs, review-site/source links, limitations/caveats, and no invented proof.
- **Fallback context sources**: Use repo-local mirrors only when the vault connector is unavailable, record the explicit vault-unavailable blocker in the validation sidecar, and omit unsupported public claims. Repo-local context may help with operational routing but cannot approve proof or override connector `resource_id`, `claim_id`, or receipt decisions.
- **Public-copy rule**: Context-backed metrics are valid only when the article body uses public-facing source links, such as the public case-study URL, review-site URL, or public research source; context-backed proof is never cited as internal context.
- **403 replacement rule**: If a DOL, Capterra, G2, Trustpilot, Google Play, or other public research/source URL returns 401, 403, or `manual_review`, do not remove the citation unless an equivalent resolved public source link replaces it in public copy or the supported claim is removed. Source Map notes must document both the rejected 403 URL and the replacement URL. Full policy and the `public_research_link_guard.py` gate live in `context/aeo-geo-blog-strategy.md`.

Proof infrastructure belongs only in the validation sidecar. The article plan records only the validation sidecar path and status so there is one authoritative proof state.

### Reader Contract

Before article planning, write a `Reader Contract` block. This is an editorial planning control, not public proof infrastructure:

- **Primary reader**: the role, business type, region, or maturity level the article is written for.
- **Sophistication level**: beginner, intermediate, expert, or mixed, with one sentence explaining what the reader already understands.
- **Trigger problem**: the moment, decision, or operational pressure that brought the reader to the article.
- **Existing belief**: what the reader likely already believes, worries about, or has tried.
- **Decision or task helped**: the decision, task, or understanding the article will help them complete.
- **Distinctive angle**: why this article deserves to exist beyond matching the SERP.
- **Promised payoff**: the concrete reader payoff the headline and intro must deliver.
- **Funnel stage**: ToFu, MoFu, BoFu, or thought leadership.
- **Exclusions**: what the article intentionally will not cover, rank, quantify, or claim.

Use the contract to set an intent/evidence-complete word target, natural terminology coverage, critical keyword placement, semantic variations, and keyword-stuffing detection. Do not expand a complete article to satisfy a universal length target or add exact-match phrases to chase density.

### Simpro Web Copy Rules

- Use numerals for cardinal numbers, including 1-9.
- Do not block source-visible metric wording when a public proof source spells out the number; preserve the supported claim wording and rely on Metric Proof Pack, numeric claim source guard, and source support guard for proof.
- Because comma decisions are grammar/context dependent. No comma when the because clause is essential to the sentence meaning. Use a comma when the because clause is nonessential, contrastive, or needed to prevent misreading. Review negative constructions carefully because comma placement can change meaning.
- Only 1 link per paragraph. Move the second link to a separate paragraph or remove it.
- Do not write source/proof meta-commentary such as "that case study is useful for this topic" or "this source is relevant for the article." Translate proof into audience-facing takeaways, outcomes, or workflow lessons.

### Down-Funnel Internal Link Rule

Every article must include at least 1 contextual down-funnel internal link to `/industries`, `/industries/...`, `/solutions/...`, or `/features/...` from @context/internal-links-map.md. Prefer the specific industry page when industry intent is clear, the `https://www.simprogroup.com/industries` hub for broad trades or general industry topics, the relevant solution page for category/workflow topics, and the relevant feature page for feature/workflow topics. Anchor text must match the destination keyword or an approved anchor example from @context/internal-links-map.md.

Feature and solution links must use function-bearing anchor text that explains the workflow, category, or outcome behind the destination. A feature or solution name alone is not enough. Use anchors like "field service payments," "accounts receivable follow-up with Fast Cash," or "field service management software" instead of "Simpro Payments," "Fast Cash," or "Simpro Premium."

### AnswerSocrates PAA Collection

Use Playwright MCP on `https://answersocrates.com`:

1. `browser_navigate` to AnswerSocrates.
2. `browser_snapshot` to identify the query input and submit control.
3. Enter `main_question`; if missing, enter `topic`.
4. Submit using snapshot-derived targets only. Do not hard-code selectors.
5. Wait for results and extract visible complete natural-language questions with `browser_evaluate`.
6. Save results to `research/paa-questions-[topic-slug]-[YYYY-MM-DD].md`.

If AnswerSocrates shows keyword fragments or query modifiers instead of complete questions, save them as query-fragment notes only and do not use them as FAQ headings or selected questions. Collect a cleaner PAA/FAQ source from AnswerSocrates, SERP, Reddit, YouTube, or a user CSV before adding FAQ copy. If AnswerSocrates is blocked, unavailable, or requires login/CAPTCHA, record the blocker in the PAA artifact and ask the user for a PAA/FAQ CSV export. Do not invent replacement questions.

### PAA Artifact Format

```markdown
# PAA Questions: [Topic]

**Date:** [YYYY-MM-DD]
**Source:** AnswerSocrates via Playwright MCP
**Query Used:** [main_question or topic]
**Status:** [collected / blocked / user-export-needed]

## Raw Questions
- [complete natural-language question]

## Query Fragments Not Eligible For FAQ
- [keyword fragment or query modifier, if present]

## Closest Related Questions
1. [complete natural-language question]
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
|----------|--------|-----------------|---------------|
| [question] | [intent] | [H2/FAQ] | [capsule/list/table/FAQ] |
```

---

## STEP 1: SERP Analysis (MANDATORY)

**You MUST research before writing. No exceptions.**

### Process

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

1. **Search the Target Keyword**
   Use WebSearch to find what's currently ranking:
   ```
   WebSearch: "[topic] industry" OR "[topic] industrying"
   ```

2. **Analyze Top 5 Ranking Articles**
   For each top-ranking article, use WebFetch and document:

   | Element | What to Capture |
   |---------|-----------------|
   | **Structure** | H2 headings, section order, content type |
   | **Word Count** | Approximate length |
   | **Gaps** | Topics missing evidence, explanation, or a useful answer |
   | **Missing Angles** | Perspectives not addressed |
   | **Unsupported Claims** | Statements without data/sources |
   | **Outdated Info** | Old statistics, deprecated tools |
   | **What They Do Well** | Useful elements to evaluate against the Reader Contract |

3. **Build Competitor Gap Blueprint**
   Use verified competitor observations to identify opportunities to beat, not merely match:
   - Recurring, reader-critical gaps found across 3 or more competitors are must-fill when evidence is available
   - Omit a must-fill candidate only when it is irrelevant, redundant, unsupported, or explicitly excluded by the Reader Contract; document the exception
   - Distinctive angles the Reader Contract supports
   - Evidence needed to support useful specificity
   - Outdated information that warrants current, source-verified replacement

### Output
Save to: `research/serp-analysis-[topic-slug]-[YYYY-MM-DD].md`

```markdown
# SERP Analysis: [Topic]

**Date**: [YYYY-MM-DD]
**Keyword**: [target keyword]
**Search Intent**: [informational/commercial/transactional]

## Top Ranking Articles

### 1. [Article Title] - [Domain]
- URL: [url]
- Word Count: ~[count]
- Structure: [H2 headings list]
- Strengths: [what they do well]
- Gaps: [what they miss]
- Outdated: [old info found]

[Repeat for top 5]

## SERP Structure Context
Common ranking sections to evaluate against the Reader Contract:
1. [Common H2 found across multiple articles]
2. [Another common section]
...

## Competitor Gap Blueprint

### MUST-FILL GAPS (recurring, reader-critical, and evidence-supported)
- [Gap 1]: [How to address it, or documented Reader Contract exception]
- [Gap 2]: [How to address it, or documented Reader Contract exception]

### QUALIFICATION REQUIRED
- [Recurring candidate]: [Resolve reader importance and evidence availability before promoting to must-fill, excluding, or omitting]

### DIFFERENTIATION OPPORTUNITIES
- [Unique angle 1]
- [Unique angle 2]

### DATA NEEDED
- [Specific statistic to find]
- [Expert quote needed]

### OUTDATED INFO TO UPDATE
- [Old stat] -> Find a current, source-verified replacement only when it supports the reader payoff
```

---

## STEP 2: Social Research (MANDATORY)

**The best insights aren't in SEO content - they're in Reddit threads and YouTube tutorials.**

### Reddit Research (Visit 5 Actual Threads)

1. **Search Reddit**
   ```
   WebSearch: site:reddit.com [topic] industry
   WebSearch: site:reddit.com r/industrying [topic]
   ```

2. **Visit 5 Promising Threads**
   Use WebFetch on each thread URL. Extract:

   | Element | What to Look For |
   |---------|------------------|
   | **OP's Question** | The specific problem/question |
   | **Top Comments** | Upvoted solutions and advice |
   | **Pain Points** | Frustrations users express |
   | **Success Stories** | Real outcomes with details |
   | **Debates** | Different perspectives |
   | **Recommendations** | What the community endorses |
   | **Real Language** | How actual users talk about this |

3. **Extract Quote Research Leads**
   Preserve each source-visible excerpt with its URL. Treat it as a research lead, not approved public copy, until the proof workflow validates its use.

### YouTube Research (Analyze 5 Videos)

1. **Search YouTube**
   ```
   WebSearch: site:youtube.com [topic] industry tutorial
   WebSearch: site:youtube.com [topic] industry review
   ```

2. **Analyze 5 Video Pages**
   Use WebFetch on each video page. Extract:

   | Element | What to Look For |
   |---------|------------------|
   | **Title & Description** | What they cover |
   | **View Count** | Engagement signal |
   | **Topics Covered** | Main points discussed |
   | **Gaps** | What they don't cover well |
   | **Comments** | What viewers ask about |

### Output
Save to: `research/social-research-[topic-slug]-[YYYY-MM-DD].md`

```markdown
# Social Research: [Topic]

**Date**: [YYYY-MM-DD]

## Reddit Insights

### Thread 1: [Title]
- URL: [url]
- OP's Question: "[quote]"
- Key Insight: [summary]
- Quote research lead: "[source-visible excerpt plus URL; not approved for public use until proof validation]"

[Repeat for 5 threads]

### Pain Points Identified
- [Pain point 1]
- [Pain point 2]

### Success Stories Found
- [Story with specific details and preserved source URL]
- Research lead only: preserve the source URL and do not publish a name, quote, metric, or outcome until the proof workflow approves it

### Real User Language (Research Vocabulary Leads Only)
- Vocabulary lead: [phrase]; source mapping and approval are required before public quotation or "users say" attribution

## YouTube Insights

### Video 1: [Title] - [Channel]
- URL: [url]
- Views: [count]
- Topics Covered: [list]
- Gaps: [what they miss]
- Top Comment Theme: [what viewers ask]

[Repeat for 5 videos]

### Content Gaps in Video
- [Topic tutorials don't cover well]

### Expert Takes (Research Leads Only)
- [Notable opinion from creator with source URL]; source mapping and approval are required before public authority or quotation use

## Synthesis: Unique Insights for Article

### Insights NOT Available in SEO Content
1. [Unique insight from social research]
2. [Another unique insight]

### Questions to Answer (from real users)
1. [Real question from Reddit/YouTube]
2. [Another real question]

### Proof-Backed Customer/Review POV Opportunities
- [Actual person or business POV from approved proof, only if it improves the article objective]

### Editorial Scene Opportunities
- [Unnamed workflow scenario for explanation only, not E-E-A-T proof]
- Do not anonymize an unapproved success claim into an editorial scene

### Language to Use
- Use "[real user phrase]" instead of "[generic SEO phrase]"
```

---

## STEP 3: Article Planning

**Create a section-by-section plan before writing.**

### Process

1. **Create Reader Contract**
   - Document Primary reader, Sophistication level, Trigger problem, Existing belief, Decision or task helped, Distinctive angle, Promised payoff, Funnel stage, and Exclusions
   - Use it to choose article scope, proof needs, CTA treatment, and section order

2. **Merge Research**
   Combine:
   - SERP analysis (structure that ranks, used as the default unless a Reader Contract exception is documented)
   - Competitor gaps (opportunities to beat, with recurring reader-critical gaps treated as must-fill when evidence is available)
   - Social research (unique insights)
   - AnswerSocrates PAA questions and intent clusters
   - your brand context (features, brand voice)
   - Validate the selected content type, applicable SERP features, and qualified must-fill gaps against the Reader Contract; do not continue with an undocumented deviation

3. **Create Reader-Guided Structure**
   - Match the dominant observed content type by default; document any Reader Contract exception
   - Include verified must-have sections and target every applicable SERP feature
   - Add must-fill sections for recurring, reader-critical, evidence-supported gaps
   - Order for logical reader flow

4. **Assign Section Details**
   For each section, specify:

   | Element | Purpose |
   |---------|---------|
   | **Type** | intro / body-how-to / body-comparison / body-explanation / faq / conclusion |
   | **Word Target** | Based on intent/evidence-complete scope, source depth, and gap filling |
   | **Strategic Angle** | What unique perspective we bring |
   | **Engagement Hook** | How this section captures attention |
   | **Knowledge Gaps** | Which competitor gaps this fills |
   | **Unique Data** | Social research insights to include |
   | **Internal Links** | Which your brand pages to link |
   | **AEO/GEO Target** | Capsule / PAA / FAQ / list / table / definition |
   | **Source Mapping** | External source, claim, anchor text, and target section |
   | **Proof Sidecar** | Validation sidecar path and status; proof packs and maps stay in that sidecar |
   | **CTA** | intent-sensitive CTA based on ToFu / MoFu / BoFu / thought leadership |
   | **Editorial Scene** | Optional unnamed workflow scene, or a named person/business only with approved proof |

5. **Plan Engagement Distribution**
   - Proof-backed customer/review POV: Optional; use only when an actual person or business story improves the objective and is sidecar-mapped
   - Editorial scenes: 0-2 editorial scenes when they materially improve understanding
   - Named people or businesses require approved proof; Unnamed workflow scenarios are explanatory only; invented names, dates, metrics, quotes, and outcomes are prohibited
   - CTAs: ToFu: 0-1 soft resource/action CTA; MoFu: one educational next step plus one contextual product CTA; BoFu: 2-3 contextual commercial CTAs; Thought leadership: discussion, reflection, or evidence resource
   - Featured snippet opportunities: FAQ, definitions

### Output
Save to: `research/article-plan-[topic-slug]-[YYYY-MM-DD].md`

```markdown
# Article Plan: [Topic]

**Date**: [YYYY-MM-DD]
**Total Word Target**: [count]
**Primary Keyword**: [keyword]
**Secondary Keywords**: [list]

## Reader Contract
- **Primary reader**: [role, business type, region, or maturity level]
- **Sophistication level**: [beginner / intermediate / expert / mixed, plus what the reader already understands]
- **Trigger problem**: [moment, decision, or operational pressure]
- **Existing belief**: [what they already believe, worry about, or tried]
- **Decision or task helped**: [decision, task, or understanding the article helps complete]
- **Distinctive angle**: [why this article exists beyond matching the SERP]
- **Promised payoff**: [concrete reader payoff the headline and intro must deliver]
- **Funnel stage**: [ToFu / MoFu / BoFu / thought leadership]
- **Exclusions**: [what the article will not cover, rank, quantify, or claim]

## SERP Strategy Decision
- **Observation**: [verified dominant content type, observed SERP features, recurring observed structure, and qualified must-fill gaps]
- **Default recommendation**: [match the dominant type, target each applicable feature, and include each qualified must-fill gap]
- **Exception decision**: [none, or one reasoned Reader Contract entry per deviation using `content_type: [subject] - [reason]`, `serp_feature: [subject] - [reason]`, `serp_structure: [subject] - [reason]`, `competitor_gap: [subject] - [reason]`, or `cta: [subject] - [reason]`]
- **Proof status**: [SERP observation source and confirmation that public claims still require approved proof]

## Meta Elements
- **Title Options**:
  1. [Option 1]
  2. [Option 2]
  3. [Option 3]
- **Meta Description**: [150-160 chars — must directly answer the target query, not just tease]
- **URL Slug**: /blog/[slug]

## Section Plan

## AEO/GEO Map
- **Main Answer Target**: [primary question the article answers]
- **Capsule Targets**: H1 plus at least 60% of major H2s
- **Selected PAA Questions**:
  1. [AnswerSocrates question and assigned section]
  2. [AnswerSocrates question and assigned section]
  3. [AnswerSocrates question and assigned section]
- **Source Map**:
  | Source | Claim Supported | Anchor Text | Target Section |
  |--------|-----------------|-------------|----------------|
  | [URL] | [claim] | [natural contextual phrase] | [section] |
- **Proof Sidecar**: [research/validation-[topic-slug]-[YYYY-MM-DD].md; ready / partial / blocked]
- **Schema Notes**: BlogPosting, BreadcrumbList, and FAQPage for standard blog posts with FAQs; nest Question and Answer inside FAQPage, ImageObject for the featured image or logo, and Organization as publisher reference only, not a separate full schema block. For public Markdown blog artifacts, place this as a `schema_notes` field in the top YAML frontmatter block, between the opening and closing --- delimiters. If a named author is present, include `author` in frontmatter and map it to `Person as author`. If no named author is available, omit `author`, omit `Person as author`, keep `Organization` as publisher reference only, and record the no-author decision in the blog assembly BOM and validation sidecar. Add VideoObject only if video is embedded.
- **AEO/GEO Score Target**: 90/100 or higher

### 1. Introduction
- **Type**: intro
- **Word Target**: [positive target supplied from the Reader Contract and available evidence]
- **Hook Strategy**: [question / scenario / statistic / bold statement]
- **APP Elements**: [Agree point, Promise, Preview]
- **Editorial Scene**: [Optional unnamed workflow scene; named people or businesses require approved proof]
- **Next Action**: [intent-appropriate next action when planned; a commercial CTA only when the funnel stage calls for one]
- **Unique Data**: [Insight from social research to include]

### 2. [H2 Title]
- **Type**: body-explanation
- **Word Target**: [positive intent/evidence-complete section target]
- **Strategic Angle**: [What unique perspective]
- **Knowledge Gap**: [Which competitor gap this fills]
- **Internal Links**: [your brand page to link]
- **Unique Data**: [Social insight to include]

### 3. [H2 Title]
- **Type**: body-how-to
- **Word Target**: [positive intent/evidence-complete section target]
- **Strategic Angle**: [Unique angle]
- **Knowledge Gap**: [Gap being filled]
- **Editorial Scene**: [Optional unnamed workflow scene; named people or businesses require approved proof]

[Continue for all sections...]

### N. FAQ
- **Type**: faq
- **Word Target**: [positive target based on selected questions and required evidence]
- **Questions from Research**:
  1. [Real question from Reddit]
  2. [Another real question]
  3. [Question competitors don't answer]
  4. [Featured snippet opportunity]
- **Featured Snippet**: Yes

### N+1. Conclusion
- **Type**: conclusion
- **Word Target**: [positive intent/evidence-complete section target]
- **Next Action**: [intent-appropriate action; commercial CTA only when the funnel stage calls for one]
- **Editorial Scene**: [Optional unnamed workflow scene; named people or businesses require approved proof]

## Engagement Map

| Element | Location |
|---------|----------|
| Optional proof-backed customer/review POV | Section where it improves the objective |
| 0-2 editorial scenes | Sections where they materially improve understanding |
| intent-sensitive CTA | ToFu: 0-1 soft resource/action CTA; MoFu: one educational next step plus one contextual product CTA; BoFu: 2-3 contextual commercial CTAs; Thought leadership: discussion, reflection, or evidence resource |

## Gap-to-Section Mapping

| Competitor Gap | Section Addressing It |
|----------------|----------------------|
| [Gap 1] | Section [X] |
| [Gap 2] | Section [Y] |

## Continuity Pass
- [ ] Every section must advance the headline promise from the Reader Contract.
- [ ] Each section answers a question created by the previous section.
- [ ] No section restarts the article, repeats the introduction, or creates repeated resets.
- [ ] Transitions explain a logical relationship, not just a transition word.
- [ ] The conclusion must complete the introduction, resolve open loops, and add a useful next action.
- [ ] remove or justify any section that does not increase the promised payoff.

## Social Insight Mapping

| Unique Insight | Where Used |
|----------------|------------|
| [Insight 1] | Section [X] |
| [Insight 2] | Section [Y] |
```

---

## STEP 4: Section-by-Section Writing

**Write each section individually to maintain quality.**

### Why Section-by-Section?
- Long-form AI writing degrades in quality toward the end
- Each section gets focused attention
- Each section gets its own editing pass
- Maintains consistent quality throughout

### Section Types & Specialized Approaches

#### Introduction
**Requirements:**
- **Direct answer first** (AI Search Optimization): For any "best/top/how" query, the first 1-2 sentences MUST directly answer the question before the narrative hook. AI scrapers pull from the top of the page.
- Hook (NOT generic opening - use question/scenario/stat/bold statement)
- APP Formula: Agree, Promise, Preview
- Primary keyword in first 100 words
- Trust signal
- Use the section Word Target from the article plan without padding

**Do NOT open with:**
- "[Product category] is..."
- "When it comes to..."
- "If you're looking for..."
- "In today's world..."

#### Key Takeaways Block (After Introduction, Before First H2)
**Requirements:**
- 3-5 bullet points summarizing the article's actual conclusions
- Each bullet is a standalone claim with approved proof-backed specifics or concrete workflow detail; never invent numbers, names, or outcomes
- NOT a table of contents — these are the conclusions up front
- Format as blockquote with bold "Key Takeaways" header
- Written after full article is drafted, then placed here

#### Body: How-To
**Requirements:**
- Numbered steps for sequential processes
- Each step actionable and specific
- Time estimates where helpful
- Common mistakes to avoid
- Use the section Word Target from the article plan without padding

#### Body: Comparison
**Requirements:**
- Balanced (acknowledge competitor strengths)
- Data tables for key metrics
- Specific prices/features
- "Best for" recommendations
- Use the section Word Target from the article plan without padding

#### Body: Explanation
**Requirements:**
- Progressive complexity (simple → advanced)
- Analogies for complex concepts
- Examples with specifics
- Evaluate selected video evidence. Embed a relevant, public, embeddable video only when it materially supports the section; otherwise document that no eligible video was selected and omit the embed.
- Use the section Word Target from the article plan without padding

#### FAQ
**Requirements:**
- 4-6 questions from research (real user questions)
- 40-60 word answers (featured snippet optimized)
- Direct answer first, then context
- FAQ answer quality is required: write a 40-60 word first paragraph that leads with a supported number or range, named recommendation, definition, concrete action, or explained yes/no response. Generic deflections such as `There is no`, `It depends`, `Pricing depends`, `Costs vary`, `We do not know`, `It is unclear`, and `No source ranks` block publish readiness. Put limitations after the direct answer.
- FAQ proof is required for every answer: include at least 1 authoritative non-owned public evidence link inside the visible answer. A Source Map or FAQ Proof Map can document the same evidence but cannot replace the reader-facing link.
- **FAQ Source Policy**: Every visible non-owned FAQ URL requires an exact `FAQ Proof Map` row with `FAQ`, `URL`, `Source class`, `Competitor check`, and `Support`. Use only `neutral` or `non_competing_expert` source classes. Competitor-owned FAQ sources: prohibited.
- **Compliant evidence**: Prefer regulators, standards bodies, universities, trade associations, independent research/editorial, or non-competing experts. Simpro-owned links may be additional resources but never satisfy the non-owned FAQ-proof rule.
- **Vendor-specific questions**: If a compliant source is unavailable, remove or reframe the FAQ and keep vendor evidence in the comparison section.
- Run `python data_sources/modules/faq_answer_quality_guard.py [file] --fail-on error` before scoring or optimization; `/publish-readiness` runs it as a blocking gate.
- PAA provenance is required for every FAQ question: include `PAA/FAQ Provenance` with Source, Artifact, and exact Selected questions from AnswerSocrates, SERP, Reddit, YouTube, or a user PAA/FAQ CSV.
- FAQ headings must be complete natural-language questions. Do not use AnswerSocrates keyword fragments or query modifiers such as `plumbing job sheet template pdf` as FAQ headings.
- Use the FAQ section Word Target from the article plan; preserve the 40-60-word first-paragraph rule for each answer

#### Conclusion
**Requirements:**
- NOT just a summary - add value
- Close the headline and introduction loops with only the takeaways needed for the promised payoff
- Intent-appropriate next action that matches the Reader Contract
- Include an intent-appropriate next action; add a commercial CTA only when the Reader Contract funnel stage calls for one
- Empowering, forward-looking close
- Use the section Word Target from the article plan without padding

### Writing Process Per Section

For each section in the plan:

1. **Write Draft**
   - Use section-specific requirements above
   - Include planned unique data/insights from research
   - Follow word target
   - Apply planned engagement hook

2. **Edit Pass**
   - Remove AI phrases ("In today's", "It's important to note", "When it comes to")
   - Replace vague words with proof-safe specifics: approved numbers when evidence supports them, or concrete workflow detail when it does not
   - Check paragraph length (max 4 sentences)
   - Vary sentence rhythm (mix 5-10 word + 15-25 word)
   - Add conversational devices (contractions, questions, parenthetical asides)
   - Verify active voice

3. **Verify Requirements**
   - Section-specific criteria met
   - Planned insights included
   - Section is complete without padding; document any material variance from the planned target

### Assembly

After all sections are written and edited:

1. **Combine Sections**
   - Assemble in planned order
   - Run the Continuity Pass: every section must advance the headline promise, answer a question created by the previous section, avoid repeated resets, express a logical relationship in transitions, complete the introduction in the conclusion, and remove or justify sections that do not increase the payoff
   - Verify internal link placement
   - Confirm intent-sensitive CTA placement

2. **Add Meta Elements**
   ```markdown
   ---
   artifact_type: blog
   brand: [Brand]
   title: [Article title]
   objective: [Reader/job objective]
   audience: [Audience]
   region: [Region]
   author: [Named author only when available; omit this field when no named author exists]
   schema_notes: [BlogPosting, BreadcrumbList, FAQPage, Question and Answer inside FAQPage, ImageObject, Organization publisher reference; add Person as author only when author exists; add VideoObject only when video is embedded]
   Meta Title: [50-60 chars ending with | Brand]
   Meta Description: [150-160 chars]
   Primary Keyword: [keyword]
   Secondary Keywords: [list]
   URL Slug: /blog/[slug]
   Word Count: [count]
   Internal Links: [list]
   External Links: [list]
   ---
   ```

   Meta titles must always end with the owning brand suffix in pipe format, for example `Construction Draw Schedule Explained | ClockShark`.

3. **Generate Checklists**

   **SEO Checklist:**
   - [ ] Primary keyword in H1
   - [ ] Primary keyword in first 100 words
   - [ ] Primary keyword in at least one relevant H2 where natural; semantic variations used elsewhere without a quota
   - [ ] Natural terminology coverage, semantic variations, and keyword-stuffing detection checked
   - [ ] 3-5+ internal links
   - [ ] 2-3 external authority links
   - [ ] Meta title 50-60 chars ending with `| Brand`
   - [ ] Meta description 150-160 chars
   - [ ] Word count fits the Reader Contract, search intent, and available evidence

   **AI Search Optimization Checklist:**
   - [ ] Direct answer in first 1-2 sentences (not buried behind narrative)
   - [ ] Key Takeaways block with 3-5 specific bullet points after introduction
   - [ ] Meta description directly answers the target query
   - [ ] Video eligibility evaluated; an eligible selected video is embedded when it materially supports the article, otherwise the embed is omitted
   - [ ] FAQ questions written in natural prompt language, not keyword fragments from AnswerSocrates
   - [ ] One idea per section (each H2/H3 focuses on single concept)
   - [ ] Author policy recorded: named author mapped to Person schema when available; otherwise `author` and `Person as author` omitted
   - [ ] AnswerSocrates PAA artifact exists at `research/paa-questions-[topic-slug]-[YYYY-MM-DD].md`
   - [ ] Capsule Method applied to H1 and 60%+ major H2s
   - [ ] AEO/GEO Map complete with selected PAA, source mapping, and E-E-A-T proof
   - [ ] Metric Proof Pack checked using the post-writing gate stack
   - [ ] FAQ proof checked using the post-writing gate stack
   - [ ] PAA provenance checked using the post-writing gate stack
   - [ ] Schema notes included for BlogPosting, BreadcrumbList, FAQPage, Question and Answer inside FAQPage, ImageObject for the featured image or logo, and Organization as publisher reference only, not a separate full schema block. Person as author is included only when a named author exists. VideoObject is included only when relevant.
   - [ ] Public article body does not mention "repo context," context file paths, Source Maps, PAA artifacts, change summaries, or internal proof-path notes

   **Engagement Checklist:**
   - [ ] Hook (not generic opening)
   - [ ] APP Formula in intro
   - [ ] Optional proof-backed customer/review POV is used only when it fits the objective and is sidecar-mapped
   - [ ] 0-2 editorial scenes when they materially improve understanding
   - [ ] Named people or businesses require approved proof; Unnamed workflow scenarios are explanatory only; invented names, dates, metrics, quotes, and outcomes are prohibited
   - [ ] intent-sensitive CTA count and type match ToFu / MoFu / BoFu / thought leadership
   - [ ] No paragraphs > 4 sentences
   - [ ] Varied sentence rhythm

   **Research Integration Checklist:**
   - [ ] Evaluates competitor gaps and includes only those that improve reader payoff, evidence completeness, or task usefulness
   - [ ] Includes only source-bound social insights that materially improve reader payoff, evidence, or task usefulness
   - [ ] Uses real user language
   - [ ] Answers questions from Reddit/YouTube
   - [ ] Replaces relevant outdated information with current, source-verified evidence

### Output
Save to: `drafts/[topic-slug]-[YYYY-MM-DD].md`

---

## Post-Writing Quality Loop

After saving the draft:

### 1. Scrub Punctuation Artifacts
```
/scrub drafts/[filename].md
```
Removes invisible Unicode marks, em dashes, and whitespace artifacts.

### 2. Publish Readiness

Proof infrastructure belongs only in the validation sidecar at `research/validation-[topic-slug]-[YYYY-MM-DD].md`; article plans and drafts retain only its sidecar path and status. The article draft must not include an `Editorial Validation Appendix`, `PAA/FAQ Provenance`, `Metric Proof Pack`, `Source Map`, `Customer Proof Pack`, `FAQ Proof Map`, or structured data plan as public copy. Use VideoObject only when a video is embedded.

Preferred publish readiness command:
```bash
/publish-readiness [file] --proof-sidecar research/validation-[topic-slug]-[YYYY-MM-DD].md --context-request research/context-request-[topic-slug].json --context-pack research/context-pack-[topic-slug].json --context-receipt research/context-receipt-[topic-slug].json --assembly-bom research/blog-assembly-bom-[topic-slug]-[YYYY-MM-DD].json
/publish-readiness drafts/[filename].md --proof-sidecar research/validation-[topic-slug]-[YYYY-MM-DD].md --context-request research/context-request-[topic-slug].json --context-pack research/context-pack-[topic-slug].json --context-receipt research/context-receipt-[topic-slug].json --assembly-bom research/blog-assembly-bom-[topic-slug]-[YYYY-MM-DD].json
```

The command runs AI copy linting, URL validation, public artifact checks, Metric Proof Pack, numeric claim, FAQ proof, PAA provenance, source support, customer proof diversity, review story identity, content score, and AEO/GEO gates internally.

**Quality Gates:**
- General content quality score must be **85/100** or higher.
- AEO/GEO score must be **90/100** or higher.
- A draft only passes if `/publish-readiness` reports no blocking gate failures.

| Dimension | Weight |
|-----------|--------|
| Humanity/Voice | 30% |
| Specificity | 25% |
| Structure Balance | 20% |
| SEO Compliance | 15% |
| Readability | 10% |

### 11. Auto-Revise if Needed
If either gate fails:
1. Review `priority_fixes` from scorer
2. Review AEO/GEO failed checks from `aeo_geo`
3. Classify each AEO/GEO failure as a copy gap, proof/sidecar gap, or scorer or parser false negative. Fix false negatives in the scorer with regression coverage instead of distorting accurate copy.
4. Review URL validation blockers from `data_sources/modules/url_validator.py --fail-on unresolved`
5. Review Metric Proof Pack blockers from `data_sources/modules/metric_proof_pack_guard.py --fail-on error`
6. Review numeric claim source blockers from `data_sources/modules/numeric_claim_source_guard.py --fail-on error`
7. Review FAQ proof blockers from `data_sources/modules/faq_proof_guard.py --fail-on error`
8. Review PAA provenance blockers from `data_sources/modules/paa_provenance_guard.py --fail-on error`
9. Review source support blockers from `data_sources/modules/source_support_guard.py --fail-on error`
10. Review customer proof diversity blockers from `data_sources/modules/customer_proof_diversity_guard.py --fail-on error`
11. Review review story identity blockers from `data_sources/modules/review_story_identity_guard.py --fail-on error`
12. Apply top 3-5 fixes
13. Review every `because` construction during the revision loop. Fix grammar in the sentence itself, then rerun `/scrub`, the AI copy linter, URL validation, Metric Proof Pack guard, numeric claim source guard, FAQ proof guard, PAA provenance guard, source support guard, customer proof diversity guard, and review story identity guard
14. Re-score
15. Repeat once more if needed
16. If AI copy lint errors remain after 1 revision, URL validation fails, Metric Proof Pack guard fails, numeric claim source guard fails, FAQ proof guard fails, PAA provenance guard fails, source support guard fails, customer proof diversity guard fails, review story identity guard fails, or content quality remains below 85/100 or AEO/GEO remains below 90/100 after 2 iterations -> move to `review-required/`

### 12. Run Optimization Agents
After passing quality threshold:
- `content-analyzer` agent
- `seo-optimizer` agent
- `meta-creator` agent
- `internal-linker` agent
- `keyword-mapper` agent

Treat those optimizer outputs as content mutations when they change the article. Update the BOM workflow stages with `post_optimization_scrub`, `post_optimization_context_binding`, and `final_publish_readiness` before final handoff.

---

## Complete Output Structure

The complete connector-backed output inventory for each Simpro blog assembly run includes:

- Article artifact: `drafts/[topic-slug]-[YYYY-MM-DD].md` or `rewrites/[topic-slug]-rewrite-[YYYY-MM-DD].md`
- Validation sidecar: `research/validation-[topic-slug]-[YYYY-MM-DD].md`
- Context request: `research/context-request-[topic-slug].json`
- Context pack: `research/context-pack-[topic-slug].json`
- Context receipt: `research/context-receipt-[topic-slug].json`
- Blog assembly BOM: `research/blog-assembly-bom-[topic-slug]-[YYYY-MM-DD].json`
- Customer proof selector evidence: `research/customer-proof-selector-evidence-[topic-slug].json`
- Fred authority selection: `research/fred-authority-selection-[topic-slug].md`

The validation sidecar must include current `Context Binding` and `Context Claim Use Map` sections generated from connector artifacts. The BOM JSON records the same article, sidecar, context request, context pack, context receipt, author policy, schema policy, and workflow stage inventory for the assembly run.

```
research/
├── serp-analysis-[topic]-[date].md         # SERP research
├── social-research-[topic]-[date].md       # Reddit/YouTube insights
├── paa-questions-[topic]-[date].md         # AnswerSocrates PAA research
└── article-plan-[topic]-[date].md          # Section-by-section plan

drafts/
├── [topic]-[date].md                       # Final article
├── content-analysis-[topic]-[date].md      # Content analyzer output
├── seo-report-[topic]-[date].md            # SEO optimizer output
├── meta-options-[topic]-[date].md          # Meta creator output
├── link-suggestions-[topic]-[date].md      # Internal linker output
└── keyword-analysis-[topic]-[date].md      # Keyword mapper output
```

---

## Required Context Files

Before writing, review these context files:
- @context/brand-voice.md - fallback mirror for brand tone and messaging when the vault is unavailable
- @context/style-guide.md - fallback mirror for formatting rules when the vault is unavailable
- @context/seo-guidelines.md - SEO requirements
- @context/aeo-geo-blog-strategy.md - AEO/GEO requirements for blog writing
- @context/target-keywords.md - keyword targets, clusters, and metric boundaries
- @context/internal-links-map.md - Linking targets
- @context/features.md - fallback product-information mirror only when the vault is unavailable; never public-claim approval authority
- @context/writing-examples.md - Style reference

---

## Quality Standards

### Research Standards
- Top 5 competitor articles analyzed
- 5 Reddit threads visited (actual pages, not snippets)
- 5 YouTube videos analyzed
- Competitor gaps documented
- Social insights synthesized

### Content Standards
- Intent/evidence-complete word target from the Reader Contract, search intent, and available evidence
- Proper H1/H2/H3 hierarchy
- 3-5 internal links
- 2-3 external authority links
- Compelling hook (not generic)
- Optional proof-backed customer/review POV when it improves the objective
- intent-sensitive CTA count and type based on funnel stage
- FAQ with real user questions
- General content quality score 85/100+
- AEO/GEO score 90/100+

### Differentiation Standards
- Evaluates competitor gaps and includes only those that improve reader payoff, evidence completeness, or task usefulness
- Includes 5+ unique social insights
- Uses real user language (not SEO-speak)
- Updates outdated competitor info
- Provides depth where competitors are thin

- **Review proof routing**: For review-derived public copy, run the selector and `review_story_identity_guard.py` before scoring. Keep detailed Review Story Selection, Capterra theme, exact-quote, rating, and metric boundaries in `context/aeo-geo-blog-strategy.md`.
