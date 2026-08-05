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

### Non-AEO Editorial Contract

Use `context/blog-editorial-strategy.md`. Resolve the Reader Contract before recommending an outline or rewrite, then evaluate whether the existing article serves that reader, advances the distinctive angle, and delivers the promised payoff. Do not let this contract approve claims, proof, product language, or competitive assertions.

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
- **E-E-A-T Proof Map**: Identify Experience, Expertise, Authority/Trust, customer proof candidates, review-site candidates, and proof gaps. Use `context/aeo-geo-blog-strategy.md` for review, quote, rating, and metric boundaries.
- **Customer Proof Pack**: Audit whether safe customer proof exists for the rewrite. Record selected proof, approved quotes/metrics, excluded claims, and missing inputs before `/rewrite`.
- **Fred Voccola authority evaluation**: Resolve the rewrite `topic`, `title`, and `objective`, then automatically run `python data_sources/modules/fred_authority_selector.py "[topic]" --title "[title]" --objective "[objective]" --slate --limit 5` and write the complete `Fred Voccola Authority Selection` block from `context/aeo-geo-blog-strategy.md` to the validation sidecar. Evaluation is mandatory and public use is optional. The selector defaults to `Selected: none`; select a source explicitly only after reviewing it and confirming direct topical support. If the selector, vault, manifest, or inventories fail, record `Evaluation status: blocked` and the blocker; do not invent Fred evidence or recommend Fred public use.
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
- Customer Proof Pack with Pack status, Quote Matrix candidates, Case-study proof paths, Review-site experience evidence, Approved quotes, Approved metrics, Use in copy, Claims excluded, and approval status
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
