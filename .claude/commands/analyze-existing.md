# Analyze Existing Command

Use this command to review and analyze existing your company blog posts for SEO opportunities, content gaps, and improvement areas.

## Usage
`/analyze-existing [URL or file path]`

## What This Command Does
1. Fetches and analyzes existing blog post content
2. Evaluates current SEO performance and optimization
3. Identifies outdated information or statistics
4. Suggests content expansion opportunities
5. Audits AEO/GEO rewrite readiness and missing strategy inputs
6. Provides actionable improvement recommendations

## Process

### Content Analysis
- **URL/File Input**: Accept either a live URL or local file path
- **Content Extraction**: Pull the full article text, headings, and structure
- **Publication Date Check**: Note when content was originally published
- **Current Relevance**: Identify outdated information, statistics, or references
- **Completeness**: Assess if topic coverage is comprehensive or has gaps

### SEO Audit (Enhanced with New Analysis Tools)
- **Search Intent Analysis** (NEW!): Determine if content matches user search intent (informational/commercial/transactional/navigational)
- **Target Keyword**: Identify primary keyword and variations
- **Keyword Density & Clustering** (NEW!): Deep analysis of keyword density, distribution heatmap, topic clustering, and keyword stuffing risk detection
- **Keyword Placement**: Check H1, H2, first 100 words, meta title/description
- **Heading Structure**: Evaluate H1-H6 hierarchy and keyword integration
- **Content Length Comparison** (NEW!): Compare word count against top 10-20 SERP competitors to determine optimal length
- **Meta Elements**: Review meta title (50-60 chars) and description (150-160 chars)
- **Internal Links**: Count and evaluate quality of internal links (aim for 3-5+)
- **External Links**: Check for authoritative external sources
- **Readability Score** (NEW!): Calculate Flesch Reading Ease, Flesch-Kincaid Grade Level, passive voice ratio, sentence complexity
- **SEO Quality Rating** (NEW!): Overall score (0-100) with category breakdowns for content, keywords, meta, structure, links, and readability

### AEO/GEO Rewrite Readiness
- **AEO/GEO readiness audit**: Check direct-answer intro, Key Takeaways, Capsule Method coverage, FAQ/PAA structure, schema notes, source-backed claims, named metadata, and one-idea-per-section structure.
- **Missing strategy inputs**: Identify missing `topic`, `audience`, `main_question`, `related_questions`, `tone`, `expertise`, and `length` inputs from @context/aeo-geo-blog-strategy.md.
- **PAA/FAQ provenance**: Record whether selected questions come from AnswerSocrates, SERP, Reddit, YouTube, or a user PAA/FAQ CSV. If no sourced questions exist, mark the rewrite blocked until the artifact or export is available.
- **Required PAA/source/proof artifacts**: List required `research/paa-questions-[topic-slug]-[YYYY-MM-DD].md`, source map, customer-proof source, author/reviewer source, and blocker notes before `/rewrite`.
- **Source map**: Identify external sources, supported claims, natural anchor text, and target sections needed for the rewrite.
- **E-E-A-T Proof Map**: Identify E-E-A-T proof details, Experience proof present/missing, Expertise proof present/missing, Authority/Trust proof present/missing, case-study proof candidates, Review-site VoC candidates, review-site experience evidence candidates, and proof gaps. Pull case-study URLs from @context/internal-links-map.md, approved metrics/proof candidates from @context/features.md, and review-site experience evidence / VoC or competitor experience themes from @context/competitor-analysis.md or future review-context files. Review narratives count as first-hand customer experience when reviewers describe product use, implementation, support, switching, pains, outcomes, or workflows. For review-site evidence, capture platform, URL, date checked, product/competitor, experience pattern, evidence summary, and whether any exact quote/rating claim was approved. Use review-derived stories as paraphrased, source-backed experience patterns by default. Exact quotes, named reviewers, star ratings, badges, rankings, aggregate ratings, and category claims require current source verification and brief-level approval.
- **Customer Proof Pack**: Audit whether a safe Customer Proof Pack exists for the rewrite. Required fields are Pack status, Quote Matrix candidates, Case-study proof paths, Review-site experience evidence, Approved metrics, Use in copy, Claims excluded, and approval status. If Pack status is partial or blocked, list missing proof inputs before `/rewrite`.
- **Claims excluded for missing proof**: List claims that must stay out of the rewrite because no public-facing source link, approved metric, case-study URL, review-site source, expert quote, or author/reviewer support exists.

### Competitive Context
- **SERP Position**: Research current ranking for target keywords (if known)
- **Top Competitors**: Identify top 3-5 ranking articles for same keywords
- **Content Gaps**: What do competitors cover that this article doesn't?
- **Competitive Advantage**: What unique angles or insights could differentiate this?

### User Experience
- **Introduction Hook**: Is the opening compelling and clear?
- **Structure**: Does the article flow logically with clear sections?
- **Actionability**: Are there practical takeaways and next steps?
- **Visual Elements**: Note if images, screenshots, or media are mentioned/needed
- **Call-to-Action**: Is there a clear CTA aligned with user intent?

## Output
Provides a comprehensive analysis report with:

### 1. Content Health Score (0-100)
Enhanced with new analysis modules:
- **SEO Quality Rating**: Overall SEO score with category breakdowns
- **Search Intent Alignment**: How well content matches search intent
- **Keyword Optimization**: Density, distribution, clustering analysis
- **Content Length Competitiveness**: Position vs SERP competitors
- **Readability Score**: Flesch scores and grade level
- **Relevance & Freshness**: Outdated content detection
- **User Experience**: Flow, structure, actionability

### 2. Quick Wins
Top 3-5 immediate improvements that can be made quickly:
- Update specific statistics or dates
- Add missing keywords to headings (with exact density recommendations)
- Optimize meta description
- Add internal links to specific pages
- Fix readability issues (sentence length, passive voice)

### 3. Strategic Improvements
Longer-term enhancements for maximum impact:
- **Content expansion**: Based on length comparison with competitors (e.g., "Add 800 words to match top performers")
- **Intent alignment**: Adjust content type to match search intent
- **Topic clustering**: Add missing semantic keywords and related topics
- New sections to add based on competitive gap analysis
- SEO optimization priorities from quality rating

### 4. Detailed Analysis Reports
The new Content Analyzer agent provides:
- **Search intent classification** with confidence scores
- **Keyword density heatmap** by section
- **Topic cluster visualization**
- **Competitive length benchmarks** (min, median, 75th percentile)
- **Readability metrics** (Flesch scores, sentence analysis, passive voice ratio)
- **SEO quality breakdown** by category (0-100 for each)
- **AEO/GEO readiness audit** covering direct answers, Capsule Method, FAQ/PAA, schema notes, source map, E-E-A-T Proof Map, Experience proof present/missing, Expertise proof present/missing, and proof gaps

### 5. Rewrite Recommendations
- **Priority Level**: Low / Medium / High / Critical (based on SEO score and competitive analysis)
- **Estimated Effort**: Light edit / Moderate update / Major rewrite / Complete refresh
- **Expected Impact**: Potential traffic increase, ranking improvement, engagement boost (data-driven estimates)
- **Specific improvements needed**: Exact word count targets, keyword density adjustments, readability fixes
- **Rewrite-specific AEO/GEO acceptance checklist**: Required direct-answer intro, 3-5 sourced FAQ/PAA questions, Source Map, E-E-A-T Proof Map, schema notes, AI copy linter zero errors, content quality 85/100+, and AEO/GEO 90/100+

### 6. Research Brief
If a rewrite is recommended, provide initial research brief including:
- Updated target keywords with optimal density targets
- Competitor articles to review with word count benchmarks
- New statistics or data to incorporate
- Trending angles or perspectives
- Search intent alignment strategy
- Optimal content length recommendation (based on SERP analysis)
- Internal linking opportunities
- Main answer target and AEO/GEO variable resolution
- PAA/FAQ provenance and selected 3-5 closest questions with intent labels
- Insight summary and suggested blog focus
- Source map with source, claim, anchor text, and target section
- E-E-A-T Proof Map with Experience proof present/missing, Expertise proof present/missing, case-study proof candidates, Review-site VoC candidates, review-site experience evidence candidates, Authority/Trust proof, and any proof gaps that must remain out of the rewrite
- Customer Proof Pack with Pack status, Quote Matrix candidates, Case-study proof paths, Review-site experience evidence, Approved metrics, Use in copy, Claims excluded, and approval status
- Context-backed metrics that can be used only with public-facing source links
- Required PAA/source/proof artifacts before `/rewrite`

## File Management
After completing the analysis, automatically save the report to:
- **File Location**: `research/analysis-[post-slug]-[YYYY-MM-DD].md`
- **File Format**: Markdown with scores, recommendations, and action items
- **Naming Convention**: Use lowercase, hyphenated post slug and current date

Example: `research/analysis-podcast-hosting-guide-2025-10-15.md`

## Next Steps
Based on the analysis, the system will suggest:
1. Running `/rewrite [topic]` if content needs significant updates
2. Running `/optimize [file]` if content needs light SEO polish
3. Archiving the post if it's no longer relevant or valuable

This ensures every analysis leads to clear, actionable next steps for improving your company blog content.
