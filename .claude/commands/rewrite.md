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
- **E-E-A-T Proof Map**: Resolve E-E-A-T proof details, Experience, Expertise, and Authority/Trust before drafting. Experience includes customer case studies, customer outcomes, review-site experience evidence / VoC themes, implementation/support themes, user pain, and field workflow examples. Review narratives count as first-hand customer experience when reviewers describe product use, implementation, support, switching, pains, outcomes, or workflows. Expertise includes product/feature knowledge, source-backed workflow explanations, expert quotes, author/reviewer metadata, and Simpro workflow specificity. Authority/Trust includes public research, case-study URLs, review-site/source links, limitations, caveats, and no invented proof.
- **Context proof routing**: Pull case-study URLs from @context/internal-links-map.md, approved metrics/proof candidates from @context/features.md, and review-site experience evidence / VoC or competitor experience themes from @context/competitor-analysis.md or future review-context files. For review-site evidence, capture platform, URL, date checked, product/competitor, experience pattern, evidence summary, and whether any exact quote/rating claim was approved. Use review-derived stories as paraphrased, source-backed experience patterns by default. Exact quotes, named reviewers, star ratings, badges, rankings, aggregate ratings, and category claims require current source verification and brief-level approval. Context-backed metrics are valid only when paired with public-facing source links in the article body.
- **Review proof routing**: For review-derived E-E-A-T stories, consult `customer_proof_selector.py` with `--slate --roles experience_story --require-eeat-story`, then run the review story identity gate from the required stack below. Use `context/aeo-geo-blog-strategy.md` for Review Story Selection, Review Site Theme Selection, Capterra theme use, exact-quote, rating, and metric boundaries.
- **Customer proof selection governance**: Run or consult `python data_sources/modules/customer_proof_selector.py "[topic]" --title "[title]" --objective "[objective]" --slate --roles metric,quote,theme --limit 10`. Use the generated selector-first `Customer Proof Slate` before drafting; choose the strongest approved proof for the objective; if selected proof is overused, add a selector-backed, source-specific `Reuse reason` in the validation sidecar.
- **Proof-index health**: Run or consult `python data_sources/modules/customer_proof_index_health.py --index context/customer-proof-index.json --ledger context/customer-proof-usage-ledger.json` before adding proof candidates.
- **Proof-index intake**: Add new proof candidates through `context/customer-proof-intake-template.csv` and validate with `python data_sources/modules/customer_proof_index_intake.py validate [input.csv] --index context/customer-proof-index.json` before relying on them in selector slates.
- **Customer Proof Pack**: Resolve selected proof, approved quotes/metrics, and excluded claims before placing customer proof. If the pack is partial or blocked, omit unsupported claims.
- **down-funnel internal link**: Every rewrite must include at least 1 contextual body link to `/industries`, `/industries/...`, `/solutions/...`, or `/features/...` from @context/internal-links-map.md. Prefer the specific industry page when industry intent is clear, the `https://www.simprogroup.com/industries` hub for broad trades or general industry topics, the relevant solution page for category/workflow topics, and the relevant feature page for feature/workflow topics. Anchor text must match the destination keyword or an approved anchor example from @context/internal-links-map.md.
- **Functional feature/solution anchors**: Feature and solution links must use function-bearing anchor text that explains the workflow, category, or outcome behind the destination. A feature or solution name alone is not enough. Use anchors like "field service payments," "accounts receivable follow-up with Fast Cash," or "field service management software" instead of "Simpro Payments," "Fast Cash," or "Simpro Premium."
- **Simpro web copy rules**: Use numerals for cardinal numbers, including 1-9. Do not block source-visible metric wording when a public proof source spells out the number; preserve the supported claim wording and rely on Metric Proof Pack, numeric claim source guard, and source support guard for proof. Always put a comma before "because". Only 1 link per paragraph. Move the second link to a separate paragraph or remove it. Do not write source/proof meta-commentary such as "that case study is useful for this topic" or "this source is relevant for the article." Translate proof into audience-facing takeaways, outcomes, or workflow lessons.
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
- FAQ proof: [each claim-bearing FAQ answer has a public proof link or question-specific Source Map / FAQ Proof Map entry with a public URL; Context file paths alone do not count]
- Suggested blog focus: [1-2 sentence focus statement]
- Source Map: [source, claim, anchor text, target section]
- E-E-A-T Proof Map: [Experience proof, Expertise proof, Authority/Trust proof, case-study candidates, review-site VoC candidates, review-site experience evidence candidates, claims excluded because proof is missing]
- Customer Proof Pack:
  - Pack status: [ready / partial / blocked]
  - Customer Proof Slate: [selector command plus metric, quote, theme, and experience_story role rows when applicable]
  - Quote Matrix candidates: [customer, trade, region, theme, exact quote or summary, source row/link, approval status]
  - Case-study proof paths: [customer, public URL, supported non-numeric theme]
  - Review-site experience evidence: [platform, URL, date checked, product/competitor, experience pattern, evidence summary, exact quote/rating approval status]
  - Customer Proof Selection Decision: [selector command, selected proof IDs, rejected stronger candidates, final use in copy]
  - Reuse reason: [source-specific; required when customer-proof-usage-ledger.json marks the selected proof as overused; must prove no stronger underused approved proof fits the same role]
  - Approved quotes: [exact quote/testimonial, customer/brand/reviewer, source type, public proof URL, Evidence, approval status]
  - Approved metrics: [named customer metric, customer/brand, public proof URL, Evidence, approval status]
  - Use in copy: [exact quote / paraphrased theme / named metric / omit]
  - Claims excluded: [claim and missing proof reason]
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

## Validation Sidecar

Save non-public proof infrastructure to a validation sidecar at `research/validation-[topic-slug]-[YYYY-MM-DD].md`. Do not put an `Editorial Validation Appendix`, `PAA/FAQ Provenance`, `Metric Proof Pack`, `Source Map`, `Customer Proof Pack`, `FAQ Proof Map`, or structured data plan in the publishable rewrite.

Preferred publish readiness command:
```bash
python data_sources/modules/publish_readiness.py [file] --proof-sidecar research/validation-[topic-slug]-[YYYY-MM-DD].md
```

Before proof gates, run `python data_sources/modules/public_artifact_guard.py [file-path] --fail-on error` to confirm the rewrite is clean. Then run proof-aware gates with `--proof-sidecar research/validation-[topic-slug]-[YYYY-MM-DD].md` so the guards can read PAA provenance, metric proof, FAQ proof maps, source maps, and Customer Proof Pack rows without exposing them in public copy.

## Automatic Scrub, AI Copy Lint, URL Validation, Metric Proof Pack Guard, Numeric Claim Source Guard, FAQ Proof Guard, PAA Provenance Guard, Source Support Guard, Customer Proof Diversity Guard, Score, And Optimize

**CRITICAL**: Immediately after saving the rewritten article file, automatically invoke the content scrubber, run the AI copy linter, run URL validation, run the Metric Proof Pack guard, run the numeric claim source guard, run the FAQ proof guard, run the PAA provenance guard, run the source support guard, run the customer proof diversity guard, score the content, then run `/optimize`.

### Why This Matters
AI-generated content often contains invisible Unicode marks and characteristic punctuation patterns. Scrubbing handles cleanup. The linter handles AI-writing detection and Simpro style enforcement.

### Scrub, Lint, URL Validation, Metric Proof Pack Guard, Numeric Claim Source Guard, FAQ Proof Guard, PAA Provenance Guard, Source Support Guard, Customer Proof Diversity Guard, Score, And Optimize Process
1. **Invoke Scrubber**: Run `/scrub [file-path]` on the saved rewritten article file
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
11. **Invoke Content Scorer**: Run `python data_sources/modules/content_scorer.py [file-path] --proof-sidecar research/validation-[topic-slug]-[YYYY-MM-DD].md --validate-urls --validate-source-support`
12. **Check Gates**: General content quality must be 85/100 or higher, AEO/GEO must be 90/100 or higher, URL validation must pass, public artifact guard must pass, Metric Proof Pack guard must pass, numeric claim source guard must pass, FAQ proof guard must pass, PAA provenance guard must pass, source support guard must pass, and customer proof diversity guard must pass
13. **Invoke Optimizer**: Run `/optimize [file-path]` only after scrub, public artifact guard, lint, URL validation, Metric Proof Pack guard, numeric claim source guard, FAQ proof guard, PAA provenance guard, source support guard, customer proof diversity guard, and score gates are complete
14. **Automatic Execution**: This should happen automatically, not require user action
15. **Timing**: Must occur immediately after file save, before optimization agents
16. **Scope**: Scrub, lint, URL validation, Metric Proof Pack guard, numeric claim source guard, FAQ proof guard, PAA provenance guard, source support guard, customer proof diversity guard, review story identity guard, and score the main rewritten article file only; proof maps live in the validation sidecar.
17. **Error Handling**: If linter errors remain, revise once, rerun `/scrub`, rerun the linter, then route to `review-required/` with lint findings if errors remain. If public artifact guard fails, move proof-only headings to the validation sidecar. If URL validation fails, replace or verify the unresolved link before `/optimize`. If Metric Proof Pack guard fails, research usable metrics and add `Metric Proof Pack` rows with `Search log`, `Approved metric`, public URL or proof artifact, source-visible Evidence, Status: approved, and Use in the sidecar. If numeric claim source guard fails, add a public proof link, map the same claim to a Source Map / Proof Pack row with a public URL or local proof artifact in the sidecar, or remove the unsupported number. If FAQ proof guard fails, add a public proof link inside the FAQ answer, map the exact question to a question-specific Source Map / FAQ Proof Map entry with a public URL in the sidecar, or remove the unsupported claim. If PAA provenance guard fails, add a `PAA/FAQ Provenance` block with an allowed source, real artifact path, and exact selected questions to the sidecar. If source support guard fails, add a strict proof row with Claim, URL, Evidence, and Status: approved to the sidecar, use Evidence visible in the cited source, or remove the unsupported claim. If customer proof diversity guard fails, add Quote Matrix, Reference, Customer Story, or review-site search evidence to the Customer Proof Pack, add Customer Proof Selection Decision, or document a source-specific `Reuse reason` plus selector-backed proof that no stronger underused approved proof fits the same role. If review story identity guard fails, add an identity-backed Review Story Selection with a public review URL and same paragraph article link, or remove the review-derived story. Context file paths alone do not count. If score gates fail after 2 iterations, route to `review-required/` with scoring details.
18. **Warnings**: Include warning findings in review notes, but do not block unless strict mode is requested

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
- Line-level findings for FAQ answers missing a public proof link or question-specific Source Map entry

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
2. Run `/scrub`, AI copy lint, URL validation, the required proof gate stack above, and the scorer from the required stack.
3. Confirm 85/100 general content quality, 90/100 AEO/GEO, and passing proof gates.
4. Then run `/optimize rewrites/article-name-rewrite-2025-10-31.md`.
5. If blockers remain, revise once and rerun the same stack.

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
