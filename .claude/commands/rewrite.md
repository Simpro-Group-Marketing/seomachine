# Rewrite Command

Use this command to update and improve existing blog posts based on analysis findings.

## Usage
`/rewrite [topic or analysis file]`

## What This Command Does
1. Takes existing blog post content and improvement recommendations
2. Rewrites content with updated information and SEO optimization
3. Maintains original article structure where effective
4. Adds new sections to fill content gaps
5. Updates outdated statistics, examples, and references

## Process

### Pre-Rewrite Review
- **Original Content**: Read the existing article thoroughly
- **Analysis Report**: Review findings from `/analyze-existing` if available
- **Research Brief**: Check if new research brief exists for updated angles
- **Brand Voice**: Verify alignment with current @context/brand-voice.md
- **SEO Guidelines**: Apply latest requirements from @context/seo-guidelines.md
- **AEO/GEO Strategy**: Apply @context/aeo-geo-blog-strategy.md before drafting
- **Competitive Context**: Understand what's changed in SERP since original publication
- **Lightning Overlay**: If the article, topic, or analysis mentions Simpro Lightning, AroFlo Lightning, BigChange Lightning, Simpro Group Lightning, JustAsk, Cooper, FieldReady, JobReady, JobScribe, JobBrief, Price Lock, AI tax, TrueTime, DirectLine, Coming Specialists, or any named roadmap specialist, also load @context/lightning-positioning.md and correct the copy against that scoped overlay.

### AEO/GEO Rewrite Requirements

Before drafting, complete AEO/GEO variable resolution from the analysis report, current article, repo context, target keyword, and sourced research:
- `topic`
- `audience`
- `main_question`
- `related_questions`
- `tone`
- `expertise`
- `length`

Required rewrite inputs:
- **PAA/FAQ provenance**: Cite the source for selected questions: AnswerSocrates, SERP, Reddit, YouTube, or a user PAA/FAQ CSV. If using AnswerSocrates, save or cite `research/paa-questions-[topic-slug]-[YYYY-MM-DD].md`. If no sourced question set exists, collect one or record the blocker before writing.
- **Question selection**: Select 3-5 closest questions, label intent, write an insight summary, write a suggested blog focus, and assign each question to an H2, H3, or FAQ answer format.
- **Source Map**: Document each external source, the claim it supports, the natural anchor text, and the target section.
- **E-E-A-T Proof Map**: Resolve E-E-A-T proof details, Experience, Expertise, and Authority/Trust before drafting. Experience includes customer case studies, customer outcomes, review-site VoC themes, implementation/support themes, user pain, and field workflow examples. Expertise includes product/feature knowledge, source-backed workflow explanations, expert quotes, author/reviewer metadata, and Simpro workflow specificity. Authority/Trust includes public research, case-study URLs, review-site/source links, limitations, caveats, and no invented proof.
- **Context proof routing**: Pull case-study URLs from @context/internal-links-map.md, approved metrics/proof candidates from @context/features.md, and review-site VoC or competitor experience themes from @context/competitor-analysis.md or future review-context files. Context-backed metrics are valid only when paired with public-facing source links in the article body.
- **down-funnel internal link**: Every rewrite must include at least 1 contextual body link to `/industries`, `/industries/...`, `/solutions/...`, or `/features/...` from @context/internal-links-map.md. Prefer the specific industry page when industry intent is clear, the `https://www.simprogroup.com/industries` hub for broad trades or general industry topics, the relevant solution page for category/workflow topics, and the relevant feature page for feature/workflow topics. Anchor text must match the destination keyword or an approved anchor example from @context/internal-links-map.md.
- **Functional feature/solution anchors**: Feature and solution links must use function-bearing anchor text that explains the workflow, category, or outcome behind the destination. A feature or solution name alone is not enough. Use anchors like "field service payments," "accounts receivable follow-up with Fast Cash," or "field service management software" instead of "Simpro Payments," "Fast Cash," or "Simpro Premium."
- **Simpro web copy rules**: Use numerals for cardinal numbers, including 1-9. Do not write number words such as "one," "two," or "three" in final public copy. Always put a comma before "because". Only 1 link per paragraph. Move the second link to a separate paragraph or remove it. Do not write source/proof meta-commentary such as "that case study is useful for this topic" or "this source is relevant for the article." Translate proof into audience-facing takeaways, outcomes, or workflow lessons.
- **Schema notes**: Include BlogPosting, FAQPage when FAQ is present, Author, and VideoObject when video is embedded.

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
- New sections to fill competitive content gaps
- Recent industry trends or developments
- Additional examples or use cases
- Better introduction hook if current one is weak
- Stronger conclusion and CTA
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
- **Expand**: Deepen shallow sections with more detail
- **Add**: Insert new sections to cover content gaps
- **Update**: Refresh stats, examples, and references throughout
- **Restructure**: Reorganize if flow can be improved
- **Optimize**: Integrate keywords more naturally if needed
- **AEO/GEO**: Add 50-60 word direct-answer capsules below the H1 and at least 60% of major H2s

#### 4. Strengthened Conclusion
- Update takeaways to reflect new/expanded content
- Refresh CTA to align with current business priorities
- End with forward-looking perspective

### SEO Enhancement

#### Keyword Optimization
- **Primary Keyword**: Ensure 1-2% density throughout
- **Keyword Placement**: Add to H2s if missing
- **Semantic Variations**: Use related keywords naturally
- **First 100 Words**: Confirm primary keyword appears early
- **Natural Integration**: Never force keywords unnaturally

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
- **Meta Title**: Rewrite if not optimized or compelling
- **Meta Description**: Refresh to highlight updated content
- **URL Slug**: Generally keep original to preserve any rankings
- **Featured Snippet**: Optimize for snippet opportunity if identified

### Quality Assurance

#### Content Accuracy
- Verify all updated statistics and data points
- Ensure technical information is current
- Confirm examples reflect current industry landscape
- Check that product references are up-to-date
- Confirm the public rewrite body does not mention "repo context," context file paths, Source Maps, PAA artifacts, change summaries, or internal proof-path notes. Context files are the internal source of truth for approved claims, proof candidates, and approved metrics, but they are not public-facing citations.
- Confirm PAA/FAQ provenance, Source Map, E-E-A-T Proof Map, direct-answer capsules, and schema notes are present for moderate, major, and complete rewrites
- Confirm every context-backed metric uses a public-facing source link, such as a case-study URL, review-site URL, or public research source.

#### Brand Alignment
- Maintain brand voice from @context/brand-voice.md
- Follow formatting from @context/style-guide.md
- Ensure messaging aligns with current positioning
- Keep focus on target audience needs
- For Lightning-specific rewrites, fix unprefixed customer-facing Lightning references, JustAsk-as-agent errors, Cooper role confusion, incorrect agent names, first-reference "the trades" category wording, unsupported proof claims, and stale pricing or competitor claims.

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

Major Changes:
- [Summary of significant updates]
- [New sections added]
- [Content removed/consolidated]

SEO Improvements:
- [Keyword optimization details]
- [Internal links added]
- [Meta element updates]

Content Updates:
- [Statistics refreshed]
- [Examples updated]
- [New industry trends added]

AEO/GEO Inputs:
- PAA/FAQ provenance: [AnswerSocrates / SERP / Reddit / YouTube / user CSV / blocker]
- PAA artifact path: [research/paa-questions-[topic-slug]-[YYYY-MM-DD].md or not available]
- Selected questions: [3-5 closest questions with intent labels]
- Suggested blog focus: [1-2 sentence focus statement]
- Source Map: [source, claim, anchor text, target section]
- E-E-A-T Proof Map: [Experience proof, Expertise proof, Authority/Trust proof, case-study candidates, review-site VoC candidates, claims excluded because proof is missing]
- Context-backed metrics with public-facing source links: [metric, proof path, public URL]
- Schema notes: [BlogPosting, FAQPage, Author, VideoObject if relevant]
---
```

### 3. Before/After Comparison
For major changes, note key differences:
- Original headline vs. new headline
- Original intro vs. new intro
- Sections added or removed
- Word count expansion
- SEO element improvements

## File Management
After completing the rewrite, save to:
- **File Location**: `rewrites/[topic-slug]-rewrite-[YYYY-MM-DD].md`
- **File Format**: Markdown with change summary frontmatter
- **Naming Convention**: Use original slug + "rewrite" + current date

Example: `rewrites/content-marketing-guide-rewrite-2025-10-15.md`

Also save the change summary separately:
- **File Location**: `rewrites/changes-[topic-slug]-[YYYY-MM-DD].md`

## Automatic Scrub, AI Copy Lint, Score, And Optimize

**CRITICAL**: Immediately after saving the rewritten article file, automatically invoke the content scrubber, run the AI copy linter, score the content, then run `/optimize`.

### Why This Matters
AI-generated content often contains invisible Unicode marks and characteristic punctuation patterns. Scrubbing handles cleanup. The linter handles AI-writing detection and Simpro style enforcement.

### Scrub, Lint, Score, And Optimize Process
1. **Invoke Scrubber**: Run `/scrub [file-path]` on the saved rewritten article file
2. **Invoke AI Copy Linter**: Run `python data_sources/modules/ai_copy_linter.py [file-path] --profile simpro-web --fail-on error`
3. **Invoke Content Scorer**: Run `python data_sources/modules/content_scorer.py [file-path]`
4. **Check Gates**: General content quality must be 85/100 or higher and AEO/GEO must be 90/100 or higher
5. **Invoke Optimizer**: Run `/optimize [file-path]` only after scrub, lint, and score gates are complete
6. **Automatic Execution**: This should happen automatically, not require user action
7. **Timing**: Must occur immediately after file save, before optimization agents
8. **Scope**: Scrub, lint, and score the main rewritten article file only (not change summary or analysis files)
9. **Error Handling**: If linter errors remain, revise once, rerun `/scrub`, rerun the linter, then route to `review-required/` with lint findings if errors remain. If score gates fail after 2 iterations, route to `review-required/` with scoring details.
10. **Warnings**: Include warning findings in review notes, but do not block unless strict mode is requested

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

### Example Workflow
```
1. Rewrite article → Save to rewrites/article-name-rewrite-2025-10-31.md
2. IMMEDIATELY run: /scrub rewrites/article-name-rewrite-2025-10-31.md
3. IMMEDIATELY run: python data_sources/modules/ai_copy_linter.py rewrites/article-name-rewrite-2025-10-31.md --profile simpro-web --fail-on error
4. IMMEDIATELY run: python data_sources/modules/content_scorer.py rewrites/article-name-rewrite-2025-10-31.md
5. Confirm 85/100 general content quality and 90/100 AEO/GEO
6. THEN run: /optimize rewrites/article-name-rewrite-2025-10-31.md
7. If errors or failed score gates remain, revise once, then rerun scrub, lint, and score
```

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
- Confirm optimal keyword placement and density

## Next Steps
After rewrite completion:
1. Review change summary and ensure all updates are intentional
2. Compare to original to verify improvements
3. Run `/optimize` for final polish if needed
4. Move to `/published` when ready
5. Note original URL to ensure proper redirect/replacement

This ensures every rewritten article is significantly improved while maintaining what worked in the original version.
