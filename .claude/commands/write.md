# Write Command

Use this command to create comprehensive, SEO-optimized long-form blog content.

For every Simpro blog, read `wiki/messaging/Voice and Tone.md` and `wiki/messaging/Tone Voice and Localization Rules.md` from the vault. Named-author Simpro blogs and thought leadership may use first-person judgment, contractions, operational scenes, decisive opinions, and short punchlines. Author opinion must remain distinguishable from empirical fact. Metrics, market comparisons, product status, roadmap statements, and commercial claims remain proof gated. Em dashes are prohibited. Product pages and landing pages retain their existing restrained channel treatment.

## Usage
`/write [topic or research brief]`

## What This Command Does
1. Creates complete, well-structured articles sized to the reader intent, evidence, and topic scope
2. Optimizes content for target keywords and SEO best practices
3. Maintains your brand voice and messaging throughout
4. Integrates internal and external links strategically
5. Includes all meta elements for publishing

## Process

### Obsidian Vault Source Rule

For every blog, SEO, AEO, competitor, proof, product, audience, partner, or workflow decision, use the Obsidian vault as the active context source: `C:\Users\patrick.grueschow\Desktop\Obsidian\Simpro Brand Context`.

Required read order: `AGENTS.md -> wiki/cache/hot.md -> wiki/Brand Graph Index.md -> smallest relevant wiki/source/raw pages`.

Do not use Google Workspace or old marketing-portal URLs as the active read path. Use them only as historical provenance when the vault already exposes a local source route.

The repo-local context files are downstream mirrors/fallbacks only and cannot override the vault when the vault is available. If a repo-local fallback is used because the vault is unavailable, document that in `Vault Context Read Path` in the validation sidecar.

Required validation sidecar sections: `Vault Context Read Path` for every workflow; `Vault Brand Language Alignment` when product, feature, add-on, solution, industry, or related Simpro product URL language appears; `Competitive Shortlist Decision` for competitor-aware posts; `Named Feature/Add-On Link Check` when named Simpro features/add-ons appear. Missing required sections block `/publish-readiness`, `/optimize`, and dev-ready handoff until documented.

### Vault-Backed Competitor and Feature Guardrails

- `Competitive Shortlist Decision`: competitor-aware posts must document selected competitors, rejected competitors, `wiki/competitors/Competitive Context.md`, `wiki/sources/simpro-battlecards-direct-competitors-1bzgf9r8.md`, and linked source/raw files in the validation sidecar, plus why the shortlist fits the article objective.
- Public competitor pages may shape SERP/article format, but cannot decide named competitors for Simpro public copy.
- `Hindsight Boundary`: Hindsight/deal intelligence can inform internal strategy, but cannot be published as proof, rankings, metrics, or claims unless separately approved and source-verified. Route Hindsight context through `wiki/sources/hindsight-copy-of-simpro-battlecards-1elcobgn.md` and keep raw deal counts out of public copy.
- `Named Feature/Add-On Link Check`: first meaningful mentions of Simpro features/add-ons must be checked against vault product routes before link decisions. Start with `wiki/concepts/payments-and-add-ons.md` and `wiki/features/Feature Library`; document each vault route checked, link decision, and reason in the validation sidecar.
- `Vault Brand Language Alignment`: product, feature, add-on, solution, and industry language must be drafted from the vault first. Read `wiki/messaging/Simpro Core Messaging Repository.md`, `wiki/messaging/Message House.md`, `wiki/messaging/Core Value Pillars.md`, `wiki/product/Product Positioning.md`, and `wiki/features/Feature Library.md`; when a named feature/add-on appears, add the relevant `wiki/features/source-docs/` route or specific source/raw route; when solution/industry language is used, also read `wiki/verticals/Vertical Profile Library.md` and the relevant vertical/source page. Document routes checked, language applied, fallback context use, source-verification boundary, and `Status: aligned` in `Vault Brand Language Alignment`. The `vault_brand_language_guard.py` publish gate runs inside `/publish-readiness`; keep this block in the validation sidecar, not public copy. The repo-local `context/brand-voice.md` and `context/style-guide.md` are fallback mirrors only when the vault is unavailable.

### Pre-Writing Review
- **Research Brief**: Review research brief from `/research` command if available
- **Brand Voice**: Use the vault messaging routes first; @context/brand-voice.md is a fallback mirror only when the vault is unavailable
- **Writing Examples**: Study @context/writing-examples.md for style consistency
- **Style Guide**: Use vault terminology first; @context/style-guide.md is a fallback mirror only when the vault is unavailable
- **SEO Guidelines**: Apply requirements from @context/seo-guidelines.md
- **AEO/GEO Strategy**: Apply @context/aeo-geo-blog-strategy.md for Generative Engine Optimization
- **Target Keywords**: Integrate keywords from @context/target-keywords.md naturally
- **Lightning Overlay**: If the topic or research brief mentions Simpro Lightning, AroFlo Lightning, BigChange Lightning, Simpro Group Lightning, JustAsk, Cooper, FieldReady, JobReady, JobScribe, JobBrief, Price Lock, AI tax, TrueTime, DirectLine, Coming Specialists, or any named roadmap specialist, also load @context/lightning-positioning.md and treat it as a scoped overlay.

### AEO/GEO Variable Resolution
Resolve `topic`, `audience`, `main_question`, `related_questions`, `tone`, `expertise`, and `length` from the research brief, Vault Context Read Path, repo context fallback, target keyword, and existing PAA artifact before writing. `/write` may skip live AnswerSocrates only when the supplied brief already includes PAA questions. If PAA questions are missing, ask for a PAA/FAQ CSV or run `/article` for full AnswerSocrates collection.

### E-E-A-T Proof Map Inputs
Before drafting, resolve an E-E-A-T Proof Map:
- **Experience**: Customer case studies, customer outcomes, review-site experience evidence / VoC themes, implementation/support themes, user pain, and field workflow examples.
- **Expertise**: Product/feature knowledge, source-backed workflow explanations, expert quotes, author/reviewer metadata, and Simpro workflow specificity.
- **Authority/Trust**: Public research, case-study URLs, review-site/source links, limitations/caveats, and no invented proof.
- **Fallback context sources**: After Vault Context Read Path, pull case-study URLs from @context/internal-links-map.md, approved metrics/proof candidates from @context/features.md, and review-site experience evidence / VoC or competitor experience themes from @context/competitor-analysis.md or future review-context files only as repo-local mirror/fallback inputs.
- **Public-copy rule**: Context-backed metrics are valid only when the article body uses public-facing source links, such as the public case-study URL, review-site URL, or public research source.
- **403 replacement rule**: If a DOL, Capterra, G2, Trustpilot, Google Play, or other public research/source URL returns 401, 403, or `manual_review`, do not remove the citation unless an equivalent resolved public source link replaces it in public copy or the supported claim is removed. Source Map notes must document both the rejected 403 URL and the replacement URL. Full policy and the `public_research_link_guard.py` gate live in `context/aeo-geo-blog-strategy.md`.

### Simpro Web Copy Rules
- Use numerals for cardinal numbers, including 1-9.
- Do not block source-visible metric wording when a public proof source spells out the number; preserve the supported claim wording and rely on Metric Proof Pack, numeric claim source guard, and source support guard for proof.
- Because comma decisions are grammar/context dependent. No comma when the because clause is essential to the sentence meaning. Use a comma when the because clause is nonessential, contrastive, or needed to prevent misreading. Review negative constructions carefully because comma placement can change meaning.
- Only 1 link per paragraph. Move the second link to a separate paragraph or remove it.
- Do not write source/proof meta-commentary such as "that case study is useful for this topic" or "this source is relevant for the article." Translate proof into audience-facing takeaways, outcomes, or workflow lessons.

### Down-Funnel Internal Link Rule

Every draft must include at least 1 contextual down-funnel internal link to `/industries`, `/industries/...`, `/solutions/...`, or `/features/...` from @context/internal-links-map.md. Prefer the specific industry page when industry intent is clear, the `https://www.simprogroup.com/industries` hub for broad trades or general industry topics, the relevant solution page for category/workflow topics, and the relevant feature page for feature/workflow topics. Anchor text must match the destination keyword or an approved anchor example from @context/internal-links-map.md.

Feature and solution links must use function-bearing anchor text that explains the workflow, category, or outcome behind the destination. A feature or solution name alone is not enough. Use anchors like "field service payments," "accounts receivable follow-up with Fast Cash," or "field service management software" instead of "Simpro Payments," "Fast Cash," or "Simpro Premium."

### Reader Contract

Before drafting the outline, write a `Reader Contract` block. This is an editorial contract, not public proof infrastructure:

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

## SERP Strategy Decision

After the Reader Contract, record the verified SERP observation source, dominant observed content type, every observed feature, recurring extracted structure, and qualified must-fill gaps. Match the dominant observed content type and target every applicable feature by default. Any deviation requires a documented Reader Contract exception. If verified SERP context is unavailable, mark the decision unresolved and do not invent observations or silently waive the handoff.

### Content Structure

#### 1. Headline (H1)
- Include primary keyword naturally
- Create compelling, click-worthy title
- Keep under 60 characters for SERP display
- Promise clear value to reader

#### 2. Introduction (use the planned section target)

**CRITICAL: Direct Answer First (AI Search Optimization)**

For any "best/top/how" query, the first 1-2 sentences MUST directly answer the question. AI scrapers (ChatGPT, Perplexity, Gemini) pull from the top of the page. Don't bury the answer behind narrative.

**Example — "best project management tools":**
> The best project management tools in 2026 are Asana, Monday, and ClickUp — each built for different team sizes and workflows. Here's how they compare.

After the direct answer, use a hook to keep human readers engaged.

**Choose ONE hook type for each article:**

| Hook Type | Example | Best For |
|-----------|---------|----------|
| **Provocative Question** | "What does the 'free' plan still make your team handle manually?" | Challenging assumptions |
| **Proof-Safe Operational Scene** | "A dispatcher opens the schedule and sees three urgent jobs competing for the same technician." | Making the reader's work pressure concrete |
| **Surprising Statistic** | Use a sourced statistic only when approved proof supports the number and the section needs it. | Data-driven topics |
| **Bold Statement** | "Your current tool is lying to you about your numbers." | Controversial takes |
| **Counterintuitive Claim** | "The cheapest option might be the most expensive decision you make this year." | Comparison content |

**After the hook, follow the APP Formula:**
- **Agree**: Acknowledge something the reader already believes/feels
- **Promise**: Tell them exactly what they'll learn or gain
- **Preview**: Brief overview of what's coming (can include mini table of contents for long posts)

- **Keyword**: Include primary keyword in first 100 words
- **Credibility**: Establish why you/this article is authoritative

#### 3. Key Takeaways Block (After Introduction)

**REQUIRED: TL;DR block immediately after the introduction, before the first H2 body section.**

This gets pulled into AI-generated summaries and helps both AI and human readers quickly assess the article's value.

```markdown
> **Key Takeaways**
> - [Core finding or recommendation #1]
> - [Core finding or recommendation #2]
> - [Core finding or recommendation #3]
> - [Core finding or recommendation #4 if needed]
> - [Core finding or recommendation #5 if needed]
```

**Rules:**
- 3-5 bullet points
- Each bullet is a standalone claim with approved proof-backed specifics or concrete workflow detail; never invent numbers, names, or outcomes
- NOT a table of contents — these are the article's actual conclusions
- Written after the full article is drafted (so the takeaways are accurate)

#### 3A. AEO/GEO Structure Requirements

Apply these requirements from @context/aeo-geo-blog-strategy.md:
- **Capsule Method**: Add a 50-60 word direct-answer capsule below the H1 and at least 60% of major H2s.
- **Early usable artifact**: Place a filled data table, download link, checklist deliverable, or calculator reference within the first 300 words of body copy; Key Takeaways bullets and plain lists do not count. Full policy and the not-applicable exemption live in `context/aeo-geo-blog-strategy.md`.
- **Concrete answers**: If the target query implies a number, range, or template, supply a concrete version with disclaimers as needed. Placeholder-only table cells such as `TBD` or `Enter lender-approved value` block publish. Full policy lives in `context/aeo-geo-blog-strategy.md`.
- **PAA selection**: Use 3-5 complete natural-language PAA or FAQ questions from AnswerSocrates, SERP research, Reddit, YouTube, or a user-provided CSV. Do not use AnswerSocrates keyword fragments or query modifiers as FAQ headings or selected questions.
- **Source mapping**: Integrate at least three credible external sources inside natural sentences; map each source to the claim it supports.
- **FAQ answer quality**: Write a 40-60 word first paragraph that leads with a supported number or range, named recommendation, definition, concrete action, or explained yes/no response. Generic deflections such as `There is no`, `It depends`, `Pricing depends`, `Costs vary`, `We do not know`, `It is unclear`, and `No source ranks` block publish readiness. Put limitations after the direct answer.
- **FAQ proof**: Every FAQ answer must include at least 1 authoritative non-owned public evidence link inside the visible answer. A Source Map or FAQ Proof Map can document the same evidence but cannot replace the reader-facing link.
- **FAQ Source Policy**: Every visible non-owned FAQ URL needs an exact `FAQ Proof Map` row with `FAQ`, `URL`, `Source class`, `Competitor check`, and `Support`. Use only `neutral` or `non_competing_expert` sources. Competitor-owned FAQ sources: prohibited.
- **Permitted FAQ evidence**: regulators, standards bodies, universities, trade associations, independent research/editorial, and non-competing experts. Simpro-owned links can be extra reader resources but cannot satisfy FAQ proof.
- **Vendor-specific FAQs**: remove or reframe an FAQ without compliant evidence; retain vendor evidence in comparison or vendor-specific body sections.
- **FAQ quality gate**: Run `python data_sources/modules/faq_answer_quality_guard.py [file] --fail-on error` before scoring or optimization; `/publish-readiness` runs it automatically.
- **E-E-A-T Proof Map**: Include named author, last-updated date, reviewer if available, Experience proof, Expertise proof, Authority/Trust proof, named customer proof or expert quote, and honest limitations where relevant.
- **Context boundary**: Use `context/` files as the internal source of truth for voice, positioning, keywords, product framing, internal links, approved claims, proof candidates, and approved metrics only when the Obsidian vault is unavailable; otherwise treat them as repo-local mirrors/fallbacks. Public copy may use public sources and context-backed proof, but must not mention "repo context," context file paths, Source Maps, PAA artifacts, change summaries, or internal proof-path notes.
- **Customer proof routing**: When citing customer proof, pair the case-study URL/theme from @context/internal-links-map.md with the metric/proof point from @context/features.md. Use exact quotes only when verified from the case-study page, Quote Matrix, Customer Stories, or References; if no mapped metric exists, cite only the broad theme.
- **Customer proof selection governance**: Before selecting or drafting proof, resolve `topic`, `title`, and `objective`, automatically run `python data_sources/modules/customer_proof_selector.py "[topic]" --title "[title]" --objective "[objective]" --slate --roles metric,quote,theme,experience_story --require-eeat-story --limit 10`, and write the generated selector-first `Customer Proof Slate` to the validation sidecar. If inputs are missing, resolve them from the brief/context or stop before drafting customer proof. If the selector fails, write the blocker into the sidecar and do not invent proof. experience_story consideration is required and E-E-A-T story usage is optional. If no story fits, use `Selected: [none]` with section-specific rejection reasons. Full policy lives in `context/aeo-geo-blog-strategy.md`.
- **Fred Voccola authority evaluation**: Resolve `topic`, `title`, and `objective`, then automatically run `python data_sources/modules/fred_authority_selector.py "[topic]" --title "[title]" --objective "[objective]" --slate --limit 5` and write the complete `Fred Voccola Authority Selection` block from `context/aeo-geo-blog-strategy.md` to the validation sidecar. Evaluation is mandatory and public use is optional. The selector defaults to `Selected: none`; select a source explicitly only after reviewing it and confirming direct topical support. If the selector, vault, manifest, or inventories fail, record `Evaluation status: blocked` and the blocker; do not invent Fred evidence or continue to Fred public use.
- **Recent-use proof diversity**: Treat any `recent_uses_90d` value above 0 as a proof-diversity warning, not only sources marked `overused`. Before claiming a proof source is underused, inspect the usage ledger and run a live repo scan across `drafts/`, `rewrites/`, `research/`, and `published/` for the proof ID, public URL, and customer name. If the live repo scan finds public-copy usage missing from the ledger, backfill `context/customer-proof-usage-ledger.json`, rerun proof health and selector checks, and document the backfill in the validation sidecar. Prefer an approved zero-recent-use source when one fits the same role, or document why no stronger underused approved proof fits. If a recently used or overused proof source is still selected, document why no stronger underused approved proof fits.
- **Selected customer proof mining**: When selected customer proof appears in public copy, add `Selected Customer Proof Mining` to the validation sidecar. Selector chooses candidates; proof mining reads the selected public URL before the writer decides quote, metric, POV/story, theme, or omit use. Full policy lives in `context/aeo-geo-blog-strategy.md`.
- **Proof-index health**: Run `python data_sources/modules/customer_proof_index_health.py --index context/customer-proof-index.json --ledger context/customer-proof-usage-ledger.json` before adding proof candidates, and review both recently used and overused proof rows.
- **Proof-index intake**: Add new proof candidates through `context/customer-proof-intake-template.csv` and validate with `python data_sources/modules/customer_proof_index_intake.py validate [input.csv] --index context/customer-proof-index.json` before relying on them in selector slates.
- **Review proof routing**: For review-derived E-E-A-T stories, automatically run `customer_proof_selector.py` with `--slate --roles experience_story --require-eeat-story`, then run the review story identity gate from the required stack below. Use `context/aeo-geo-blog-strategy.md` for Review Story Selection, Review Site Theme Selection, Capterra theme use, exact-quote, rating, and metric boundaries.
- **Customer Proof Pack**: Use the brief's Customer Proof Pack before placing direct quotes, named customer proof, approved metrics, or review-derived Experience patterns. If the pack is partial or blocked, omit unsupported claims.
- **Schema notes**: For standard blog posts with FAQs, include BlogPosting, BreadcrumbList, and FAQPage. Nest Person as author, Question and Answer inside FAQPage, ImageObject for the featured image or logo, and Organization as publisher reference only, not a separate full schema block. For public Markdown blog artifacts, place this as a `schema_notes` field in the top YAML frontmatter block, between the opening and closing --- delimiters. Keep the Author frontmatter field mapped to Person. Use VideoObject only when a video is embedded.

#### 4. Main Body (use caller-supplied, intent/evidence-complete section targets)
- **Logical Flow**: Organize sections in clear, progressive order
- **H2 Sections**: Use only the main sections needed to complete the Reader Contract and verified applicable coverage
- **H3 Subsections**: Break complex sections into digestible pieces
- **Keyword Integration**: Use natural terminology coverage, critical keyword placement, semantic variations, and keyword-stuffing detection
- **Depth**: Provide thorough, actionable information at each point
- **Data**: Reference statistics and studies to support claims
- **Visuals**: Note where images, screenshots, or graphics enhance understanding
- **YouTube Embed**: Evaluate selected video evidence. Embed a relevant, public, embeddable video only when it materially supports the section; otherwise document that no eligible video was selected and omit the embed.
- **Lists**: Use bulleted or numbered lists for scannability
- **Formatting**: Bold key concepts, use short paragraphs (2-4 sentences MAX)

**OPTIONAL: Proof-Backed Customer/Review POV**

Use a proof-backed customer/review POV only when it improves the article objective. If no strong proof-backed story fits, omit the story.

Allowed:
- Actual person or business POV from an approved customer story, case study, Quote Matrix route, reference, or review-site row with sidecar proof.
- Unnamed workflow scenarios for explanation only; do not treat them as E-E-A-T.

Not allowed:
- Fictional named personas or invented company stories.
- Invented dates, metrics, quotes, outcomes, or testimonial wording.

**REQUIRED: Intent-Sensitive CTA Plan**

Give the reader a useful next action that fits the Reader Contract and funnel stage:

| Funnel stage | intent-sensitive CTA default |
|--------------|------------------------------|
| ToFu | ToFu: 0-1 soft resource/action CTA |
| MoFu | MoFu: one educational next step plus one contextual product CTA |
| BoFu | BoFu: 2-3 contextual commercial CTAs |
| Thought leadership | Thought leadership: discussion, reflection, or evidence resource |

**CTA Rules:**
- Make each CTA contextual to the surrounding section and earned by the article's proof.
- Use a commercial CTA only when the reader has enough decision context.
- Never use generic "Click here" text.

#### 5. Conclusion (use the planned section target)
- **Recap**: Close the Reader Contract promise without adding new claims
- **Action**: Provide a useful next action matched to funnel stage and reader intent
- **Next Action**: Use an intent-appropriate next action; include a commercial CTA only when the Reader Contract funnel stage calls for one
- **Encouragement**: End on empowering, forward-looking note

### SEO Optimization

#### Keyword Placement
- H1 headline
- First paragraph (within first 100 words)
- At least one relevant H2 where the exact phrase is natural; use semantic variations elsewhere without a quota
- Naturally throughout the body using reader language, related terms, and stuffing checks
- Meta title and description
- URL slug

#### Internal Linking (3-5+ links)
- Reference @context/internal-links-map.md for key pages
- Link to relevant pillar content from your site
- Link to related blog articles
- Link to product/service pages where natural
- Use descriptive anchor text with keywords

#### External Linking (2-3 links)
- Link to authoritative sources for statistics
- Reference industry research or studies
- Link to tools or resources mentioned
- Build credibility with quality sources

#### Readability
- Keep sentences under 25 words average
- Use transition words between sections
- Vary sentence length for rhythm
- Write at 8th-10th grade reading level
- Use active voice predominantly
- Add subheadings when the topic or reader question changes

### Target Audience Focus
- **Audience Perspective**: Write for the target audience from the vault route; @context/brand-voice.md is fallback mirror context only
- **Practical Application**: Show how information applies to their specific challenges
- **Product Integration**: Naturally mention how your features solve problems (reference @context/features.md)
- **Industry Context**: Reference relevant trends and best practices
- **Technical Accuracy**: Ensure terminology and processes are correct for your industry

### Brand Voice Consistency
- Maintain Simpro tone from the vault first; reference @context/brand-voice.md only as fallback mirror context
- Follow your established voice pillars
- Use messaging framework from your context files
- Apply terminology preferences consistently
- Match tone to content type (how-to, strategy, news, etc.)
- For Lightning-specific content, apply @context/lightning-positioning.md: use required brand prefixes, keep JustAsk as the interface, Cooper as the brain, exact agent names, field service trades first-reference wording, and verified Lightning proof claims.

## Output
Provides a complete, publish-ready article including:

### 1. Article Content
Full markdown-formatted article with:
- H1 headline
- Introduction
- Body sections with H2/H3 structure
- Conclusion with an intent-appropriate next action
- Proper formatting and styling

### 2. Meta Elements
```
---
Meta Title: [50-60 character optimized title ending with | Brand]
Meta Description: [150-160 character compelling description]
Primary Keyword: [main target keyword]
Secondary Keywords: [keyword1, keyword2, keyword3]
URL Slug: /blog/[optimized-slug]
Internal Links: [list of pages linked from your site]
External Links: [list of external sources]
Word Count: [actual word count]
---
```

### 3. SEO Checklist
- [ ] Primary keyword in H1
- [ ] Primary keyword in first 100 words
- [ ] Primary keyword in at least one relevant H2 where natural; semantic variations used elsewhere without a quota
- [ ] Natural terminology coverage, semantic variations, and keyword-stuffing detection checked
- [ ] 3-5+ internal links included
- [ ] 2-3 external authority links
- [ ] Meta title 50-60 characters
- [ ] Meta description 150-160 characters
- [ ] Word count fits the Reader Contract, search intent, and available evidence
- [ ] Proper H2/H3 hierarchy
- [ ] Readability optimized

### 4. AI Search Optimization Checklist
- [ ] **AEO/GEO score**: Draft is expected to score 90/100 or higher
- [ ] **Direct answer**: First 1-2 sentences directly answer the target query
- [ ] **Key Takeaways**: TL;DR block with 3-5 specific bullet points after introduction
- [ ] **Meta description**: Directly answers the query (not just a teaser)
- [ ] **YouTube embed**: Video eligibility evaluated; an eligible selected video is embedded when it materially supports the article, otherwise the embed is omitted
- [ ] **FAQ prompts**: Questions written in natural language people would type into ChatGPT, not keyword fragments from AnswerSocrates
- [ ] **One idea per section**: Each H2/H3 focuses on a single clear concept
- [ ] **Author attribution**: Named author in frontmatter
- [ ] **Capsule Method**: H1 and 60%+ major H2s include 50-60 word direct-answer capsules
- [ ] **Early usable artifact**: A filled data table, download link, checklist deliverable, or calculator reference starts within the first 300 words of body copy, or the sidecar documents a not-applicable reason
- [ ] **Concrete answers**: Number/range/template queries get a concrete answer; no placeholder table scaffolds
- [ ] **PAA**: 3-5 selected PAA/FAQ questions are answered in the draft
- [ ] **source mapping**: At least three source-backed claims use natural contextual links
- [ ] **Customer Proof Pack**: Selector automatically run, selected proof mined with `Selected Customer Proof Mining`, recent-use or overuse reason added when needed, and approved quotes/metrics mapped before use. Full proof boundaries live in `context/aeo-geo-blog-strategy.md`.
- [ ] **Schema**: BlogPosting, BreadcrumbList, FAQPage, Person as author, Question and Answer inside FAQPage, ImageObject for the featured image or logo, and Organization as publisher reference only, not a separate full schema block. VideoObject is included only when relevant.

### 5. Engagement Checklist
- [ ] **Hook**: Opens with question, scenario, statistic, or bold statement (NOT generic definition)
- [ ] **APP Formula**: Introduction includes Agree, Promise, Preview elements
- [ ] **Editorial scenes**: 0-2 editorial scenes when they materially improve understanding
- [ ] **Proof-safe story boundary**: Named people or businesses require approved proof; Unnamed workflow scenarios are explanatory only; invented names, dates, metrics, quotes, and outcomes are prohibited
- [ ] **Intent-sensitive CTA**: CTA count and type match the Reader Contract funnel stage
- [ ] **Paragraph length**: No paragraphs exceed 4 sentences
- [ ] **Sentence rhythm**: Mix of short (5-10 words) and longer sentences (15-25 words)

### 6. Continuity Pass
- [ ] Every section must advance the headline promise from the Reader Contract.
- [ ] Each section answers a question created by the previous section.
- [ ] No section restarts the article, repeats the introduction, or creates repeated resets.
- [ ] Transitions explain a logical relationship, not just a transition word.
- [ ] The conclusion must complete the introduction, resolve open loops, and add a useful next action.
- [ ] remove or justify any section that does not increase the promised payoff.

## File Management
After completing the article, automatically save to:
- **File Location**: `drafts/[topic-slug]-[YYYY-MM-DD].md`
- **File Format**: Markdown with frontmatter and formatted content
- **Naming Convention**: Use lowercase, hyphenated topic slug and current date

Example: `drafts/content-marketing-strategies-2025-10-15.md`

## Validation Sidecar

Proof infrastructure belongs only in the validation sidecar at `research/validation-[topic-slug]-[YYYY-MM-DD].md`; the draft records only its sidecar path and status. Do not put an `Editorial Validation Appendix`, `PAA/FAQ Provenance`, `Metric Proof Pack`, `Source Map`, `Customer Proof Pack`, `FAQ Proof Map`, or structured data plan in the publishable blog draft. Use VideoObject only when a video is embedded.

Preferred publish readiness command:
```bash
/publish-readiness [file] --proof-sidecar research/validation-[topic-slug]-[YYYY-MM-DD].md
```

Meta titles must always end with the owning brand suffix in pipe format, for example `Construction Draw Schedule Explained | ClockShark`.

Run `/publish-readiness [file] --proof-sidecar research/validation-[topic-slug]-[YYYY-MM-DD].md` to confirm the article is clean and all proof, URL validation, source support, content score, and AEO/GEO gates pass. The command reads the validation sidecar without exposing proof infrastructure in public copy.

## Automatic Scrub And Publish Readiness

**CRITICAL**: Immediately after saving the article file, automatically invoke the content scrubber and then `/publish-readiness` before scoring, optimization, or handoff.

### Why This Matters
AI-generated content often contains invisible Unicode marks and characteristic punctuation patterns. Scrubbing handles cleanup. The linter handles AI-writing detection and Simpro style enforcement.

### Scrub And Publish Readiness Process
1. **Invoke Scrubber**: Run `/scrub [file-path]` on the saved article file
2. **Invoke Publish Readiness**: Run `/publish-readiness [file-path] --proof-sidecar research/validation-[topic-slug]-[YYYY-MM-DD].md`
3. **Automatic Execution**: This should happen automatically, not require user action
4. **Timing**: Must occur immediately after file save, before scoring or agent processing
5. **Scope**: Scrub and publish-readiness checks apply to the main article file only; proof maps live in the validation sidecar.
6. **Error Handling**: If `/publish-readiness` fails, fix the highest-severity gate it reports. Use `context/aeo-geo-blog-strategy.md` for proof policy and individual module debugging. Review `because` grammar in context during each revision loop, fix the sentence when comma placement changes or clarifies meaning, and rerun `/scrub` plus `/publish-readiness`.
7. **AI copy avoid-rule errors**: Fix copy avoid-rule errors before handoff. The linter blocks modal verbs, passive voice, repeated starts, vague generalizations, filler words, and long sentences in Simpro web copy.

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

### Example Workflow
1. Write article and save to `drafts/article-name-2025-10-31.md`.
2. Run `/scrub`, AI copy lint, URL validation, and the required proof gate stack above. Review every `because` construction during this loop, fix grammar in the sentence itself, and rerun the gates.
3. If errors remain, revise once and rerun the same stack.
4. Then proceed with scoring and optimization agents below.

This keeps cleanup separate from AI copy detection before any further processing.

URL validation confirms destinations resolve; it does not prove the page supports the claim. Use `context/aeo-geo-blog-strategy.md` for proof, source support, metric, FAQ, PAA, quote, testimonial, and customer metric boundaries.

## Automatic Agent Execution
After saving, scrubbing, linting, and passing the quality loop, execute optimization agents:

### 1. Content Analyzer Agent (NEW!)
- **Agent**: `content-analyzer`
- **Input**: Full article, meta elements, keywords, SERP data (if available)
- **Output**: Comprehensive analysis covering search intent, keyword distribution, content scope comparison, readability score, and SEO quality rating
- **File**: `drafts/content-analysis-[topic-slug]-[YYYY-MM-DD].md`

This new agent uses 5 specialized analysis modules:
- Search intent analysis
- Keyword distribution, terminology coverage, and clustering
- Content length vs competitors
- Readability scoring (Flesch scores)
- SEO quality rating (0-100)

### 2. SEO Optimizer Agent
- **Agent**: `seo-optimizer`
- **Input**: Full article content
- **Output**: SEO optimization report and suggestions
- **File**: `drafts/seo-report-[topic-slug]-[YYYY-MM-DD].md`

### 3. Meta Creator Agent
- **Agent**: `meta-creator`
- **Input**: Article content and primary keyword
- **Output**: Multiple meta title/description options
- **File**: `drafts/meta-options-[topic-slug]-[YYYY-MM-DD].md`

### 4. Internal Linker Agent
- **Agent**: `internal-linker`
- **Input**: Article content
- **Output**: Specific internal linking recommendations
- **File**: `drafts/link-suggestions-[topic-slug]-[YYYY-MM-DD].md`

### 5. Keyword Mapper Agent
- **Agent**: `keyword-mapper`
- **Input**: Article and target keywords
- **Output**: Keyword placement analysis and improvements
- **File**: `drafts/keyword-analysis-[topic-slug]-[YYYY-MM-DD].md`

## Automatic Quality Loop

After saving the initial draft, automatically run the scrubber and publish-readiness gate:

### Step 1: Scrub The Draft
Run the scrubber before publish readiness:
```bash
/scrub drafts/[article-file].md
```

### Step 2: Confirm Publish Readiness
Run the command-system gate:
```bash
/publish-readiness drafts/[article-file].md --proof-sidecar research/validation-[topic-slug]-[YYYY-MM-DD].md
```

The draft must have zero blocking findings, general content quality at 85/100 or higher, and AEO/GEO at 90/100 or higher before `/optimize`.

### Step 3: Evaluate Score
The publish-readiness command includes 5 content-quality dimensions plus the required AEO/GEO gate:

| Dimension | Weight | Target |
|-----------|--------|--------|
| Humanity/Voice | 30% | No AI phrases, use contractions |
| Specificity | 25% | Concrete operational and workflow detail; proof-sensitive names, numbers, quotes, metrics, dates, and outcomes remain score-neutral until validated |
| Structure Balance | 20% | 40-70% prose (not all lists) |
| SEO Compliance | 15% | Keywords, meta, structure |
| Readability | 10% | Flesch 60-70, grade 8-10 |

### Step 4: Auto-Revise if Needed
If content quality is below 85/100 or AEO/GEO is below 90/100:
1. Review the `priority_fixes` from `/publish-readiness`
2. Apply the top 3-5 fixes automatically
3. Rerun `/scrub`
4. Review `because` grammar in context, then rerun `/publish-readiness`
5. Repeat once more if still below threshold

### Step 5: Route Based on Final Score
- **General content quality score >= 85/100 and AEO/GEO score >= 90/100**: Save to `drafts/` and proceed to optimization agents
- **Any AI copy lint errors after 1 revision, or general content quality score < 85/100 or AEO/GEO score < 90/100 after 2 iterations**: Save to `review-required/` with a `_REVIEW_NOTES.md` file containing lint findings, scoring details, AEO/GEO failed checks, and remaining issues

### Review-Required Folder
Articles that fail quality threshold after 2 revision attempts go to `review-required/`:
```
review-required/
├── article-name-[YYYY-MM-DD].md
└── article-name-[YYYY-MM-DD]_REVIEW_NOTES.md
```

The `_REVIEW_NOTES.md` file contains:
- Final composite score
- Dimension breakdown
- Remaining priority fixes
- Reason for human review

## Quality Standards
Every article must meet these requirements:

### Content Requirements
- Intent/evidence-complete word target based on the Reader Contract, search intent, and proof available
- Proper H1/H2/H3 hierarchy
- Primary keyword naturally integrated
- 3-5 internal links to your site content
- 2-3 external authoritative links
- Compelling meta title and description
- Clear introduction and conclusion
- Actionable, valuable information
- Brand voice maintained
- Target audience focused

### Engagement Requirements
- **Compelling hook** in first 1-2 sentences (no generic openings)
- Optional proof-backed customer/review POV when it improves the objective
- **Intent-sensitive CTA** count and type based on funnel stage
- **Usable artifact within first 300 words**
- **No paragraphs longer than 4 sentences**
- **Varied sentence rhythm** (mix short punchy + longer flowing)

### Quality Score
- **Composite quality score must be 85/100 or higher**
- **AEO/GEO score must be 90/100 or higher**
- Publish-ready quality

This ensures every article is comprehensive, optimized, engaging, and ready to rank while providing genuine value to your target audience.
