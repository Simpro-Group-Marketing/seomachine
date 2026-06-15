# Write Command

Use this command to create comprehensive, SEO-optimized long-form blog content.

## Usage
`/write [topic or research brief]`

## What This Command Does
1. Creates complete, well-structured long-form articles (2000-3000+ words)
2. Optimizes content for target keywords and SEO best practices
3. Maintains your brand voice and messaging throughout
4. Integrates internal and external links strategically
5. Includes all meta elements for publishing

## Process

### Pre-Writing Review
- **Research Brief**: Review research brief from `/research` command if available
- **Brand Voice**: Check @context/brand-voice.md for tone and messaging
- **Writing Examples**: Study @context/writing-examples.md for style consistency
- **Style Guide**: Follow formatting rules from @context/style-guide.md
- **SEO Guidelines**: Apply requirements from @context/seo-guidelines.md
- **AEO/GEO Strategy**: Apply @context/aeo-geo-blog-strategy.md for Generative Engine Optimization
- **Target Keywords**: Integrate keywords from @context/target-keywords.md naturally
- **Lightning Overlay**: If the topic or research brief mentions Simpro Lightning, AroFlo Lightning, BigChange Lightning, Simpro Group Lightning, JustAsk, Cooper, FieldReady, JobReady, JobScribe, JobBrief, Price Lock, AI tax, TrueTime, DirectLine, Coming Specialists, or any named roadmap specialist, also load @context/lightning-positioning.md and treat it as a scoped overlay.

### AEO/GEO Variable Resolution
Resolve `topic`, `audience`, `main_question`, `related_questions`, `tone`, `expertise`, and `length` from the research brief, repo context, target keyword, and existing PAA artifact before writing. `/write` may skip live AnswerSocrates only when the supplied brief already includes PAA questions. If PAA questions are missing, ask for a PAA/FAQ CSV or run `/article` for full AnswerSocrates collection.

### E-E-A-T Proof Map Inputs
Before drafting, resolve an E-E-A-T Proof Map:
- **Experience**: Customer case studies, customer outcomes, review-site experience evidence / VoC themes, implementation/support themes, user pain, and field workflow examples.
- **Expertise**: Product/feature knowledge, source-backed workflow explanations, expert quotes, author/reviewer metadata, and Simpro workflow specificity.
- **Authority/Trust**: Public research, case-study URLs, review-site/source links, limitations/caveats, and no invented proof.
- **Context sources**: Pull case-study URLs from @context/internal-links-map.md, approved metrics/proof candidates from @context/features.md, and review-site experience evidence / VoC or competitor experience themes from @context/competitor-analysis.md or future review-context files.
- **Public-copy rule**: Context-backed metrics are valid only when the article body uses public-facing source links, such as the public case-study URL, review-site URL, or public research source.

### Simpro Web Copy Rules
- Use numerals for cardinal numbers, including 1-9.
- Do not block source-visible metric wording when a public proof source spells out the number; preserve the supported claim wording and rely on Metric Proof Pack, numeric claim source guard, and source support guard for proof.
- Always put a comma before "because".
- Only 1 link per paragraph. Move the second link to a separate paragraph or remove it.
- Do not write source/proof meta-commentary such as "that case study is useful for this topic" or "this source is relevant for the article." Translate proof into audience-facing takeaways, outcomes, or workflow lessons.

### Down-Funnel Internal Link Rule

Every draft must include at least 1 contextual down-funnel internal link to `/industries`, `/industries/...`, `/solutions/...`, or `/features/...` from @context/internal-links-map.md. Prefer the specific industry page when industry intent is clear, the `https://www.simprogroup.com/industries` hub for broad trades or general industry topics, the relevant solution page for category/workflow topics, and the relevant feature page for feature/workflow topics. Anchor text must match the destination keyword or an approved anchor example from @context/internal-links-map.md.

Feature and solution links must use function-bearing anchor text that explains the workflow, category, or outcome behind the destination. A feature or solution name alone is not enough. Use anchors like "field service payments," "accounts receivable follow-up with Fast Cash," or "field service management software" instead of "Simpro Payments," "Fast Cash," or "Simpro Premium."

### Content Structure

#### 1. Headline (H1)
- Include primary keyword naturally
- Create compelling, click-worthy title
- Keep under 60 characters for SERP display
- Promise clear value to reader

#### 2. Introduction (150-250 words)

**CRITICAL: Direct Answer First (AI Search Optimization)**

For any "best/top/how" query, the first 1-2 sentences MUST directly answer the question. AI scrapers (ChatGPT, Perplexity, Gemini) pull from the top of the page. Don't bury the answer behind narrative.

**Example — "best project management tools":**
> The best project management tools in 2026 are Asana, Monday, and ClickUp — each built for different team sizes and workflows. Here's how they compare.

After the direct answer, use a hook to keep human readers engaged.

**Choose ONE hook type for each article:**

| Hook Type | Example | Best For |
|-----------|---------|----------|
| **Provocative Question** | "What if the 'free' plan is actually costing you $500/month in lost opportunities?" | Challenging assumptions |
| **Specific Scenario** | "Last Tuesday, Sarah checked her dashboard and discovered something alarming: her site had been invisible to Google for three weeks." | Creating emotional connection |
| **Surprising Statistic** | "73% of SaaS users who switch platforms do so within 18 months, and most cite the same three reasons." | Data-driven topics |
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
- Each bullet is a standalone claim with specifics (numbers, names, outcomes)
- NOT a table of contents — these are the article's actual conclusions
- Written after the full article is drafted (so the takeaways are accurate)

#### 3A. AEO/GEO Structure Requirements

Apply these requirements from @context/aeo-geo-blog-strategy.md:
- **Capsule Method**: Add a 50-60 word direct-answer capsule below the H1 and at least 60% of major H2s.
- **PAA selection**: Use 3-5 PAA or FAQ questions from AnswerSocrates, SERP research, Reddit, YouTube, or a user-provided CSV.
- **Source mapping**: Integrate at least three credible external sources inside natural sentences; map each source to the claim it supports.
- **FAQ proof**: Every claim-bearing FAQ answer must include a public proof link inside the answer, or map the exact question to a question-specific Source Map / FAQ Proof Map entry with a public URL. Context file paths alone do not count.
- **E-E-A-T Proof Map**: Include named author, last-updated date, reviewer if available, Experience proof, Expertise proof, Authority/Trust proof, named customer proof or expert quote, and honest limitations where relevant.
- **Context boundary**: Use `context/` files as the internal source of truth for voice, positioning, keywords, product framing, internal links, approved claims, proof candidates, and approved metrics. Public copy may use public sources and context-backed proof, but must not mention "repo context," context file paths, Source Maps, PAA artifacts, change summaries, or internal proof-path notes.
- **Customer proof routing**: When citing customer proof, pair the case-study URL/theme from @context/internal-links-map.md with the metric/proof point from @context/features.md. Use exact quotes only when verified from the case-study page, Quote Matrix, Customer Stories, or References; if no mapped metric exists, cite only the broad theme.
- **Customer proof selection governance**: Run or consult `python data_sources/modules/customer_proof_selector.py "[topic]" --title "[title]" --objective "[objective]" --slate --roles metric,quote,theme --limit 10`. Use the generated selector-first `Customer Proof Slate` before drafting; choose the strongest approved proof for the objective; if selected proof is overused, add a selector-backed, source-specific `Reuse reason` in the validation sidecar.
- **Proof-index intake**: Add new proof candidates through `context/customer-proof-intake-template.csv` and validate with `python data_sources/modules/customer_proof_index_intake.py validate [input.csv] --index context/customer-proof-index.json` before relying on them in selector slates.
- **Review proof routing**: For review-derived E-E-A-T stories, consult `customer_proof_selector.py` with `--slate --roles experience_story --require-eeat-story`, then run the review story identity gate from the required stack below. Use `context/aeo-geo-blog-strategy.md` for Review Story Selection, Review Site Theme Selection, Capterra theme use, exact-quote, rating, and metric boundaries.
- **Customer Proof Pack**: Use the brief's Customer Proof Pack before placing direct quotes, named customer proof, approved metrics, or review-derived Experience patterns. If the pack is partial or blocked, omit unsupported claims.
- **Schema notes**: Include BlogPosting, FAQPage when FAQ is present, Author, and VideoObject when a video is embedded.

#### 4. Main Body (1800-2500+ words)
- **Logical Flow**: Organize sections in clear, progressive order
- **H2 Sections**: 4-7 main sections covering comprehensive topic scope
- **H3 Subsections**: Break complex sections into digestible pieces
- **Keyword Integration**: Use primary keyword 1-2% density, variations throughout
- **Depth**: Provide thorough, actionable information at each point
- **Data**: Reference statistics and studies to support claims
- **Visuals**: Note where images, screenshots, or graphics enhance understanding
- **YouTube Embed**: Include at least one relevant YouTube video (prefer your own channel, then authoritative third-party) — AI models cross-reference video and article content
- **Lists**: Use bulleted or numbered lists for scannability
- **Formatting**: Bold key concepts, use short paragraphs (2-4 sentences MAX)

**REQUIRED: Mini-Stories (2-3 per article)**

Research shows we're 22x more likely to remember facts wrapped in stories. Every article MUST include 2-3 mini-scenarios with:
- A **specific person** (use names, even if fictional: "Sarah," "Mike," "The team at Acme Corp")
- A **concrete situation** with details (dates, numbers, specifics)
- A **clear outcome** that illustrates the point

**Example mini-story (aim for 50-150 words each):**
> "When Marcus launched his SaaS product in March 2024, he chose the cheapest hosting plan he could find, $5/month seemed like a no-brainer. Six months later, his app hit 10,000 active users. That's when he discovered the hidden bandwidth fees buried in his provider's terms. His $5/month plan suddenly became $89/month. Worse, migrating mid-growth meant a 3-week gap in analytics that cost him a $2,000 partnership deal. The 'savings' from cheap hosting cost him over $3,000."

**Place mini-stories:**
- One in the introduction or early section (to hook readers)
- One in the middle (to re-engage skimmers)
- One near the conclusion (to reinforce the main point)

**REQUIRED: Contextual CTAs (2-3 per article)**

Don't just put one CTA at the end. Embedded CTAs get 121% more conversions than end-only CTAs.

**CTA Placement Strategy:**
| Location | CTA Type | Example |
|----------|----------|---------|
| After first major value section | Soft CTA (learn more) | "Want to see how this works in practice? [Explore our features →]" |
| After comparison/proof section | Medium CTA (try it) | "**Ready to test the difference?** Start a free trial, no credit card required." |
| End of article | Strong CTA (convert) | "**[Start Your Free Trial →]**" with supporting text |

**CTA Rules:**
- Make CTAs contextual (relate to the section content)
- Vary the format (inline text, bold callout, button-style)
- First CTA should appear within the first 500 words
- Never use generic "Click here" text

#### 5. Conclusion (150-200 words)
- **Recap**: Summarize 3-5 key takeaways
- **Action**: Provide clear next steps for reader
- **CTA**: Include relevant call-to-action (free trial, resource download, etc.)
- **Encouragement**: End on empowering, forward-looking note

### SEO Optimization

#### Keyword Placement
- H1 headline
- First paragraph (within first 100 words)
- At least 2-3 H2 headings
- Naturally throughout body (1-2% density)
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
- Break up text with subheadings every 300-400 words

### Target Audience Focus
- **Audience Perspective**: Write for your target audience (defined in @context/brand-voice.md)
- **Practical Application**: Show how information applies to their specific challenges
- **Product Integration**: Naturally mention how your features solve problems (reference @context/features.md)
- **Industry Context**: Reference relevant trends and best practices
- **Technical Accuracy**: Ensure terminology and processes are correct for your industry

### Brand Voice Consistency
- Maintain your brand tone (reference @context/brand-voice.md for specifics)
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
- Conclusion with CTA
- Proper formatting and styling

### 2. Meta Elements
```
---
Meta Title: [50-60 character optimized title]
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
- [ ] Primary keyword in 2+ H2 headings
- [ ] Keyword density 1-2%
- [ ] 3-5+ internal links included
- [ ] 2-3 external authority links
- [ ] Meta title 50-60 characters
- [ ] Meta description 150-160 characters
- [ ] Article 2000+ words
- [ ] Proper H2/H3 hierarchy
- [ ] Readability optimized

### 4. AI Search Optimization Checklist
- [ ] **AEO/GEO score**: Draft is expected to score 90/100 or higher
- [ ] **Direct answer**: First 1-2 sentences directly answer the target query
- [ ] **Key Takeaways**: TL;DR block with 3-5 specific bullet points after introduction
- [ ] **Meta description**: Directly answers the query (not just a teaser)
- [ ] **YouTube embed**: At least one relevant video embedded
- [ ] **FAQ prompts**: Questions written in natural language people would type into ChatGPT
- [ ] **One idea per section**: Each H2/H3 focuses on a single clear concept
- [ ] **Author attribution**: Named author in frontmatter
- [ ] **Capsule Method**: H1 and 60%+ major H2s include 50-60 word direct-answer capsules
- [ ] **PAA**: 3-5 selected PAA/FAQ questions are answered in the draft
- [ ] **source mapping**: At least three source-backed claims use natural contextual links
- [ ] **Customer Proof Pack**: Selector consulted, selected proof documented, source-specific overuse reason added when needed, and approved quotes/metrics mapped before use. Full proof boundaries live in `context/aeo-geo-blog-strategy.md`.
- [ ] **Schema**: BlogPosting, FAQPage, Author, and VideoObject notes are included when relevant

### 5. Engagement Checklist
- [ ] **Hook**: Opens with question, scenario, statistic, or bold statement (NOT generic definition)
- [ ] **APP Formula**: Introduction includes Agree, Promise, Preview elements
- [ ] **Mini-stories**: 2-3 specific scenarios with names, details, and outcomes
- [ ] **Contextual CTAs**: 2-3 CTAs placed throughout (not just at end)
- [ ] **First CTA**: Appears within first 500 words
- [ ] **Paragraph length**: No paragraphs exceed 4 sentences
- [ ] **Sentence rhythm**: Mix of short (5-10 words) and longer sentences (15-25 words)

## File Management
After completing the article, automatically save to:
- **File Location**: `drafts/[topic-slug]-[YYYY-MM-DD].md`
- **File Format**: Markdown with frontmatter and formatted content
- **Naming Convention**: Use lowercase, hyphenated topic slug and current date

Example: `drafts/content-marketing-strategies-2025-10-15.md`

## Validation Sidecar

Save non-public proof infrastructure to a validation sidecar at `research/validation-[topic-slug]-[YYYY-MM-DD].md`. Do not put an `Editorial Validation Appendix`, `PAA/FAQ Provenance`, `Metric Proof Pack`, `Source Map`, `Customer Proof Pack`, `FAQ Proof Map`, or structured data plan in the publishable blog draft.

Preferred publish readiness command:
```bash
python data_sources/modules/publish_readiness.py [file] --proof-sidecar research/validation-[topic-slug]-[YYYY-MM-DD].md
```

Before proof gates, run `python data_sources/modules/public_artifact_guard.py [file-path] --fail-on error` to confirm the article is clean. Then run proof-aware gates with `--proof-sidecar research/validation-[topic-slug]-[YYYY-MM-DD].md` so the guards can read PAA provenance, metric proof, FAQ proof maps, source maps, and Customer Proof Pack rows without exposing them in public copy.

## Automatic Scrub, AI Copy Lint, URL Validation, Metric Proof Pack Guard, Numeric Claim Source Guard, FAQ Proof Guard, PAA Provenance Guard, Source Support Guard, Customer Proof Diversity Guard, And Review Story Identity Guard

**CRITICAL**: Immediately after saving the article file, automatically invoke the content scrubber, run the AI copy linter, run URL validation, run the Metric Proof Pack guard, run the numeric claim source guard, run the FAQ proof guard, run the PAA provenance guard, run the source support guard, run the customer proof diversity guard, and run the review story identity guard before scoring or optimization.

### Why This Matters
AI-generated content often contains invisible Unicode marks and characteristic punctuation patterns. Scrubbing handles cleanup. The linter handles AI-writing detection and Simpro style enforcement.

### Scrub, Lint, URL Validation, Metric Proof Pack Guard, Numeric Claim Source Guard, FAQ Proof Guard, PAA Provenance Guard, Source Support Guard, Customer Proof Diversity Guard, And Review Story Identity Guard Process
1. **Invoke Scrubber**: Run `/scrub [file-path]` on the saved article file
2. **Invoke Public Artifact Guard**: Run `python data_sources/modules/public_artifact_guard.py [file-path] --fail-on error`
3. **Invoke AI Copy Linter**: Run `python data_sources/modules/ai_copy_linter.py [file-path] --profile simpro-web --fail-on error`
4. **Invoke URL Validation**: Run `python data_sources/modules/url_validator.py [file-path] --fail-on unresolved`
5. **Invoke Metric Proof Pack Guard**: Run `python data_sources/modules/metric_proof_pack_guard.py [file-path] --proof-sidecar research/validation-[topic-slug]-[YYYY-MM-DD].md --fail-on error`
6. **Invoke Numeric Claim Source Guard**: Run `python data_sources/modules/numeric_claim_source_guard.py [file-path] --proof-sidecar research/validation-[topic-slug]-[YYYY-MM-DD].md --fail-on error`
7. **Invoke FAQ Proof Guard**: Run `python data_sources/modules/faq_proof_guard.py [file-path] --proof-sidecar research/validation-[topic-slug]-[YYYY-MM-DD].md --fail-on error`
8. **Invoke PAA Provenance Guard**: Run `python data_sources/modules/paa_provenance_guard.py [file-path] --proof-sidecar research/validation-[topic-slug]-[YYYY-MM-DD].md --fail-on error`
9. **Invoke Source Support Guard**: Run `python data_sources/modules/source_support_guard.py [file-path] --proof-sidecar research/validation-[topic-slug]-[YYYY-MM-DD].md --fail-on error`
10. **Invoke Customer Proof Diversity Guard**: Run `python data_sources/modules/customer_proof_diversity_guard.py [file-path] --proof-sidecar research/validation-[topic-slug]-[YYYY-MM-DD].md --fail-on error`
11. **Invoke Review Story Identity Guard**: Run `python data_sources/modules/review_story_identity_guard.py [file-path] --proof-sidecar research/validation-[topic-slug]-[YYYY-MM-DD].md --fail-on error`
11. **Automatic Execution**: This should happen automatically, not require user action
12. **Timing**: Must occur immediately after file save, before scoring or agent processing
13. **Scope**: Scrub, lint, validate, metric proof-check, numeric proof-check, FAQ proof-check, PAA provenance-check, source-support-check, customer-proof-check, and review-story-check the main article file only; proof maps live in the validation sidecar.
14. **Error Handling**: If linter errors remain, revise once, rerun `/scrub`, rerun the linter, then route to `review-required/` with lint findings if errors remain. If public artifact guard fails, move proof-only headings to the validation sidecar. If URL validation fails, replace or verify the unresolved link before `/optimize`. If Metric Proof Pack guard fails, research usable metrics and add `Metric Proof Pack` rows with `Search log`, `Approved metric`, public URL or proof artifact, source-visible Evidence, Status: approved, and Use in the sidecar. If numeric claim source guard fails, add a public proof link, map the same claim to a Source Map / Proof Pack row with a public URL or local proof artifact in the sidecar, or remove the unsupported number. If FAQ proof guard fails, add a public proof link inside the FAQ answer, map the exact question to a question-specific Source Map / FAQ Proof Map entry with a public URL in the sidecar, or remove the unsupported claim. If PAA provenance guard fails, add a `PAA/FAQ Provenance` block with an allowed source, real artifact path, and exact selected questions to the sidecar. If source support guard fails, add a strict proof row with Claim, URL, Evidence, and Status: approved to the sidecar, use Evidence visible in the cited source, or remove the unsupported claim. If customer proof diversity guard fails, add Quote Matrix, Reference, Customer Story, or review-site search evidence to the Customer Proof Pack, add Customer Proof Selection Decision, or document a source-specific `Reuse reason` plus selector-backed proof that no stronger underused approved proof fits the same role. If review story identity guard fails, add an identity-backed Review Story Selection with a public review URL and same paragraph article link, or remove the review-derived story. Context file paths alone do not count.
15. **Warnings**: Include warning findings in review notes, but do not block unless strict mode is requested

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
- Line-level findings for FAQ answers missing a public proof link or question-specific Source Map entry

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
2. Run `/scrub`, AI copy lint, URL validation, and the required proof gate stack above.
3. If errors remain, revise once and rerun the same stack.
4. Then proceed with scoring and optimization agents below.

This keeps cleanup separate from AI copy detection before any further processing.

URL validation confirms destinations resolve; it does not prove the page supports the claim. Use `context/aeo-geo-blog-strategy.md` for proof, source support, metric, FAQ, PAA, quote, testimonial, and customer metric boundaries.

## Automatic Agent Execution
After saving, scrubbing, linting, and passing the quality loop, execute optimization agents:

### 1. Content Analyzer Agent (NEW!)
- **Agent**: `content-analyzer`
- **Input**: Full article, meta elements, keywords, SERP data (if available)
- **Output**: Comprehensive analysis covering search intent, keyword density, content length comparison, readability score, and SEO quality rating
- **File**: `drafts/content-analysis-[topic-slug]-[YYYY-MM-DD].md`

This new agent uses 5 specialized analysis modules:
- Search intent analysis
- Keyword density & clustering
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

After saving the initial draft, automatically run the AI copy linter and content quality scorer:

### Step 1: Confirm AI Copy Lint Gate
Run the AI copy linter before scoring:
```bash
python data_sources/modules/ai_copy_linter.py drafts/[article-file].md --profile simpro-web --fail-on error
```

The draft must have zero linter errors before scoring. Warnings go into review notes unless strict mode is requested.

### Step 2: Confirm Proof Gates
Run the required proof gate stack above. The draft must have zero blocking findings before scoring.

### Step 3: Score Content
Run the content scorer to evaluate the draft:
```bash
python data_sources/modules/content_scorer.py drafts/[article-file].md --proof-sidecar research/validation-[topic-slug]-[YYYY-MM-DD].md --validate-urls --validate-source-support
```

This scorer command includes URL validation and source support validation before `/optimize`.

### Step 4: Evaluate Score
The scorer evaluates 5 content-quality dimensions plus the required AEO/GEO gate:

| Dimension | Weight | Target |
|-----------|--------|--------|
| Humanity/Voice | 30% | No AI phrases, use contractions |
| Specificity | 25% | Concrete examples, numbers, names |
| Structure Balance | 20% | 40-70% prose (not all lists) |
| SEO Compliance | 15% | Keywords, meta, structure |
| Readability | 10% | Flesch 60-70, grade 8-10 |

### Step 4: Auto-Revise if Needed
If content quality is below 85/100 or AEO/GEO is below 90/100:
1. Review the `priority_fixes` from the scorer
2. Apply the top 3-5 fixes automatically
3. Rerun `/scrub` and the AI copy linter
4. Re-score the content
5. Repeat once more if still below threshold

### Step 5: Route Based on Final Score
- **General content quality score >= 85/100 and AEO/GEO score >= 90/100**: Save to `drafts/` and proceed to optimization agents
- **Any AI copy lint errors after 1 revision, or general content quality score < 85/100 or AEO/GEO score < 90/100 after 2 iterations**: Save to `review-required/` with a `_REVIEW_NOTES.md` file containing lint findings, scoring details, AEO/GEO failed checks, and remaining issues

### Review-Required Folder
Articles that fail quality threshold after 2 revision attempts go to `review-required/`:
```
review-required/
├── article-name-2025-12-10.md
└── article-name-2025-12-10_REVIEW_NOTES.md
```

The `_REVIEW_NOTES.md` file contains:
- Final composite score
- Dimension breakdown
- Remaining priority fixes
- Reason for human review

## Quality Standards
Every article must meet these requirements:

### Content Requirements
- Minimum 2000 words (2500-3000+ preferred)
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
- **2-3 mini-stories** with specific names, details, and outcomes
- **2-3 contextual CTAs** distributed throughout (not just at end)
- **First CTA within 500 words**
- **No paragraphs longer than 4 sentences**
- **Varied sentence rhythm** (mix short punchy + longer flowing)

### Quality Score
- **Composite quality score must be 85/100 or higher**
- **AEO/GEO score must be 90/100 or higher**
- Publish-ready quality

This ensures every article is comprehensive, optimized, engaging, and ready to rank while providing genuine value to your target audience.
