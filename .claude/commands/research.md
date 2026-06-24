# Research Command

Use this command to conduct comprehensive SEO keyword research and competitive analysis before writing new content.

## Usage
`/research [topic]`

## What This Command Does
1. Performs keyword research for your industry-related topics
2. Analyzes top-ranking competitor content
3. Identifies content gaps and opportunities
4. Develops unique angle for your company perspective
5. Creates detailed research brief for writing

## Process

### Keyword Research
- **Primary Keyword**: Identify main target keyword for the topic
- **Search Volume & Difficulty**: Research estimated monthly searches and competition level
- **Keyword Variations**: Find semantic variations and long-tail opportunities
- **Related Questions**: Discover what people are actually asking (People Also Ask, forums, Reddit)
- **Search Intent**: Determine if intent is informational, navigational, commercial, or transactional
- **Topic Cluster**: Identify how this topic fits into your company content clusters

### Competitive Analysis
- **Top 10 SERP Review**: Analyze the top 10 ranking articles for target keyword
- **Content Length**: Note word count of top-performing articles (benchmark target)
- **Common Themes**: What topics/sections do all top articles cover?
- **Content Gaps**: What's missing from competitor coverage?
- **Unique Angles**: What perspectives or insights are underexplored?
- **Featured Snippets**: Identify if there's a featured snippet opportunity
- **Domain Authority**: Note which competitors rank (indie blogs vs. major publications)

### Context Integration
- **Must-read context before drafting the brief**:
  - @context/brand-voice.md for Simpro voice, FY26 positioning, audience maturity archetypes, and best-fit targeting boundaries
  - @context/features.md for Simpro capabilities, add-ons, AI positioning, implementation, integrations, security, proof points, and fit boundaries
  - @context/style-guide.md for terminology, product-name rules, tone, regional language, and forbidden phrasing
  - @context/internal-links-map.md for sitemap-backed internal links
  - @context/target-keywords.md for sitemap-derived topic clusters, first-party GSC/GA4 performance signals, and remaining metric boundaries
  - @context/competitor-analysis.md for competitive differentiation and objections
  - @context/cro-best-practices.md for proof-source workflow and CTA/trust-signal guidance
  - @context/aeo-geo-blog-strategy.md for AEO/GEO variable resolution, Capsule Method, PAA/FAQ selection, source mapping, and quality gates
- **Lightning overlay**: If the topic mentions Simpro Lightning, AroFlo Lightning, BigChange Lightning, Simpro Group Lightning, JustAsk, Cooper, FieldReady, JobReady, JobScribe, JobBrief, Price Lock, AI tax, TrueTime, DirectLine, Coming Specialists, or any named roadmap specialist, also read @context/lightning-positioning.md and apply it as a scoped overlay.
- **Simpro advantage**: Identify how Simpro's product features, customer proof, and best-fit use cases naturally enhance this topic.
- **Customer proof routing**: When citing customer proof, pair the case-study URL/theme from @context/internal-links-map.md with the metric/proof point from @context/features.md. Use exact quotes only when verified from the case-study page, Quote Matrix, Customer Stories, or References; if no mapped metric exists, cite only the broad theme.
- **Proof-index health**: Run `python data_sources/modules/customer_proof_index_health.py --index context/customer-proof-index.json --ledger context/customer-proof-usage-ledger.json` before adding proof candidates or selector slates.
- **Customer proof selection governance**: Before selecting or drafting proof, resolve `topic`, `title`, and `objective`, automatically run `python data_sources/modules/customer_proof_selector.py "[topic]" --title "[title]" --objective "[objective]" --slate --roles metric,quote,theme,experience_story --require-eeat-story --limit 10`, and write the generated selector-first `Customer Proof Slate` to the validation sidecar. If inputs are missing, resolve them from the brief/context or stop before drafting customer proof. If the selector fails, write the blocker into the sidecar and do not invent proof. experience_story consideration is required and E-E-A-T story usage is optional. If no story fits, use `Selected: [none]` with section-specific rejection reasons. Edit selected/rejected rows only when editorial judgment requires it. If selected proof is overused, the sidecar needs a selector-backed, source-specific `Reuse reason`. Full policy lives in `context/aeo-geo-blog-strategy.md`.
- **Proof-index intake**: Add new proof candidates through `context/customer-proof-intake-template.csv` and validate with `python data_sources/modules/customer_proof_index_intake.py validate [input.csv] --index context/customer-proof-index.json` before relying on them in selector slates.
- **Customer proof diversity gate**: Plan for `/publish-readiness [file] --proof-sidecar research/validation-[topic-slug]-[YYYY-MM-DD].md` before scoring or `/optimize`. The brief and sidecar must include non-case-study proof search evidence when case studies are selected.
- **Review proof routing**: For review-site experience evidence, use Playwright MCP for live collection, run the selector with `--require-eeat-story --proof-role experience_story` when Review Story Selection is needed, and let `/publish-readiness` run the review story identity gate before scoring. Keep detailed Review Site Theme Selection, Capterra, exact-quote, rating, and metric boundaries in `context/aeo-geo-blog-strategy.md`.
- **Optional proof-backed customer/review POV**: Use a proof-backed customer/review POV only when it improves the article objective. If no actual person or business POV fits, omit the story. Fictional named personas are prohibited; unnamed workflow scenarios are explanatory only and do not count as E-E-A-T.
- **Brand alignment**: Apply Simpro's authoritative, ambitious, trades-focused, practical, outcomes-driven voice.
- **Evidence boundaries**: Do not present search volume, ranking, conversion priority, or live SERP findings as verified unless checked with GSC, GA4, DataForSEO, Ahrefs/Semrush, or live SERP review in this run.
- **Lightning evidence boundary**: Do not use time-sensitive Lightning pricing, roadmap, or competitor claims publicly unless they are verified in the current run or explicitly sourced from approved current material.

### Simpro Industry Focus
- **Trade operator angle**: Explain how this topic affects residential and commercial trade service businesses, especially low voltage, HVAC, plumbing, electrical/data, mechanical, and multi-trade operators.
- **Best-fit boundaries**: Use the Product Marketing Best-Fit Targeting Framework. Simpro is strongest for residential, light commercial, and medium commercial work involving small jobs, recurring contracts, inspections, maintenance, repairs, installations, and mid-sized projects. Be cautious with mostly residential North America, heavy commercial, industrial, general contractors, and complex-project-dominant businesses.
- **Customer maturity**: When useful, map pain points to the Empower, Elevate, and Excel archetypes from @context/brand-voice.md.
- **Product specificity**: Bring in relevant Simpro capabilities from @context/features.md, such as real-time job costing, quote-to-cash workflows, Simpro Payments, Delight, Fast Cash, Data Feed, Digital Forms, Maintenance Planner, Takeoffs, Multi-Company, Simtrac, SMS Messaging, Sage Intacct, implementation packages, and security/infrastructure proof.
- **Pain points**: Anchor recommendations in margin visibility, cash flow, admin reduction, field adoption, recurring maintenance, asset compliance, quoting speed, inventory, and scaling without chaos.

### Content Planning
- **Recommended Structure**: Outline H2 and H3 headings based on research
- **Content Depth**: Determine target word count (typically 2000-3000+ for SEO)
- **Supporting Evidence**: Identify statistics, studies, or data to include
- **Expert Sources**: Find industry experts or quotes to reference
- **Visual Opportunities**: Suggest images, screenshots, or graphics needed
- **Internal Links**: Map 3-5 key your company pages to link to (from @context/internal-links-map.md)
- **External Authority**: Identify 2-3 authoritative external sources to link
- **AEO/GEO Variables**: Resolve `topic`, `audience`, `main_question`, `related_questions`, `tone`, `expertise`, and `length` where possible from repo context and research evidence
- **Source Mapping**: For each credible external source, document the claim it supports, the natural anchor phrase, and the target section
- **Metric Proof Pack**: For software, comparison, guide, pricing, cost, ROI, KPI, profit, margin, or vs topics, extract usable numbers before writing. Record `Search log`, each `Approved metric`, public proof URL or local proof artifact, source-visible Evidence, Status: approved, and intended Use. Plan for `/publish-readiness` before writing or scoring.
- **Validation sidecar**: Store proof-only blocks in `research/validation-[topic-slug]-[YYYY-MM-DD].md`, not in the public draft. The sidecar can contain `PAA/FAQ Provenance`, `Metric Proof Pack`, `Source Map`, `Customer Proof Pack`, `FAQ Proof Map`, and structured data notes. Do not add an `Editorial Validation Appendix` to blog copy. Preferred publish check: `/publish-readiness [file] --proof-sidecar research/validation-[topic-slug]-[YYYY-MM-DD].md`.
- **PAA/FAQ Inputs**: If AnswerSocrates or a PAA/FAQ CSV has been used, identify the 3-5 closest questions, intent labels, and suggested article placement

### Hook Development
- **Introduction Angle**: Compelling way to open the article
- **Value Proposition**: Clear benefit reader will get from article
- **Contrarian Elements**: Any unexpected perspectives to explore
- **Story Opportunities**: Real examples or case studies to feature

## Output
Provides a comprehensive research brief with:

### 1. SEO Foundation
- **Primary Keyword**: [keyword] (volume, difficulty)
- **Secondary Keywords**: 3-5 related keywords and variations
- **Target Word Count**: Minimum words needed to compete
- **Featured Snippet Opportunity**: Yes/No, format (paragraph, list, table)
- **AEO/GEO Variables**: topic, audience, main_question, related_questions, tone, expertise, length
- **PAA/FAQ Questions**: 3-5 closest questions with intent labels and article section mapping
- **Source Map**: source, supported claim, anchor text, target section
- **Metric Proof Pack**:
  - **Metric requirement**: required / not applicable
  - **Search log**: [public sources and local proof artifacts checked for usable numbers]
  - **Approved metric**: [metric claim, public proof URL or local proof artifact, source-visible Evidence, Status: approved, intended Use]
  - **Rejected metrics**: [candidate metric and missing proof reason]
- **Customer Proof Pack**:
  - **Pack status**: ready / partial / blocked
  - **Topic or page fit**: [topic, audience, region, trade, funnel stage]
  - **Customer Proof Slate**: [selector command plus metric, quote, theme, and experience_story role rows; story usage optional]
  - **Quote Matrix candidates**: [customer, trade, region, theme, exact quote or summary, source row/link, approval status]
  - **Case-study proof paths**: [customer, public URL, supported metric/theme]
  - **Review-site experience evidence**: [platform, URL, date checked, product/competitor, experience pattern, evidence summary, exact quote/rating approval status]
  - **Customer Proof Selection Decision**: [selector command, selected proof IDs, rejected stronger candidates, final use in copy]
  - **Reuse reason**: [source-specific; required when customer-proof-usage-ledger.json marks the selected proof as overused; must prove no stronger underused approved proof fits the same role]
  - **Approved quotes**: [exact quote/testimonial, customer/brand/reviewer, source type, public proof URL, Evidence, approval status]
  - **Approved metrics**: [metric, customer, source file, public proof URL]
  - **Use in copy**: [exact quote / paraphrased theme / named metric / omit]
  - **Claims excluded**: [claim and missing proof reason]

### 2. Competitive Landscape
- **Top 3 Competitor Articles**: URLs and key takeaways from each
- **Common Sections**: Must-cover topics based on SERP analysis
- **Content Gaps**: Opportunities to provide unique value
- **Differentiation Strategy**: How your company can stand out

### 3. Recommended Outline
```
H1: [Optimized headline with primary keyword]

Introduction
- Hook
- Problem statement
- Value proposition

H2: [Main section 1]
H3: [Subsection]
H3: [Subsection]

H2: [Main section 2]
...

Conclusion
- Key takeaways
- Call to action
```

### 4. Supporting Elements
- **Statistics to Include**: 5-7 relevant data points with sources
- **Expert Quotes**: Potential sources or existing quotes
- **Examples/Case Studies**: Real Simpro customer outcomes or relevant trade-service scenarios to feature
- **Visual Suggestions**: Screenshots, charts, or graphics needed

### 5. Internal Linking Strategy
- **Pillar Page**: Main your company pillar content to link to
- **Related Articles**: 2-4 relevant blog posts to link
- **Product Pages**: your company features to naturally mention
- **Resource Pages**: Tools or guides to reference

### 6. Meta Elements Preview
- **Meta Title**: Draft optimized title (50-60 characters)
- **Meta Description**: Draft compelling description (150-160 characters)
- **URL Slug**: Recommended URL structure

## File Management
After completing the research, automatically save the brief to:
- **File Location**: `research/brief-[topic-slug]-[YYYY-MM-DD].md`
- **File Format**: Markdown with clear sections and structured data
- **Naming Convention**: Use lowercase, hyphenated topic slug and current date

Example: `research/brief-podcast-editing-software-2025-10-15.md`

## Next Steps
The research brief serves as the foundation for:
1. Running `/write [topic]` to create the optimized article
2. Reference material for maintaining SEO focus throughout writing
3. Checklist to ensure all competitive gaps are addressed

This ensures every article is built on solid SEO research and strategic competitive positioning.
