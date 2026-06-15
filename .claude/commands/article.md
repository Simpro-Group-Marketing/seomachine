# Article Command

A unified content creation pipeline that produces comprehensive, SEO-optimized articles through mandatory research, strategic planning, and section-by-section writing.

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

Before opening the browser or drafting, resolve these variables from the user prompt, repo context, existing research, and current SERP/PAA evidence:

| Variable | Resolution Rule |
|----------|-----------------|
| `topic` | Use the user prompt or topic file; ask if missing. |
| `audience` | Derive from @context/brand-voice.md and best-fit guidance; ask only if multiple audiences fit. |
| `main_question` | Infer from target keyword, SERP intent, or user prompt; ask if no primary question is clear. |
| `related_questions` | Use AnswerSocrates PAA, SERP, Reddit, YouTube, or a user-provided PAA/FAQ CSV. |
| `tone` | Use @context/brand-voice.md and @context/style-guide.md unless the user requested another tone. |
| `expertise` | Use @context/features.md, customer proof, expert quotes, and author/reviewer data. |
| `length` | Use `/research-serp` competitive length; default to the top-SERP benchmark if available. |

If a variable cannot be answered by the repo or research, ask the user for only that missing variable. Do not synthesize PAA questions, expert quotes, customer claims, search volume, or ranking evidence.
Customer proof routing: before citing customer proof, generate a selector-first `Customer Proof Slate` with `python data_sources/modules/customer_proof_selector.py "[topic]" --title "[title]" --objective "[objective]" --slate --roles metric,quote,theme --limit 10` so metric, quote, and theme options are compared before drafting. Run `python data_sources/modules/customer_proof_index_health.py --index context/customer-proof-index.json --ledger context/customer-proof-usage-ledger.json` before adding proof candidates. Add new proof candidates through `context/customer-proof-intake-template.csv` and validate with `python data_sources/modules/customer_proof_index_intake.py validate [input.csv] --index context/customer-proof-index.json` before relying on them in selector slates. Then pair approved case-study URL/theme from @context/internal-links-map.md with the metric/proof point from @context/features.md. Use exact quotes only when verified from the case-study page, Quote Matrix, Customer Stories, or References; if no mapped metric exists, cite only the broad theme.
Review-site experience evidence / VoC routing: cite public review-site themes with source links when they show first-hand customer experience with product use, implementation, support, switching, pains, outcomes, or workflows. Capture platform, URL, date checked, product/competitor, experience pattern, evidence summary, and whether any exact quote/rating claim was approved. Use review-derived stories as paraphrased, source-backed experience patterns by default. Do not use exact quotes, named reviewers, star ratings, badges, rankings, aggregate ratings, or category-leadership claims unless they have current source verification and brief-level approval.

### E-E-A-T Proof Map Inputs

Before planning or drafting, resolve an E-E-A-T Proof Map:
- **Experience**: Customer case studies, customer outcomes, review-site experience evidence / VoC themes, implementation/support themes, user pain, and field workflow examples.
- **Expertise**: Product/feature knowledge, source-backed workflow explanations, expert quotes, author/reviewer metadata, and Simpro workflow specificity.
- **Authority/Trust**: Public research, case-study URLs, review-site/source links, limitations/caveats, and no invented proof.
- **Context sources**: Pull case-study URLs from @context/internal-links-map.md, approved metrics/proof candidates from @context/features.md, and review-site experience evidence / VoC or competitor experience themes from @context/competitor-analysis.md or future review-context files.
- **Public-copy rule**: Context-backed metrics are valid only when the article body uses public-facing source links, such as the public case-study URL, review-site URL, or public research source; context-backed proof is never cited as internal context.

### Simpro Web Copy Rules

- Use numerals for cardinal numbers, including 1-9.
- Do not block source-visible metric wording when a public proof source spells out the number; preserve the supported claim wording and rely on Metric Proof Pack, numeric claim source guard, and source support guard for proof.
- Always put a comma before "because".
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
5. Wait for results and extract visible questions with `browser_evaluate`.
6. Save results to `research/paa-questions-[topic-slug]-[YYYY-MM-DD].md`.

If AnswerSocrates is blocked, unavailable, or requires login/CAPTCHA, record the blocker in the PAA artifact and ask the user for a PAA/FAQ CSV export. Do not invent replacement questions.

### PAA Artifact Format

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
|----------|--------|-----------------|---------------|
| [question] | [intent] | [H2/FAQ] | [capsule/list/table/FAQ] |
```

---

## STEP 1: SERP Analysis (MANDATORY)

**You MUST research before writing. No exceptions.**

### Process

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
   | **Gaps** | Topics covered superficially (<150 words) |
   | **Missing Angles** | Perspectives not addressed |
   | **Unsupported Claims** | Statements without data/sources |
   | **Outdated Info** | Old statistics, deprecated tools |
   | **What They Do Well** | Strong sections to match |

3. **Build Competitor Gap Blueprint**
   Document opportunities where your brand content can beat, not match:
   - Gaps found in all competitors (must-fill)
   - Unique angles no one covers
   - Data needed to be more specific
   - Outdated info to update with 2025 data

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

## Google-Validated Structure
Based on what's ranking, these sections appear essential:
1. [Common H2 found across multiple articles]
2. [Another common section]
...

## Competitor Gap Blueprint

### MUST-FILL GAPS (found in 3+ competitors)
- [Gap 1]: [How to address]
- [Gap 2]: [How to address]

### DIFFERENTIATION OPPORTUNITIES
- [Unique angle 1]
- [Unique angle 2]

### DATA NEEDED
- [Specific statistic to find]
- [Expert quote needed]

### OUTDATED INFO TO UPDATE
- [Old stat] → Need 2025 version
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

3. **Extract Quotable Insights**
   Pull specific quotes that can inform (or be used in) the article.

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
- Quotable: "[specific quote that could inform article]"

[Repeat for 5 threads]

### Pain Points Identified
- [Pain point 1]
- [Pain point 2]

### Success Stories Found
- [Story with specific details]

### Real User Language
- Users say "[phrase]" instead of "[what competitors say]"

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

### Expert Takes
- [Notable opinion from creator]

## Synthesis: Unique Insights for Article

### Insights NOT Available in SEO Content
1. [Unique insight from social research]
2. [Another unique insight]

### Questions to Answer (from real users)
1. [Real question from Reddit/YouTube]
2. [Another real question]

### Story Seeds (for mini-stories)
- [Story possibility based on real user experience]

### Language to Use
- Use "[real user phrase]" instead of "[generic SEO phrase]"
```

---

## STEP 3: Article Planning

**Create a section-by-section plan before writing.**

### Process

1. **Merge Research**
   Combine:
   - SERP analysis (structure that ranks)
   - Competitor gaps (opportunities to beat)
   - Social research (unique insights)
   - AnswerSocrates PAA questions and intent clusters
   - your brand context (features, brand voice)

2. **Create Google-Validated Structure**
   - Include sections that appear in multiple top-ranking articles
   - Add sections to fill identified gaps
   - Order for logical reader flow

3. **Assign Section Details**
   For each section, specify:

   | Element | Purpose |
   |---------|---------|
   | **Type** | intro / body-how-to / body-comparison / body-explanation / faq / conclusion |
   | **Word Target** | Based on competitor depth + gap filling |
   | **Strategic Angle** | What unique perspective we bring |
   | **Engagement Hook** | How this section captures attention |
   | **Knowledge Gaps** | Which competitor gaps this fills |
   | **Unique Data** | Social research insights to include |
   | **Internal Links** | Which your brand pages to link |
   | **AEO/GEO Target** | Capsule / PAA / FAQ / list / table / definition |
   | **Source Mapping** | External source, claim, anchor text, and target section |
   | **Metric Proof Pack** | Metric requirement, Search log, Approved metric rows, public URL or local proof artifact, source-visible Evidence, Status: approved, intended Use, rejected metrics |
   | **E-E-A-T Proof Map** | Experience proof, Expertise proof, Authority/Trust proof, case-study candidates, review-site VoC candidates, claims excluded because proof is missing |
   | **Customer Proof Pack** | Selector result, selected proof, source-specific overuse reason when needed, approved quotes/metrics, claims excluded |
   | **CTA** | soft / medium / strong (if applicable) |
   | **Mini-Story** | Whether to place a story here |

4. **Plan Engagement Distribution**
   - Mini-stories: Early, middle, near-end (2-3 total)
   - CTAs: First 500 words (soft), middle (medium), end (strong)
   - Featured snippet opportunities: FAQ, definitions

### Output
Save to: `research/article-plan-[topic-slug]-[YYYY-MM-DD].md`

```markdown
# Article Plan: [Topic]

**Date**: [YYYY-MM-DD]
**Total Word Target**: [count]
**Primary Keyword**: [keyword]
**Secondary Keywords**: [list]

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
- **Metric Proof Pack**:
  - **Metric requirement**: required / not applicable
  - **Search log**: [public pages and local proof artifacts checked for source-visible numbers]
  - **Approved metric**: [metric claim, public proof URL or local proof artifact, source-visible Evidence, Status: approved, intended Use]
  - **Rejected metrics**: [candidate metric, source checked, reason excluded]
- **E-E-A-T Proof Map**: [Experience proof, Expertise proof, Authority/Trust proof, case-study candidates, review-site VoC candidates, public-facing source links, claims excluded because proof is missing]
- **Customer Proof Pack**:
  - **Pack status**: ready / partial / blocked
  - **Selection governance**: Run or consult `python data_sources/modules/customer_proof_selector.py "[topic]" --title "[title]" --objective "[objective]" --slate --roles metric,quote,theme --limit 10`; choose the most relevant approved proof, not the easiest mapped case study.
  - **Customer Proof Slate**: [generated selector command plus metric, quote, theme, and experience_story role rows when applicable]
  - **Topic or page fit**: [topic, audience, region, trade, funnel stage]
  - **Quote Matrix candidates**: [customer, trade, region, theme, exact quote or summary, source row/link, approval status]
  - **Case-study proof paths**: [customer, public URL, supported non-numeric theme]
  - **Review-site experience evidence**: [platform, URL, date checked, product/competitor, experience pattern, evidence summary, exact quote/rating approval status]
  - **Customer Proof Selection Decision**: [selector command, selected proof IDs, rejected stronger candidates, final use in copy]
  - **Reuse reason**: [source-specific; required when customer-proof-usage-ledger.json marks the selected proof as overused; must prove no stronger underused approved proof fits the same role]
  - **Approved quotes**: [exact quote/testimonial, customer/brand/reviewer, source type, public proof URL, Evidence, approval status]
  - **Approved metrics**: [named customer metric, customer/brand, public proof URL, Evidence, approval status]
  - **Use in copy**: [exact quote / paraphrased theme / named metric / omit]
  - **Claims excluded**: [claim and missing proof reason]
- **Schema Notes**: BlogPosting, FAQPage if FAQ is present, Author, VideoObject if video is embedded
- **AEO/GEO Score Target**: 90/100 or higher

### 1. Introduction
- **Type**: intro
- **Word Target**: 200
- **Hook Strategy**: [question / scenario / statistic / bold statement]
- **APP Elements**: [Agree point, Promise, Preview]
- **Mini-Story**: [Yes - place opening scenario here]
- **CTA**: soft (within first 500 words)
- **Unique Data**: [Insight from social research to include]

### 2. [H2 Title]
- **Type**: body-explanation
- **Word Target**: 300
- **Strategic Angle**: [What unique perspective]
- **Knowledge Gap**: [Which competitor gap this fills]
- **Internal Links**: [your brand page to link]
- **Unique Data**: [Social insight to include]

### 3. [H2 Title]
- **Type**: body-how-to
- **Word Target**: 400
- **Strategic Angle**: [Unique angle]
- **Knowledge Gap**: [Gap being filled]
- **Mini-Story**: [Yes - real user scenario]

[Continue for all sections...]

### N. FAQ
- **Type**: faq
- **Word Target**: 200
- **Questions from Research**:
  1. [Real question from Reddit]
  2. [Another real question]
  3. [Question competitors don't answer]
  4. [Featured snippet opportunity]
- **Featured Snippet**: Yes

### N+1. Conclusion
- **Type**: conclusion
- **Word Target**: 200
- **CTA**: strong
- **Mini-Story**: [Optional - reinforcing story]

## Engagement Map

| Element | Location |
|---------|----------|
| Mini-Story 1 | Introduction |
| Mini-Story 2 | Section [X] |
| Mini-Story 3 | Conclusion (optional) |
| CTA (soft) | Section 1 or 2 |
| CTA (medium) | Section [X] |
| CTA (strong) | Conclusion |

## Gap-to-Section Mapping

| Competitor Gap | Section Addressing It |
|----------------|----------------------|
| [Gap 1] | Section [X] |
| [Gap 2] | Section [Y] |

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
- 150-250 words

**Do NOT open with:**
- "[Product category] is..."
- "When it comes to..."
- "If you're looking for..."
- "In today's world..."

#### Key Takeaways Block (After Introduction, Before First H2)
**Requirements:**
- 3-5 bullet points summarizing the article's actual conclusions
- Each bullet is a standalone claim with specifics (numbers, names, outcomes)
- NOT a table of contents — these are the conclusions up front
- Format as blockquote with bold "Key Takeaways" header
- Written after full article is drafted, then placed here

#### Body: How-To
**Requirements:**
- Numbered steps for sequential processes
- Each step actionable and specific
- Time estimates where helpful
- Common mistakes to avoid
- 250-400 words per section

#### Body: Comparison
**Requirements:**
- Balanced (acknowledge competitor strengths)
- Data tables for key metrics
- Specific prices/features
- "Best for" recommendations
- 300-400 words per section

#### Body: Explanation
**Requirements:**
- Progressive complexity (simple → advanced)
- Analogies for complex concepts
- Examples with specifics
- Embed at least one relevant YouTube video in a body section where it adds context (prefer your own channel, then authoritative third-party)
- 250-400 words per section

#### FAQ
**Requirements:**
- 4-6 questions from research (real user questions)
- 40-60 word answers (featured snippet optimized)
- Direct answer first, then context
- FAQ proof is required for every FAQ answer that makes a claim: include a public proof link inside the answer, or map the exact question to a question-specific Source Map / FAQ Proof Map entry with a public URL. Context file paths alone do not count.
- PAA provenance is required for every FAQ question: include `PAA/FAQ Provenance` with Source, Artifact, and exact Selected questions from AnswerSocrates, SERP, Reddit, YouTube, or a user PAA/FAQ CSV.
- 200-300 words total

#### Conclusion
**Requirements:**
- NOT just a summary - add value
- 3-5 key takeaways as actionable items
- Clear next steps ("This week:", "This month:")
- Strong CTA with risk reversal
- Empowering, forward-looking close
- 150-250 words

### Writing Process Per Section

For each section in the plan:

1. **Write Draft**
   - Use section-specific requirements above
   - Include planned unique data/insights from research
   - Follow word target
   - Apply planned engagement hook

2. **Edit Pass**
   - Remove AI phrases ("In today's", "It's important to note", "When it comes to")
   - Replace vague words with specifics ("many" → "73%")
   - Check paragraph length (max 4 sentences)
   - Vary sentence rhythm (mix 5-10 word + 15-25 word)
   - Add conversational devices (contractions, questions, parenthetical asides)
   - Verify active voice

3. **Verify Requirements**
   - Section-specific criteria met
   - Planned insights included
   - Word target within ±10%

### Assembly

After all sections are written and edited:

1. **Combine Sections**
   - Assemble in planned order
   - Check transitions between sections
   - Verify internal link placement
   - Confirm CTA distribution

2. **Add Meta Elements**
   ```markdown
   ---
   Meta Title: [50-60 chars]
   Meta Description: [150-160 chars]
   Primary Keyword: [keyword]
   Secondary Keywords: [list]
   URL Slug: /blog/[slug]
   Word Count: [count]
   Internal Links: [list]
   External Links: [list]
   ---
   ```

3. **Generate Checklists**

   **SEO Checklist:**
   - [ ] Primary keyword in H1
   - [ ] Primary keyword in first 100 words
   - [ ] Primary keyword in 2+ H2 headings
   - [ ] Keyword density 1-2%
   - [ ] 3-5+ internal links
   - [ ] 2-3 external authority links
   - [ ] Meta title 50-60 chars
   - [ ] Meta description 150-160 chars
   - [ ] 2000+ words

   **AI Search Optimization Checklist:**
   - [ ] Direct answer in first 1-2 sentences (not buried behind narrative)
   - [ ] Key Takeaways block with 3-5 specific bullet points after introduction
   - [ ] Meta description directly answers the target query
   - [ ] At least one relevant YouTube video embedded
   - [ ] FAQ questions written in natural prompt language
   - [ ] One idea per section (each H2/H3 focuses on single concept)
   - [ ] Author attribution in frontmatter
   - [ ] AnswerSocrates PAA artifact exists at `research/paa-questions-[topic-slug]-[YYYY-MM-DD].md`
   - [ ] Capsule Method applied to H1 and 60%+ major H2s
   - [ ] AEO/GEO Map complete with selected PAA, source mapping, and E-E-A-T proof
   - [ ] Metric Proof Pack checked using the post-writing gate stack
   - [ ] FAQ proof checked using the post-writing gate stack
   - [ ] PAA provenance checked using the post-writing gate stack
   - [ ] Schema notes included for BlogPosting, FAQPage, Author, and VideoObject when relevant
   - [ ] Public article body does not mention "repo context," context file paths, Source Maps, PAA artifacts, change summaries, or internal proof-path notes

   **Engagement Checklist:**
   - [ ] Hook (not generic opening)
   - [ ] APP Formula in intro
   - [ ] 2-3 mini-stories with names/details/outcomes
   - [ ] 2-3 contextual CTAs
   - [ ] First CTA within 500 words
   - [ ] No paragraphs > 4 sentences
   - [ ] Varied sentence rhythm

   **Research Integration Checklist:**
   - [ ] Addresses 3+ competitor gaps
   - [ ] Includes 5+ social research insights
   - [ ] Uses real user language
   - [ ] Answers questions from Reddit/YouTube
   - [ ] Updates outdated info with 2025 data

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

### 2. Lint AI Copy
```bash
python data_sources/modules/ai_copy_linter.py drafts/[filename].md --profile simpro-web --fail-on error
```

If errors remain, revise once, rerun `/scrub`, rerun the linter, then move to `review-required/` with lint findings if errors remain. Warnings go into review notes unless strict mode is requested.

### 3. Validate URLs
```bash
python data_sources/modules/url_validator.py drafts/[filename].md --fail-on unresolved
```

URL validation confirms destinations resolve; it does not prove the page supports the claim, so Source Map and E-E-A-T proof review still verify claim support.

### Validation Sidecar And Public Artifact Check

Save proof-only blocks to a validation sidecar at `research/validation-[topic-slug]-[YYYY-MM-DD].md`. The article draft must not include an `Editorial Validation Appendix`, `PAA/FAQ Provenance`, `Metric Proof Pack`, `Source Map`, `Customer Proof Pack`, `FAQ Proof Map`, or structured data plan as public copy.

Preferred publish readiness command:
```bash
python data_sources/modules/publish_readiness.py [file] --proof-sidecar research/validation-[topic-slug]-[YYYY-MM-DD].md
```

Run `python data_sources/modules/public_artifact_guard.py drafts/[filename].md --fail-on error` before proof gates. Run proof-aware gates with `--proof-sidecar research/validation-[topic-slug]-[YYYY-MM-DD].md` so the guards can read the sidecar without exposing proof infrastructure in the article.

### 4. Check Metric Proof Pack
```bash
python data_sources/modules/metric_proof_pack_guard.py drafts/[filename].md --proof-sidecar research/validation-[topic-slug]-[YYYY-MM-DD].md --fail-on error
```

Use `context/aeo-geo-blog-strategy.md` for the Metric Proof Pack policy and evidence boundary.

### 5. Check Numeric Claim Sources
```bash
python data_sources/modules/numeric_claim_source_guard.py drafts/[filename].md --proof-sidecar research/validation-[topic-slug]-[YYYY-MM-DD].md --fail-on error
```

Use `context/aeo-geo-blog-strategy.md` for numeric-claim proof requirements.

### 6. Check FAQ Proof
```bash
python data_sources/modules/faq_proof_guard.py drafts/[filename].md --proof-sidecar research/validation-[topic-slug]-[YYYY-MM-DD].md --fail-on error
```

Use `context/aeo-geo-blog-strategy.md` for FAQ proof requirements.

### 7. Check PAA Provenance
```bash
python data_sources/modules/paa_provenance_guard.py drafts/[filename].md --proof-sidecar research/validation-[topic-slug]-[YYYY-MM-DD].md --fail-on error
```

Use `context/aeo-geo-blog-strategy.md` for PAA provenance source-label and proof-boundary policy.

### 8. Check Source Support
```bash
python data_sources/modules/source_support_guard.py drafts/[filename].md --proof-sidecar research/validation-[topic-slug]-[YYYY-MM-DD].md --fail-on error
```

Use `context/aeo-geo-blog-strategy.md` for source support, Approved quote, testimonial, and named customer metric boundaries.

### 9. Check Customer Proof Diversity
```bash
python data_sources/modules/customer_proof_diversity_guard.py drafts/[filename].md --proof-sidecar research/validation-[topic-slug]-[YYYY-MM-DD].md --fail-on error
```

Before selecting proof, generate a `Customer Proof Slate` with `customer_proof_selector.py --slate`; use `context/aeo-geo-blog-strategy.md` for diversity and reuse policy.

### 10. Check Review Story Identity
```bash
python data_sources/modules/review_story_identity_guard.py drafts/[filename].md --proof-sidecar research/validation-[topic-slug]-[YYYY-MM-DD].md --fail-on error
```

Use `context/aeo-geo-blog-strategy.md` for Review Story Selection, Review Site Theme Selection, identity, same-paragraph link, exact-quote, rating, and metric boundaries.

### 11. Score Content Quality
```bash
python data_sources/modules/content_scorer.py drafts/[filename].md --proof-sidecar research/validation-[topic-slug]-[YYYY-MM-DD].md --validate-urls --validate-source-support
```

**Quality Gates:**
- General content quality score must be **85/100** or higher.
- AEO/GEO score must be **90/100** or higher.
- URL validation must pass before `/optimize`.
- Metric Proof Pack guard must pass before scoring or `/optimize`.
- Numeric claim source guard must pass before scoring or `/optimize`.
- FAQ proof guard must pass before scoring or `/optimize`.
- PAA provenance guard must pass before scoring or `/optimize`.
- Source support guard must pass before scoring or `/optimize`.
- Customer proof diversity guard must pass before scoring or `/optimize`.
- Review story identity guard must pass before scoring or `/optimize`.
- A draft only passes if AI copy lint has zero errors, URL validation passes, Metric Proof Pack guard passes, numeric claim source guard passes, FAQ proof guard passes, PAA provenance guard passes, source support guard passes, customer proof diversity guard passes, review story identity guard passes, and both score gates pass.

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
3. Review URL validation blockers from `data_sources/modules/url_validator.py --fail-on unresolved`
4. Review Metric Proof Pack blockers from `data_sources/modules/metric_proof_pack_guard.py --fail-on error`
5. Review numeric claim source blockers from `data_sources/modules/numeric_claim_source_guard.py --fail-on error`
6. Review FAQ proof blockers from `data_sources/modules/faq_proof_guard.py --fail-on error`
7. Review PAA provenance blockers from `data_sources/modules/paa_provenance_guard.py --fail-on error`
8. Review source support blockers from `data_sources/modules/source_support_guard.py --fail-on error`
9. Review customer proof diversity blockers from `data_sources/modules/customer_proof_diversity_guard.py --fail-on error`
10. Review review story identity blockers from `data_sources/modules/review_story_identity_guard.py --fail-on error`
11. Apply top 3-5 fixes
12. Rerun `/scrub`, the AI copy linter, URL validation, Metric Proof Pack guard, numeric claim source guard, FAQ proof guard, PAA provenance guard, source support guard, customer proof diversity guard, and review story identity guard
13. Re-score
14. Repeat once more if needed
15. If AI copy lint errors remain after 1 revision, URL validation fails, Metric Proof Pack guard fails, numeric claim source guard fails, FAQ proof guard fails, PAA provenance guard fails, source support guard fails, customer proof diversity guard fails, review story identity guard fails, or content quality remains below 85/100 or AEO/GEO remains below 90/100 after 2 iterations -> move to `review-required/`

### 11. Run Optimization Agents
After passing quality threshold:
- `content-analyzer` agent
- `seo-optimizer` agent
- `meta-creator` agent
- `internal-linker` agent
- `keyword-mapper` agent

---

## Complete Output Structure

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
- @context/brand-voice.md - your brand tone and messaging
- @context/style-guide.md - Formatting rules
- @context/seo-guidelines.md - SEO requirements
- @context/aeo-geo-blog-strategy.md - AEO/GEO requirements for blog writing
- @context/target-keywords.md - keyword targets, clusters, and metric boundaries
- @context/internal-links-map.md - Linking targets
- @context/features.md - your brand product information
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
- 2000-3000+ words
- Proper H1/H2/H3 hierarchy
- 3-5 internal links
- 2-3 external authority links
- Compelling hook (not generic)
- 2-3 mini-stories with specifics
- 2-3 contextual CTAs
- FAQ with real user questions
- General content quality score 85/100+
- AEO/GEO score 90/100+

### Differentiation Standards
- Addresses 3+ competitor gaps
- Includes 5+ unique social insights
- Uses real user language (not SEO-speak)
- Updates outdated competitor info
- Provides depth where competitors are thin

- **Review proof routing**: For review-derived public copy, run the selector and `review_story_identity_guard.py` before scoring. Keep detailed Review Story Selection, Capterra theme, exact-quote, rating, and metric boundaries in `context/aeo-geo-blog-strategy.md`.
